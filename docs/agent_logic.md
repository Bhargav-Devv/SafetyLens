# SafetyLens assistant — agent logic specification

**Status: BUILT, as of 2026-09-20. See the boundary below.**

| Piece | Where | State |
|---|---|---|
| Orchestration | `src/pipeline.py` | built |
| Service layer | `src/service.py` | built |
| Tool contract + JSON schemas | `src/assistant_tools.py` | built |
| System prompt | `docs/assistant_system_prompt.md` | built |
| Decision flow, deterministic | `src/agent.py` | built - run `python main.py bob` |
| Refusal rules as tests | `tests/test_refusals.py` | built - 15 passing |
| Captured transcript | `docs/assistant_transcript.md` | generated, not hand-written |
| HTTP service | `serve.py` | built, smoke-tested |
| OpenAPI 3 spec | `openapi.json` | built - `python serve.py --spec` |
| **watsonx.ai agent + guard** | `src/assistant_llm.py` | **built**, 10 tests vs an adversarial model |
| Live run against a real model | - | **needs `.env`** — credentials only Bhargav has |

The one unbuilt piece is the language model itself. Everything it needs exists and is tested; what
has not happened is importing the schemas into watsonx Orchestrate and pasting in the prompt, which
requires an account this project does not have.

`src/agent.py` implements the same decision flow with the language model removed. That costs
conversational fluency and buys two things: every refusal rule becomes an assertion that runs in
seconds rather than a behaviour that can only be spot-checked, and the system runs without
credentials. See ADR-013.

Stating the boundary precisely is deliberate. "the assistant is built" and "the assistant is specified" are both wrong;
the table is what is true.

## What the assistant is for

The pipeline answers a machine-shaped question: *narrative in, structured analysis out.* A safety
officer does not ask that question. They ask:

> "A guy on the night shift got his hand caught cleaning the packaging line. What do I need to do?"

the assistant's job is to turn that into the machine's question, call the tools, and turn the answer back into
something a person can act on - without ever inventing the part that matters.

## Tools

| Tool | Input | Returns |
|---|---|---|
| `analyse_incident` | narrative text | hazard group + specific event, both with margins; applicable standards with section number, title, verbatim quote and match score; three similar past incidents |
| `explain_standard` | section number | the full verbatim text of that section from the cached eCFR corpus |
| `find_similar` | narrative text, k | k most similar past incidents with their hazard labels |

All three are thin wrappers over functions that already exist: `pipeline.SafetyLens.analyse()`,
`regulations.fetch()` and `retrieval.Index.search()`.

## Decision flow

```
user describes an incident
        |
        v
  analyse_incident
        |
        +-- margin < 0.30 ------> ask for detail. Do not classify. Do not retrieve.
        |                         "What equipment, what motion, which part of the body?"
        |
        +-- no standard above floor --> say so explicitly. Do not offer the
        |                               least-bad section as though it applied.
        |
        v
  report: hazard, quoted standard with citation, similar incidents
        |
        v
  offer the next action (not the next fact):
  "Three other employers reported this same thing while cleaning a running
   conveyor. The standard requires the machine be de-energised first."
```

## Rules the assistant cannot break

1. **Never state a regulatory requirement that did not come from `explain_standard` or
   `analyse_incident`.** the assistant quotes; it does not paraphrase regulation text, and it does not answer
   from its own knowledge of OSHA.
2. **Never convert an abstention into an answer.** If the classifier declined, the assistant asks for detail.
   It does not offer its own guess to be helpful.
3. **Never present a low-scoring retrieval as the applicable rule.** "No section matched above the
   threshold" is a complete and correct answer.
4. **Always carry the citation.** Every regulatory claim reaches the user with its section number.
5. **Never issue a compliance determination.** the assistant says what the standard requires. It does not say
   whether the employer is in violation.

## Worked exchange

> **User:** A guy on the night shift got his hand caught cleaning the packaging line.
>
> **Assistant:** *(calls `analyse_incident`)*
> That reads as **caught in running equipment during maintenance or cleaning** - the classifier is
> confident (margin 3.86).
>
> The section that applies is **29 CFR 1910.219, Mechanical power-transmission apparatus**. It opens:
> *"This section covers all types and shapes of power-transmission belts…"*
>
> Three other employers reported almost exactly this: a thumb amputation, an index finger, and a
> fractured arm - all workers cleaning a conveyor that was still running.
>
> The pattern is the machine being live during cleaning. Would you like the full text of 1910.219, or
> the lockout/tagout section it points toward?

> **User:** Someone got hurt at work yesterday.
>
> **Assistant:** *(calls `analyse_incident`, margin 0.236 - below floor)*
> I can't classify that reliably - there isn't enough in it to tell what kind of incident it was.
> What was the person doing, what equipment was involved, and which part of the body?
>
> *(the assistant does not guess. It does not retrieve a standard. It asks.)*

## What building it would take

A the assistant skill with the three tool definitions above, a system prompt carrying the five rules, and HTTP
wrappers around `pipeline.SafetyLens`. The models are already serialised in `out/`; the standards
corpus is already cached in `data/standards.json`. No retraining, no new logic - roughly an
afternoon's integration work.
