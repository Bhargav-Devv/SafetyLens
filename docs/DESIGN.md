# Design System

*DESIGN = HOW IT SHOULD LOOK AND FEEL.*

SafetyLens has **no user interface today**. Its output is a text report. So this document has two
clearly separated parts:

- **Part 1 — Output format standards.** Live, enforced in `src/pipeline.py::render`.
- **Part 2 — UI specification.** **BUILT 2026-09-20** as `app.py` (`streamlit run app.py`), with `tests/test_ui.py` asserting all five required states. One deliberate deviation, recorded in Part 2.

---

# Part 1 — Output format standards  *(live)*

## Principles

1. **Uncertainty is visible, never hidden.** Every classification carries its margin. Every retrieved
   standard carries its match score.
2. **A quoted regulation always looks like a quotation.** Section number, title, then the text in
   quotation marks. It must never be possible to mistake a quote for the system's own words.
3. **A refusal is a first-class output**, formatted as deliberately as an answer — not an error.
4. **Nothing is padded.** If a field is unknown, the report says so rather than omitting it.

## Report structure

```
================================================================================
INCIDENT: <narrative, truncated to 220 chars>
--------------------------------------------------------------------------------
GROUP    : <major event group>   (margin 3.857)
SPECIFIC : <fine-grained event>  (margin 1.511)
ALSO     : [(runner-up, score), (runner-up, score)]

APPLICABLE STANDARDS - quoted from eCFR, not generated:

  29 CFR 1910.219 - § 1910.219 Mechanical power-transmission apparatus.   [match 0.159]
   "(a) General requirements. (1) This section covers all types and shapes of…"

SIMILAR PAST INCIDENTS:
  - <narrative, truncated to 200 chars>
================================================================================
```

## Rules

| Element | Rule |
|---|---|
| Section header | `29 CFR <number> - <title>` followed by `[match <score>]` |
| Quoted text | Always wrapped in `"…"`, always followed by `…` when truncated |
| Provenance line | The phrase **"quoted from eCFR, not generated"** appears above every standards block |
| Margins | Always shown, always to 3 decimal places, never converted to a percentage |
| Refusal | `NOT CLASSIFIED (margin 0.236)` plus a request naming what detail is missing |
| No match | `APPLICABLE STANDARDS: none above the match floor.` plus the reason |
| Truncation | 220 chars for narratives, 200 for similar incidents, 380 for quotes |

## Language

- State the limitation, don't apologise for it. "No section matched above the floor" — not "Sorry, I
  couldn't find…"
- Never use "probability" for a margin. It is a margin.
- Never tell the user what to do about compliance. Report what the standard requires.

## Figures

Used in `src/charts.py` and the report deck.

| Token | Value | Use |
|---|---|---|
| Accent | `#E8A33D` | Primary series, emphasis |
| Ink | `#1C2127` | Text, dark surfaces |
| Ink soft | `#2B333C` | Secondary text |
| Steel | `#5B7B95` | Secondary series |
| Muted | `#6B7682` | Axis labels, captions |
| Good | `#3E9D6E` | Confident margins |
| Warn | `#C25A3A` | Abstention, failing classes |
| Grid | `#EDEFF2` | Gridlines only |

Chart rules: horizontal bars for category counts, value labels on every bar, no top or right spine,
gridlines on the value axis only, no chart title when the slide or section already carries one.

---

# Part 2 — UI specification  *(BUILT)*

Implemented in `app.py`. Run it with `streamlit run app.py`. `tests/test_ui.py` drives it headlessly
through Streamlit's `AppTest` and asserts each required state — 5 tests, all passing.

**Deviation from this spec, deliberate.** Below, the regulation card is specified to carry a *match
score*. ADR-019 established that the ranking score is a lexical/latent blend carrying a 1.5x–3.4x
routing multiplier: comparable within one result, meaningless across incidents, and not a measure of
fit. Rendering it as "match 0.30" would be exactly the kind of number that looks authoritative and is
not. **The card shows rank plus the calibrated lexical score instead**, matching what `src/agent.py`
says in words. The spec is left as written so the change is visible.

## Intended style

Utilitarian, high-contrast, legible on a phone in a workshop. Closer to an instrument panel than a
consumer app. No decorative imagery.

## Palette

| Token | Value |
|---|---|
| Primary | `#1C2127` |
| Surface | `#FFFFFF` |
| Surface raised | `#F4F5F7` |
| Accent | `#E8A33D` |
| Border | `#DDE1E6` |
| Text | `#1C2127` |
| Text muted | `#6B7682` |
| Confirmed | `#3E9D6E` |
| Caution | `#C25A3A` |

## Typography

Body and UI: **Inter**. Regulation citations, section numbers and margins: a monospace face —
citations must be visually distinct from prose.

| Element | Size | Weight |
|---|---|---|
| Page title | 32px | 700 |
| Section header | 20px | 600 |
| Body | 15px | 400 |
| Citation / margin | 13px | 500 mono |
| Caption | 12px | 400 muted |

## Components

- **Incident input** — multiline, no character limit, placeholder showing a real narrative
- **Hazard result card** — group and specific event, each with its margin rendered as a labelled bar
- **Regulation card** — section number, title, verbatim quote, match score, expand for full text.
  Carries the "quoted from eCFR" provenance line permanently.
- **Similar incidents list** — narrative excerpt plus hazard label
- **Refusal state** — visually distinct from both a result and an error; names the missing detail

Radius 8px. No shadows on regulation cards — a quote should read as a document, not a widget.

## Required states

Every view must define: loading · empty · **refusal** · error · result.

**Refusal is not an error state.** It must not use error styling, an error icon, or apologetic
language. It is a correct outcome.

## Accessibility

WCAG 2.2 AA. Status never conveyed by colour alone — every margin and match score carries its number.
Keyboard operable throughout. Minimum 4.5:1 text contrast.
