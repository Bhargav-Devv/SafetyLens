# SafetyLens

**Hazard classification + regulation retrieval for severe workplace injury reports.**

Bhargav Rao Mahankali - St Peter's Engineering College
1M1B x IBM SkillsBuild, AI for Sustainability Virtual Internship - **SDG 8.8**

---

## The problem

OSHA holds **86,209** reports of severe workplace injuries (Jan 2015 - Sep 2023). Each is a
plain-English narrative written by the employer. Nobody reads them systematically, so the same
accident repeats.

And knowing *what happened* is not enough to prevent it. You need the specific safety standard that
applies - and that lives in thousands of pages of regulation no floor supervisor has ever opened.

Two pieces of knowledge exist and never meet.

## The system

| Half | Job | Why it is separate |
|---|---|---|
| **Classifier** (ML) | narrative -> hazard category | Learns from 86k human-coded incidents |
| **Retrieval** (RAG) | hazard + narrative -> applicable standard, **quoted** | A model must never invent a regulation |

Retrieval ranks on a blend of lexical TF-IDF and a latent semantic space fitted over the standards
plus 20,000 narratives. The lexical half is what puts a forklift narrative on *Powered industrial
trucks* every time; the latent half is what finds *lockout/tagout* from "cleaning a running
conveyor", where the two texts share almost no words at all.

**The design rule: the model classifies, retrieval quotes. No regulatory text is ever generated.**
If eCFR cannot be reached, `src/regulations.py` raises rather than falling back to generated text.

## Results

| Task | Classes | Accuracy | Macro F1 | Baseline macro F1 | Lift |
|---|---|---|---|---|---|
| Major event group | 8 | **0.938** | 0.832 | 0.126 | 6.6x |
| Fine-grained event | 77 | **0.668** | **0.584** | 0.013 | 45x |

**Retrieval is the weaker half, and now has a number.** Measured on a third labelled set of 30 that
was never used to make a decision:

| | value |
|---|---|
| recall@3 | **0.600** |
| recall@1 | **0.400** |
| Best single fixed section | 0.167 |
| Random 3 of 170 | 0.000 |
| **Correct silence** where no standard exists | **0.889** |

That figure is measured against labels assigned by an AI assistant, not a safety professional, and it
is always reported that way.

**Three evaluation sets, and the second and third earned their keep in opposite directions.**

| | dev said | unseen data said | verdict |
|---|---|---|---|
| Scope routing | recall@3 0.364 → 0.424 | 0.484 → **0.484** | gain was **noise**, discarded |
| Latent retrieval | recall@1 0.394 → **0.303** | 0.267 → **0.400** | gain is **real**, shipped |

One looked like a six-point win and was nothing. The other looked like a loss and was a thirteen-point
gain. **Two sets of thirty disagreed about the sign of the effect**, which is the plainest thing this
project can say about how much weight a small evaluation carries. See `docs/results.md`.

Full per-class breakdown in `docs/results.md`.

## Setup

```bash
pip install -r requirements.txt          # core
pip install -r requirements-serve.txt    # optional: HTTP service
pip install -r requirements-ui.txt       # optional: Streamlit interface
```

Put the OSHA CSV (`January2015toSeptember2023.csv`) in `data/raw/`.

## Usage

```bash
python main.py train                  # train both models, write metrics + figures
python main.py failures               # where it fails, and why that is a finding
python main.py demo                   # run the built-in examples end to end
python main.py analyse "Worker fell 18 feet from an unguarded roof edge."

python main.py bob                    # talk to it - the agent decision flow
python main.py transcript             # regenerate docs/assistant_transcript.md
python tests/test_refusals.py         # 15 tests: every refusal rule

python main.py evaluate-retrieval     # retrieval accuracy against the labelled set
python main.py review                 # second-labeller pass over 15 of the 50

python serve.py                       # HTTP service on :8000, interactive docs at /docs
python serve.py --spec                # write openapi.json for an agent platform, don't serve

streamlit run app.py                  # the interface, per DESIGN.md Part 2
python tests/test_ui.py               # 5 tests: every required UI state, headless
```

`train` takes about 4-6 minutes. Everything else loads the saved models - the first call warms up in
about 25 seconds, then answers immediately.

### A conversation

```
you > Someone got hurt at work yesterday.

assistant > I cannot identify the hazard reliably from that - the margin between the
      top two categories was 0.009, below the 0.3 floor.
      Tell me: equipment involved; motion or activity; part of the body injured.

you > He was cleaning the packaging conveyor while it was still running and his
      hand was pulled into the rollers. He lost two fingers.

assistant > That reads as Contact with objects and equipment - specifically
      "Caught in running equipment or machinery during maintenance, cleaning".
      29 CFR 1910.219 - Mechanical power-transmission apparatus applies...

you > Are we going to be cited for that?

assistant > I can't tell you that, and I'd be doing you harm if I tried. Whether an
      employer gets cited is a judgement an OSHA compliance officer makes...
```

Full transcript, generated rather than written: `docs/assistant_transcript.md`.

## What is and is not built

| Piece | State |
|---|---|
| Classifiers, retrieval, abstention, CLI | built |
| Tool contract + JSON schemas, system prompt | built |
| Decision flow, deterministic (`src/agent.py`) | built, tested |
| HTTP service + OpenAPI 3 spec (`serve.py`) | built, smoke-tested |
| Streamlit interface (`app.py`) | built, 5 state tests |
| **Hosted agent on IBM watsonx** | **not built - needs an account, not code** |

Everything the hosted agent needs exists: `openapi.json` to import, `docs/assistant_system_prompt.md` to
paste. `python serve.py --spec` prints the five wiring steps.

`src/agent.py` is the decision flow with the language model removed. That costs conversational
fluency and buys two things: every refusal rule becomes a test that runs in seconds, and the system
runs without credentials. See `docs/DECISIONS.md` ADR-013.

## Documentation — read in this order

| File | Holds |
|---|---|
| `docs/PRD.md` | **What and why.** Problem, users, features, success criteria |
| `docs/ARCHITECTURE.md` | **How.** Stack, flow, folder structure, architectural rules |
| `docs/DESIGN.md` | Output format standards (live) + future UI spec (not built) |
| `docs/RULES.md` | **The rulebook.** Coding, ML, data, security, testing, AI collaboration |
| `docs/DECISIONS.md` | Architecture decision records — permanent, with reasoning |
| `docs/MEMORY.md` | Current project state, known issues, next step |
| `TASKS.md` | Work breakdown by phase, one task at a time |
| `docs/agent_logic.md` | assistant tool contract, refusal rules, and what is built vs not |
| `docs/assistant_system_prompt.md` | The system prompt, verbatim, ready to paste |
| `docs/assistant_transcript.md` | A captured conversation - generated, not hand-written |
| `docs/retrieval_labelling_guide.md` | How the retrieval ground truth was built, frozen before labelling |
| **`HANDOFF.md`** | **Everything still outstanding, and what each item needs** |
| `docs/findings_indian_data.md` | Why the port to India is blocked by disclosure, not by method |
| `docs/assistant_test_scenarios.md` | 10 scenarios to run against the hosted agent |
| `docs/rti_application_draft.md` | RTI request for Form 18 narratives, ready to file |
| `docs/DECISIONS.md` ADR-016/017 | Why the dev gain was discarded, and what was left deliberately unfixed |
| `docs/results.md` | Every number, with the failure analysis |
| `docs/limitations.md` | What this does not do, stated plainly |

### Working with an AI assistant on this project

Give it context before asking for code:

> Read `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/DESIGN.md`, `docs/RULES.md` and `TASKS.md`.
> Do not modify anything yet. Understand the product, the architecture, the design system, the rules
> and the current tasks. Identify missing information. Then explain the implementation plan for
> TASK-XXX. Do not write code yet.

Cursor rules are in `.cursor/rules/` and load automatically.

## Layout

```
safetylens/
├── config.py              every tunable in the project - start here
├── main.py                CLI entry point
├── TASKS.md               work breakdown
├── .env.example           environment variables, values blank
├── .cursor/rules/         AI assistant rules, auto-loaded
├── docs/                  see the table above
├── src/
│   ├── data.py            loading, encoding, label preparation
│   ├── model.py           classifier, baselines, margin confidence
│   ├── regulations.py     eCFR fetch + parse + cache  (never generates text)
│   ├── retrieval.py       TF-IDF indexes over standards and past incidents
│   ├── pipeline.py        the two halves joined, with abstention
│   ├── service.py         load-once service; carries refusals as data
│   ├── assistant_tools.py       the three tools, with JSON schemas
│   ├── agent.py           the decision flow, deterministic
│   ├── evalset.py         the labelled retrieval set - sampling and scoring
│   └── charts.py          figures
├── app.py                 the interface - streamlit run app.py
├── serve.py               HTTP service; --spec writes openapi.json
├── openapi.json           import this into an agent platform
├── tests/
│   ├── test_refusals.py   every refusal rule, as an assertion
│   └── test_ui.py         every required UI state, driven headlessly
├── data/raw/              put the OSHA CSV here
└── out/                   models, metrics, figures
```

## Two things worth knowing

**The OSHA CSV is Windows-1252 encoded, not UTF-8.** Reading it with the default encoding fails with
`No columns to parse from file`, which looks like a corrupt download and is not. `config.ENCODINGS`
handles it.

**Ask for lockout/tagout by number and you get 30,924 characters of 1910.147 instantly. Ask the
system to *find* it from "cleaning a running conveyor" and it ranks 77th of 170.** The corpus holds
the right answer; TF-IDF cannot reach it, because the regulation says "energy isolating device" and
"servicing and maintenance" while the narrative says "cleaning", "rollers" and "fingers". That gap is
the measured case for embeddings in TASK-302, and the reason `docs/limitations.md` claims no accuracy
figure for retrieval.
