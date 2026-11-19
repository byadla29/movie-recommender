# Requirements

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

This document defines *what* the platform must do and *how well*. It deliberately says
nothing about frameworks; see `architecture.md` for the *how*.

## 1. Product statement

A movie **discovery and recommendation** web app. Users sign in, tell us where they are
and which languages/genres they like, browse and search a catalog of movie *metadata*,
keep a watchlist, and get a personalized homepage that adapts as they interact.

**Out of scope (permanently):** video streaming, hosting or linking to pirated content,
redistributing licensed datasets.

## 2. Personas

| Persona | Description | Main need |
|---|---|---|
| New user (cold start) | Just signed up; zero history | Relevant movies immediately from explicit choices |
| Returning user | Has clicked, liked, skipped, "watched" (simulated) | Homepage that reflects behavior, not just onboarding |
| Developer/learner (you) | Building and studying the system | Transparent scores, reproducible evaluation, debuggable services |

## 3. Key user journeys

**J1 — Sign up & onboarding.** Visitor → sign up (identity provider) → onboarding wizard:
country (required), region/state (optional), languages (≥1, ordered), genres (optional,
0–5) → personalized homepage.

**J2 — Homepage.** Rows such as *Top picks for you*, *Popular in Telugu*, *Popular in
English*, *Popular releases in India (proxy)*, *Because you liked X*, *Thrillers for you*.
Each card offers a "Why this?" explanation.

**J3 — Search & browse.** Text search with filters (genre, language, release year),
paginated results.

**J4 — Movie details.** Metadata, genres, languages, *More like this*, watchlist toggle,
like button, "Simulate watching" control.

**J5 — Watchlist.** Add/remove/list, paginated.

**J6 — Preferences & privacy.** Change region/languages/genres at any time; view/withdraw
consent for behavior tracking; delete account and associated data.

**J7 — Adaptation (the example scenario).** A user from Andhra Pradesh picks Telugu and
English. Initially both languages appear. After repeatedly engaging with English
thrillers, English thrillers rise in *Top picks* — but Telugu titles never vanish
entirely, because explicit choices remain a prior (see `recommendation-design.md` §5).

## 4. Functional requirements

IDs are referenced from `TASKS.md` and tests.

### Identity & session
- **FR-1** Register, sign in, sign out via a managed identity provider.
- **FR-2** Protected pages redirect unauthenticated users to sign-in.
- **FR-3** Every protected backend endpoint validates the access token server-side and
  scopes data to the token's subject (no user IDs taken from URLs for "my" data).

### Onboarding & profile
- **FR-4** User *chooses* country (ISO 3166-1) and optionally region (ISO 3166-2, e.g. `IN-AP`).
- **FR-5** User chooses ≥1 language (ISO 639-1, e.g. `te`, `en`), ordered by preference.
- **FR-6** User optionally chooses 0–5 genres.
- **FR-7** The system never infers language or identity from region. Region is only used
  for *regional popularity* signals, and only if the user supplied it.
- **FR-8** Preferences are editable anytime; changes affect the next homepage load.

### Catalog
- **FR-9** Import movie metadata from license-compliant sources via an offline job.
- **FR-10** Search by title text with filters (genre, language, year); paginated.
- **FR-11** Movie details by ID; batch lookup by IDs (for hydrating lists).
- **FR-12** Record data provenance (source, import time) for every movie and metric.

### Watchlist
- **FR-13** Add (idempotent), remove, list (paginated) watchlist items; only the owner can read/modify.

### Recommendations
- **FR-14** Homepage returns multiple labeled rows of ranked movies.
- **FR-15** Cold start: rank from explicit preferences + popularity; any regional signal
  that is a proxy (not real regional engagement) is **labeled as such in the UI**.
- **FR-16** *More like this* on movie details (content similarity).
- **FR-17** Each recommended item carries a human-readable reason.
- **FR-18** Recommendations include some diversity/exploration and do not show the same
  ignored items indefinitely.

### Interactions
- **FR-19** Track impressions, clicks, likes, skips, watchlist adds and *simulated* watch
  progress — only when the user has granted consent for personalization tracking.
- **FR-20** Events are idempotent (client-generated event ID) and persisted durably.
- **FR-21** Ranking uses persisted events; a test demonstrates that a scripted sequence of
  events measurably changes recommendations.
- **FR-22** Simulated and synthetic data are flagged (`is_simulated`) and never presented as
  real-world engagement.

### Evaluation
- **FR-23** Offline evaluation reports Recall@K, NDCG@K, catalog coverage and intra-list
  diversity, reproducible with a fixed random seed.

## 5. Non-functional requirements

Numbers are **targets to measure**, not claims. Nothing here asserts scale we have not tested.

| ID | Category | Requirement |
|---|---|---|
| NFR-1 | Latency | Homepage BFF render p95 < 800 ms; recommendation endpoint p95 < 250 ms with a ≤50k-movie catalog on a dev laptop. Measured in Phase 6. |
| NFR-2 | Availability (dev) | If recommendation-service is down, homepage still renders popular rows from catalog-service (graceful degradation). |
| NFR-3 | Reliability | All inter-service calls have timeouts; retries only on idempotent reads, max 2, with jitter. |
| NFR-4 | Security | No plaintext passwords stored by us (IdP handles credentials); token validation on every protected endpoint; ownership checks; secrets only via env; `.env` never committed. |
| NFR-5 | Privacy | Store minimal PII (no email/name copies unless needed); coarse location only; consent gates tracking; account deletion removes data from all services. |
| NFR-6 | Accessibility | WCAG 2.2 AA target: keyboard-navigable carousels, visible focus, alt text, color contrast, reduced-motion support. |
| NFR-7 | Responsiveness | Usable from 360 px wide phones to desktop. |
| NFR-8 | Testability | Ranking logic is pure functions with deterministic unit tests; each service testable in isolation. |
| NFR-9 | Maintainability | Each service has its own deps, migrations, tests, OpenAPI contract. |
| NFR-10 | Observability | Structured JSON logs, request-ID propagation, `/health` and `/ready` per service. |
| NFR-11 | Licensing | Every dataset's license recorded in `dataset-strategy.md`; raw data never committed. |
| NFR-12 | Portability | `docker compose up` runs the whole stack locally. |

## 6. Assumptions

- A1. Single developer, learning-focused; ~10–15 hours/week (drives the timeline).
- A2. Initial catalog: 5k–50k movies. Users: a handful of real accounts plus clearly
  labeled synthetic users for testing.
- A3. No real regional engagement data exists at launch. "Regional popularity" begins as a
  labeled proxy and is gradually replaced by our own event counts once they exist.
- A4. Movie posters/metadata come from a provider whose terms we comply with (attribution
  shown in footer); non-commercial use.
- A5. Simulated watch progress is a user-driven UI control, not real playback.

## 7. Acceptance criteria for the MVP (end of Phase 5)

1. A new user can sign up, complete onboarding, and see ≥4 labeled homepage rows.
2. Every row/card shows a reason; proxy-based rows say "proxy" or equivalent.
3. Search, details, and watchlist work and are paginated; another user's watchlist is inaccessible (tested).
4. Scripted test: 20 positive events on English thrillers raises the share of English
   thrillers in *Top picks* top-20 versus baseline, while ≥1 Telugu title remains in top-20.
5. Turning off tracking consent stops event persistence (tested).
6. Deleting an account removes profile, watchlist and events (tested across services).
7. Offline evaluation script prints Recall@10, NDCG@10, coverage and diversity versus a
   popularity baseline on MovieLens, with the dataset limitations stated in the output.
