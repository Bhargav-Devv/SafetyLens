# Development Rules

The AI rulebook for this project. Read before writing any code.
Supersedes `context.md`.

---

## 1. General principles

- **Do not invent requirements.** Implement what PRD.md and TASKS.md specify, by task ID.
- **Do not implement anything listed under Out of Scope in PRD.md.**
- Reuse what exists. Do not duplicate logic.
- Keep functions small and named for what they do.
- Do not modify files unrelated to the task at hand.
- If a change touches more than three files, write the plan down first.

## 2. Before coding

1. Read PRD.md, ARCHITECTURE.md and RULES.md.
2. Read DECISIONS.md — do not reverse a recorded decision without a new ADR.
3. Read MEMORY.md for current state and known issues.
4. Inspect the existing implementation before changing it.
5. State the plan for anything non-trivial before writing code.

## 3. Coding standards

- Python 3.10+. Type hints on public functions.
- Module docstring explaining **why the module exists**, not what the language does.
- `from __future__ import annotations` at the top of every module.
- Standard library, then third-party, then local imports.
- No bare `except:`. Catch what you can handle.
- No print-debugging left in committed code.
- Max line length 100.

## 4. Project structure

- All tunables in `config.py`. **A hard-coded number elsewhere is a bug.**
- One responsibility per module — see the table in ARCHITECTURE.md.
- No module writes outside `out/` and `data/`.
- `src/pipeline.py` orchestrates; it does not train.
- `main.py` wires the CLI; it contains no business logic.

## 5. Machine learning rules

- **Always report a baseline beside every metric.** A number with nothing to compare it to is not a
  result.
- **Fix the seed** (`config.SEED`) and record it in the output.
- **Split by the right unit.** Stratify by the target. Never a random split when grouping matters.
- **Touch the test set once.** If it is evaluated twice, say so.
- **Refuse to report metrics for classes with fewer than 10 test examples.** Print "insufficient
  data" instead.
- **Check what the label actually contains before building on it.** An earlier version of this
  project predicted severity until the data showed every record was already severe. That question,
  asked in the first hour, is worth more than any model choice made later.
- Record `model_version` on every prediction artefact.
- When two models disagree on an obvious case, **investigate before trusting the metric**. That is
  how the OIICS zero-padding bug was found — see DECISIONS.md ADR-007.

## 6. Data rules

- The OSHA CSV is **Windows-1252**, not UTF-8. `config.ENCODINGS` handles it. Do not "fix" this by
  forcing UTF-8.
- Validate columns before accepting any input file. Never train on an unvalidated CSV.
- OIICS event codes are **variable length**. The major group is the first digit **as written**. Do
  not zero-pad first.
- Never commit the raw dataset or trained models to git.

## 7. Regulation and retrieval rules

**These are not style preferences. They are the reason the system is defensible.**

1. **Never generate, paraphrase or summarise regulation text.** It enters only through
   `src/regulations.py`, verbatim from eCFR.
2. **If the authoritative source is unreachable and no cache exists, raise.** Do not degrade
   gracefully into invented text.
3. **Ranking may be adjusted. Text may not.** Title weighting and hazard boosting change which
   section surfaces, never its contents.
4. **Never present a match below `config.RETRIEVAL_FLOOR` as applicable.** "No match" is a complete
   answer.

## 8. Abstention rules

- Below `config.MARGIN_FLOOR`, the system refuses and asks for specific detail.
- **Do not lower a threshold to make a demo look better.** Change it only after inspecting real
  margins, and record the reasoning.
- Abstention is enforced in `pipeline.py`. A caller cannot opt out.
- A refusal is a correct output. Never style or describe it as an error.

## 9. Security

- No secrets in source. Use `.env`, and keep `.env.example` current with every variable — values
  blank.
- `.env` is gitignored. Never commit it.
- No API key, token or credential in a log line, error message or committed notebook output.
- Validate any external input before it reaches a model.
- Treat the regulation corpus as read-only.

## 10. Testing

- Every module in `src/` gets tests for its contract, not its implementation.
- **Required tests before a feature is done:** the happy path, the abstention path, and the failure
  path.
- Specifically required:
  - `regulations.fetch()` raises rather than returning generated text when the source is unreachable
  - `pipeline.analyse()` abstains below the margin floor
  - `retrieval.search_for_hazard()` returns an empty list below the retrieval floor
  - `data.prepare()` derives the major group without zero-padding
- Run the suite after implementation. Fix failures before continuing.

## 11. Git and version control

- Small commits, one logical change each.
- Imperative commit messages: `fix OIICS major group derivation`, not `fixed stuff`.
- Never commit `data/raw/`, `out/*.joblib`, `.env`, or `__pycache__`.
- Do not commit a change that leaves the test suite failing.

## 12. Documentation

- Update MEMORY.md when project state changes.
- Add an ADR to DECISIONS.md for any architectural decision — do not bury it in a commit message.
- Update TASKS.md when a task completes.
- **If results change, update `results.md` in the same commit.** Stale numbers in documentation are
  worse than no numbers.

## 13. AI collaboration guide

When working with an AI assistant on this project:

**Give it context first.** Before asking for code:

> Read PRD.md, ARCHITECTURE.md, DESIGN.md, RULES.md and TASKS.md. Do not modify anything yet.
> Understand the product, architecture, design system, rules and current tasks. Identify missing
> information. Then explain the implementation plan for TASK-XXX. Do not write code yet.

**Then work one task at a time:**

```
TASK-001 → implement → test → review → mark complete → TASK-002
```

**Rules for the assistant:**

- Implement by task ID, never by loose description.
- Do not reverse a DECISIONS.md entry without proposing a new ADR.
- Do not add a dependency without justification.
- Do not change the technology stack without approval.
- Do not delete existing functionality to implement a new feature.
- Do not mark a task complete without running it.
- **When uncertain, ask. Do not guess and proceed.**

## 14. What not to do

- ❌ Generate regulation text under any circumstance
- ❌ Remove abstention to improve a demo
- ❌ Report accuracy without a baseline
- ❌ Report a metric for a class with almost no examples
- ❌ Predict severity on this dataset
- ❌ Hard-code a threshold outside `config.py`
- ❌ Commit the dataset, the models, or `.env`
- ❌ Claim a component is built when it is specified — see `agent_logic.md`
- ❌ Quietly update a number in a slide without updating `results.md`

## 15. Definition of done

A task is done when **all** of these hold:

- [ ] It runs end to end on the real dataset
- [ ] Tests exist for the happy path, the abstention path and the failure path
- [ ] The full suite passes
- [ ] No hard-coded values outside `config.py`
- [ ] Docstrings explain why, not what
- [ ] `results.md` updated if any number changed
- [ ] MEMORY.md and TASKS.md updated
- [ ] An ADR added if an architectural decision was made
- [ ] **It has actually been executed** — not assumed to work

## 16. Revision history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-09-20 | Initial rulebook. Supersedes `context.md`. |
