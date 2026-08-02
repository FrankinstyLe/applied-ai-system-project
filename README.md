# 🎵 Music Recommender — Reliable, Explainable Recommendations

## Summary

This project turns a small classroom prototype into an interactive, **trustworthy-by-design** music recommender. It doesn't just return songs — it explains *why* each song was picked, and it ships with a reliability harness that measures **how consistently and how well** it performs across many kinds of users.

**Why it matters:** getting a recommender to *work* is one thing; making it *accurately beneficial to real users* is the actual goal. By building the evolution and the measurement together, I can see exactly what's missing and what needs to improve — instead of guessing. The headline of this version is reliability and consistency: same input → same list, small input change → small output change, and every recommendation carries a plain-English reason.

### Where it started — *Music Recommender Simulation*

The original project, **Music Recommender Simulation**, was a command-line, content-based recommender. It represented songs and a user "taste profile" as data, applied a hand-written scoring rule (genre, mood, energy, acousticness) to rank a 20-song catalog, and printed the top-k matches with explanations. Its goals were to learn how raw data becomes a prediction, to evaluate what the system got right and wrong, and to reflect on how this mirrors real-world AI recommenders.

This applied-AI version keeps that scoring core intact and extends it into a fuller system: an **interactive Streamlit front-end** so non-technical users can build a profile and get results (with inline audio and listen links), **graded fuzzy matching** so related tastes earn partial credit, and a **reliability evaluator** that puts hard numbers behind the system's strengths and biases.

---

## How The System Works

The recommender is **content-based**: it recommends songs that *sound and feel like* what the user asks for, in two clear steps — **score every song**, then **rank and trim** the list.

**Each `Song`** carries ten fields, but four drive the recommendation: `genre`, `mood`, `energy` (0–1), and `acousticness` (0–1). The rest (`id`, `title`, `artist`, `tempo_bpm`, `valence`, `danceability`) are labels for display or features kept for future experiments.

**A user's taste profile** is: `favorite_genre`, `favorite_mood`, `target_energy` (0–1), and `likes_acoustic` (True/False). The Streamlit UI lets a user pick *multiple* genres and moods; the scorer keeps the best-matching pairing per song.

**Scoring rule** (`_score_song_attrs`), with weights rebalanced so the discriminating signals do more work than the near-universal energy term:

| What's checked | How it's scored | Weight |
|---|---|---|
| Genre match | graded (exact / substring / same family) | **×3.0** |
| Mood match | graded (exact / substring / same family) | **×2.0** |
| Energy closeness | `1 − abs(target − energy)` | **×1.5** |
| Acoustic preference | rewards acoustic if `likes_acoustic`, else non-acoustic | **up to ±1.0** |

Graded **fuzzy matching** means `indie pop` earns partial credit toward `pop`, and `chill` ~ `relaxed`, instead of scoring zero. Along the way the scorer collects plain-English **reasons** so every recommendation can explain itself.

**Choosing recommendations:** score every song → sort high→low → keep the top `k` (default 5) with their explanations.

---

## Architecture Overview

The full system is captured in [`diagrams/system_diagram.mmd`](diagrams/system_diagram.mmd) (Mermaid). It reads left-to-right as **input → process → output**, with two feedback loops layered on top:

- **Input** — the song catalog (`data/songs.csv`, plus optional media columns) and the user's taste profile. Profiles arrive two ways: hard-coded in the CLI (`src/main.py`) or interactively from the **Streamlit UI** (`src/app.py`).
- **Process** — `load_songs()` parses the catalog; the **scoring rule** (`recommender.py`) turns each song + profile into a score and reasons; `recommend_multi()` (used by the UI) scores each song against every selected genre×mood pairing and keeps the best; the **ranking rule** sorts and trims to top-k.
- **Output** — the CLI prints a ranked text list; the web app renders result cards with an inline audio player and YouTube/Spotify links.
- **Evaluation loop** — the `ReliabilityEvaluator` (`src/reliability.py`) *observes* the recommender without changing it, producing a `ReliabilityReport`.
- **Human & testing loop** — automated tests plus my own review of the report and biases feed back into the scoring weights and data.

The key architectural idea: **both front-ends share one scoring core**, and the reliability harness measures that core rather than either UI — so the evaluation stays honest no matter how a user interacts with the system.

---

## Setup Instructions

1. **(Optional) create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\activate         # Windows
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Run the interactive web app** (recommended)

   ```bash
   streamlit run src/app.py
   ```

   Then pick genres/moods, tune energy, and click **Recommend** (or **🎲 Surprise me**).

4. **Or run the command-line version**

   ```bash
   python -m src.main
   ```

5. **Run the reliability report**

   ```bash
   python -m src.run_reliability
   ```

6. **Run the tests**

   ```bash
   pytest
   ```

> To play tracks inline in the web app, see [`data/audio/HOW_TO_ADD_AUDIO.md`](data/audio/HOW_TO_ADD_AUDIO.md).

---

## Sample Interactions

### A) Web app (Streamlit) — multi-select profile

**Input:** genres = `[pop]`, moods = `[chill]`, energy = `0.40`, acoustic = `yes`, k = `5`

**Output:**

```text
1. Library Rain - Paper Lanterns   | lofi, chill    | energy 0.35 | score 4.29
   Because: matches your mood (chill), energy level is a great fit, nice and acoustic, like you prefer
2. Spacewalk Thoughts - Orbit Bloom | ambient, chill | energy 0.28 | score 4.24
   Because: matches your mood (chill), energy level is a great fit, nice and acoustic, like you prefer
3. Midnight Coding - LoRoom        | lofi, chill    | energy 0.42 | score 4.18
   Because: matches your mood (chill), energy level is a great fit, nice and acoustic, like you prefer
4. Sunrise City - Neon Echo        | pop, happy     | energy 0.82 | score 4.05
   Because: matches your favorite genre (pop), energy level is a decent fit
5. Gym Hero - Max Pulse            | pop, intense   | energy 0.93 | score 3.75
   Because: matches your favorite genre (pop)
```

Note how the **acoustic + low-energy + chill** signals pull acoustic lofi/ambient tracks to the top, while the `pop` genre preference still surfaces two pop songs lower down — the explanation makes the trade-off visible.

<!-- Optional: add a screenshot of the running Streamlit app here -->

### B) Command line — mainstream taste

**Input:** genre = `pop`, mood = `happy`, energy = `0.8`, likes_acoustic = `True`

**Output:**

```text
1. Sunrise City - Neon Echo      Score: 6.65 | pop, happy
   Because: matches your favorite genre (pop), matches your mood (happy), energy level is a great fit
2. Rooftop Lights - Indigo Parade Score: 5.59 | indie pop, happy
   Because: related to your favorite genre (indie pop), matches your mood (happy), energy level is a great fit
3. Gym Hero - Max Pulse          Score: 4.35 | pop, intense
   Because: matches your favorite genre (pop), energy level is a great fit
4. Night Drive Loop - Neon Echo  Score: 3.15 | synthwave, moody
   Because: related to your favorite genre (synthwave), energy level is a great fit
5. Dusty Highway - Cody Rivers   Score: 2.78 | country, hopeful
   Because: a similar mood (hopeful), energy level is a decent fit
```

Fuzzy matching earns `indie pop` and `synthwave` partial genre credit — related discovery instead of an exact-match filter bubble.

### C) Command line — adversarial input (negative energy)

**Input:** genre = `rock`, mood = `sad`, energy = `-1.0`, likes_acoustic = `True`

**Output:**

```text
1. Storm Runner - Voltline       Score: 1.73 | rock, intense
   Because: matches your favorite genre (rock)
2. Spacewalk Thoughts - Orbit Bloom Score: 0.50 | ambient, chill
   Because: nice and acoustic, like you prefer
3. Moonlit Sonata Drift - Aria Vance Score: 0.50 | classical, melancholy
   Because: nice and acoustic, like you prefer
4. Library Rain - Paper Lanterns Score: 0.33 | lofi, chill
   Because: nice and acoustic, like you prefer
5. Coffee Shop Stories - Slow Stereo Score: 0.33 | jazz, relaxed
   Because: nice and acoustic, like you prefer
```

An out-of-range `energy = -1.0` inverts the energy term, so low-energy acoustic tracks bubble up. The list still looks plausible — a deliberate demonstration of the "garbage in, garbage out" limitation documented below.

---

## Design Decisions

- **Keep one scoring core, add front-ends around it.** The Streamlit app and CLI both call the same `score_song` / `_score_song_attrs`. Trade-off: the UI can't invent new scoring behavior, but every interface (and the reliability harness) stays consistent and testable.
- **Graded fuzzy matching instead of exact string equality.** Related labels earn partial credit (`indie pop` ~ `pop`, `chill` ~ `relaxed`). This adds a little discovery/exploration and lifted **stability from 0.83 → 0.93**. Trade-off: fuzzy families are hand-authored, so they encode my judgment about what's "similar."
- **Rebalanced weights (genre 3.0 / mood 2.0 / energy 1.5).** The discriminating signals now outweigh the near-universal energy term, pushing true matches into the top-k and separating the #1 pick from the pack. Trade-off: strong genre weighting can crowd out cross-genre serendipity.
- **Multi-select in the UI, single-signal scorer underneath.** `recommend_multi()` scores each song against every chosen (genre, mood) pair and keeps the best. Trade-off: "match *any* of my tastes" is simple and predictable, but it can't express "match *all* of them at once."
- **Reliability as an observer, not a gatekeeper.** `reliability.py` measures the recommender without altering what it recommends, so the report is an honest health check rather than a filter that hides weak spots.
- **Explanations are first-class.** Every recommendation ships a reason string. Trade-off: a little extra bookkeeping in the scorer, in exchange for transparency users can actually read.

---

## Reliability System

To measure *how well* and *how consistently* the recommender performs, `src/reliability.py` observes it without changing its output. Run it with `python -m src.run_reliability`. Each dimension is normalised to `[0.0, 1.0]` (1.0 is best) and averaged into an **overall** score:

| Metric | Question it answers | How it's measured |
|---|---|---|
| **Determinism** | Same profile → same list, every time? | Run a profile 5× and check the ranking is byte-for-byte identical. |
| **Stability** | Tiny input change → only a tiny output change? | Nudge `target_energy` by ±0.05 and measure the Jaccard overlap of the top-k. |
| **Relevance** | Is the top-k actually on-taste? | Fraction of the top-k whose genre **or** mood matches (precision@k). |
| **Confidence** | Is the #1 pick decisive, not a near-tie? | Normalised score margin between rank 1 and the cut-off. |
| **Coverage** | Can the system reach the whole catalog? | Distinct songs recommended across a suite of profiles ÷ catalog size. |

Sample run over five diverse profiles:

```text
  Determinism  ####################  1.00
  Stability    ###################.  0.93
  Relevance    #########...........  0.44
  Confidence   ########............  0.40
  Coverage     ##############......  0.70
  --------------------------------------------------------
  OVERALL      ##############......  0.69
```

---

## Testing Summary

**What worked, what didn't, and what I learned:** some metrics improved and some stayed flat — and the flat ones were mostly capped by the **limited data size**, not by the ranking logic.

| Metric | Before | After | Why |
|---|---:|---:|---|
| **Stability** | 0.83 | **0.93** | Fuzzy matching stops small energy nudges from swapping songs. |
| **Overall** | 0.67 | **0.69** | Net lift, driven mostly by stability. |
| **Relevance** | 0.44 | 0.44 | **Data ceiling** — 1 jazz / 1 metal song caps precision@5 at 0.20. |
| **Confidence** | 0.40 | 0.40 | **Inherent** — several equally-good matches, not fragility. |

The lesson: not every weakness is a code bug. Stability responded to a code change (fuzzy matching), but relevance and confidence are structural — they reflect a tiny, imbalanced catalog with multiple equally-valid answers. Measuring first told me *which* problems code could fix and which ones only more/better data could. Tests for every metric live in `tests/test_reliability.py`.

---

## Limitations and Risks

Beyond the obvious limits (tiny 20-song catalog, no understanding of lyrics), I stress-tested the scorer with adversarial and edge-case profiles and found several **structural biases** — measured against the real catalog, so they aren't hypothetical.

1. **The "energy gap" underserves moderate-energy users.** Energy is bimodal (a real empty gap between 0.64 and 0.75), so a user wanting energy ≈ 0.6 gets dragged toward whichever extreme cluster is nearer.
2. **Energy and acousticness are secretly the same axis.** `corr(energy, acousticness) = −0.97` — the two "independent" terms are really one signal counted twice (double jeopardy for calm-music fans).
3. **There is no "neutral" on acoustic.** `likes_acoustic` always contributes up to ±1.0 and defaults to `False`, silently biasing undecided users toward electronic/produced tracks.
4. **Fuzzy matching softens but doesn't eliminate the filter bubble.** Related labels now earn partial credit, but the system still leans heavily on the labels the user typed.
5. **Catalog imbalance penalizes niche-genre fans.** With `lofi=3, pop=2` and everything else appearing once, niche fans get one true match and a top-5 padded with energy-only strangers.
6. **Three measured features are ignored.** `tempo_bpm`, `valence`, and `danceability` are loaded but never scored — `valence` especially, which directly measures positivity.
7. **Rankings never change.** Ties keep CSV order and there's no randomization, so a profile returns the identical list every run — no freshness.
8. **Invalid input isn't validated.** Out-of-range or negative `energy` silently hijacks or inverts the ranking (see Sample Interaction C); case mismatches (`"Pop"` vs `"pop"`) drop the exact-genre bonus with no warning.

I go deeper on the fairness implications in the [model card](model_card.md).

---

## Reflection

Building this taught me that a recommender is only as good as its fit to *real* people, and that's the hard part: **it's hard to make one that's one-size-fits-all.** I can optimize the scoring, tune the weights, and add fuzzy matching to squeeze out more relevance and stability — but only up to a point. The scoring rule encodes *my* assumptions about what "similar" and "good" mean, and the data caps what any rule can achieve.

What I take away is that the last mile can't be reached by code alone. Turning data into predictions is straightforward; turning predictions into something genuinely helpful and fair needs **real user experience and feedback** to guide the next round of weight and scoring adjustments. That's also where bias hides — in the default assumptions (like `likes_acoustic=False`), the imbalanced catalog, and the labels I decided were "related." Measuring reliability didn't remove those biases, but it made them visible and honest, which is the necessary first step toward improving them.

See the [**Model Card**](model_card.md) for the full fairness analysis.
