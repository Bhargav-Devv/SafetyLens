# Problem Statement

**Bhargav Rao Mahankali** - St Peter's Engineering College
1M1B x IBM SkillsBuild, AI for Sustainability Virtual Internship, 2026

## The problem

Severe workplace injuries repeat. The same accident - a worker caught in an unguarded machine, a fall
from an unprotected edge - happens again and again across different employers, for the same reasons.

The reports describing exactly how each one happened already exist. OSHA holds **86,209** of them from
January 2015 to September 2023, each a plain-English narrative written by the employer within 24 hours
of the event.

Nobody reads them. They sit in a spreadsheet.

## The second gap

Even when someone does read a report, knowing what happened is not enough to prevent the next one.
Prevention requires knowing **which safety standard applies and what it requires** - and that lives in
thousands of pages of 29 CFR that no floor supervisor has ever opened.

So two bodies of knowledge exist, and they never meet:

| | Where it lives | Who reads it |
|---|---|---|
| What happened | 86,209 incident narratives | Nobody, systematically |
| What should have been done | 29 CFR Part 1910 | Specialists only |

## Who is affected

Workers at small and mid-size employers - the ones with no safety department, no compliance officer,
and no in-house counsel. A large manufacturer has people whose job is reading regulations. A
twelve-person workshop has an owner who also drives the forklift.

## Why AI

Both halves are tractable problems that happen to need different techniques:

- Reading 86,000 narratives and assigning a hazard category is **text classification with abundant
  human labels** - a solved problem applied to a job nobody has done.
- Finding the applicable standard is **retrieval over a fixed authoritative corpus** - also solved.

Neither half is research. The contribution is joining them so the output is actionable rather than
merely descriptive.

## SDG alignment

**SDG 8.8** - Protect labour rights and promote safe and secure working environments for all workers.

## Non-goals

- Determining compliance or liability. The output is decision support for a human.
- Predicting *whether* an injury will occur. This system explains incidents that already happened.
- Replacing a safety professional.
