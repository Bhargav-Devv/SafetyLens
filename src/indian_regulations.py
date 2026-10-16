"""Authoritative DGFASLI Model Factories Rules corpus.

This corpus is deliberately separate from the OSHA/eCFR index.  The source is
the Government of India PDF and every generated cache records its SHA-256.
Extracted text is never reconstructed or completed by a language model.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

import config as cfg

PROVENANCE_MARKER = "safetylens/dgfasli-pdf-parse/v1"
SOURCE_URL = (
    "https://dgfasli.gov.in/public/Admin/Cms/AllPdf/"
    "Model_Factories_Rules_as_on_15_12_2020.pdf"
)
EXPECTED_RULE_COUNT = 154

_TOC_ENTRY = re.compile(
    r"(?<!\w)(\d{1,3}(?:[A-Z]|\s+[A-Z])?)\.\s+(.*?)\s+(\d{1,3})"
    r"(?=\s+(?:\d{1,3}(?:[A-Z]|\s+[A-Z])?)\.\s+|\s+Chapter\s+|\s+Forms\s+|$)"
)


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _strip_page_number(value: str) -> str:
    """Remove the PDF's printed page number, not any rule content."""
    return re.sub(r"^\s*\d+\s*(?:\r?\n)", "", value, count=1)


def _toc_entries(page_texts: list[str]) -> list[dict]:
    entries: list[dict] = []
    for page in page_texts[1:5]:
        text = " ".join(page.split())
        text = re.sub(r"^\d+\s+", "", text).replace("Rule Subject Page No.", "")
        for number, title, page_number in _TOC_ENTRY.findall(text):
            entries.append({
                "rule": re.sub(r"\s+", "", number),
                "title": " ".join(title.split()),
                "declared_page": int(page_number),
            })
    return entries


def _find_heading(page_texts: list[str], entry: dict) -> tuple[int, int, float]:
    number = re.fullmatch(r"(\d+)([A-Z]?)", entry["rule"])
    assert number is not None
    number_pattern = re.escape(number.group(1))
    if number.group(2):
        number_pattern += r"\s*" + re.escape(number.group(2))
    heading = re.compile(
        rf"(?i)(?:^|\s)(?:rule\s+)?{number_pattern}\s*[.:]"
    )
    expected = _normalise(entry["title"])
    word_count = len(expected.split())
    candidates: list[tuple[float, int, int]] = []
    first = max(5, entry["declared_page"] - 2)
    last = min(len(page_texts), entry["declared_page"] + 3)
    for page_index in range(first, last):
        offset = 0
        for line in page_texts[page_index].splitlines(keepends=True):
            match = heading.search(line)
            if match:
                tail = _normalise(line[match.end():])
                observed = " ".join(tail.split()[:word_count])
                score = SequenceMatcher(None, expected, observed).ratio()
                candidates.append((score, page_index, offset + match.start()))
            offset += len(line)
    if not candidates:
        raise RuntimeError(f"Rule {entry['rule']} heading was not found near page "
                           f"{entry['declared_page']}")
    score, page_index, offset = max(candidates)
    # Most headings score above 0.84. Rule 96 contains broken embedded glyphs
    # in the authoritative PDF ("Cr�ches"), so a lower bounded fuzzy match is
    # required. The rule number and declared-page window remain exact guards.
    if score < 0.40:
        raise RuntimeError(f"Rule {entry['rule']} heading did not match its contents title")
    return page_index, offset, score


def _slice_rule(page_texts: list[str], start: tuple[int, int],
                end: tuple[int, int]) -> str:
    start_page, start_offset = start
    end_page, end_offset = end
    if start_page == end_page:
        chunks = [page_texts[start_page][start_offset:end_offset]]
    else:
        chunks = [page_texts[start_page][start_offset:]]
        chunks.extend(page_texts[start_page + 1:end_page])
        if end_page < len(page_texts):
            chunks.append(page_texts[end_page][:end_offset])
    return re.sub(r"\s+", " ", " ".join(chunks)).strip()


def parse_pages(page_texts: list[str]) -> list[dict]:
    """Parse top-level rules from text extracted from the authoritative PDF."""
    if len(page_texts) < 215:
        raise RuntimeError("The DGFASLI PDF is incomplete (fewer than 215 pages)")
    entries = _toc_entries(page_texts)
    if len(entries) != EXPECTED_RULE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_RULE_COUNT} rules in the contents; found {len(entries)}"
        )

    starts: list[tuple[int, int]] = []
    for entry in entries:
        page_index, offset, _ = _find_heading(page_texts, entry)
        starts.append((page_index, offset))
    if starts != sorted(starts) or len(set(starts)) != len(starts):
        raise RuntimeError("Rule headings are not unique and ordered; refusing to cache")

    sections: list[dict] = []
    for index, entry in enumerate(entries):
        start_page, start_offset = starts[index]
        if index + 1 < len(starts):
            end_page, end_offset = starts[index + 1]
        else:
            end_page = start_page
            end_offset = len(page_texts[start_page])  # Forms start on the next PDF page.
        body = _slice_rule(page_texts, starts[index], (end_page, end_offset))
        intentionally_blank = set(_normalise(entry["title"]).split()) == {"x"}
        if len(body) < 20 and not intentionally_blank:
            raise RuntimeError(f"Rule {entry['rule']} parsed as empty")
        sections.append({
            "rule": entry["rule"],
            "title": entry["title"],
            "text": body,
            "page_start": start_page + 1,
            "page_end": (start_page + 1 if start_page == end_page
                         else end_page + (1 if end_offset else 0)),
        })
    return sections


def add_model_rules(path: Path) -> list[dict]:
    """Extract and cache the official DGFASLI PDF with source provenance."""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError(
            "TASK-212 requires pypdf. Install requirements-india.txt first."
        ) from exc

    raw = Path(path).read_bytes()
    reader = PdfReader(path)
    page_texts = [_strip_page_number(page.extract_text() or "") for page in reader.pages]
    sections = parse_pages(page_texts)
    payload = {
        "provenance": {
            "marker": PROVENANCE_MARKER,
            "jurisdiction": "India",
            "authority": "Directorate General Factory Advice Service and Labour Institutes",
            "document": "Model Rules under the Factories Act, 1948",
            "corrected_through": "2020-12-15",
            "source_url": SOURCE_URL,
            "source_file": Path(path).name,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "page_count": len(page_texts),
            "rule_count": len(sections),
            "parsed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "extraction_note": "Text extracted from the authoritative PDF; no generated text.",
        },
        "sections": sections,
    }
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg.INDIA_RULES_CACHE.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"DGFASLI Model Factories Rules: {len(sections)} rules cached to "
          f"{cfg.INDIA_RULES_CACHE.name}")
    return sections


def load_model_rules() -> dict:
    if not cfg.INDIA_RULES_CACHE.exists():
        raise RuntimeError("Indian rules corpus is absent. Run `python main.py add-indian-rules PDF`.")
    payload = json.loads(cfg.INDIA_RULES_CACHE.read_text(encoding="utf-8"))
    provenance = payload.get("provenance", {}) if isinstance(payload, dict) else {}
    if provenance.get("marker") != PROVENANCE_MARKER:
        raise RuntimeError("Indian rules cache has no valid provenance and will not be loaded")
    sections = payload.get("sections", [])
    if provenance.get("rule_count") != len(sections) or len(sections) != EXPECTED_RULE_COUNT:
        raise RuntimeError("Indian rules cache is incomplete and will not be loaded")
    return payload
