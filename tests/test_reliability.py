from src.recommender import Song, UserProfile, Recommender
from src.reliability import ReliabilityEvaluator, ReliabilityReport


def make_recommender() -> Recommender:
    songs = [
        Song(1, "Pop Hit", "A", "pop", "happy", 0.80, 120, 0.9, 0.8, 0.10),
        Song(2, "Chill Lofi", "B", "lofi", "chill", 0.40, 80, 0.6, 0.5, 0.90),
        Song(3, "Rock Storm", "C", "rock", "intense", 0.90, 150, 0.5, 0.7, 0.05),
        Song(4, "Jazz Night", "D", "jazz", "relaxed", 0.35, 90, 0.7, 0.5, 0.88),
        Song(5, "EDM Pulse", "E", "edm", "energetic", 0.95, 128, 0.7, 0.9, 0.03),
        Song(6, "Folk Road", "F", "folk", "nostalgic", 0.45, 98, 0.7, 0.5, 0.82),
    ]
    return Recommender(songs)


def sample_profiles():
    return [
        UserProfile("pop", "happy", 0.8, False),
        UserProfile("jazz", "relaxed", 0.35, True),
        UserProfile("rock", "intense", 0.9, False),
    ]


def test_determinism_is_perfect_for_deterministic_recommender():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    # Ranking has no randomness, so repeated runs must be identical.
    assert ev.measure_determinism(UserProfile("pop", "happy", 0.8, False)) == 1.0


def test_relevance_rewards_on_taste_matches():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    # The pop/happy profile has an exact genre AND mood match in the catalog,
    # so at least the top pick should count as relevant.
    score = ev.measure_relevance(UserProfile("pop", "happy", 0.8, False))
    assert 0.0 < score <= 1.0


def test_stability_returns_high_overlap_for_small_nudge():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    # A 0.05 energy nudge should not overhaul the top-3.
    assert ev.measure_stability(UserProfile("pop", "happy", 0.8, False)) >= 0.5


def test_confidence_is_between_zero_and_one():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    c = ev.measure_confidence(UserProfile("pop", "happy", 0.8, False))
    assert 0.0 <= c <= 1.0


def test_coverage_fraction_of_catalog():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    cov = ev.measure_coverage(sample_profiles())
    assert 0.0 < cov <= 1.0


def test_evaluate_produces_report_with_overall():
    ev = ReliabilityEvaluator(make_recommender(), k=3)
    report = ev.evaluate(sample_profiles())
    assert isinstance(report, ReliabilityReport)
    assert 0.0 <= report.overall <= 1.0
    assert len(report.per_profile) == 3
    assert isinstance(report.summary(), str)
