# Product Requirements Document

**SafetyLens** · Bhargav Rao Mahankali · St Peter's Engineering College
1M1B × IBM SkillsBuild — AI for Sustainability Virtual Internship, 2026

*PRD = WHAT + WHY. For HOW, see ARCHITECTURE.md.*

---

## Product

SafetyLens reads a workplace injury narrative and returns the hazard category, the safety standard
that applies quoted verbatim, and similar incidents that already happened.

## Problem

Severe workplace injuries repeat. The same accident — a worker caught in an unguarded machine, a fall
from an unprotected edge — happens again and again across different employers, for the same reasons.

The reports describing exactly how each one happened already exist: **86,209** of them, filed with
OSHA between January 2015 and September 2023, each a plain-English narrative written by the employer.

**Nobody reads them.**

And even when someone does, knowing what happened is not enough to prevent it. Prevention needs the
specific standard that applies — which lives in thousands of pages of 29 CFR that no floor supervisor
has opened.

Two bodies of knowledge exist. They never meet.

## Target users

**Primary** — the safety officer or site supervisor at a small or mid-size employer. No safety
department, no compliance officer, no in-house counsel. A large manufacturer has staff whose job is
reading regulations; a twelve-person workshop has an owner who also drives the forklift.

**Secondary** — safety researchers and inspectorates who need incident narratives structured at scale.

## Goal

Make the knowledge needed to prevent the next injury reachable in one step, by a person with no
specialist training, without ever fabricating a regulatory requirement.

## Core features

1. **Hazard classification** — narrative → OIICS event category, at two granularities
2. **Regulation retrieval** — the applicable 29 CFR 1910 section, quoted verbatim with its citation
3. **Similar incident search** — has this happened before, and how did it end
4. **Abstention** — refuse to answer when the evidence does not support one
5. **Conversational layer (the SafetyLens assistant)** — tool contract, prompt, decision flow and tests built
   (Phase 1). The hosted watsonx agent is not; see `agent_logic.md` for the exact boundary.

## MVP — what shipped

- [x] Load and validate the OSHA corpus (Windows-1252, column detection)
- [x] Derive two label granularities from the OIICS event code
- [x] Train and evaluate a major-group classifier (8 classes)
- [x] Train and evaluate a fine-grained classifier (76 classes)
- [x] Report both against dummy baselines
- [x] Fetch and cache 29 CFR 1910 from the eCFR API
- [x] Retrieve applicable standards, conditioned on the predicted hazard
- [x] Retrieve similar past incidents
- [x] Abstain on low classifier margin and on low retrieval score
- [x] CLI: `train`, `demo`, `analyse`, `failures`
- [x] Figures and metrics exported for reporting

**Phase 1 — the agent layer (2026-09-20)**

- [x] Load-once service with machine-readable refusal states
- [x] Three tools with JSON schemas, importable by an agent platform
- [x] System prompt carrying all six refusal rules
- [x] Deterministic decision flow — `python main.py bob`
- [x] 15 tests asserting every refusal rule
- [x] Generated transcript covering every branch
- [x] Known-gap map: hazards with no governing standard answer with the General Duty Clause
- [ ] Hosted agent on IBM watsonx — blocked on an account, not on code

## Out of scope (v1)

- Predicting injury **severity** — every record in this dataset is already severe by definition, so
  the outcome barely varies. Removed after inspecting the data. See DECISIONS.md ADR-006.
- Compliance or liability determination
- Any web or mobile interface
- Real-time monitoring or sensor input
- Indian regulatory corpus (planned — TASKS.md Phase 2)

## Success criteria

A user should be able to:

1. Install dependencies and train both models with two commands
2. Paste an incident narrative and receive a hazard category with a confidence margin
3. See the applicable OSHA section **quoted, with its citation**
4. See three similar past incidents from the corpus
5. Receive an explicit refusal when the narrative is too vague to classify
6. Trace any regulatory claim back to its source section

**Measured outcome (achieved):** major-group accuracy **0.938** against a most-frequent baseline of
0.458; fine-grained macro F1 **0.585** against a stratified baseline of 0.013. Full results in
`results.md`.
