# Results

Dataset: **86,209** OSHA Severe Injury Reports (Jan 2015 - Sep 2023), **86,204** usable after
dropping narratives under 25 characters.

## Headline

| Task | Classes | Records | Accuracy | Macro F1 | Weighted F1 |
|---|---|---|---|---|---|
| Major event group | 8 | 86,204 | **0.938** | 0.832 | 0.938 |
| Fine-grained event | 77 | 77,908 | **0.668** | **0.584** | 0.652 |

## Against baselines

| Task | Model macro F1 | Most-frequent | Stratified | Lift |
|---|---|---|---|---|
| Major group | 0.832 | 0.070 | 0.126 | **6.6x** |
| Fine-grained | 0.584 | 0.002 | 0.013 | **45x** |

## Major group, per class

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Contact with objects and equipment | 0.95 | 0.97 | **0.96** | 7,904 |
| Falls, slips, trips | 0.95 | 0.96 | **0.96** | 5,244 |
| Exposure to harmful substances/environments | 0.94 | 0.95 | **0.95** | 1,425 |
| Violence / injury by persons or animals | 0.94 | 0.87 | 0.90 | 415 |
| Fires and explosions | 0.92 | 0.86 | 0.89 | 297 |
| Transportation incidents | 0.86 | 0.83 | 0.85 | 1,513 |
| Overexertion and bodily reaction | 0.83 | 0.81 | 0.82 | 286 |
| Nonclassifiable | 0.79 | 0.22 | 0.34 | 157 |

Macro F1 (0.832) sits well below accuracy (0.938) because of the last row: `Nonclassifiable` has 157
test examples and 0.22 recall. **Reporting accuracy alone would hide that** - which is why both are
reported.

## A bug found in our own label derivation

The first run reported **0.831** accuracy on the major group. That number was wrong, and the cause was
in our code rather than the model.

OIICS event codes are **variable length**: `64`, `531`, `1214`. The major group is the first digit as
written. The original implementation zero-padded to four digits first, turning `531` (exposure to
environmental heat) into `0531` and reading the group as `0` - *Nonclassifiable*.

That single line misfiled **2,192 heat-exposure incidents** and thousands of others into a junk
category, inflating `Nonclassifiable` from 787 records to roughly 24,000.

Fixing it moved accuracy from **0.831 to 0.938**.

The bug surfaced because a demo case looked wrong: a heat-exhaustion narrative was confidently
classified as `Nonclassifiable` while the fine-grained model called it *Exposure to environmental
heat*. **Two models disagreeing was the signal.** Checking why beat trusting the metric.

## The failure pattern

Fine-grained classes ranked by F1. The **best**:

| F1 | n | Class |
|---|---|---|
| 0.98 | 439 | Exposure to environmental heat |
| 0.96 | 47 | Stings and venomous bites |
| 0.96 | 44 | Shooting by other person - intentional |
| 0.95 | 62 | Other animal bites, nonvenomous |
| 0.93 | 124 | Inhalation of harmful substance - single episode |

The **worst**:

| F1 | n | Class |
|---|---|---|
| 0.27 | 67 | Struck against stationary object or equipment, **n.e.c.** |
| 0.23 | 132 | Struck by object or equipment, **unspecified** |
| 0.22 | 248 | Caught in running equipment or machinery, **unspecified** |
| 0.21 | 416 | Caught in or compressed by equipment or objects, **unspecified** |
| 0.21 | 106 | Fall, slip, trip, **unspecified** |
| 0.11 | 203 | Contact with objects and equipment, **unspecified** |
| 0.00 | 40 | Fall onto or against object on same level, **n.e.c.** |

**Eight of the ten worst classes are residual buckets** - "unspecified" or "not elsewhere classified".

These categories are defined by **exclusion rather than content**. No narrative describes an
"unspecified caught-in"; a human coder assigns that label when the text is too vague to place. Such a
class has no linguistic signature to learn.

**The model fails precisely where the human coders could not decide.** That is a finding about the
label scheme, not a weakness of the classifier.

## Retrieval

**170** sections of 29 CFR Part 1910, fetched from the eCFR API.

Plain TF-IDF performed badly. Section bodies average ~10,000 characters, so narrative vocabulary
("sleeve", "rollers") pulled in whichever industry-specific section shared those words. A conveyor
amputation retrieved **bakery equipment, textiles and rubber mills**. Heat exhaustion retrieved
**oxygen and hydrogen**.

Five corrections, all to ranking or candidacy - never to the text returned:

1. **Title weighting** - titles repeated 8x in the indexed document
2. **Hazard boost** - sections whose title matches the predicted hazard vocabulary are boosted
3. **A retrieval floor** - below 0.08 similarity the system reports no match instead of returning its
   three least-bad guesses
4. **A routing requirement** (2026-09-20) - a section is a candidate only when the predicted hazard's
   vocabulary appears in its **title**
5. **A known-gap map** (2026-09-20) - hazards with no governing standard are answered before the
   index is consulted at all

### The defect that produced corrections 4 and 5

Heat exhaustion retrieved **1910.138 Hand protection** at 0.0845, against a floor of 0.08, and
presented it as the applicable standard. That section's body mentions temperature extremes in the
context of gloves. It shipped in `out/demo.json` while `limitations.md` claimed the system reported
no match for heat.

The obvious fix - raise the floor - was measured and rejected:

| Incident | Top section | Score | Correct? |
|---|---|---|---|
| Conveyor cleaning amputation | 1910.219 Mechanical power-transmission | 0.159 | yes |
| 18-foot fall from roof edge | 1910.28 Fall protection | 0.207 | yes |
| Struck by beam from crane rigging | 1910.179 Overhead and gantry cranes | **0.085** | yes |
| Heat exhaustion | 1910.138 Hand protection | **0.085** | **no** |

A true positive and a false positive on the same number. **No threshold separates them.** So the fix
came from a different question - does the section's *subject* match the predicted hazard? - and from
naming the two hazards that have no standard at all.

Implementing correction 4 exposed two further bugs, both found by measurement:

- Substring matching counted `machine` inside "machinery", so *Woodworking machinery requirements*
  took the maximum boost from one concept and **outranked the correct section** on a conveyor
  amputation. Fixed by deduplicating keyword matches by span.
- Strict word boundaries then broke plurals: `crane` stopped matching *Overhead and gantry cranes*
  and a correct retrieval silently dropped below the floor. Fixed with prefix matching. **The second
  bug was introduced by the fix for the first, and was caught only because the crane case was still
  in the regression set.**

### Results after all five corrections

| Incident | Top section retrieved |
|---|---|
| Conveyor cleaning amputation | **1910.219 Mechanical power-transmission apparatus** (alone - *Laundry* and *Woodworking* now fall below the floor) |
| 18-foot fall from roof edge | **1910.28 Duty to have fall protection** |
| Struck by beam from crane rigging | **1910.179 Overhead and gantry cranes** |
| Forklift tipped over with a raised load | **1910.178 Powered industrial trucks** |
| Heat exhaustion | **No standard exists** - General Duty Clause §5(a)(1) |
| Assault by a patient | **No standard exists** - General Duty Clause §5(a)(1) |
| "Employee got hurt at work." | *not classified - abstained* |

### Retrieval accuracy - measured, 2026-09-20

For most of this project no accuracy figure was reported for retrieval, because no ground truth
existed. 50 incidents were sampled from the held-out split and labelled against the 170-section
corpus under a protocol frozen beforehand (`docs/retrieval_labelling_guide.md`). **The labels were
assigned without looking at what the retriever returned** - otherwise the correct answer sits in the
candidate list by construction and recall@k is 1.0 by definition.

Of the 50: **33 scorable**, 10 where no standard exists, 2 governed by Part 1926 (construction, not
in this corpus), 5 too vague to label.

| Metric | Value |
|---|---|
| recall@1 | **0.364** |
| recall@3 | **0.364** |
| recall@3, primary section only | 0.242 |
| MRR | 0.364 |
| Returned nothing when a section existed | **0.333** |
| **Correct silence** on the 10 no-standard hazards | **1.000** |

| Baseline | recall@3 |
|---|---|
| Random 3 of 170 | 0.000 |
| Always return 1910.212 (best single fixed answer) | 0.212 |

**recall@1 equals recall@3 equals MRR.** When it is right, it is right at rank 1; it never recovers
at rank 2 or 3. The routing gate returns few candidates, so the second and third slots add nothing.

**Correct silence is 1.000.** Every hazard with no governing standard - heat, violence, overexertion
- correctly returned nothing. The known-gap work (ADR-011) is the part of retrieval that works
perfectly, and it works because it never asks the index.

### Where it works, and why

| Hazard group | n | recall@3 | returned nothing |
|---|---|---|---|
| Transportation incidents | 5 | **1.000** | 0.000 |
| Falls, slips, trips | 7 | 0.429 | 0.286 |
| Contact with objects and equipment | 12 | 0.250 | 0.333 |
| Exposure to harmful substances/environments | 5 | 0.200 | 0.600 |
| Fires and explosions | 4 | **0.000** | 0.500 |

Every forklift incident found 1910.178. Not one fire or explosion found its section. The split is not
random, and the cause is legible in the misses:

1. **Generic titles are invisible to title-based routing.** The governing section for a slip on a
   walking surface is **1910.22 "General requirements"**. For an unguarded machine it is
   **1910.212 "General requirements for all machines"**. Those titles carry almost no hazard
   vocabulary, so the routing gate (ADR-012) never nominates them - and between them they are two of
   the most-cited standards in all of OSHA. Eight of the 21 misses are these two sections.

2. **Procedures lose to objects.** 1910.147 (lockout/tagout) was the correct answer four times and
   was found none of them. It is written in *"energy isolating device"* and *"servicing and
   maintenance"*; the narratives say *"cleaning"*, *"rollers"*, *"fingers"*. Asked for 1910.147 **by
   number**, the system returns all 30,924 characters instantly - it ranks **77th of 170** when asked
   to find it from a narrative.

3. **What works is a named thing.** Transportation scored 1.000 because "forklift" in a narrative and
   "Powered industrial trucks" in a title are the same object. Retrieval succeeds exactly where the
   hazard *is* a piece of equipment with its own section.

That is a far more useful statement than "TF-IDF is weak", and it predicts what to fix: TASK-302's
embeddings target cause 2 directly, and indexing section *scope* text rather than titles alone
targets cause 1.

### The held-out set, and the result it killed

The 50 above became a dev set the moment anything was tuned against it. A second, disjoint 50 was
drawn and labelled under the same frozen guide (31 scorable, 13 no-standard, 1 out-of-scope,
5 uncertain), then scored **once**, after the scope-routing change of ADR-016 was finished.

| | dev (33) | held-out (31) |
|---|---|---|
| recall@1 before → after | 0.364 → **0.394** | 0.419 → **0.419** |
| recall@3 before → after | 0.364 → **0.424** | 0.484 → **0.484** |
| MRR before → after | 0.364 → **0.409** | 0.446 → **0.446** |
| **returned nothing** before → after | 0.333 → **0.212** | 0.194 → **0.065** |
| correct silence | 1.000 | 0.923 |

**The recall improvement was not real.** Held-out recall is identical to three decimal places before
and after the change. The 6-point dev gain was noise on 33 cases, and without the second set it would
have shipped as a result.

**The coverage improvement was real.** The rate at which the system returns nothing when a section
does exist fell by two thirds on held-out and by a third on dev. It replicates, so it is the claim
the change earns: *it does not rank better, it stops giving up.* The change was kept on that basis -
fewer dead ends at identical recall, and "here is a section" instead of "no section matched" is the
behaviour a user actually experiences.

**Held-out baseline recall@3 (0.484) is higher than dev (0.364) on the same system.** That gap is
sampling noise between two sets of ~30 drawn the same way, and it is the most honest thing on this
page about how much weight a number from 30 cases can carry.

### What the two sets agree on

Disagreement between dev and held-out is noise; agreement is signal.

- **1910.147 (lockout/tagout) is missed at a stable rate** - four times in dev, four times in
  held-out, never retrieved in either. It is the correct answer for cleaning or servicing a live
  machine, which is one of the most common mechanisms in the whole corpus. Asked for it **by
  number**, the system returns all 30,924 characters instantly; asked to find it from a narrative it
  ranks 77th of 170. This is replicated evidence, not an anecdote, and it is the case for TASK-302.
- **Correct silence holds** - 1.000 and 0.923. The single failure is H029, a mail carrier struck in a
  personal vehicle on a public highway, where 1910.178 was retrieved and no standard in fact applies.
- **Transportation and Falls lead; Exposure and Fires trail** in both sets, though the per-group
  numbers themselves swing wildly at n = 2 to 13 and should not be quoted individually.

### The cost of the change, measured

Scope routing re-admits **1910.138 Hand protection** - its opening mentions *"skin absorption of
harmful substances"*, which matches the Exposure vocabulary. It appears in three of the sixteen
held-out misses and held-out Exposure recall is 0.000. The heat defect of ADR-011 cannot recur, since
the known-gap map answers before the index is consulted, but the Exposure keyword list is too coarse
and TASK-312 records it.

**Two findings were deliberately not acted on** (ADR-017): the public-road gap above, and the
Exposure keyword list. Both were found *on the held-out set*, and fixing them against it would spend
it the same way the dev set was spent. They wait for a third set.

### Latent semantic retrieval, and a third set

The diagnosis above - a vocabulary gap, not a ranking bug - predicted its own fix. 1910.147 says
*"energy isolating device"*; the narratives say *"cleaning"* and *"rollers"*. Dense sentence
embeddings are the standard answer, and huggingface.co is blocked by network policy in both
workspaces, so no pretrained weights are reachable.

**Latent semantic analysis needs nothing downloaded.** A 300-component truncated SVD fitted over
TF-IDF of the 170 standards *plus 20,000 incident narratives* (explained variance 0.459), blended
half-and-half with the lexical score. Terms that co-occur across that combined corpus collapse onto
shared dimensions, which is exactly the bridge the query needs.

Both earlier sets were spent, so a **third 50** was drawn and labelled under the same frozen guide
(30 scorable). Neither arm had seen it. Measured once:

| | lexical only | + latent | change |
|---|---|---|---|
| recall@1 | 0.267 | **0.400** | **+0.133** |
| recall@3 | 0.500 | **0.600** | **+0.100** |
| MRR | 0.367 | **0.483** | **+0.116** |
| returned nothing | 0.200 | **0.067** | **-0.133** |
| correct silence | 0.889 | 0.889 | unchanged |

**1910.147 is now retrieved.** It was the correct answer eight times across the first two sets and
was returned on none of them. It appears for cleaning a running conveyor, clearing a palletizer jam,
and an engine started during inspection.

### The two experiments, side by side

This is the part worth reading twice.

| | dev says | unseen data says | verdict |
|---|---|---|---|
| **Scope routing** (ADR-016) | recall@3 0.364 → 0.424 | 0.484 → **0.484** | gain was **noise** |
| **Latent retrieval** (ADR-018) | recall@1 0.394 → **0.303** | 0.267 → **0.400** | gain is **real** |

The first looked like a six-point win and was nothing. The second looked on dev like a *loss* at
rank 1 and turned out to be a thirteen-point gain on unseen data. **Two sets of thirty disagreed
about the sign of the effect.**

Neither could have been sorted out by staring at the dev number harder, and the discipline is not
"held-out numbers come in lower" - it is that a number from thirty cases does not tell you which way
a change went. Both changes were decided on data that had never been used to make a decision.

### Would multi-label classification help? Measured, before building it.

An incident can be both a fall and a struck-by. The classifier forces one label, which has sat in the
backlog as an obvious improvement. Building it means retraining both classifiers and re-deriving the
group assignments in all four evaluation sets, so it was worth measuring the size of the problem
first.

Top-two margin on the major-group classifier, over 4,000 randomly sampled narratives:

| | share of incidents |
|---|---|
| margin < 0.30 (below the abstention floor) | **1.3%** |
| margin < 0.50 | 2.4% |
| margin < 1.00 | **6.5%** |
| median margin | **2.458** |

**Most incidents are decisively one group.** The ambiguous 6.5% are exactly the pairs you would
predict:

| n | ambiguous pair |
|---|---|
| 74 | Contact with objects and equipment + Transportation incidents |
| 52 | Contact with objects and equipment + Falls, slips, trips |
| 31 | Falls, slips, trips + Transportation incidents |

A worker struck by a forklift is genuinely both contact and transport; someone who falls and hits
machinery on the way down is genuinely both.

**Conclusion: real, narrow, and not worth the cost right now.** It would change the answer for about
one incident in fifteen, and the worst 1.3% are already caught by abstention rather than answered
wrongly. Retraining and invalidating four labelled evaluation sets to improve a twentieth of cases is
the wrong trade at this stage — and that sentence is now backed by a number rather than a hunch.

### After the roadway collapse (TASK-315, ADR-024)

Both classifiers were retrained once the 28 public-roadway OIICS events were folded into one class.
The headline numbers did not move — major group 0.938 / 0.832 exactly as before, fine-grained
0.668 / 0.584 across 77 classes instead of 76 — and the new class is learnable at **F1 0.518**.

Retrieval was then re-measured on all four sets. **These are re-measurements, not held-out results**,
because every set had already been used:

| set | recall@3 before → after | correct silence before → after |
|---|---|---|
| dev | 0.485 → 0.485 | 1.000 → 1.000 |
| held-out | 0.484 → **0.548** | 0.923 → 0.846 |
| third | 0.600 → 0.567 | 0.889 → 0.889 |
| fourth | 0.567 → **0.633** | 1.000 → 1.000 |

Small and bidirectional, which is what retraining does. **The claim this change earns is not a recall
improvement — it is a verified correctness property**: every public-road incident now returns the
General Duty Clause instead of a warehouse forklift standard, and every control is unchanged.

Two further known-gap candidates surfaced in the process — a utility task vehicle rollover, and a
sulphur dust explosion (**OSHA has no combustible dust standard**). Both were found on sets that are
spent, so both are logged and deliberately unfixed.

### What this number is not

**It is 0.364 against an AI-labelled reference set of 33 incidents.** Not "retrieval accuracy".

- The labels were assigned by an AI assistant reading the regulation text, not by a certified safety
  professional. `python main.py review` exists so a second labeller can put an agreement figure on
  them; until it is run, that figure is missing and its absence is stated rather than glossed.
- 33 scorable cases. A single case moves the number by 3 points.
- The sample over-weights small hazard groups on purpose, so the aggregate is a mean over the sample,
  not an estimate of corpus-wide accuracy.
- Narratives under 60 characters were excluded, which biases the set toward richer text and the
  figure toward optimism.
- **All three sets are now spent.** The first was tuned against; the second and third have each had
  their single measurement. Any further change needs a fourth set, or it is not measured.

### The measured case for embeddings

Ask the system for lockout/tagout **by number** and it returns 30,924 characters of 1910.147
instantly. Ask it to *find* that section from *"cleaning a running conveyor"* and it ranks
**77th of 170**, raw score 0.0113.

The corpus holds the right answer. TF-IDF cannot reach it, because 1910.147 is written in
*"energy isolating device"* and *"servicing and maintenance"* while the narrative says *"cleaning"*,
*"rollers"* and *"fingers"* - near-zero lexical overlap, and precisely the gap dense embeddings
close. This is the concrete justification for TASK-302, and it is worth more than a general claim
that embeddings might help.

It is also why TASK-300 comes first. Without a labelled set, "embeddings are better" is an opinion.

## Abstention

`LinearSVC` gives decision margins, not probabilities, so confidence is the gap between the top two
class scores - reported as a margin, not dressed up as a probability.

Below a margin of 0.30 the system refuses to classify. On the demo set, *"Employee got hurt at work."*
scores 0.236 and is correctly declined, while the crane incident scores 3.33 and proceeds.

An earlier threshold of 0.40 caused a **false abstention** on a crane case the model was getting
right. The threshold was lowered after inspecting real margins rather than being guessed.

## The agent layer

`tests/test_refusals.py` - **15/15 passing**. Every refusal rule in `agent_logic.md` is an assertion,
not a hope:

| Rule | Asserted by |
|---|---|
| Abstention never becomes an answer | Reply to a vague narrative contains no citation and no hazard label |
| Detail is added, not substituted | The follow-up is analysed with the original narrative, not instead of it |
| A known gap is stated, not filled | Heat and violence return zero sections and name the General Duty Clause |
| A missing section is never swapped | A lookup for 1910.99999 returns no text at all |
| Nothing is generated | **Every quote is verified as a substring of the cached eCFR corpus** |
| No compliance determination | Five phrasings of *"are we going to be cited?"* are refused without calling a tool |

The last row exists because the first build failed it. Asked *"Are we going to be cited for that?"*,
it ran the **question** through the classifier, decided it was a caught-in-machinery incident and
quoted 1910.219 at it. Rules 1-4 constrain the answer; nothing constrained the question. Found by
generating a transcript and reading it - not by reasoning about the code.

## Reproducibility

Fixed seed (42), stratified 80/20 split. The pipeline reproduced identically on two different
machines - `0.938 / 0.832` and `0.668 / 0.585` both times.

**Re-verified after the roadway collapse (ADR-024), trained on a third machine:** `0.938 / 0.832`
unchanged to three decimals, and `0.668 / 0.584` across 77 classes rather than 76. The major-group
classifier is untouched by that change *by construction*, so its reproducing exactly is a check that
the change did what it claimed and nothing else.
