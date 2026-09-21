"""
The the assistant decision flow, executed deterministically.

WHAT THIS IS, PRECISELY. the SafetyLens assistant is a hosted conversational agent: a language
model given the tool definitions in `assistant_tools.py` and the prompt in
`docs/assistant_system_prompt.md`. This module is NOT that. It is the same decision
flow - the branching in `docs/agent_logic.md` - implemented as code, with the
language model removed.

It exists for two reasons, and both matter more than the convenience:

  1. It makes the refusal rules TESTABLE. "the assistant must never convert an abstention
     into an answer" is a claim about behaviour. Behaviour a language model
     produces can only be spot-checked; behaviour this module produces can be
     asserted in a unit test that runs every time. `tests/test_refusals.py`
     does exactly that.

  2. It makes the system RUNNABLE without IBM credentials. Anyone can clone the
     repository and hold a conversation with it today.

What it deliberately does not have is language understanding. It routes on a
regex and composes from templates. A real the assistant handles "the guy on nights got
his hand caught" far better than this does. What it guarantees, and a language
model cannot, is that the branching is exactly what the specification says -
which makes it the reference the hosted agent is checked against, not a
replacement for it.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from src import assistant_tools

# "what does 1910.147 say" - a section reference in a short utterance is a
# lookup; the same reference inside a long narrative is context, not a request.
_SECTION_REQUEST = re.compile(r"\b1910\.\d+")
_SECTION_REQUEST_MAX_CHARS = 140

# Rule 5. These are the words people reach for when what they actually want to
# know is whether they are in trouble - which is not a question this system can
# answer, and the most damaging one it could answer anyway.
#
# This was found by reading a generated transcript, not by reasoning about it.
# Asked "Are we going to be cited for that?", the agent ran the QUESTION through
# the classifier, decided it was a caught-in-machinery incident, and cited
# 1910.219 at it. Every individual rule held; what was missing was the check
# that the input is an incident at all.
_COMPLIANCE_QUESTION = re.compile(
    r"\b(cited?|citation|violat\w*|fined?|penalt\w*|liable|liabilit\w*|"
    r"sued?|lawsuit|prosecut\w*|in trouble|at fault|to blame|negligent)\b",
    re.I,
)

# A narrative describes something that happened. A question does not.
_INCIDENT_SIGNAL = re.compile(
    r"\b(was|were|got|had|fell|struck|caught|cut|burn\w*|crush\w*|amputat\w*|"
    r"injur\w*|hurt|hospitalis\w*|hospitaliz\w*|fractur\w*|collapsed|"
    r"assault\w*|slipped|tripped|pulled|hit)\b",
    re.I,
)
_SHORT_QUESTION_MAX_CHARS = 120

GENERAL_DUTY_NOTE = (
    "That is not the system failing to find a section. It is the system "
    "reporting that none exists."
)


class IncidentAgent:
    """One conversation. Holds the narrative under discussion across turns."""

    def __init__(self) -> None:
        self.narrative: str = ""        # accumulates while detail is gathered
        self.awaiting_detail: bool = False
        self.trace: list[dict] = []     # every tool call, for the transcript

    # -- helpers ------------------------------------------------------------

    def _call(self, name: str, **kwargs) -> dict:
        result = assistant_tools.call(name, **kwargs)
        self.trace.append({"tool": name, "args": kwargs,
                           "status": result.get("status"),
                           "standards_status": result.get("standards_status")})
        return result

    @staticmethod
    def _is_section_request(text: str) -> bool:
        return (len(text) <= _SECTION_REQUEST_MAX_CHARS
                and bool(_SECTION_REQUEST.search(text)))

    @staticmethod
    def _is_compliance_question(text: str) -> bool:
        return bool(_COMPLIANCE_QUESTION.search(text))

    @staticmethod
    def _is_question_not_narrative(text: str) -> bool:
        """A short question with nothing that happened in it is not an incident.

        Running it through the classifier produces a hazard label for a
        sentence that describes no hazard - a confident answer to a question
        nobody asked.
        """
        return (text.rstrip().endswith("?")
                and len(text) <= _SHORT_QUESTION_MAX_CHARS
                and not _INCIDENT_SIGNAL.search(text))

    # -- the flow -----------------------------------------------------------

    def respond(self, user_text: str) -> str:
        text = (user_text or "").strip()
        if not text:
            return "Tell me what happened."

        # Rule 5 comes first. It applies whatever else the message contains,
        # and a compliance question must never reach the classifier.
        if self._is_compliance_question(text):
            return self._refuse_compliance()

        if self._is_section_request(text):
            return self._answer_section(text)

        if self._is_question_not_narrative(text):
            return self._redirect_question()

        # Rule: when detail was requested, it is ADDED to the original
        # narrative. Analysing the detail alone throws away the incident.
        if self.awaiting_detail and self.narrative:
            self.narrative = f"{self.narrative} {text}"
        else:
            self.narrative = text

        return self._answer_incident(self.narrative)

    # -- branch: refusals ---------------------------------------------------

    def _refuse_compliance(self) -> str:
        """No tool is called here. There is nothing to look up."""
        self.trace.append({"tool": None, "args": {}, "status": "refused_rule_5",
                           "standards_status": None})
        return (
            "I can't tell you that, and I'd be doing you harm if I tried.\n\n"
            "Whether an employer gets cited is a judgement an OSHA compliance "
            "officer makes after an inspection, weighing things this system "
            "never sees - what was known beforehand, what controls were in "
            "place, the inspection history. I classify hazards and quote "
            "standards. I don't decide who is at fault.\n\n"
            "What I can do is show you exactly what the relevant standard "
            "requires, so you can read it yourself. Ask me for a section by "
            "number, or describe the incident and I'll find the section that "
            "covers it."
        )

    def _redirect_question(self) -> str:
        self.trace.append({"tool": None, "args": {}, "status": "not_an_incident",
                           "standards_status": None})
        return (
            "That's a question rather than a description of an incident, and I "
            "shouldn't run it through the hazard classifier - it would hand you "
            "a confident label for something that isn't an incident.\n\n"
            "Describe what happened, or give me a section number like 1910.147."
        )

    # -- branch: a section was asked for by number --------------------------

    def _answer_section(self, text: str) -> str:
        section = _SECTION_REQUEST.search(text).group(0)
        r = self._call("explain_standard", section=section)

        if r["status"] == "invalid_section":
            return r["message"]

        if r["status"] == "not_found":
            near = ", ".join(r["suggestions_not_the_answer"][:5])
            return (f"{r['message']}\n\nI will not hand you a different section "
                    f"as though it were that one. Sections I do hold nearby: "
                    f"{near}.")

        body = r["text"]
        opening = body[:700] + ("..." if len(body) > 700 else "")
        return (f"**{r['citation']} - {r['title']}**\n"
                f"({r['characters']:,} characters, {r['source']})\n\n"
                f"It opens:\n\n\"{opening}\"\n\n"
                "Ask for a specific paragraph and I will quote that part.")

    # -- branch: an incident was described ----------------------------------

    def _answer_incident(self, narrative: str) -> str:
        r = self._call("analyse_incident", narrative=narrative)

        if r["status"] == "insufficient_input":
            self.awaiting_detail = True
            return r["message"]

        if r["status"] == "abstained":
            self.awaiting_detail = True
            asks = "; ".join(r["ask_for"])
            return (
                f"I cannot identify the hazard reliably from that - the margin "
                f"between the top two categories was {r['margin']}, below the "
                f"{r['margin_floor']} floor.\n\n"
                f"Tell me: {asks}.\n\n"
                "I would rather ask than guess. A confident wrong answer about "
                "a safety hazard is the thing worth avoiding here."
            )

        self.awaiting_detail = False
        out = [
            f"That reads as **{r['hazard_group']}** - specifically "
            f"*{r['specific_event']}* (margin {r['hazard_group_margin']}).",
            "",
        ]
        out += self._standards_section(r)
        out += self._pattern_section(r)
        return "\n".join(out)

    # -- composing the regulatory half --------------------------------------

    def _standards_section(self, r: dict) -> list[str]:
        st = r["standards_status"]

        if st == "no_specific_standard":
            return [
                f"**No OSHA standard applies - none exists for this hazard.**",
                "",
                f"The authority is the **{r['authority']}**.",
                "",
                r["standards_message"],
                "",
                GENERAL_DUTY_NOTE,
                "",
            ]

        if st == "no_match":
            return [
                "**No section of 29 CFR 1910 matched above the retrieval floor.**",
                "",
                "I am not going to offer you the least-bad section instead. If "
                "you have a section in mind, give me the number and I will quote it.",
                "",
            ]

        if st == "not_attempted":
            return [
                "The hazard group came back as Nonclassifiable, so there was "
                "nothing to route a regulation search on. Classification stands; "
                "retrieval declines.",
                "",
            ]

        top, *related = r["standards"]
        lines = [
            f"**{top['citation']} - {top['title']}** is the closest match "
            f"(ranked 1 of {len(r['standards'])}).",
            "",
            f"\"{top['quote']}\"",
            "",
            f"_{top['source']}._",
            "",
        ]
        if related:
            names = "; ".join(
                f"{s['citation']} {s['title'].split('§')[-1].strip()[:44]}"
                for s in related
            )
            lines += [
                f"Ranked below it, in the same hazard family: {names}. "
                "Related, not additional requirements.",
                "",
                "_Ranking is relative within this result. It is not a measure of "
                "how well the section fits, and it is not comparable to any "
                "other incident's scores._",
                "",
            ]
        return lines

    # -- composing the pattern half -----------------------------------------

    def _pattern_section(self, r: dict) -> list[str]:
        sims = r.get("similar_incidents") or []
        if not sims:
            return []
        lines = [f"**This has happened before.** The {len(sims)} closest reports "
                 "in the corpus:", ""]
        lines += [f"- {s['text'].rstrip()}  _(similarity {s['similarity']})_"
                  for s in sims]
        lines += ["", "What they share is the pattern worth acting on - not the "
                  "injury, the circumstance that produced it.", "",
                  "_Decision support only. What a standard requires is not a "
                  "finding that anyone violated it._"]
        return lines
