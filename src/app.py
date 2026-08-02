"""
Streamlit front-end for the Music Recommender.

Users build their own taste profile (one or more genres and moods, an
energy level, and an acoustic preference) and the system recommends the
top-k songs from the songs database, ranked with the same scoring logic
used on the command line.

Run with:
    streamlit run src/app.py
"""

import csv
import os
import random
import sys
from urllib.parse import quote_plus

import streamlit as st

# Make the recommender importable whether the app is launched from the repo
# root or from inside src/.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from recommender import load_songs, score_song

# Resolve data path relative to the repo root so the app works from any CWD.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(_REPO_ROOT, "data", "songs.csv")


@st.cache_data
def get_songs():
    """Load songs once and cache them across reruns."""
    return load_songs(DATA_PATH)


def unique_sorted(songs, field):
    """Distinct values for a song field, sorted for stable dropdowns."""
    return sorted({song[field] for song in songs})


# Optional media columns the CSV *may* carry. If present, we play the track
# inline instead of only linking out to a search. recommender.load_songs()
# ignores these columns, so we read them here without touching that module.
_MEDIA_COLUMNS = ("preview_url", "audio_file")


@st.cache_data
def get_media_map():
    """
    Map song id -> playable source, if the CSV has a media column.

    Returns {} when neither 'preview_url' nor 'audio_file' exists, so the
    UI cleanly falls back to search links. A 'preview_url' is used as-is;
    an 'audio_file' is resolved relative to the repo root.
    """
    with open(DATA_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        media_col = next(
            (c for c in _MEDIA_COLUMNS if c in (reader.fieldnames or [])),
            None,
        )
        if media_col is None:
            return {}

        media = {}
        for row in reader:
            value = (row.get(media_col) or "").strip()
            if not value:
                continue
            if media_col == "audio_file":
                value = os.path.join(_REPO_ROOT, value)
            media[int(row["id"])] = value
        return media


def search_urls(song):
    """Build outbound 'listen on' search links from title + artist."""
    query = quote_plus(f"{song['title']} {song['artist']}")
    return {
        "YouTube": f"https://www.youtube.com/results?search_query={query}",
        "Spotify": f"https://open.spotify.com/search/{query}",
    }


def render_player(song, media_map):
    """
    Inline audio when we have a source, plus outbound search links.

    The YouTube/Spotify buttons show for *every* song for consistency; an
    inline player is added on top when the song has a playable source.
    """
    source = media_map.get(song["id"])
    if source:
        try:
            st.audio(source)
        except Exception:
            # Bad path/URL — the search links below still work.
            pass

    links = search_urls(song)
    cols = st.columns(len(links))
    for col, (label, url) in zip(cols, links.items()):
        with col:
            st.link_button(f"▶ {label}", url, use_container_width=True)


def recommend_multi(genres, moods, energy, likes_acoustic, songs, k):
    """
    Score every song against the user's selected genres and moods.

    Genre and mood are scored independently in recommender.py, so for a
    multi-select profile we score each song against every (genre, mood)
    pairing and keep the best-scoring one — i.e. a song matching *any* of
    the chosen tastes ranks highly. Falls back to an empty preference when
    a list is left blank.
    """
    genres = genres or [""]
    moods = moods or [""]

    scored = []
    for song in songs:
        best_score = None
        best_reasons = None
        for genre in genres:
            for mood in moods:
                prefs = {
                    "genre": genre,
                    "mood": mood,
                    "energy": energy,
                    "likes_acoustic": likes_acoustic,
                }
                score, reasons = score_song(prefs, song)
                if best_score is None or score > best_score:
                    best_score = score
                    best_reasons = reasons
        scored.append((song, best_score, ", ".join(best_reasons)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:k]


def init_state(genres, moods):
    """Seed profile widgets with sensible defaults on first load."""
    st.session_state.setdefault("genres", [genres[0]])
    st.session_state.setdefault("moods", [moods[0]])
    st.session_state.setdefault("energy", 0.5)
    st.session_state.setdefault("likes_acoustic", False)


def surprise(genres, moods):
    """Randomize the profile. Runs as a button callback, before rerun."""
    st.session_state.genres = random.sample(
        genres, k=random.randint(1, min(3, len(genres)))
    )
    st.session_state.moods = random.sample(
        moods, k=random.randint(1, min(3, len(moods)))
    )
    st.session_state.energy = round(random.uniform(0.0, 1.0), 2)
    st.session_state.likes_acoustic = random.choice([True, False])
    st.session_state.show_results = True


def main() -> None:
    st.set_page_config(page_title="Music Recommender", page_icon="🎵")

    st.title("🎵 Build Your Music Profile")
    st.write(
        "Pick one or more genres and moods, tune the energy, and we'll "
        "recommend songs from the database that fit best."
    )

    songs = get_songs()
    media_map = get_media_map()
    genres = unique_sorted(songs, "genre")
    moods = unique_sorted(songs, "mood")
    init_state(genres, moods)

    with st.sidebar:
        st.header("Your Profile")
        st.multiselect("Favorite genres", genres, key="genres")
        st.multiselect("Moods", moods, key="moods")
        st.slider(
            "Energy level",
            min_value=-1.0,
            max_value=1.0,
            step=0.05,
            key="energy",
            help="0 = calm, 1 = high energy. Negative values stress-test "
                 "the scorer with out-of-range input.",
        )
        st.checkbox("I like acoustic tracks", key="likes_acoustic")
        k = st.slider("How many recommendations?", 1, 20, 5)

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Recommend", type="primary", use_container_width=True):
                st.session_state.show_results = True
        with col2:
            st.button(
                "🎲 Surprise me",
                use_container_width=True,
                on_click=surprise,
                args=(genres, moods),
            )

    if not st.session_state.get("show_results"):
        st.info("Set your preferences in the sidebar, then click "
                "**Recommend** — or hit **🎲 Surprise me**.")
        return

    genre_sel = st.session_state.genres
    mood_sel = st.session_state.moods
    energy = st.session_state.energy
    likes_acoustic = st.session_state.likes_acoustic

    recommendations = recommend_multi(
        genre_sel, mood_sel, energy, likes_acoustic, songs, k
    )

    st.subheader("Top Recommendations")
    st.caption(
        f"genres = {', '.join(genre_sel) or '—'}  •  "
        f"moods = {', '.join(mood_sel) or '—'}  •  "
        f"energy = {energy:.2f}  •  "
        f"acoustic = {'yes' if likes_acoustic else 'no'}"
    )

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        with st.container(border=True):
            st.markdown(f"**{rank}. {song['title']}** — {song['artist']}")
            st.caption(
                f"{song['genre']} · {song['mood']} · "
                f"energy {song['energy']:.2f} · score {score:.2f}"
            )
            st.write(f"_Because: {explanation}_")
            render_player(song, media_map)


if __name__ == "__main__":
    main()
