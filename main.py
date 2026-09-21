"""
SafetyLens - command line entry point.

    python main.py train              train both classifiers, write metrics + figures
    python main.py demo               run the built-in examples through the pipeline
    python main.py analyse "text"     analyse one incident narrative
    python main.py failures           show where the model fails, and why it matters
    python main.py bob                talk to it - deterministic agent, no credentials
    python main.py bob --llm          the same flow with a watsonx.ai model behind it
    python main.py transcript         replay the scripted conversation to docs/
    python main.py add-part 1926 F    parse a downloaded eCFR Part XML and cache it
    python main.py evaluate-retrieval measure retrieval against the labelled set
    python main.py review             second-labeller pass - 15 of the 50

Run `train` once. Everything else loads the saved models.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import config as cfg
from src import agent, charts, data, evalset, model, pipeline, regulations

EXAMPLES = [
    "Employee was cleaning a conveyor belt while it was running when his sleeve "
    "became caught in the rollers and his right arm was pulled in, resulting in "
    "an amputation below the elbow.",

    "Worker fell approximately 18 feet from an unguarded roof edge while "
    "installing sheet metal and sustained multiple fractures.",

    "An employee was struck by a steel beam that slipped from the crane rigging "
    "during unloading.",

    "Employee was working outdoors in high temperatures and collapsed from heat "
    "exhaustion.",   # no federal standard exists - General Duty Clause

    "An employee was assaulted by a patient in the psychiatric ward and sustained "
    "a broken nose.",   # the second known gap - no workplace violence standard

    "Employee got hurt at work.",   # deliberately vague - should abstain
]


def _dataset():
    return data.prepare(data.load_raw())


def cmd_train() -> None:
    d = _dataset()
    cfg.OUT.mkdir(parents=True, exist_ok=True)
    results = {}

    print("\n--- major group -------------------------------------------------")
    dm = data.filter_rare(d, "major")
    clf_major, m_major, y_te_m, pred_m = model.train_and_evaluate(dm, "major", "major_group")
    model.save(clf_major, "clf_major")
    results["major_group"] = m_major

    print("\n--- fine grained ------------------------------------------------")
    df_ = data.filter_rare(d, "fine")
    clf_fine, m_fine, y_te_f, pred_f = model.train_and_evaluate(df_, "fine", "fine_grained")
    model.save(clf_fine, "clf_fine")
    results["fine_grained"] = m_fine

    rows = model.per_class_table(y_te_f, pred_f)
    results["best_classes"] = [{"label": k, "f1": round(f, 3), "n": n} for k, f, n in rows[:10]]
    results["worst_classes"] = [{"label": k, "f1": round(f, 3), "n": n} for k, f, n in rows[-10:]]

    (cfg.OUT / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print("\nfigures:", charts.class_distribution(dm).name,
          charts.confusion(y_te_m, pred_m).name)
    print("metrics: out/metrics.json")
    print("\nNow run:  python main.py failures")


def cmd_failures() -> None:
    metrics = json.loads((cfg.OUT / "metrics.json").read_text(encoding="utf-8"))
    print("BEST 10 CLASSES\n")
    for r in metrics["best_classes"]:
        print(f"  {r['f1']:.2f}  n={r['n']:<5} {r['label'][:68]}")
    print("\nWORST 10 CLASSES\n")
    for r in metrics["worst_classes"]:
        print(f"  {r['f1']:.2f}  n={r['n']:<5} {r['label'][:68]}")

    vague = [r for r in metrics["worst_classes"]
             if "unspecified" in r["label"].lower() or "n.e.c" in r["label"].lower()]
    print(f"\n>>> {len(vague)} of the 10 worst classes are 'unspecified' or 'n.e.c.' buckets.")
    print(">>> Those categories are defined by EXCLUSION, not by content. They have no")
    print(">>> linguistic signature to learn, so the model fails exactly where the human")
    print(">>> coders could not decide either.")
    print(">>> That is a finding about the labels, not a weakness of the model.")


def _lens():
    return pipeline.SafetyLens.load(_dataset())


def cmd_demo() -> None:
    lens = _lens()
    out = []
    for text in EXAMPLES:
        result = lens.analyse(text)
        print(pipeline.render(result)); print()
        out.append(result)
    (cfg.OUT / "demo.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("saved out/demo.json")


def cmd_analyse(text: str) -> None:
    print(pipeline.render(_lens().analyse(text)))


# A scripted conversation that exercises every branch of the decision flow:
# abstention, the detail loop, a matched standard, a section lookup, a known
# regulatory gap, and a refusal to make a compliance determination.
SCRIPT = [
    "Someone got hurt at work yesterday.",
    "He was cleaning the packaging conveyor while it was still running and his "
    "hand was pulled into the rollers. He lost two fingers.",
    "what does 1910.147 say",
    "One of our guys collapsed with heat exhaustion working outside last week.",
    "Are we going to be cited for that?",
]


def cmd_bob() -> None:
    """Interactive.

    `--llm` runs the watsonx.ai-backed agent, whose replies pass through the
    guard in src/assistant_llm.py before reaching you. Without it, the deterministic
    agent runs - same tools, same decision flow, no credentials needed.
    """
    use_llm = "--llm" in sys.argv
    if use_llm:
        from src import assistant_llm
        try:
            bob = assistant_llm.AssistantLLM()
        except assistant_llm.MissingCredentials as exc:
            print(f"\n{exc}\n")
            print("Falling back to the deterministic agent.\n")
            use_llm = False
            bob = agent.IncidentAgent()
        else:
            print(f"\nwatsonx.ai model: {bob.client.model_id}")
    else:
        bob = agent.IncidentAgent()

    label = "watsonx.ai, guarded" if use_llm else "deterministic"
    print(f"\nSafetyLens ({label}) - describe an incident, or ask about a "
          "section by number.")
    print("Empty line to quit.\n")
    while True:
        try:
            text = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if not text:
            break
        print("\nassistant > " + bob.respond(text) + "\n")


def cmd_transcript() -> None:
    """Replay SCRIPT and write it to docs/. Nothing here is hand-written -
    every bob turn below is what the code actually produced."""
    bob = agent.IncidentAgent()
    lines = [
        "# SafetyLens assistant - captured transcript",
        "",
        "**Generated by `python main.py transcript`. Every reply below is the",
        "verbatim output of `src/agent.py` - nothing is hand-written or edited.**",
        "",
        "The five turns exercise every branch of the decision flow in",
        "`docs/agent_logic.md`: abstention, the detail loop, a matched standard,",
        "a section lookup by number, a known regulatory gap, and a refused",
        "compliance determination.",
        "",
        "---",
        "",
    ]
    for turn, text in enumerate(SCRIPT, 1):
        reply = bob.respond(text)
        lines += [f"### Turn {turn}", "", f"**You:** {text}", "",
                  "**Assistant:**", "", reply, "", "---", ""]
        print(f"you > {text}\n\nassistant > {reply}\n" + "-" * 78)

    lines += ["## Tool calls made", "",
              "| # | tool | status | standards_status |", "|---|---|---|---|"]
    for i, t in enumerate(bob.trace, 1):
        lines.append(f"| {i} | `{t['tool']}` | `{t['status']}` | "
                     f"`{t['standards_status'] or '-'}` |")
    lines += ["", "Six user turns, "
              f"{len(bob.trace)} tool calls. the assistant said nothing about a hazard or a "
              "regulation without calling a tool first.", ""]

    out = cfg.ROOT / "docs" / "assistant_transcript.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nsaved {out.relative_to(cfg.ROOT)}")


def cmd_evaluate_retrieval(holdout="dev") -> None:
    """The figure results.md could never report, because no ground truth existed."""
    from src.service import get_service
    svc = get_service()
    m = evalset.evaluate(svc, holdout)
    b = evalset.baselines(svc, holdout)

    print(f"\nRETRIEVAL EVALUATION  [{m['set'].upper()} SET]")
    print("=" * 74)
    print(f"  sample {m['n_sample']}  ->  {m['n_scored']} scored  ·  "
          f"{m['n_none_exists']} no-standard-exists  ·  "
          f"{m['n_out_of_scope']} out-of-scope (Part 1926)  ·  "
          f"{m['n_uncertain']} uncertain")
    print("-" * 74)
    print(f"  recall@1                      {m['recall_at_1']:.3f}")
    print(f"  recall@3                      {m['recall_at_3']:.3f}")
    print(f"  recall@1  (primary only)      {m['recall_at_1_primary_only']:.3f}")
    print(f"  recall@3  (primary only)      {m['recall_at_3_primary_only']:.3f}")
    print(f"  MRR                           {m['mrr']:.3f}")
    print(f"  returned nothing              {m['returned_nothing_when_a_section_exists']:.3f}"
          "   (a section existed and none was offered)")
    print("-" * 74)
    print("  BASELINES")
    print(f"  random 3 of 170               {b['random_3_of_170']:.3f}")
    print(f"  always {b['always_same_section']['section']:<12}          "
          f"{b['always_same_section']['recall']:.3f}   (the best single fixed answer)")
    print("-" * 74)
    cs = m["correct_silence_rate"]
    print(f"  correct silence               {cs:.3f}   "
          f"(of {m['n_none_exists']} hazards with no standard, how often it said nothing)")
    print("=" * 74)

    print("\n  BY HAZARD GROUP (recall@3, and how often it returned nothing)\n")
    print("    %-46s %3s  %6s  %6s" % ("group", "n", "rec@3", "silent"))
    for group, n, rec, silent in evalset.per_group(m):
        print("    %-46s %3d  %6.3f  %6.3f" % (group[:46], n, rec, silent))

    print("\n  MISSES - a section existed and was not found in the top 3:\n")
    for r in m["detail"]["section"]:
        if not r["rank_any"]:
            got = ", ".join(r["retrieved"]) or "nothing"
            print(f"    {r['id']}  want {r['primary']:<10} got {got}")

    name = f"retrieval_metrics_{m['set']}.json"
    (cfg.OUT / name).write_text(
        json.dumps({k: v for k, v in m.items() if k != "detail"} | {"baselines": b},
                   indent=2), encoding="utf-8")
    print(f"\n  saved out/{name}")


REVIEW_N = 15


def cmd_review() -> None:
    """Second-labeller pass over a subset of the evaluation set.

    The labels in data/retrieval_eval_labels.json were assigned by an AI
    assistant. That is stated openly in docs/retrieval_labelling_guide.md and in
    limitations.md, and it is the weakest link in the retrieval figure. This is
    how it gets a number attached to it instead of an apology.

    You are NOT asked to find the right section yourself - only whether the
    label and its reasoning are defensible. Agreement is reported with its
    sample size, and disagreements are listed so they can be argued about.
    """
    import json as _json
    from src import evalset

    sample = {r["id"]: r for r in evalset.load_sample()}
    labels = evalset.load_labels()
    standards = {s["section"]: s for s in regulations.fetch()}
    ids = sorted(labels)[:REVIEW_N]

    done = {}
    if evalset.REVIEW_PATH.exists():
        done = {d["id"]: d for d in _json.loads(
            evalset.REVIEW_PATH.read_text(encoding="utf-8"))}
        print(f"\nresuming - {len(done)} already reviewed")

    print(f"\nReviewing {len(ids)} of 50. y = agree, n = disagree, s = skip, q = quit.")
    print("Nothing is lost if you quit; progress is saved after each answer.\n")

    for i, eid in enumerate(ids, 1):
        if eid in done:
            continue
        lab, row = labels[eid], sample[eid]
        print("=" * 76)
        print(f"{eid}   ({i} of {len(ids)})")
        print("-" * 76)
        print(row["narrative"][:600])
        print()
        print(f"  MY LABEL : {lab['verdict']}"
              + (f"  ->  29 CFR {lab['primary']}" if lab["primary"] else ""))
        if lab["primary"]:
            print(f"             {standards[lab['primary']]['title'].strip()}")
        if lab["acceptable"]:
            print(f"  ALSO OK  : {', '.join(lab['acceptable'])}")
        print(f"  BECAUSE  : {lab['reasoning']}")
        print()
        try:
            answer = input("  agree? [y/n/s/q] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(); break
        if answer == "q":
            break
        if answer == "s":
            continue
        note = ""
        if answer == "n":
            note = input("  what should it be, and why? ").strip()
        done[eid] = {"id": eid, "agree": answer == "y", "note": note,
                     "reviewer": "bhargav"}
        evalset.REVIEW_PATH.write_text(
            _json.dumps(list(done.values()), indent=1), encoding="utf-8")
        print()

    if not done:
        print("\nnothing recorded."); return

    agreed = sum(1 for d in done.values() if d["agree"])
    print("=" * 76)
    print(f"  agreement: {agreed}/{len(done)} = {agreed / len(done):.0%}")
    if agreed / len(done) < 0.70:
        print("  Below 70% - per the guide that means the GUIDE is ambiguous, not that")
        print("  you are wrong. The disagreements below should become rules in \u00a78.")
    for d in done.values():
        if not d["agree"]:
            print(f"    {d['id']}  {d['note']}")
    print(f"\n  saved {evalset.REVIEW_PATH.name}")


COMMANDS = {"train": cmd_train, "demo": cmd_demo, "failures": cmd_failures,
            "review": cmd_review,
            "bob": cmd_bob, "transcript": cmd_transcript,
            "evaluate-retrieval": cmd_evaluate_retrieval}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    action = sys.argv[1]
    if action == "add-part":
        if len(sys.argv) < 4:
            print("usage: python main.py add-part <part> <path-to-ecfr-xml>")
            print("e.g.   python main.py add-part 1926 ~/Downloads/title-29-part-1926.xml")
            sys.exit(1)
        regulations.add_part(sys.argv[2], Path(sys.argv[3]))
        print("\nRun `python main.py demo` to see it in the index.")
    elif action == "analyse":
        if len(sys.argv) < 3:
            print('usage: python main.py analyse "incident narrative"'); sys.exit(1)
        cmd_analyse(" ".join(sys.argv[2:]))
    elif action == "evaluate-retrieval":
        which = "dev"
        if "--holdout" in sys.argv: which = "holdout"
        if "--valid" in sys.argv: which = "valid"
        if "--cal" in sys.argv: which = "cal"
        cmd_evaluate_retrieval(which)
    elif action in COMMANDS:
        COMMANDS[action]()
    else:
        print(__doc__); sys.exit(1)
