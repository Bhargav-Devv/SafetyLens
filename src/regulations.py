"""
The OSHA standards corpus - fetched from eCFR, never written.

This module has one hard rule: if the real text cannot be retrieved, it fails.
It does NOT fall back to generated or paraphrased regulation text.

A model that invents a safety regulation could get someone killed. The refusal
is the design, not a missing feature.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg

SECTION_RE = re.compile(r"^1910\.\d+")

# Every extra-Part cache must carry this. See _extra_parts for why.
PROVENANCE_MARKER = "safetylens/ecfr-parse/v1"


def _section_re(part: str) -> "re.Pattern[str]":
    return re.compile(rf"^{re.escape(part)}\.\d+")


def _parse(xml_bytes: bytes, part: str = "1910") -> list[dict]:
    """Parse eCFR XML into sections. Works for any Part, not just 1910."""
    root = ET.fromstring(xml_bytes)
    pattern = _section_re(part)
    found = []
    for el in root.iter():
        number = el.attrib.get("N", "")
        if not pattern.match(number):
            continue
        head_el = el.find("HEAD")
        title = "".join(head_el.itertext()).strip() if head_el is not None else ""
        body = " ".join("".join(p.itertext()) for p in el.iter("P"))
        body = re.sub(r"\s+", " ", body).strip()
        if len(body) >= cfg.MIN_STANDARD_CHARS:
            found.append({"section": number, "title": title, "text": body})
    return found


def _drop_administrative(standards: list[dict]) -> list[dict]:
    """Remove sections that state no requirement about any hazard.

    Purpose and scope, Definitions, Effective dates, Incorporation by reference,
    Recordkeeping. `retrieval_labelling_guide.md` §5 already says these can never
    be a correct answer; leaving them in the index only created ways to be wrong,
    and 1910.21 "Scope and definitions" was in fact returned for a real incident.
    """
    keep = [s for s in standards if s["section"] not in cfg.ADMINISTRATIVE_SECTIONS]
    dropped = len(standards) - len(keep)
    if dropped:
        print(f"standards: dropped {dropped} administrative sections")
    return keep


def _dedupe(sections: list[dict]) -> list[dict]:
    """Keep the longest body per section number."""
    best: dict[str, dict] = {}
    for sec in sections:
        if sec["section"] not in best or len(sec["text"]) > len(best[sec["section"]]["text"]):
            best[sec["section"]] = sec
    return list(best.values())


def add_part(part: str, path: Path) -> list[dict]:
    """Parse a locally downloaded eCFR XML for one Part and cache it.

    This exists because `ecfr.gov` is denied by network policy in both
    workspaces. The file can be downloaded in a browser; the parser is the same
    one that built the 1910 corpus, and the same refusal applies - if nothing
    parses out, it raises rather than caching an empty or invented corpus.
    """
    raw = Path(path).read_bytes()
    sections = _dedupe(_parse(raw, part))
    if not sections:
        raise RuntimeError(
            f"No sections of Part {part} parsed out of {path}.\n"
            "Check that this is the eCFR XML for that Part. An empty corpus is "
            "not cached: retrieval must come from the authoritative source."
        )
    cache = cfg.DATA_DIR / cfg.EXTRA_PART_CACHE.format(part=part)
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "provenance": {
            "marker": PROVENANCE_MARKER,
            "part": part,
            "source_file": Path(path).name,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "section_count": len(sections),
            "parsed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "sections": sections,
    }
    cache.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"Part {part}: {len(sections)} sections parsed and cached to {cache.name}")
    return sections


def _extra_parts() -> list[dict]:
    """Additional Parts, loaded only if they carry provenance.

    THIS GUARD EXISTS BECAUSE THE FAILURE HAPPENED. A unit test wrote a
    synthetic fixture - the sentence "This section covers fall protection in
    construction." repeated twenty times - into `data/` as a Part 1926 cache. It
    was merged into the index and **served to a user as 29 CFR 1926.501, quoted
    under a heading that reads "quoted from eCFR, not generated"**. Fabricated
    regulation text, presented as authoritative, by the system whose first
    architectural rule forbids exactly that.

    The hole was that a cache file on disk was trusted absolutely. Now a cache
    must carry a provenance block written by `add_part`: the source filename,
    its SHA-256, the section count and the parse time. A file without one is
    refused loudly rather than silently trusted, and the refusal names the file
    so it can be deleted.

    This does not make a cache tamper-proof - anyone can write a provenance
    block. It makes an ACCIDENT impossible, and the accident is what happened.
    """
    extra: list[dict] = []
    for part in cfg.EXTRA_PARTS:
        cache = cfg.DATA_DIR / cfg.EXTRA_PART_CACHE.format(part=part)
        if not cache.exists():
            continue
        payload = json.loads(cache.read_text(encoding="utf-8"))
        if (not isinstance(payload, dict)
                or payload.get("provenance", {}).get("marker") != PROVENANCE_MARKER):
            raise RuntimeError(
                f"{cache} has no provenance block and will not be loaded.\n"
                "Regulation text enters this system only through add_part, which "
                "records the source file and its checksum. Delete this file and "
                f"re-run:  python main.py add-part {part} <path-to-ecfr-xml>"
            )
        sections = payload["sections"]
        prov = payload["provenance"]
        extra.extend(sections)
        print(f"standards: +{len(sections)} sections from Part {part} "
              f"(source {prov['source_file']}, sha {prov['source_sha256'][:12]})")
    return extra


def fetch(force: bool = False) -> list[dict]:
    """29 CFR Part 1910, cached to data/standards.json after the first call."""
    if cfg.STANDARDS_CACHE.exists() and not force:
        standards = json.loads(cfg.STANDARDS_CACHE.read_text(encoding="utf-8"))
        standards = _drop_administrative(standards + _extra_parts())
        print(f"standards: {len(standards)} sections (cached)")
        return standards

    standards: list[dict] = []
    for date in cfg.ECFR_DATES:
        try:
            print(f"fetching eCFR {date} ...")
            resp = requests.get(cfg.ECFR_URL.format(date=date), timeout=300)
            resp.raise_for_status()
            standards = _parse(resp.content)
            if standards:
                break
        except Exception as exc:
            print(f"  failed: {str(exc)[:110]}")

    if not standards:
        raise RuntimeError(
            "eCFR unreachable and no cache present.\n"
            "The retrieval corpus must come from the authoritative source. "
            "Generated regulation text is not an acceptable substitute."
        )

    standards = _dedupe(standards)

    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg.STANDARDS_CACHE.write_text(json.dumps(standards, indent=1), encoding="utf-8")
    print(f"standards: {len(standards)} sections fetched and cached")
    return standards
