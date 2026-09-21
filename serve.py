"""
SafetyLens over HTTP - the three tools, as an agent platform consumes them.

    pip install -r requirements-serve.txt
    python serve.py                      # http://127.0.0.1:8000, docs at /docs
    python serve.py --spec               # write openapi.json and exit

IBM watsonx Orchestrate imports an OpenAPI 3 specification and turns each
operation into a tool. `--spec` writes that file without starting the server, so
the spec can be imported and reviewed before anything is deployed.

Nothing here decides anything. Every refusal was decided in `pipeline.py` and
carried outward by `service.py`; this layer only puts it on a port. In
particular the enumerated `status` and `standards_status` values survive the
trip intact, because an agent handed prose will eventually narrate around a
refusal and an agent handed `"abstained"` cannot.

WARNING - there is no authentication. `scope.md` equivalent: this is a
demonstration service. Do not expose it to the internet without putting a
gateway in front of it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
from src import assistant_tools
from src.service import get_service

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Build the engine once, before the first request. Roughly 40 seconds:
    two classifiers, 170 cached sections, a TF-IDF index over ~86,000
    narratives and the SVD fitted over both. Every request after is fast."""
    get_service()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="SafetyLens",
    version="1.0.0",
    description=(
        "Hazard classification and OSHA regulation retrieval for workplace "
        "incident narratives.\n\n"
        "**Branch on `status`, never on prose.** `abstained` means the "
        "classifier declined and the caller must ask for detail rather than "
        "guess. `no_specific_standard` means no OSHA standard exists for this "
        "hazard and the General Duty Clause applies - it is a complete answer, "
        "not a failure to find one.\n\n"
        "Regulation text is quoted verbatim from eCFR and is never generated."
    ),
)


class IncidentRequest(BaseModel):
    narrative: str = Field(
        ...,
        description="Plain-language description of what happened. Richer is "
                    "better: activity, equipment, motion, body part.",
        json_schema_extra={"example": (
            "Employee was cleaning a conveyor belt while it was running when "
            "his sleeve became caught in the rollers."
        )},
    )


class SectionRequest(BaseModel):
    section: str = Field(
        ..., description="e.g. '1910.147', '29 CFR 1910.219', '1910.28(b)'.",
        json_schema_extra={"example": "1910.147"},
    )


class SimilarRequest(BaseModel):
    narrative: str = Field(..., description="Incident description.")
    k: int = Field(cfg.N_SIMILAR, ge=1, le=10, description="How many to return.")


@app.get("/health", operation_id="health", tags=["meta"],
         summary="Readiness and the thresholds currently in force")
def health() -> dict:
    return get_service().health()


@app.post("/analyse_incident", operation_id="analyse_incident", tags=["tools"],
          summary="Classify a hazard, retrieve applicable standards, find similar incidents")
def analyse_incident(body: IncidentRequest) -> dict:
    """ALWAYS call this before saying anything about a hazard or a regulation.

    Read `status` first: `insufficient_input`, `abstained`, or `classified`.
    Then `standards_status`: `matched`, `no_specific_standard`, `no_match`, or
    `not_attempted`. Never answer from your own knowledge of OSHA.
    """
    return assistant_tools.call("analyse_incident", narrative=body.narrative)


@app.post("/explain_standard", operation_id="explain_standard", tags=["tools"],
          summary="Full verbatim text of one section of 29 CFR 1910")
def explain_standard(body: SectionRequest) -> dict:
    """Quote what comes back. Never paraphrase a regulation, and never supply
    section text from memory. `status` is `found`, `not_found` or
    `invalid_section`; a `not_found` result carries no text at all."""
    return assistant_tools.call("explain_standard", section=body.section)


@app.post("/find_similar", operation_id="find_similar", tags=["tools"],
          summary="Most similar past incidents from ~86,000 OSHA reports")
def find_similar(body: SimilarRequest) -> dict:
    """Historical reports, not regulations. Never cite one as a requirement."""
    return assistant_tools.call("find_similar", narrative=body.narrative, k=body.k)


def write_spec(path: Path) -> None:
    spec = app.openapi()
    spec["servers"] = [{
        "url": "https://REPLACE-WITH-YOUR-PUBLIC-URL",
        "description": "Set this to the public HTTPS URL of this service before "
                       "importing. watsonx Orchestrate calls the URL in this field.",
    }]
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    print(f"wrote {path}")
    print("\nTo wire this into IBM watsonx Orchestrate:")
    print("  1. Run this service somewhere reachable over HTTPS")
    print("  2. Edit the `servers[0].url` field above to that address")
    print("  3. Orchestrate -> Skills -> Add -> Import OpenAPI, upload this file")
    print("  4. Paste docs/assistant_system_prompt.md into the agent's instructions")
    print("  5. Work through tests/test_refusals.py by hand against the agent")
    print("     and record where the language model differs (TASK-113)")


if __name__ == "__main__":
    if "--spec" in sys.argv:
        write_spec(Path(__file__).parent / "openapi.json")
        sys.exit(0)
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
