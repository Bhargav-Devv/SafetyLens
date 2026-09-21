"""
The refusal rules, as executable assertions.

Every rule in `docs/agent_logic.md` is a claim about behaviour. A claim nobody
checks is a claim that quietly stops being true - which is exactly what happened
to "heat cases report no match": the documents said it for days while the code
returned 1910.138 Hand protection.

So each rule gets a test. These run in seconds and they run every time.

    python tests/test_refusals.py        (no pytest needed)
    pytest tests/ -v                     (if you have it)
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).parent.parent))

import config as cfg
from src import assistant_tools
from src.agent import IncidentAgent
from src.service import get_service

SVC = get_service()

VAGUE = "Employee got hurt at work."
CONVEYOR = ("Employee was cleaning a conveyor belt while it was running when his "
            "sleeve became caught in the rollers and his right arm was pulled in, "
            "resulting in an amputation below the elbow.")
HEAT = ("Employee was working outdoors in high temperatures and collapsed from "
        "heat exhaustion.")
VIOLENCE = ("An employee was assaulted by a patient in the psychiatric ward and "
            "sustained a broken nose.")
LIFTING = ("An employee injured his lower back while lifting a 70 pound box of parts "
           "from the floor onto a pallet and was hospitalised for a herniated disc.")

CITATION_MARKERS = ("29 CFR", "1910.")


# -- TASK-104 : abstention must never become an answer ---------------------

def test_abstention_returns_no_hazard_and_no_standard():
    r = SVC.analyse_incident(VAGUE)
    assert r["status"] == "abstained", r["status"]
    assert "hazard_group" not in r
    assert "standards" not in r
    assert r["margin"] < cfg.MARGIN_FLOOR


def test_agent_reply_to_abstention_cites_nothing():
    reply = IncidentAgent().respond(VAGUE)
    for marker in CITATION_MARKERS:
        assert marker not in reply, f"abstention reply leaked a citation: {marker}"
    assert "?" in reply or "Tell me" in reply, "abstention must ask for detail"


def test_detail_is_added_to_the_original_narrative():
    """The follow-up must be analysed WITH the incident, not instead of it."""
    a = IncidentAgent()
    a.respond("Someone got hurt yesterday.")
    a.respond("He was cleaning a running conveyor and his hand went into the rollers.")
    assert "hurt yesterday" in a.narrative
    assert "rollers" in a.narrative


# -- TASK-105 : silence must be reported as silence ------------------------

def test_known_gap_reports_no_standard_and_names_the_authority():
    for narrative in (HEAT, VIOLENCE, LIFTING):
        r = SVC.analyse_incident(narrative)
        assert r["status"] == "classified"
        assert r["standards_status"] == "no_specific_standard", narrative[:40]
        assert r["standards"] == [], "a known gap must return zero sections"
        assert "General Duty Clause" in r["authority"]


def test_agent_states_the_gap_without_offering_a_substitute():
    reply = IncidentAgent().respond(HEAT)
    assert "General Duty Clause" in reply
    assert "no osha standard applies" in reply.lower()   # needle must be lowered too
    # It may mention the hazard, but it must not cite a section as applicable.
    # Tracks the agent's actual wording - a stale needle here would pass forever.
    assert "closest match" not in reply
    assert "29 CFR 1910." not in reply


def test_missing_section_never_returns_a_different_one():
    r = SVC.explain_standard("1910.99999")
    assert r["status"] == "not_found"
    assert "text" not in r, "a not-found lookup must not carry section text"
    reply = IncidentAgent().respond("what does 1910.99999 say")
    assert "will not hand you a different section" in reply


# -- TASK-106 : no regulatory claim without a citation ---------------------

def test_every_returned_standard_carries_a_citation():
    r = SVC.analyse_incident(CONVEYOR)
    assert r["standards_status"] == "matched"
    for s in r["standards"]:
        assert s["citation"].startswith("29 CFR 1910.")
        assert s["section"] and s["title"] and s["quote"]
        assert "verbatim, not generated" in s["source"]


def test_blended_scores_are_not_presented_as_match_quality():
    """ADR-019. The ranking score is a blend whose scale is not calibrated, so
    the caller must receive the lexical score and a warning alongside it."""
    for s in SVC.analyse_incident(CONVEYOR)["standards"]:
        assert "lexical_score" in s
        assert "ADR-019" in s["score_note"]
    reply = IncidentAgent().respond(CONVEYOR)
    assert "closest match" in reply, "must not claim a section 'applies' on a blended score"
    if "Ranked below it" in reply:
        assert "not a measure of how well the section fits" in reply


def test_no_returned_score_is_below_the_floor():
    for narrative in (CONVEYOR, HEAT, VIOLENCE, LIFTING):
        for s in SVC.analyse_incident(narrative).get("standards", []):
            assert s["match_score"] >= cfg.RETRIEVAL_FLOOR


def test_quotes_are_genuine_substrings_of_the_corpus():
    """The strongest form of 'no generated regulation': every character Bob
    quotes must already exist in the cached eCFR text."""
    corpus = {s["section"]: s["text"] for s in SVC.lens.standards}
    for narrative in (CONVEYOR, "A forklift tipped over and crushed the operator."):
        for s in SVC.analyse_incident(narrative).get("standards", []):
            quote = s["quote"].rstrip(".").rstrip("…").rstrip(".")
            body = quote[:200]
            assert body in corpus[s["section"]], (
                f"{s['citation']} quote is not present in the source text")


def test_explain_standard_returns_the_corpus_text_unmodified():
    corpus = {s["section"]: s["text"] for s in SVC.lens.standards}
    r = SVC.explain_standard("29 CFR 1910.219(a)")
    assert r["status"] == "found" and r["section"] == "1910.219"
    assert r["text"] == corpus["1910.219"]


# -- Rule 5 : never issue a compliance determination -----------------------

COMPLIANCE_QUESTIONS = [
    "Are we going to be cited for that?",
    "Will OSHA fine us?",
    "Is the company liable here?",
    "Was that a violation?",
    "Am I in trouble?",
]


def test_compliance_questions_are_refused_without_classifying():
    for q in COMPLIANCE_QUESTIONS:
        a = IncidentAgent()
        reply = a.respond(q)
        assert "compliance officer" in reply.lower(), q
        assert "That reads as" not in reply, f"{q!r} was classified as an incident"
        assert a.trace and a.trace[-1]["status"] == "refused_rule_5", q
        assert all(t["tool"] is None for t in a.trace), \
            f"{q!r} called a tool; nothing should be looked up"


def test_a_bare_question_is_not_analysed_as_an_incident():
    a = IncidentAgent()
    reply = a.respond("What should I do next?")
    assert "isn't an incident" in reply or "question rather than" in reply
    assert not any(t["tool"] for t in a.trace)


def test_a_real_narrative_is_still_analysed_normally():
    """The guards must not swallow genuine incidents - including ones that use
    the word 'violation' incidentally, or end in a question mark."""
    a = IncidentAgent()
    reply = a.respond(CONVEYOR)
    assert "Contact with objects and equipment" in reply
    assert a.trace[-1]["tool"] == "analyse_incident"


# -- corpus integrity ------------------------------------------------------

def test_add_part_parses_only_the_requested_part():
    """Part 1926 cannot be fetched here (network policy), so the parser is
    exercised against eCFR-shaped XML. The guard that matters: it must not
    scoop up sections belonging to another Part.

    The cache goes to a temp directory, never to data/. A test that writes into
    the project's data folder can corrupt a real corpus, and this one failed the
    moment file deletion was restricted because its cleanup could not run."""
    import tempfile
    from pathlib import Path as _P
    from src import regulations

    body = "This section covers fall protection in construction. " * 20
    xml = (f'<ECFR><DIV5 N="1926">'
           f'<DIV8 N="1926.501"><HEAD>1926.501 Duty to have fall protection.</HEAD>'
           f'<P>{body}</P></DIV8>'
           f'<DIV8 N="1910.999"><HEAD>a section from another Part</HEAD>'
           f'<P>{body}</P></DIV8></DIV5></ECFR>')
    parsed = regulations._parse(xml.encode(), "1926")
    assert {x["section"] for x in parsed} == {"1926.501"}

    with tempfile.TemporaryDirectory() as tmpdir:
        original = cfg.DATA_DIR
        cfg.DATA_DIR = _P(tmpdir)
        try:
            xml_path = _P(tmpdir) / "part1926.xml"
            xml_path.write_text(xml, encoding="utf-8")
            regulations.add_part("1926", xml_path)
            assert (_P(tmpdir) / cfg.EXTRA_PART_CACHE.format(part="1926")).exists()
        finally:
            cfg.DATA_DIR = original


def test_add_part_refuses_to_cache_an_empty_corpus():
    """Same rule as `fetch`: real text or nothing. An XML that yields no
    sections must raise rather than cache silence."""
    import tempfile
    from pathlib import Path as _P
    from src import regulations

    with tempfile.TemporaryDirectory() as tmpdir:
        original = cfg.DATA_DIR
        cfg.DATA_DIR = _P(tmpdir)
        try:
            xml_path = _P(tmpdir) / "empty.xml"
            xml_path.write_text('<ECFR><DIV5 N="1926"/></ECFR>', encoding="utf-8")
            try:
                regulations.add_part("1926", xml_path)
            except RuntimeError:
                return
            raise AssertionError("an empty parse must raise, not cache an empty corpus")
        finally:
            cfg.DATA_DIR = original


def test_a_cache_without_provenance_is_refused():
    """THE REGRESSION TEST FOR A REAL INCIDENT.

    A unit test wrote a synthetic fixture into data/ as a Part 1926 cache. It
    was merged into the index and served to a user as 29 CFR 1926.501, quoted
    under a heading reading "quoted from eCFR, not generated". A hand-written or
    accidentally-written cache must now be refused, loudly."""
    import tempfile, json as _json
    from pathlib import Path as _P
    from src import regulations

    with tempfile.TemporaryDirectory() as tmpdir:
        original = cfg.DATA_DIR
        cfg.DATA_DIR = _P(tmpdir)
        try:
            fake = _P(tmpdir) / cfg.EXTRA_PART_CACHE.format(part="1926")
            fake.write_text(_json.dumps(
                [{"section": "1926.501", "title": "invented", "text": "x" * 500}]),
                encoding="utf-8")
            try:
                regulations._extra_parts()
            except RuntimeError as exc:
                assert "provenance" in str(exc)
                return
            raise AssertionError("a cache with no provenance must be refused")
        finally:
            cfg.DATA_DIR = original


def test_add_part_writes_provenance_that_survives_a_reload():
    import tempfile
    from pathlib import Path as _P
    from src import regulations

    body = "This section covers fall protection in construction. " * 20
    xml = (f'<ECFR><DIV5 N="1926"><DIV8 N="1926.501">'
           f'<HEAD>1926.501 Duty to have fall protection.</HEAD>'
           f'<P>{body}</P></DIV8></DIV5></ECFR>')
    with tempfile.TemporaryDirectory() as tmpdir:
        original = cfg.DATA_DIR
        cfg.DATA_DIR = _P(tmpdir)
        try:
            xml_path = _P(tmpdir) / "p.xml"
            xml_path.write_text(xml, encoding="utf-8")
            regulations.add_part("1926", xml_path)
            loaded = regulations._extra_parts()
            assert [s["section"] for s in loaded] == ["1926.501"]
        finally:
            cfg.DATA_DIR = original


def test_no_section_in_the_live_index_is_outside_part_1910():
    """The corpus this build actually holds is 29 CFR 1910 and nothing else.
    Anything else appearing is either an un-provenanced cache or a mistake."""
    stray = [s["section"] for s in SVC.lens.standards
             if not s["section"].startswith("1910.")]
    assert not stray, f"unexpected sections in the index: {stray}"


def test_administrative_sections_are_absent_from_the_index():
    sections = {s["section"] for s in SVC.lens.standards}
    assert not (sections & cfg.ADMINISTRATIVE_SECTIONS)


# -- configuration integrity ----------------------------------------------

def test_known_gap_labels_actually_exist():
    groups = set(SVC.lens.clf_major.classes_)
    events = set(SVC.lens.clf_fine.classes_)
    for g in cfg.NO_SPECIFIC_STANDARD_GROUPS:
        assert g in groups, f"dead rule: {g!r} is not a hazard group"
    for e in cfg.NO_SPECIFIC_STANDARD_EVENTS:
        assert e in events, f"dead rule: {e!r} is not a fine-grained event"


def test_unknown_tool_raises_rather_than_returning_nothing():
    try:
        assistant_tools.call("delete_the_evidence", narrative="x")
    except ValueError:
        return
    raise AssertionError("an unknown tool must raise, not return a falsy result")


# -- runner ----------------------------------------------------------------

if __name__ == "__main__":
    tests = [(n, f) for n, f in sorted(globals().items())
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:
            failed += 1
            print(f"  FAIL  {name}\n          {type(exc).__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
