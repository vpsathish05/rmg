# RMG — Architecture & Conventions

## Project Overview
AI-powered Resource Management System for JMan Group. Replaces manual email-based resource negotiation.

### Use Cases
- UC1: RMG Engine — 3-tab view (Pipeline → Extensions → Changes) with AI-powered recommendation per role
  - Pipeline: new demand from pipeline_requests, AI scores candidates per open role
  - Extensions: auto-detected resource gaps (alloc_end < project_end) + AI replacement recommendations
  - Changes: email PDF form → AI parse (PyPDF2 form fields + pdfplumber fallback + GPT-4o) → auto-route (NEW→Pipeline, EXTEND→Changes with AI recs, CHANGE→Changes). Accepts subjects "Resource Request" and "Extension Request". "Process Emails" button triggers manual fetch.
- UC2: Demand Forecasting — pipeline requests with 6-month outlook, weighted FTE, capacity gap, revenue at risk, hot deals
- UC3: Availability Dashboard — employee allocation status with billability tracking, charts (utilization donut, RAG, demand vs supply, COE distribution)
- UC4: Project Health — RAG from WSR data (latest non-NO_COLOR entry), overrunning & ramp-down detection
- UC5: Resource Map — network graph (projects connected by shared employees) + project/resource timeline (Gantt)

### Scoring Formula
```
With competency:    total = skill×0.40 + competency×0.25 + availability×0.25 + productivity×0.10
Without competency: total = skill×0.65 + availability×0.25 + productivity×0.10

skill_score = 0.5 × COE_skill_score + 0.5 × semantic_similarity (when embeddings available)
avail_score = 1.0 if available >= requested_alloc_pct, else available / requested_alloc_pct
```
Categories: Available (has capacity) → BestMatch (score ≥ 0.40, allocated) → Stretch (poor fit)

### AI Pipeline (per role recommendation)
1. **COE Detection**: SQL role-based → SQL global fallback → GPT-4o inference
2. **Skills Extraction**: LLM infers required skills when pipeline data has null/nan
3. **Semantic Skill Match**: Embed role query → pgvector ANN index (top-K nearest) vs employee skill embeddings
4. **Formula Scoring**: Weighted sum (skill + competency + availability + productivity)
5. **Rationale Generation**: GPT-4o 2-3 sentence explanation per top 10 candidates
6. **LLM Re-Ranking**: GPT-4o re-orders top 10 based on holistic fit
7. **KB Proof**: pgvector search for past project evidence
8. **Smart Hire Signal**: GPT-4o generates actionable hiring profile when no match

## Tech Stack
| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Next.js (App Router) | 16.2.9 |
| React | React | 19.2.4 |
| UI | shadcn/ui + Tailwind CSS 4 + Lucide icons | latest |
| Data fetching | TanStack Query | 5.101.1 |
| HTTP client | Axios | 1.18.1 |
| Backend | FastAPI + Uvicorn | ≥0.111.0 |
| Database | Azure PostgreSQL Flexible Server + pgvector | psycopg2-binary |
| ORM | SQLAlchemy 2.x | ≥2.0.0 |
| AI | OpenAI (gpt-4o + text-embedding-3-small 1536d) | ≥1.30.0 |
| Email | Azure Communication Services (azure-communication-email) | ≥1.0.0 |
| Scheduling | APScheduler (AsyncIO) | ≥3.10.4 |
| Auth | Custom JWT sessions (jose) — username/password | N/A |

## Folder Structure
```
rmg/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx              ← Root layout (Inter font, Providers)
│   │   ├── providers.tsx           ← TanStack QueryClientProvider
│   │   ├── icon.svg               ← Favicon (purple J)
│   │   ├── (auth)/login/           ← Login page (centered, no sidebar)
│   │   └── (app)/                  ← Authenticated route group
│   │       ├── layout.tsx          ← Sidebar + main layout
│   │       ├── page.tsx            ← Dashboard
│   │       ├── rmg-engine/         ← 3-tab RMG Engine (main screen)
│   │       ├── availability/       ← Employee availability
│   │       ├── forecast/           ← Pipeline forecasting
│   │       ├── projects/           ← Project health
│   │       ├── resource-map/       ← Network graph + project/resource timelines
│   │       └── recommend/          ← Manual recommendation form
│   ├── components/
│   │   ├── layout/sidebar.tsx      ← Navigation (Dashboard, Engine, Forecast)
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
│   │   ├── config.py             ← pydantic-settings (Azure PG + OpenAI + Graph)
│   │   ├── database.py           ← SQLAlchemy engine + session (Azure AD token support)
│   │   ├── models/               ← 11 ORM models
│   │   ├── routers/
│   │   │   ├── rmg_engine.py     ← Main endpoints (pipeline, extensions, recommend, KB, cache)
│   │   │   ├── recommend.py      ← Manual recommendation
│   │   │   ├── employees.py      ← Availability, allocations
│   │   │   ├── projects.py       ← Health, overrunning, ramp-down
│   │   │   ├── forecast.py       ← Pipeline + outlook
│   │   │   ├── dashboard.py      ← Summary aggregation
│   │   │   ├── webhooks.py       ← Graph email notifications
│   │   │   ├── resource_map.py   ← Network graph + timeline endpoints
│   │   │   ├── chat.py           ← GPT-4o chatbot with function calling
│   │   │   ├── allocations.py    ← Allocation CRUD
│   │   │   └── health.py         ← Health check
│   │   ├── schemas/              ← Pydantic request/response
│   │   └── services/
│   │       ├── scorer.py         ← Core scoring engine (formula + semantic blend)
│   │       ├── llm.py            ← GPT-4o: rationale, re-ranking, hire signals
│   │       ├── kb.py             ← pgvector KB build + search + semantic skill scoring (ANN)
│   │       ├── rec_cache.py      ← Nightly pre-compute (full AI pipeline)
│   │       ├── auto_reply.py     ← Auto-reply: EXTEND emails → AI recommend → send via ACS
│   │       ├── email_parser.py   ← GPT-4o email parsing
│   │       └── graph.py          ← Microsoft Graph client
│   ├── etl/
│   │   ├── schema.sql            ← 12 tables DDL
│   │   ├── migrate_add_rec_cache.py    ← role_recommendations table
│   │   ├── migrate_ai_tables.py        ← employee_skill_embeddings table
│   │   ├── load_all.py                 ← Master ETL
│   │   ├── loaders/                    ← 9 data loaders
│   │   ├── build_kb.py                 ← Project embeddings rebuild
│   │   ├── build_skill_embeddings.py   ← Employee skill profile embeddings
│   │   └── compute_recommendations.py  ← Standalone rec compute
│   └── requirements.txt
└── docs/                          ← Source data (CSV, XLSX)
```

## Data Flow

### Request Path
```
Browser → Next.js (port 3000) → Axios → FastAPI (port 8000) → SQLAlchemy → Azure PostgreSQL
                                                              → OpenAI API (embeddings + chat)
```

### RMG Engine (instant): GET /api/rmg/pipeline + GET /api/rmg/recommendations (pre-computed JSONB)
### Inline Recommend: POST /api/rmg/recommend-role → semantic scoring → scorer → LLM rationale → KB proofs
### Extensions Needs: GET /api/rmg/extensions/needs → alloc_end < project_end detection → grouped by project → inline recommend per leaving resource
### Nightly 2am IST: APScheduler → rec_cache.compute_all() → full AI pipeline → UPSERT role_recommendations
### Email Webhook: Graph POST → background: fetch message → GPT parse → INSERT email_requests
### Email Manual: POST /api/webhooks/email/process-latest → fetch latest emails → extract PDF → GPT parse → route (NEW→pipeline, EXTEND/CHANGE→email_requests)

## API Routes
| Prefix | Router | Purpose |
|--------|--------|---------|
| `/api/dashboard` | dashboard.py | Summary stats |
| `/api/employees` | employees.py | Availability, allocations |
| `/api/projects` | projects.py | Health, overrunning, ramp-down |
| `/api/allocations` | allocations.py | Allocation CRUD |
| `/api/recommend` | recommend.py | Manual recommendation |
| `/api/forecast` | forecast.py | Pipeline + outlook + insights (funnel, capacity gap, revenue, hot deals) |
| `/api/rmg/*` | rmg_engine.py | Pipeline, extensions, extensions/needs, recommend, KB, cache, auto-coe |
| `/api/resource-map` | resource_map.py | Network graph, project timeline, employee timeline, employee search |
| `/api/chat` | chat.py | GPT-4o chatbot with function calling (7 tools) |
| `/api/webhooks/email` | webhooks.py | Graph notifications + process-latest (manual trigger) |

## Database: 14 Tables (Azure PostgreSQL)
employees, projects, project_coes, allocations, timesheets, weekly_status,
employee_skills, employee_competencies, role_mapping, pipeline_requests,
email_requests, project_embeddings, role_recommendations, **employee_skill_embeddings**

Key patterns:
- `is_active_version = true` filter on most queries (soft-versioning)
- `(end_date IS NULL OR end_date >= CURRENT_DATE)` for active allocations
- `score > 0` filter for meaningful skill scores
- BAU exclusion: `LOWER(p.type_of_project) != 'bau activity'` on ALL allocation queries (BAU is tracking overhead, not real work)
- Project Health: uses latest WSR entry WHERE at least one status != 'NO_COLOR' (skips blank entries)
- COE grouping: `LOWER(TRIM(coe))` for case-insensitive dedup
- Dashboard KPIs and charts all have drill-down modals showing raw data + calculation explanation

## AI Integration Summary
| Service | Model | Purpose | When |
|---------|-------|---------|------|
| Semantic embeddings | text-embedding-3-small | Employee skill profiles + role query matching | ETL + per-role |
| COE detection | gpt-4o | Infer COE when SQL fails | Per-role (fallback only) |
| Skills extraction | gpt-4o | Infer required skills from role name | Per-role (null skills only) |
| Rationale | gpt-4o | 2-3 sentence candidate explanation | Top 10 per role |
| Re-ranking | gpt-4o | Holistic re-ordering of top 10 | Per role |
| Hire signal | gpt-4o | Actionable hiring profile | no_resource roles only |
| KB proof | text-embedding-3-small | Past project evidence via cosine search | Top 6 per role |
| Email/PDF parsing | gpt-4o | Structured extraction from emails + PDF attachments (pdfplumber) | Per email |
| Chatbot | gpt-4o (function calling) | Natural language queries → tool execution → formatted answers | Per user message |

## Email (ACS)
- Send via Azure Communication Services Email SDK (`azure-communication-email`)
- Connection string: `ACS_CONNECTION_STRING` env var
- Sender: `DoNotReply@e3445e90-bf10-44d1-8ea3-32eb935710d6.azurecomm.net`
- Used for: sending recommendation emails from RMG Engine pipeline + auto-reply for EXTEND requests
- **Auto-Reply (EXTEND)**: When an EXTEND email is processed, the system automatically runs AI recommendation (scorer + semantic ANN + rationale) and sends a reply to the sender with top candidates. Status changes to `REPLIED`.
- Graph API still used for: webhook subscriptions + message fetch + PDF attachment extraction (inbound email parsing)
- Email request routing: NEW → pipeline_requests, EXTEND → email_requests + auto-reply, CHANGE → email_requests (Changes tab)
- EXTEND requests show AI replacement recommendations in Changes tab
- PDF form: official JMan editable PDFs (Resourcing Form + Change Request Form), extracted via PyPDF2 form fields
- Accepted email subjects: "Resource Request", "Extension Request"
- Graph permissions required: Mail.Read, Mail.Send (Application, admin-consented)
- email_requests.status: PENDING → PARSED → REPLIED (for EXTEND) or stays PARSED (for CHANGE/NEW)

## Chatbot
- POST /api/chat — GPT-4o with function calling
- 7 tools: search_available, get_employee_info, get_dashboard_stats, get_capacity_gap, get_project_team, get_project_health, recommend_for_role
- Frontend: floating ChatPanel component in app layout (bottom-right)
- Supports markdown tables (react-markdown + remark-gfm)

## Conventions
- Backend: one router file per domain in `backend/app/routers/`
- Frontend: ALL API calls centralized in `lib/hooks.ts` — never call Axios from components
- UI: JMan brand — primary #19105B (Midnight Blue), secondary #FF6196 (Rose), 75% white / 20% primary / 5% secondary, Arial font
- Sidebar: 3 top-level routes — Dashboard, Engine, Forecast
- Scoring categories: Available / BestMatch (≥0.40) / Stretch
- Auth: custom JWT (jose), httpOnly cookie, 8h expiry
- Layered: Routers (thin) → Services (logic) → Database
- Batch SQL in scorer (5 queries then in-memory scoring — avoids complex joins)
- Parallel AI: asyncio.gather() for rationale + KB lookups
- Never commit .env files

## Critical Files
| File | Role |
|------|------|
| `backend/app/services/scorer.py` | Core scoring formula + semantic blend + relative avail scoring |
| `backend/app/services/rec_cache.py` | Nightly AI orchestrator (all 8 steps, uses ANN) |
| `backend/app/services/llm.py` | All GPT-4o calls: rationale, rerank, hire signal |
| `backend/app/services/kb.py` | pgvector build + search + semantic skill scoring (ANN + full) |
| `backend/app/services/auto_reply.py` | Auto-reply for EXTEND emails: recommend + build HTML + send ACS |
| `backend/app/routers/rmg_engine.py` | Largest router — main operational screen |
| `backend/etl/schema.sql` | Schema source of truth |
| `backend/etl/build_skill_embeddings.py` | Employee skill embedding ETL |
| `frontend/lib/hooks.ts` | All TS interfaces + query hooks (API contract) |
| `backend/app/main.py` | Lifespan, scheduler, all router mounts |

## Running Locally
```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev  # → localhost:3000
```

## Database Connection
```env
# Azure PostgreSQL (static auth)
DATABASE_URL=postgresql://adminuser:<password>@rg-tenaliaiaz-prod-uksouth-02.postgres.database.azure.com:5432/postgres?sslmode=require

# Azure Communication Services (email send)
ACS_CONNECTION_STRING=endpoint=https://acs-tenaliaiaz-prod-uksouth-01.uk.communication.azure.com/;accesskey=<key>
ACS_SENDER_EMAIL=DoNotReply@e3445e90-bf10-44d1-8ea3-32eb935710d6.azurecomm.net
```

## ETL Commands
```bash
cd backend && source .venv/bin/activate

# Load source data
python -m etl.load_all

# Build project KB embeddings
python -m etl.build_kb

# Build employee skill embeddings
python -m etl.build_skill_embeddings

# Compute all recommendations (full AI pipeline)
python -m etl.compute_recommendations
```
