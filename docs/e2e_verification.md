# End-to-end verification — 2026-10-24

This record distinguishes locally verified behavior from external submission evidence.

## Environment

- Python 3.13.5.
- `python -m pip check`: no broken requirements after pinning the compatible FastAPI/Starlette
  service stack.
- `.env` contains the four required watsonx variable names; values were not printed or committed.
- Saved major and fine classifiers load from `out/`.
- Service health reports 369 OSHA sections and 86,204 indexed incidents.

## HTTP API

The service was started with `python -u serve.py` and checked over localhost.

- `GET /health`: 200 and `ready: true`.
- Detailed conveyor narrative: 200, classified as contact with objects/equipment, with lead citation
  `29 CFR 1910.219` and verbatim eCFR provenance.
- `Employee got hurt at work.`: 200 with `status: abstained`; margin 0.237 is below the 0.30 floor.
- Empty narrative: 200 with `status: insufficient_input`.
- Missing or non-string narrative: 422 schema validation.
- Unknown section `9999.999`: 200 with `status: not_found` and no regulation text.

## Streamlit

The interface was started with `python -m streamlit run app.py --server.headless true
--server.port 8501` and exercised in a browser.

- Initial page and empty state rendered.
- Empty submission displayed `Enter a narrative before analysing.`
- A detailed conveyor narrative displayed the hazard and specific event, both margins and floors,
  three ranked standards with eCFR provenance, three similar incidents, and the decision-support
  disclaimer.
- The vague narrative above displayed `NOT CLASSIFIED`, the 0.237 margin, the 0.30 floor, and prompts
  for the missing detail.

## Known limitation preserved

The combined OSHA index can rank a Part 1926 construction section for a narrative that does not say
whether the work is construction or general industry. In the conveyor check, Part 1910.219 ranked
first and Part 1926.307 ranked second. This is reported rather than tuned on spent evaluation sets;
future routing changes require a new untouched evaluation set.

## Evidence still requiring the user

- TASK-210: the applicant must file the prepared RTI request, pay the required fee, and retain the
  receipt. TASK-211 depends on narratives being returned.
- Four IBM Bob screenshots described in `docs/ibm_bob_usage.md`; these must come from the desktop
  application and must show the actual scan/test results.
