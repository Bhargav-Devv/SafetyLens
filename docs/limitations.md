# Limitations

Stated here so they appear in the presentation rather than in a reviewer's question.

## 1. Severity is not predicted

Every record in the Severe Injury Reports database is already severe by definition - it qualified for
mandatory reporting through hospitalisation or amputation. The outcome variable barely varies, so
predicting it would produce a number with no meaning.

An earlier version of this project proposed severity prediction. It was removed once the data was
examined. **Checking what the label actually contains, before building on it, is the single most
useful habit in applied machine learning.**

## 1b. Where the law is silent - fixed, and how it was found

**This was a real defect, found on 2026-09-20 while building the the assistant tool layer, and it is recorded
here rather than quietly patched.**

A heat-exhaustion narrative retrieved **29 CFR 1910.138, Hand protection**, and presented it as the
applicable standard. The section's body mentions temperature extremes in the context of gloves, which
was enough lexical overlap to score 0.0845 against a floor of 0.08. It shipped in `out/demo.json`.

The instinct is to raise the floor. The measurement says that cannot work:

| incident | top section | score | correct? |
|---|---|---|---|
| conveyor amputation | 1910.219 Mechanical power-transmission | 0.159 | yes |
| roof fall | 1910.28 Fall protection | 0.207 | yes |
| crane struck-by | 1910.179 Overhead and gantry cranes | **0.085** | yes |
| heat exhaustion | 1910.138 Hand protection | **0.085** | **no** |

A true positive and a false positive land on the same number. **No threshold separates them**, and
tuning one until the demo looked clean would have been exactly the failure this project is built to
avoid. Two principled fixes were applied instead:

1. **A routing requirement** (`REQUIRE_HAZARD_ROUTING`). A section is a candidate only when the
   predicted hazard's vocabulary appears in its **title**. Bodies run to ~10,000 characters, so a
   narrative finds purchase in almost any of them; the title is what identifies the subject. This
   makes retrieval *confirm* the classification instead of wandering away from it - which is what
   `retrieval.py` always claimed in its docstring but did not enforce.

2. **A known-gap map** (`NO_SPECIFIC_STANDARD_GROUPS` / `_EVENTS`). Two of the eight hazard groups
   have no standard to retrieve because none was ever written:

   | hazard | authority | source |
   |---|---|---|
   | Exposure to environmental heat | General Duty Clause §5(a)(1) | Aug 2024 proposed rule unfinalised, no target date |
   | Violence / injury by persons or animals | General Duty Clause §5(a)(1) | osha.gov: *"There are currently no specific OSHA standards for workplace violence."* |

   Both checked against primary sources on 2026-09-20. For these, the system states that no standard
   exists and names the authority that does apply, **before the index is consulted at all**.

That the two groups with no keyword vocabulary turned out to be exactly the two with no governing
standard is not a coincidence - it is the same gap showing up twice.

**Residual limitation.** Sections ranked second and third are frequently weak. A conveyor amputation
still returns *Laundry machinery* and *Woodworking machinery* below the correct match, because both
titles contain "machinery". They are shown with their scores (0.082 and 0.081, against 0.159 for the
correct section), and the assistant presents only the top section as applicable. Suppressing them properly
needs §2.

## 2. Retrieval finds the right section about a third of the time

Measured 2026-09-20 against three labelled sets. The current system, on the third set (30 scorable
cases, never used to make a decision): **recall@3 = 0.600**, recall@1 0.400, and it returns nothing
in 6.7% of cases where a section does exist. The best single fixed answer scores 0.167.

**Sets of thirty disagree with each other.** The same system scored recall@3 0.424 on dev and 0.484
on held-out; latent retrieval *lowered* dev recall@1 while raising it thirteen points on unseen data.
That disagreement is the most useful thing to know about how much weight any of these numbers
carries.

That is a weak number and it is the honest one. Three things make it worth reporting rather than
burying:

- **Correct silence is 1.000.** Where no standard exists, it says so every time.
- **The failures are legible, not random.** Sections with generic titles (1910.22 *General
  requirements*, 1910.212 *General requirements for all machines*) are invisible to title-based
  routing; procedural standards like 1910.147 lose to equipment-named ones. Transportation scores
  1.000 because "forklift" and "Powered industrial trucks" are the same object.
- **It predicted the fix, and the fix worked.** Scope-text indexing for the generic titles
  (ADR-016), and latent semantic retrieval for the vocabulary gap (ADR-018) - the latter worth +13
  points of recall@1 on unseen data.

**The labels are the weak link, and it is named rather than buried.** They were assigned by an AI
assistant reading the regulation text - not by a certified safety professional. The protocol was
frozen first and labels were assigned without seeing retriever output
(`docs/retrieval_labelling_guide.md`), which removes circularity but not the provenance problem.
`python main.py review` produces a second-labeller agreement figure; **it has not been run, so no
agreement figure exists yet.**

**A self-consistency check was attempted and is reported as invalid.** On 2026-09-21 the first
fifteen dev incidents were re-labelled from the narratives alone and compared with the originals:
**15 out of 15 identical.** That number is worthless, and it is recorded here so it cannot be
mistaken for validation. The same labeller, in the same session, having written the originals hours
earlier, cannot be blind to them - the test measures recall of a previous decision, not the
reliability of the procedure that produced it. A self-agreement figure from one annotator is not
evidence, and a *perfect* one is a warning that the experiment had no power rather than a sign that
the labels are good.

The check that would mean something needs a genuinely independent labeller. That is still TASK-307.

**One improvement has already been caught this way.** Scope routing (ADR-016) raised dev recall@3
from 0.364 to 0.424 - a clean 6-point gain. On the held-out set recall was **identical before and
after**. The gain was noise, and without the second set it would have been reported as a result. What
did replicate was coverage: returned-nothing fell from 0.194 to 0.065 held-out.

**All four sets are now spent** - the first was tuned against, the second and third have each had
their one measurement. Two further findings (a public-road known gap, and an over-coarse Exposure
keyword list) are deliberately left unfixed for that reason; see ADR-017.

## 1c. The corpus was poisoned once, by a test

On 2026-09-21 a unit-test fixture left in `data/` was merged into the retrieval index and returned to
a user as **29 CFR 1926.501**, quoted verbatim beneath the line *"quoted from eCFR, not generated"*.
The text was invented. Every guard held and every guard was quoting a lie, because they all trusted
the corpus — including the strongest test in the suite, which verifies that each quote is a genuine
substring of the cached text. It was.

Fixed by requiring a provenance block on every cached Part, refusing any cache without one, and
moving the test out of `data/` entirely. Three regression tests now cover it, including one asserting
no section in the live index lies outside Part 1910. See ADR-025.

**Stated here rather than quietly patched** because it is the most serious thing that has gone wrong
in this project, and because the lesson is general: an integrity check that compares an output to a
source cannot tell you the source is real.

## 2a. The retrieval floor is currently inert

`RETRIEVAL_FLOOR` was calibrated against raw TF-IDF cosine scores, which span 0.00-0.08. Since latent
retrieval was enabled the ranking score is a blend spanning 0.25-0.33, so **every result clears the
floor** and the "no section matched" path has effectively stopped firing (ADR-019).

The abstention that matters for a user is unaffected: a hazard with **no standard at all** is
answered before the index is consulted, and correct silence is unchanged. What is lost is the weaker
guard - "a standard exists but nothing scored well enough" - and part of the improved coverage figure
in §2 is that guard being bypassed rather than retrieval genuinely finding more.

Reported ranking scores are likewise no longer interpretable as match quality. The agent states rank
rather than score, and `lexical_score` is carried alongside so a calibrated number still reaches any
caller. Recalibrating the floor needs a fourth labelled set - TASK-313.

## 2b. The corpus is general industry only

29 CFR **1926** (construction) and **1928** (agriculture) are not cached. Two of the 50 sampled
incidents - a residential roof tear-off and a highway-work-zone flagger - are governed by real
standards the system has never been given, and the OSHA severe-injury dataset contains a great deal
of construction work. They are scored as `out_of_scope` rather than as retrieval failures, because
the failure is corpus coverage, not ranking.

## 3. The worst classes reflect the coding scheme

"Unspecified" and "n.e.c." categories cannot be learned because they are defined by exclusion. This
limits fine-grained performance in a way no model change will fix.

## 4. US data, US regulations - and the port to India is blocked by disclosure, not by method

The dataset is OSHA; the corpus is 29 CFR.

**TASK-200 tested whether this ports to India and the answer is no, for a reason worth stating.**
Form 18 under the Factories Act 1948 requires a free-text description of every reportable accident
and its causes, filed within four hours for a fatality. Those filings go to state Inspectorates of
Factories and are **published nowhere**. India publishes *"Industrial Injuries in Factories"* -
aggregate counts by state and year, no records, no text.

The method transfers. The artefacts do not exist in public form. See `docs/findings_indian_data.md`
and ADR-020.

This is the second time the project has hit the same wall: the archived AccessHyd work died because
Indian accessibility data is published as aggregates while the underlying records are withheld.

## 5. Narratives are employer-written

Each report is written after the fact by the party with an interest in how it reads. Systematic
under-description of employer fault is plausible and unmeasured.

## 6. Reporting bias

Only injuries meeting the reporting threshold appear. Near-misses - the richest source of preventive
signal - are absent entirely.

## 7. Decision support only

The output tells a human where to look. It is not a compliance determination, not a legal opinion,
and not a substitute for a safety professional.

## 8. The agent runs; the hosted model does not

Built and tested: the tool contract with schemas, the system prompt, a deterministic implementation
of the decision flow (`python main.py bob`), and fifteen tests asserting the refusal rules.

Not built: the assistant itself - a language model on IBM watsonx given those schemas and that prompt. No code
change is needed for it; it needs an account.

`src/agent.py` routes on regular expressions, not language understanding. It will mishandle phrasings
a language model would read easily. It is the reference the hosted agent gets checked against, and
the reason the refusal rules are assertions rather than hopes. See ADR-013.

## 9. Not co-designed with workers

The system was designed without input from the safety officers or workers it describes. Any real
deployment would need that first.
