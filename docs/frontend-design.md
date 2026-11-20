# Frontend Design

Status: **Phase 0 draft — awaiting approval** · Last updated: 2026-11-18

## 1. Responsibilities

The Next.js app is both the **UI** and the **BFF** (backend-for-frontend):
- Renders pages, mostly as **React Server Components** that call services server-side
  (tokens never handled by browser JS beyond the IdP SDK's own session cookie).
- Exposes a few **route handlers** (`/api/*`) for browser-initiated mutations.
- Never contains ranking logic or business rules.

## 2. Pages & routes

| Route | Access | Content |
|---|---|---|
| `/` | public | Landing: what it is, sign in/up CTA, TMDB attribution |
| `/sign-in`, `/sign-up` | public | IdP-hosted or embedded components |
| `/onboarding` | 🔒 | 3-step wizard: country/region → languages (ordered) → genres (optional) + tracking consent |
| `/home` | 🔒, onboarded | Personalized rows (carousels) |
| `/search` | 🔒 | Search box, filters (genre, language, year), paginated grid |
| `/movies/[id]` | 🔒 | Details, watchlist/like buttons, simulate-watch slider, *More like this* |
| `/watchlist` | 🔒 | Paginated grid |
| `/settings` | 🔒 | Preferences summary (+ Edit → `/onboarding`), consent toggle, data explanation, delete account |
| `/goodbye` | public | Shown after account deletion |
| `/about/data` | public | Data sources, licenses, proxy vs real signals explained |

**As built in Phase 2** (differs from the draft above where noted):
- `/onboarding` is one page with four fieldsets, not a multi-step wizard: a plain `<form>`
  + Server Action works without JavaScript and keeps every choice on errors. It doubles as
  the "edit preferences" page.
- `/settings` is one page instead of `/settings/preferences` + `/settings/privacy`.
- Next.js 16 `proxy.ts` (formerly `middleware.ts`) only runs `clerkMiddleware()`. Pages gate
  themselves with `auth.protect()`. "Not onboarded → `/onboarding`" is decided by `/home`
  when user-service answers 404, not by the proxy (no extra flag to keep in sync).
- Mutations use Server Actions (`app/onboarding/actions.ts`, `app/settings/actions.ts`)
  instead of `api/preferences` / `api/account` route handlers.

## 3. Component inventory

```
app/
  (public)/page.tsx, about/data/page.tsx
  (auth)/sign-in, sign-up
  (app)/layout.tsx            ← AppShell: header, nav, footer with attribution
  (app)/home/page.tsx
  (app)/search/page.tsx
  (app)/movies/[id]/page.tsx
  (app)/watchlist/page.tsx
  (app)/onboarding/page.tsx
  (app)/settings/...
  api/events/route.ts, api/watchlist/[movieId]/route.ts, api/preferences/route.ts, api/account/route.ts
components/
  ui/            Button, Chip, Toggle, Slider, Dialog, Skeleton, Toast   (presentational only)
  movie/         MovieCard, MovieGrid, MovieRow (carousel), MovieHero, PosterImage
  reco/          WhyThisPopover, SignalBadge ("Proxy" / "Based on your activity")
  onboarding/    CountryRegionStep, LanguageRankStep, GenreStep, ConsentStep
  tracking/      ImpressionTracker, EventQueueProvider
lib/
  api/           user.ts, catalog.ts, reco.ts   ← typed clients (generated types), timeouts, fallbacks
  auth/          getAccessToken(), requireUser()
  tracking/      queue.ts (batching, retries, sendBeacon)
```

**Separation rule (CLAUDE.md):** `components/` are presentational and receive props;
`lib/api/` does all integration. Pages wire them together.

## 4. Key UX details

- **MovieRow carousel:** horizontal scroll-snap list; left/right buttons; arrow-key
  navigation within the row; `aria-roledescription="carousel"`, each card a link with
  accessible name "Title (Year)". No autoplay. Honors `prefers-reduced-motion`.
- **WhyThisPopover:** button "Why this?" on each card → reasons from the API, plus signal
  badge. Keyboard and screen-reader accessible.
- **Proxy labeling:** rows with `signal.type = provider_proxy` show a visible badge, not
  just a tooltip.
- **Simulate watching:** on details page, a slider + "Record simulated watch" button,
  clearly labeled "Simulation — this app does not stream movies".
- **Language step:** chips for selection + drag/arrow buttons to reorder; copy explains
  "We won't guess your language from your location."
- **Skeletons** for streaming rows (React `Suspense` per row, so a slow row doesn't block others).
- **Empty/error states** for every list; recommendation failure shows popular fallback with
  a subtle "Personalization temporarily unavailable" note.
- **Responsive:** 2 cards per view at 360 px, up to 6–7 on desktop; Tailwind breakpoints.

## 5. Interaction tracking (client)

- `ImpressionTracker` uses `IntersectionObserver`: impression when a card is ≥50% visible
  for ≥1 s, once per card per page view.
- Click, like, skip ("Not interested" menu item), watchlist and simulated watch events are
  emitted by their controls.
- Each event gets `event_id = crypto.randomUUID()` at creation → safe retries.
- Queue flushes every 10 s, at 20 events, or on `visibilitychange: hidden` via
  `navigator.sendBeacon('/api/events')`.
- **No tracking calls at all** when consent is off (checked client-side for efficiency and
  server-side for enforcement).

## 6. User journeys (flow)

```
Landing → Sign up (IdP) → /onboarding
  Step 1 Country (required) + Region (optional)
  Step 2 Languages: pick ≥1, order them
  Step 3 Genres: pick 0–5 (skippable) + tracking consent (default OFF, explained)
→ PUT /api/preferences → /home

/home → card → /movies/[id] → like / add to watchlist / simulate 65% watch
→ back to /home → rows reflect new state (next load)
```

## 7. Frontend testing

| Layer | Tool | Examples |
|---|---|---|
| Unit/component | Vitest + Testing Library | MovieRow keyboard nav, WhyThisPopover renders reasons, event queue batching/dedupe |
| Accessibility | `@axe-core/playwright` | No serious violations on main pages |
| E2E | Playwright | Sign-up → onboarding → home; watchlist add/remove; consent off ⇒ no `/api/events` requests |
| Types | `tsc --noEmit` with generated OpenAPI types | contract drift fails build |

E2E auth uses the IdP's official testing mode/test users — never a production auth bypass.

## 8. Security headers & practices

CSP (images from TMDB CDN allowed), `X-Frame-Options: DENY` via `frame-ancestors`,
`Referrer-Policy: strict-origin-when-cross-origin`, no secrets in `NEXT_PUBLIC_*` variables,
CSRF protection for route handlers (same-site cookies + origin check).
