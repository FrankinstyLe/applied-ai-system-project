"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

import logging

from recommender import (
    load_songs,
    recommend_songs,
    confidence_from_score,
    validate_user_prefs,
)


def show_recommendations(user_prefs: dict, songs: list, k: int = 5) -> None:
    """Validate one profile, log any input problems, then print its top-k."""
    # Surface input problems (out-of-range energy, missing fields) up front.
    for warning in validate_user_prefs(
        user_prefs.get("genre", ""),
        user_prefs.get("mood", ""),
        user_prefs.get("energy"),
    ):
        logging.warning("Profile input: %s", warning)

    recommendations = recommend_songs(user_prefs, songs, k=k)

    print()
    print("=" * 60)
    print("  TOP RECOMMENDATIONS")
    print(f"  For: genre={user_prefs['genre']}, "
          f"mood={user_prefs['mood']}, energy={user_prefs['energy']}, "
          f"likes_acoustic={user_prefs['likes_acoustic']}")
    print("=" * 60)

    for rank, rec in enumerate(recommendations, start=1):
        # You decide the structure of each returned item.
        # A common pattern is: (song, score, explanation)
        song, score, explanation = rec
        confidence = confidence_from_score(score)
        print(f"\n  {rank}.  {song['title']} - {song['artist']}")
        print(f"      Score: {score:.2f}  |  Confidence: {confidence:.0%}  "
              f"|  {song['genre']}, {song['mood']}")
        print(f"      Because: {explanation}")

    print()
    print("=" * 60)


def main() -> None:
    # Show INFO+ logs from the recommender (catalog load, skipped rows, etc.).
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    songs = load_songs("data/songs.csv")

    # Three profiles: a clean one, plus two that stress-test validation —
    # user_prefs_1 has out-of-range energy (-1.0) and user_prefs_2 uses a mood
    # ("sad") that isn't in the catalog.
    profiles = [
        {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": True},
        {"genre": "rock", "mood": "sad", "energy": -1.0, "likes_acoustic": True},
        {"genre": "jazz", "mood": "sad", "energy": 1.0, "likes_acoustic": False},
    ]

    for user_prefs in profiles:
        show_recommendations(user_prefs, songs, k=5)


if __name__ == "__main__":
    main()
