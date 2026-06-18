# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [1.2.0] - 2026-06-18

### Changed
- **Code quality:** `get_rule_based_insights` decomposed into per-category helper
  functions; all rule thresholds, reduction factors, and flat savings promoted to
  named module constants (flight savings now reuse the published `factors.py`
  per-flight values instead of duplicated literals).
- Backend services switched from the legacy `get_event_loop().run_in_executor`
  pattern to idiomatic `asyncio.to_thread` (BigQuery, Pub/Sub, Firestore, Gemini).
- Tightened types in `routes/insights.py`: `_spawn_background` takes a
  `Coroutine`, analytics kwargs use a `TypedDict`, and the ranked-category list is
  computed once and threaded through instead of recomputed.
- Frontend benchmark constants (global average / Paris target) centralised in
  `utils/constants.ts`, removing four hard-coded copies across `App` and
  `ResultsDisplay`.
- Shared `ChartTooltip` component extracted, de-duplicating the bar- and
  line-chart tooltip markup.

### Fixed
- `carbonStore.saveEntry` no longer swallows errors silently — failures are now
  logged (history saving stays non-blocking by design).
- React list keys now use stable identifiers (`entry.id`,
  `category`+`priority`) instead of array indices in the insights, history chart,
  and history table lists.
- Removed dead code: three unused hook files (`useCarbon`/`useHistory`/
  `useInsights`) and the unused `breakdown` prop on `CategoryChart`.

### Added
- Direct unit tests for the Zustand store (`tests/carbonStore.test.ts`) covering
  success, error, non-Error-fallback, and early-return paths; the store is no
  longer excluded from coverage.
- Backend robustness tests (`tests/test_robustness.py`): rate-limit 429
  enforcement, route 500 error path, exact comparison-math correctness, and
  calculator fallback branches.
- Frontend edge-case tests: API network-rejection and non-JSON error bodies,
  `formatKg` rounding boundaries, and the `getDeviceId` format contract.
- Backend coverage gate raised to 90% (`fail_under`), matching the documented
  target; suites now run warning-clean.

## [1.1.0] - 2026-06-17

### Fixed
- Rule-engine fallback now personalises to the user's real diet, consumption, and
  flight habits. These were previously hard-coded (meat_medium / medium / no flights),
  so the deterministic fallback ignored user context. The lifestyle inputs are now
  echoed onto `CarbonResult` and threaded through to the rule engine.
- BigQuery analytics now log the real `diet_type` instead of always `"unknown"`
  (the value was read from the numeric `breakdown` dict, which has no such key).
- The Gemini path now guarantees exactly 3 insights or falls back to the rule
  engine, instead of silently returning a short, contract-violating response.
- Rate limiting now keys on the originating client IP via `X-Forwarded-For`
  (the previous peer-address key is the platform proxy behind Cloud Run).
- Firestore documents now serialise `ranked_categories` to plain dicts, matching
  the insights handling and avoiding a write failure on real Firestore.

### Changed
- All routes refactored to idiomatic FastAPI `@router.get/@router.post`
  decorators, removing the `get_type_hints` / `__annotations__` / manual
  `add_api_route` metaprogramming workaround (it existed only to compensate
  for `from __future__ import annotations`, which has been dropped from the
  route modules).
- `device_id` validation centralised into a single shared `DeviceId` type.
- `InsightItem.category` constrained to a closed set (was a free string).
- Background analytics tasks are now tracked to prevent garbage-collection
  cancellation of in-flight fire-and-forget coroutines.

### Added
- Regression test suite (`tests/test_personalization.py`) locking in the
  context-aware fallback, analytics, Gemini contract, rate-limit, and
  serialisation fixes.

## [1.0.0] - 2025-06-01

### Added
- Carbon footprint calculator with transport, home energy, diet, and consumption inputs
- Science-backed emission factors (UK DEFRA 2023, US EPA eGRID 2023, IPCC AR6)
- Google Gemini 1.5 Flash AI-powered personalised insight generation
- Deterministic rule-engine fallback when Gemini is unavailable
- Firestore history tracking per anonymous device_id
- BigQuery anonymised aggregate analytics logging
- Pub/Sub event streaming for downstream consumers
- React 18 + TypeScript frontend with Zustand state management
- WCAG 2.1 AA accessibility compliance (jest-axe verified)
- Rate limiting: 30/min calculate, 10/min insights, 20/min entries
- Security headers: CSP, HSTS, X-Frame-Options, Permissions-Policy
- Multi-stage Docker build with non-root user
- GitHub Actions CI with lint, typecheck, test, and coverage gates
- Cloud Run deployment via configurable GCP project ID
