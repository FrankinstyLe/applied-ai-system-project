# Local audio files

Drop track files here (e.g. `1.mp3`) and reference them from an
`audio_file` column in `../songs.csv` (path relative to repo root,
e.g. `data/audio/1.mp3`). The app's `get_media_map()` resolves and
plays them inline with `st.audio()`.

Alternatively, fill the `preview_url` column with a hosted MP3 or
streaming preview URL for inline playback without local files.
