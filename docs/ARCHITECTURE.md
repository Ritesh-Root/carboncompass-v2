# System Architecture Document
## Carbon Footprint Awareness Platform

---

## 1. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                │
│                                                         │
│  ┌──────────────┐     ┌──────────────────────────────┐  │
│  │  Cloud Run   │────►│  Vertex AI (Gemini 1.5 Flash)│  │
│  │  Container   │     └──────────────────────────────┘  │
│  │              │     ┌──────────────────────────────┐  │
│  │  FastAPI     │────►│  Firestore (Native mode)     │  │
│  │  + React SPA │     └──────────────────────────────┘  │
│  │              │     ┌──────────────────────────────┐  │
│  │              │────►│  BigQuery (analytics)        │  │
│  │              │     └──────────────────────────────┘  │
│  │              │     ┌──────────────────────────────┐  │
│  │              │────►│  Pub/Sub (events)            │  │
│  └──────────────┘     └──────────────────────────────┘  │
│         │             ┌──────────────────────────────┐  │
│         └────────────►│  Secret Manager (creds)      │  │
│                        └──────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Cloud Build ──► Artifact Registry ──► Cloud Run │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
           ▲
           │ HTTPS
           │
    ┌──────┴──────┐
    │  Browser    │
    │  React SPA  │
    └─────────────┘
```

---

## 2. Container Architecture

**Multi-stage Dockerfile:**

```
Stage 1 (node:20-alpine)
  └── npm ci → npm run build → /app/frontend/dist/

Stage 2 (python:3.11-slim)
  ├── pip install requirements.txt
  ├── COPY app/ → /app/app/
  ├── COPY dist/ → /app/static/
  ├── USER appuser (non-root)
  └── CMD uvicorn app.main:app --workers 2 --port 8080
```

The single container serves:
- `GET /api/*` → FastAPI routes
- `GET /assets/*` → StaticFiles (Vite build)
- `GET /*` → index.html (SPA fallback)

---

## 3. Request Flow: Carbon Calculation

```
Browser POST /api/calculate
    │
    ▼
FastAPI: SecurityHeadersMiddleware
    │
    ▼
FastAPI: CORSMiddleware
    │
    ▼
slowapi: Rate limit check (30/min/IP)
    │
    ▼
Pydantic: CarbonInput validation
    │
    ▼
calculator.calculate_footprint() — pure function, no I/O
    │
    ▼
Return CarbonResult (JSON)
```

---

## 4. Request Flow: Insights Generation

```
Browser POST /api/insights
    │
    ▼
FastAPI + slowapi (10/min/IP)
    │
    ▼
get_settings(): USE_GEMINI?
    │
    ├─ YES ──► vertexai.GenerativeModel.generate_content()
    │              ├─ SUCCESS → parse JSON → InsightItem[]
    │              └─ FAIL → GeminiUnavailableError
    │
    └─ NO (or FAIL) ──► get_rule_based_insights()
                              └─ Deterministic rules → InsightItem[]
    │
    ▼
asyncio.create_task():
    ├── bigquery_service.log_event_async()  ← fire-and-forget
    └── pubsub_service.publish_insight_request()  ← fire-and-forget
    │
    ▼
Return InsightsResponse { insights, source, total_potential_saving_kg }
```

---

## 5. Data Model

### Firestore: `carbon_entries/{docId}`
```json
{
  "device_id": "dev-lk3j2-abc123",
  "timestamp": "2024-01-15T12:00:00Z",
  "total_kg": 6800.0,
  "breakdown": {
    "transport": 3000.0,
    "home": 1300.0,
    "diet": 2500.0,
    "consumption": 1000.0
  },
  "ranked_categories": [...],
  "vs_global_average_pct": 170.0,
  "vs_paris_target_pct": 340.0,
  "insights": [...]
}
```

### BigQuery: `carbon_analytics.carbon_events`
```
timestamp       TIMESTAMP  — UTC event time
total_kg        FLOAT64    — total annual footprint
diet_type       STRING     — dietary pattern
insight_source  STRING     — "gemini" or "rules"
top_category    STRING     — highest-emission category
```
_Note: No `device_id` — privacy by design._

### Pub/Sub: `carbon-insights` topic
```json
{
  "footprint_total": 6800.0,
  "top_category": "transport",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

---

## 6. Frontend State Management

```
Zustand Store
├── inputs: Partial<CarbonInput>      — form values
├── result: CarbonResult | null       — latest calculation
├── insights: InsightsResponse | null — latest insights
├── history: HistoryEntry[]           — all saved entries
├── step: 'form' | 'results' | 'history'
├── isCalculating / isLoadingInsights / isLoadingHistory
└── error: string | null

Actions:
  calculate(inputs) ──► POST /api/calculate
  fetchInsights()   ──► POST /api/insights
  saveEntry()       ──► POST /api/entries
  fetchHistory()    ──► GET  /api/entries/{device_id}
```

---

## 7. Security Architecture

See [SECURITY_ARCHITECTURE.md](../SECURITY_ARCHITECTURE.md) for full details.

Key controls:
- **Authentication**: Application Default Credentials (ADC) — no API keys in code
- **Transport**: HTTPS-only via Cloud Run (TLS 1.2+)
- **Headers**: CSP, HSTS, X-Frame-Options, Permissions-Policy
- **Input validation**: Pydantic v2 (backend) + Zod (frontend)
- **Rate limiting**: slowapi per-IP
- **Firestore rules**: Create-only, field-validated
- **No PII**: device_id is cryptographically random, session-scoped
