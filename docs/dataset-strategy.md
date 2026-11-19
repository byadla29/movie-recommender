# Dataset Strategy

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

> **Not legal advice.** Terms change. Before each import we re-read the source's current
> terms and record the review date in `import_runs.license_note`. Summaries below are
> for planning and must be verified against the official pages at use time.

## 1. What data we need, and which signals are real

| Need | Ideal signal | What we can actually get | Label in product |
|---|---|---|---|
| Movie metadata (title, overview, genres, runtime, release date) | Licensed provider | TMDB API, Wikidata, MovieLens (titles/genres only) | — |
| Original/spoken language | Provider metadata | TMDB (`original_language`, `spoken_languages`), Wikidata | — |
| Countries | Provider metadata | TMDB (`production_countries`, per-country release dates) | — |
| Global popularity | Engagement counts | TMDB `popularity` (their own proprietary signal), MovieLens rating counts | "Popular (TMDB)" |
| **Regional popularity** | Views per region | **Not available** from any free source we know of | "Popular releases in India — based on global popularity, not regional viewing" (**proxy**) |
| User–movie preferences for training/eval | Real ratings | MovieLens ratings (real, but US-centric users, mostly older Western films, no locations or languages) | Only in offline eval reports |
| Watch sessions | Real playback | None; we don't stream | **Simulated** watch progress, flagged `is_simulated` |
| Our own engagement | Our events | Our users' events (tiny volume) | Used once thresholds met (`recommendation-design.md` §2.3) |

## 2. Candidate sources

### 2.1 MovieLens (GroupLens Research)
- **Content:** ratings (0.5–5), tags, movie titles with year, pipe-separated genres, and
  `links.csv` mapping to IMDb and TMDB IDs. Variants: `ml-latest-small` (~100k ratings,
  ~9k movies), `ml-32m` (~32M ratings).
- **Terms (summary, verify):** research/education use; must cite the GroupLens paper
  (Harper & Konstan, 2015); **no redistribution** without permission; commercial use
  requires permission.
- **Our use:** offline evaluation and collaborative-filtering experiments; aggregate
  rating stats stored as `source_metrics` with provenance.
- **Limitations:** no language, no country, no user location; few Indian-language films
  (Telugu coverage is sparse); ratings ≠ watching; heavily skewed to popular Western titles.
- **Repo rule:** never committed. Download script verifies checksum into `data/raw/` (git-ignored).

### 2.2 TMDB API (The Movie Database)
- **Content:** rich metadata incl. languages, countries, release dates by country,
  posters, a `popularity` score, `vote_average`/`vote_count`, `/discover` filters
  (`with_original_language`, `region`).
- **Terms (summary, verify):** free API key for **non-commercial** use; attribution required
  ("This product uses the TMDB API but is not endorsed or certified by TMDB" + logo);
  commercial use requires a separate agreement; follow their rules on caching/storage and
  rate limits; images served from TMDB's image CDN.
- **Our use:** primary metadata source for a catalog that actually contains Telugu,
  Hindi, Tamil, English etc. titles. Import a bounded set (e.g. top-N by popularity per
  language of interest + all titles linked from MovieLens).
- **Limitations:** `popularity` is a global, proprietary, time-varying signal — **not
  regional**; community-sourced metadata may be incomplete for regional films.
- **Repo rule:** API key only in `.env`; imported data lives in Postgres, not Git.

### 2.3 Wikidata
- **Content:** structured film facts (language, country, genre, IDs). **License: CC0**
  (public domain dedication) — the most permissive option.
- **Our use:** optional enrichment/fallback; good for license-clean sample fixtures.
- **Limitations:** uneven coverage; genre taxonomy differs from TMDB (needs mapping).

### 2.4 IMDb non-commercial datasets
- **Terms (summary):** personal and non-commercial use only; no republishing.
- **Decision:** **not used** initially — TMDB + MovieLens cover our needs, fewer license risks.

### 2.5 Synthetic / fictional fixtures (ours)
- ~30 fictional movies (made-up titles, languages, genres) + scripted synthetic users.
- Committed to `data/fixtures/` — we own them, so no license issue.
- Purpose: deterministic tests and demos. **Never evidence of real-world quality.**

## 3. Normalization rules

- Languages: ISO 639-1 (`te`, `en`, `hi`); TMDB uses these already.
- Countries: ISO 3166-1 alpha-2; regions ISO 3166-2 (`IN-AP`).
- Genres: our controlled vocabulary `contracts/vocab/genres.v1.json` (slugs like
  `thriller`, `crime`, `romance`), with mapping tables from TMDB genre IDs and MovieLens
  genre strings. Example: MovieLens `Sci-Fi` → `science-fiction`; TMDB `878` → `science-fiction`.
- Movie identity: our own UUID; `external_ids(source, external_id)` unique. MovieLens ↔ TMDB
  joined via `links.csv` `tmdbId`.

## 4. Proxy labeling policy (FR-15)

Any signal shown to users must say where it comes from:

| Row | Computation | Visible label |
|---|---|---|
| Popular in Telugu | TMDB popularity among movies with `original_language = te` | "Popular Telugu films (TMDB)" |
| Popular releases in India | TMDB popularity among movies with an India release date | "Released in India · ranked by global popularity" |
| Trending in your region | Our own decayed event counts from users who *chose* that region, only when ≥ threshold events | "Trending among users in Andhra Pradesh" |

## 5. Data pipeline (Phase 3)

```
download (checksum) → data/raw/ (git-ignored)
   → catalog-service CLI: parse → normalize → upsert (idempotent by external_id)
   → import_runs row (source, counts, license_note, started/finished)
   → recommendation-service sync-features pulls derived features via API
```

Re-running an import must not duplicate movies (upsert on `(source, external_id)`).
