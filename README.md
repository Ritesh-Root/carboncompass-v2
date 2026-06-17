# CarbonCompass

![Python](https://img.shields.io/badge/python-3.11-blue)
![React](https://img.shields.io/badge/react-18.3-61dafb)
![TypeScript](https://img.shields.io/badge/typescript-strict-3178c6)
![Accessibility](https://img.shields.io/badge/a11y-WCAG%202.1%20AA-success)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

**A personal carbon footprint companion that turns "I want to be greener" into a ranked, quantified plan.**

You answer a few questions about how you travel, heat your home, eat, and shop.
CarbonCompass estimates your annual emissions, shows where you actually stand
against global and climate-target benchmarks, and hands you three concrete actions
ordered by how much carbon they remove — not generic advice.

## 🚀 Live demo

**[https://carboncompass-743502904048.us-central1.run.app](https://carboncompass-743502904048.us-central1.run.app)**

Deployed on **Google Cloud Run**. The live instance runs with the cloud
integrations disabled, so insights are served by the deterministic rule engine
(the AI path is identical — see §2).

---

## 1. Chosen vertical

**Personal sustainability — the individual carbon footprint assistant.**

Most footprint calculators stop at a number. A number alone doesn't change behaviour:
people are left asking *"is that good or bad?"* and *"what do I do about it?"*.

CarbonCompass is built around a single persona — **a motivated non-expert** who wants
to act but doesn't know where their emissions come from. The product is designed around
the decisions *that person* needs to make, not around the data we happen to collect.
Everything in the app maps to one of three jobs:

| Job | What the user gets |
| --- | --- |
| **Understand** | A defensible annual CO₂e estimate built from peer-reviewed emission factors, broken down by category. |
| **Track** | Each result can be saved against an anonymous device ID and plotted over time, so progress is visible. |
| **Reduce** | Three prioritised actions targeting the user's *largest* emission sources, each with an estimated yearly saving. |

---

## 2. Approach & logic

The core idea is that the assistant should be **context-aware**: the advice it gives
must depend on the specific shape of the user's footprint, not be a fixed checklist.

### The decision flow

```
 User inputs (transport, home energy, diet, consumption)
        │
        ▼
 [1] Carbon engine  ──►  per-category kg CO₂e
        │
        ▼
 [2] Rank categories by absolute impact (largest first)
        │
        ▼
 [3] Benchmark the total against:
        • Global average  ≈ 4,000 kg/yr
        • Paris 1.5°C target ≈ 2,000 kg/yr
        │
        ▼
 [4] Generate 3 reduction actions for the TOP categories
        ├── Primary:  Gemini 1.5 Flash (personalised, quantified)
        └── Fallback: deterministic rule engine (always available)
        │
        ▼
 [5] (Optional) persist snapshot + log anonymised analytics
```

### Why it's built this way

- **Impact-first ranking.** Suggesting "switch off standby lights" to someone whose
  footprint is 70% flights is noise. The engine sorts categories by absolute kilograms
  and only generates advice for the categories that actually move the needle.
- **AI with a safety net.** The personalised insights come from Google Gemini, but the
  app never *depends* on it. If Gemini is disabled, rate-limited, times out, or returns
  malformed JSON, a deterministic rule engine produces the same shape of response. The
  UI shows which engine answered. This keeps the assistant useful and predictable.
- **Pure calculation core.** The emission math is a side-effect-free module with no
  network or framework dependencies, which makes it trivial to test exhaustively and
  reason about.
- **Anonymous by design.** Tracking works off a random, session-scoped device ID — no
  account, no email, no name.

---

## 3. How the solution works

### Backend (FastAPI)

- `POST /api/calculate` — validates inputs (Pydantic v2), runs the pure carbon engine,
  returns the total, a per-category breakdown, ranked categories, and benchmark comparisons.
- `POST /api/insights` — takes a calculation result and returns three ranked actions.
  Tries Gemini first, falls back to the rule engine, and tags the response `source: gemini | rules`.
- `POST /api/entries` / `GET /api/entries/{device_id}` — save and read footprint history.
- `GET /api/health` — reports which integrations are enabled.

Cross-cutting concerns: OWASP security headers on every response, per-IP rate limiting,
CORS locked to the dev origin, and feature flags so the whole stack runs locally with
**zero cloud credentials**.

### Frontend (React + TypeScript)

A small single-page app with three views — **Calculate → Results → History** — backed by
a Zustand store and a typed fetch client. Inputs are validated client-side with Zod
(mirroring the backend models) before anything is sent. Results render a category
breakdown chart and benchmark bars; insights render as prioritised cards. The UI is
intentionally minimal and accessibility-first (see §6).

### Optional Google Cloud integrations

Each is behind a `USE_*` feature flag and is **off-by-default for local runs**:
Vertex AI (Gemini), Firestore (history), BigQuery (anonymised analytics), and Pub/Sub
(event streaming). When the flags are off, the app uses the rule-based fallback and
in-memory behaviour, so it is fully functional offline.

---

## 4. Quick start — local development (no GCP required)

> Requires Python 3.11 and Node 18+.

```bash
# 1. Clone your repository
git clone https://github.com/<your-username>/carboncompass.git
cd carboncompass

# 2. Backend — feature flags off, no cloud credentials needed
cd backend
python3.11 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
USE_GEMINI=false USE_FIRESTORE=false USE_BIGQUERY=false USE_PUBSUB=false \
  PROJECT_ID=local uvicorn app.main:app --reload --port 8000

# 3. Frontend — in a second terminal
cd frontend
npm install
npm run dev                          # http://localhost:5173 (proxies /api → :8000)
```

Open <http://localhost:5173>. The API docs are at <http://localhost:8000/api/docs>.

---

## 5. Tests

```bash
# Backend — pytest with coverage (gate: 90%)
cd backend
pytest --cov=app --cov-report=term -v

# Frontend — Vitest + jest-axe with coverage
cd frontend
npm test
```

The backend test suite runs with all `USE_*` flags off, so it exercises the rule-based
fallback path without touching any cloud service. The frontend suite includes unit tests,
interaction tests, and automated accessibility checks (`jest-axe`) on every component.

---

## 6. Accessibility

Accessibility is treated as a requirement, not a polish step. The frontend targets
**WCAG 2.1 AA** and every component is asserted against `axe-core` in CI:

- Skip-to-content link and visible keyboard focus rings throughout
- Every input has an associated `<label>`; radio groups use `<fieldset>` + `<legend>`
- Charts expose a screen-reader data table alternative (`role="img"` + `<table>`)
- Live regions (`aria-live`) announce new results and insights
- `prefers-reduced-motion` is respected

---

## 7. Security & privacy

- **No secrets in code.** Cloud access uses Application Default Credentials; nothing is hardcoded.
- **No PII.** Only a random, session-scoped `device_id` is stored — never names or emails.
- **Analytics are anonymised.** Aggregate logging never includes the device ID.
- **Input validation** at both boundaries (Zod on the client, Pydantic on the server).
- **Security headers** (CSP, HSTS, X-Frame-Options, Permissions-Policy) on every response.
- **Rate limiting** per IP on every endpoint.

---

## 8. Emission factor sources

| Factor | Source |
| --- | --- |
| Transport (car, bus, train) | UK DEFRA 2023 |
| Aviation (flights) | ICAO Carbon Calculator 2023 |
| Electricity | US EPA eGRID 2023 |
| Natural gas | UK DEFRA 2023 |
| Diet | Our World in Data 2023 (Poore & Nemecek 2018) |
| Consumption | IPCC AR6 WG3 Ch.5 |
| Global average (~4,000 kg) | Our World in Data 2023 |
| Paris target (~2,000 kg) | IPCC SR1.5 2018 |

---

## 9. Assumptions

These are the simplifying assumptions behind the estimates — stated openly because a
footprint number is only as honest as its assumptions:

1. **Annual basis.** All inputs and outputs are annualised (km/year, kWh/year, flights/year).
2. **Home energy is shared.** Household electricity and gas are split equally across the
   number of people in the home.
3. **Average grid/factors.** Electricity uses an average grid intensity rather than a
   live regional mix; real emissions vary by location and time of day.
4. **Diet is categorical.** Diet is modelled as one of four patterns rather than itemised
   food logging — accurate enough to rank, not a nutrition tracker.
5. **Consumption is a tier.** Shopping/goods are modelled as low/medium/high spend tiers.
6. **Benchmarks are global.** The 4,000 kg average and 2,000 kg Paris target are global
   reference points, not country-specific targets.
7. **Estimates, not audits.** Output is an educational estimate to guide action, not a
   certified carbon accounting figure.

---

## 10. Project structure

```
carboncompass/
├── backend/            FastAPI application
│   ├── app/
│   │   ├── carbon/     Pure emission calculation engine + rule-based insights
│   │   ├── core/       Config, security headers, rate limiting
│   │   ├── models/     Pydantic v2 request/response models
│   │   ├── routes/     calculate · insights · entries · health
│   │   └── services/   Gemini · Firestore · BigQuery · Pub/Sub (flag-gated)
│   └── tests/          pytest suite (runs fully offline)
├── frontend/           React 18 + TypeScript SPA
│   ├── src/
│   │   ├── components/ Calculator · Insights · History · shared
│   │   ├── store/      Zustand state
│   │   ├── api/        Typed fetch client
│   │   └── utils/      Formatters + Zod validators
│   └── tests/          Vitest + jest-axe suite
├── docs/               PRD, architecture notes
└── Dockerfile          Multi-stage build
```

---

## 11. Deployment (optional)

The app ships as a single container (multi-stage `Dockerfile`) and can run on any
container host. For Google Cloud Run, set your **own** project ID and enable the
integrations you want via env vars:

```bash
gcloud config set project <YOUR_GCP_PROJECT>
gcloud builds submit --tag gcr.io/<YOUR_GCP_PROJECT>/carboncompass .
gcloud run deploy carboncompass \
  --image gcr.io/<YOUR_GCP_PROJECT>/carboncompass \
  --region <YOUR_REGION> \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars PROJECT_ID=<YOUR_GCP_PROJECT>,REGION=<YOUR_REGION>,ENVIRONMENT=production
```

> Replace every `<...>` placeholder with your own values before deploying.

---

## License

MIT — see [`SECURITY.md`](./SECURITY.md) for the security policy.
