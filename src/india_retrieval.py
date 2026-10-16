"""Separate retrieval index for the DGFASLI Model Factories Rules."""
from __future__ import annotations

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src import indian_regulations


class IndianRulesIndex:
    def __init__(self, payload: dict):
        self.provenance = payload["provenance"]
        self.sections = payload["sections"]
        documents = [f"{section['title']} " * 8 + section["text"]
                     for section in self.sections]
        self.vectorizer = TfidfVectorizer(
            lowercase=True, stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        )
        self.matrix = self.vectorizer.fit_transform(documents)

    @classmethod
    def load(cls) -> "IndianRulesIndex":
        return cls(indian_regulations.load_model_rules())

    def search(self, query: str, k: int = 3) -> list[dict]:
        if not isinstance(query, str) or not query.strip():
            return []
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = scores.argsort()[::-1][:max(0, k)]
        results = []
        for rank, index in enumerate(ranked, 1):
            section = self.sections[int(index)]
            results.append({
                "rank": rank,
                "rule": section["rule"],
                "title": section["title"],
                "text": section["text"],
                "page_start": section["page_start"],
                "page_end": section["page_end"],
                "score": float(scores[index]),
                "source": self.provenance["document"],
                "authority": self.provenance["authority"],
                "source_url": self.provenance["source_url"],
                "source_sha256": self.provenance["source_sha256"],
            })
        return results
