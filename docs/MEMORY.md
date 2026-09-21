# Project Memory

**Current project state.** Update this whenever state changes.
For permanent decisions see DECISIONS.md — decisions are permanent, state is not.

**Last updated:** 2026-09-20 (Phase 1 complete)

---

## Current status

**v1 complete. Phase 1 (the agent layer) complete.** Both classifiers trained on the full
86,204-record corpus, retrieval over 170 cached OSHA sections with a routing requirement and a
known-gap map, abstention enforced on both halves, a runnable agent, 15 passing refusal tests.

Not built: the hosted agent on IBM watsonx. It needs an account, not code — Phase 1b.

## Completed

- Data loading with encoding fallback and column validation
- Two label granularities derived from the OIICS event code
- Major-group classifier — accuracy 0.938, macro F1 0.832
- Fine-grained classifier — accuracy 0.668, macro F1 0.585
- Dummy baselines reported beside every metric
- Per-class analysis, best and worst
- 29 CFR 1910 fetched and cached — 170 sections
- Retrieval with title weighting, hazard boost and a floor
- Similar-incident search
- Abstention on classifier margin and retrieval score
- CLI: `train`, `demo`, `analyse`, `failures`
- Full document set: PRD, ARCHITECTURE, DESIGN, RULES, DECISIONS, TASKS, MEMORY
- assistant specification (`agent_logic.md`)
- 14-slide presentation deck, PPTX and PDF

**Phase 1, 2026-09-20:**

- `src/service.py` — load-once service with machine-readable `status` / `standards_status`
- `src/assistant_tools.py` — three tools with JSON schemas and a dispatcher
- `docs/assistant_system_prompt.md` — the prompt, six rules
- `src/agent.py` — the decision flow, deterministic; `python main.py bob`
- `tests/test_refusals.py` — 15 tests, every refusal rule asserted
- `docs/assistant_transcript.md` — generated, not hand-written
- Known-gap map and routing requirement (ADR-011, ADR-012)

## The finding worth keeping from Phase 1

Asked for lockout/tagout **by number**, the system returns 30,924 characters of 1910.147 instantly.
Asked to *find* it from "cleaning a running conveyor", it ranks it **77th of 170**.

The corpus has the right answer. TF-IDF cannot reach it, because 1910.147 is written in
"energy isolating device" and "servicing and maintenance" while the narrative says "cleaning",
"rollers" and "fingers" — near-zero lexical overlap. This is the concrete, measured case for
sentence-transformer embeddings in TASK-302, and it is worth more than a generic statement that
embeddings might help.

## Current task

**None.** v1 is closed. Next work begins at TASK-100 (Phase 1, the SafetyLens assistant).

## Known issues

1. **Retrieval has no ground truth.** `results.md` reports no accuracy figure for it, by design. The
   fix is TASK-300, not a number.

3. **Heat cases have no correct answer.** There is no federal OSHA heat standard — heat illness is
   enforced under the General Duty Clause. The system returns a weak match rather than saying no
   section applies. Observed live: a heat-exhaustion narrative retrieves *1910.138 Hand protection*
   at 0.085 — noise clearing the 0.08 floor. TASK-304.

3. **`Nonclassifiable` recall is 0.22.** Only 157 test examples and the class is a junk drawer by
   construction. Not worth fixing; worth reporting.

4. **The hosted watsonx agent is not built.** Everything it needs is (ADR-013). Phase 1b — needs an account, not code.

5. **No test suite yet.** `tests/` exists and is empty. RULES.md §10 specifies what it must contain.

## Next step

Retrieval on the third (unseen) set: **recall@3 0.600**, recall@1 0.400, MRR 0.483, after latent
semantic retrieval (ADR-018). **All three evaluation sets are now spent.**

Next is **TASK-307** — run `python main.py review`, 15 of the 50, as second labeller. It takes about
fifteen minutes and it is the only thing standing between "0.364 against an AI-labelled set" and
"0.364, agreement with a second reviewer X%". Everything else in Phase 3 is improvement work;
this is the one that shores up the number already reported.

Then TASK-308 (index scope text — 1910.22 and 1910.212 are invisible to title routing) and TASK-310
(a second held-out 50, before any improvement is claimed).

Phase 1b (wiring the hosted agent) needs an IBM account, not code.

## Verification log

| Date | Check | Result |
|---|---|---|
| 2026-09-20 | Retrained on corrected labels (post-ADR-007) | major 0.938 / 0.832 · fine 0.668 / 0.585 |
| 2026-09-20 | `demo` — all five cases | Correct. Heat now classifies as *Exposure*, previously *Nonclassifiable* |
| 2026-09-20 | Abstention on a vague narrative | Refused at margin 0.236 |
| 2026-09-20 | Reproduced on a second machine, seed 42 | Identical to the digit |
| 2026-09-20 | **Heat case retrieval** | **DEFECT.** Returned *1910.138 Hand protection* at 0.0845 vs floor 0.08, and shipped it. Docs claimed the opposite |
| 2026-09-20 | Can a higher floor fix it? | **No.** Correct crane retrieval also scores 0.085. Measured, not assumed |
| 2026-09-20 | Fix: known-gap map + routing requirement | Heat and violence now report the General Duty Clause (ADR-011, ADR-012) |
| 2026-09-20 | Keyword matcher, substring → prefix + span dedupe | Conveyor now returns 1910.219 alone; *Laundry*/*Woodworking* gone |
| 2026-09-20 | Crane regression from strict word boundaries | Caught by the regression set. Plurals broke `crane` → *cranes* |
| 2026-09-20 | 1910.147 (lockout/tagout) rank on a cleaning-a-running-machine narrative | **77th of 170**, raw 0.0113. The vocabulary gap TF-IDF cannot cross |
| 2026-09-20 | `tests/test_refusals.py` | 15/15 passing |
| 2026-09-20 | *"Are we going to be cited for that?"* | **DEFECT.** Classified as an incident, cited 1910.219. Rule 5 breach, now tested |
| 2026-09-20 | `python main.py transcript` — 5 turns | All branches correct. `docs/assistant_transcript.md` |
| 2026-09-20 | Third known gap: overexertion | **No OSHA ergonomics standard** — rescinded by Congress 2001, OSHA barred from reissuing. osha.gov/ergonomics/faqs |
| 2026-09-20 | TASK-300 — 50 labelled, protocol frozen first | 33 scorable · 10 none-exists · 2 out-of-scope (Part 1926) · 5 uncertain |
| 2026-09-20 | **TASK-301 — retrieval baseline** | **recall@3 0.364** (0.212 always-1910.212, 0.000 random). Correct silence **1.000** |
| 2026-09-20 | Per-group retrieval | Transportation **1.000**, Fires **0.000**. Cause: generic titles and procedural standards |
| 2026-09-20 | Second-labeller review | **NOT RUN.** No agreement figure exists — TASK-307 |
| 2026-09-20 | TASK-309 cache 29 CFR 1926 | **BLOCKED** — ecfr.gov denied by network policy in both workspaces |
| 2026-09-20 | TASK-310 held-out 50 built and labelled | 31 scorable · 13 none-exists · 1 out-of-scope · 5 uncertain. Disjoint verified |
| 2026-09-20 | TASK-308 scope routing, dev | recall@3 0.364 → **0.424**, returned-nothing 0.333 → 0.212 |
| 2026-09-20 | **TASK-308 scope routing, HELD-OUT** | recall@3 **0.484 → 0.484 — unchanged.** The dev gain was noise |
| 2026-09-20 | What did replicate | returned-nothing 0.194 → **0.065** held-out, 0.333 → 0.212 dev. Change kept for coverage, not recall |
| 2026-09-20 | Cost of the change | 1910.138 re-admitted via "skin absorption of harmful substances"; held-out Exposure recall 0.000 |
| 2026-09-20 | 1910.147 misses | 4 in dev, 4 in held-out, never retrieved. Replicated — the case for TASK-302 |
| 2026-09-20 | huggingface.co | **BLOCKED** by policy in both workspaces — no pretrained embeddings |
| 2026-09-20 | TASK-302a latent semantic retrieval (SVD, no download) | Explained variance 0.459 over 300 components |
| 2026-09-20 | LSA on **dev** | recall@1 0.394 → **0.303** (worse), recall@3 0.424 → 0.485 |
| 2026-09-20 | Third set built and labelled | 30 scorable · 9 none-exists · 9 uncertain · 2 out-of-scope. Disjoint from both |
| 2026-09-20 | **LSA on SET 3 (unseen)** | recall@1 0.267 → **0.400**, recall@3 0.500 → **0.600**, MRR 0.367 → **0.483** |
| 2026-09-20 | 1910.147 after LSA | **Retrieved.** Zero times across the first two sets, now returned for all three cleaning/servicing cases |
| 2026-09-20 | Lexical-lead variant | **REJECTED** — lost on every dev metric. Recorded in ADR-018 |
| 2026-09-20 | **Blend scale mismatch (ADR-019)** | lexical spans 0.00-0.08, latent 0.50-0.68. "50/50" is latent-dominated; **RETRIEVAL_FLOOR is inert** |
| 2026-09-20 | Min-max normalising before blending | **WORSE** — crane top hit becomes 1910.30 Training requirements. Rejected |
| 2026-09-20 | Score presentation | Agent now states rank, not score; `lexical_score` carried through; 16th test asserts it |
| 2026-09-20 | Cost of ADR-018, concretely | Crane demo case lost 1910.179, which lexical-only got right |
| 2026-09-20 | **TASK-200 Indian narratives** | **RESOLVED: none published.** Form 18 is mandatory and free-text but filed to state inspectorates; data.gov.in publishes counts only |
| 2026-09-20 | dgfasli.gov.in | Blocked by network policy — DGFASLI PDFs need a browser download |
| 2026-09-20 | Phase 2 | Closed as a finding (ADR-020), replaced by TASK-210..212 |
| 2026-09-20 | TASK-110 `serve.py` + `openapi.json` | Smoke-tested; refusal states survive the HTTP boundary |
| 2026-09-20 | Fourth eval set built and labelled | 30 scorable · 12 none-exists · 8 uncertain |
| 2026-09-20 | TASK-313 sigma floor, set 4 | **−6.6 pts recall@3** to gain declining in 2 of 30. **Reverted** |
| 2026-09-20 | TASK-312a admin sections dropped | **SHIPPED** — dev recall@1 0.303 → 0.333; provably cannot hurt recall |
| 2026-09-20 | TASK-312b PPE scope exclusion | **REVERTED** — −3 pts recall@3; PPE sections are sometimes the correct answer |
| 2026-09-20 | TASK-311 roadway known gap | **Not implementable** — all 28 roadway events below the 150 threshold |
| 2026-09-20 | Methodological error | Measured three changes as a bundle on set 4; result uninterpretable. Ablated on dev after |
| 2026-09-20 | Streamlit UI (DESIGN.md Part 2) | **BUILT** — `app.py`, `tests/test_ui.py` 5/5 |
| 2026-09-20 | Multi-label, measured before building | Only **6.5%** of incidents have top-2 margin < 1.0; median 2.458. Deferred on the evidence |
| 2026-09-20 | `regulations.py` generalised to any CFR Part | `main.py add-part 1926 <xml>`; tested, incl. refusing to cache an empty parse |
| 2026-09-20 | Near-miss corpus search | **None public for general industry.** NASA ASRS is public and narrative but aviation — logged as the honest next experiment |
| 2026-09-20 | RTI application drafted | `docs/rti_application_draft.md` — redaction request built in against s.8(1)(j) |
| 2026-09-20 | Hosted-agent scenarios written | `docs/assistant_test_scenarios.md` — 10 cases for TASK-113 |
| 2026-09-20 | `HANDOFF.md` written | Single list of everything needing Bhargav |
| 2026-09-21 | **TASK-315 roadway collapse** | 28 labels → 1 class, 381 records. Retrained. Headline metrics unmoved; roadway class F1 **0.518** |
| 2026-09-21 | Roadway gap verified end to end | 3 roadway cases → General Duty Clause; 4 controls unchanged. **H029 fixed** |
| 2026-09-21 | Local workspace RAM | **2.9 GB — kills training partway.** Trained in the cloud container (8 GB); models returned compressed + split, SHA-256 verified |
| 2026-09-21 | `model.save` now compresses | zlib 9 — fine classifier 68 MB → 29 MB |
| 2026-09-21 | Post-retrain churn | recall@3: held-out 0.484→0.548, fourth 0.567→0.633, third 0.600→0.567. Silence 42/44 → 41/44 |
| 2026-09-21 | New gap candidates, NOT acted on | H027 UTV rollover, H046 combustible dust (no OSHA standard). TASK-316/317 |
| 2026-09-21 | All data hosts re-tested | ecfr/govinfo/asrs/dgfasli/huggingface **blocked** in cloud AND device; no Chrome connected |
| 2026-09-21 | **CORPUS POISONING INCIDENT** | A test fixture left in `data/` was merged into the index and **served as 29 CFR 1926.501 under "quoted from eCFR, not generated"**. Fixed: provenance required (ADR-025) |
| 2026-09-21 | Self-consistency relabel, 15 dev cases | **15/15 identical — INVALID.** Same labeller, same session; measures memory, not reliability. Recorded so it is not mistaken for validation |
| 2026-09-21 | Telangana RTI | **Online filing exists** — rti.telangana.gov.in, 114 authorities, UPI payment |
| 2026-09-20 | `access-hyd/` | Archived to `../archive/access-hyd/` with a README explaining the null result |

## Environment notes

- Reproduced identically on two machines with seed 42
- Training takes 4–6 minutes for both models on CPU
- `data/standards.json` is cached; eCFR is only contacted on first run
- The OSHA CSV is Windows-1252 — see RULES.md §6
