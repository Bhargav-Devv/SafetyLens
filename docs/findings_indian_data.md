# Finding: can this method port to India?

**TASK-200, resolved 2026-09-20. The answer is no, and the reason is worth more than the answer.**

Phase 2 proposed rebuilding SafetyLens on Indian data: incident narratives under the Factories Act
1948, with DGFASLI standards as the retrieval corpus. `TASKS.md` flagged TASK-200 as the gate and the
real risk. This is what testing it produced.

---

## 1. The narratives exist. By law.

**Form 18, Notice of Accident**, prescribed under the Factories Act 1948 and the state Factories
Rules, is a statutory filing. Its structure:

| Part | Contents |
|---|---|
| A | Factory name, licence number, address, industry, manager |
| **B** | Date, time, location within the factory, fatal / non-fatal / dangerous occurrence, **and a brief description of the accident** |
| C | Injured person - name, age, sex, occupation, nature of injury, treatment |
| **D** | **Primary cause, contributing factors**, witnesses, preventive action |
| E | Manager's signature, date |

Fatal accidents must be filed within **4 hours**, others within 48. Parts B and D are free text
describing what happened and why - structurally the same object as the OSHA `Final Narrative` field
this project is built on.

So the data this method needs is not merely conceivable in India. It is **mandatory, and it is
written every time someone is seriously hurt in a registered factory.**

## 2. It is never published.

Form 18 is filed with the **state** Inspectorate of Factories, or through Shram Suvidha. Each state
holds its own. There is no central repository, and no state publishes the filings.

What *is* published, on the Open Government Data platform:

> **"Industrial Injuries in Factories"** - *All India, State wise statistics of injuries in
> factories.*

Verified: **aggregate counts by state and year.** Number of persons injured. No incident records, no
descriptions, no causes.

| | OSHA (United States) | India |
|---|---|---|
| Narrative collected by law | yes | **yes** - Form 18 Part B |
| Narrative published | **86,209 records, downloadable** | **none** |
| What is published | full incident text | counts by state and year |

**The gap is a publication decision, not a technical or linguistic one.** Nothing about Indian
workplaces, Indian English or Indian record-keeping makes this method inapplicable. The corpus is
written and then filed away.

## 3. The regulation corpus is a separate, smaller problem

DGFASLI publishes the Model Factories Rules and allied standards as PDFs. That is a real, obtainable
corpus - a PDF parse rather than the clean XML API eCFR provides, but tractable.

`dgfasli.gov.in` is denied by network policy in both the cloud workspace and the local one, the same
way `ecfr.gov` and `huggingface.co` are. This one is genuinely a workspace restriction and not a data
problem: the files can be downloaded in a browser and dropped into `data/raw/`.

## 4. Consequence for Phase 2

Phase 2 as written cannot be built, and **TASK-201 through TASK-206 are not blocked on effort or on
access - they are blocked on a corpus that does not exist in public form.**

The realistic routes, none of them an internship-sized task:

1. **RTI request** to one state Inspectorate of Factories for anonymised Form 18 narratives. Legally
   available; timeline and format unpredictable; would likely arrive as scanned PDFs.
2. **A partnership** with a state factory inspectorate or a large manufacturer willing to share its
   own filings.
3. **Court judgments** under the Employees' Compensation Act, which quote accident narratives at
   length and are public on Indian Kanoon. Heavily biased toward disputed and fatal cases, and a
   different population from routine reportable injuries.
4. **News-derived incident text**, which is biased toward the severe and the newsworthy and would not
   support the per-hazard distribution the classifier needs.

## 5. Why this is reportable rather than embarrassing

This is the **second time in this project** that the same shape of obstacle has appeared, found by
testing the premise before building on it:

| Attempt | Premise tested | Finding |
|---|---|---|
| AccessHyd (archived) | *accessibility facts are in review text* | Zero mentions of wheelchair, ramp or disabled across 10,000 reviews. The 85% automated check was false |
| SafetyLens Phase 2 | *Indian incident narratives are obtainable* | Mandatory under law, filed to 30+ state inspectorates, **published nowhere**. Only counts are public |

Both times the aggregate was public and the records were not. That is a consistent and reportable
property of the Indian open-data landscape as it touches worker safety, and it is a more useful thing
to have established than another model trained on data that was easy to get.

**It also sharpens what SafetyLens actually demonstrates.** The method is not the interesting part -
TF-IDF and a linear SVM are forty-year-old technology. What makes the system possible is that someone
decided to publish 86,209 narratives. The transferable claim is therefore about **disclosure policy**,
not about modelling: *publish the narratives and this system can be rebuilt for any jurisdiction in
a week.*

## 6. What replaces Phase 2

Recorded in `TASKS.md`:

- **TASK-210** - file an RTI request with one state Inspectorate of Factories. Slow, real, and the
  only route to the actual corpus.
- **TASK-211** - if any Form 18 narratives are obtained, measure classifier transfer honestly:
  train on OSHA, test on Indian text, report the drop. A large drop is a finding, not a failure.
- **TASK-212** - build the DGFASLI retrieval corpus from the PDFs, which needs only a browser
  download. This is worth doing **regardless of TASK-210**, because it demonstrates the retrieval
  half ports even while the classifier half waits for data.
