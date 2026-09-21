# Architecture

*ARCHITECTURE = HOW. For WHAT and WHY, see PRD.md.*

---

## Technology stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.10+ | The ML work is the project |
| Data | pandas | |
| Classifier | scikit-learn — TF-IDF + LinearSVC | Trains in minutes on CPU; competitive on short formulaic text |
| Retrieval | scikit-learn TF-IDF + cosine similarity | No embedding service, no vector DB, no network at query time |
| Regulations | eCFR public API → cached JSON | Authoritative source, verbatim text |
| Persistence | joblib for models, JSON for corpus and metrics | Zero setup |
| Interface | CLI (`main.py`) | The output is a report, not a page |
| Conversational layer | Tools, prompt, decision flow and tests **built**; hosted watsonx agent **not** | See `agent_logic.md` |

**Explicitly not used:** no database server, no web framework, no Docker, no cloud hosting, no
authentication. Each would consume time that belongs to the model. See DECISIONS.md ADR-003.

## High-level flow

```
                    data/raw/*.csv                 eCFR API
                          |                            |
                    src/data.py                 src/regulations.py
              load · validate · label            fetch · parse · cache
                          |                            |
                          |                     data/standards.json
                          |                            |
                    src/model.py                 src/retrieval.py
             TF-IDF + LinearSVC x2            StandardsIndex · Index
              out/clf_*.joblib                          |
                          |                            |
                          +------------+---------------+
                                       |
                               src/pipeline.py
                    classify → condition query → retrieve → abstain
                                       |
                    +------------------+------------------+
                    |                                     |
              main.py (CLI)                      the SafetyLens assistant (specified)
                                                  docs/agent_logic.md
```

## Folder structure

```
safetylens/
├── config.py              every tunable in the project
├── main.py                CLI entry point
├── TASKS.md               work breakdown, phase by phase
├── .env.example           environment variables (no secrets)
├── docs/
│   ├── PRD.md             what and why
│   ├── ARCHITECTURE.md    this file — how
│   ├── DESIGN.md          output format standards + future UI spec
│   ├── RULES.md           development rules
│   ├── DECISIONS.md       architecture decision records
│   ├── MEMORY.md          current project state
│   ├── agent_logic.md     assistant tool contract and refusal rules
│   ├── assistant_system_prompt.md   the prompt, verbatim
│   ├── assistant_transcript.md      a captured conversation (generated)
│   ├── problem_statement.md
│   ├── results.md         every number, with failure analysis
│   └── limitations.md
├── src/
│   ├── data.py            loading, encoding, label preparation
│   ├── model.py           classifiers, baselines, margin confidence
│   ├── regulations.py     eCFR fetch/parse/cache — never generates text
│   ├── retrieval.py       TF-IDF indexes over standards and incidents
│   ├── pipeline.py        the two halves joined, with abstention
│   ├── service.py         load-once service; refusals as machine-readable data
│   ├── assistant_tools.py       the three tools, with JSON schemas
│   ├── agent.py           the decision flow, deterministic
│   └── charts.py          figures
├── tests/
│   └── test_refusals.py   every refusal rule, as an assertion
├── data/
│   ├── raw/               the OSHA CSV
│   └── standards.json     cached regulation corpus
└── out/                   models, metrics, figures, demo output
```

## Component responsibilities

| Module | Owns | Must not |
|---|---|---|
| `config.py` | Every tunable value | Contain logic |
| `src/data.py` | Encoding, validation, label derivation, rare-class filtering | Know about models or retrieval |
| `src/model.py` | Training, baselines, per-class metrics, margin confidence | Load files from disk except via `config` paths |
| `src/regulations.py` | Fetching and caching authoritative regulation text | **Ever generate, paraphrase or infer regulation text** |
| `src/retrieval.py` | Ranking. Title weighting, hazard boost, floors | Modify the text it returns |
| `src/pipeline.py` | Orchestration and abstention | Contain training code |
| `src/service.py` | Loading once; carrying refusals outward as enumerated `status` values | Decide anything. Every decision was made in `pipeline.py` |
| `src/assistant_tools.py` | Tool schemas and dispatch | Interpret a result |
| `src/agent.py` | Branching on `status`, composing replies, refusing per Rules 5 and 6 | Answer without calling a tool first |
| `src/charts.py` | Figures | Compute metrics |
| `main.py` | CLI wiring | Contain business logic |

## Architectural rules

1. **Regulation text is fetched, never generated.** It enters the system only through
   `src/regulations.py`. If the source is unreachable, the system raises.
2. **Ranking may be adjusted; text may not.** Title weighting and hazard boosting change *which*
   section surfaces, never *what it says*.
3. **All tunables live in `config.py`.** A magic number anywhere else is a bug.
4. **`src/data.py` knows nothing about models.** Label preparation is independent of what consumes it.
5. **`src/pipeline.py` does not train.** It loads what `main.py train` produced.
6. **No module writes outside `out/` and `data/`.**
7. **Every metric is reported beside a baseline.**
8. **Abstention is enforced in `pipeline.py`, not in the caller.** A consumer cannot opt out of it.
9. **Refusals travel as data, not prose.** `status` and `standards_status` are enumerated values. An
   agent handed prose will eventually narrate around a refusal in order to be helpful; an agent
   handed `status == "abstained"` cannot. The refusal has to survive the trip to the language model.
10. **A hazard with no governing standard is answered before the index is consulted.** See
   `config.NO_SPECIFIC_STANDARD_*` and ADR-011. Retrieval never gets the chance to fill that silence.
11. **Retrieval confirms the classification.** A section whose title does not carry the predicted
   hazard's vocabulary is not a candidate. See `REQUIRE_HAZARD_ROUTING` and ADR-012.

## Data flow guarantees

- The narrative is never modified between input and classification.
- The retrieval query is `predicted_major. predicted_fine. narrative` — retrieval is always
  conditioned on the classifier's output.
- Every returned standard carries its section number, match score and verbatim quote.
- A `(place, feature)` — here, a `(narrative, hazard)` — with insufficient evidence returns an
  explicit refusal, never a default.

## Failure behaviour

| Failure | Behaviour |
|---|---|
| CSV missing or undecodable | `FileNotFoundError` / `ValueError` naming the searched paths |
| Wrong CSV supplied | Rejected by column validation before any training |
| Models not trained | `FileNotFoundError` pointing at `python main.py train` |
| eCFR unreachable, no cache | `RuntimeError`. **No fallback to generated text.** |
| Classifier margin below floor | Refusal with a request for specific detail |
| No standard above retrieval floor | Explicit "no match" message, not the three least-bad sections |
