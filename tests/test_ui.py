"""
The interface, exercised headlessly.

`streamlit run` starting without an exception proves almost nothing - the
branches that matter only execute once a narrative is submitted. Streamlit's
AppTest runs the script in-process and lets the states be asserted, so the
refusal path in particular is checked rather than hoped for.

    python tests/test_ui.py
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

APP = str(ROOT / "app.py")
TIMEOUT = 240

CONVEYOR = ("Employee was cleaning a conveyor belt while it was running when his sleeve "
            "became caught in the rollers and his right arm was pulled in, resulting in "
            "an amputation below the elbow.")
HEAT = "Employee was working outdoors in high temperatures and collapsed from heat exhaustion."
VAGUE = "Employee got hurt at work."


def _run(text: str) -> AppTest:
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    at.text_area[0].set_value(text)
    at.button[0].click().run()
    return at


def _body(at: AppTest) -> str:
    return " ".join(str(getattr(e, "value", "")) for e in at.markdown) + " " + \
           " ".join(str(getattr(e, "value", "")) for e in at.caption)


def test_empty_state_renders_without_a_narrative():
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception
    assert "No incident yet" in _body(at)


def test_result_state_shows_hazard_citation_and_provenance():
    at = _run(CONVEYOR)
    assert not at.exception
    body = _body(at)
    assert "Contact with objects and equipment" in body
    assert "29 CFR 1910." in body
    assert "Quoted from eCFR, not generated." in body
    assert "margin" in body


def test_refusal_state_is_not_an_error_state():
    """The rule this interface exists to respect: declining is a correct
    outcome, so it must not render as a failure."""
    at = _run(VAGUE)
    assert not at.exception
    assert not at.error, "a refusal must not use Streamlit's error styling"
    body = _body(at)
    assert "NOT CLASSIFIED" in body
    assert "correct outcome, not a failure" in body
    assert "29 CFR" not in body, "an abstention must not leak a citation"


def test_known_gap_names_the_authority_and_claims_no_section():
    at = _run(HEAT)
    assert not at.exception
    body = _body(at)
    assert "NO STANDARD EXISTS" in body
    assert "General Duty Clause" in body
    assert "not failing to find one" in body


def test_blended_score_is_never_shown_as_match_quality():
    """ADR-019 - the ranking score is not a measure of fit, so the card shows
    rank and the calibrated lexical score instead."""
    at = _run(CONVEYOR)
    body = _body(at)
    assert "Closest match" in body
    assert "lexical score" in body
    assert "not a measure of how well a section fits" in body


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
