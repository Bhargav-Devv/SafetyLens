# Handoff — what needs you

Everything in this repository that can be done without you is done. What remains needs an account, a
browser download, a signature, or fifteen minutes of your judgement. Ordered by value.

Current state: **57 of 69 tasks**, `tests/test_refusals.py` 19/19, `tests/test_ui.py` 5/5.

---

## 1. Run the review — 15 minutes, highest value on the board  ·  TASK-307

```bash
python main.py review
```

It shows you 15 of the 50 dev incidents, one at a time: the narrative, the section I chose, and my
one-line reason. You press `y` or `n`. Progress saves after every answer, so you can quit and resume.

**Why this matters more than anything else left.** I labelled 200 incidents across four evaluation
sets, and every retrieval number in `docs/results.md` rests on those labels. I am not a safety
professional. Right now the figure has to be written *"recall@3 0.600 against an AI-labelled set"*.
After you run this it becomes *"…agreement with a second reviewer, X%"* — and if you disagree with me
a lot, that is itself the finding, and the guide gets amended and the set relabelled.

If your agreement comes out below 70%, that means the **guide** is ambiguous, not that you are wrong.
The tool says so when it happens.

**I tried to substitute for this and could not.** On 21 September I re-labelled the first fifteen dev
incidents from the narratives alone and got 15 out of 15 identical to my originals. That figure is
worthless — same labeller, same session, hours apart; it measures whether I remember what I decided,
not whether the procedure is reliable. It is recorded in `docs/limitations.md` as an invalid check
precisely so nobody reads it as validation. **Only a different person can do this one.**

---

## 2. Wire up the SafetyLens assistant  ·  TASK-111, 112, 113

Everything it needs is built and tested. Three steps:

```bash
python serve.py --spec        # writes openapi.json and prints these steps
```

1. Run `python serve.py` somewhere reachable over **HTTPS** (ngrok, Render, Railway, an IBM Code
   Engine deployment — anything with a public URL).
2. Edit `servers[0].url` in `openapi.json` to that address. Orchestrate calls whatever is in that
   field.
3. watsonx Orchestrate → Skills → Add → **Import OpenAPI**, upload `openapi.json`. You get three
   tools: `analyse_incident`, `explain_standard`, `find_similar`.
4. Paste `docs/assistant_system_prompt.md` — the block inside the fenced `text` section, verbatim — into
   the agent's instructions.

**Then do TASK-113, which is the interesting part.** Work through the scenarios in
`docs/assistant_test_scenarios.md` by hand against the hosted agent and record where it differs from
`src/agent.py`. The deterministic agent *cannot* break a refusal rule, because it has no capacity to
improvise. A language model can. **The comparison is the finding**, not a formality.

⚠ `serve.py` has no authentication. Put a gateway in front of it or keep the URL private.

---

## 3. Two browser downloads — the code is already waiting

I re-tested every route before writing this: `ecfr.gov`, `govinfo.gov`, `asrs.arc.nasa.gov`,
`dgfasli.gov.in` and `huggingface.co` are **all denied by network policy in both the cloud workspace
and the one on your laptop**, and no Chrome is connected for browser automation. I deliberately did
not use the web-fetch tool to reconstruct the corpus: that routes authoritative regulation text
through a summarising model, which is the one thing ADR-001 forbids outright.

Both are blocked here by network policy, not by anything missing in the project.

### 29 CFR 1926 — construction  ·  TASK-309

```
https://www.ecfr.gov/api/versioner/v1/full/2026-01-01/title-29.xml?part=1926
```

Save it, then:

```bash
python main.py add-part 1926 path/to/the-file.xml
```

Parsed, validated and merged into the index. Tested against eCFR-shaped XML, including the guard that
it will not cache an empty corpus. **Why it matters:** the OSHA dataset is full of construction work,
and two incidents in the evaluation sets currently score `out_of_scope` because the governing
standard lives in a Part this build has never had.

### DGFASLI Model Factories Rules  ·  TASK-212

```
https://dgfasli.gov.in/public/Admin/Cms/AllPdf/Model_Factories_Rules_as_on_15_12_2020.pdf
```

Drop it in `data/raw/` and tell me — this one is a PDF, so it needs an extraction step I have not
written blind. Worth doing even though the Indian *narratives* are unobtainable: it demonstrates the
retrieval half ports to another jurisdiction while the classifier half waits for data.

---

## 4. File the RTI request  ·  TASK-210

`docs/rti_application_draft.md` is written and ready — addressed, worded to survive the three usual
grounds for refusal, with the redaction request built in so Section 8(1)(j) cannot be used against
it. Fill in the bracketed fields, enclose ₹10, send.

**Every outcome is reportable**, including a refusal. The project's claim is about disclosure policy,
so a refusal letter is evidence *for* the argument rather than an obstacle to it. The draft has a
table of what each possible answer means.

---

## 5. Find a safety professional  ·  backlog

One conversation with a practising safety officer, walking through ten real outputs, would be worth
more than another thousand labelled incidents. It is the only way `docs/limitations.md` stops having
to say the labels are mine.

---

## Deliberately not done, with reasons

| | Why |
|---|---|
| **TASK-316 / 317** — two new known-gap candidates | A utility task vehicle rollover and a combustible dust explosion, both with no governing 1910 section. Found on evaluation sets that are spent, so fixing them against those sets is the exact mistake ADR-017 exists to prevent. Needs a fifth set |
| **Multi-label events** | Measured first: only **6.5%** of incidents have a top-two group margin below 1.0, median 2.458, and the worst 1.3% are already abstained on. Real but narrow. `docs/results.md` |
| **TASK-302b** — sentence embeddings | huggingface.co denied by policy in both workspaces. LSA is the substitute and it works (ADR-018); it is a baseline, not a ceiling |
| **A fifth evaluation set** | Would be needed before any further retrieval change. Four is already a lot of my judgement in one place — §1 above is worth more than a fifth set |

---

## If you only do one thing

Run `python main.py review`. Everything else on this page can wait; that one changes what the project
is allowed to claim.
