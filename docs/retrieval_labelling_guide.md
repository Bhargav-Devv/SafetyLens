# Retrieval labelling guide

**Version 1.0 — FROZEN once labelling begins (2026-09-20).**

*Amended once, before the first label was written, to add the `out_of_scope` verdict and four §8
rules discovered while reading the sample. Nothing had been labelled, so no relabelling was needed.
Every amendment after the first label requires a version bump and a relabel — that is the whole
point of freezing it.*

`results.md` has never reported an accuracy figure for retrieval, because no ground truth existed.
This guide creates it. Everything below is decided *before* any label is assigned, because a rule
invented halfway through labelling quietly invalidates every label that came before it, and nothing
in the output will show that it happened.

---

## 1. What is being labelled

For each of 50 sampled incident narratives: **which section of 29 CFR Part 1910 states the
requirement that most directly addresses the hazard that produced this injury?**

Not "which section mentions this equipment". Not "which section the employer was cited under" — that
is unknowable from the narrative and is a compliance determination, which this project refuses to
make anywhere else. The question is which rule, had it been followed, addresses the mechanism of
injury described.

## 2. The label

| Field | Meaning |
|---|---|
| `primary` | The one section that most directly addresses the hazard. Exactly one, or `null`. |
| `acceptable` | Other sections a competent safety officer could reasonably cite instead. May be empty. |
| `verdict` | `section` · `none_exists` · `uncertain` |
| `reasoning` | One sentence. Why this section and not a neighbour. |
| `labeller` | Who assigned it. |
| `guide_version` | `1.0` |

**`acceptable` exists because the question often has more than one defensible answer.** A worker
whose hand enters a running machine during cleaning is covered by both 1910.147 (lockout/tagout, the
energy control failure) and 1910.212 (machine guarding, the missing guard). Forcing a single answer
would measure agreement with one labeller's preference rather than whether the system found a
relevant rule. Metrics credit a hit on `primary` **or** any `acceptable`, and `primary`-only recall
is reported separately.

## 3. The four verdicts

**`section`** — a substantive standard applies. Give `primary`.

**`none_exists`** — no 29 CFR 1910 standard addresses this hazard; the General Duty Clause §5(a)(1)
governs. Environmental heat and workplace violence are the documented cases (ADR-011). These are
scored separately: the system is correct here when it retrieves **nothing**, so including them in
recall@k would reward the wrong behaviour.

**`out_of_scope`** — a standard exists, but not in 29 CFR Part 1910. 1910.12 assigns construction
work to **Part 1926**, which this corpus does not contain; agriculture sits in Part 1928. A roofing
fall or a highway work-zone incident is governed by a real standard the system has never been given.

This is **not** the same as `none_exists`, and collapsing the two would hide the more interesting
finding. `none_exists` says the law is silent. `out_of_scope` says *the corpus is incomplete* — a
property of this build, fixable by caching Part 1926, and a live limitation of a system trained on a
dataset that contains a great deal of construction work. Scored separately from recall.

**`uncertain`** — the narrative is too thin to identify a hazard mechanism, or the correct section is
genuinely unclear. **Excluded from every metric, and the count is reported.** Quietly guessing on
these would inflate the denominator with noise and make the figure look better than it is.

## 4. The rule that makes the measurement mean anything

> **The label is assigned without looking at what the retriever returned.**

Read the narrative. Decide what regulatory subject it belongs to. *Then* find that subject in the
list of 170 section titles. Only after the label is written is retrieval output consulted.

If labels were drawn from the retriever's candidate list, the correct answer would be in that list by
construction and recall@k would be 1.0 by definition — a number that measures nothing. This is the
single easiest way to produce a meaningless evaluation, and it is easy to do by accident.

## 5. Sections that can never be the answer

Roughly twenty of the 170 cached sections are administrative rather than substantive:

> Purpose and scope · Definitions · Applicability · Effective dates · Amendments · Incorporation by
> reference · Petitions · Table of contents · Severability · Scope and application · Recordkeeping ·
> Access to employee exposure and medical records · Introduction

They state no requirement about any hazard. They are never a valid `primary` or `acceptable`, and a
retrieval that returns one is a miss. That they sit in the index at all is itself a finding — see
`results.md`.

## 6. Provenance, stated rather than implied

**These labels are assigned by an AI assistant reading the regulation text, not by a certified safety
professional.** That is a real limitation and it goes in `limitations.md` and in the deck, not in a
footnote nobody reads.

What makes them worth having anyway:

1. They are assigned from the **actual section text**, not from memory of OSHA.
2. They are assigned **independently of the retriever** (§4), so the measurement is not circular.
3. The protocol was **frozen before labelling** (this file).
4. Every label carries its reasoning, so any of them can be disputed by a reader.
5. A second labeller reviews a subset and **agreement is reported** (§7).

A figure derived this way is described as *"retrieval accuracy against an AI-labelled reference set,
agreement with a second reviewer X%"* — never as *"retrieval accuracy"* unqualified. Validation by a
practising safety professional remains in the backlog and remains necessary.

## 7. Agreement

A second labeller independently reviews **15 of the 50** (`python main.py review`) and records agree
or disagree with `primary`. The agreement rate is reported with its sample size.

Below ~70% agreement the guide is ambiguous rather than the reviewer being wrong: find the
disagreements, add them to §8 as decided rules, bump the version, and relabel.

## 8. Decided in advance

| Situation | Rule |
|---|---|
| Machine guarding **and** lockout/tagout both apply | `primary` is the one matching the described failure. Cleaning or servicing a live machine → 1910.147. Contact with an unguarded moving part in normal operation → 1910.212. The other goes in `acceptable`. |
| A specific industry section exists (1910.263 Bakery, 1910.265 Sawmills) | The industry section is `primary` **only if** the narrative names that industry. Otherwise the general section is. |
| Fall from a ladder | 1910.23 Ladders is `primary`; 1910.28 is `acceptable`. |
| Fall from a roof, platform or edge | 1910.28 is `primary`; 1910.29 and 1910.140 are `acceptable`. |
| Struck by a falling object | 1910.28 (falling object protection) unless a specific lifting section applies. |
| Construction work — roofing, formwork, highway work zones, excavation | `out_of_scope`. 1910.12 assigns it to Part 1926, which is not cached. |
| Agricultural operations, livestock | `out_of_scope` (Part 1928) or `none_exists` for animal contact. |
| Vehicle incident on a public road | `none_exists` — 29 CFR 1910 does not govern public highways. |
| Hydraulic or pneumatic press | **1910.212**, not 1910.217 — 1910.217(a)(5) excludes hydraulic and pneumatic presses from the mechanical power press standard. |
| Arboriculture / tree care | `uncertain`. 1910.266 covers logging and explicitly excludes tree-care operations; no section replaces it. |
| Forklift, powered truck | 1910.178. |
| Crane, hoist, sling, rigging | 1910.179 / 1910.180 / 1910.184 by equipment named. |
| PPE was absent | PPE sections (1910.132–1910.138) are `acceptable`, rarely `primary`. The hazard that required the PPE is `primary`. |
| Electrical contact | 1910.333 for work practices; 1910.303–305 for installation defects. |
| Chemical exposure | The substance-specific section if one exists; otherwise 1910.1200 or 1910.1000. |
| Slip or trip on the same level | 1910.22 General requirements (walking-working surfaces). |
| Overexertion, lifting, repetitive strain | `none_exists` — **OSHA has no ergonomics standard.** The 2000 rule was repealed by Congress in 2001. |
| Heat, cold, environmental exposure | `none_exists` (ADR-011). |
| Assault, animal | `none_exists` (ADR-011). |
| Narrative names no mechanism at all | `uncertain`. |
