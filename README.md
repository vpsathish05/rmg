# RMG — AI-Powered Resource Management

Resource Management System for JMan Group. Replaces manual email-based resource negotiation with AI-powered candidate recommendations.

## Quick Start

```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend && npm run dev
```

Open http://localhost:3000 and login.

## Architecture

```
Next.js (3000) → FastAPI (8000) → Azure PostgreSQL + OpenAI GPT-4o
```

- **Frontend**: Next.js App Router, shadcn/ui, TanStack Query
- **Backend**: FastAPI, SQLAlchemy 2.x, APScheduler
- **Database**: Azure PostgreSQL Flexible Server + pgvector
- **AI**: OpenAI gpt-4o (reasoning) + text-embedding-3-small (semantic matching)

## Key Features

| Feature | Description |
|---------|-------------|
| RMG Engine | Pipeline roles with AI-scored candidate recommendations |
| Semantic Matching | Employee skill embeddings matched against role requirements |
| LLM Re-Ranking | GPT-4o re-orders candidates by holistic fit |
| Smart Hire Signal | Actionable hiring profile when no internal match |
| Demand Forecast | 6-month outlook with weighted FTE |
| Availability | Real-time allocation view across all employees |
| Project Health | RAG status from weekly status reports |
| Email Integration | Microsoft Graph webhook for resource requests |

## AI Pipeline (per role)

1. COE Detection (SQL → GPT-4o fallback)
2. Skills Extraction (GPT-4o for missing data)
3. Semantic Skill Matching (embedding cosine similarity)
4. Formula Scoring (skill + competency + availability + productivity)
5. Rationale Generation (GPT-4o per candidate)
6. LLM Re-Ranking (GPT-4o holistic ordering)
7. KB Proof (pgvector past project search)
8. Hire Signal (GPT-4o when no match)

## Database

14 tables on Azure PostgreSQL with pgvector extension.

```
Host: rg-tenaliaiaz-prod-uksouth-02.postgres.database.azure.com
DB:   postgres
```

## ETL

```bash
cd backend && source .venv/bin/activate

python -m etl.load_all                  # Load source data from CSVs
python -m etl.build_kb                  # Build project embeddings (pgvector)
python -m etl.build_skill_embeddings    # Build employee skill embeddings
python -m etl.compute_recommendations   # Run full AI recommendation pipeline
```

## Environment Variables

Copy `backend/.env.example` → `backend/.env`:

```
DATABASE_URL=postgresql://adminuser:<pass>@<host>:5432/postgres?sslmode=require
OPENAI_API_KEY=sk-...
GRAPH_CLIENT_ID=...
GRAPH_CLIENT_SECRET=...
GRAPH_TENANT_ID=...
GRAPH_MAILBOX=...
```

## Project Structure

```
rmg/
├── frontend/          Next.js app (port 3000)
│   ├── app/           Pages and layouts
│   ├── components/    UI components
│   └── lib/           API hooks, auth, utilities
├── backend/           FastAPI app (port 8000)
│   ├── app/
│   │   ├── routers/   API endpoints
│   │   ├── services/  Business logic + AI
│   │   ├── models/    SQLAlchemy ORM
│   │   └── schemas/   Pydantic models
│   └── etl/           Data loading + embedding scripts
└── docs/              Source data (CSV, XLSX)
```
