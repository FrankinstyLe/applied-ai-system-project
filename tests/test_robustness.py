"""
Tests for the reliability-hardening features: per-recommendation confidence,
input validation, and robust CSV loading with logging.
"""
import logging

import pytest

from src.recommender import (
    Song,
    UserProfile,
    Recommender,
    MAX_SCORE,
    confidence_from_score,
    validate_user_prefs,
    load_songs,
    _score_song_attrs,
)


# --- Confidence scoring -----------------------------------------------------

def test_confidence_is_normalised_to_0_1():
    assert confidence_from_score(0.0) == 0.0
    assert confidence_from_score(MAX_SCORE) == 1.0
    assert confidence_from_score(MAX_SCORE / 2) == pytest.approx(0.5)


def test_confidence_clamps_out_of_range_scores():
    # Scores can't really exceed MAX_SCORE, but confidence must stay in [0, 1].
    assert confidence_from_score(MAX_SCORE * 5) == 1.0
    assert confidence_from_score(-10.0) == 0.0


def test_perfect_match_scores_near_full_confidence():
    song = Song(1, "T", "A", "pop", "happy", 0.8, 120, 0.9, 0.8, 0.9)
    user = UserProfile("pop", "happy", 0.8, True)
    score, _ = Recommender([song])._score(user, song)
    assert confidence_from_score(score) > 0.9


# --- Input validation -------------------------------------------------------

def test_validate_flags_missing_genre_and_mood():
    warnings = validate_user_prefs("", "", 0.5)
    assert any("genre" in w for w in warnings)
    assert any("mood" in w for w in warnings)


def test_validate_flags_out_of_range_energy():
    assert validate_user_prefs("pop", "happy", 100.0)
    assert validate_user_prefs("pop", "happy", -1.0)
    assert validate_user_prefs("pop", "happy", 0.5) == []


def test_out_of_range_energy_is_clamped_not_hijacking():
    # energy=100 must not send the score wildly negative; clamped it behaves
    # like energy=1.0.
    hijack, _ = _score_song_attrs("pop", "happy", 100.0, 0.2, "pop", "happy", 0.5, False)
    clamped, _ = _score_song_attrs("pop", "happy", 1.0, 0.2, "pop", "happy", 0.5, False)
    assert hijack == clamped
    assert hijack > 0


def test_matching_is_case_insensitive():
    upper, _ = _score_song_attrs("Pop", "Happy", 0.8, 0.2, "pop", "happy", 0.8, False)
    lower, _ = _score_song_attrs("pop", "happy", 0.8, 0.2, "pop", "happy", 0.8, False)
    assert upper == lower


# --- Robust loading + logging ----------------------------------------------

def test_missing_file_raises_and_logs(tmp_path, caplog):
    with caplog.at_level(logging.ERROR):
        with pytest.raises(FileNotFoundError):
            load_songs(str(tmp_path / "does_not_exist.csv"))
    assert any("not found" in r.message.lower() for r in caplog.records)


def test_malformed_row_is_skipped_not_fatal(tmp_path, caplog):
    csv_path = tmp_path / "songs.csv"
    csv_path.write_text(
        "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
        "1,Good,A,pop,happy,0.8,120,0.9,0.8,0.2\n"
        "2,Bad,A,pop,happy,NOT_A_NUMBER,120,0.9,0.8,0.2\n",
        encoding="utf-8",
    )
    with caplog.at_level(logging.WARNING):
        songs = load_songs(str(csv_path))
    assert len(songs) == 1
    assert songs[0]["title"] == "Good"
    assert any("malformed" in r.message.lower() for r in caplog.records)
