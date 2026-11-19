# ADR 0001 — Service boundaries and data ownership

- **Status:** Accepted (2026-11-18)
- **Date:** 2026-11-18
- **Deciders:** project owner

## Context

We are building a movie discovery and recommendation platform as a learning project with
goals that explicitly include microservice communication and data ownership. We need to
decide how to split the backend and who owns which data. Constraints: one developer,
local Docker Compose, PostgreSQL, FastAPI, Next.js; no premature infrastructure.

## Decision

Three backend services plus a Next.js UI/BFF:

1. **user-service** — profile, country/region, languages, genres, consents, watchlist.
2. **catalog-service** — movie metadata, vocabularies, search, import jobs, provider metrics.
3. **recommendation-service** — interaction events, learned user features, a read-model
   copy of movie features, popularity stats, ranking, explanations, evaluation.

Rules:
- Each service owns its own Postgres **database and login role**; no cross-database access.
- Communication is synchronous HTTP with versioned OpenAPI contracts (`contracts/`).
- Shared vocabularies (genre slugs, ISO codes) are versioned contract files, not shared code.
- Users are identified across services by the IdP `sub` claim.
- The browser talks only to the Next.js BFF.

## Options considered

| Option | Pros | Cons |
|---|---|---|
| **A. Modular monolith** (one FastAPI app, modules, one DB with schemas) | Simplest; one deploy; no network failures; easy refactors | Doesn't teach service communication; boundaries easy to violate |
| **B. Three services (chosen)** | Clear ownership; independent deploy/tests; recommender can fail or be rewritten in isolation; matches learning goals | More moving parts; network calls and latency; contract maintenance; eventual consistency of feature read model |
| **C. Finer split** (separate watchlist, events, search, auth services) | Even more isolation | Overhead with no current benefit; many tiny services for one developer |

## Rationale

- Boundaries follow sources of truth and rates of change (profiles vs catalog imports vs
  algorithm iteration).
- Interaction events live in the recommendation-service because it is their only consumer
  today; extracting an event/ingestion service is deferred until a second consumer or a
  durability requirement appears (see `service-communication.md` §6).
- Watchlist lives with the user (it is user-owned data with simple CRUD), not in the
  catalog.

## Consequences

- ✅ A recommender bug cannot corrupt profiles or catalog data.
- ✅ Homepage can degrade to catalog popularity when recommendation-service fails.
- ⚠️ recommendation-service holds a *stale-able copy* of movie features; we monitor sync age.
- ⚠️ Account deletion must be orchestrated across services (idempotent deletes, BFF retries).
- ⚠️ Using IdP `sub` as cross-service user key couples data to the IdP; switching IdPs
  requires a mapping migration.
- ⚠️ Higher operational overhead than a monolith — accepted for learning value; revisit if
  it slows progress significantly.

## Revisit when

- A second consumer of interaction events appears → consider an event ingestion service + broker.
- Search needs exceed Postgres FTS → consider a dedicated search component inside catalog.
- Team or traffic growth justifies splitting further — with measurements.
