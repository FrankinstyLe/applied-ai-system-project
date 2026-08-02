# 🎧 Model Card: Music Recommender (Snoofy 2.0)

## 1. Model Name

**Snoofy 2.0**

---

## 2. Intended Use

Snoofy 2.0 recommends the top songs for a user based on their stated preferences for **genre, mood, energy level, and acoustic sound**. It is a content-based recommender: it compares a user's taste profile to each song's attributes and ranks the closest matches, returning a plain-English reason for every pick.

This remains a **classroom / learning project**, not a production service. The goal is to understand how raw data becomes a prediction, to measure how reliably it does so, and to reflect honestly on where bias and limitations creep in. Recommendations are not intended for real end users yet.

---

## 3. How the Model Works

The model scores every song in the catalog against the user's profile, sorts high-to-low, and keeps the top `k`. Four signals drive the score, with weights rebalanced so the *discriminating* signals do more work than the near-universal energy term:

| Signal | How it's scored | Weight |
|---|---|---|
| Genre match | graded: exact / substring / same family | ×3.0 |
| Mood match | graded: exact / substring / same family | ×2.0 |
| Energy closeness | `1 − abs(target − energy)` | ×1.5 |
| Acoustic preference | rewards acoustic if `likes_acoustic`, else non-acoustic | up to ±1.0 |

Two capabilities were added in this version:

- **Graded fuzzy matching** (`_similarity`): exact match earns full credit, a substring like `indie pop` ~ `pop` earns 0.6, and same-family labels like `chill` ~ `relaxed` earn 0.5 — with explanations that say *"related to"* or *"a similar mood."* This replaces strict string equality, which had treated related tastes as unrelated.
- **An interactive Streamlit front-end** (`src/app.py`) so a non-technical user can build a multi-genre/multi-mood profile and get results with inline audio and listen links — sharing the exact same scoring core as the command line.

A separate **reliability harness** (`src/reliability.py`) *observes* the recommender without changing its output, reporting how consistently and how well it performs.

---

## 4. Data

The catalog started at 10 songs; I added 10 more to increase diversity, for **20 songs** spanning genres (pop, rock, jazz, classical, electronic, lofi, and more) and moods (happy, sad, energetic, calm, and others). The dataset is still small and **not balanced**: some genres and moods appear only once, and the energy values cluster at the extremes with a gap in the middle. As the evaluation below shows, this data shape — not the ranking logic — is the single biggest cap on the system's quality.

---

## 5. Strengths

- Works well for users with **clear, mainstream preferences** (e.g. pop, lofi), returning a coherent, on-taste list.
- **Balances multiple factors** — it can surface a song outside the preferred genre when its mood or energy is a strong match, and fuzzy matching now enables a little discovery instead of an exact-match filter bubble.
- **Explains itself** — every recommendation carries a reason, so the trade-offs behind a pick are visible.
- **Reliable and repeatable** — the same profile returns the same ranking every run (determinism 1.00), and small input changes cause only small output changes (stability 0.93).

---

## 6. Limitations and Bias

I stress-tested the scorer against the real catalog, so these biases are measured, not hypothetical:

- **Double jeopardy on the energy/acoustic axis.** In this catalog `corr(energy, acousticness) = −0.97` — the two "independent" terms are essentially one signal counted twice. A user who wants calm, acoustic music is penalized on both, quietly burying jazz, classical, and folk for anyone who doesn't explicitly set `likes_acoustic=True`.
- **No "neutral" on acoustic.** `likes_acoustic` is a boolean defaulting to `False`, so every undecided user is silently nudged toward electronic/produced tracks. There is no "don't care."
- **Catalog imbalance penalizes niche fans.** With some genres appearing only once, a metal or classical fan gets one true match and a top-5 padded with energy-only strangers.
- **A moderate-energy blind spot.** Energy is bimodal with a real gap (~0.64–0.75), so a user wanting mid-energy music has little that fits and gets pulled toward whichever extreme is nearer.
- **Fuzzy matching softens but doesn't remove the filter bubble** — the system still leans on the labels the user typed, and the "similar" families are hand-authored by me.
- **Unused features and no freshness.** `tempo_bpm`, `valence`, and `danceability` are loaded but never scored, and with no randomization a profile returns the identical list every run.
- **No input validation.** Out-of-range or negative energy can silently hijack or invert the ranking, and case mismatches (`"Pop"` vs `"pop"`) drop the exact-genre bonus without warning.

---

## 7. Could This Be Misused — and How to Prevent It

Yes — a system like this can absolutely be misused. Because a developer fully controls the scoring weights and the "similarity" families, they can **intentionally bias the outputs**: for example, receiving a commission from a third party to push certain artists or labels to the top. Over time that doesn't just skew one list — it can **shape users' demand and taste** for someone else's profit, all while the recommendations still look neutral and personalized.

Preventing this is mostly about **transparency and accountability** rather than clever code:

- **Show the reasons (already done).** Every pick states *why* it was chosen, which makes an artificially boosted result easier to spot.
- **Keep the weights and any "sponsored" influence auditable and disclosed** — no hidden thumb on the scale.
- **Separate ranking from monetization**, so commercial incentives can't quietly rewrite what counts as a "good match."
- **Measure reliability and coverage openly** (as this project does) so systematic favoritism shows up as a metric, not a surprise.

---

## 8. Evaluation & What Surprised Me

I evaluated the system with the reliability harness (determinism, stability, relevance, confidence, coverage) and by trying levers in `recommender.py`: rebalancing the weights (genre 3.0 / mood 2.0 / energy 1.5, up from 2.0/1.5/2.0) and adding graded fuzzy matching.

**What actually moved:**

| Metric | Before | After | Why |
|---|---:|---:|---|
| Stability | 0.83 | **0.93** | Fuzzy matching stops small energy nudges from swapping songs. |
| Overall | 0.67 | **0.69** | Net lift, driven mostly by stability. |
| Relevance | 0.44 | 0.44 | **Data ceiling** — 1 jazz / 1 metal song caps precision@5 at 0.20. |
| Confidence | 0.40 | 0.40 | **Inherent** — several equally-good matches, not fragility. |

**The surprise: the metrics stopped me from fooling myself.** My original hypothesis was that energy dominance was evicting true matches from the top-k — but the report showed exact matches were *already* surfacing. Relevance turned out to be a **catalog problem**, and the flat confidence was **healthy** (close scores mean several right answers, not a fragile ranking). The scoring changes still earned their place by lifting stability and making the #1 pick win decisively, so I kept them and documented the two structural ceilings — a **sparse catalog** and **correlated features** — honestly rather than pretending code had fixed them. All 8 reliability tests pass.

---

## 9. Collaboration with AI

I used AI throughout this project to generate code, shape the algorithm, and reason about edge cases.

- **A genuinely helpful instance:** the AI could **think across the whole system** — reading multiple files and suggesting fixes that stayed consistent across them (for example, keeping the CLI, the Streamlit app, and the reliability harness all aligned on one scoring core). That cross-file awareness caught things I would have had to hunt for manually.
- **A flawed instance:** the AI can be **overconfident**. As reflected in the evaluation above, the real problem was mostly the **data's size and variety**, but the AI (and my own first hypothesis) leaned toward a scoring explanation. In this case the flaw was harmless — the metrics corrected the story — so no fix was needed, but I'll revert or push back when a confident suggestion doesn't match the evidence.

The broader lesson: AI is a strong collaborator for breadth and speed, but it needs a human to **check its confidence against measured reality**.

---

## 10. Future Work

- **Validate & clamp inputs:** clip `target_energy` to `[0,1]` and lowercase genre/mood before matching, so bad input can't hijack or silently drop matches.
- **Stop double-counting energy & acousticness:** since they correlate −0.97, merge them into a single "vibe" axis so calm/acoustic fans aren't penalized twice.
- **Add a neutral acoustic option:** replace the `likes_acoustic` boolean with a three-way like / dislike / don't-care so under-specified users aren't silently pushed toward electronic music.
- **Score the unused features:** fold `valence` (measured positivity) into mood matching, and use `tempo_bpm` / `danceability` as tie-breakers.
- **Add diversity + freshness:** a secondary sort key or small randomization so the same profile doesn't get the identical list every run.
- **Rebalance the catalog:** add songs in under-represented genres/moods and in the mid-energy gap (~0.65–0.75) so niche and moderate-energy users get relevant matches.
- **Explore collaborative filtering:** combine the current content-based approach with user-behavior signals to recommend beyond what a single profile can express.

---

## 11. Personal Reflection

Through this project I learned how a recommender turns data into predictions, and — just as importantly — how measurement keeps that process honest. Balancing multiple factors is genuinely hard, and my biggest takeaway is that **it's hard to make one system that fits everyone.** I can tune the weights, add fuzzy matching, and squeeze out more stability and relevance, but only up to a point; the scoring rule encodes *my* assumptions about what "similar" and "good" mean, and the data caps what any rule can achieve.

The reliability harness taught me not to trust my own hypotheses without evidence — it showed me the ceilings were structural (sparse, correlated data), not bugs I could code away. The last mile toward a *genuinely* helpful, fair recommender can't be reached by code alone: it needs **real user experience and feedback** to guide the next round of weight and scoring adjustments. That's also where bias hides — in default assumptions, imbalanced data, and the labels I decided were "related." I'd like to fulfill the future-work items and eventually fold in collaborative filtering to make Snoofy more robust and more fair.
