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
        SELECT COALESCE(deal_stage, 'Unknown') AS stage, COUNT(*) AS cnt
        FROM pipeline_requests
        GROUP BY deal_stage ORDER BY cnt DESC
    """)).fetchall()
    pipeline_by_stage = [{"stage": r.stage, "count": int(r.cnt)} for r in stage_rows]

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
          AND a.end_date >= CURRENT_DATE
          AND a.end_date < CURRENT_DATE + INTERVAL '6 months'
        GROUP BY TO_CHAR(a.end_date, 'YYYY-MM')
        ORDER BY month
    """)).fetchall()
    demand_rows = db.execute(text("""
        SELECT TO_CHAR(likely_start_date, 'YYYY-MM') AS month, COUNT(*) AS demand
        FROM pipeline_requests
        WHERE likely_start_date >= CURRENT_DATE
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
        SELECT INITCAP(TRIM(coe)) AS coe, COUNT(DISTINCT employee_id) AS cnt
        FROM employee_skills
        WHERE is_assessed = true AND score IS NOT NULL AND score > 0
          AND coe IS NOT NULL AND TRIM(coe) != ''
        GROUP BY TRIM(coe) ORDER BY cnt DESC LIMIT 8
    """)).fetchall()
    coe_distribution = [{"coe": r.coe, "count": int(r.cnt)} for r in coe_rows]

    return {
        "pipeline_by_stage": pipeline_by_stage,
        "top_roles": top_roles,
        "demand_supply": demand_supply,
        "coe_distribution": coe_distribution,
    }
