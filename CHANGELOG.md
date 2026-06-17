# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

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
