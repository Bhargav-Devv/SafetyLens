"""
The retrieval evaluation set - sampling, loading, scoring.

`results.md` reported no accuracy figure for retrieval for one reason: nobody
had labelled which standard applies to which incident. This module builds that
missing piece.

Sampling decisions, all made before any label was written:

  * Drawn from the HELD-OUT test split (seed 42, the same split model.py uses).
    Retrieval does not train on incidents, but the classifier does, and
    retrieval is conditioned on the classifier's output - so a training-set
    narrative would flatter the whole pipeline.

  * Stratified with a floor, NOT proportionally. A proportional sample of 50
    would contain one overexertion incident and no fires. Small groups are
    over-sampled so per-group behaviour is visible. Metrics are therefore
    reported PER GROUP, and any aggregate is a mean over the sample, not an
    estimate of corpus-wide accuracy. Saying which one it is matters.

  * Minimum narrative length, because a label cannot be assigned to a sentence
    that names no mechanism. This biases the set toward richer narratives and
    the figure toward optimism; it is declared rather than hidden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg

MIN_CHARS = 60
SEED = cfg.SEED

# group -> how many to draw. Sums to 50.
ALLOCATION = {
    "Contact with objects and equipment": 14,
    "Falls, slips, trips": 10,
    "Transportation incidents": 6,
    "Exposure to harmful substances/environments": 6,
    "Violence / injury by persons or animals": 5,
    "Fires and explosions": 5,
    "Overexertion and bodily reaction": 4,
}
# Nonclassifiable is excluded: pipeline.py declines retrieval for it by design
# (ADR-009), so there is nothing to measure.

SAMPLE_PATH = cfg.DATA_DIR / "retrieval_eval_sample.json"
LABELS_PATH = cfg.DATA_DIR / "retrieval_eval_labels.json"
REVIEW_PATH = cfg.DATA_DIR / "retrieval_eval_review.json"

# The held-out set. Drawn the same way, disjoint by construction, labelled under
# the same frozen guide - and scored ONCE, after an improvement is finished.
#
# It exists because the first 50 stopped being a test set the moment anything was
# tuned against it. Reporting a tuned number on the set it was tuned against is
# the most common way an honest project starts overstating itself, and it is
# invisible in the output when it happens.
HOLDOUT_SAMPLE_PATH = cfg.DATA_DIR / "retrieval_holdout_sample.json"
HOLDOUT_LABELS_PATH = cfg.DATA_DIR / "retrieval_holdout_labels.json"
HOLDOUT_SEED = cfg.SEED + 1

# The third set. Built because both earlier sets are spent: the first was tuned
# against, the second has had its single measurement. Latent retrieval is a big
# enough change to deserve its own clean number rather than a re-reading of one.
VALID_SAMPLE_PATH = cfg.DATA_DIR / "retrieval_valid_sample.json"
VALID_LABELS_PATH = cfg.DATA_DIR / "retrieval_valid_labels.json"
VALID_SEED = cfg.SEED + 2

# The fourth set. Built for the floor-recalibration work of TASK-313, because
# the first three are spent - tuned against, and measured once each. A threshold
# that gates whether a safety claim reaches a user is exactly the kind of number
# that must not be fitted to the data it is then reported on.
CAL_SAMPLE_PATH = cfg.DATA_DIR / "retrieval_cal_sample.json"
CAL_LABELS_PATH = cfg.DATA_DIR / "retrieval_cal_labels.json"
CAL_SEED = cfg.SEED + 3


def build_sample(data) -> list[dict]:
    """Draw the sample. Deterministic - same seed, same 50 incidents."""
    from sklearn.model_selection import train_test_split

    filtered = data[data["major"].isin(ALLOCATION)]
    _, test = train_test_split(
        filtered, test_size=cfg.TEST_SIZE, random_state=SEED,
        stratify=filtered["major"],
    )
    test = test[test["text"].str.len() >= MIN_CHARS]

    rows = []
    for group, n in ALLOCATION.items():
        pool = test[test["major"] == group]
        take = pool.sample(n=min(n, len(pool)), random_state=SEED)
        for i, r in take.iterrows():
            rows.append({
                "id": f"E{len(rows) + 1:03d}",
                "narrative": r["text"],
                "true_group": r["major"],
                "true_event": r["fine"],
            })
    return rows


def build_holdout(data, dev_narratives: set[str]) -> list[dict]:
    """The second 50. Same allocation and filters; disjoint from the dev set."""
    from sklearn.model_selection import train_test_split

    filtered = data[data["major"].isin(ALLOCATION)]
    _, test = train_test_split(
        filtered, test_size=cfg.TEST_SIZE, random_state=SEED,
        stratify=filtered["major"],
    )
    test = test[test["text"].str.len() >= MIN_CHARS]
    test = test[~test["text"].isin(dev_narratives)]

    rows = []
    for group, n in ALLOCATION.items():
        pool = test[test["major"] == group]
        take = pool.sample(n=min(n, len(pool)), random_state=HOLDOUT_SEED)
        for _, r in take.iterrows():
            rows.append({
                "id": f"H{len(rows) + 1:03d}",
                "narrative": r["text"],
                "true_group": r["major"],
                "true_event": r["fine"],
            })
    return rows


def build_nth(data, used: set[str], seed: int, prefix: str) -> list[dict]:
    """Draw another set. Same allocation and filters; disjoint from `used`."""
    from sklearn.model_selection import train_test_split

    filtered = data[data["major"].isin(ALLOCATION)]
    _, test = train_test_split(
        filtered, test_size=cfg.TEST_SIZE, random_state=SEED,
        stratify=filtered["major"],
    )
    test = test[test["text"].str.len() >= MIN_CHARS]
    test = test[~test["text"].isin(used)]

    rows = []
    for group, n in ALLOCATION.items():
        pool = test[test["major"] == group]
        take = pool.sample(n=min(n, len(pool)), random_state=seed)
        for _, r in take.iterrows():
            rows.append({
                "id": f"{prefix}{len(rows) + 1:03d}",
                "narrative": r["text"],
                "true_group": r["major"],
                "true_event": r["fine"],
            })
    return rows


def build_valid(data, used: set[str]) -> list[dict]:
    """The third set. Same allocation and filters; disjoint from both others."""
    from sklearn.model_selection import train_test_split

    filtered = data[data["major"].isin(ALLOCATION)]
    _, test = train_test_split(
        filtered, test_size=cfg.TEST_SIZE, random_state=SEED,
        stratify=filtered["major"],
    )
    test = test[test["text"].str.len() >= MIN_CHARS]
    test = test[~test["text"].isin(used)]

    rows = []
    for group, n in ALLOCATION.items():
        pool = test[test["major"] == group]
        take = pool.sample(n=min(n, len(pool)), random_state=VALID_SEED)
        for _, r in take.iterrows():
            rows.append({
                "id": f"V{len(rows) + 1:03d}",
                "narrative": r["text"],
                "true_group": r["major"],
                "true_event": r["fine"],
            })
    return rows


_PATHS = {
    "dev": (SAMPLE_PATH, LABELS_PATH),
    "holdout": (HOLDOUT_SAMPLE_PATH, HOLDOUT_LABELS_PATH),
    "valid": (VALID_SAMPLE_PATH, VALID_LABELS_PATH),
    "cal": (CAL_SAMPLE_PATH, CAL_LABELS_PATH),
}


def _which(holdout) -> str:
    if holdout is True:
        return "holdout"
    if holdout in (False, None):
        return "dev"
    return str(holdout)


def load_sample(holdout=False) -> list[dict]:
    return json.loads(_PATHS[_which(holdout)][0].read_text(encoding="utf-8"))


def load_labels(holdout=False) -> dict[str, dict]:
    path = _PATHS[_which(holdout)][1]
    if not path.exists():
        return {}
    return {l["id"]: l for l in json.loads(path.read_text(encoding="utf-8"))}


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def _hit_rank(retrieved: list[str], label: dict, primary_only: bool) -> int | None:
    """1-based rank of the first acceptable section, or None."""
    targets = {label["primary"]} if primary_only else (
        {label["primary"]} | set(label["acceptable"]))
    for i, sec in enumerate(retrieved, 1):
        if sec in targets:
            return i
    return None


def evaluate(svc, holdout: bool = False) -> dict:
    """Score retrieval against the labelled set.

    Four populations, scored separately because the correct behaviour differs:

      verdict=section       a section should be retrieved -> recall@k, MRR
      verdict=none_exists   NOTHING should be retrieved   -> correct-silence rate
      verdict=out_of_scope  the standard is in Part 1926  -> reported, not scored
      verdict=uncertain     excluded entirely

    Aggregating these would let good behaviour on one hide failure on another -
    a system that retrieves nothing scores 100% on the second population and 0%
    on the first.
    """
    labels = load_labels(holdout)
    results = {"section": [], "none_exists": [], "out_of_scope": [], "uncertain": []}

    for row in load_sample(holdout):
        label = labels[row["id"]]
        analysis = svc.analyse_incident(row["narrative"])
        retrieved = [s["section"] for s in analysis.get("standards", [])]
        record = {
            "id": row["id"], "group": row["true_group"],
            "retrieved": retrieved,
            "standards_status": analysis.get("standards_status"),
            "abstained": analysis["status"] == "abstained",
            "primary": label["primary"], "acceptable": label["acceptable"],
            "rank_any": _hit_rank(retrieved, label, primary_only=False),
            "rank_primary": _hit_rank(retrieved, label, primary_only=True),
        }
        results[label["verdict"]].append(record)

    scored = results["section"]
    n = len(scored)
    if not n:
        raise RuntimeError("nothing scorable - are the labels present?")

    def recall(field: str, k: int) -> float:
        return sum(1 for r in scored if r[field] and r[field] <= k) / n

    silent = results["none_exists"]
    return {
        "set": _which(holdout),
        "n_sample": len(load_sample(holdout)),
        "n_scored": n,
        "n_none_exists": len(silent),
        "n_out_of_scope": len(results["out_of_scope"]),
        "n_uncertain": len(results["uncertain"]),
        "recall_at_1": recall("rank_any", 1),
        "recall_at_3": recall("rank_any", 3),
        "recall_at_1_primary_only": recall("rank_primary", 1),
        "recall_at_3_primary_only": recall("rank_primary", 3),
        "mrr": sum(1 / r["rank_any"] for r in scored if r["rank_any"]) / n,
        "returned_nothing_when_a_section_exists": sum(
            1 for r in scored if not r["retrieved"]) / n,
        "correct_silence_rate": (
            sum(1 for r in silent if not r["retrieved"]) / len(silent) if silent else None),
        "detail": results,
    }


def per_group(metrics: dict) -> list[tuple[str, int, float, float]]:
    """recall@3 by hazard group. The aggregate hides which half of the corpus
    works - and the answer is not the half you would guess."""
    from collections import defaultdict
    buckets = defaultdict(list)
    for r in metrics["detail"]["section"]:
        buckets[r["group"]].append(r)
    rows = []
    for group, rs in buckets.items():
        hits = sum(1 for r in rs if r["rank_any"])
        silent = sum(1 for r in rs if not r["retrieved"])
        rows.append((group, len(rs), hits / len(rs), silent / len(rs)))
    return sorted(rows, key=lambda r: -r[2])


def baselines(svc, holdout: bool = False) -> dict:
    """What the number has to beat.

    A retrieval metric without a baseline is the same mistake as a classifier
    accuracy without one - and 170 sections makes random look worse than it is
    until you write it down.
    """
    import random

    labels = load_labels(holdout)
    scored = [(r, labels[r["id"]]) for r in load_sample(holdout)
              if labels[r["id"]]["verdict"] == "section"]
    sections = [s["section"] for s in svc.lens.standards]
    rng = random.Random(SEED)

    def targets(l): return {l["primary"]} | set(l["acceptable"])

    random_hits = sum(
        1 for _, l in scored
        if targets(l) & set(rng.sample(sections, cfg.N_STANDARDS)))

    # The single section that would score best if returned for every incident.
    best_fixed, best_hits = None, 0
    for candidate in set(sections):
        hits = sum(1 for _, l in scored if candidate in targets(l))
        if hits > best_hits:
            best_fixed, best_hits = candidate, hits

    n = len(scored)
    return {
        "random_3_of_170": random_hits / n,
        "always_same_section": {"section": best_fixed, "recall": best_hits / n},
    }
