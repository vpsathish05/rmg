# RMG — Resource Management System

## Project Overview
AI-driven resourcing system for JMan Group. Replaces manual email-based resource negotiation.
- UC1: Resource Recommendation Engine (email-triggered, 5-step scored pipeline)
- UC2: Demand Forecasting (pipeline view)
- UC3: Availability Dashboard
- UC4: Project Health / WSR tracking

Source documents: `/docs/` (employee CSV, project CSV, allocations, timesheets, WSR, skills XLSX, competencies XLSX, pipeline XLSX)

## Tech Stack
| Layer | Choice |
|-------|--------|
| Frontend | Next.js 15 (App Router) + shadcn/ui + Tailwind CSS + TanStack Query |
| Backend | FastAPI (Python 3.13) |
| Database | Neon PostgreSQL 18 (serverless) + pgvector for RAG |
| ORM | SQLAlchemy 2.x |
| Auth | NextAuth.js — username/password, single role (RMG team) |
| AI | OpenAI API — gpt-4o (chat), text-embedding-3-small 1536d (RAG) |
| Email | Microsoft Graph API — monitors sathishkumar@jmangroup.com |

## Folder Structure
```
rmg/
├── frontend/               ← Next.js 15 (App Router)
│   ├── app/
│   ├── components/ui/      ← shadcn components
│   └── lib/                ← api.ts (axios client), utils.ts
├── backend/
│   ├── app/
│   │   ├── main.py         ← FastAPI app + CORS
│   │   ├── config.py       ← pydantic-settings (reads .env)
│   │   ├── database.py     ← SQLAlchemy engine + SessionLocal
│   │   ├── models/         ← 12 SQLAlchemy ORM models
│   │   ├── routers/        ← employees, projects, allocations, recommend, forecast, health
│   │   └── services/       ← scorer.py, llm.py (Phase 2+)
│   ├── etl/
│   │   ├── schema.sql      ← Run once to create all 12 tables
│   │   ├── load_all.py     ← Master ETL runner (python -m etl.load_all)
│   │   └── loaders/        ← 9 loader modules (one per source file)
│   ├── requirements.txt
│   ├── .env                ← NEVER commit (gitignored)
│   └── .env.example
└── docs/                   ← Source data files (CSV / XLSX)
```

## Database — 12 Tables on Neon
employees, projects, project_coes, allocations, timesheets, weekly_status,
employee_skills, employee_competencies, role_mapping, pipeline_requests,
email_requests, project_embeddings

## Loaded Row Counts (Phase 0 baseline)
| Table | Rows |
|-------|------|
| employees | 1,042 |
| projects | 2,040 |
| project_coes | 1,223 |
| allocations | 29,690 |
| timesheets | 126,336 |
| weekly_status | 71,205 |
| employee_skills | 82,211 |
| employee_competencies | 700 |
| role_mapping | 27 |
| pipeline_requests | 293 |

## Environment Variables
- Backend: copy `backend/.env.example` → `backend/.env`, fill in real values
- Frontend: copy `frontend/.env.example` → `frontend/.env.local`
- **Never commit `.env` files — they are gitignored**

Key var: `DATABASE_URL` — Neon PostgreSQL connection string

## Team
> Each developer must set their git identity before working:
```bash
git config user.name "Your Name"
git config user.email "your@email.com"
```

| Developer | Email | Owns |
|-----------|-------|------|
| Sathish Kumar | sathishkumar@jmangroup.com | Architect, project lead |
| (add team members here) | | |

## Conventions
- Backend routes live in `backend/app/routers/`, one file per domain (e.g. `resources.py`, `projects.py`)
- Frontend pages live in `frontend/app/`, using Next.js App Router conventions
- Shared types between frontend and backend should be documented in `docs/data-model.md`
- All API endpoints prefixed with `/api/v1/`

## Running Locally
```bash
# Backend (first time)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in DATABASE_URL and OPENAI_API_KEY

# Run schema (first time only)
python3 -c "import os,psycopg2; from dotenv import load_dotenv; load_dotenv('.env'); conn=psycopg2.connect(os.environ['DATABASE_URL']); conn.cursor().execute(open('etl/schema.sql').read()); conn.commit()"

# Run ETL (first time only)
PYTHONPATH=. python3 -m etl.load_all

# Start API
source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
cp .env.local.example .env.local
npm install
npm run dev  # → http://localhost:3000
```

## Scoring Formula (Phase 2)
```
Total = skill×0.40 + competency×0.25 + availability×0.25 + productivity×0.10
```
Fallback (no competency data): `skill×0.65 + availability×0.25 + productivity×0.10`

## Open Questions (non-blocking)
- Q2: allocation % range values (e.g. "25-50%") — how to interpret
- Q3: Trainee SEs — include or exclude from recommendations
- Q4: Does date_of_resignation = last working day or resignation date?
- Q5: Cross-COE recommendations allowed?
