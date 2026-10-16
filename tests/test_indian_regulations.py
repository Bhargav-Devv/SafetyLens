import json
import config as cfg
from src import indian_regulations
from src.india_retrieval import IndianRulesIndex


def _payload(sections):
    return {
        "provenance": {
            "marker": indian_regulations.PROVENANCE_MARKER,
            "document": "Model Rules under the Factories Act, 1948",
            "authority": "DGFASLI",
            "source_url": indian_regulations.SOURCE_URL,
            "source_sha256": "0" * 64,
            "rule_count": len(sections),
        },
        "sections": sections,
    }


def test_indian_index_is_separate_and_returns_provenance():
    payload = _payload([
        {"rule": "60", "title": "Hoists and lifts",
         "text": "Authoritative fixture text about lift equipment.",
         "page_start": 40, "page_end": 41},
        {"rule": "68", "title": "Fire Protection",
         "text": "Authoritative fixture text about fire precautions.",
         "page_start": 49, "page_end": 57},
    ])
    result = IndianRulesIndex(payload).search("fire precautions", k=1)[0]
    assert result["rule"] == "68"
    assert result["authority"] == "DGFASLI"
    assert result["source_sha256"] == "0" * 64


def test_unprovenanced_indian_cache_is_refused():
    class UnprovenancedCache:
        def exists(self):
            return True

        def read_text(self, encoding):
            return json.dumps({"sections": []})

    original = cfg.INDIA_RULES_CACHE
    cfg.INDIA_RULES_CACHE = UnprovenancedCache()
    try:
        try:
            indian_regulations.load_model_rules()
        except RuntimeError as exc:
            assert "provenance" in str(exc)
            return
        raise AssertionError("an unprovenanced Indian corpus must be refused")
    finally:
        cfg.INDIA_RULES_CACHE = original


def test_blank_indian_query_returns_nothing():
    payload = _payload([
        {"rule": "1", "title": "Short title", "text": "fixture text",
         "page_start": 6, "page_end": 6},
    ])
    assert IndianRulesIndex(payload).search("   ") == []


def test_rules_on_the_same_page_do_not_include_the_next_rule():
    pages = ["Rule 1. First rule body. Rule 2. Second rule body."]
    body = indian_regulations._slice_rule(pages, (0, 0), (0, pages[0].index("Rule 2")))
    assert body == "Rule 1. First rule body."
    assert "Rule 2" not in body


def test_printed_page_number_is_not_regulation_text():
    assert indian_regulations._strip_page_number("117\n116. Notice by worker") == \
        "116. Notice by worker"
