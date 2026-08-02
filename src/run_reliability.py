"""
Run the reliability report against the real catalog.

    python -m src.run_reliability

Prints how WELL (relevance, confidence) and how CONSISTENTLY (determinism,
stability, coverage) the recommender performs across a suite of test profiles.
"""

from .recommender import load_songs, Song, Recommender, UserProfile
from .reliability import ReliabilityEvaluator


# A suite of diverse profiles so coverage and averages are meaningful:
# a well-served mainstream taste, a niche taste, and an adversarial input.
TEST_PROFILES = [
    UserProfile("pop", "happy", 0.80, False),
    UserProfile("lofi", "chill", 0.40, True),
    UserProfile("rock", "intense", 0.90, False),
    UserProfile("jazz", "relaxed", 0.35, True),
    UserProfile("metal", "aggressive", 0.95, False),
]


def main() -> None:
    rows = load_songs("data/songs.csv")
    songs = [Song(**row) for row in rows]
    recommender = Recommender(songs)

    evaluator = ReliabilityEvaluator(recommender, k=5)
    report = evaluator.evaluate(TEST_PROFILES)

    print()
    print(report.summary())
    print()
    print("  Per-profile relevance / confidence:")
    for row in report.per_profile:
        p = row["profile"]
        print(
            f"    - {p.favorite_genre:<9} {p.favorite_mood:<11}"
            f"  relevance={row['relevance']:.2f}  confidence={row['confidence']:.2f}"
        )
    print()


if __name__ == "__main__":
    main()
