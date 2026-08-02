"""
Reliability metrics for the music recommender.

"Reliability" here means two things a user actually cares about:

  * How WELL does it perform?   -> is the top-k list actually on-taste, and is
                                   the ranking confident (not a near-tie)?
  * How CONSISTENTLY does it     -> does the same profile always get the same
    perform?                       list, and do tiny changes to a profile cause
                                   only tiny changes to the results?

This module leaves the scoring logic in recommender.py untouched. It only
*observes* a Recommender and reports on its behaviour, so it can be run as a
health check without changing what the system recommends.

Every metric is normalised to [0.0, 1.0] where 1.0 is best, so they can be
averaged into a single overall reliability score.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Sequence

from .recommender import Recommender, UserProfile


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _ids(songs) -> List[int]:
    """Ranking as a list of song ids (order matters)."""
    return [song.id for song in songs]


def _jaccard(a: Sequence[int], b: Sequence[int]) -> float:
    """Set overlap of two id lists: |A∩B| / |A∪B|. 1.0 == identical sets."""
    set_a, set_b = set(a), set(b)
    if not set_a and not set_b:
        return 1.0
    return len(set_a & set_b) / len(set_a | set_b)


# ---------------------------------------------------------------------------
# Report container
# ---------------------------------------------------------------------------
@dataclass
class ReliabilityReport:
    """The result of evaluating a recommender across a suite of profiles."""
    determinism: float          # same profile -> same list, every time
    stability: float            # tiny profile change -> tiny result change
    relevance: float            # top-k actually matches the stated taste
    confidence: float           # #1 stands clearly above the cut-off
    coverage: float             # fraction of the catalog the system can reach
    per_profile: List[Dict] = field(default_factory=list)

    @property
    def overall(self) -> float:
        """Single headline number: the average of the five sub-scores."""
        parts = [
            self.determinism,
            self.stability,
            self.relevance,
            self.confidence,
            self.coverage,
        ]
        return sum(parts) / len(parts)

    def summary(self) -> str:
        def bar(value: float, width: int = 20) -> str:
            filled = round(value * width)
            return "#" * filled + "." * (width - filled)

        lines = [
            "=" * 60,
            "  RELIABILITY REPORT",
            "=" * 60,
            "",
            f"  Determinism  {bar(self.determinism)}  {self.determinism:.2f}",
            f"  Stability    {bar(self.stability)}  {self.stability:.2f}",
            f"  Relevance    {bar(self.relevance)}  {self.relevance:.2f}",
            f"  Confidence   {bar(self.confidence)}  {self.confidence:.2f}",
            f"  Coverage     {bar(self.coverage)}  {self.coverage:.2f}",
            "  " + "-" * 56,
            f"  OVERALL      {bar(self.overall)}  {self.overall:.2f}",
            "=" * 60,
        ]
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# The evaluator
# ---------------------------------------------------------------------------
class ReliabilityEvaluator:
    """
    Runs a battery of checks against a Recommender and produces a
    ReliabilityReport. Construct it once with the recommender under test.
    """

    def __init__(self, recommender: Recommender, k: int = 5):
        self.recommender = recommender
        self.k = k
        self.catalog_size = len(recommender.songs)

    # -- individual metrics -------------------------------------------------

    def measure_determinism(self, profile: UserProfile, runs: int = 5) -> float:
        """
        A reliable system is repeatable: the *identical* profile must return
        the *identical* ranking every run. Returns 1.0 if all runs agree on
        the exact order, else 0.0 (order-sensitive on purpose).
        """
        baseline = _ids(self.recommender.recommend(profile, k=self.k))
        for _ in range(runs - 1):
            if _ids(self.recommender.recommend(profile, k=self.k)) != baseline:
                return 0.0
        return 1.0

    def measure_stability(self, profile: UserProfile, delta: float = 0.05) -> float:
        """
        A reliable system is robust: nudging the profile by a tiny amount
        should not overhaul the recommendations. We perturb target_energy by
        ±delta and report the average set-overlap (Jaccard) with the original
        top-k. 1.0 == a small input change caused no change in *which* songs
        are recommended.
        """
        base = _ids(self.recommender.recommend(profile, k=self.k))
        overlaps = []
        for signed in (delta, -delta):
            nudged = UserProfile(
                favorite_genre=profile.favorite_genre,
                favorite_mood=profile.favorite_mood,
                target_energy=profile.target_energy + signed,
                likes_acoustic=profile.likes_acoustic,
            )
            overlaps.append(
                _jaccard(base, _ids(self.recommender.recommend(nudged, k=self.k)))
            )
        return sum(overlaps) / len(overlaps)

    def measure_relevance(self, profile: UserProfile) -> float:
        """
        A reliable system is on-taste: how much of the top-k actually matches
        what the user asked for? We give a song credit if its genre OR mood
        matches the profile, and return the fraction of the top-k that does
        (a precision@k on the stated preferences).
        """
        top = self.recommender.recommend(profile, k=self.k)
        if not top:
            return 0.0
        hits = sum(
            1
            for song in top
            if song.genre == profile.favorite_genre
            or song.mood == profile.favorite_mood
        )
        return hits / len(top)

    def measure_confidence(self, profile: UserProfile) -> float:
        """
        A reliable ranking is decisive, not a coin-flip: the #1 pick should
        stand clearly above the last song that made the cut. We report the
        normalised score margin between rank 1 and rank k. Near 0.0 means the
        top-k is essentially a tie and the ordering is fragile.
        """
        top = self.recommender.recommend(profile, k=self.k)
        if len(top) < 2:
            return 0.0
        best = self.recommender._score(profile, top[0])[0]
        cutoff = self.recommender._score(profile, top[-1])[0]
        spread = abs(best) + abs(cutoff) + 1e-9
        return max(0.0, min(1.0, (best - cutoff) / spread))

    def measure_coverage(self, profiles: Sequence[UserProfile]) -> float:
        """
        A reliable system serves the whole catalog, not just a few crowd-
        pleasers. Across every test profile, what fraction of distinct songs
        ever appears in a top-k? Low coverage means most of the catalog is
        unreachable no matter who the user is (a popularity filter bubble).
        """
        if self.catalog_size == 0:
            return 0.0
        seen = set()
        for profile in profiles:
            seen.update(_ids(self.recommender.recommend(profile, k=self.k)))
        return len(seen) / self.catalog_size

    # -- orchestration ------------------------------------------------------

    def evaluate(self, profiles: Sequence[UserProfile]) -> ReliabilityReport:
        """
        Run every metric over the supplied suite of profiles and average the
        per-profile metrics into one report. Coverage is measured once across
        the whole suite.
        """
        if not profiles:
            raise ValueError("Need at least one profile to evaluate reliability.")

        per_profile: List[Dict] = []
        for profile in profiles:
            per_profile.append({
                "profile": profile,
                "determinism": self.measure_determinism(profile),
                "stability": self.measure_stability(profile),
                "relevance": self.measure_relevance(profile),
                "confidence": self.measure_confidence(profile),
            })

        def avg(key: str) -> float:
            return sum(row[key] for row in per_profile) / len(per_profile)

        return ReliabilityReport(
            determinism=avg("determinism"),
            stability=avg("stability"),
            relevance=avg("relevance"),
            confidence=avg("confidence"),
            coverage=self.measure_coverage(profiles),
            per_profile=per_profile,
        )
