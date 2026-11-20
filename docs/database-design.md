# Database Design

Status: **Approved 2026-11-18; user-service tables implemented (step 2.2)** · Last updated: 2026-11-20

Constraint names follow a fixed convention (`pk_<table>`, `fk_<table>_<col>_<referred>`,
`uq_<table>_<cols>`, `ck_<table>_<name>`) so migrations can reference them reliably.

## 1. Isolation model

One PostgreSQL 16 server locally, **three databases**, **three login roles**:

| Database | Role | Granted to | Migrations |
|---|---|---|---|
| `user_db` | `user_svc` | user-service only | `services/user-service/migrations/` (Alembic) |
| `catalog_db` | `catalog_svc` | catalog-service only | `services/catalog-service/migrations/` |
| `reco_db` | `reco_svc` | recommendation-service only | `services/recommendation-service/migrations/` |

Each role can connect only to its own database, so a cross-service query is not just
discouraged — it fails. In production these could become separate servers with no code
changes (only connection strings).

**Conventions:** UUID primary keys (`gen_random_uuid()`), `timestamptz` in UTC,
`created_at`/`updated_at` columns, snake_case, explicit `CHECK` constraints for
enumerations (simpler to migrate than Postgres `ENUM` types). `user_sub` = IdP `sub` claim.

Migration policy: forward-only, reviewed; destructive migrations (drop/rename) require
explicit approval and a two-step expand → contract rollout.

## 2. user-service (`user_db`)

Implemented in migration `0002` (Phase 2, step 2.2) except `watchlist_items` (Phase 3).
Changes from the Phase 0 draft: no `display_name` (data minimisation — nothing needs it) and
no `deleted_at` (deletion is a hard delete with cascade; revisit in step 2.5 only if the
cross-service deletion workflow needs a marker); `country_code` is `varchar(2)` + a format
CHECK; `onboarded_at` is NOT NULL because a preferences row exists only once onboarded.
CHECKs validate code *format*; vocabulary membership is validated by the application.

```sql
users (
  id            uuid PK DEFAULT gen_random_uuid(),
  user_sub      text UNIQUE NOT NULL CHECK (length 1..255),  -- IdP subject; no email/name stored
  created_at, updated_at timestamptz NOT NULL DEFAULT now()
)

user_preferences (
  user_id        uuid PK FK→users(id) ON DELETE CASCADE,
  country_code   varchar(2) NOT NULL CHECK (~ '^[A-Z]{2}$'),   -- ISO 3166-1, user-chosen
  region_code    varchar(6) NULL,              -- ISO 3166-2 e.g. 'IN-AP'; must start with country_code || '-'
  onboarded_at   timestamptz NOT NULL,
  updated_at     timestamptz NOT NULL
)

user_languages (
  user_id        uuid FK ON DELETE CASCADE,
  language_code  varchar(3) NOT NULL,          -- ISO 639-1, CHECK (~ '^[a-z]{2,3}$')
  rank           smallint NOT NULL CHECK (rank BETWEEN 1 AND 10),
  PRIMARY KEY (user_id, language_code),
  UNIQUE (user_id, rank)
)

user_genres (
  user_id     uuid FK ON DELETE CASCADE,
  genre_slug  text NOT NULL,                   -- validated against contracts/vocab/genres.v1.json
  PRIMARY KEY (user_id, genre_slug)
)

user_consents (
  user_id     uuid FK ON DELETE CASCADE,
  purpose     text CHECK (purpose IN ('personalization_tracking')),
  granted     boolean NOT NULL,
  updated_at  timestamptz NOT NULL,
  PRIMARY KEY (user_id, purpose)
)

watchlist_items (
  user_id   uuid FK ON DELETE CASCADE,
  movie_id  uuid NOT NULL,                     -- catalog ID; NOT a foreign key (other service)
  added_at  timestamptz NOT NULL,
  PRIMARY KEY (user_id, movie_id)
)
INDEX watchlist_items (user_id, added_at DESC, movie_id)   -- keyset pagination
```

`movie_id` has no FK because the movie lives in another database. Integrity is enforced
at write time by calling catalog `GET /v1/movies/{id}`. If a movie is later removed from
the catalog, hydration returns "unavailable" and the UI hides/flags it.

## 3. catalog-service (`catalog_db`)

```sql
movies (
  id                uuid PK,
  title             text NOT NULL,
  original_title    text NULL,
  overview          text NULL,
  release_date      date NULL,
  runtime_minutes   smallint NULL,
  original_language varchar(3) NULL,
  poster_path       text NULL,                -- provider-relative path, URL built at read time
  adult             boolean NOT NULL DEFAULT false,
  search_tsv        tsvector GENERATED ALWAYS AS (to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(original_title,''))) STORED,
  created_at, updated_at timestamptz NOT NULL
)
INDEX movies USING GIN (search_tsv)
INDEX movies USING GIN (title gin_trgm_ops)     -- typo-tolerant search (pg_trgm)
INDEX movies (updated_at, id)                   -- feature sync cursor

genres          (slug text PK, name text NOT NULL)
movie_genres    (movie_id FK, genre_slug FK, PRIMARY KEY (movie_id, genre_slug))
movie_languages (movie_id FK, language_code, kind CHECK (kind IN ('original','spoken')),
                 PRIMARY KEY (movie_id, language_code, kind))
movie_countries (movie_id FK, country_code char(2), kind CHECK (kind IN ('production','release')),
                 release_date date NULL, PRIMARY KEY (movie_id, country_code, kind))

external_ids (
  movie_id uuid FK, source text CHECK (source IN ('tmdb','movielens','imdb','wikidata','fixture')),
  external_id text NOT NULL,
  PRIMARY KEY (source, external_id)
)

source_metrics (                               -- provenance-preserving numeric signals
  movie_id uuid FK, source text, metric text,  -- e.g. ('tmdb','popularity'), ('movielens','rating_count')
  value double precision NOT NULL, as_of timestamptz NOT NULL,
  PRIMARY KEY (movie_id, source, metric)
)

import_runs (
  id uuid PK, source text, started_at, finished_at timestamptz,
  status text CHECK (status IN ('running','succeeded','failed')),
  inserted int, updated int, skipped int,
  license_note text NOT NULL                    -- e.g. 'TMDB terms reviewed 2026-11-18'
)
```

The simple `'simple'` text-search config is used because titles span many languages; an
English stemmer would mangle Telugu transliterations.

## 4. recommendation-service (`reco_db`)

```sql
movie_features (                               -- READ MODEL synced from catalog API
  movie_id          uuid PK,
  genres            text[] NOT NULL,
  original_language varchar(3),
  spoken_languages  text[] NOT NULL,
  release_countries text[] NOT NULL,
  release_year      smallint NULL,
  popularity_raw    double precision NULL,     -- TMDB popularity
  rating_mean       double precision NULL,     -- MovieLens or TMDB vote average
  rating_count      integer NULL,
  feature_version   smallint NOT NULL,
  source_updated_at timestamptz NOT NULL,      -- catalog's updated_at (sync cursor)
  synced_at         timestamptz NOT NULL
)
feature_sync_state (id smallint PK DEFAULT 1, cursor_updated_at timestamptz, cursor_id uuid, last_success_at timestamptz)

popularity_stats (
  scope_type   text CHECK (scope_type IN ('global','country','region','language')),
  scope_value  text NOT NULL,                  -- 'all', 'IN', 'IN-AP', 'te'
  movie_id     uuid NOT NULL,
  score        double precision NOT NULL,      -- normalized 0..1
  signal       text CHECK (signal IN ('provider_proxy','internal_events','blended')),
  computed_at  timestamptz NOT NULL,
  PRIMARY KEY (scope_type, scope_value, movie_id)
)
INDEX popularity_stats (scope_type, scope_value, score DESC)

interaction_events (
  event_id     uuid PK,                        -- client-generated idempotency key
  user_sub     text NOT NULL,
  movie_id     uuid NOT NULL,
  event_type   text CHECK (event_type IN ('impression','click','like','unlike','skip',
                                          'watchlist_add','watchlist_remove','watch_progress')),
  value        real NULL CHECK (value IS NULL OR value BETWEEN 0 AND 1),  -- watch progress fraction
  surface      text NULL,                      -- 'home:top_picks', 'details:similar', 'search'
  position     smallint NULL,
  rec_request_id uuid NULL,                    -- links event to the recommendation that showed it
  is_simulated boolean NOT NULL,
  occurred_at  timestamptz NOT NULL,           -- client time (clamped to ±24h of received)
  received_at  timestamptz NOT NULL DEFAULT now()
)
INDEX interaction_events (user_sub, occurred_at DESC)
INDEX interaction_events (movie_id, occurred_at DESC)

user_feature_state (                           -- incrementally maintained affinities
  user_sub          text PK,
  language_weights  jsonb NOT NULL,            -- {"en": 14.2, "te": 3.1}   decayed evidence mass
  genre_weights     jsonb NOT NULL,            -- {"thriller": 11.0, ...}
  total_weight      double precision NOT NULL,
  liked_movie_ids   uuid[] NOT NULL,           -- recent positives (bounded, e.g. 200) for content profile
  suppressed_ids    uuid[] NOT NULL,           -- skipped / ignored items (bounded)
  event_count       integer NOT NULL,
  updated_at        timestamptz NOT NULL
)

recommendation_requests (
  id uuid PK, user_sub text, surface text, algorithm_version text,
  degraded boolean, created_at timestamptz
)
recommendation_items (
  request_id uuid FK, position smallint, movie_id uuid, score double precision,
  components jsonb,                            -- {"pop":0.21,"lang":0.30,"genre":0.12,"content":0.08}
  reasons jsonb,                               -- [{"code":"language_pref","params":{"lang":"te"}}]
  PRIMARY KEY (request_id, position)
)
```

**Why log recommendations?** To compute offline metrics like click-through by position,
to reproduce "why did I see this?", and later to train learned rankers with proper
exposure data. Retention: 90 days (purged by a scheduled job), documented in privacy notes.

**Growth:** `interaction_events` is the only table expected to grow quickly. When it
passes ~10M rows we will consider monthly range partitioning on `occurred_at` — not before.

## 5. Deletion paths (privacy)

| Data | Deleted by | Mechanism |
|---|---|---|
| Profile, prefs, consents, watchlist | user-service `DELETE /v1/me` | row delete + cascades |
| Events, feature state, rec logs | recommendation-service `DELETE /v1/me/events` | delete by `user_sub` |
| Credentials | IdP | BFF calls IdP user-deletion API |
| Catalog | — | contains no user data |

The BFF orchestrates the three deletes; each is idempotent so it can retry safely.

## 6. Migrations workflow

```
cd services/<service>
uv run alembic revision --autogenerate -m "add watchlist"   # review generated file!
uv run alembic upgrade head
```

Autogenerate output is always reviewed by a human; CI runs `alembic upgrade head` on an
empty database to prove migrations apply cleanly from scratch.
