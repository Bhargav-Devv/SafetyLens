"""
The classifier.

TF-IDF over word AND character n-grams, then a linear SVM.

Character n-grams matter here: narratives are full of equipment names, model
numbers and typos that word-level features miss entirely.

Deliberately not a transformer - it trains in minutes on CPU and on short,
formulaic incident text it is genuinely competitive. Complexity you cannot
justify is not sophistication.
"""
from __future__ import annotations

import sys
from pathlib import Path

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline, make_union
from sklearn.svm import LinearSVC

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg


def build_classifier() -> "Pipeline":
    return make_pipeline(
        make_union(
            TfidfVectorizer(
                ngram_range=(1, 2), min_df=3, sublinear_tf=True,
                strip_accents="unicode", max_features=cfg.WORD_MAX_FEATURES,
            ),
            TfidfVectorizer(
                analyzer="char_wb", ngram_range=(3, 5), min_df=5,
                sublinear_tf=True, max_features=cfg.CHAR_MAX_FEATURES,
            ),
        ),
        LinearSVC(C=cfg.SVM_C),
    )


def train_and_evaluate(data, target: str, name: str) -> tuple:
    """Train one classifier and score it against two baselines.

    A result reported without a baseline beside it is not a result.
    """
    X_tr, X_te, y_tr, y_te = train_test_split(
        data["text"], data[target],
        test_size=cfg.TEST_SIZE, random_state=cfg.SEED, stratify=data[target],
    )

    print(f"training {name}: {data[target].nunique()} classes, {len(X_tr):,} train rows")
    clf = build_classifier()
    clf.fit(X_tr, y_tr)
    pred = clf.predict(X_te)

    metrics = {
        "n_records": int(len(data)),
        "n_classes": int(data[target].nunique()),
        "accuracy": float(accuracy_score(y_te, pred)),
        "macro_f1": float(f1_score(y_te, pred, average="macro")),
        "weighted_f1": float(f1_score(y_te, pred, average="weighted")),
    }

    for strategy in ("most_frequent", "stratified"):
        dummy = DummyClassifier(strategy=strategy, random_state=cfg.SEED)
        dummy.fit(X_tr, y_tr)
        bp = dummy.predict(X_te)
        metrics[f"baseline_{strategy}"] = {
            "accuracy": float(accuracy_score(y_te, bp)),
            "macro_f1": float(f1_score(y_te, bp, average="macro")),
        }

    print(f"  accuracy {metrics['accuracy']:.3f}  "
          f"(most-frequent {metrics['baseline_most_frequent']['accuracy']:.3f})")
    print(f"  macro F1 {metrics['macro_f1']:.3f}  "
          f"(stratified    {metrics['baseline_stratified']['macro_f1']:.3f})")

    return clf, metrics, y_te, pred


def per_class_table(y_true, y_pred) -> list[tuple[str, float, int]]:
    """Per-class F1, sorted best to worst. Read the bottom of this list -
    it is where the most interesting finding in the project lives."""
    rep = classification_report(y_true, y_pred, zero_division=0, output_dict=True)
    rows = [
        (label, vals["f1-score"], int(vals["support"]))
        for label, vals in rep.items()
        if label not in ("accuracy", "macro avg", "weighted avg")
    ]
    return sorted(rows, key=lambda r: -r[1])


def top_prediction(clf, text: str) -> tuple[str, float, list]:
    """Predicted class, margin, and runners-up.

    LinearSVC has no predict_proba. Confidence is the gap between the top two
    decision scores - an honest margin, not a probability dressed up as one.
    """
    scores = clf.decision_function([text])[0]
    order = np.argsort(scores)[::-1]
    margin = float(scores[order[0]] - scores[order[1]])
    runners = [(clf.classes_[i], round(float(scores[i]), 3)) for i in order[1:3]]
    return clf.classes_[order[0]], margin, runners


def save(clf, name: str) -> None:
    cfg.OUT.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, cfg.OUT / f"{name}.joblib")


def load(name: str):
    path = cfg.OUT / f"{name}.joblib"
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run:  python main.py train")
    return joblib.load(path)
