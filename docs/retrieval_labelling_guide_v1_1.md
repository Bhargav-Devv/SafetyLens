# Retrieval labelling guide

**Version 1.1 — frozen 2026-10-10 before the fifth sample was drawn or any
TASK-302b retrieval output was inspected.**

This guide inherits version 1.0 in `retrieval_labelling_guide.md` except for the
changes below. Existing labels and historical metrics remain governed by 1.0
and are never rewritten.

## Evaluation question

For each incident, identify the section of **29 CFR Part 1910 or Part 1926**
that most directly addresses the hazard, if the narrative contains enough
information to identify which industry part applies.

Labels must be assigned from the narrative and authoritative cached eCFR text.
The labeller must not inspect output from TF-IDF, LSA, or the sentence
transformer until every label is frozen.

## Industry applicability

Part 1910 governs general industry and Part 1926 governs construction. Similar
hazards often have parallel sections in both parts, so a combined index can
produce textually relevant but legally inapplicable candidates.

Use these rules:

1. If the narrative explicitly describes construction, demolition, roofing,
   excavation, scaffolding, or another construction operation, label the most
   direct Part 1926 section.
2. If it explicitly describes manufacturing, warehousing, healthcare, retail,
   maintenance in a general-industry establishment, or another general-industry
   operation, label the most direct Part 1910 section.
3. If the work context is absent and both parts contain plausible parallel
   duties, use verdict `uncertain`; do not guess the industry from the injury
   mechanism.
4. A section from the other industry part is not `acceptable` merely because
   its wording is similar.
5. `out_of_scope` is reserved for a governing OSHA part that is still absent
   from the corpus, such as Part 1928 agriculture. Part 1926 is no longer
   automatically out of scope.

## Unchanged rules

- `section`, `none_exists`, `out_of_scope`, and `uncertain` remain separate.
- `primary` is one section; `acceptable` contains only independently defensible
  alternatives from the applicable part.
- Administrative sections can never be answers.
- Known federal regulatory gaps are labelled `none_exists`.
- Metrics report recall@1, recall@3, primary-only recall, MRR, returned-nothing,
  correct silence, and per-group results.
- The labels are AI-assigned reference labels, not professional legal or safety
  determinations. A second reviewer must review 15 cases before a new result is
  described as validated.

## Frozen TASK-302b comparison

- Baseline: current TF-IDF plus LSA path exactly as committed before this set.
- Experimental arm: `all-MiniLM-L6-v2`, revision
  `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, CPU, normalized cosine,
  title plus the first 1,200 characters of authoritative section text.
- Both arms use identical hazard/event routing, candidate tiers, floors,
  abstention, and authoritative text rendering.
- The experimental score replaces LSA; it is not blended with LSA or tuned on
  this set.
- The arm is adopted only if it improves retrieval without reducing correct
  silence or weakening the deterministic safety guarantees. A mixed result is
  recorded as a finding rather than tuned against this set.
