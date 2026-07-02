# RMG Engine — AI-Powered Resource Management System

## Project Overview
AI-driven resourcing system for JMan Group. Replaces manual email-based resource negotiation.
- UC1: RMG Engine — 3-tab view (Pipeline → Extensions → Changes) with AI-powered recommendations
- UC2: Demand Forecasting — 12-month ML forecast (revenue, clusters, resources, projects, COE gap) + pipeline insights
- UC3: Dashboard — KPIs + 6 charts with drill-down modals (raw data + calculation)
- UC4: Project Health — RAG from latest non-NO_COLOR WSR entry
- UC5: Lifecycle — project & resource timelines with right-panel Gantt
- UC6: AI Chatbot — GPT-4o function calling with 7 tools

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (App Router) + React 19 + Tailwind CSS 4 + Recharts |
| Backend | FastAPI + Python + APScheduler |
| Database | Azure PostgreSQL + pgvector (1536-d) |
| AI | GPT-4o + text-embedding-3-small |
| ML | statsmodels (Holt-Winters) + scikit-learn (ensemble) |
| Email Out | Azure Communication Services |
| Email In | Microsoft Graph + PyPDF2 (form fields) + pdfplumber |
| Auth | Custom JWT (jose), httpOnly cookie |

## Key Features
- 8-step AI scoring pipeline per role (COE detect → semantic match → formula → rationale → re-rank → KB proof → hire signal)
- **ML Forecasting Service** (5 models, 7 API endpoints, 4.4% MAPE):
  - Revenue: Holt + Headcount regression ensemble → $59.4M/year forecast, P10/P50/P90
  - Clusters: Pipeline-derived weights → 5-cluster revenue decomposition
  - Resources: FTE by role (Holt per role + pipeline overlay) → hiring gap
  - Projects: Holt-Winters seasonal (90 months) → 430 projects/year with seasonality
  - COE Gap: Dynamic supply vs demand → hiring recommendations
- Relative availability scoring: avail_score = 1.0 if capacity meets requested allocation, proportional otherwise
- pgvector ANN index for semantic skill matching (top-K nearest instead of full scan)
- Email PDF form parsing: Resourcing Form + Change Request Form → auto-route (NEW→Pipeline, EXTEND→Changes with AI recs, CHANGE→Changes)
- **Auto-reply for EXTEND emails**: when processed, system auto-runs AI recommendation and sends reply to sender via ACS with top candidates
- Dashboard drill-downs: click any KPI or chart → modal with raw data + calculation explanation
- Project Health: uses latest WSR with meaningful status (skips NO_COLOR entries)
- Nightly pre-compute at 2 AM IST, ~$3.60/night for 240 roles
- BAU exclusion: type_of_project='BAU Activity' (CLIENT_127) ignored from all allocation calculations — it's a tracking bucket, not real work. 278 BAU-only employees show as bench (available).

## ML Forecasting
```bash
cd backend && source .venv/bin/activate

# Train all models (5.3s)
PYTHONPATH=. python3 -m ml.train

# Generate predictions (table or JSON)
PYTHONPATH=. python3 -m ml.predict --horizon 12

# Backtest evaluation (4.4% MAPE)
PYTHONPATH=. python3 -m ml.evaluate
```

API: `/api/forecast/ml/*` (revenue, revenue/clusters, projects, resources, coe-gap, summary, actuals)

## Brand Guidelines
- Primary: #19105B (Midnight Blue), Secondary: #FF6196 (Rose)
- 75% white, 20% primary, 5% secondary
- Font: Arial, body 13px base

## Running Locally
```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm run dev
```

## Team Super Nova
Sathish · Karthi · Lejoy · Rohit
