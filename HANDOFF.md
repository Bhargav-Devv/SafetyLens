# Handoff — what needs you

This file preserves the manual handoff history. TASK-113, TASK-307 and TASK-309 below were completed
after the original handoff was written. Current implementation order is in `DEVELOPMENT_PLAN.md`.

Current verified state, 2026-10-08: full suite **37/37 passing**; direct watsonx live scenarios
completed; second review completed; authoritative Part 1926 corpus imported.

---

## 1. Review — completed  ·  TASK-307

Completed by Bhargav: **15/15 agreement (100%)**, saved in
`data/retrieval_eval_review.json`. This is not validation by a practising safety professional.

The earlier same-labeller self-consistency attempt remains documented as invalid. The later Bhargav
review is the TASK-307 result; professional validation remains open.

---

## 2. SafetyLens assistant — completed  ·  TASK-111, 112, 113

The direct watsonx path superseded the Orchestrate deployment. Ten live scenarios were completed on
2026-10-08; see `docs/assistant_live_results.md` and ADR-029.

⚠ `serve.py` has no authentication. Put a gateway in front of it or keep the URL private.

---

## 3. Remaining browser download

I re-tested every route before writing this: `ecfr.gov`, `govinfo.gov`, `asrs.arc.nasa.gov`,
`dgfasli.gov.in` and `huggingface.co` are **all denied by network policy in both the cloud workspace
and the one on your laptop**, and no Chrome is connected for browser automation. I deliberately did
not use the web-fetch tool to reconstruct the corpus: that routes authoritative regulation text
through a summarising model, which is the one thing ADR-001 forbids outright.

The remaining DGFASLI source is blocked here by network policy, not by missing parser code.

### 29 CFR 1926 — construction — completed  ·  TASK-309

```
https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/title-29.xml?part=1926
```

The authoritative XML was downloaded and imported. The provenance cache records 230 sections and
the source SHA-256. The historical command was:

```bash
python main.py add-part 1926 path/to/the-file.xml
```

It was parsed, validated and merged into the index. The older evaluation labels remain historical;
their `out_of_scope` verdicts describe the corpus that existed when those sets were frozen.

### DGFASLI Model Factories Rules  ·  TASK-212

```
https://dgfasli.gov.in/public/Admin/Cms/AllPdf/Model_Factories_Rules_as_on_15_12_2020.pdf
```

Drop it in `data/raw/` and tell me — this one is a PDF, so it needs an extraction step I have not
written blind. Worth doing even though the Indian *narratives* are unobtainable: it demonstrates the
retrieval half ports to another jurisdiction while the classifier half waits for data.

---

## 4. File the RTI request  ·  TASK-210

`docs/rti_application_draft.md` is written and ready — addressed, worded to survive the three usual
grounds for refusal, with the redaction request built in so Section 8(1)(j) cannot be used against
it. Fill in the bracketed fields, enclose ₹10, send.

**Every outcome is reportable**, including a refusal. The project's claim is about disclosure policy,
so a refusal letter is evidence *for* the argument rather than an obstacle to it. The draft has a
table of what each possible answer means.

---

## 5. Find a safety professional  ·  backlog

One conversation with a practising safety officer, walking through ten real outputs, would be worth
more than another thousand labelled incidents. It is the only way `docs/limitations.md` stops having
to say the labels are mine.

---

## Deliberately not done, with reasons

| | Why |
|---|---|
| **TASK-316** — UTV gap candidate | Resolved without code (ADR-031): the emitted rollover label is much broader than UTVs and cannot safely key a known gap |
| **TASK-317** — combustible dust candidate | Still open. Any behavior change needs new untouched evidence because all five sets are spent |
| **Multi-label events** | Measured first: only **6.5%** of incidents have a top-two group margin below 1.0, median 2.458, and the worst 1.3% are already abstained on. Real but narrow. `docs/results.md` |
| **TASK-302b** — sentence embeddings | Completed as a negative experiment (ADR-030). MiniLM gained one top-three hit but weakened lead and primary-only recall, tripled warm-up, and was not adopted |
| **Further retrieval changes** | All five sets are spent. TASK-316 and TASK-317 need new untouched evidence |

---

## If you only do one thing

Run `python main.py review`. Everything else on this page can wait; that one changes what the project
is allowed to claim.
