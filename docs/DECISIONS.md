# Architecture Decision Records

Permanent decisions and the reasoning behind them. **Do not reverse one of these without adding a new
ADR that supersedes it.**

For current project state, see MEMORY.md. Decisions are permanent; state changes.

---

## ADR-001 — Regulation text is retrieved, never generated

**Decision.** Regulation text enters the system only through `src/regulations.py`, fetched verbatim
from the eCFR public API. If the source is unreachable and no cache exists, the system raises.

**Reason.** A language model asked to recall a safety standard will, when uncertain, produce
something plausible and wrong. In this domain a plausible-but-wrong regulation is more dangerous than
no answer. Regulations also change; a trained model freezes whatever it saw.

**Consequence.** The system cannot run offline on first use. Accepted.

---

## ADR-002 — TF-IDF and a linear SVM rather than a transformer

**Decision.** Classification uses TF-IDF over word and character n-grams with `LinearSVC`.

**Reason.** Narratives are short and formulaic. Character n-grams capture equipment names and typos
that word features miss. The model trains in minutes on CPU, which made the iteration that found
ADR-007 possible at all. Complexity that cannot be justified is not sophistication.

**Revisit when.** Fine-grained macro F1 becomes the binding constraint — see TASKS.md Phase 3.

---

## ADR-003 — No database, no web framework, no container

**Decision.** joblib for models, JSON for the corpus and metrics, a CLI for the interface.

**Reason.** A server database, an API layer and a front end would each consume time that belongs to
the model and the evaluation. The deliverable is a working analysis, not a deployment.

**Consequence.** Not multi-user and not deployable as-is. Accepted for v1.

---

## ADR-004 — Two label granularities, both reported

**Decision.** Train and report a major-group classifier (8 classes) **and** a fine-grained classifier
(76 classes).

**Reason.** `EventTitle` has 363 categories, most far too rare to learn. Reporting only the coarse
task would overstate the system; reporting only the fine task would understate it. Both are true.

---

## ADR-005 — Confidence is a margin, not a probability

**Decision.** `LinearSVC` has no `predict_proba`. Confidence is the gap between the top two decision
scores, reported as a margin.

**Reason.** Calibrating the SVM (`CalibratedClassifierCV`) tripled training time. More importantly, a
calibrated number would invite readers to treat it as a probability it is not. An honest margin is
better than a dressed-up one.

**Consequence.** Thresholds are not comparable across models. Documented in DESIGN.md.

---

## ADR-006 — Severity is not predicted

**Decision.** The system predicts hazard category only. Severity prediction was specified, then
removed.

**Reason.** Every record in the OSHA Severe Injury Reports database is already severe by definition —
it qualified for mandatory reporting through hospitalisation or amputation. The outcome barely varies,
so a severity model would produce a meaningless number.

**How it was caught.** By inspecting the label distribution before building on it. This is now
RULES.md §5.

---

## ADR-007 — OIICS major group is the first digit as written

**Decision.** `str(int(code))[0]`. **Never** `.zfill(4)[0]`.

**Reason.** OIICS event codes are variable length — `64`, `531`, `1214`. Zero-padding to four digits
turned `531` (exposure to environmental heat) into `0531`, read the group as `0`, and filed 2,192 heat
incidents as *Nonclassifiable* — inflating that class from 787 records to roughly 24,000.

**Impact.** Fixing it moved major-group accuracy from **0.831 to 0.938**.

**How it was caught.** The two classifiers disagreed on a heat-exhaustion narrative: major said
*Nonclassifiable*, fine said *Exposure to environmental heat*. The accuracy metric looked healthy
throughout. This is now RULES.md §5, last bullet.

---

## ADR-008 — Retrieval ranking is adjusted; retrieved text is not

**Decision.** The standards index repeats each section title `TITLE_WEIGHT` times and boosts sections
whose title matches the predicted hazard's vocabulary.

**Reason.** Plain TF-IDF failed badly — section bodies average ~10,000 characters, so narrative words
("sleeve", "rollers") pulled in whichever industry-specific section shared that vocabulary. A conveyor
amputation retrieved *bakery equipment*; heat exhaustion retrieved *oxygen*.

**Boundary.** These are routing aids, not legal assertions. They change which section surfaces, never
what it says. `config.HAZARD_KEYWORDS` is transparent and editable for exactly that reason.

---

## ADR-009 — Both halves abstain

**Decision.** The classifier refuses below `MARGIN_FLOOR`; retrieval returns nothing below
`RETRIEVAL_FLOOR`; a `Nonclassifiable` group skips retrieval entirely.

**Reason.** A safety tool that guesses confidently is worse than one that admits it does not know.
Returning the three least-bad sections for a narrative with no identifiable hazard is the retrieval
equivalent of hallucination.

**Tuning note.** `MARGIN_FLOOR` was briefly 0.40, which falsely abstained on a crane incident the
model classified correctly. Lowered to 0.30 after inspecting real margins — not guessed. See
RULES.md §8.

---

## ADR-010 — The assistant is specified, not built

**Decision.** v1 ships the orchestration in `src/pipeline.py` and the the assistant specification in
`agent_logic.md`. The the assistant wrapper itself is not implemented.

**Reason.** The tool contract, decision flow and refusal rules are complete and submitted as agent
logic, which the project guide accepts as a prototype form. Claiming a built agent that does not
exist would be the same failure this project is designed to avoid everywhere else.

**Superseded when.** TASK-101 lands — see TASKS.md Phase 1.

**SUPERSEDED 2026-09-20 by ADR-013.** Phase 1 landed. The tool layer, the prompt, a runnable
reference implementation and a test suite now exist. What remains unbuilt is the hosted agent, and
ADR-013 is explicit about that boundary.

---

## ADR-011 — Where no standard exists, say so before searching

**Decision.** `config.NO_SPECIFIC_STANDARD_GROUPS` and `NO_SPECIFIC_STANDARD_EVENTS` name the
hazards for which no 29 CFR 1910 standard exists. `pipeline.analyse()` consults them **before** the
index is touched, and returns the General Duty Clause as the authority instead.

**Reason — and this one was a live defect, not a precaution.** A heat-exhaustion narrative retrieved
*1910.138 Hand protection* and presented it as the applicable standard. That section's body mentions
temperature extremes in the context of gloves, which was enough overlap to score 0.0845 against a
floor of 0.08. It shipped in `out/demo.json` while `limitations.md` claimed the opposite behaviour.

Raising the floor does not fix it. The correct crane retrieval (1910.179) also scores 0.085 — a true
positive and a false positive on the same number. No threshold separates them, so the fix had to
come from somewhere other than the score.

Two entries, both verified against primary sources on 2026-09-20:

| hazard | source |
|---|---|
| Exposure to environmental heat | Aug 2024 proposed rule unfinalised, no target date |
| Violence / injury by persons or animals | osha.gov: *"There are currently no specific OSHA standards for workplace violence."* |

**Note.** These are exactly the two hazard groups with no entries in `HAZARD_KEYWORDS`. The empty
vocabulary looked like an oversight for weeks. It was the same gap, showing up in a different place.

**Cost.** The map is hand-maintained and will drift if OSHA finalises a heat rule.
`service._validate_known_gaps()` fails loudly at startup if a key stops matching a classifier label,
which catches the label drifting but not the law changing. The dates are in `config.py` for that
reason.

---

## ADR-012 — Retrieval must confirm the classification, not wander from it

**Decision.** `REQUIRE_HAZARD_ROUTING`. A section is a retrieval candidate only when the predicted
hazard's vocabulary appears in its **title**. Keyword matching is prefix-based with span
deduplication.

**Reason.** Section bodies average ~10,000 characters, so a narrative finds lexical purchase in
almost any of them — that is how a heat report reached *Hand protection*. The title is the field
that identifies the subject. Requiring it to agree with the classifier makes retrieval a routing aid
conditioned on the prediction, which is what `retrieval.py` always claimed in its docstring and did
not enforce.

**Two bugs found while implementing it, both by measurement:**

1. Plain substring matching counted `machine` inside "machinery", so *Woodworking machinery
   requirements* took the maximum boost from one concept and **outranked the correct section** on a
   conveyor amputation. Fixed by deduplicating matches by span.
2. Strict word boundaries then broke plurals — `crane` stopped matching *Overhead and gantry
   cranes*, and a correct retrieval silently dropped below the floor. Fixed with prefix matching.

The second bug was introduced by the fix for the first, and was caught only because the crane case
was in the regression set. **Keep the passing cases in the test set, not just the failing ones.**

**Effect.** The conveyor case now returns 1910.219 alone rather than 1910.219 plus *Laundry
machinery* and *Woodworking machinery*. Forklift narratives reach 1910.178 unaided.

**Cost.** `HAZARD_KEYWORDS` is hand-written, so retrieval can only reach hazards someone thought to
describe. This is a real ceiling and §2 of `limitations.md` explains why it cannot be raised
honestly until TASK-300 produces a labelled set.

---

## ADR-013 — The agent layer is built; the hosted agent is not

**Decision.** Phase 1 ships four things: the tool contract with JSON schemas (`src/assistant_tools.py`),
the system prompt (`docs/assistant_system_prompt.md`), a **deterministic reference implementation** of the
decision flow (`src/agent.py`), and a test suite that asserts every refusal rule
(`tests/test_refusals.py`). What is still not built is the assistant itself — a language model hosted on IBM
watsonx, given those schemas and that prompt.

**Reason.** Two things follow from removing the language model, and both are worth more than the
conversation quality lost:

1. **The refusal rules become testable.** "the assistant must never convert an abstention into an answer" is a
   behavioural claim. From a language model it can only be spot-checked; from `src/agent.py` it is
   an assertion that runs in seconds, every time. Fifteen of them do.
2. **The system runs without credentials.** Anyone can clone the repository and hold the
   conversation today.

**What it cannot do.** It routes on regular expressions. Real the assistant will handle *"the guy on nights got
his hand caught"* far better. This is the reference the hosted agent gets checked against, not a
replacement for it.

**Found by building it.** Asked *"Are we going to be cited for that?"*, the first version ran the
**question** through the classifier, decided it was a caught-in-machinery incident and quoted
1910.219 at it — a direct breach of Rule 5. Every individual rule was implemented; what was missing
was a check that the input is an incident at all. Rules 1–4 constrain the answer. Nothing constrained
the question until the transcript exposed it. `_is_compliance_question` and
`_is_question_not_narrative` were added, and five compliance phrasings are now in the test suite.

**Superseded when.** The schemas are imported into watsonx Orchestrate and the prompt is pasted into
the agent's instructions. No code change is needed for that — see TASKS.md Phase 1b.

---

## ADR-014 — Retrieval is measured against an AI-labelled set, with the provenance stated

**Decision.** Build the missing ground truth by labelling 50 sampled incidents against the 170-section
corpus, under a protocol frozen before labelling (`docs/retrieval_labelling_guide.md`). Labels are
assigned by an AI assistant. Report the resulting figure **always qualified by how it was made**, and
ship `python main.py review` so a human can attach an agreement number.

**Reason.** The alternative was to keep reporting nothing. "No accuracy figure is reported" was
honest for as long as no set existed, but it had become a way of never having to find out - and
ADR-011 and ADR-012 were both tuned against five demo examples, which is exactly the overfitting the
project condemns elsewhere. A flawed measurement whose flaws are enumerated beats no measurement.

**The rule that makes it worth anything.** Labels are assigned **without looking at retriever
output**. Read the narrative, decide the regulatory subject, then find it among the 170 titles. If
labels are drawn from the retriever's candidates, the answer is in the list by construction and
recall@k is 1.0 by definition. This is the easiest way to produce a meaningless evaluation and it
happens by accident.

**Result.** recall@3 **0.364** on 33 scorable cases, against 0.212 for the best single fixed answer
and 0.000 for random. Correct silence **1.000** on the ten hazards with no standard.

**What it bought beyond the number.** The per-group split - Transportation 1.000, Fires 0.000 - named
the actual defect: sections with generic titles (1910.22, 1910.212) are invisible to title-based
routing, and procedural standards (1910.147) lose to equipment-named ones. Before this, the
diagnosis was "TF-IDF is weak", which predicts nothing. Eight of 21 misses are two sections.

**Cost, stated plainly.** The labeller is not a safety professional. 33 scorable cases means one case
moves the figure three points. Small groups are over-sampled, so the aggregate is a mean over the
sample and not a corpus-wide estimate. Narratives under 60 characters were excluded, biasing toward
optimism. **And the set is now a dev set** - anything tuned against it and re-measured on it is dev
performance, which is why TASK-310 exists.

**Superseded when.** A practising safety professional labels a set, or a second held-out 50 exists.

---

## ADR-015 — Overexertion is the third hazard group with no standard

**Decision.** Add `Overexertion and bodily reaction` to `NO_SPECIFIC_STANDARD_GROUPS`.

**Reason.** OSHA has no ergonomics standard. The 2000 rule was rescinded by Senate Joint Resolution 6
under the Congressional Review Act in 2001, and the same resolution bars OSHA from issuing a
substantially similar one. Ergonomic hazards are enforced under the General Duty Clause. Verified at
osha.gov/ergonomics/faqs on 2026-09-20.

**What it changes.** The group previously returned `no_match`, which implies a standard exists and
was not found. It now returns `no_specific_standard` with the authority and the reason - a stronger
and more useful answer. All 38 fine-grained events in the group are exertion or bodily-reaction
types, so the gap is correctly declared at group level rather than per event.

**Three of the eight hazard groups now have no governing standard** - violence, overexertion, and
(at event level) environmental heat. Together that is roughly 3,500 of the 86,204 incidents where the
correct answer is "the law is silent here" rather than a citation.

---

## ADR-016 — Routing reads the section's scope, and the title still leads

**Decision.** A section is a retrieval candidate when the predicted hazard's vocabulary appears in its
title **or** in the first 400 characters of its body. A title match still takes the larger boost and
is guaranteed the lead position; everything else competes on score.

**Reason.** Eight of the twenty-one dev-set misses were two sections: 1910.22 *"General
requirements"* and 1910.212 *"General requirements for all machines"* - among the most-cited
standards in OSHA, with titles that carry no hazard vocabulary whatsoever. Title-only routing could
never nominate them. Their scope openings carry it plainly (*"walking-working surfaces"*, *"machine
guarding... ingoing nip points"*).

Only the opening, never the whole body: body-wide matching is what retrieved *Hand protection* for a
heat narrative in the first place (ADR-011).

**Why the title leads.** This follows the product, not the metric. The agent presents the first
section as the one that applies and the rest as *"related, scoring lower"*, so the lead slot must
hold the strongest kind of evidence. Ranking *every* slot by tier cost recall@3 (0.424 → 0.394) by
letting weak title matches crowd out strong scope matches; ranking none by tier cost recall@1.

### The result, and the part worth keeping

| | dev (33) | held-out (31) |
|---|---|---|
| recall@1 before → after | 0.364 → **0.394** | 0.419 → **0.419** |
| recall@3 before → after | 0.364 → **0.424** | 0.484 → **0.484** |
| MRR before → after | 0.364 → **0.409** | 0.446 → **0.446** |
| returned nothing before → after | 0.333 → **0.212** | 0.194 → **0.065** |

**The recall gain did not transfer. It was dev noise.** Held-out recall is identical to three decimal
places, before and after. Had the held-out set not existed, this would have shipped as
*"recall@3 improved from 0.364 to 0.424"* - a real-sounding 6-point gain that is not real.

**What did transfer is coverage.** The rate at which the system returns nothing when a section does
exist fell by two thirds on held-out (0.194 → 0.065) and by a third on dev. That replicates across
both sets, so it is the honest claim: *this change does not rank better, it stops giving up.*

**The change was kept** on that basis. Fewer dead ends at identical recall is worth having, and the
user-visible behaviour - an answer instead of "no section matched" - is the one that matters.

**Cost, measured.** Scope routing re-admits 1910.138 *Hand protection*, whose opening mentions *"skin
absorption of harmful substances"* and so matches the Exposure vocabulary. It appears in three of the
sixteen held-out misses, and held-out Exposure recall is 0.000. The heat defect of ADR-011 cannot
recur - the known-gap map answers before the index is consulted - but this is a real side-effect and
the Exposure keyword list is too coarse.

**Not tuned further.** The held-out set has been spent. Any further change is measured on a third
set, or it is not measured.

---

## ADR-017 — Findings held back deliberately

Two things were found while scoring the held-out set. **Neither was acted on**, because acting on
them would mean tuning against the set that is supposed to be untouched - and the value of a held-out
set is destroyed silently, by exactly this kind of reasonable-sounding fix.

1. **A fourth candidate known gap.** H029 - a mail carrier struck in a personal vehicle on a public
   highway - retrieved 1910.178 *Powered industrial trucks*. 29 CFR 1910 does not govern public
   roads, so the correct answer is that no standard applies. This is the single correct-silence
   failure (12 of 13 rather than 13 of 13).

2. **1910.147 is missed at a stable rate.** Four times in dev, four times in held-out. Replicated,
   not noise - and the strongest evidence in the project for TASK-302's embeddings.

Both go into TASKS.md as work, with a third evaluation set as their prerequisite.

---

## ADR-018 — Latent semantic retrieval, blended with the lexical score

**Decision.** `USE_LSA = True`. A truncated SVD (300 components) is fitted over TF-IDF of the 170
standards **plus 20,000 incident narratives**, and the final ranking score is
`0.5 * lexical + 0.5 * latent`.

**Reason.** The defect was diagnosed by measurement and it was a **vocabulary gap**, not a ranking
bug. 1910.147 is the correct answer for cleaning or servicing a live machine - one of the most common
mechanisms in the corpus - and it was retrieved **zero times across both earlier evaluation sets**.
The regulation says *"energy isolating device"* and *"servicing and maintenance"*; the narratives say
*"cleaning"*, *"rollers"*, *"fingers"*. Lexical overlap is near zero, so no amount of re-weighting
TF-IDF could ever reach it.

**Why not sentence embeddings.** That is the textbook answer and it was the plan (TASK-302).
huggingface.co is denied by network policy in both the cloud workspace and the local one, so no
pretrained weights can be downloaded. Latent semantic analysis needs nothing downloaded, trains in
about fifteen seconds on CPU, and is the pre-neural solution to precisely this problem.

**Why the narratives are in the fit.** Fitting the SVD on 170 regulation sections alone would learn
regulation-to-regulation structure and leave narrative vocabulary exactly as foreign as it was. With
narratives mixed in, "cleaning" and "rollers" occupy the same fitted space as "servicing" and
"maintenance", and the decomposition can place them on shared dimensions because they describe the
same events. Explained variance is 0.459 over 300 components.

**Why blended, not replaced.** The lexical half is what puts a forklift narrative on *Powered
industrial trucks* every time. The latent half is for when no word lines up at all. Neither is
reliable alone.

### Measured on the third evaluation set, once

Both earlier sets were spent - the first tuned against, the second already measured - so a third 50
was drawn and labelled under the same frozen guide (30 scorable). Neither arm had seen it.

| | lexical only | + latent | change |
|---|---|---|---|
| recall@1 | 0.267 | **0.400** | **+0.133** |
| recall@3 | 0.500 | **0.600** | **+0.100** |
| MRR | 0.367 | **0.483** | **+0.116** |
| returned nothing | 0.200 | **0.067** | **-0.133** |
| correct silence | 0.889 | 0.889 | unchanged |

Every metric improved, and the abstention behaviour was untouched.

**The dev set said the opposite about rank 1.** On dev, adding latent scoring *lowered* recall@1
from 0.394 to 0.303 while raising recall@3. Had that been the only evidence, the honest reading would
have been "a trade, not a win", and this would probably not have shipped. On unseen data recall@1
rose by thirteen points. **Two sets of thirty disagreed about the sign of the effect** - which is the
plainest statement available about how much weight a number from thirty cases carries.

**Compare ADR-016**, where the dev set showed a six-point gain that turned out to be nothing. The
same discipline killed a false positive there and confirmed a real one here. That is the argument for
the discipline: it is not that held-out numbers are always lower.

**Cost.** Warm-up goes from about 25 seconds to about 40. Memory rises by the SVD components.
`USE_LSA = False` restores the lexical path exactly.

**TRIED AND REJECTED, recorded so it is not re-derived:** choosing the lead result on the *lexical*
score among title matches, on the theory that the precise signal should lead and the soft one add
breadth beneath it. It lost on every dev metric - recall@1 0.303 → 0.273, recall@3 0.485 → 0.424,
MRR 0.384 → 0.338. The blended score is better evidence even for the lead slot.

**Superseded when.** Pretrained sentence embeddings become reachable. LSA is a strong baseline for
this, not the ceiling - and the comparison would need a fourth set.

---

## ADR-019 — The blend is not a blend, and the retrieval floor is inert

**Found after ADR-018 was measured and accepted. Recorded rather than quietly patched.**

`LSA_BLEND = 0.5` was written to mean half lexical, half latent. Measured across narratives it does
not:

| | range | contribution at 0.5 |
|---|---|---|
| lexical (TF-IDF cosine) | 0.00 – 0.08 | at most **0.02** |
| latent (SVD cosine, shifted to [0,1]) | 0.50 – 0.68 | about **0.28** |

Ranking is driven by the latent score; lexical acts as a tiebreak. **Two real defects follow.**

**1. `RETRIEVAL_FLOOR` no longer does anything.** It is 0.08 and every blended score is 0.25–0.33, so
the "no section matched above the floor" path has effectively stopped firing. Part of the
`returned nothing → 0.067` improvement reported in ADR-018 is the floor being bypassed rather than
retrieval genuinely finding more. **The abstention that protects a user is untouched**: a hazard with
no standard at all is answered by the known-gap map in `pipeline.py` *before* the index is consulted
(ADR-011), and correct silence is unchanged at 0.889 in both arms.

**2. Reported scores stopped meaning anything.** Everything lands in 0.25–0.33, and the assistant was printing
*"applies (match 0.302)"* as though that were a measure of fit — in a system whose stated principle is
traceable claims. Fixed at the presentation layer, not by touching the ranking:

- the agent now says *"is the closest match (ranked 1 of 3)"* and never quotes the blended number
- related sections are listed without scores, under an explicit note that ranking is relative within
  one result and not comparable across incidents
- `lexical_score` is carried through `pipeline` → `service` → the tool result, so a calibrated
  absolute number still reaches any caller
- every standard in a tool result carries a `score_note` pointing here
- `tests/test_refusals.py::test_blended_scores_are_not_presented_as_match_quality` asserts all of it

**The obvious fix is worse.** Min-max normalising both vectors before blending amplifies noise in the
latent vector's narrow range and wrecks the ranking: the crane case's top hit becomes *1910.30
Training requirements* and the forklift's becomes *1910.244 Other portable tools*. Tried, measured,
rejected — do not re-derive it.

**Why this ships anyway.** The configuration measured on the third evaluation set is exactly the
configuration on disk, and it beat lexical-only on every metric on data neither arm had seen. The
result is real even though the mechanism is not what the code claimed. Reverting would discard a
measured improvement because of a mechanism concern rather than an outcome concern.

**What it costs, concretely.** The crane demo case lost **1910.179 Overhead and gantry cranes**, which
lexical-only retrieved correctly. Aggregate recall rose; this case fell.

**A calibrated floor for a blended score needs a fourth labelled set** — TASK-313. Until then the
floor is documented as inert rather than described as working.

---

## ADR-020 — Phase 2 is closed as a finding, not carried as a blocked task

**Decision.** Phase 2 (port to Indian data) cannot be built as written. TASK-201..206 are superseded.
The result is written up in `docs/findings_indian_data.md` and treated as a project finding.

**Reason.** The narratives exist and are compulsory: **Form 18** under the Factories Act 1948 carries
a free-text description of the accident and a cause analysis, filed within four hours of a fatality.
They go to **state** Inspectorates of Factories and are published nowhere. The only public artefact
is *"Industrial Injuries in Factories"* on data.gov.in — aggregate counts by state and year, verified,
with no incident records and no text.

So the obstacle is neither linguistic nor technical. **It is a publication decision.**

**Why closing it beats leaving it open.** A task list that carries seven items nobody can ever start
is a list that stops being read. Naming the reason converts dead weight into the most transferable
claim the project has:

> The method here is forty-year-old technology. What makes SafetyLens possible is that someone chose
> to publish 86,209 narratives. Publish the narratives and this system can be rebuilt for any
> jurisdiction in a week.

**The second time this shape appeared.** The archived AccessHyd project died the same way: the
aggregate was public, the records were not — *"497 stations have lifts"* without ever saying which
497. Two independent attempts, the same obstacle, both found by testing the premise before building
on it.

**What survives.** TASK-212 — the DGFASLI standards corpus — is a browser download away and is worth
doing on its own, because it demonstrates the retrieval half ports even while the classifier half has
no data. TASK-210 (an RTI request) is the only honest route to the narratives and is not an
internship-sized task.

---

## ADR-021 — The retrieval floor cannot be recovered, and the attempt made things worse

**TASK-313/314, resolved 2026-09-20 against a fourth labelled set. Three changes were proposed, one
shipped, two reverted with measurements.**

### Why the old floor cannot work

`RETRIEVAL_FLOOR` was an absolute cut on a raw TF-IDF cosine. Two things now sit between it and the
number it gates:

1. the score is a lexical/latent blend on a different scale (ADR-019), and
2. it is multiplied by a routing boost of **1.5x to 3.4x**, so the value mostly encodes *how a
   section was routed* rather than how well it matched.

An absolute threshold on that quantity is not mis-tuned. It is meaningless.

### What was tried

A **sigma floor**: keep only candidates standing at least *k* standard deviations above the mean of
the routed candidates for that query. Scale-free, so it survives any future change to the blend, and
it degrades the right way — when nothing stands out, nothing is returned.

Swept on dev:

| sigma | rec@1 | rec@3 | returned nothing | precision@1 |
|---|---|---|---|---|
| 0.0 | 0.333 | 0.485 | 0.000 | 0.333 |
| 0.5 | 0.333 | 0.485 | 0.000 | 0.333 |
| **1.0** | 0.303 | 0.424 | 0.121 | 0.345 |
| 1.5 | 0.273 | 0.394 | 0.273 | 0.375 |
| 2.0 | 0.242 | 0.364 | 0.303 | 0.347 |

precision@1 moves across a 4-point range that is noise at n=33. **A floor does not buy recall and was
never supposed to — it buys the ability to decline.** 1.0 was chosen as the cheapest setting that
actually fires, then measured on the fourth set:

| set 4 (n=30) | without | with sigma 1.0 |
|---|---|---|
| recall@1 | 0.267 | 0.267 |
| recall@3 | **0.633** | **0.567** |
| MRR | 0.433 | 0.411 |
| returned nothing | 0.000 | 0.067 |
| correct silence | 0.917 | 0.917 |

**Six and a half points of recall@3 to gain declining in 2 cases out of 30.** Reverted.

### The honest end state

**There is no working retrieval floor.** The absolute one is inert, the sigma one costs more than it
returns, and the guards that remain are:

- the **known-gap map**, which answers before the index is consulted and is the one that matters
  (correct silence 0.917–1.000 across all four sets)
- **honest phrasing** — the agent says *"is the closest match (ranked 1 of 3)"*, never *"applies"*,
  and never quotes the blended score (ADR-019)

That is a weaker guarantee than the project started with and it is stated rather than papered over.

### A methodological mistake worth recording

The three changes were **measured as a bundle** on set 4, which made the result uninterpretable —
recall fell, and the comparison could not say which change caused it. An ablation on dev separated
them afterwards, but dev is not where the claim lives. **Change one thing per measurement**, or the
held-out set is spent on a question it cannot answer.

---

## ADR-022 — Administrative sections leave the index; PPE sections stay in it

**Shipped: drop administrative sections.** `retrieval_labelling_guide.md` §5 already said Purpose and
scope, Definitions, Effective dates, Incorporation by reference and Recordkeeping can never be a
correct answer. They were in the index anyway, and **1910.21 "Scope and definitions" was returned for
a real incident** on the dev set.

Measured on dev: recall@1 0.303 → **0.333**, MRR 0.384 → **0.404**, recall@3 unchanged.

This one carries a guarantee rather than just a measurement. **No label in any of the four evaluation
sets references an administrative section** — checked programmatically across all 121 labelled
targets. Dropping them therefore cannot reduce recall; it can only free a slot in the top three.

**Reverted: excluding PPE sections from scope routing.** The reasoning was sound — 1910.138 "Hand
protection" opens by listing *"skin absorption of harmful substances... temperature extremes"*, which
matches almost any hazard vocabulary, and that is how it reached a heat narrative in the first place
(ADR-011). Excluding PPE from scope routing looked obviously right.

Measured on dev it cost **3 points of recall@3** (0.485 → 0.455) and gained nothing at rank 1,
because **PPE sections are genuinely the correct answer sometimes**: a hydroblasting laceration and a
bleach splash to the face are both labelled to 1910.132/1910.133 as the controlling duty, and neither
title carries the hazard vocabulary, so scope routing was the only route to them.

The over-admission is real. The cure was worse than the disease.

---

## ADR-023 — The public-road known gap cannot be implemented

**TASK-311, closed as not implementable.**

Held-out scoring found a fourth candidate gap: 29 CFR 1910 does not govern public highways, so a
worker struck by a car on a public road has no applicable standard — and the system retrieved
*1910.178 Powered industrial trucks* for one.

The fix would be an entry in `NO_SPECIFIC_STANDARD_EVENTS` keyed on the roadway event labels. **Those
labels do not exist in the classifier's vocabulary.** All 28 public-roadway OIICS events fall below
`MIN_EXAMPLES_PER_CLASS` (150) and are filtered out before training:

| event | n |
|---|---|
| Pedestrian struck by vehicle in roadway, unspecified | 63 |
| Pedestrian struck by forward-moving vehicle in roadway | 49 |
| Fall or jump from vehicle in normal operation, roadway | 47 |
| Jack-knifed or overturned, roadway | 43 |
| *…24 more, all below 32* | |

About 380 incidents in total, split across 28 labels that are individually too rare. Every surviving
class containing "roadway" is a **non**roadway variant. `service._validate_known_gaps()` would
correctly refuse the rule as dead.

**The route that would work** is collapsing all 28 into one `roadway` class before the rare-class
filter, which clears the threshold. That changes the label taxonomy, requires retraining both
classifiers, and invalidates the group assignments in all four evaluation sets. Logged as TASK-315;
it is a bigger change than the defect it fixes.

---

## ADR-024 — Public-roadway events collapsed into one class, and the gap now fires

**TASK-315, done 2026-09-21. ADR-023 said this was not implementable at acceptable cost. That was
right about the cost and wrong about the conclusion.**

### The defect

29 CFR 1910 does not govern public highways. A mail carrier struck by a car on a public road has no
applicable standard — the answer is the General Duty Clause. The system returned **1910.178 Powered
industrial trucks**.

The fix is an entry in `NO_SPECIFIC_STANDARD_EVENTS`, and it could not be written, because OIICS
splits public-roadway events across **28 labels and every one falls below the 150-example
threshold**: 63, 49, 47, 43, 31, and a tail below 20. All were filtered out before training, so the
classifier was literally incapable of saying "this happened on a public road".

### The change

One function, `data._collapse_roadway`, folding the 28 into a single class before the rare-class
filter. The substring test has to exclude `nonroadway`, which contains `roadway` and means the
opposite — a forklift in a warehouse aisle, which 1910.178 does govern.

**381 records. Clears the threshold comfortably.**

### What it cost, measured

Retrained both classifiers (in the cloud container — the local workspace has 2.9 GB of RAM and is
killed partway through; see the note below).

| | before | after |
|---|---|---|
| Major group accuracy | 0.938 | **0.938** |
| Major group macro F1 | 0.832 | **0.832** |
| Fine accuracy | 0.668 | **0.668** |
| Fine macro F1 | 0.585 | **0.584** |
| Fine classes | 76 | 77 |
| Roadway class per-class F1 | *did not exist* | **0.518** (support 76) |

**The headline numbers do not move.** Macro F1 drifts by one thousandth across a changed class count,
which is noise. The major-group classifier is untouched by construction, which is a useful sanity
check that the change did what it claimed and nothing else.

### Verified end to end

| | result |
|---|---|
| Mail carrier struck on a public road | **no standard exists** — General Duty Clause |
| Struck by a car crossing the street | **no standard exists** — General Duty Clause |
| Van ran off the roadway | **no standard exists** — General Duty Clause |
| *Control:* forklift on a loading dock | 1910.178 — unchanged |
| *Control:* cleaning a running conveyor | 1910.219, 1910.147 — unchanged |
| *Control:* heat exhaustion | General Duty Clause — unchanged |
| *Control:* vague narrative | abstained — unchanged |

H029, the case that exposed the defect, is fixed.

### The churn, reported rather than buried

Retraining shifts fine-grained predictions slightly, which shifts the retrieval query, which shifts
what comes back. Re-measured across all four sets:

| set | recall@3 before → after | correct silence before → after |
|---|---|---|
| dev | 0.485 → 0.485 | 1.000 → 1.000 |
| held-out | 0.484 → **0.548** | 0.923 → **0.846** |
| third | 0.600 → **0.567** | 0.889 → 0.889 |
| fourth | 0.567 → **0.633** | 1.000 → 1.000 |

Bidirectional and small — two sets up on recall@3, one down, one flat. Aggregate correct silence goes
from 42/44 to **41/44**: H029 fixed, and two cases newly failing for unrelated reasons.

**These numbers are re-measurements, not held-out results.** All four sets had already been used. The
claim this change earns is the verified correctness property above, not a recall improvement.

### Two further gap candidates, logged and not acted on

The two new silence failures are the same category of finding as ADR-017:

- **H027** — a utility task vehicle rollover. No 1910 section covers UTVs.
- **H046** — a sulphur dust explosion. **OSHA has no combustible dust standard**; it is cited under
  the General Duty Clause, and the long-proposed rule was never finalised.

Both are real. Both were found **on evaluation sets that are spent**, so fixing them against those
sets is precisely the mistake ADR-017 exists to prevent. Logged as TASK-316 and TASK-317.

### A note on where this had to run

The local workspace has 2.9 GB of RAM and is killed partway through fitting a quarter of a million
TF-IDF features over 69,000 documents. Training ran in the cloud container (8 GB), and the models
came back compressed and split into three parts under the 20 MB transfer cap, reassembled against a
SHA-256 checksum that was verified before anything was replaced. The previous models are in
`out/_pre315_backup/`.

`model.save` now compresses at zlib level 9 as a result: 68 MB → 29 MB for the fine classifier, nine
seconds out, nothing extra coming back in.

---

## ADR-025 — A regulation cache must carry provenance. Found the hard way.

**Incident, 2026-09-21. The worst defect in the project's history, in the project's own repository.**

### What happened

`add_part` was added so Part 1926 could be loaded from a browser download. Its unit test wrote a
synthetic fixture — the sentence *"This section covers fall protection in construction."* repeated
twenty times — into `data/standards_part_1926.json`, and cleaned up afterwards by deleting it.

Then file deletion was restricted mid-session. The cleanup failed. The fixture stayed on disk.

`_extra_parts()` loads any cache it finds. On the next run it merged that fixture into the retrieval
index, and `python main.py demo` returned this for a roof-fall narrative:

> `29 CFR 1926.501 - 1926.501 Duty to have fall protection.`
> *"This section covers fall protection in construction. This section covers fall protection in
> construction. This section covers fall protection in construction…"*

printed beneath the heading **"APPLICABLE STANDARDS - quoted from eCFR, not generated"**.

**Invented regulation text, cited with a section number, presented as authoritative, by the system
whose first architectural rule is that regulation text is fetched and never generated.** Every guard
in the project held — the text was quoted verbatim, the citation was carried, the provenance line was
printed — and every one of them was quoting a lie, because they all trusted the corpus.

### Why the existing design did not catch it

ADR-001 secured the *fetch* path: if eCFR is unreachable, `regulations.py` raises rather than
generating. Nothing secured the *cache* path. A JSON file in `data/` was trusted absolutely, and the
checks downstream verify that a quote matches the corpus — which it did, perfectly.

**A test asserting that every quote is a substring of the cached corpus cannot detect a poisoned
corpus.** That test passed throughout.

### The fix

1. `add_part` writes a **provenance block**: source filename, SHA-256 of the source bytes, section
   count, parse timestamp, and a format marker.
2. `_extra_parts` **refuses** any cache without one, raising with the file path and the command to
   regenerate it — rather than silently loading.
3. The test no longer writes into `data/` at all; it uses a temp directory, so its cleanup cannot be
   the thing that protects the corpus.
4. Three regression tests: a cache without provenance is refused; `add_part` writes provenance that
   survives a reload; and **no section in the live index lies outside Part 1910**.

This does not make a cache tamper-proof — anyone can hand-write a provenance block. It makes the
*accident* impossible, and the accident is what happened.

### What this is worth

Three lessons, and the third is the one that generalises:

1. **A test that writes into a data directory is a test that can corrupt production data.** It only
   looked safe because cleanup normally works.
2. **Integrity checks that compare an output to a source cannot validate the source.** The strongest
   test in the suite — every quote is a real substring — was satisfied by fabricated text.
3. **The guard was on the door nobody came through.** The fetch path was hardened because that was
   where generation was imagined to come from. The text arrived through the cache, which had no door
   at all. Adding a provenance requirement is cheap; noticing which paths have no guard is the work.

Caught by reading demo output during a routine audit, which is also how the heat defect (ADR-011) and
the Rule 5 breach (ADR-013) were found. **Three of the project's most serious defects were found by
generating output and reading it, and none by reasoning about the code.**

---

## ADR-026 — The assistant is a watsonx.ai agent, and the refusal rules are enforced in code

**Phase 1b, built 2026-09-21. Supersedes the Orchestrate plan in ADR-013.**

### Not Orchestrate

The original plan was to import `openapi.json` into watsonx Orchestrate as three skills. That needs
this laptop exposed on a public HTTPS URL through a tunnel — fragile, and a service with no
authentication pointed at the open internet.

**Calling watsonx.ai directly needs no tunnel.** `src/assistant_llm.py` runs the loop locally: the model
returns tool calls, the code executes them against the real pipeline, results go back, the model
writes the reply. `serve.py` and `openapi.json` remain for anyone who does want the Orchestrate
route.

### The part that matters: a prompt is a request, a guard is a fact

`docs/assistant_system_prompt.md` tells the model never to invent a citation, never to convert an
abstention into an answer, never to issue a compliance determination. **A prompt cannot enforce
that.** A model under pressure — a user saying *"just give me your best guess"* — will eventually
oblige, and no amount of capitalised MUST NOT prevents it.

So every reply passes through `_guard`, checked against the tool results **from the same turn**:

| Rule | Enforced how |
|---|---|
| 1 — no citation that did not come from a tool | Every `1910.x` in the reply must be in this turn's tool results |
| 2 — quote, never paraphrase | Any quoted run of 60+ characters must be a substring of a returned section |
| 3 — never convert an abstention into an answer | If a tool returned `abstained`, the reply may contain no section and no hazard-group name |
| 5 — no compliance determination | Detected **before** the model is called, so the question never reaches it |
| loop | Tool rounds capped; an unterminated sequence is blocked |

A blocked reply **degrades to the deterministic agent's answer**, not to an error. The user still
gets a correct analysis; the violation goes in the trace.

### Two things the tests caught

Written against a scripted model that tries to break every rule (`tests/test_assistant_llm.py`, 10 tests,
no credentials, no network):

1. **Rule ordering.** A citation after an abstention was being reported as a Rule 1 breach — "that
   section was not returned" — which names the symptom. It is a Rule 3 breach: the model was asked
   not to answer at all. Rule 3 is now checked first.
2. **The guard leaked what it blocked.** The message read *"blocked: cited 1910.9999, which no tool
   returned"* — printing the invented section number on screen, which was the entire point of
   blocking it. A fabricated quotation would have been reproduced in full the same way. The user now
   sees the *category* ("a regulatory citation that did not come from the corpus"); the detail goes
   to the trace.

The second is the more interesting failure: **a safety mechanism that reports what it caught can
republish the thing it caught.**

### What is and is not proven

Built, and tested against an adversarial scripted model: the loop, the guard, the fallback, the
Rule 5 pre-check, the prompt loading from its documented file.

**Not yet run against a live model.** That needs credentials in `.env`, which only Bhargav can
supply. When it runs, `docs/assistant_test_scenarios.md` is the protocol, and **the interesting result is
which rules the real model tries to break** — the scripted one breaks them all by construction, which
proves the guard works but says nothing about how often a real model would need it.

---

## ADR-027 — Routing on the predicted event: tried twice, rejected twice

**An accuracy idea that sounded right and measured as nothing. Recorded so it is not re-derived.**

`HAZARD_KEYWORDS` is eight hand-written lists — one per major group — doing the routing for 86,000
incidents across 77 event types. The fine-grained prediction is far more specific and already
computed: *"Caught in running equipment or machinery during maintenance, cleaning"* contains
**maintenance** and **cleaning**, and 1910.147 opens with *"the servicing and maintenance of machines
and equipment"*. Free routing vocabulary for all 77 classes, where the hand-written list has eight.

| variant | dev recall@1 | dev recall@3 | dev MRR |
|---|---|---|---|
| off (shipped) | **0.333** | 0.485 | **0.404** |
| event words in title **and** scope routing | 0.242 | 0.485 | 0.354 |
| event words in scope routing only | 0.333 | 0.485 | 0.404 |

**The first variant actively hurt.** Generic event words — `equipment`, `object`, `vehicle` — matched
many section titles, putting them in tier 0 and crowding the lead slot that exists to hold the
strongest evidence. Nine points of recall@1.

**The second did nothing at all**, identically to three decimals. The reason is that the gap it was
built to bridge is already bridged: latent retrieval (ADR-018) surfaces 1910.147 for a
cleaning-a-running-machine narrative without any of this.

Disabled rather than deleted, with the numbers in `config.py`, because the idea is obvious enough
that someone will have it again.

**The general point:** an improvement that targets a defect something else already fixed measures as
zero, and it is worth knowing *why* it measured as zero rather than just that it did.

