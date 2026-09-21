# SafetyLens — project instructions

Hazard classification + regulation retrieval over OSHA severe injury reports.
**SDG 8.8** · Bhargav Rao Mahankali · St Peter's Engineering College

## Read before changing anything

| File | Holds |
|---|---|
| `docs/PRD.md` | What and why — problem, users, features, success criteria |
| `docs/ARCHITECTURE.md` | How — stack, flow, module responsibilities, architectural rules |
| `docs/RULES.md` | The full rulebook: coding, ML, data, security, testing |
| `docs/DECISIONS.md` | ADR-001…010. **Do not reverse one without a new ADR.** |
| `docs/MEMORY.md` | Current state, known issues, next step |
| `TASKS.md` | Work breakdown. Implement by task ID, never by loose description. |
| `docs/DESIGN.md` | Output format standards (live) + future UI spec (not built) |
| `docs/agent_logic.md` | assistant tool contract + what is built vs not (table at the top) |

## The five non-negotiables

1. **Never generate, paraphrase or summarise regulation text.** It enters only through
   `src/regulations.py`, verbatim from eCFR. If the source is unreachable, raise — do not degrade
   into invented text. A plausible-but-wrong safety regulation is more dangerous than no answer.
2. **Never remove or weaken abstention to make output look better.** The classifier refuses below
   `MARGIN_FLOOR`; retrieval returns nothing below `RETRIEVAL_FLOOR`. A refusal is a correct output.
3. **Always report a baseline beside every metric.** A number with nothing to compare it to is not
   a result.
4. **All tunables live in `config.py`.** A hard-coded number anywhere else is a bug.
5. **Never claim something is built when it is specified.** the SafetyLens assistant is specified in
   `docs/agent_logic.md` and not implemented. Every document that mentions it says so.

## Facts that cost hours to discover

- The OSHA CSV is **Windows-1252**, not UTF-8. Do not "fix" this by forcing UTF-8.
- OIICS event codes are **variable length** (`64`, `531`, `1214`). The major group is the first digit
  **as written** — `str(int(code))[0]`, never `.zfill(4)[0]`. That bug misfiled 2,192 heat incidents
  and cost 10 points of accuracy. See ADR-007.
- Regulation sections average ~10,000 characters, which drowns plain TF-IDF. Title weighting plus the
  hazard boost is what makes retrieval work. See ADR-008.
- `osha.gov` blocks scripted downloads. Figshare returns HTTP 202 with an empty body for large ones.
- There is **no federal OSHA heat standard** — heat illness is enforced under the General Duty Clause,
  so no section of 1910 is a correct answer for a heat case.

## Working style

```
read the docs → pick a task ID from TASKS.md → plan → implement → test → run it → mark complete
```

- Do not modify files unrelated to the current task.
- Do not add a dependency without justification.
- Do not mark a task complete without executing it.
- If a result changes, update `docs/results.md` in the same change.
- Update `docs/MEMORY.md` when project state changes.
- **When uncertain, ask. Do not guess and proceed.**

## What is outstanding

`HANDOFF.md` is the single list. Everything on it needs an account, a browser download, a signature
or Bhargav's judgement — nothing on it is blocked on code.

## Training needs more than 2.9 GB

The local Cowork workspace is killed partway through fitting. Train on Windows, or in the cloud
container. Models are now saved compressed (zlib 9): fine classifier 29 MB, not 68 MB.

## Commands

```bash
python main.py train      # train both classifiers, write metrics + figures
python main.py demo       # run the built-in examples end to end
python main.py failures   # where the model fails, and why that is a finding
python main.py analyse "Worker fell 18 feet from an unguarded roof edge."
python main.py bob        # the agent decision flow, interactive
python main.py transcript # regenerate docs/assistant_transcript.md
python tests/test_refusals.py   # 15 tests - run these before claiming anything works
python main.py evaluate-retrieval   # retrieval recall against the labelled set
python main.py review               # second-labeller pass - Bhargav runs this
```

## Current state

v1 and Phase 1 complete. Major group **0.938** accuracy / 0.832 macro F1 · fine-grained **0.668** /
**0.585**. Retrieval on the third, unseen set: **recall@3 0.600**, recall@1 0.400, correct silence
0.889, after latent semantic retrieval (ADR-018).
`tests/test_refusals.py` 15/15. Next work is **TASK-307** — Bhargav runs `python main.py review` so
the retrieval figure gets an agreement number. See `docs/MEMORY.md`.

## THE RETRIEVAL FLOOR IS INERT — ADR-019

`RETRIEVAL_FLOOR` was calibrated for raw TF-IDF cosine (0.00-0.08). The blended score spans
0.25-0.33, so everything clears it and the no-match path no longer fires. This is known, documented
and deliberate — the measured configuration is the shipped one. **Do not "fix" it by raising the
number**; a calibrated floor for a blended score needs a fourth labelled set (TASK-313).

**Do not min-max normalise the two score vectors before blending.** Tried and measured: it wrecks the
ranking (crane's top hit becomes *1910.30 Training requirements*).

Ranking scores are not match quality. The agent states rank; `lexical_score` carries the calibrated
number. A test asserts this.

## ALL FOUR EVALUATION SETS ARE SPENT — read this before touching retrieval

`data/retrieval_eval_*.json` — **dev**, tuned against.
`data/retrieval_holdout_*.json` — **held-out**, one measurement spent on ADR-016.
`data/retrieval_valid_*.json` — **third set**, one measurement spent on ADR-018.
`data/retrieval_cal_*.json` — **fourth set**, one measurement spent on ADR-021, re-measured after ADR-024.

**Any further retrieval change needs a FIFTH labelled set, or it is not measured.** Re-running an
existing set after a new change produces a number that looks real and is not.

Neither of these is hypothetical:

- **ADR-016** raised dev recall@3 from 0.364 to 0.424 — a clean 6-point gain. Held-out recall was
  **identical before and after**. Noise. The change was kept only for the coverage effect, which
  replicated.
- **ADR-018** *lowered* dev recall@1 from 0.394 to 0.303 and would reasonably have been dropped. On
  the unseen third set it raised recall@1 by **thirteen points**.

The rule is not "trust the lower number". It is that thirty cases cannot tell you which way a change
went, in either direction.

Two known fixes are deliberately **left unfixed** for the same reason — a public-road known gap and
an over-coarse Exposure keyword list, both found on held-out. See ADR-017. Do not "just fix" them.

Not built: the hosted agent on IBM watsonx. Needs an account, not code (Phase 1b).

## NEVER write a test fixture into `data/` — ADR-025

A test did, deletion was restricted so its cleanup failed, and the fixture was merged into the
retrieval index and **served to a user as a real OSHA section**. Cached Parts now require a
provenance block and are refused without one. Tests use temp directories.

## Two defects found on 2026-09-20 — do not reintroduce either

1. **Heat retrieved *1910.138 Hand protection*** at 0.0845 against a floor of 0.08 and shipped it,
   while the docs claimed it reported no match. No threshold fixes this: the correct crane retrieval
   scores 0.085 too. Fixed by `NO_SPECIFIC_STANDARD_*` and `REQUIRE_HAZARD_ROUTING` (ADR-011/012).
   **Before changing a retrieval threshold, read ADR-012 — the obvious fix has already been tried
   and measured.**

2. ***"Are we going to be cited for that?"*** was run through the classifier and answered with a
   hazard label and a citation — a Rule 5 breach. Rules 1–4 constrain the answer; nothing constrained
   the question. `_is_compliance_question` and `_is_question_not_narrative` in `src/agent.py` do now,
   and five phrasings are in the test suite (ADR-013).

Both were found by generating output and reading it, not by reasoning about the code.
