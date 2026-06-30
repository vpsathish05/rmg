"""RMG Chatbot — GPT-4o with function calling over existing services."""
import json
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from openai import AsyncOpenAI
from app.config import settings
from app.database import get_db

router = APIRouter()

SYSTEM = """You are the RMG (Resource Management Group) AI assistant at JMan Group.
You help users find resources, check availability, view project health, and manage staffing.
Answer concisely. Use tables when listing multiple items. Be specific with employee IDs and scores.
When recommending resources, explain why they're a good fit."""

TOOLS = [
    {"type": "function", "function": {"name": "search_available", "description": "Find available employees, optionally filtered by role or skill", "parameters": {"type": "object", "properties": {"role": {"type": "string", "description": "Canonical role filter e.g. 'Senior Software Engineer'"}, "skill": {"type": "string", "description": "Skill or COE to match e.g. 'Data Engineering'"}}, "required": []}}},
    {"type": "function", "function": {"name": "get_employee_info", "description": "Get an employee's current allocation and details", "parameters": {"type": "object", "properties": {"employee_id": {"type": "string"}}, "required": ["employee_id"]}}},
    {"type": "function", "function": {"name": "get_dashboard_stats", "description": "Get summary stats: active employees, bench, pipeline, projects", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_capacity_gap", "description": "Get demand vs bench capacity gap by role for next 3 months", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "get_project_team", "description": "Get team members allocated to a project", "parameters": {"type": "object", "properties": {"project_id": {"type": "string", "description": "Project ID e.g. CLIENT_9_261"}}, "required": ["project_id"]}}},
    {"type": "function", "function": {"name": "get_project_health", "description": "Get projects with RED or AMBER health status", "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {"name": "recommend_for_role", "description": "AI-score candidates for a specific role and COE", "parameters": {"type": "object", "properties": {"role": {"type": "string", "description": "Role name"}, "coe": {"type": "string", "description": "Technology/COE"}, "skills": {"type": "string", "description": "Required skills comma-separated"}}, "required": ["role"]}}},
]


def _exec_tool(name: str, args: dict, db: Session) -> str:
    if name == "search_available":
        return _search_available(db, args.get("role"), args.get("skill"))
    elif name == "get_employee_info":
        return _get_employee_info(db, args["employee_id"])
    elif name == "get_dashboard_stats":
        return _get_dashboard_stats(db)
    elif name == "get_capacity_gap":
        return _get_capacity_gap(db)
    elif name == "get_project_team":
        return _get_project_team(db, args["project_id"])
    elif name == "get_project_health":
        return _get_project_health(db)
    elif name == "recommend_for_role":
        return _recommend_for_role(db, args["role"], args.get("coe"), args.get("skills"))
    return json.dumps({"error": "Unknown tool"})


def _search_available(db: Session, role: str | None, skill: str | None) -> str:
    q = """
        SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
               COALESCE(SUM(a.allocation_pct), 0) AS allocated
        FROM employees e
        LEFT JOIN allocations a ON a.employee_id = e.employee_id
          AND a.is_active = true AND a.is_active_version = true
          AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
        LEFT JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
          AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        WHERE e.account_status = true AND e.is_active_version = true
          AND e.date_of_resignation IS NULL
    """
    params = {}
    if role:
        q += " AND e.canonical_role ILIKE :role"
        params["role"] = f"%{role}%"
    q += " GROUP BY e.employee_id, e.job_name, e.canonical_role, e.location HAVING COALESCE(SUM(a.allocation_pct), 0) < 100 ORDER BY allocated ASC LIMIT 10"
    rows = db.execute(text(q), params).fetchall()
    results = [{"id": r.employee_id, "name": r.job_name, "role": r.canonical_role, "location": r.location, "allocated": f"{r.allocated}%", "available": f"{100 - float(r.allocated)}%"} for r in rows]
    return json.dumps(results)


def _get_employee_info(db: Session, eid: str) -> str:
    emp = db.execute(text("SELECT employee_id, job_name, canonical_role, location, department_name FROM employees WHERE employee_id = :id AND is_active_version = true"), {"id": eid}).fetchone()
    if not emp:
        return json.dumps({"error": "Employee not found"})
    allocs = db.execute(text("""
        SELECT project_id, allocation_pct, start_date, end_date, resourcing_status
        FROM allocations WHERE employee_id = :id AND is_active = true AND is_active_version = true
        ORDER BY start_date
    """), {"id": eid}).fetchall()
    return json.dumps({"employee": {"id": emp.employee_id, "name": emp.job_name, "role": emp.canonical_role, "location": emp.location, "department": emp.department_name}, "allocations": [{"project": a.project_id, "pct": f"{a.allocation_pct}%", "start": str(a.start_date), "end": str(a.end_date), "status": a.resourcing_status} for a in allocs]})


def _get_dashboard_stats(db: Session) -> str:
    active = db.execute(text("SELECT COUNT(*) FROM employees WHERE account_status = true AND is_active_version = true AND date_of_resignation IS NULL")).scalar()
    bench = db.execute(text("""
        SELECT COUNT(*) FROM employees e WHERE e.account_status = true AND e.is_active_version = true AND e.date_of_resignation IS NULL
          AND COALESCE((
              SELECT SUM(a.allocation_pct) FROM allocations a
              JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
              WHERE a.employee_id = e.employee_id AND a.is_active = true AND a.is_active_version = true
                AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
          ), 0) = 0
    """)).scalar()
    pipeline = db.execute(text("SELECT COUNT(*) FROM pipeline_requests WHERE LOWER(status) = 'not resourced'")).scalar()
    projects = db.execute(text("SELECT COUNT(*) FROM projects WHERE UPPER(project_status) = 'ACTIVE' AND is_active_version = true")).scalar()
    return json.dumps({"active_employees": active, "on_bench": bench, "not_resourced_roles": pipeline, "active_projects": projects})


def _get_capacity_gap(db: Session) -> str:
    rows = db.execute(text("""
        SELECT UNNEST(canonical_roles) AS role, ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0)::numeric, 1) AS demand
        FROM pipeline_requests WHERE LOWER(status) = 'not resourced'
          AND likely_start_date <= CURRENT_DATE + INTERVAL '3 months'
        GROUP BY role ORDER BY demand DESC LIMIT 6
    """)).fetchall()
    bench = db.execute(text("""
        SELECT e.canonical_role, COUNT(*) AS bench FROM employees e
        WHERE e.account_status = true AND e.is_active_version = true AND e.date_of_resignation IS NULL AND e.canonical_role IS NOT NULL
          AND COALESCE((
              SELECT SUM(a.allocation_pct) FROM allocations a
              JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
              WHERE a.employee_id = e.employee_id AND a.is_active = true AND a.is_active_version = true
                AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
          ), 0) = 0
        GROUP BY e.canonical_role
    """)).fetchall()
    bench_map = {r.canonical_role: r.bench for r in bench}
    return json.dumps([{"role": r.role, "demand_fte": float(r.demand), "bench": bench_map.get(r.role, 0), "gap": round(float(r.demand) - bench_map.get(r.role, 0), 1)} for r in rows])


def _get_project_team(db: Session, pid: str) -> str:
    rows = db.execute(text("""
        SELECT a.employee_id, e.job_name, e.canonical_role, a.allocation_pct, a.resourcing_status
        FROM allocations a JOIN employees e ON e.employee_id = a.employee_id
        WHERE a.project_id = :pid AND a.is_active = true AND a.is_active_version = true
        ORDER BY e.canonical_role
    """), {"pid": pid}).fetchall()
    return json.dumps([{"id": r.employee_id, "name": r.job_name, "role": r.canonical_role, "alloc": f"{r.allocation_pct}%", "status": r.resourcing_status} for r in rows])


def _get_project_health(db: Session) -> str:
    rows = db.execute(text("""
        SELECT p.project_id, p.client_id, ws.scope_status, ws.schedule_status
        FROM projects p
        LEFT JOIN LATERAL (SELECT scope_status, schedule_status FROM weekly_status WHERE project_id = p.project_id ORDER BY week_end DESC LIMIT 1) ws ON true
        WHERE p.is_active_version = true AND UPPER(p.project_status) = 'ACTIVE'
          AND (ws.scope_status = 'RED' OR ws.schedule_status = 'RED' OR ws.scope_status = 'AMBER' OR ws.schedule_status = 'AMBER')
        LIMIT 10
    """)).fetchall()
    return json.dumps([{"project": r.project_id, "client": r.client_id, "scope": r.scope_status, "schedule": r.schedule_status} for r in rows])


def _recommend_for_role(db: Session, role: str, coe: str | None, skills: str | None) -> str:
    from app.services.scorer import score_all
    from app.services.kb import compute_semantic_skill_scores
    import asyncio
    if not coe:
        coe = "Data Engineering"
    role_query = f"{role} {coe} {skills or ''}".strip()
    all_ids = [r[0] for r in db.execute(text("SELECT employee_id FROM employees WHERE account_status=true AND is_active_version=true AND date_of_resignation IS NULL")).fetchall()]
    try:
        semantic = asyncio.run(compute_semantic_skill_scores(db, role_query, all_ids))
    except RuntimeError:
        import nest_asyncio
        nest_asyncio.apply()
        semantic = asyncio.run(compute_semantic_skill_scores(db, role_query, all_ids))
    scored = score_all(db, canonical_roles=None, always_best_match=False, coe=coe, requested_alloc_pct=100, semantic_scores=semantic)
    top = scored[:5]
    return json.dumps([{"id": c.employee_id, "name": c.job_name, "role": c.canonical_role, "score": f"{round(c.total_score*100)}%", "available": f"{c.available_pct}%", "category": c.category} for c in top])


class ChatRequest(BaseModel):
    message: str
    history: list[dict] = []


@router.post("")
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    messages = [{"role": "system", "content": SYSTEM}]
    for h in req.history[-10:]:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": req.message})

    resp = await client.chat.completions.create(model="gpt-4o", messages=messages, tools=TOOLS, tool_choice="auto", max_tokens=800)
    msg = resp.choices[0].message

    # Handle tool calls
    if msg.tool_calls:
        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _exec_tool(tc.function.name, args, db)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        resp2 = await client.chat.completions.create(model="gpt-4o", messages=messages, max_tokens=800)
        return {"reply": resp2.choices[0].message.content}

    return {"reply": msg.content}
