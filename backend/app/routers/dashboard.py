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
