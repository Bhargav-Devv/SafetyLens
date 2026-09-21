"""
The service layer - SafetyLens as three callable tools.

`pipeline.SafetyLens` is the engine. It is expensive to construct: two
serialised classifiers, a 170-section regulation corpus and a TF-IDF index over
~90,000 past narratives. Building that per request would make the agent
unusable, so this module builds it once and holds it.

Everything here returns a plain JSON-serialisable dict. Nothing here decides
anything - the decisions were already made in `pipeline.py`, and this layer's
only job is to carry them outward without softening them.

That is the point of the `status` fields. An agent asked to read prose will
eventually narrate around a refusal to be helpful. An agent handed
`status == "abstained"` cannot. The refusal is machine-readable on purpose.
"""
from __future__ import annotations

import contextlib
import io
import re
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from src import data, pipeline

# "29 CFR 1910.219(a)(2)" / "1910.219" / "§1910.219"  ->  "1910.219"
_SECTION_RE = re.compile(r"(1910\.\d+)")

MIN_INPUT_CHARS = 10
MAX_SIMILAR = 10


class SafetyLensService:
    """Load-once wrapper around the pipeline. Thread-safe warmup."""

    _instance: "SafetyLensService | None" = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.lens: pipeline.SafetyLens | None = None
        self._by_section: dict[str, dict] = {}

    # -- lifecycle ----------------------------------------------------------

    @classmethod
    def instance(cls) -> "SafetyLensService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def warm(self, quiet: bool = True) -> "SafetyLensService":
        """Build the engine. Idempotent. Call before serving traffic."""
        if self.lens is not None:
            return self
        with self._lock:
            if self.lens is not None:
                return self
            sink = io.StringIO()
            ctx = contextlib.redirect_stdout(sink) if quiet else contextlib.nullcontext()
            with ctx:
                dataset = data.prepare(data.load_raw())
                lens = pipeline.SafetyLens.load(dataset)
            self._by_section = {s["section"]: s for s in lens.standards}
            self.lens = lens
            self._validate_known_gaps()
            return self

    def _validate_known_gaps(self) -> None:
        """A gap keyed on a label the classifier never emits is a dead rule that
        fails silently. Fail loudly at startup instead."""
        lens = self.lens
        groups = set(lens.clf_major.classes_)
        events = set(lens.clf_fine.classes_)
        bad = [g for g in cfg.NO_SPECIFIC_STANDARD_GROUPS if g not in groups]
        bad += [e for e in cfg.NO_SPECIFIC_STANDARD_EVENTS if e not in events]
        if bad:
            raise ValueError(
                "config declares a known regulatory gap for labels the "
                f"classifiers never produce: {bad}. The rule would never fire."
            )

    @property
    def ready(self) -> bool:
        return self.lens is not None

    def _require(self) -> pipeline.SafetyLens:
        if self.lens is None:
            raise RuntimeError(
                "Service not warm. Call warm() before use. Models are loaded "
                "from out/ - run `python main.py train` if they are missing."
            )
        return self.lens

    def health(self) -> dict:
        return {
            "ready": self.ready,
            "standards_loaded": len(self._by_section),
            "incidents_indexed": len(self._require().incident_texts) if self.ready else 0,
            "margin_floor": cfg.MARGIN_FLOOR,
            "retrieval_floor": cfg.RETRIEVAL_FLOOR,
        }

    # -- tool 1 -------------------------------------------------------------

    def analyse_incident(self, narrative: str) -> dict:
        """Hazard classification + applicable standards + similar incidents.

        `status` is the field the agent must branch on:
            insufficient_input - too short to analyse at all
            abstained          - margin below floor; the agent must ask for detail
            classified         - a result is present

        `standards_status` is the second branch:
            matched         - sections above the floor, each with a verbatim quote
            matched              - sections above the floor, each with a verbatim quote
            no_specific_standard - no standard EXISTS for this hazard. The answer is
                                   the General Duty Clause, and `authority` carries it.
            no_match             - a standard may exist but nothing scored above the
                                   floor. A complete answer, not a gap.
            not_attempted        - group is Nonclassifiable; retrieval declined to route
        """
        narrative = (narrative or "").strip()
        if len(narrative) < MIN_INPUT_CHARS:
            return {
                "status": "insufficient_input",
                "narrative": narrative,
                "message": (
                    "Too short to analyse. Describe what the person was doing, "
                    "what equipment was involved, and which part of the body."
                ),
            }

        result = self._require().analyse(narrative)

        if result["abstained"]:
            return {
                "status": "abstained",
                "narrative": narrative,
                "margin": result["major_margin"],
                "margin_floor": cfg.MARGIN_FLOOR,
                "message": result["message"],
                "ask_for": ["equipment involved", "motion or activity",
                            "part of the body injured"],
            }

        if result["standards"]:
            standards_status = "matched"
        elif result["no_specific_standard"]:
            standards_status = "no_specific_standard"
        elif result["major"] in cfg.NO_RETRIEVAL_GROUPS:
            standards_status = "not_attempted"
        else:
            standards_status = "no_match"

        return {
            "status": "classified",
            "narrative": narrative,
            "hazard_group": result["major"],
            "hazard_group_margin": result["major_margin"],
            "specific_event": result["fine"],
            "specific_event_margin": result["fine_margin"],
            "runners_up": [{"label": l, "score": s} for l, s in result["alternatives"]],
            "standards_status": standards_status,
            "standards": [
                {
                    "citation": f"29 CFR {s['section']}",
                    "section": s["section"],
                    "title": s["title"],
                    "quote": s["quote"],
                    "match_score": s["score"],
                    "lexical_score": s["lexical_score"],
                    "score_note": ("Ranking score is a lexical/latent blend - "
                                   "comparable within this result, not across "
                                   "incidents. lexical_score is the calibrated "
                                   "one. See ADR-019."),
                    "source": "eCFR, Title 29 Part 1910 - verbatim, not generated",
                }
                for s in result["standards"]
            ],
            "standards_message": result.get("message"),
            "authority": result.get("authority"),
            "similar_incidents": [
                {"text": s["text"], "hazard_group": s["group"], "similarity": s["score"]}
                for s in result["similar"]
            ],
        }

    # -- tool 2 -------------------------------------------------------------

    def explain_standard(self, section: str) -> dict:
        """Full verbatim text of one section, from the cached eCFR corpus.

        Exact match only. A near-miss is returned as a labelled suggestion, never
        as the section the caller asked for - handing someone the wrong
        regulation is worse than handing them nothing.
        """
        self._require()
        raw = (section or "").strip()
        m = _SECTION_RE.search(raw)
        if not m:
            return {
                "status": "invalid_section",
                "requested": raw,
                "message": ("Section must look like 1910.219 or 29 CFR 1910.219. "
                            "Only 29 CFR Part 1910 is in this corpus."),
            }

        key = m.group(1)
        found = self._by_section.get(key)
        if found is None:
            prefix = key.rsplit(".", 1)[0] + "."
            near = sorted(s for s in self._by_section if s.startswith(prefix))[:8]
            return {
                "status": "not_found",
                "requested": key,
                "message": (f"{key} is not in the cached corpus "
                            f"({len(self._by_section)} sections of 29 CFR 1910). "
                            "It may exist but fall below the length threshold, or "
                            "sit in another Part."),
                "suggestions_not_the_answer": near,
            }

        return {
            "status": "found",
            "citation": f"29 CFR {found['section']}",
            "section": found["section"],
            "title": found["title"],
            "text": found["text"],
            "characters": len(found["text"]),
            "source": "eCFR, Title 29 Part 1910 - verbatim, not generated",
        }

    # -- tool 3 -------------------------------------------------------------

    def find_similar(self, narrative: str, k: int = cfg.N_SIMILAR) -> dict:
        """k most similar past incidents, with their hazard labels."""
        lens = self._require()
        narrative = (narrative or "").strip()
        if len(narrative) < MIN_INPUT_CHARS:
            return {"status": "insufficient_input", "matches": [],
                    "message": "Too short to search against."}

        k = max(1, min(int(k), MAX_SIMILAR))
        matches = [
            {
                "text": lens.incident_texts[i][:300],
                "hazard_group": lens.incident_labels[i],
                "similarity": round(score, 3),
            }
            for i, score in lens.inc_index.search(narrative, k)
        ]
        return {
            "status": "ok",
            "requested_k": k,
            "corpus_size": len(lens.incident_texts),
            "matches": matches,
        }


def get_service(warm: bool = True) -> SafetyLensService:
    svc = SafetyLensService.instance()
    if warm:
        svc.warm()
    return svc
