# RMG — Architecture & Conventions

## Project Overview
AI-powered Resource Management System for JMan Group. Replaces manual email-based resource negotiation.

### Use Cases
- UC1: RMG Engine — 3-panel view (Pipeline → Extensions → Email Requests) with inline recommendation per role
- UC2: Demand Forecasting — pipeline requests with 6-month outlook, weighted FTE
- UC3: Availability Dashboard — employee allocation status with billability tracking
- UC4: Project Health — RAG from WSR data, overrunning & ramp-down detection

### Scoring Formula
```
With competency:    total = skill×0.40 + competency×0.25 + availability×0.25 + productivity×0.10
Without competency: total = skill×0.65 + availability×0.25 + productivity×0.10
```
Categories: Available (has capacity) → BestMatch (allocated but scored well) → Stretch (poor fit)

## Tech Stack
| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js (App Router) | 16.2.9 |
| React | React | 19.2.4 |
| UI | shadcn/ui + Tailwind CSS 4 + Lucide icons | latest |
| Data fetching | TanStack Query | 5.101.1 |
| HTTP client | Axios | 1.18.1 |
| Backend | FastAPI + Uvicorn | ≥0.111.0 |
| Database | Neon PostgreSQL 18 + pgvector | psycopg2-binary |
| ORM | SQLAlchemy 2.x | ≥2.0.0 |
| AI | OpenAI (gpt-4o + text-embedding-3-small 1536d) | ≥1.30.0 |
| Email | Microsoft Graph API (httpx) | ≥0.27.0 |
| Scheduling | APScheduler (AsyncIO) | ≥3.10.4 |
| Auth | Custom JWT sessions (jose) — username/password | N/A |

## Folder Structure
```
rmg/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              ← Root layout (Inter font, Providers)
│   │   ├── providers.tsx           ← TanStack QueryClientProvider
│   │   ├── (auth)/login/           ← Login page
│   │   └── (app)/                  ← Authenticated route group
│   │       ├── layout.tsx          ← Sidebar + main layout
│   │       ├── page.tsx            ← Dashboard
│   │       ├── rmg-engine/         ← 3-panel RMG Engine (main screen)
│   │       ├── availability/       ← Employee availability
│   │       ├── forecast/           ← Pipeline forecasting
│   │       ├── projects/           ← Project health
│   │       └── recommend/          ← Manual recommendation form
│   ├── components/
│   │   ├── layout/sidebar.tsx      ← Navigation (RMG Engine, Forecast, Dashboard)
│   │   └── ui/                     ← shadcn primitives
│   └── lib/
│       ├── api.ts                  ← Axios instance
│       ├── hooks.ts                ← ALL TanStack Query hooks & interfaces
│       ├── actions.ts              ← Server actions: login/logout
│       ├── session.ts              ← JWT session management
│       └── utils.ts                ← Utilities
├── backend/
│   ├── app/
│   │   ├── main.py                ← FastAPI app, CORS, lifespan (webhook + scheduler)
│   │   ├── config.py             ← pydantic-settings
│   │   ├── database.py           ← SQLAlchemy engine + session
│   │   ├── models/               ← 11 ORM models
│   │   ├── routers/
│   │   │   ├── rmg_engine.py     ← Main endpoints (pipeline, extensions, recommend, KB, cache)
│   │   │   ├── recommend.py      ← Manual recommendation
│   │   │   ├── employees.py      ← Availability, allocations
│   │   │   ├── projects.py       ← Health, overrunning, ramp-down
│   │   │   ├── forecast.py       ← Pipeline + outlook
│   │   │   ├── dashboard.py      ← Summary aggregation
│   │   │   ├── webhooks.py       ← Graph email notifications
│   │   │   ├── allocations.py    ← Allocation CRUD
│   │   │   └── health.py         ← Health check
│   │   ├── schemas/              ← Pydantic request/response
│   │   └── services/
│   │       ├── scorer.py         ← Core scoring engine
│   │       ├── llm.py            ← GPT-4o rationale (batch parallel)
│   │       ├── kb.py             ← pgvector KB build + search
│   │       ├── rec_cache.py      ← Nightly pre-compute
│   │       ├── email_parser.py   ← GPT-4o email parsing
│   │       └── graph.py          ← Microsoft Graph client
│   ├── etl/
│   │   ├── schema.sql            ← 12 tables DDL
│   │   ├── migrate_add_rec_cache.py ← 13th table migration
│   │   ├── load_all.py           ← Master ETL
│   │   ├── loaders/              ← 9 data loaders
│   │   ├── build_kb.py           ← Standalone KB rebuild
│   │   └── compute_recommendations.py ← Standalone rec compute
│   └── requirements.txt
└── docs/                          ← Source data (CSV, XLSX)
```

## Data Flow

### Request Path
```
Browser → Next.js (port 3000) → Axios → FastAPI (port 8000) → SQLAlchemy → Neon PostgreSQL
                                                              → OpenAI API (rationale + embeddings)
```

### RMG Engine (instant): GET /api/rmg/pipeline + GET /api/rmg/recommendations (pre-computed JSONB)
### Inline Recommend: POST /api/rmg/recommend-role → scorer → LLM rationale → KB proofs
### Nightly 2am IST: APScheduler → rec_cache.compute_all() → UPSERT role_recommendations
### Email Webhook: Graph POST → background: fetch message → GPT parse → INSERT email_requests

## API Routes
| Prefix | Router | Purpose |
|--------|--------|---------|
| `/api/dashboard` | dashboard.py | Summary stats |
| `/api/employees` | employees.py | Availability, allocations |
| `/api/projects` | projects.py | Health, overrunning, ramp-down |
| `/api/allocations` | allocations.py | Allocation CRUD |
| `/api/recommend` | recommend.py | Manual recommendation |
| `/api/forecast` | forecast.py | Pipeline + outlook |
| `/api/rmg/*` | rmg_engine.py | Pipeline, extensions, inline recommend, KB, cache |
| `/api/webhooks/email` | webhooks.py | Graph notifications |

## Database: 13 Tables
employees, projects, project_coes, allocations, timesheets, weekly_status,
employee_skills, employee_competencies, role_mapping, pipeline_requests,
email_requests, project_embeddings, role_recommendations

Key pattern: `is_active_version = true` filter on most queries (soft-versioning).

## Conventions
- Backend: one router file per domain in `backend/app/routers/`
- Frontend: ALL API calls centralized in `lib/hooks.ts` — never call Axios from components
- Brand colors defined as constants (C.MIDNIGHT=#19105B, C.TRYPAN=#3411A3, C.ROSE=#FF6196, etc.)
- Sidebar: 3 top-level routes — RMG Engine, Forecast, Dashboard
- Scoring categories: Available / BestMatch / Stretch
- Auth: custom JWT (jose), httpOnly cookie, 8h expiry, credentials from env vars
- Layered: Routers (thin) → Services (logic) → Database
- Batch SQL in scorer (5 queries then in-memory scoring — avoids complex joins)
- Parallel AI: asyncio.gather() for rationale + KB lookups
- Never commit .env files

## Critical Files
| File | Role |
|------|------|
| `backend/app/services/scorer.py` | Core scoring formula + categorization |
| `backend/app/services/rec_cache.py` | Nightly orchestrator (scorer + LLM + KB) |
| `backend/app/routers/rmg_engine.py` | Largest router — main operational screen |
| `backend/etl/schema.sql` | Schema source of truth (12 tables) |
| `frontend/lib/hooks.ts` | All TS interfaces + query hooks (API contract) |
| `backend/app/main.py` | Lifespan, scheduler, all router mounts |
| `backend/app/services/kb.py` | pgvector build + cosine search |
| `backend/app/services/email_parser.py` | GPT-4o structured parsing |

## Running Locally
```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev  # → localhost:3000
```
