# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

My recommender is a **content-based** system: it recommends songs that *sound and feel like* what the user says they want. It works in two clear steps — **score every song**, then **rank and trim** the list.

### What features does each `Song` use?

Each `Song` stores ten fields, but only four actually drive the recommendation:

- **`genre`** (e.g. pop, lofi, rock) — the style of the song.
- **`mood`** (e.g. happy, chill, intense) — the feeling it gives off.
- **`energy`** (0–1) — how intense or laid-back it is.
- **`acousticness`** (0–1) — how acoustic vs. electronic it sounds.

The song also carries `id`, `title`, and `artist` (labels for display, not scoring) and `tempo_bpm`, `valence`, and `danceability` (extra audio features I keep on hand for future experiments but don't score on yet).

### What does the `UserProfile` store?

A user's "taste profile" is four preferences:

- **`favorite_genre`** — the genre they're in the mood for.
- **`favorite_mood`** — the vibe they want.
- **`target_energy`** (0–1) — how energetic they want the music.
- **`likes_acoustic`** (True/False) — whether they prefer acoustic tracks.

### How does the `Recommender` compute a score for each song?

For one song, it adds up four rewards (all handled in `_score_song_attrs`):

| What's checked | How it's scored | Points |
|---|---|---|
| Genre matches favorite | exact match | **+2.0** |
| Mood matches favorite | exact match | **+1.5** |
| Energy close to target | `1 − abs(target − energy)`, then ×2.0 | **up to +2.0** |
| Acoustic preference | rewards acoustic if `likes_acoustic`, else non-acoustic | **up to +1.0** |

The closer a song is to the profile, the higher its total. Along the way the scorer also collects plain-English **reasons** (e.g. *"matches your favorite genre (pop)"*) so the recommendation can explain itself.

### How do I choose which songs to recommend?

1. **Score** every song in the catalog with the rule above.
2. **Sort** them from highest score to lowest.
3. **Keep the top `k`** (default 5) and hand them back with their explanations.

So the final list is simply *"the k songs that best match this profile, best first."*

```
UserProfile ─┐
             ├─►  score each Song  ─►  sort high→low  ─►  keep top k  ─►  recommendations
  all Songs ─┘        (Scoring Rule)      (Ranking Rule)
```

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output
### Profile 1: genre=pop, mood=happy, energy=0.8
```
============================================================
  TOP RECOMMENDATIONS
  For: genre=pop, mood=happy, energy=0.8
============================================================

  1.  Sunrise City - Neon Echo
      Score: 6.28  |  pop, happy
      Because: matches your favorite genre (pop), matches your mood (happy), energy level is a great fit, energetic, non-acoustic sound

  2.  Gym Hero - Max Pulse
      Score: 4.69  |  pop, intense
      Because: matches your favorite genre (pop), energy level is a great fit, energetic, non-acoustic sound

  3.  Rooftop Lights - Indigo Parade
      Score: 4.07  |  indie pop, happy
      Because: matches your mood (happy), energy level is a great fit

  4.  Concrete Kingdom - Blocktext
      Score: 2.88  |  hip hop, confident
      Because: energy level is a great fit, energetic, non-acoustic sound

  5.  Late Shift Funk - The Groove Unit
      Score: 2.76  |  funk, playful
      Because: energy level is a great fit, energetic, non-acoustic sound

============================================================
```
### Profile 2: genre=rock, mood=sad, energy=-1.0
```
============================================================
  TOP RECOMMENDATIONS
  For: genre=rock, mood=sad, energy=-1.0
============================================================

  1.  Storm Runner - Voltline
      Score: 1.08  |  rock, intense
      Because: matches your favorite genre (rock), energetic, non-acoustic sound

  2.  Velvet Hours - Marlowe Rae
      Score: -0.42  |  r&b, romantic
      Because: a reasonable all-round match

  3.  Spacewalk Thoughts - Orbit Bloom
      Score: -0.48  |  ambient, chill
      Because: a reasonable all-round match

  4.  Midnight Coding - LoRoom
      Score: -0.55  |  lofi, chill
      Because: a reasonable all-round match

  5.  Moonlit Sonata Drift - Aria Vance
      Score: -0.55  |  classical, melancholy
      Because: a reasonable all-round match

============================================================
```
### Profile 3: genre=jazz, mood=sad, energy=1.0
```
============================================================
  TOP RECOMMENDATIONS
  For: genre=jazz, mood=sad, energy=1.0
============================================================

  1.  Iron Verdict - Ashfall
      Score: 2.90  |  metal, aggressive
      Because: energy level is a great fit, energetic, non-acoustic sound

  2.  Voltage Bloom - Pulsewave
      Score: 2.87  |  edm, energetic
      Because: energy level is a great fit, energetic, non-acoustic sound

  3.  Coffee Shop Stories - Slow Stereo
      Score: 2.85  |  jazz, relaxed
      Because: matches your favorite genre (jazz)

  4.  Gym Hero - Max Pulse
      Score: 2.81  |  pop, intense
      Because: energy level is a great fit, energetic, non-acoustic sound

  5.  Storm Runner - Voltline
      Score: 2.72  |  rock, intense
      Because: energy level is a great fit, energetic, non-acoustic sound

============================================================
```
**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Reliability System

To measure *how well* and *how consistently* the recommender performs, I added a
reliability check (`src/reliability.py`) that observes the recommender without
changing what it recommends. Run it against the real catalog with:

```bash
python -m src.run_reliability
```

It scores five dimensions, each normalised to `[0.0, 1.0]` (1.0 is best) and
averaged into one **overall** number:

| Metric | Question it answers | How it's measured |
|---|---|---|
| **Determinism** | Same profile → same list, every time? | Run a profile 5× and check the ranking is byte-for-byte identical. |
| **Stability** | Does a tiny input change cause only a tiny output change? | Nudge `target_energy` by ±0.05 and measure the Jaccard overlap of the top-k. |
| **Relevance** | Is the top-k actually on-taste? | Fraction of the top-k whose genre **or** mood matches the profile (precision@k). |
| **Confidence** | Is the #1 pick decisive, not a near-tie? | Normalised score margin between rank 1 and the last song that made the cut. |
| **Coverage** | Can the system reach the whole catalog? | Distinct songs recommended across a suite of profiles ÷ catalog size. |

Sample run over five diverse profiles:

```
  Determinism  ####################  1.00
  Stability    ###################.  0.93
  Relevance    #########...........  0.44
  Confidence   ########............  0.40
  Coverage     ##############......  0.70
  --------------------------------------------------------
  OVERALL      ##############......  0.69
```

The numbers put hard evidence behind the biases in *Limitations and Risks*
below, and they also reveal which problems code can and can't fix:

- **Relevance** is high for mainstream tastes (pop 0.60, lofi 0.80) but collapses
  for niche genres (jazz and metal 0.20). This is a **data ceiling, not a ranking
  bug**: the catalog holds exactly one jazz and one metal song, so precision@5
  caps at 1/5 no matter how songs are scored. The honest fix is a larger, more
  balanced catalog.
- **Confidence** sits around 0.40 because most profiles have *several* equally-good
  matches (e.g. two pop songs plus indie pop), so the top-k scores are naturally
  close. That reflects a catalog with multiple right answers, not a fragile ranking.

To push more true matches into the top-k I rebalanced the weights
(genre 3.0 / mood 2.0 / energy 1.5) and added **graded fuzzy matching** so related
labels earn partial credit (`indie pop` ~ `pop`, `chill` ~ `relaxed`). That lifted
**stability from 0.83 to 0.93** and made the #1 pick win by a clear margin instead
of a near-tie, even though the relevance/confidence ceilings above are structural.
Tests for every metric live in `tests/test_reliability.py`.

---

## Experiments You Tried

I experimented with the following changes to the scoring rule:
- Weighted the genre by 3/4 instead of 2.0, to see if it would diversify recommendations more.
- Added a new feature for acousticness, giving a bonus if the user likes acoustic tracks and the song is acoustic.
- Temporarily disabled the mood match bonus to see how it affected recommendations.

The results of these experiments were:
- The ranking slightly changed for all 3 profiles, with more diverse genres appearing in the third recommendation and below.
- The accousticness almost doesn't affect the top recommendations, but it does change the lower-ranked songs, especially for users who prefer acoustic tracks. It does heavily affect if the user profile negative energy level. 
- In general, the top 2 recommendations for each profile remained the same, but the lower-ranked songs changed more significantly.

---

## Limitations and Risks

Beyond the obvious limits (tiny 20-song catalog, no understanding of lyrics or
language), I stress-tested the scoring rule with adversarial and edge-case
profiles and found several **structural biases** — filter bubbles that affect
users even when they enter perfectly valid preferences. I measured these against
the actual catalog, so they aren't hypothetical.

**1. The "energy gap" underserves moderate-energy users.**
The catalog's energy is bimodal — 7 songs below 0.5, 9 songs at 0.7 or above,
and only 4 in the middle (with a real empty gap between 0.64 and 0.75). Because
the energy term is a symmetric linear penalty (`1 − abs(target − energy)`), a
user who wants energy ≈ 0.6 has almost nothing close, so the fixed genre/mood
bonuses drag them toward whichever extreme cluster is nearer. High- and
low-energy tastes are served well; the middle is a blind spot the data can't see.

**2. Energy and acousticness are secretly the same axis (double jeopardy).**
In this catalog `corr(energy, acousticness) = −0.97` — nearly perfect. The two
"independent" scoring terms are really one signal counted twice. A user who wants
calm, low-energy music gets low-energy songs (which are acoustic), which are then
penalized *again* by the default non-acoustic reward. One preference, two strikes.

**3. There is no "neutral" on acoustic.**
`likes_acoustic` is a boolean that *always* contributes up to ±1.0, and it
defaults to `False`. So every user — including those who never expressed an
opinion — is silently biased toward electronic/produced tracks (edm, metal, pop)
and away from jazz, classical, folk, ambient, and lofi. There is no "don't care."

**4. Exact-match genre/mood kills discovery.**
Genre and mood are compared with strict string equality and no notion of
similarity. "pop" and "indie pop" are treated as unrelated; so are "chill",
"relaxed", and "focused". The system is pure exploitation with zero exploration —
it can only ever reinforce the one label the user typed, which is the textbook
definition of a filter bubble.

**5. Catalog imbalance penalizes niche-genre fans.**
Genre counts are `lofi=3, pop=2`, and everything else appears once. A lofi or pop
fan gets a coherent, on-taste list; a metal, classical, or reggae fan gets
*exactly one* genre match and the rest of their top-5 is filled by strangers
matched only on energy. The same applies to the ~14 moods that appear only once.

**6. Three measured features are ignored.**
`tempo_bpm`, `valence`, and `danceability` are loaded but never scored. This
matters most for `valence` (0–1 positivity): it directly measures how "happy" a
track is, yet mood matching relies entirely on the text label rather than the
number that actually captures the feeling.

**7. Rankings never change.**
Ties keep CSV order (lowest `id` wins) and there is no randomization, so a given
profile returns the identical list on every run — no rotation, no freshness.

**8. Invalid input is not validated (garbage in, garbage out).**
Because energy closeness is never clamped, an out-of-range `energy` (e.g. `100`)
sends every score massively negative and silently hijacks the ranking; a
*negative* energy inverts the intent entirely (it starts rewarding low-energy
songs) while still producing plausible-looking scores. Case also matters —
`"Pop"` never matches `"pop"`, so the genre bonus vanishes with no warning.

I go deeper on the fairness implications of these in the model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



