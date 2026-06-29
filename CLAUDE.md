# RMG Engine - AI-Powered Resource Management System

## Project Overview
AI-driven resourcing system for JMan Group. Replaces manual email-based resource negotiation.
- UC1: RMG Engine - 3-tab view (Pipeline → Extensions → Changes) with AI-powered recommendations
- UC2: Demand Forecasting - 12-month ML forecast (revenue, clusters, resources, projects, COE gap) + pipeline insights
- UC3: Dashboard - KPIs + 6 charts with drill-down modals (raw data + calculation)
- UC4: Project Health - RAG from latest non-NO_COLOR WSR entry
- UC5: Lifecycle - project & resource timelines with right-panel Gantt
- UC6: AI Chatbot - GPT-4o function calling with 7 tools

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
- **Send Recommendation email**: multi-recipient support - `to_emails: list[str]`, EM pre-filled from pipeline `em_name`, all rows editable, add/remove recipients, backwards-compatible with legacy `to_email` single field
- Dashboard drill-downs: click any KPI or chart → modal with raw data + calculation explanation
- Project Health: uses latest WSR with meaningful status (skips NO_COLOR entries)
- Nightly pre-compute at 2 AM IST, ~$3.60/night for 240 roles
- BAU exclusion: type_of_project='BAU Activity' (CLIENT_127) ignored from all allocation calculations - it's a tracking bucket, not real work. 278 BAU-only employees show as bench (available).

## Scoring Notes (known limitations - improvement backlog)
- Competency data only exists for 3 roles: Solutions Enabler, Solutions Consultant, Senior Software Engineer. All other roles use `skill×0.65 + avail×0.25 + prod×0.10` formula.
- `SKILL_NEUTRAL = 0.15` applied when employee has skills in other COEs but not the requested one.
- Inline recommend uses full-scan semantic search; nightly cache uses ANN - results can differ slightly.
- Availability check uses today's allocations, not the role's `likely_start_date` - future-rolling candidates may show as BestMatch when they'll actually be free by start date.
- KB proof badges have no minimum similarity threshold - low-relevance matches still appear.

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

## Session Decisions & Improvements Log

### Session - July 2026
**Send Recommendation - multi-recipient upgrade**
- `POST /api/rmg/send-recommendation` now accepts `to_emails: list[str]` (was single `to_email: str`)
- Legacy `to_email: str | None` field kept for backwards compatibility - merged at validation time
- Frontend `SendRecommendationBtn` pre-fills first row from `project.em_name` (EM badge shown)
- Every email row is fully editable; rows can be added (`+ Add recipient`) or removed (`X`)
- `Enter` key in any row adds new row; send button shows live count `Send to N`
- Frontend error handler parses both custom `{message}` and Pydantic `{detail}` 422 formats

**Scoring logic - identified improvement backlog (not yet implemented)**
- Inline `/api/rmg/recommend-role` still uses full-scan `compute_semantic_skill_scores` - should switch to `compute_semantic_skill_scores_ann(top_k=100)` (3-line fix)
- Bench employees penalised on `prod_score` (0 hours logged = 0 score) - should use neutral 0.5 for available employees
- KB proof `search_employee_proofs` returns results regardless of similarity - add `>= 0.35` threshold
- Competency covers only 3 roles (Solutions Enabler, Solutions Consultant, Senior Software Engineer) - all others use the no-comp formula
- Availability scoring uses `CURRENT_DATE`, not `likely_start_date` - future-rolling employees may be misclassified

**Forecast page - documented all ML logic**
- Revenue: Holt damped (60%) + headcount regression (40%) ensemble, P10/P50/P90 with 8%/month widening
- Cluster: pipeline-derived weights + exponential decay blending (`e^-0.3×distance`)
- Resource FTE: Holt per role + 50% pipeline overlay; hiring gap = peak demand − headcount × 80%
- Project volume: Holt-Winters additive seasonal (period=12) on 90 months
- COE Gap: arithmetic supply/demand projection - no ML model
- MAPE 4.4% on revenue model only; other models do not compute MAPE


## Team Super Nova
Sathish · Karthi · Lejoy · Rohit
