"""
SafetyLens - the two halves joined.

    narrative
       |
       +-- classifier  -> hazard group + specific event   (learned from data)
       |
       +-- retrieval   -> applicable standard, QUOTED     (never generated)
       |
       +-- retrieval   -> similar past incidents
       v
    one answer

Abstention: when the margin between the top two classes is small, the system
refuses to classify and asks for detail. A safety tool that guesses confidently
is worse than one that admits it does not know.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from src import model, regulations, retrieval


class SafetyLens:
    def __init__(self, clf_major, clf_fine, standards, incident_texts, incident_labels):
        self.clf_major = clf_major
        self.clf_fine = clf_fine
        self.standards = standards
        self.incident_texts = list(incident_texts)
        self.incident_labels = list(incident_labels)
        self.std_index = retrieval.build_standards_index(standards)
        self.std_index.fit_latent(self.incident_texts)
        self.inc_index = retrieval.build_incident_index(self.incident_texts)

    @classmethod
    def load(cls, data):
        """Rebuild from saved models + cached standards + the incident corpus."""
        return cls(
            clf_major=model.load("clf_major"),
            clf_fine=model.load("clf_fine"),
            standards=regulations.fetch(),
            incident_texts=data["text"].values,
            incident_labels=data["major"].values,
        )

    def analyse(self, narrative: str) -> dict:
        major, major_margin, _ = model.top_prediction(self.clf_major, narrative)
        fine, fine_margin, alternatives = model.top_prediction(self.clf_fine, narrative)

        result = {
            "narrative": narrative,
            "major": major, "major_margin": round(major_margin, 3),
            "fine": fine, "fine_margin": round(fine_margin, 3),
            "alternatives": alternatives,
            "abstained": major_margin < cfg.MARGIN_FLOOR,
            "standards": [],
            "similar": [],
            "no_specific_standard": False,
            "authority": None,
        }

        if result["abstained"]:
            result["message"] = (
                "Margin below threshold - not classified. Add detail: what "
                "equipment was involved, what motion, which part of the body."
            )
            return result

        # A narrative the coders could not categorise gives retrieval nothing to
        # route on. Returning "the three least-bad sections" would be guessing.
        # Some hazards have no standard because Congress never wrote one, not
        # because retrieval failed. Returning the least-bad section there is the
        # single most dangerous thing this system could do, so it is checked
        # BEFORE the index is ever consulted.
        gap = (cfg.NO_SPECIFIC_STANDARD_GROUPS.get(major)
               or cfg.NO_SPECIFIC_STANDARD_EVENTS.get(fine))

        if major in cfg.NO_RETRIEVAL_GROUPS:
            result["message"] = (
                "Hazard group is Nonclassifiable - no standard can be routed to "
                "from this narrative. Classification stands; retrieval declines."
            )
        elif gap:
            result["no_specific_standard"] = True
            result["authority"] = cfg.GENERAL_DUTY_CLAUSE
            result["message"] = gap
        else:
            query = f"{major}. {fine}. {narrative}"
            for idx, score, lex in self.std_index.search_for_hazard(
                    query, major, cfg.N_STANDARDS, event=fine):
                s = self.standards[idx]
                result["standards"].append({
                    "section": s["section"], "title": s["title"],
                    "quote": s["text"][:380] + "...", "score": round(score, 3),
                    # Carried because `score` is a blended number that is
                    # comparable within one result and not across incidents.
                    # See ADR-019.
                    "lexical_score": round(lex, 3),
                })
            if not result["standards"]:
                result["message"] = (
                    f"No section of 29 CFR 1910 matched above the floor "
                    f"({cfg.RETRIEVAL_FLOOR}). Some hazards - heat stress, for "
                    "one - have no specific standard and are enforced under the "
                    "General Duty Clause. Reporting no match is the correct answer."
                )

        for idx, score in self.inc_index.search(narrative, cfg.N_SIMILAR):
            result["similar"].append({
                "text": self.incident_texts[idx][:200],
                "group": self.incident_labels[idx], "score": round(score, 3),
            })

        return result


def render(result: dict) -> str:
    """Human-readable report. This is what the SafetyLens assistant speaks."""
    lines = ["=" * 80, f"INCIDENT: {result['narrative'][:220]}", "-" * 80]

    if result["abstained"]:
        lines += [f"NOT CLASSIFIED (margin {result['major_margin']})",
                  result["message"], "=" * 80]
        return "\n".join(lines)

    lines += [
        f"GROUP    : {result['major']}   (margin {result['major_margin']})",
        f"SPECIFIC : {result['fine']}   (margin {result['fine_margin']})",
        f"ALSO     : {result['alternatives']}",
    ]
    if result["standards"]:
        lines += ["", "APPLICABLE STANDARDS - quoted from eCFR, not generated:"]
    for s in result["standards"]:
        lines += ["",
                  f"  29 CFR {s['section']} - {s['title'][:66]}   "
                  f"[rank score {s['score']}, lexical {s['lexical_score']}]",
                  f'   "{s["quote"][:260]}"']

    if result["no_specific_standard"]:
        lines += ["", "APPLICABLE STANDARDS: none exist.",
                  f"  AUTHORITY: {result['authority']}",
                  "  " + (result.get("message") or "")]
    elif not result["standards"]:
        lines += ["", "APPLICABLE STANDARDS: none above the match floor.",
                  "  " + (result.get("message") or "")]

    lines += ["", "SIMILAR PAST INCIDENTS:"]
    lines += [f"  - {s['text']}" for s in result["similar"]]
    lines.append("=" * 80)
    return "\n".join(lines)
