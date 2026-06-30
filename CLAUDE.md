# RMG Engine — AI-Powered Resource Management System

## Project Overview
AI-driven resourcing system for JMan Group. Replaces manual email-based resource negotiation.
- UC1: RMG Engine — 3-tab view (Pipeline → Extensions → Changes) with AI-powered recommendations
- UC2: Demand Forecasting — capacity gap, revenue at risk, hot deals, 6-month outlook
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
| Email Out | Azure Communication Services |
| Email In | Microsoft Graph + PyPDF2 (form fields) + pdfplumber |
| Auth | Custom JWT (jose), httpOnly cookie |

## Key Features
- 8-step AI scoring pipeline per role (COE detect → semantic match → formula → rationale → re-rank → KB proof → hire signal)
- Email PDF form parsing: Resourcing Form + Change Request Form → auto-route (NEW→Pipeline, EXTEND→Changes with AI recs, CHANGE→Changes)
- Dashboard drill-downs: click any KPI or chart → modal with raw data + calculation explanation
- Project Health: uses latest WSR with meaningful status (skips NO_COLOR entries)
- Nightly pre-compute at 2 AM IST, ~$3.60/night for 240 roles
- BAU exclusion: type_of_project='BAU Activity' (CLIENT_127) ignored from all allocation calculations — it's a tracking bucket, not real work. 278 BAU-only employees show as bench (available).

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
