# SafetyLens development plan

**Plan version:** 1.1

**Updated:** 2026-10-08

**Current product version:** SafetyLens v1.0 — verified submission build

**Next planned version:** SafetyLens v1.1 — evidence and state reconciliation

**Research version:** SafetyLens v1.2-experimental — retrieval experiments

This is a planning document. A version is released only after its tasks meet
`docs/RULES.md` §15 and repository evidence supports the claim.

## Version map

| Version | Meaning | State |
|---|---|---|
| **v1.0** | OSHA classification, authoritative retrieval, similar incidents, abstention, CLI/API/UI and guarded watsonx integration | Current verified build |
| **v1.1** | Reconciled task documentation, IBM Bob evidence and final submission evidence | Planned |
| **v1.2-experimental** | Sentence-transformer comparison and independently evaluated TASK-316/317 candidates | Planned research |
| **v2.0** | Indian-data expansion using RTI narratives and a DGFASLI corpus | Blocked on external data |

## Current verified behavior — v1.0

SafetyLens classifies workplace incident narratives, retrieves cached authoritative eCFR text,
returns similar OSHA incidents and abstains when evidence is weak or a known regulatory gap applies.
Its CLI, FastAPI, Streamlit and assistant paths are implemented. The watsonx model can select tools,
while code renders the final safety answer. Authenticated regulation caches support Parts 1910 and
1926. The most recently reported full-suite result is **37 passing tests**; it must be rerun before
v1.1 is declared complete.

## Release v1.1 — evidence and state reconciliation

### Step 1 — reconcile repository state

**What can be done**

- Confirm whether TASK-113, TASK-307 and TASK-309 meet their acceptance criteria.
- Replace stale statements that still describe executed work as blocked or half done.
- Make `TASKS.md`, `MEMORY.md`, architecture notes and limitations match executable behavior.

**How to implement it**

1. Inspect the saved review artefact, Part 1926 provenance, assistant behavior and Git state.
2. Run focused assistant/corpus tests and the full suite.
3. Update task state only where execution evidence exists.
4. Update `docs/MEMORY.md`; amend an ADR only if a decision changed.
5. Do not regenerate retrieval metrics or remeasure a changed retriever on a spent set.

**Completion evidence:** passing tests, consistent documentation and no tracked raw XML, caches,
models, `.env` files or secrets.

### Step 2 — finish IBM Bob evidence

**What can be done**

- Demonstrate that IBM Bob was used as the development environment.
- Preserve the distinction between IBM Bob and the SafetyLens assistant.
- Record Semgrep's actual result separately from the manually documented missing-auth limitation.

**How to implement it**

1. Capture the four items listed in `docs/ibm_bob_usage.md`: repository, code explanation, security
   review and passing tests.
2. Save submission-safe images under `docs/evidence/`; show no credentials or private data.
3. Link the evidence from the usage document and record the commands and observed results.
4. Check Phase 1c boxes only after the evidence exists.

### Step 3 — create the submission checkpoint

**What can be done:** produce one reproducible Git revision and short reviewer commands for tests,
the deterministic demo and guarded live-assistant use.

**How to implement it**

1. Run the full suite and inspect representative output.
2. Check tracked paths for secrets and verify ignored assets are not staged.
3. Reconcile `README.md`, `docs/results.md` and `docs/limitations.md` with the actual build.
4. Commit one logical documentation/evidence change, push without force and record the commit ID.

## Release v1.2-experimental — retrieval research

These experiments cannot change v1.0 behavior until independent evidence supports adoption.

### TASK-302b — sentence-transformer retrieval

**Status 2026-10-10:** implementation and protocol frozen; fifth-set labelling and
one-time comparison remain. The optional path passed an unlabelled live smoke
test in 124.4 seconds of full application warm-up and 0.855 seconds for the
first query. It returned only verbatim corpus text. The submission build still
uses LSA.

**What can be done:** compare a pinned local sentence-transformer with the shipped TF-IDF/LSA
retriever, including quality, runtime, memory, package size and offline reproducibility.

**How to implement it**

1. Recheck model availability and hardware; record the exact model and licence.
2. Add the dependency only if it can be pinned and reproduced offline.
3. Implement an optional embedding index behind settings in `config.py`; retain TF-IDF/LSA.
4. Freeze the implementation and protocol before examining new labels or scores.
5. Build a new disjoint set whose labels are assigned without viewing retriever output.
6. Compare recall@1, recall@3, MRR, correct silence, runtime and memory with the baseline.
7. Adopt only if evidence and deployment cost justify it; otherwise record the negative result.

Embeddings may change ranking only. Regulation text still enters verbatim through
`src/regulations.py`, and classifier/retrieval abstention remains enforced. The four existing
evaluation sets are spent and cannot support a new improvement claim.

### TASK-316 — utility task vehicle gap

**What can be done:** determine whether a defined UTV event family has no applicable cached federal
section, or whether Part 1926 and industry context change the answer.

**How to implement it**

1. Verify the conclusion against authoritative sources and the complete cached corpus.
2. Define a rule using existing classifier labels, never one narrative.
3. Confirm the label has enough support to be emitted reliably.
4. Freeze the candidate rule, then evaluate on untouched data reserved for this change.
5. Include nearby positive cases that must continue retrieving a section.

### TASK-317 — combustible-dust gap

**What can be done:** determine when combustible-dust incidents should name the General Duty Clause
while preserving specific standards that genuinely apply.

**How to implement it**

1. Verify federal status and relevant specific standards from authoritative sources.
2. Map the candidate to sufficiently broad classifier evidence.
3. Freeze the handling rule and regression cases before evaluation.
4. Use untouched data reserved for TASK-317, not a set already consumed by TASK-302b or TASK-316.
5. Report corrected silence and any valid retrievals lost.

### Evaluation allocation before implementation

Before results are examined, either create separate untouched sets for the three sequential changes,
or freeze all three variants first and evaluate them once on one untouched set. The second option is
cheaper, but no variant may be tuned after the shared result is visible.

### Mixed Part 1910/1926 applicability check

The combined index can rank a Part 1926 construction section for a narrative that does not establish
construction context. Before accepting a new retriever:

1. define how construction or industry context is established;
2. create paired construction/general-industry cases;
3. ensure Part routing does not present an inapplicable lead section;
4. preserve exact lookup across both authenticated corpora; and
5. report unresolved industry ambiguity instead of guessing.

This is a product-safety question, not a score-only tuning exercise.

## Version v2.0 — Indian-data expansion

- **TASK-210:** file the prepared RTI request using the applicant's identity and keep its receipt.
- **TASK-211:** if narratives arrive, train on OSHA and test on Indian text without hiding domain
  shift.
- **TASK-212:** after obtaining and inspecting the authoritative DGFASLI PDF, design a
  provenance-preserving parser and separate Indian regulation corpus.

No parser will be written blind against a document that has not been obtained and inspected.

## Stop conditions

- No regulation text is generated, reconstructed or paraphrased.
- No threshold is changed to improve a demo.
- No new retrieval claim comes from the four spent evaluation sets.
- No task is completed until it is executed, tested, reviewed and documented.
- A failed experiment, abstention or regulatory gap remains a valid result.
