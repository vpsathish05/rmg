from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.dashboard import DashboardSummary

router = APIRouter()

_RAG_RANK = {"RED": 0, "AMBER": 1, "GREEN": 2, "NO_COLOR": 3}


def _overall(statuses):
    worst = min((_RAG_RANK.get(s, 3) for s in statuses if s), default=3)
    return {0: "RED", 1: "AMBER", 2: "GREEN", 3: "NO_COLOR"}[worst]


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    # Employee counts
    emp_rows = db.execute(text("""
        SELECT
            e.employee_id,
            COALESCE(SUM(a.allocation_pct), 0) AS allocated_pct
        FROM employees e
        LEFT JOIN allocations a
            ON a.employee_id = e.employee_id
            AND a.is_active = true
            AND a.is_active_version = true
        WHERE e.account_status = true
          AND e.is_active_version = true
          AND e.date_of_resignation IS NULL
          AND e.job_name IS NOT NULL
        GROUP BY e.employee_id
    """)).fetchall()

    total_emp = db.execute(text(
        "SELECT count(*) FROM employees WHERE is_active_version=true"
    )).scalar()

    on_bench = partial = allocated = 0
    for r in emp_rows:
        pct = float(r.allocated_pct or 0)
        if pct == 0:
            on_bench += 1
        elif pct < 100:
            partial += 1
        else:
            allocated += 1

    # Project health
    health_rows = db.execute(text("""
        SELECT ws.scope_status, ws.schedule_status, ws.quality_status,
               ws.csat_status, ws.team_status
        FROM projects p
        LEFT JOIN LATERAL (
            SELECT scope_status, schedule_status, quality_status,
                   csat_status, team_status
            FROM weekly_status
            WHERE project_id = p.project_id
            ORDER BY week_end DESC NULLS LAST
            LIMIT 1
        ) ws ON true
        WHERE p.project_status IN ('ACTIVE','DEAL WON')
          AND p.is_active_version = true
    """)).fetchall()

    red_count = amber_count = 0
    for r in health_rows:
        oh = _overall([r.scope_status, r.schedule_status,
                       r.quality_status, r.csat_status, r.team_status])
        if oh == "RED":
            red_count += 1
        elif oh == "AMBER":
            amber_count += 1

    pipeline_total = db.execute(text("SELECT count(*) FROM pipeline_requests")).scalar()
    pipeline_high = db.execute(text(
        "SELECT count(*) FROM pipeline_requests WHERE probability_weight >= 0.7"
    )).scalar()

    return DashboardSummary(
        total_employees=total_emp or 0,
        active_employees=len(emp_rows),
        on_bench=on_bench,
        partially_available=partial,
        fully_allocated=allocated,
        active_projects=len(health_rows),
        red_projects=red_count,
        amber_projects=amber_count,
        pipeline_requests=pipeline_total or 0,
        high_probability_pipeline=pipeline_high or 0,
    )



@router.get("/charts")
def charts(db: Session = Depends(get_db)):
    """Data for dashboard charts."""

    # 1. Pipeline by deal stage
    stage_rows = db.execute(text("""
        SELECT deal_stage AS stage, COUNT(*) AS cnt
        FROM pipeline_requests
        WHERE deal_stage IS NOT NULL
        GROUP BY deal_stage ORDER BY cnt DESC
    """)).fetchall()
    # Merge case duplicates
    merged: dict[str, int] = {}
    display: dict[str, str] = {}
    for r in stage_rows:
        key = r.stage.lower().strip()
        merged[key] = merged.get(key, 0) + int(r.cnt)
        if key not in display or int(r.cnt) > merged[key] - int(r.cnt):
            display[key] = r.stage
    pipeline_by_stage = [{"stage": display[k], "count": v} for k, v in sorted(merged.items(), key=lambda x: -x[1])]

    # 2. Top open roles (Not Resourced)
    role_rows = db.execute(text("""
        SELECT UNNEST(canonical_roles) AS role, COUNT(*) AS cnt
        FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
        GROUP BY role ORDER BY cnt DESC LIMIT 8
    """)).fetchall()
    top_roles = [{"role": r.role, "count": int(r.cnt)} for r in role_rows]

    # 3. Demand vs Supply next 6 months
    supply_rows = db.execute(text("""
        SELECT TO_CHAR(a.end_date, 'YYYY-MM') AS month, COUNT(DISTINCT a.employee_id) AS freeing
        FROM allocations a
        WHERE a.is_active = true AND a.is_active_version = true
          AND a.end_date >= DATE_TRUNC('month', CURRENT_DATE)
          AND a.end_date < CURRENT_DATE + INTERVAL '6 months'
        GROUP BY TO_CHAR(a.end_date, 'YYYY-MM')
        ORDER BY month
    """)).fetchall()
    demand_rows = db.execute(text("""
        SELECT TO_CHAR(likely_start_date, 'YYYY-MM') AS month, COUNT(*) AS demand
        FROM pipeline_requests
        WHERE likely_start_date >= DATE_TRUNC('month', CURRENT_DATE)
          AND likely_start_date < CURRENT_DATE + INTERVAL '6 months'
          AND LOWER(status) = 'not resourced'
        GROUP BY TO_CHAR(likely_start_date, 'YYYY-MM')
        ORDER BY month
    """)).fetchall()
    supply_map = {r.month: int(r.freeing) for r in supply_rows}
    demand_map = {r.month: int(r.demand) for r in demand_rows}
    all_months = sorted(set(list(supply_map.keys()) + list(demand_map.keys())))
    demand_supply = [{"month": m, "supply": supply_map.get(m, 0), "demand": demand_map.get(m, 0)} for m in all_months]

    # 4. COE distribution (top 8)
    coe_rows = db.execute(text("""
        SELECT coe, COUNT(DISTINCT employee_id) AS cnt
        FROM employee_skills
        WHERE is_assessed = true AND score IS NOT NULL AND score > 0
          AND coe IS NOT NULL AND TRIM(coe) != ''
        GROUP BY coe ORDER BY cnt DESC
    """)).fetchall()
    # Merge case duplicates
    coe_merged: dict[str, int] = {}
    coe_display: dict[str, str] = {}
    for r in coe_rows:
        key = r.coe.lower().strip()
        coe_merged[key] = coe_merged.get(key, 0) + int(r.cnt)
        if key not in coe_display or int(r.cnt) > coe_merged[key] - int(r.cnt):
            coe_display[key] = r.coe.strip()
    coe_distribution = [{"coe": coe_display[k], "count": v} for k, v in sorted(coe_merged.items(), key=lambda x: -x[1])][:8]

    return {
        "pipeline_by_stage": pipeline_by_stage,
        "top_roles": top_roles,
        "demand_supply": demand_supply,
        "coe_distribution": coe_distribution,
    }



@router.get("/charts/detail")
def chart_detail(chart: str, db: Session = Depends(get_db)):
    """Return raw data + calculation explanation for a specific chart."""

    if chart == "project_health":
        rows = db.execute(text("""
            SELECT p.project_id, p.client_id, p.proposition_coe,
                   ws.scope_status, ws.schedule_status, ws.quality_status,
                   ws.csat_status, ws.team_status, ws.week_end
            FROM projects p
            LEFT JOIN LATERAL (
                SELECT scope_status, schedule_status, quality_status, csat_status, team_status, week_end
                FROM weekly_status WHERE project_id = p.project_id
                ORDER BY week_end DESC NULLS LAST LIMIT 1
            ) ws ON true
            WHERE p.project_status IN ('ACTIVE','DEAL WON') AND p.is_active_version = true
            ORDER BY CASE
                WHEN LEAST(
                    CASE ws.scope_status WHEN 'RED' THEN 0 WHEN 'AMBER' THEN 1 WHEN 'GREEN' THEN 2 ELSE 3 END,
                    CASE ws.schedule_status WHEN 'RED' THEN 0 WHEN 'AMBER' THEN 1 WHEN 'GREEN' THEN 2 ELSE 3 END
                ) = 0 THEN 0 ELSE 1 END, p.project_id
        """)).fetchall()
        data = [{
            "project_id": r.project_id, "client": r.client_id, "coe": r.proposition_coe,
            "scope": r.scope_status, "schedule": r.schedule_status, "quality": r.quality_status,
            "csat": r.csat_status, "team": r.team_status, "week": r.week_end.isoformat() if r.week_end else None,
        } for r in rows]
        return {
            "title": "Project Health",
            "explanation": "Overall health = worst status across Scope, Schedule, Quality, CSAT, and Team from the latest weekly_status report per project. RED if any dimension is RED, AMBER if any is AMBER, else GREEN.",
            "columns": ["project_id", "client", "coe", "scope", "schedule", "quality", "csat", "team", "week"],
            "data": data,
        }

    elif chart == "pipeline_by_stage":
        rows = db.execute(text("""
            SELECT deal_stage, client_name, role_code_raw, status, probability_weight
            FROM pipeline_requests WHERE deal_stage IS NOT NULL
            ORDER BY deal_stage, client_name
        """)).fetchall()
        data = [{"stage": r.deal_stage, "client": r.client_name, "role": r.role_code_raw, "status": r.status, "probability": float(r.probability_weight) if r.probability_weight else None} for r in rows]
        return {
            "title": "Pipeline by Deal Stage",
            "explanation": "All pipeline_requests grouped by deal_stage. Case-insensitive merge applied in the chart (e.g. 'Build the Proposition' and 'Build the proposition' are combined). Count = number of roles at each stage.",
            "columns": ["stage", "client", "role", "status", "probability"],
            "data": data,
        }

    elif chart == "top_roles":
        rows = db.execute(text("""
            SELECT UNNEST(canonical_roles) AS role, client_name, role_code_raw, likely_start_date
            FROM pipeline_requests WHERE LOWER(status) = 'not resourced'
            ORDER BY role, client_name
        """)).fetchall()
        data = [{"role": r.role, "client": r.client_name, "role_code": r.role_code_raw, "start_date": r.likely_start_date.isoformat() if r.likely_start_date else None} for r in rows]
        return {
            "title": "Top Open Roles",
            "explanation": "UNNEST(canonical_roles) from pipeline_requests WHERE status = 'Not Resourced'. Grouped by role name, ordered by count descending. Shows which roles have the highest unfilled demand.",
            "columns": ["role", "client", "role_code", "start_date"],
            "data": data,
        }

    elif chart == "coe_distribution":
        rows = db.execute(text("""
            SELECT LOWER(TRIM(coe)) AS coe_key, coe, employee_id,
                   ROUND(AVG(score)::numeric, 1) AS avg_score
            FROM employee_skills
            WHERE is_assessed = true AND score IS NOT NULL AND score > 0
              AND coe IS NOT NULL AND TRIM(coe) != ''
            GROUP BY LOWER(TRIM(coe)), coe, employee_id
            ORDER BY LOWER(TRIM(coe)), avg_score DESC
        """)).fetchall()
        data = [{"coe": r.coe.strip(), "employee_id": r.employee_id, "avg_score": float(r.avg_score)} for r in rows]
        return {
            "title": "COE Distribution",
            "explanation": "COUNT DISTINCT employee_id from employee_skills WHERE is_assessed = true AND score > 0, grouped by COE (case-insensitive merge). Shows workforce strength by technology domain. Table shows each employee's average skill score per COE.",
            "columns": ["coe", "employee_id", "avg_score"],
            "data": data,
        }

    elif chart == "demand_supply":
        demand_rows = db.execute(text("""
            SELECT TO_CHAR(likely_start_date, 'YYYY-MM') AS month, client_name, role_code_raw, canonical_roles
            FROM pipeline_requests
            WHERE likely_start_date >= DATE_TRUNC('month', CURRENT_DATE) AND likely_start_date < CURRENT_DATE + INTERVAL '6 months'
              AND LOWER(status) = 'not resourced'
            ORDER BY likely_start_date
        """)).fetchall()
        supply_rows = db.execute(text("""
            SELECT TO_CHAR(a.end_date, 'YYYY-MM') AS month, a.employee_id, e.job_name, a.project_id
            FROM allocations a
            JOIN employees e ON e.employee_id = a.employee_id
            WHERE a.is_active = true AND a.is_active_version = true
              AND a.end_date >= DATE_TRUNC('month', CURRENT_DATE) AND a.end_date < CURRENT_DATE + INTERVAL '6 months'
            ORDER BY a.end_date
        """)).fetchall()
        data = []
        for r in demand_rows:
            data.append({"type": "DEMAND", "month": r.month, "client": r.client_name, "role": r.role_code_raw, "employee": None, "project": None})
        for r in supply_rows:
            data.append({"type": "SUPPLY", "month": r.month, "client": None, "role": None, "employee": f"{r.employee_id} ({r.job_name})", "project": r.project_id})
        return {
            "title": "Demand vs Supply",
            "explanation": "DEMAND = COUNT of 'Not Resourced' pipeline_requests by likely_start_date month. SUPPLY = COUNT DISTINCT employees whose active allocation end_date falls in that month (they become free). Surplus means more people freeing than roles needed; deficit means hiring/reallocation required.",
            "columns": ["type", "month", "client", "role", "employee", "project"],
            "data": data,
        }

    return {"title": "Unknown", "explanation": "", "columns": [], "data": []}



@router.get("/kpi/detail")
def kpi_detail(kpi: str, db: Session = Depends(get_db)):
    """Return raw data for a specific KPI card."""

    if kpi == "active_employees":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location, e.department_name
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Active Employees",
            "explanation": "All employees WHERE account_status = true, is_active_version = true, date_of_resignation IS NULL, and job_name IS NOT NULL.",
            "columns": ["employee_id", "job_name", "role", "location", "department"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "department": r.department_name} for r in rows],
        }

    elif kpi == "on_bench":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            LEFT JOIN allocations a ON a.employee_id = e.employee_id
              AND a.is_active = true AND a.is_active_version = true
              AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
            GROUP BY e.employee_id, e.job_name, e.canonical_role, e.location
            HAVING COALESCE(SUM(a.allocation_pct), 0) = 0
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "On Bench",
            "explanation": "Active employees with 0% total allocation — no active allocation where end_date >= today. These people are fully available for new projects.",
            "columns": ["employee_id", "job_name", "role", "location"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location} for r in rows],
        }

    elif kpi == "open_pipeline":
        rows = db.execute(text("""
            SELECT id, client_name, role_code_raw, status, deal_stage, probability_weight, likely_start_date
            FROM pipeline_requests
            ORDER BY client_name, id
        """)).fetchall()
        return {
            "title": "Open Pipeline",
            "explanation": "All rows from pipeline_requests table. Includes all statuses (Not Resourced, Resourced, Part Resourced).",
            "columns": ["id", "client", "role", "status", "stage", "probability", "start_date"],
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "status": r.status, "stage": r.deal_stage, "probability": f"{int(r.probability_weight*100)}%" if r.probability_weight else "—", "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "—"} for r in rows],
        }

    elif kpi == "high_probability":
        rows = db.execute(text("""
            SELECT id, client_name, role_code_raw, status, deal_stage, probability_weight, likely_start_date
            FROM pipeline_requests
            WHERE probability_weight >= 0.7
            ORDER BY probability_weight DESC, client_name
        """)).fetchall()
        return {
            "title": "High Probability Pipeline",
            "explanation": "Pipeline requests WHERE probability_weight >= 0.70 (70%+). These are the most likely deals to convert — highest priority for resourcing.",
            "columns": ["id", "client", "role", "status", "stage", "probability", "start_date"],
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "status": r.status, "stage": r.deal_stage, "probability": f"{int(r.probability_weight*100)}%", "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "—"} for r in rows],
        }

    elif kpi == "active_projects":
        rows = db.execute(text("""
            SELECT p.project_id, p.client_id, p.proposition_coe, p.project_start_date, p.project_end_date,
                   COUNT(DISTINCT a.employee_id) AS team_size
            FROM projects p
            LEFT JOIN allocations a ON a.project_id = p.project_id AND a.is_active = true AND a.is_active_version = true
            WHERE p.project_status IN ('ACTIVE','DEAL WON') AND p.is_active_version = true
            GROUP BY p.project_id, p.client_id, p.proposition_coe, p.project_start_date, p.project_end_date
            ORDER BY COUNT(DISTINCT a.employee_id) DESC
        """)).fetchall()
        return {
            "title": "Active Projects",
            "explanation": "Projects WHERE project_status IN ('ACTIVE', 'DEAL WON') AND is_active_version = true. Team size = distinct employees with active allocations.",
            "columns": ["project_id", "client", "coe", "start", "end", "team_size"],
            "data": [{"project_id": r.project_id, "client": r.client_id, "coe": r.proposition_coe, "start": r.project_start_date.isoformat() if r.project_start_date else "—", "end": r.project_end_date.isoformat() if r.project_end_date else "—", "team_size": int(r.team_size)} for r in rows],
        }

    return {"title": "Unknown", "explanation": "", "columns": [], "data": []}
