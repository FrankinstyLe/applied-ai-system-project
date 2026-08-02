import csv
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

# Library code gets a named logger; the *application* entry points
# (main.py, run_reliability.py) decide how logs are shown. A NullHandler
# keeps things quiet if a caller never configures logging.
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# ---------------------------------------------------------------------------
# Scoring weights (shared by both the OOP and functional implementations).
# These encode the "Algorithm Recipe": reward genre/mood matches, reward
# songs whose energy is close to what the user wants, and factor in whether
# the user likes acoustic tracks.
# ---------------------------------------------------------------------------
# Weights rebalanced so the *discriminating* signals (genre, mood) do more of
# the work than the near-universal energy term. This surfaces true matches into
# the top-k (relevance) and spreads the #1 pick away from the pack (confidence).
GENRE_MATCH_BONUS = 3.0
MOOD_MATCH_BONUS = 2.0
ENERGY_WEIGHT = 1.5
ACOUSTIC_WEIGHT = 1.0

# Partial-credit factors for fuzzy matching (see _similarity).
SUBSTRING_CREDIT = 0.6   # e.g. "pop" within "indie pop"
SYNONYM_CREDIT = 0.5     # e.g. "chill" and "relaxed" in the same family

# Loose families so related labels earn partial credit instead of nothing.
# Strict string equality treated "pop"/"indie pop" and "chill"/"relaxed" as
# unrelated, which starved niche-genre users of any second match.
_GENRE_FAMILIES = [
    {"pop", "indie pop", "synthwave"},
    {"lofi", "ambient", "chill"},
    {"edm", "hip hop", "funk"},
    {"rock", "metal"},
    {"jazz", "r&b", "funk"},
    {"folk", "country", "world"},
]
_MOOD_FAMILIES = [
    {"chill", "relaxed", "focused", "melancholy"},
    {"happy", "uplifting", "playful", "energetic", "hopeful"},
    {"intense", "aggressive", "confident", "moody"},
]


# The most any song can score: a perfect genre + mood + energy match plus the
# full acoustic reward. Used to turn a raw score into a 0-1 confidence.
MAX_SCORE = GENRE_MATCH_BONUS + MOOD_MATCH_BONUS + ENERGY_WEIGHT + ACOUSTIC_WEIGHT


def _clamp01(value: float) -> float:
    """Force a value into [0.0, 1.0]. Guards against out-of-range input
    (e.g. energy=100 or -1) silently hijacking the ranking."""
    return max(0.0, min(1.0, value))


def _norm(label: str) -> str:
    """Normalise a genre/mood label for matching: lowercase + trimmed, so
    'Pop ' and 'pop' are treated as the same thing."""
    return label.strip().lower() if isinstance(label, str) else ""


def _similarity(value: str, target: str, families: List[set]) -> float:
    """
    Graded match in [0.0, 1.0]:
      1.0  exact match
      0.6  one label contains the other ("pop" ~ "indie pop")
      0.5  both labels share a family ("chill" ~ "relaxed")
      0.0  unrelated
    Matching is case-insensitive. Returns the strongest applicable credit.
    """
    value, target = _norm(value), _norm(target)
    if not value or not target:
        return 0.0
    if value == target:
        return 1.0
    if value in target or target in value:
        return SUBSTRING_CREDIT
    for family in families:
        if value in family and target in family:
            return SYNONYM_CREDIT
    return 0.0


def confidence_from_score(score: float) -> float:
    """
    Turn a raw song score into a 0.0-1.0 confidence ("how sure the system is
    about this pick"). It's the score as a fraction of the best score any song
    could earn (MAX_SCORE), clamped so it never leaves [0, 1].
    """
    return _clamp01(score / MAX_SCORE) if MAX_SCORE else 0.0


def validate_user_prefs(
    favorite_genre: str,
    favorite_mood: str,
    target_energy: Optional[float],
) -> List[str]:
    """
    Check a user's inputs and return a list of human-readable warnings
    (empty == all good). This does NOT mutate anything — scoring clamps
    out-of-range energy on its own — it just surfaces *why* results might
    look off so callers can log or display it.
    """
    warnings: List[str] = []
    if not favorite_genre:
        warnings.append("no favorite genre given; genre match will be skipped")
    if not favorite_mood:
        warnings.append("no favorite mood given; mood match will be skipped")
    if target_energy is not None and not (0.0 <= target_energy <= 1.0):
        warnings.append(
            f"target_energy={target_energy} is outside 0.0-1.0 and was clamped"
        )
    return warnings


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


def _score_song_attrs(
    genre: str,
    mood: str,
    energy: float,
    acousticness: float,
    favorite_genre: str,
    favorite_mood: str,
    target_energy: float,
    likes_acoustic: bool,
) -> Tuple[float, List[str]]:
    """
    Core scoring routine used by both the OOP and functional interfaces.
    Returns (score, reasons) so callers can rank songs and explain why.
    """
    score = 0.0
    reasons: List[str] = []

    # Genre match (graded: exact, partial, or related family)
    genre_sim = _similarity(genre, favorite_genre, _GENRE_FAMILIES)
    if genre_sim > 0:
        score += GENRE_MATCH_BONUS * genre_sim
        if genre_sim == 1.0:
            reasons.append(f"matches your favorite genre ({genre})")
        else:
            reasons.append(f"related to your favorite genre ({genre})")

    # Mood match (graded the same way)
    mood_sim = _similarity(mood, favorite_mood, _MOOD_FAMILIES)
    if mood_sim > 0:
        score += MOOD_MATCH_BONUS * mood_sim
        if mood_sim == 1.0:
            reasons.append(f"matches your mood ({mood})")
        else:
            reasons.append(f"a similar mood ({mood})")

    # Energy closeness: closer to target -> higher score (max ENERGY_WEIGHT).
    # Both values are clamped to [0, 1] first so out-of-range input (e.g.
    # energy=100 or a negative target) can't drive the score wildly negative
    # and silently hijack the ranking.
    if target_energy is not None:
        energy_closeness = 1.0 - abs(_clamp01(target_energy) - _clamp01(energy))
        score += ENERGY_WEIGHT * energy_closeness
        if energy_closeness >= 0.8:
            reasons.append("energy level is a great fit")
        elif energy_closeness >= 0.5:
            reasons.append("energy level is a decent fit")

    # Acoustic preference
    if likes_acoustic:
        score += ACOUSTIC_WEIGHT * acousticness
        if acousticness >= 0.6:
            reasons.append("nice and acoustic, like you prefer")
    else:
        # Reward non-acoustic tracks slightly when the user doesn't want acoustic
        score += ACOUSTIC_WEIGHT * (1.0 - acousticness)
        if acousticness <= 0.3:
            reasons.append("energetic, non-acoustic sound")

    if not reasons:
        reasons.append("a reasonable all-round match")

    return score, reasons


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        return _score_song_attrs(
            genre=song.genre,
            mood=song.mood,
            energy=song.energy,
            acousticness=song.acousticness,
            favorite_genre=user.favorite_genre,
            favorite_mood=user.favorite_mood,
            target_energy=user.target_energy,
            likes_acoustic=user.likes_acoustic,
        )

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        ranked = sorted(
            self.songs,
            key=lambda song: self._score(user, song)[0],
            reverse=True,
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        _, reasons = self._score(user, song)
        return f"'{song.title}' recommended because it " + ", ".join(reasons) + "."


def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dicts with numeric fields
    converted to the correct types.
    Required by src/main.py

    Robust to bad input: a missing file raises FileNotFoundError with a clear
    message, and any individual row that is malformed (missing column, non-numeric
    field) is logged and skipped rather than crashing the whole load.
    """
    try:
        f = open(csv_path, newline="", encoding="utf-8")
    except FileNotFoundError:
        logger.error("Song catalog not found at %s", csv_path)
        raise

    songs: List[Dict] = []
    skipped = 0
    with f:
        reader = csv.DictReader(f)
        for line_no, row in enumerate(reader, start=2):  # header is line 1
            try:
                songs.append({
                    "id": int(row["id"]),
                    "title": row["title"],
                    "artist": row["artist"],
                    "genre": row["genre"],
                    "mood": row["mood"],
                    "energy": float(row["energy"]),
                    "tempo_bpm": float(row["tempo_bpm"]),
                    "valence": float(row["valence"]),
                    "danceability": float(row["danceability"]),
                    "acousticness": float(row["acousticness"]),
                })
            except (KeyError, ValueError, TypeError) as exc:
                skipped += 1
                logger.warning("Skipping malformed row at line %d: %s", line_no, exc)

    if not songs:
        logger.error("No valid songs loaded from %s", csv_path)
    elif skipped:
        logger.warning("Loaded %d songs, skipped %d malformed row(s)", len(songs), skipped)
    else:
        logger.info("Loaded %d songs from %s", len(songs), csv_path)
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song (dict) against user preferences (dict).
    Required by recommend_songs() and src/main.py
    Expected return format: (score, reasons)
    """
    return _score_song_attrs(
        genre=song.get("genre", ""),
        mood=song.get("mood", ""),
        energy=song.get("energy", 0.0),
        acousticness=song.get("acousticness", 0.0),
        favorite_genre=user_prefs.get("genre", ""),
        favorite_mood=user_prefs.get("mood", ""),
        target_energy=user_prefs.get("energy"),
        likes_acoustic=user_prefs.get("likes_acoustic", False),
    )


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Scores and ranks all songs, returning the top k.
    Required by src/main.py
    Expected return format: (song_dict, score, explanation)
    """
    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = ", ".join(reasons)
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]
