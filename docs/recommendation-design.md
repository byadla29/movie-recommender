# Recommendation System Design

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

The engine is built in layers. Each layer is useful alone and is a fallback for the next.

```
Layer 1  Popularity baseline (global / language / country-proxy / trending)
Layer 2  Explicit preference matching (languages, genres)          ← cold start = L1 + L2
Layer 3  Content-based similarity (cosine over movie feature vectors)
Layer 4  Behavior-learned affinities + hybrid ranking + diversity + exploration
Layer 5  (Phase 7) Collaborative filtering / matrix factorization / embeddings
```

Every recommended item records its **score components**, which also drive the "Why this?" text.

---

## 1. Notation

| Symbol | Meaning |
|---|---|
| `u`, `m` | a user, a movie |
| `L(m)` | original language of `m`; `S(m)` spoken languages |
| `G(m)` | set of genres of `m` |
| `e` | an interaction event with weight `w_e` and age `Δt_e` |
| `h` | half-life for time decay |
| `n_u` | user's decayed positive evidence mass ("how much we know") |
| all component scores | normalized into `[0, 1]` so weights are comparable |

---

## 2. Layer 1 — Popularity baselines

### 2.1 Quality-adjusted rating (Bayesian average)

**Problem:** a movie with one 5★ rating shouldn't beat one with 500 ratings averaging 4.2★.

**Formula** (the "weighted rating" used by IMDb's Top 250 style lists):

```
WR(m) = v/(v+m₀) · R  +  m₀/(v+m₀) · C
```

`R` = movie's mean rating, `v` = its number of ratings, `C` = mean rating over all movies,
`m₀` = prior strength (e.g. the 80th percentile of `v`). Intuition: pretend every movie
starts with `m₀` average-quality votes; real votes gradually outweigh the pretend ones.

**Example** (`C = 3.5`, `m₀ = 50`):

| Movie | R | v | WR |
|---|---|---|---|
| A | 4.8 | 5 | 5/55·4.8 + 50/55·3.5 = 0.436 + 3.182 = **3.62** |
| B | 4.2 | 500 | 500/550·4.2 + 50/550·3.5 = 3.818 + 0.318 = **4.14** |

B ranks above A despite a lower raw average. ✔

### 2.2 Popularity normalization

Provider popularity (TMDB) is heavy-tailed: a few movies score 1000+, most < 20. We
compress it with a log, then scale to `[0, 1]` within the scope (global, language, country):

```
pop(m) = log(1 + p_m) / log(1 + p_max)
```

Example: `p_max = 1000`; movie with `p = 30` → `log 31 / log 1001 = 3.43 / 6.91 = 0.50`.
Without the log it would be 0.03 — almost indistinguishable from obscure titles.

### 2.3 Trending (time-decayed counts) and regional popularity

From *our own* events (Phase 5+):

```
trend(m) = Σ_e  w_e · 2^(−Δt_e / h)          h = 7 days
```

Event today counts 1.0×, one week old 0.5×, two weeks 0.25×.

**Regional popularity** is the honest-labeling problem. Until we have real data from users
who *chose* a region, we use a **proxy**: provider popularity among movies released in
that country. Once real events accumulate, we blend with **shrinkage**:

```
regional(m, r) = (n_r · internal_r(m) + k · proxy_r(m)) / (n_r + k)        k = 50 events
```

With `n_r = 0` it's pure proxy; with `n_r = 450` it's 90% internal. The row's label states
which signal dominates (`provider_proxy` / `blended` / `internal_events`).

**Edge cases:** missing popularity → treat as 0 and rely on other signals; brand-new
movies → small freshness boost (Layer 4); region with no releases → hide the row.
**Complexity:** precomputed per scope by a job, `O(N log N)` sort; serving is an index read.
**Limitation:** popularity is self-reinforcing (popular → shown → more popular). Diversity
and exploration in Layer 4 counteract it.

---

## 3. Layer 2 — Explicit preference matching (cold start)

### 3.1 Preference priors

From onboarding: languages `{te, en}` → prior `p_u(te) = p_u(en) = 0.5`. (Phase 4 starts with
equal weights; rank is used for row order. Rank-weighted priors are a later experiment.)
Genres chosen `{thriller, drama}` → `p_u(thriller) = p_u(drama) = 0.5`; none chosen → uniform
over all genres (genre signal is then switched off for ranking until behavior arrives).

Region is **not** used to create language priors — FR-7.

### 3.2 Component scores

```
lang(m, u)  = max( a_u(L(m)),  0.5 · max_{l∈S(m)} a_u(l) )        original language counts fully,
                                                                   spoken languages half
genre(m, u) = cos( a_u^genre , x_m^genre )                          (cosine defined in §4)
```

At cold start `a_u = p_u` (no evidence yet). A Telugu movie scores `lang = 0.5`, a Korean
movie `0`.

**Cold-start ranking** = `0.40·pop + 0.35·lang + 0.25·genre` (weights evolve; §5.3).

---

## 4. Layer 3 — Content-based similarity

### 4.1 Feature vectors

Each movie becomes a vector built from blocks, each block L2-normalized then weighted:

| Block | Encoding | Weight |
|---|---|---|
| Genres | multi-hot over ~19 genres | 1.0 |
| Original language | one-hot | 0.5 |
| Release decade | one-hot | 0.3 |
| (Later) keywords / overview | TF-IDF, top terms | 0.5 |

### 4.2 Cosine similarity

```
cos(a, b) = (a · b) / (‖a‖ ‖b‖)       ∈ [0, 1] for non-negative vectors
```

It measures the *angle* between vectors, so a movie with many genres isn't automatically
"bigger". **Tiny example** over dimensions `[Thriller, Crime, Romance, en, te]` (weights
omitted for clarity):

```
A = Thriller+Crime, English  → [1,1,0,1,0]
B = Thriller, English        → [1,0,0,1,0]
C = Romance, Telugu          → [0,0,1,0,1]

cos(A,B) = (1+0+0+1+0) / (√3·√2) = 2 / 2.449 = 0.816
cos(A,C) = 0 / (√3·√2)          = 0
```

### 4.3 Uses

- **More like this** (`/v1/movies/{id}/similar`): top-K by `cos(x_m, x_j)`.
- **User content profile:** `p_u = Σ_e w_e · 2^(−Δt_e/h) · x_{m_e}` over positive events;
  `content(m, u) = cos(p_u, x_m)`.
- **"Because you liked X"** rows: neighbors of the user's most recent strongly liked movie.

**Implementation:** SciPy sparse matrix `X` (N × d), rows pre-normalized, so all similarities to
a query are one matrix–vector product `X · q`. **Complexity:** `O(N·d_nnz)` per query —
for N = 50k and ~5 non-zeros per row that's ~250k multiply-adds (well under 10 ms).
Precomputed item-item top-50 neighbors: `O(N²·d)` offline once (~minutes for 50k; can
be chunked). Memory for dense 50k×64 float32 = 12.8 MB.
**Edge cases:** movie with no genres → zero vector → similarity undefined → excluded; ties
broken by popularity then ID (deterministic).
**Limitations:** only as good as the metadata; can't discover "people who like X also like
Y" when X and Y look different (that's collaborative filtering, Layer 5); tends to
over-specialize (diversity re-ranking helps).

---

## 5. Layer 4 — Learning from behavior

### 5.1 Event weights

| Event | Weight `w_e` | Notes |
|---|---|---|
| impression | 0 | Exposure only; used for fatigue and CTR denominators |
| click (open details) | 0.5 | Weak positive |
| watchlist_add | 2.0 | Strong intent |
| like | 3.0 | Explicit positive; `unlike` reverses it |
| watch_progress (simulated) | 3 · progress | 0.65 → 1.95; ignored below 0.1 |
| skip | — | Not added to affinities; suppresses the item for 30 days |

Weights are hand-set hyperparameters, documented and tuned via simulation/offline tests —
not "learned" yet.

### 5.2 Affinity update: explicit prior + decayed evidence

For each language `l` (and analogously each genre `g`):

```
E_u(l) = Σ_{positive e, L(m_e)=l}  w_e · 2^(−Δt_e / h)      h = 30 days
n_u    = Σ_l E_u(l)

a_u(l) = ( α · p_u(l) + E_u(l) ) / ( α + n_u )              α = 10 (prior strength)
```

**Plain language:** explicit choices act like 10 "pretend events" split across your chosen
languages. Real behavior adds real evidence. As evidence grows, behavior dominates — but
your explicit choices never drop to exactly zero, and old behavior fades with a 30-day half-life.

**Incremental update (O(1) per event):** store `E` and `last_updated`; on a new event at
time `t`: `E ← E · 2^(−(t − t_last)/h) + w_e`. No need to re-scan history.

**The Andhra Pradesh example.** Prior `te 0.5, en 0.5`, `α = 10`. User generates 20 units
of positive weight on English thrillers (e.g. 4 likes + 4 watchlist adds), all recent:

```
a(en) = (10·0.5 + 20) / (10 + 20) = 25/30 = 0.833
a(te) = (10·0.5 +  0) / 30        =  5/30 = 0.167      ← reduced, not zero
```

Genre (no genres chosen → prior 1/19 ≈ 0.053 each):

```
a(thriller) = (10·0.053 + 20) / 30 = 0.684
a(other)    = (10·0.053 + 0)  / 30 = 0.0175   each
```

If the user then watches Korean films they never chose, `a(ko)` rises from 0 — location
and onboarding never lock preferences in.

### 5.3 Hybrid score

```
s(m,u) = w_pop·pop(m) + w_lang·lang(m,u) + w_genre·genre(m,u) + w_content·content(m,u)
         + w_fresh·fresh(m) − fatigue(m,u)
```

Confidence `c = n_u / (n_u + 10)` shifts weight from popularity to personal signals:

```
w_pop = 0.40 − 0.20c     w_lang = 0.35 − 0.05c     w_genre = 0.25     w_content = 0.25c
(sum = 1.0 for any c;  w_fresh = 0.05 small constant)
fatigue(m,u) = 0.15 · min(k_m, 3)/3     k_m = impressions without click in last 14 days
```

**Worked example** — three movies, freshness ignored:

| Movie | pop | lang (cold → learned) | genre (learned) | content (learned) |
|---|---|---|---|---|
| M1 English thriller | 0.60 | 0.5 → 0.833 | 0.721 | 0.80 |
| M2 Telugu drama (very popular) | 0.90 | 0.5 → 0.167 | 0.025 | 0.10 |
| M3 Telugu thriller | 0.70 | 0.5 → 0.167 | 0.721 | 0.60 |

(genre for M1/M3: `cos(a_genre, [thriller, crime]) = (0.684+0.0175)/√2 / 0.688 = 0.721`.)

*Cold start* (`c = 0`, genre off): `s = 0.40·pop + 0.35·lang`
- M1 = 0.240 + 0.175 = **0.415**, M2 = 0.360 + 0.175 = **0.535**, M3 = 0.280 + 0.175 = **0.455** → order M2, M3, M1.

*After 20 units of English-thriller evidence* (`c = 20/30 = 0.667`: w_pop 0.267, w_lang 0.317, w_genre 0.25, w_content 0.167):
- M1 = 0.160 + 0.264 + 0.180 + 0.134 = **0.738**
- M2 = 0.240 + 0.053 + 0.006 + 0.017 = **0.316**
- M3 = 0.187 + 0.053 + 0.180 + 0.100 = **0.520**
→ order **M1, M3, M2**. English thrillers rise; the Telugu *thriller* stays competitive
because the genre signal carries over across languages.

### 5.4 Candidate generation (two-stage retrieval → ranking)

Scoring every movie with every feature is wasteful once models get heavier, so we first
gather a few hundred plausible **candidates** from cheap sources, then rank only those:

| Source | Size |
|---|---|
| Global popularity top | 300 |
| Popularity within each preferred language | 200 each |
| Country proxy / regional | 150 |
| Content-profile nearest neighbors | 300 |
| Neighbors of recent likes | 50 per like (≤5 likes) |
| Trending (internal) | 100 |

Union → remove watchlisted, liked-already, suppressed (skipped), adult (unless enabled) →
typically 800–1500 candidates → score → re-rank.

### 5.5 Re-ranking: diversity (MMR), explicit-language floor, exploration

**Maximal Marginal Relevance** picks items one at a time:

```
next = argmax_{m ∉ S}  λ·s(m)  −  (1−λ)·max_{j∈S} cos(x_m, x_j)          λ = 0.7
```

Example: S = {M1}. M3 (s 0.520, similarity to M1 0.80) vs M4 (s 0.480, similarity 0.10):
- M3: 0.7·0.520 − 0.3·0.80 = 0.124
- M4: 0.7·0.480 − 0.3·0.10 = **0.306** → M4 chosen, avoiding a wall of near-duplicates.

**Explicit-language floor:** in *Top picks* top-20, each explicitly chosen language gets ≥2
slots if candidates exist (keeps Telugu visible for the Andhra user).

**Exploration:** fixed slots (positions 5 and 15 of 20) are filled from an *explore pool*
(preferred languages/genres with low exposure for this user), sampled with seed
`hash(user_sub, date)` for reproducibility. Reason shown: "Something different you might
like". Logged so evaluation can separate exploit vs explore clicks.

**Complexity:** MMR is `O(K·C)` similarity lookups for K=20 picks over C candidates — trivial.

### 5.6 Explanations

Contribution of each component = `w_i · f_i`. Components contributing ≥25% of the score
become reasons via templates:

| Component | Reason text |
|---|---|
| lang (explicit dominant) | "Because you chose Telugu" |
| lang (behavior dominant) | "You've been watching a lot in English" |
| genre | "You often engage with Thrillers" |
| content | "Similar to *{title}*, which you liked" |
| pop (proxy) | "Popular releases in India — based on global popularity" |
| explore | "Something different you might like" |

Explanations are generated from the real score, never written after the fact.

### 5.7 Feedback loop summary

```
show (log request + impressions) → user acts → event stored (idempotent)
  → affinities & profile updated (same txn) → next request ranks with new state
```

**Risk: feedback loops narrow the feed.** Mitigations: prior never reaches zero, MMR,
exploration slots, fatigue penalty, 30-day decay.

---

## 6. Layer 5 (Phase 7 preview — not built yet)

- **Implicit matrix factorization (ALS):** learn user/item vectors so `u·v ≈` preference
  from interaction matrix; train on MovieLens + our events.
- **Two-tower / embeddings** + approximate nearest-neighbor retrieval when catalogs grow
  beyond what brute-force handles within latency budget.
- **Learned ranker** (logistic regression / gradient boosting over our components) trained
  on logged impressions → clicks, with position-bias correction.

Each needs: explanation, worked example, offline comparison vs hybrid-v1, before adoption.

---

## 7. Evaluation

### 7.1 Offline on MovieLens (real ratings, limited signals)

Protocol: ratings ≥ 4 treated as positives; per-user **temporal split** (last 20% of each
user's positives = test; users with < 5 positives excluded); fixed seed. Because MovieLens
lacks language/region, only genre/content/popularity components can be evaluated here.

Compared models: random, global popularity, Bayesian-average quality, genre affinity,
content-based, hybrid-v1.

**Recall@K** = |relevant ∩ top-K| / |relevant|.
**NDCG@K** rewards relevant items ranked higher:

```
DCG@K = Σ_{i=1..K} rel_i / log₂(i+1)          NDCG@K = DCG@K / IDCG@K
```

Example: relevant = {A, B, C}; recommended top-5 = [A, X, C, Y, Z].
- Recall@5 = 2/3 = 0.667
- DCG = 1/log₂2 + 1/log₂4 = 1 + 0.5 = 1.5
- IDCG (3 relevant at top) = 1 + 1/log₂3 + 1/log₂4 = 1 + 0.631 + 0.5 = 2.131
- NDCG@5 = 1.5 / 2.131 = **0.704**

Also: **catalog coverage** (share of catalog recommended to anyone), **intra-list diversity**
(mean pairwise `1 − cos` within a list), **popularity bias** (mean popularity percentile of
recommendations).

### 7.2 Simulation tests (synthetic users — mechanism, not quality)

Scripted users with a hidden "true taste" (e.g. English thrillers) interact with our own
recommendations via a known probability model. We measure how many rounds until the
target segment's share of top-20 exceeds a threshold, and verify chosen languages keep
their floor. **This validates the adaptation mechanism only.** It says nothing about real
users and is labeled accordingly in reports.

### 7.3 Online (tiny scale)

CTR by row and position, like rate, from `recommendation_items` + events. With few users
these are anecdotal and reported with counts.

### 7.4 Latency

Benchmark `GET /v1/me/home` p50/p95 with 5k and 50k movies (Phase 6).

---

## 8. Testing plan for ranking code

All algorithms are pure functions (`numpy` arrays / dataclasses in, scores out) separate
from FastAPI routes and DB code.

| Test | Asserts |
|---|---|
| `test_bayesian_average` | Example in §2.1 gives 3.62 and 4.14 (±0.01) |
| `test_log_popularity_normalization` | 30 / 1000 → 0.50; empty scope handled |
| `test_decay_half_life` | weight after 1 half-life = 0.5 |
| `test_affinity_prior_never_zero` | explicit language stays > 0 after 1000 events elsewhere |
| `test_andhra_scenario` | §5.2 numbers; M1 > M3 > M2 after evidence; M2 > M3 > M1 cold |
| `test_cosine_examples` | §4.2: 0.816 and 0 |
| `test_mmr_prefers_diverse` | §5.5 example picks M4 |
| `test_language_floor` | ≥2 Telugu in top-20 when candidates exist |
| `test_exploration_deterministic` | same seed → same explore picks |
| `test_ndcg_example` | §7.1 example = 0.704 |
| `test_idempotent_events` | same `event_id` twice → affinities change once |

## 9. Assumptions & open questions

- Hyperparameters (α=10, h=30d, weights) are starting points; tuning documented in ADRs.
- Genre vocabulary mapping from TMDB/MovieLens may lose nuance (e.g. "Masala" films).
- Original language is a weak proxy for "language I'd watch it in" (dubbing data missing).
