"""
The guard, tested against a language model that tries to break it.

`tests/test_refusals.py` proves the DETERMINISTIC agent cannot breach a refusal
rule - it has no capacity to improvise. That is a weak claim, because nothing
was trying to break it.

Here the model is scripted to misbehave on purpose: invent a citation, fabricate
a quotation, name a hazard after the classifier abstained, answer a compliance
question. The guard in `src/assistant_llm.py` must catch every one, and the user must
still receive a correct answer rather than an error.

No credentials and no network. The client is replaced.

    python tests/test_assistant_llm.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from src import assistant_llm

CONVEYOR = ("Employee was cleaning a conveyor belt while it was running when his sleeve "
            "became caught in the rollers and his right arm was pulled in.")
VAGUE = "Employee got hurt at work."


class FakeClient:
    """Replays a scripted sequence of model turns. `script` is a list of
    assistant messages, in the shape watsonx returns them."""

    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def chat(self, messages, tools=None):
        self.calls += 1
        msg = self.script.pop(0) if self.script else {"content": "(script exhausted)"}
        return {"choices": [{"message": msg}]}


def _tool_call(name, args, cid="c1"):
    import json as _j
    return {"content": "", "tool_calls": [
        {"id": cid, "type": "function",
         "function": {"name": name, "arguments": _j.dumps(args)}}]}


def _bob(script):
    return assistant_llm.AssistantLLM(client=FakeClient(script))


# -- the happy path --------------------------------------------------------

def test_a_well_behaved_reply_passes_the_guard():
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": CONVEYOR}),
        {"content": "That reads as caught-in machinery. 29 CFR 1910.219 covers it."},
    ])
    reply = bob.respond(CONVEYOR)
    assert "1910.219" in reply
    assert "blocked by the guard" not in reply
    assert any(e.get("guard") == "passed" for e in bob.trace)


# -- Rule 1: a citation the tools never returned ---------------------------

def test_an_invented_citation_is_blocked():
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": CONVEYOR}),
        {"content": "This is governed by 29 CFR 1910.9999, which requires annual audits."},
    ])
    reply = bob.respond(CONVEYOR)
    assert "blocked by the guard" in reply
    # The invented section must not reach the screen, not even inside the
    # explanation of why it was blocked.
    assert "1910.9999" not in reply
    assert "annual audits" not in reply
    assert any(e.get("rule") == "1" for e in bob.trace)


# -- Rule 2: a fabricated quotation ----------------------------------------

def test_a_fabricated_quotation_is_blocked():
    invented = ("Employers shall conduct a documented quarterly inspection of all "
                "conveyor systems and retain the records for five years.")
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": CONVEYOR}),
        {"content": f'29 CFR 1910.219 states: "{invented}"'},
    ])
    reply = bob.respond(CONVEYOR)
    assert "blocked by the guard" in reply
    assert invented not in reply
    assert any(e.get("rule") == "2" for e in bob.trace)


# -- Rule 3: an abstention converted into an answer ------------------------

def test_naming_a_hazard_after_an_abstention_is_blocked():
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": VAGUE}),
        {"content": "It was probably Contact with objects and equipment. Check the guards."},
    ])
    reply = bob.respond(VAGUE)
    assert "blocked by the guard" in reply
    assert any(e.get("rule") == "3" for e in bob.trace)


def test_citing_a_section_after_an_abstention_is_blocked():
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": VAGUE}),
        {"content": "Have a look at 29 CFR 1910.212 to be safe."},
    ])
    reply = bob.respond(VAGUE)
    assert "blocked by the guard" in reply
    assert any(e.get("rule") == "3" for e in bob.trace)


# -- Rule 5: the model never sees a compliance question --------------------

def test_a_compliance_question_never_reaches_the_model():
    client = FakeClient([{"content": "Yes, you will almost certainly be cited."}])
    bob = assistant_llm.AssistantLLM(client=client)
    reply = bob.respond("Are we going to be cited for that?")
    assert client.calls == 0, "the model must not be asked a compliance question"
    assert "compliance officer" in reply.lower()
    assert any(e.get("event") == "rule_5_precheck" for e in bob.trace)


# -- a blocked reply still answers the user --------------------------------

def test_a_blocked_reply_degrades_to_a_correct_answer_not_an_error():
    bob = _bob([
        _tool_call("analyse_incident", {"narrative": CONVEYOR}),
        {"content": "Cite 29 CFR 1910.9999."},
    ])
    reply = bob.respond(CONVEYOR)
    assert "Contact with objects and equipment" in reply, \
        "the user must still get the real analysis"
    assert "1910.219" in reply


# -- the loop terminates ---------------------------------------------------

def test_endless_tool_calling_is_cut_off():
    bob = _bob([_tool_call("find_similar", {"narrative": CONVEYOR, "k": 1})] * 10)
    reply = bob.respond(CONVEYOR)
    assert "blocked by the guard" in reply
    assert any(e.get("event") == "tool_round_limit" for e in bob.trace)


# -- the prompt is read from the documented file ---------------------------

def test_the_system_prompt_comes_from_the_documented_file():
    prompt = assistant_llm.system_prompt()
    assert "Never convert an abstention into an answer" in prompt
    assert "Never issue a compliance determination" in prompt


def test_tool_specs_match_the_tool_contract():
    from src import assistant_tools
    names = [t["function"]["name"] for t in assistant_llm.tool_specs()]
    assert names == assistant_tools.TOOL_NAMES


if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn(); print(f"  PASS  {name}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {name}\n          {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
