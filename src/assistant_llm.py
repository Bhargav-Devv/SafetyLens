"""
The SafetyLens assistant, backed by a watsonx.ai language model.

`src/agent.py` implements the decision flow deterministically: no language
model, no capacity to improvise, every refusal rule an assertion. This module is
the real thing - a language model given the three tools and the prompt.

THE DESIGN THAT MATTERS: the refusal rules are enforced in CODE, not in the
prompt alone.

A prompt is a request. A model under pressure - a user saying "just give me your
best guess" - will eventually grant the request, and no amount of capitalised
MUST NOT changes that. So every reply the model produces passes through
`_guard`, which checks it against the tool results from the same turn and
BLOCKS it if it:

  * cites a section that no tool returned this turn          (Rule 1)
  * quotes text that is not a substring of a tool result     (Rule 2)
  * names a hazard or a section after an abstention          (Rule 3)
  * answers a compliance question at all                     (Rule 5)

Rule 5 is checked before the model is called, so a compliance question never
reaches it. The rest are checked after, and a blocked reply is replaced with the
deterministic agent's answer for the same turn.

That inversion is the point. The prompt asks the model to behave; the guard
makes the behaviour true. And unlike a prompt, a guard can be unit-tested - see
`tests/test_assistant_llm.py`, which runs the whole loop against a scripted model that
deliberately tries to break every rule.

    python main.py bob --llm

Credentials come from `.env` (see `.env.example`) and are never logged.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from src import agent as det_agent
from src import assistant_tools

IAM_URL = "https://iam.cloud.ibm.com/identity/token"
CHAT_PATH = "/ml/v1/text/chat?version=2024-10-08"
SECTION_IN_TEXT = re.compile(r"\b1910\.\d+")
MAX_TOOL_ROUNDS = 4


class MissingCredentials(RuntimeError):
    pass


def _load_env() -> dict:
    """Read .env without a dependency. Values are never printed."""
    env = {}
    path = cfg.ROOT / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL", "WATSONX_MODEL_ID"):
        env.setdefault(k, os.environ.get(k, ""))
    return env


# --------------------------------------------------------------------------
# The watsonx.ai client
# --------------------------------------------------------------------------

class WatsonxClient:
    """Minimal watsonx.ai chat client with tool calling.

    Deliberately written against the REST API with `requests` rather than the
    `ibm-watsonx-ai` SDK: one dependency the project already has, and the HTTP
    exchange stays visible instead of disappearing into a wrapper.
    """

    def __init__(self, env: dict | None = None):
        self.env = env or _load_env()
        missing = [k for k in ("WATSONX_API_KEY", "WATSONX_PROJECT_ID", "WATSONX_URL")
                   if not self.env.get(k)]
        if missing:
            raise MissingCredentials(
                "Missing from .env: " + ", ".join(missing) + "\n"
                "Copy .env.example to .env and fill it in. The file is gitignored.\n"
                "Project ID: watsonx.ai -> Projects -> your project -> Manage -> General."
            )
        self.model_id = self.env.get("WATSONX_MODEL_ID") or "ibm/granite-3-8b-instruct"
        self._token = None
        self._token_expires = 0.0

    def _iam_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        resp = requests.post(
            IAM_URL, timeout=60,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "urn:ibm:params:oauth:grant-type:apikey",
                  "apikey": self.env["WATSONX_API_KEY"]},
        )
        if resp.status_code != 200:
            raise RuntimeError(
                f"IAM token request failed ({resp.status_code}). "
                "Check WATSONX_API_KEY. The key itself is not logged."
            )
        payload = resp.json()
        self._token = payload["access_token"]
        self._token_expires = time.time() + payload.get("expires_in", 3600)
        return self._token

    def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        url = self.env["WATSONX_URL"].rstrip("/") + CHAT_PATH
        body = {
            "model_id": self.model_id,
            "project_id": self.env["WATSONX_PROJECT_ID"],
            "messages": messages,
            "max_tokens": 900,
            "temperature": 0,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice_option"] = "auto"
        resp = requests.post(
            url, timeout=180, json=body,
            headers={"Authorization": f"Bearer {self._iam_token()}",
                     "Content-Type": "application/json", "Accept": "application/json"},
        )
        if resp.status_code != 200:
            raise RuntimeError(f"watsonx chat failed ({resp.status_code}): {resp.text[:300]}")
        return resp.json()


# --------------------------------------------------------------------------
# Tool schemas in the shape a chat API expects
# --------------------------------------------------------------------------

def tool_specs() -> list[dict]:
    return [{
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    } for t in assistant_tools.TOOLS]


def system_prompt() -> str:
    """The prompt, read from the file that documents it.

    Extracted from the fenced block in docs/assistant_system_prompt.md so there is one
    copy rather than two that drift apart.
    """
    text = (cfg.ROOT / "docs" / "assistant_system_prompt.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```text\n(.*?)```", text, re.S)
    if not blocks:
        raise RuntimeError("No ```text block found in docs/assistant_system_prompt.md")
    return blocks[0].strip()


# --------------------------------------------------------------------------
# The guard
# --------------------------------------------------------------------------

class GuardViolation(Exception):
    """A blocked reply.

    `detail` is for the trace and the log. It is deliberately NOT shown to the
    user, because for rules 1 and 2 the detail would contain the very thing
    being blocked - the invented section number, or the fabricated quotation.
    Printing "I blocked the claim that 1910.9999 requires quarterly audits"
    puts the invention on screen anyway, which was the whole point of blocking
    it. The user is told the rule; the developer gets the detail.
    """

    SUMMARY = {
        "1": "a regulatory citation that did not come from the corpus",
        "2": "a quotation that is not in the cited section",
        "3": "an answer where the classifier had declined to classify",
        "5": "a compliance determination",
        "loop": "an unterminated sequence of tool calls",
    }

    def __init__(self, rule: str, detail: str):
        super().__init__(f"Rule {rule}: {detail}")
        self.rule = rule
        self.detail = detail

    @property
    def public(self) -> str:
        return self.SUMMARY.get(self.rule, "a refusal rule")


def _guard(reply: str, tool_results: list[dict]) -> None:
    """Check a model reply against the tool results from the same turn.

    Raises GuardViolation on the first breach. The caller falls back to the
    deterministic agent, so a blocked reply degrades to a correct one rather
    than to an error.
    """
    abstained = any(r.get("status") in ("abstained", "insufficient_input")
                    for r in tool_results)

    returned = set()
    corpus_text = []
    for r in tool_results:
        for s in r.get("standards", []) or []:
            returned.add(s["section"])
            corpus_text.append(s.get("quote", ""))
        if r.get("section"):
            returned.add(r["section"])
            corpus_text.append(r.get("text", ""))

    # Rule 3 first. After an abstention ANY citation is a rule 3 breach, and
    # reporting it as rule 1 ("that section was not returned") would name the
    # symptom instead of the cause - the model was asked not to answer at all.
    if abstained:
        if SECTION_IN_TEXT.search(reply):
            raise GuardViolation("3", "cited a section after the classifier abstained")
        for group in cfg.MAJOR_GROUPS.values():
            if group != "Nonclassifiable" and group.lower() in reply.lower():
                raise GuardViolation(
                    "3", f"named the hazard group {group!r} after abstaining")

    # Rule 1 - every section cited must have come from a tool this turn.
    for cited in set(SECTION_IN_TEXT.findall(reply)):
        if cited not in returned:
            raise GuardViolation(
                "1", "cited a section that no tool returned this turn")

    # Rule 2 - anything in quotation marks that looks like regulation text must
    # actually be regulation text we returned.
    for quoted in re.findall(r'"([^"]{60,})"', reply):
        probe = quoted[:60].strip()
        if not any(probe in (t or "") for t in corpus_text):
            raise GuardViolation(
                "2", f"quoted text not found in any tool result: {probe[:70]!r}")


# --------------------------------------------------------------------------
# The agent
# --------------------------------------------------------------------------

class AssistantLLM:
    """A language model with the three tools, a prompt, and a guard behind it."""

    def __init__(self, client=None):
        self.client = client or WatsonxClient()
        self.messages = [{"role": "system", "content": system_prompt()}]
        self.fallback = det_agent.IncidentAgent()
        self.trace: list[dict] = []

    def respond(self, user_text: str) -> str:
        text = (user_text or "").strip()

        # Rule 5 is enforced before the model sees the question at all. A
        # compliance question has no correct answer for this system to give, so
        # there is nothing to be gained by asking a model to decline politely.
        if det_agent.IncidentAgent._is_compliance_question(text):
            self.trace.append({"event": "rule_5_precheck", "llm_called": False})
            return self.fallback._refuse_compliance()

        self.messages.append({"role": "user", "content": text})
        tool_results: list[dict] = []

        for _ in range(MAX_TOOL_ROUNDS):
            payload = self.client.chat(self.messages, tool_specs())
            choice = payload["choices"][0]["message"]
            calls = choice.get("tool_calls") or []
            self.messages.append({
                "role": "assistant",
                "content": choice.get("content") or "",
                **({"tool_calls": calls} if calls else {}),
            })
            if not calls:
                reply = (choice.get("content") or "").strip()
                try:
                    _guard(reply, tool_results)
                except GuardViolation as violation:
                    self.trace.append({"event": "guard_blocked", "rule": violation.rule,
                                       "detail": violation.detail})
                    return self._blocked(text, violation)
                self.trace.append({"event": "reply", "guard": "passed"})
                return reply

            for call in calls:
                fn = call["function"]["name"]
                args = call["function"]["arguments"]
                if isinstance(args, str):
                    args = json.loads(args or "{}")
                try:
                    result = assistant_tools.call(fn, **args)
                except Exception as exc:                 # unknown tool, bad args
                    result = {"status": "tool_error", "message": str(exc)[:200]}
                tool_results.append(result)
                self.trace.append({"event": "tool", "name": fn,
                                   "status": result.get("status")})
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": call.get("id", fn),
                    "content": json.dumps(result)[:6000],
                })

        self.trace.append({"event": "tool_round_limit"})
        return self._blocked(text, GuardViolation(
            "loop", f"the model kept calling tools after {MAX_TOOL_ROUNDS} rounds"))

    def _blocked(self, text: str, violation: GuardViolation) -> str:
        """A blocked reply degrades to the deterministic agent, not to an error.

        The user still gets a correct answer. The violation is recorded in the
        trace, which is what TASK-113 exists to collect."""
        safe = self.fallback.respond(text)
        return (safe + "\n\n---\n_The language model's reply was blocked by the "
                f"guard: it contained {violation.public}. This answer came from "
                "the deterministic agent instead. The blocked text is in the "
                "trace, not on screen._")
