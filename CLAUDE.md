# Movie Recommendation Platform — Claude Code Project Instructions

## Mission
Build a Netflix-style **movie discovery and personalized recommendation** web application from scratch. The project is for learning recommendation mathematics, frontend/backend engineering, microservice communication, reliability, and eventual scaling. **Do not build video streaming or host copyrighted films.** Explain important decisions so the developer learns, rather than generating unexplained code.

## Approved technical direction
- **Repository:** one Git monorepo containing independently runnable services.
- **Frontend:** Next.js (App Router), TypeScript, Tailwind CSS; use accessible, responsive components.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, Alembic.
- **Data:** PostgreSQL with separate *service-owned databases or schemas* and migrations. Services never query one another's tables directly.
- **Local development:** Docker Compose; HTTP/REST with documented OpenAPI contracts.
- **Auth:** prefer a maintained identity provider; validate tokens and authorization server-side. Never implement homemade cryptography or store plaintext passwords.
- **Initial services:**
  1. `user-service`: profiles, explicit country/region, language and genre preferences, watchlists.
  2. `catalog-service`: licensed/authorized movie metadata, import, genres, languages, search and movie details.
  3. `recommendation-service`: candidate generation, cold start, user features, scoring/ranking and evaluation.
- **Frontend/BFF:** Next.js server-side routes or an explicitly documented API gateway; do not add a separate gateway until justified.
- **Later, not day one:** interaction-event worker, message broker, Redis, collaborative filtering, vector search, model-training jobs, Kubernetes.

## Product behavior and MVP scope
1. Authentication and protected sessions.
2. Onboarding: user **chooses** location and languages (e.g. India, Telugu, English) and optional genres; never infer language or identity solely from region.
3. Browse/search catalog, movie details and watchlist.
4. Personalized homepage including popular-in-region, preferred-language and genre sections.
5. Cold-start ranking from explicit preferences plus **clearly labeled** regional popularity proxies when real regional engagement data is unavailable.
6. Track consent-appropriate impressions, clicks, likes, skips and *simulated* watch progress; persist events and use them to update ranking.
7. Show an understandable explanation of why a movie was recommended.

## Architecture rules (mandatory)
- Keep service boundaries explicit: each service owns its data, API, migration history, and tests.
- No cross-service SQL joins or direct reads of another service's database. Use API contracts or events.
- Favor simple synchronous HTTP initially; timeouts, explicit errors, bounded retries only for safe/idempotent operations.
- Add asynchronous messaging only when a concrete user interaction/reliability requirement warrants it. Specify event schemas, idempotency keys, retry and dead-letter behavior before adopting a broker.
- Secure every protected endpoint; apply authorization checks to resource ownership, not only authentication.
- Validate request payloads, paginate list responses, avoid secrets in logs, use `.env.example` with placeholders and never commit `.env` or credentials.
- Respect dataset licenses and API terms; do not scrape or redistribute content without permission. MovieLens is useful for ratings but lacks real individual watch-session and verified regional-popularity signals. Metadata from TMDB or another provider must comply with its terms.
- Keep privacy in mind: minimize user data, allow preference changes, document consent and deletion paths; use coarse region where possible.
- Do not claim the system supports millions of users without capacity measurements, load tests and an operational plan.

## Recommendation engineering rules
Implement algorithms incrementally, with clear mathematical explanations and reproducible tests:
1. Global and regional popularity baseline (fall back when user/history/data is missing).
2. Language/genre preference matching and weighted ranking.
3. Content-based similarity (e.g. cosine similarity over movie feature vectors).
4. Interaction-based personalization and exploration/diversity.
5. Later: collaborative filtering, matrix factorization, embeddings, candidate retrieval and learned ranking.

For every algorithm, explain inputs, feature construction, formula, tiny numerical example, edge cases, limitations, time/space complexity, and evaluation metrics. Include deterministic unit tests; consider Recall@K, NDCG@K, coverage/diversity, and latency when appropriate. Do not pretend synthetic interactions establish real-world recommendation quality.

## Repository organization
- `frontend/`: Next.js UI and BFF.
- `services/user-service/`, `services/catalog-service/`, `services/recommendation-service/`: independent FastAPI services.
- `contracts/`: versioned OpenAPI/event schema definitions.
- `data/`: ingestion scripts and small, license-compliant sample fixtures; exclude large/raw/private datasets from Git.
- `docs/requirements.md`: product flows and acceptance criteria.
- `docs/architecture.md`: component diagram, communication, data ownership and failure modes.
- `docs/api-contracts.md`: endpoints and example requests/responses.
- `docs/database-design.md`: per-service tables and migrations.
- `docs/recommendation-design.md`: algorithms, data assumptions and evaluation.
- `docs/implementation-plan.md`: phases and dependencies.
- `docs/adr/`: architecture decision records.
- `TASKS.md`: checked/unchecked tasks, decisions, blockers, next step.

Do not create every file and service up front. Scaffold what the **currently approved phase** requires.

## How to work in Claude Code
1. At the start of each task, read this file, `TASKS.md`, and only the relevant `docs/` and service instructions.
2. Inspect the existing repository before suggesting changes. Do not assume files or commands exist.
3. **Before major implementation:** propose a small scoped plan with affected files, API/data-contract changes, test strategy, and acceptance criteria. Wait for approval when architecture, dependencies, or scope materially changes.
4. Make one small, reviewable change at a time. Prefer simple code and clear names to speculative abstraction.
5. Implement backend business logic separately from routes; keep frontend presentation separate from API integration.
6. Write and run relevant unit/integration/UI tests and formatting/type checks. Report exact commands and outcomes; never claim success without executing them.
7. Update `TASKS.md` and impacted documents after verified changes. Summarize what was built, how to run it, remaining risks and the next smallest step.
8. Never silently overwrite user changes, delete data, run destructive migrations or deploy to production. Ask first.
9. Explain new algorithms or distributed-systems concepts in plain language with an example.

## Phased implementation order
- **Phase 0 — Design:** requirements, user journeys, data sources/license check, service boundaries, contracts, DB model, architecture decisions and `TASKS.md`.
- **Phase 1 — Foundation:** monorepo, Next.js app, three FastAPI skeletons, Docker Compose, Postgres ownership, health checks, env templates and CI.
- **Phase 2 — Identity & onboarding:** authentication, profile, preferred region/languages/genres and protected pages.
- **Phase 3 — Catalog & UX:** ingest permitted metadata, homepage, search, movie details and watchlist.
- **Phase 4 — Recommendations:** popularity baseline, regional/language cold start, content-based similarity and transparent ranking.
- **Phase 5 — Interactions:** durable user events, preference updates and evidence that recommendations change.
- **Phase 6 — Quality & deployment:** contract/integration/end-to-end tests, accessibility, observability, deployment and load-test baseline.
- **Phase 7 — Advanced learning:** asynchronous pipeline, model training, collaborative filtering, vector retrieval, caching and scaling experiments.

**First action if the repository is empty:** create and present Phase 0 documents and task breakdown. Do not generate the entire app in one step. Ask for approval before beginning Phase 1.
