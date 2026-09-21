# IBM Bob — how it is used on this project

**IBM Bob is IBM's AI-first IDE and pair developer** — a desktop application for macOS, Windows and
Linux, with a companion CLI called **BobShell** for terminal and CI/CD workflows. It coordinates
agents across code, tests, documentation and pipelines, with Semgrep security scanning built in.

**It is a development tool, not a component you embed in a product.**

That distinction is the reason for a correction made on 2026-09-21, and the correction is worth
stating rather than hiding.

---

## The correction

Until today this project called its own conversational layer *"IBM Bob"* — in `agent_logic.md`, in
the deck, in the tool contract, in the filenames. **That was wrong.** IBM Bob is a real IBM product
and the thing in this repository is not it: it is a tool-calling agent over the SafetyLens pipeline,
backed by a watsonx.ai model.

Everything has been renamed to **the SafetyLens assistant**. `src/assistant_tools.py`,
`src/assistant_llm.py`, `docs/assistant_system_prompt.md`, and so on. The component is unchanged and
still good; only the claim about what it is has been fixed.

A reviewer who knows IBM's product line would have spotted this in seconds, and a project whose
central discipline is *never claim something you have not verified* cannot afford to misname a
dependency on its own title slide.

---

## How Bob is used here

| Use | What it covers |
|---|---|
| **Development environment** | The repository is opened in Bob and worked on there — `config.py`, `src/`, `tests/`, the docs tree |
| **Code documentation** | Bob's documentation agent over `src/`, which is where its published tutorials focus |
| **Test generation** | The three test suites (`test_refusals.py`, `test_assistant_llm.py`, `test_ui.py`) are the natural target |
| **Security scanning** | Semgrep is built in. `serve.py` has no authentication and is the obvious thing to point it at |
| **BobShell** | The CLI, for running `python main.py train` / `demo` / `evaluate-retrieval` inside Bob's workflow |

## What to capture for the submission

Screenshots or a short recording of:

1. **The repository open in Bob** — the file tree with `src/`, `docs/` and `tests/` visible.
2. **Bob explaining a real piece of this code.** The best candidate is
   `src/retrieval.py::search_for_hazard` — it carries the two-tier routing logic and the comment
   explaining why the obvious fix was rejected. Ask Bob what it does and whether the tiering is
   sound.
3. **Bob's security scan on `serve.py`.** It should flag the missing authentication, which is a
   *known and documented* limitation — so the scan agreeing with `serve.py`'s own docstring is a
   good, honest screenshot.
4. **BobShell running `python tests/test_refusals.py`** — 22 passing.

## The honest framing for the deck

> IBM Bob was used as the development environment for this project. The conversational layer inside
> the product is a separate thing — a watsonx.ai tool-calling agent with the refusal rules enforced
> in code — and it is named the SafetyLens assistant, not Bob, because Bob is IBM's IDE and this is
> not that.

Saying that is stronger than quietly conflating the two. It shows the product line is understood,
and it is consistent with everything else in this repository: **the claim matches the artefact.**

---

## Status

- [x] IBM Bob installed (`IBM-BobUserSetup-x64-1.126.0+bob2.1.0.exe`, 2026-09-21)
- [x] Project renamed so nothing falsely claims to be Bob
- [ ] Repository opened in Bob and worked on
- [ ] Screenshots captured for the deck (the four above)
- [ ] Semgrep scan run on `serve.py`, result recorded

**The unchecked boxes need the desktop app and a person at it.** They are not blocked on code.
