"""Offline tests for the optional TASK-302b sentence-transformer path."""
from __future__ import annotations

import numpy as np

import config as cfg
from src import retrieval


class FakeEncoder:
    """Deterministic encoder with no network or PyTorch dependency."""

    def encode(self, texts, **kwargs):
        assert kwargs["normalize_embeddings"] is True
        vectors = []
        for text in texts:
            lower = text.lower()
            vector = np.array([
                float("conveyor" in lower or "machine" in lower),
                float("ladder" in lower or "fall" in lower),
            ])
            norm = np.linalg.norm(vector)
            vectors.append(vector / norm if norm else np.array([1.0, 0.0]))
        return np.vstack(vectors)


def _standards():
    return [
        {"section": "1910.212", "title": "General requirements for all machines",
         "text": "Machine guarding for points of operation and moving parts."},
        {"section": "1910.23", "title": "Ladders",
         "text": "Requirements for ladders and protection from falls."},
    ]


def test_dense_index_scores_normalised_cosine_without_external_dependency():
    index = retrieval.SentenceTransformerIndex(
        ["machine conveyor", "ladder fall"], encoder=FakeEncoder())
    scores = index.scores("employee caught in conveyor machine")
    assert scores[0] == 1.0
    assert scores[0] > scores[1]


def test_default_standards_index_does_not_load_sentence_transformer():
    index = retrieval.StandardsIndex(_standards())
    assert cfg.USE_SENTENCE_TRANSFORMER is False
    assert index.dense is None


def test_dense_experiment_preserves_routing_and_returns_corpus_index(monkeypatch):
    index = retrieval.StandardsIndex(_standards())
    index.dense = retrieval.SentenceTransformerIndex(
        ["machine conveyor", "ladder fall"], encoder=FakeEncoder())
    monkeypatch.setattr(cfg, "USE_SENTENCE_TRANSFORMER", True)
    found = index.search_for_hazard(
        "employee caught in conveyor machine",
        "Contact with objects and equipment",
        k=1,
    )
    assert found[0][0] == 0
    assert index.standards[found[0][0]]["section"] == "1910.212"
