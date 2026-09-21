"""
Two indexes:

  StandardsIndex - 29 CFR 1910 sections, for "which rule applies?"
  Index          - past narratives, for "has this happened before?"

Plain TF-IDF over the standards performs badly: section bodies average ~10,000
characters, so narrative-specific words ("sleeve", "rollers") pull in whichever
industry-specific section happens to share that vocabulary. A conveyor
amputation retrieved *bakery equipment*.

Two corrections, both applied to ranking only - never to the text returned:

  1. Title weighting. Section titles are the most informative field, so they are
     repeated TITLE_WEIGHT times in the indexed document.
  2. Hazard boost. Sections whose title matches the predicted hazard vocabulary
     are boosted. This is a routing aid, not a legal claim.

And a floor: below RETRIEVAL_FLOOR the index reports no match rather than
returning its three least-bad guesses.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

sys.path.insert(0, str(Path(__file__).parent.parent))
import config as cfg


class Index:
    """Plain TF-IDF index over a list of documents."""

    def __init__(self, documents: list[str], min_df: int = 1):
        self.documents = documents
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), min_df=min_df, sublinear_tf=True,
            stop_words="english", max_features=60_000,
        )
        self.matrix = self.vectorizer.fit_transform(documents)

    def _scores(self, query: str) -> np.ndarray:
        return cosine_similarity(self.vectorizer.transform([query]), self.matrix).ravel()

    def search(self, query: str, k: int = 3) -> list[tuple[int, float]]:
        s = self._scores(query)
        return [(int(i), float(s[i])) for i in s.argsort()[::-1][:k]]


class LatentIndex:
    """Truncated SVD over TF-IDF - latent semantic indexing.

    Fitted on the standards corpus PLUS a sample of incident narratives. That
    mixture is the whole point: fitting on 170 regulation sections alone would
    learn regulation-to-regulation structure and leave the narrative vocabulary
    exactly as foreign as it was. Mixing the narratives in means "cleaning",
    "rollers" and "jam" appear in the same fitted space as "servicing",
    "maintenance" and "energy isolating device", and the SVD can put them on
    shared dimensions because they describe the same events.

    Scores are cosine similarities in the reduced space, rescaled to [0, 1] so
    they can be blended with the lexical scores rather than replacing them.
    Lexical matching is precise when the words happen to line up; latent
    matching degrades gracefully when they do not. Neither is reliable alone.
    """

    def __init__(self, documents: list[str], extra_corpus: list[str]):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.preprocessing import Normalizer

        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 1), min_df=2, sublinear_tf=True,
            stop_words="english", max_features=60_000,
        )
        fit_on = list(documents) + list(extra_corpus)
        self.vectorizer.fit(fit_on)

        n_components = min(cfg.LSA_COMPONENTS, len(self.vectorizer.vocabulary_) - 1)
        self.svd = TruncatedSVD(n_components=n_components, random_state=cfg.SEED)
        self.svd.fit(self.vectorizer.transform(fit_on))
        self.normalizer = Normalizer(copy=False)

        self.matrix = self._embed(documents)
        self.explained = float(self.svd.explained_variance_ratio_.sum())

    def _embed(self, texts: list[str]) -> np.ndarray:
        return self.normalizer.fit_transform(
            self.svd.transform(self.vectorizer.transform(texts)))

    def scores(self, query: str) -> np.ndarray:
        raw = cosine_similarity(self._embed([query]), self.matrix).ravel()
        # Cosine in a latent space runs negative; TF-IDF cosine does not. Shift
        # to [0, 1] so a blend of the two is not quietly dominated by sign.
        return (raw + 1.0) / 2.0


class StandardsIndex(Index):
    """TF-IDF over regulation sections, with title weighting and hazard boost."""

    def __init__(self, standards: list[dict]):
        self.standards = standards
        self.titles = [s["title"].lower() for s in standards]
        self.scopes = [s["text"][:cfg.ROUTING_SCOPE_CHARS].lower() for s in standards]
        documents = [((s["title"] + " ") * cfg.TITLE_WEIGHT) + s["text"]
                     for s in standards]
        super().__init__(documents, min_df=1)
        self.latent: "LatentIndex | None" = None

    def fit_latent(self, narratives) -> None:
        """Build the latent index. Optional - the lexical path works without it."""
        if not cfg.USE_LSA:
            return
        sample = list(narratives)[:cfg.LSA_FIT_NARRATIVES]
        self.latent = LatentIndex(self.documents, sample)

    @staticmethod
    def _apply_floor(candidates: list[int], scores: np.ndarray) -> list[int]:
        """Keep only candidates that stand above the field for THIS query.

        The old absolute floor cannot work on the current score: it is a
        lexical/latent blend on a different scale (ADR-019) and is then
        multiplied by a routing boost of 1.5x-3.4x, so the number mostly encodes
        how a section was routed. A fixed threshold on that is meaningless - it
        admitted everything.

        A sigma cut asks a question the score can actually answer: does this
        section stand out from the other candidates for this narrative? That is
        scale-free, so it survives any future change to the blend, and it
        degrades the right way - when nothing stands out, nothing is returned.
        """
        if not candidates:
            return candidates
        if not cfg.USE_SIGMA_FLOOR:
            return [i for i in candidates if scores[i] >= cfg.RETRIEVAL_FLOOR]
        if len(candidates) < 3:
            return candidates
        v = scores[candidates]
        sd = v.std()
        if sd == 0:
            return candidates
        cut = v.mean() + cfg.FLOOR_SIGMA * sd
        kept = [i for i in candidates if scores[i] >= cut]
        return kept

    @staticmethod
    def _keyword_hits(title: str, keywords: list[str]) -> int:
        """Count DISTINCT hazard concepts named in a title.

        A keyword matches at a word START and may run to the end of that word,
        so "crane" matches "cranes" and "machine" matches "machinery". Matches
        are then deduplicated BY SPAN: two keywords that fire on the same run of
        text are one piece of evidence, not two.

        Both halves are needed, and each was found by breaking the other:

          * plain substring matching counted "machine" inside "machinery", so
            "Woodworking machinery requirements" took the maximum boost from a
            single concept and outranked "Mechanical power-transmission
            apparatus" on a conveyor amputation.

          * strict word boundaries then failed on plurals - "crane" no longer
            matched "Overhead and gantry cranes", and a correct retrieval
            dropped below the floor and vanished.

        Prefix match plus span dedupe satisfies both.
        """
        spans: set[tuple[int, int]] = set()
        for kw in keywords:
            m = re.search(rf"\b{re.escape(kw)}\w*", title)
            if m:
                spans.add(m.span())
        distinct = [x for x in spans
                    if not any(y != x and y[0] <= x[0] and x[1] <= y[1] for y in spans)]
        return len(distinct)

    @staticmethod
    def event_keywords(event: str | None) -> list[str]:
        """Routing vocabulary taken from the predicted event label itself.

        The hand-written HAZARD_KEYWORDS has eight entries - one per major
        group - and was never going to describe 77 distinct events. The fine
        label already does: "Caught in running equipment or machinery during
        maintenance, cleaning" yields `maintenance` and `cleaning`, and 1910.147
        opens "the servicing and maintenance of machines and equipment". That is
        the bridge the hand-written list could not build.
        """
        if not event or not cfg.EVENT_ROUTING:
            return []
        words = re.findall(r"[a-z]+", event.lower())
        return sorted({w for w in words
                       if len(w) >= cfg.EVENT_MIN_WORD
                       and w not in cfg.EVENT_STOPWORDS})

    def search_for_hazard(self, query: str, hazard: str, k: int = 3,
                          event: str | None = None) -> list[tuple[int, float]]:
        """Ranked sections above the floor. May return fewer than k, or none.

        Two gates, applied in order:

          routing - the predicted hazard's vocabulary must appear in the
                    section TITLE, or the section is not a candidate at all
          floor   - what survives must still clear RETRIEVAL_FLOOR

        The routing gate is the one that matters, and it exists because of a
        real failure: a heat-exhaustion narrative retrieved "1910.138 Hand
        protection", whose body mentions temperature extremes in the context of
        gloves. It scored 0.085 against a floor of 0.08 and was presented as the
        applicable rule.

        Raising the floor does not fix that. The correct crane match (1910.179)
        also scores 0.085 - a true positive and a false positive land on the
        same number. So the fix is not a better threshold but a different
        question: does this section's SUBJECT match the hazard we predicted?
        Body-vocabulary overlap is not evidence; title agreement is.
        """
        lexical = self._scores(query)
        scores = lexical
        if cfg.USE_LSA and self.latent is not None:
            # NOT ACTUALLY A 50/50 BLEND. Read ADR-019 before changing this.
            #
            # Measured across narratives: lexical scores span 0.00-0.08, latent
            # scores span ~0.50-0.68. At LSA_BLEND = 0.5 the lexical term
            # contributes at most ~0.02 and the latent term ~0.28, so ranking is
            # driven by the latent score with lexical acting as a tiebreak.
            #
            # Two consequences, both real defects, both kept deliberately
            # because this exact configuration is the one that was MEASURED on
            # the third evaluation set and beat lexical-only on every metric:
            #
            #   1. RETRIEVAL_FLOOR (0.08) is inert. Every blended score clears
            #      it, so the "no section matched" path effectively stops
            #      firing. The abstention that protects users - a hazard with no
            #      standard at all - runs in pipeline.py BEFORE retrieval and is
            #      untouched.
            #   2. Reported scores are compressed into ~0.25-0.33 and are
            #      comparable within one result, not across incidents. The
            #      lexical score is carried alongside so an absolute, calibrated
            #      number still reaches the caller.
            #
            # Min-max normalising both vectors first is the obvious fix and it
            # is WORSE - it amplifies noise in the latent vector's narrow range
            # and wrecks the ranking (the crane case's top hit becomes
            # "1910.30 Training requirements"). Tried, measured, rejected.
            #
            # A calibrated floor for a blended score needs a fourth labelled
            # set. TASK-313.
            scores = ((1 - cfg.LSA_BLEND) * lexical
                      + cfg.LSA_BLEND * self.latent.scores(query))
        keywords = list(cfg.HAZARD_KEYWORDS.get(hazard, []))
        # Event words widen SCOPE routing only. Letting them match titles as
        # well put generic words like "equipment" into tier 0, which crowded
        # the lead slot: dev recall@1 fell 0.333 -> 0.242. Reach below the lead
        # is what they are for.
        scope_keywords = keywords + self.event_keywords(event)

        if not keywords:
            ranked = [(int(i), float(scores[i]), float(lexical[i]))
                      for i in scores.argsort()[::-1][:k]]
            return [r for r in ranked if r[1] >= cfg.RETRIEVAL_FLOOR]

        # Two tiers, and the tier is decided before the score is.
        #
        # 0 - the TITLE names the hazard. The section is about this.
        # 1 - only the scope opening does. The section touches this.
        # 2 - neither. Not a candidate.
        #
        # Tier beats score, always. Adding scope routing as a flat score boost
        # raised recall@3 from 0.364 to 0.424 but dropped recall@1 from 0.364 to
        # 0.333: scope matches with high raw similarity displaced correct
        # title matches at rank 1. Ordering by tier keeps every title match where
        # it was and lets scope matches fill the slots underneath - which were
        # empty a third of the time.
        tier = np.full(len(scores), 2, dtype=int)
        for i, title in enumerate(self.titles):
            hits = self._keyword_hits(title, keywords)
            if hits:
                tier[i] = 0
                scores[i] *= 1 + cfg.KEYWORD_BOOST * min(hits, 2)
                continue
            if self.standards[i]["section"] in cfg.NO_SCOPE_ROUTING:
                continue  # reachable by title only - see config.NO_SCOPE_ROUTING
            scope_hits = self._keyword_hits(self.scopes[i], scope_keywords)
            if scope_hits:
                tier[i] = 1
                scores[i] *= 1 + cfg.SCOPE_BOOST * min(scope_hits, 2)

        candidates = [i for i in range(len(scores)) if tier[i] < 2]
        candidates = self._apply_floor(candidates, scores)
        candidates.sort(key=lambda i: -scores[i])

        # The lead slot goes to a TITLE match if one exists; the remaining slots
        # compete on score alone.
        #
        # This follows the product, not the metric. The agent presents the first
        # section as the one that applies and the rest as "related, scoring
        # lower" - so the lead must be the strongest kind of evidence, while the
        # slots beneath it are better used for breadth. Sorting every slot by
        # tier cost recall@3 (0.424 -> 0.394) by letting weak title matches crowd
        # out strong scope matches; sorting none of them cost recall@1.
        # TRIED AND REJECTED: choosing the lead on the LEXICAL score among title
        # matches, on the theory that the precise signal should lead and the
        # soft one should only add breadth beneath it. It sounded right and it
        # lost on every metric - dev recall@1 0.303 -> 0.273, recall@3 0.485 ->
        # 0.424, MRR 0.384 -> 0.338. The blended score is better evidence even
        # for the lead slot. Recorded so it is not re-derived and re-tried.
        lead = next((i for i in candidates if tier[i] == 0), None)
        if lead is not None:
            candidates.remove(lead)
            candidates.insert(0, lead)
        return [(int(i), float(scores[i]), float(lexical[i])) for i in candidates[:k]]


def build_standards_index(standards: list[dict]) -> StandardsIndex:
    return StandardsIndex(standards)


def build_incident_index(texts) -> Index:
    return Index(list(texts), min_df=2)
