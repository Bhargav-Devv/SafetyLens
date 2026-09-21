"""
The three tools, as the SafetyLens assistant consumes them.

This module is the contract between the agent and the engine. It holds:

  * JSON Schema definitions for each tool - the thing an agent platform imports
  * a dispatch function that executes a tool call by name

Nothing here decides anything. Every refusal was already decided in
`pipeline.py` and carried outward by `service.py`; this layer only makes those
decisions callable and machine-readable.

Why schemas rather than free-text descriptions: an agent handed prose will
eventually narrate around a refusal in order to be helpful. An agent handed
`"status": "abstained"` as an enumerated value cannot pretend it got an answer.
The refusal has to survive the trip to the language model, and a schema is how
it survives.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg
from src.service import get_service

# --------------------------------------------------------------------------
# Schemas
# --------------------------------------------------------------------------

ANALYSE_INCIDENT = {
    "name": "analyse_incident",
    "description": (
        "Classify a workplace injury narrative into an OIICS hazard group and "
        "specific event, retrieve the 29 CFR 1910 sections that apply, and find "
        "similar past incidents. ALWAYS call this before saying anything about a "
        "hazard or a regulation. Branch on `status` and `standards_status`; never "
        "answer from your own knowledge of OSHA."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative": {
                "type": "string",
                "description": (
                    "Plain-language description of what happened. Richer is "
                    "better: activity, equipment, motion, body part."
                ),
            }
        },
        "required": ["narrative"],
    },
    "returns": {
        "status": ["insufficient_input", "abstained", "classified"],
        "standards_status": [
            "matched", "no_specific_standard", "no_match", "not_attempted",
        ],
    },
}

EXPLAIN_STANDARD = {
    "name": "explain_standard",
    "description": (
        "Return the full verbatim text of one section of 29 CFR Part 1910 from "
        "the cached eCFR corpus. Use this whenever the user asks what a section "
        "says or requires. Quote what comes back. Never paraphrase a regulation "
        "and never supply section text from memory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": "e.g. '1910.219', '29 CFR 1910.147', '1910.28(b)'.",
            }
        },
        "required": ["section"],
    },
    "returns": {"status": ["found", "not_found", "invalid_section"]},
}

FIND_SIMILAR = {
    "name": "find_similar",
    "description": (
        "Find the k most similar incidents in the corpus of ~86,000 OSHA severe "
        "injury reports, with their hazard labels. Use it to show whether an "
        "incident is part of a pattern. These are historical reports, not "
        "regulations - never cite one as a requirement."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "narrative": {"type": "string", "description": "Incident description."},
            "k": {
                "type": "integer", "default": cfg.N_SIMILAR,
                "minimum": 1, "maximum": 10,
                "description": "How many to return.",
            },
        },
        "required": ["narrative"],
    },
    "returns": {"status": ["ok", "insufficient_input"]},
}

TOOLS = [ANALYSE_INCIDENT, EXPLAIN_STANDARD, FIND_SIMILAR]
TOOL_NAMES = [t["name"] for t in TOOLS]


# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

def call(name: str, **kwargs) -> dict:
    """Execute one tool call. Unknown names raise rather than return something
    plausible - a silent no-op here would look exactly like a refusal."""
    svc = get_service()
    if name == "analyse_incident":
        return svc.analyse_incident(kwargs["narrative"])
    if name == "explain_standard":
        return svc.explain_standard(kwargs["section"])
    if name == "find_similar":
        return svc.find_similar(kwargs["narrative"], kwargs.get("k", cfg.N_SIMILAR))
    raise ValueError(f"unknown tool {name!r}; expected one of {TOOL_NAMES}")
