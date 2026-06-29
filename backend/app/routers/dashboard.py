from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam
from app.database import get_db
from app.schemas.dashboard import DashboardSummary

router = APIRouter()


def _month_range(n: int) -> list[str]:
    """Continuous 'YYYY-MM' labels for the next n months, including the current one."""
    today = date.today()
    y, m = today.year, today.month
    months = []
    for _ in range(n):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months

_RAG_RANK = {"RED": 0, "AMBER": 1, "GREEN": 2, "NO_COLOR": 3}

# Deployable delivery workforce - matches CANONICAL_ROLE_MAP in etl/loaders/employees.py.
# Excludes corporate/support staff (HR, Finance, admin, etc.) whose job_name falls
# through that map unmapped, so they never appear as "available" for client work.
TECH_CONSULTANT_ROLES = (
    "Associate Consultant", "Senior Associate Consultant", "Consultant", "Senior Consultant",
    "Manager", "Senior Manager", "Associate Partner", "Partner", "Principal",
    "Trainee Software Engineer", "Software Engineer", "Senior Software Engineer",
    "Solutions Enabler", "Solutions Consultant", "Senior Solutions Consultant",
    "Engagement Manager", "GTM Architect",
)

_BAU_EXCLUDE = "LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'"

# project_status alone can be stale (still 'ACTIVE' after the end date has passed) -
# a project only counts as currently active if its end date hasn't happened yet.
_NOT_ENDED = "(p.project_end_date IS NULL OR p.project_end_date >= CURRENT_DATE)"

# The allocations table is populated in ~weekly segments per project, so a person's
# current-week row can lag several days behind reality even after it starts. Approved
# timesheet hours are the ground truth for "are they actually working right now" -
# used to stop someone whose allocation row hasn't rolled over yet from showing as bench.
_RECENT_REAL_WORK = """EXISTS (
        SELECT 1 FROM timesheets t
        JOIN projects tp ON tp.project_id = t.project_id AND tp.is_active_version = true
        WHERE t.employee_id = e.employee_id
          AND t.date >= CURRENT_DATE - INTERVAL '30 days'
          AND t.status = 'APPROVED'
          AND LOWER(COALESCE(tp.type_of_project, '')) IN ('client project', 'managed services')
    )"""


def _overall(statuses):
    worst = min((_RAG_RANK.get(s, 3) for s in statuses if s), default=3)
    return {0: "RED", 1: "AMBER", 2: "GREEN", 3: "NO_COLOR"}[worst]


@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    # Employee counts (BAU allocations excluded from allocation %)
    # Extended query: also fetch billable vs unbillable allocation breakdown
    emp_rows = db.execute(text(f"""
        SELECT e.employee_id, e.canonical_role,
            COALESCE((
                SELECT SUM(a.allocation_pct)
                FROM allocations a
                JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                WHERE a.employee_id = e.employee_id
                  AND a.is_active_version = true
                  AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                  AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
            ), 0) AS allocated_pct,
            COALESCE((
                SELECT SUM(a.allocation_pct)
                FROM allocations a
                JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                WHERE a.employee_id = e.employee_id
                  AND a.is_active_version = true
                  AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                  AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                  AND UPPER(a.resourcing_status) = 'BILLABLE'
            ), 0) AS billable_pct,
            COALESCE((
                SELECT SUM(a.allocation_pct)
                FROM allocations a
                JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                WHERE a.employee_id = e.employee_id
                  AND a.is_active_version = true
                  AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                  AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                  AND UPPER(a.resourcing_status) != 'BILLABLE'
            ), 0) AS unbillable_pct,
            {_RECENT_REAL_WORK} AS has_recent_real_work
        FROM employees e
        WHERE e.account_status = true
          AND e.is_active_version = true
          AND e.date_of_resignation IS NULL
          AND e.job_name IS NOT NULL
    """)).fetchall()

    total_emp = db.execute(text(
        "SELECT count(*) FROM employees WHERE is_active_version=true"
    )).scalar()

    # On Bench / Partially Available / Fully Allocated only consider deployable
    # delivery workforce (tech roles & Consultants) - corporate/support staff are
    # never assigned client work so they shouldn't show as "available".
    on_bench = partial = allocated = 0
    # Allocation Health: Billable / Unbillable / Over-Allocated / Bench
    billable_count = unbillable_count = over_allocated_count = 0
    for r in emp_rows:
        if r.canonical_role not in TECH_CONSULTANT_ROLES:
            continue
        pct = float(r.allocated_pct or 0)
        billable_pct = float(r.billable_pct or 0)
        unbillable_pct_val = float(r.unbillable_pct or 0)

        # Legacy categories (kept for backwards compat)
        if pct == 0:
            if r.has_recent_real_work:
                partial += 1
            else:
                on_bench += 1
        elif pct < 100:
            partial += 1
        else:
            allocated += 1

        # New Allocation Health categories
        if pct > 100:
            over_allocated_count += 1
        elif pct == 0:
            if r.has_recent_real_work:
                # Shadow resource: working (timesheets) but no formal allocation → unbillable
                unbillable_count += 1
            # else: bench - counted separately (on_bench already captured)
        elif unbillable_pct_val > 0 and billable_pct == 0:
            # All allocation is non-billable
            unbillable_count += 1
        elif billable_pct > 0:
            # Has at least some billable allocation and total ≤ 100%
            billable_count += 1
        else:
            # Allocated but status unclear - treat as unbillable
            unbillable_count += 1

    # Project health - latest WSR within last calendar month (not all-time),
    # so stale projects with no recent reporting don't show a months-old status.
    health_rows = db.execute(text("""
        SELECT ws.scope_status, ws.schedule_status, ws.quality_status,
               ws.csat_status, ws.team_status
        FROM projects p
        LEFT JOIN LATERAL (
            SELECT scope_status, schedule_status, quality_status,
                   csat_status, team_status
            FROM weekly_status
            WHERE project_id = p.project_id
              AND week_start >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
              AND week_start < DATE_TRUNC('month', CURRENT_DATE)
              AND (scope_status != 'NO_COLOR' OR schedule_status != 'NO_COLOR'
                   OR quality_status != 'NO_COLOR' OR csat_status != 'NO_COLOR'
                   OR team_status != 'NO_COLOR')
            ORDER BY week_end DESC NULLS LAST
            LIMIT 1
        ) ws ON true
        WHERE p.project_status IN ('ACTIVE','DEAL WON')
          AND p.is_active_version = true
          AND """ + _BAU_EXCLUDE + """
          AND """ + _NOT_ENDED + """
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

    # ── Revenue Leakage Calculation ─────────────────────────────────────────
    # Uses average day rate from rate card × working days to estimate monthly £ lost
    from ml.rate_card import load_rate_card, FX_GBP_TO_USD
    rates = load_rate_card()
    avg_day_rate_usd = sum(e.day_rate_usd for e in rates.values()) / max(len(rates), 1)
    avg_day_rate_gbp = avg_day_rate_usd / FX_GBP_TO_USD
    working_days_month = 22

    # Unbillable leakage: sum of non-BILLABLE allocation % across all employees
    unbill_row = db.execute(text("""
        SELECT COALESCE(SUM(a.allocation_pct), 0) AS total_unbillable_pct
        FROM allocations a
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        WHERE a.is_active_version = true
          AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
          AND UPPER(a.resourcing_status) != 'BILLABLE'
          AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
    """)).fetchone()
    unbill_fte = float(unbill_row.total_unbillable_pct or 0) / 100.0
    unbillable_leakage = round(unbill_fte * avg_day_rate_gbp * working_days_month, 0)

    # Over-allocation leakage: sum of (total_alloc - 100%) for all over-allocated employees
    over_rows = db.execute(text("""
        SELECT SUM(sub.total_pct - 100) AS excess_pct FROM (
            SELECT a.employee_id, SUM(a.allocation_pct) AS total_pct
            FROM allocations a
            JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
            JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
              AND e.account_status = true AND e.date_of_resignation IS NULL
            WHERE a.is_active_version = true
              AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
              AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
            GROUP BY a.employee_id
            HAVING SUM(a.allocation_pct) > 100
        ) sub
    """)).fetchone()
    over_excess_fte = float(over_rows.excess_pct or 0) / 100.0
    overalloc_leakage = round(over_excess_fte * avg_day_rate_gbp * working_days_month, 0)

    return DashboardSummary(
        total_employees=total_emp or 0,
        active_employees=len(emp_rows),
        on_bench=on_bench,
        partially_available=partial,
        fully_allocated=allocated,
        billable_count=billable_count,
        unbillable_count=unbillable_count,
        over_allocated_count=over_allocated_count,
        unbillable_leakage_monthly=unbillable_leakage,
        overalloc_leakage_monthly=overalloc_leakage,
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
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        WHERE a.is_active_version = true
          AND a.end_date >= DATE_TRUNC('month', CURRENT_DATE)
          AND a.end_date < CURRENT_DATE + INTERVAL '6 months'
          AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
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
    # Continuous month range - months with zero demand AND zero supply must still
    # appear (as 0/0), otherwise the line chart silently drops that month.
    all_months = _month_range(6)
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
def chart_detail(chart: str, status: str | None = None, db: Session = Depends(get_db)):
    """Return raw data + calculation explanation for a specific chart.

    `status` (RED/AMBER/GREEN) narrows project_health to projects whose current
    (latest-week-in-last-month) status matches - used when a RAG badge is clicked.
    """

    if chart == "project_health":
        rows = db.execute(text("""
            SELECT p.project_id, p.client_id, p.proposition_coe,
                   ws.scope_status, ws.schedule_status, ws.quality_status,
                   ws.csat_status, ws.team_status, ws.week_start, ws.week_end,
                   ROW_NUMBER() OVER (PARTITION BY p.project_id ORDER BY ws.week_start) AS week_num
            FROM projects p
            LEFT JOIN weekly_status ws ON ws.project_id = p.project_id
              AND ws.week_start >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
              AND ws.week_start < DATE_TRUNC('month', CURRENT_DATE)
              AND (ws.scope_status != 'NO_COLOR' OR ws.schedule_status != 'NO_COLOR'
                   OR ws.quality_status != 'NO_COLOR' OR ws.csat_status != 'NO_COLOR'
                   OR ws.team_status != 'NO_COLOR')
            WHERE p.project_status IN ('ACTIVE','DEAL WON') AND p.is_active_version = true
              AND """ + _BAU_EXCLUDE + """
              AND """ + _NOT_ENDED + """
            ORDER BY p.project_id, ws.week_start NULLS FIRST
        """)).fetchall()

        by_project: dict[str, list] = {}
        for r in rows:
            by_project.setdefault(r.project_id, []).append(r)

        data = []
        for pid, prows in by_project.items():
            headline = max(prows, key=lambda r: r.week_start or date.min)
            headline_status = _overall([headline.scope_status, headline.schedule_status,
                                         headline.quality_status, headline.csat_status, headline.team_status])
            if status and headline_status != status.upper():
                continue
            for r in prows:
                overall = _overall([r.scope_status, r.schedule_status, r.quality_status, r.csat_status, r.team_status])
                data.append({
                    "project_id": r.project_id, "client": r.client_id, "coe": r.proposition_coe,
                    "week": f"Week {r.week_num}" if r.week_start else None,
                    "status": overall,
                    "scope": r.scope_status, "schedule": r.schedule_status, "quality": r.quality_status,
                    "csat": r.csat_status, "team": r.team_status,
                    "week_end": r.week_end.isoformat() if r.week_end else None,
                })
        data.sort(key=lambda d: (_RAG_RANK.get(d["status"], 3), d["project_id"], d["week"] or ""))
        return {
            "title": "Project Health" + (f" - {status.upper()}" if status else ""),
            "explanation": "Overall status per week = worst of Scope, Schedule, Quality, CSAT, and Team (excluding all-NO_COLOR weeks), scoped to the last calendar month. A project's dashboard RAG badge reflects its most recent reported week in that month. Use the 'week' column filter to inspect Week 1-4 individually. BAU-only projects are excluded.",
            "columns": ["project_id", "client", "coe", "week", "status", "scope", "schedule", "quality", "csat", "team", "week_end"],
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
            JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
            WHERE a.is_active_version = true
              AND a.end_date >= DATE_TRUNC('month', CURRENT_DATE) AND a.end_date < CURRENT_DATE + INTERVAL '6 months'
              AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
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

    elif chart == "allocation_health":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), 0) AS total_pct,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                      AND UPPER(a.resourcing_status) = 'BILLABLE'
                ), 0) AS billable_pct,
                COALESCE((
                    SELECT STRING_AGG(DISTINCT UPPER(a.resourcing_status), ', ') FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), '') AS statuses
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
            ORDER BY total_pct DESC NULLS LAST
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()

        data = []
        for r in rows:
            total = float(r.total_pct or 0)
            billable = float(r.billable_pct or 0)
            unbillable = total - billable
            if total == 0:
                category = "Bench"
            elif total > 100:
                category = "Over-Allocated"
            elif unbillable > 0 and billable == 0:
                category = "Unbillable"
            elif billable > 0:
                category = "Billable"
            else:
                category = "Unbillable"
            data.append({
                "employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role,
                "location": r.location, "category": category, "total_pct": f"{int(total)}%",
                "billable_pct": f"{int(billable)}%", "unbillable_pct": f"{int(unbillable)}%",
                "statuses": r.statuses,
            })

        return {
            "title": "Allocation Health",
            "explanation": "Every delivery employee classified by allocation health: Billable (has BILLABLE allocations, total ≤100%), Unbillable (allocated but all non-BILLABLE status - SHADOW, INTERNAL, etc.), Over-Allocated (total allocation >100% across projects - burnout risk), Bench (0% allocation). Use the 'category' column filter to focus on one group.",
            "columns": ["employee_id", "job_name", "role", "location", "category", "total_pct", "billable_pct", "unbillable_pct", "statuses"],
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
        rows = db.execute(text(f"""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
              AND COALESCE((
                  SELECT SUM(a.allocation_pct) FROM allocations a
                  JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                  WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                    AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                    AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
              ), 0) = 0
              AND NOT {_RECENT_REAL_WORK}
            ORDER BY e.canonical_role, e.employee_id
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()
        return {
            "title": "On Bench",
            "explanation": "Active employees in delivery roles (tech roles & Consultants - corporate/support staff excluded) with 0% non-BAU allocation AND no approved Client Project / Managed Services timesheet hours in the last 30 days. The timesheet check catches people whose allocation record hasn't rolled over to the new period yet but who are still actively working - the allocations table is populated in weekly segments and can lag 2-4 weeks.",
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
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "status": r.status, "stage": r.deal_stage, "probability": f"{int(r.probability_weight*100)}%" if r.probability_weight else "-", "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "-"} for r in rows],
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
            "explanation": "Pipeline requests WHERE probability_weight >= 0.70 (70%+). These are the most likely deals to convert - highest priority for resourcing.",
            "columns": ["id", "client", "role", "status", "stage", "probability", "start_date"],
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "status": r.status, "stage": r.deal_stage, "probability": f"{int(r.probability_weight*100)}%", "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "-"} for r in rows],
        }

    elif kpi == "partially_available":
        rows = db.execute(text(f"""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), 0) AS allocated_pct,
                {_RECENT_REAL_WORK} AS has_recent_real_work
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
            ORDER BY e.canonical_role, e.employee_id
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()

        data = []
        for r in rows:
            pct = float(r.allocated_pct or 0)
            if 0 < pct < 100:
                data.append({"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "allocated_pct": f"{int(pct)}%"})
            elif pct == 0 and r.has_recent_real_work:
                data.append({"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "allocated_pct": "Active (allocation record lapsed)"})

        return {
            "title": "Partially Available",
            "explanation": "Active employees in delivery roles (tech roles & Consultants) with 1-99% non-BAU allocation, OR 0% allocation but approved Client Project / Managed Services timesheet hours logged in the last 30 days (allocation record hasn't rolled over yet, but timesheets show they're still actively working - so they're not truly free).",
            "columns": ["employee_id", "job_name", "role", "location", "allocated_pct"],
            "data": data,
        }

    elif kpi == "active_projects":
        rows = db.execute(text("""
            SELECT p.project_id, p.client_id, p.proposition_coe, p.project_start_date, p.project_end_date
            FROM projects p
            WHERE p.project_status IN ('ACTIVE','DEAL WON') AND p.is_active_version = true
              AND """ + _BAU_EXCLUDE + """
              AND """ + _NOT_ENDED + """
            ORDER BY p.project_end_date NULLS LAST, p.project_id
        """)).fetchall()
        return {
            "title": "Active Projects",
            "explanation": "Projects WHERE project_status IN ('ACTIVE', 'DEAL WON') AND is_active_version = true, excluding BAU Activity projects (tracking overhead, not real client work) and projects whose end date has already passed (stale status).",
            "columns": ["project_id", "client", "coe", "start", "end"],
            "data": [{"project_id": r.project_id, "client": r.client_id, "coe": r.proposition_coe, "start": r.project_start_date.isoformat() if r.project_start_date else "-", "end": r.project_end_date.isoformat() if r.project_end_date else "-"} for r in rows],
        }

    elif kpi == "billable":
        rows = db.execute(text(f"""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), 0) AS total_pct,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                      AND UPPER(a.resourcing_status) = 'BILLABLE'
                ), 0) AS billable_pct
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
            ORDER BY e.canonical_role, e.employee_id
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()

        data = []
        for r in rows:
            total = float(r.total_pct or 0)
            billable = float(r.billable_pct or 0)
            if billable > 0 and total <= 100:
                data.append({"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "billable_pct": f"{int(billable)}%", "total_pct": f"{int(total)}%"})

        return {
            "title": "Billable Resources",
            "explanation": "Active delivery employees with at least some BILLABLE allocation on non-BAU projects, and total allocation ≤ 100%. These are generating revenue.",
            "columns": ["employee_id", "job_name", "role", "location", "billable_pct", "total_pct"],
            "data": data,
        }

    elif kpi == "unbillable":
        rows = db.execute(text(f"""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), 0) AS total_pct,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                      AND UPPER(a.resourcing_status) = 'BILLABLE'
                ), 0) AS billable_pct,
                COALESCE((
                    SELECT STRING_AGG(DISTINCT UPPER(a.resourcing_status), ', ') FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                      AND UPPER(a.resourcing_status) != 'BILLABLE'
                ), '') AS unbillable_statuses,
                {_RECENT_REAL_WORK} AS has_recent_real_work
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
            ORDER BY e.canonical_role, e.employee_id
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()

        data = []
        for r in rows:
            total = float(r.total_pct or 0)
            billable = float(r.billable_pct or 0)
            unbillable_pct = total - billable
            if total == 0 and r.has_recent_real_work:
                data.append({"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "unbillable_pct": "Shadow (no allocation)", "status": "SHADOW", "reason": "Approved timesheets but no formal allocation"})
            elif unbillable_pct > 0 and billable == 0:
                data.append({"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "unbillable_pct": f"{int(unbillable_pct)}%", "status": r.unbillable_statuses, "reason": "All allocations are non-billable"})

        return {
            "title": "Unbillable Resources",
            "explanation": "Delivery employees who are working but NOT generating revenue: either allocated with non-BILLABLE status (SHADOW, INTERNAL, NON-BILLABLE) OR have approved timesheets on projects but no formal allocation record (shadow resources). This is hidden cost.",
            "columns": ["employee_id", "job_name", "role", "location", "unbillable_pct", "status", "reason"],
            "data": data,
        }

    elif kpi == "over_allocated":
        rows = db.execute(text(f"""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location,
                COALESCE((
                    SELECT SUM(a.allocation_pct) FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ), 0) AS total_pct,
                (
                    SELECT STRING_AGG(p.client_id || ' (' || a.allocation_pct || '%)', ', ')
                    FROM allocations a
                    JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                    WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                      AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                      AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
                ) AS project_breakdown
            FROM employees e
            WHERE e.account_status = true AND e.is_active_version = true
              AND e.date_of_resignation IS NULL AND e.job_name IS NOT NULL
              AND e.canonical_role IN :roles
            HAVING COALESCE((
                SELECT SUM(a.allocation_pct) FROM allocations a
                JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                WHERE a.employee_id = e.employee_id AND a.is_active_version = true
                  AND a.start_date <= CURRENT_DATE AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                  AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
            ), 0) > 100
            ORDER BY total_pct DESC
        """).bindparams(bindparam("roles", expanding=True)), {"roles": TECH_CONSULTANT_ROLES}).fetchall()

        data = [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "total_pct": f"{int(float(r.total_pct))}%", "projects": r.project_breakdown} for r in rows]

        return {
            "title": "Over-Allocated Resources",
            "explanation": "Delivery employees whose total non-BAU allocation exceeds 100% across competing projects. This causes burnout, quality issues, and context-switching costs. The 'projects' column shows which clients/projects are competing for the same person.",
            "columns": ["employee_id", "job_name", "role", "location", "total_pct", "projects"],
            "data": data,
        }

    return {"title": "Unknown", "explanation": "", "columns": [], "data": []}



# ─────────────────────────────────────────────────────────────────────────────
# Data Health — Gap Analysis
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/data-health")
def data_health(db: Session = Depends(get_db)):
    """Compute data completeness score and identify gaps across all tables."""

    # Total active employees
    emp_total = db.execute(text(
        "SELECT COUNT(*) FROM employees WHERE is_active_version=true AND account_status=true AND date_of_resignation IS NULL"
    )).scalar() or 1

    # 1. Employee Skills
    with_skills = db.execute(text(
        "SELECT COUNT(DISTINCT employee_id) FROM employee_skills WHERE is_assessed=true AND score IS NOT NULL AND score > 0"
    )).scalar() or 0

    # 2. Employee COE tag
    with_coe = db.execute(text(
        "SELECT COUNT(DISTINCT employee_id) FROM employee_skills WHERE coe IS NOT NULL AND TRIM(coe) != ''"
    )).scalar() or 0

    # 3. Competency
    with_comp = db.execute(text(
        "SELECT COUNT(DISTINCT employee_id) FROM employee_competencies WHERE score IS NOT NULL"
    )).scalar() or 0

    # 4. Pipeline totals
    pipe_total = db.execute(text("SELECT COUNT(*) FROM pipeline_requests")).scalar() or 1
    pipe_no_duration = db.execute(text(
        "SELECT COUNT(*) FROM pipeline_requests WHERE duration_weeks IS NULL"
    )).scalar() or 0
    pipe_no_skills = db.execute(text(
        "SELECT COUNT(*) FROM pipeline_requests WHERE required_skills IS NULL OR required_skills = 'nan'"
    )).scalar() or 0

    # 5. Project COE
    proj_total = db.execute(text("SELECT COUNT(*) FROM projects WHERE is_active_version=true")).scalar() or 1
    proj_no_coe = db.execute(text(
        "SELECT COUNT(*) FROM projects WHERE is_active_version=true AND (proposition_coe IS NULL OR proposition_coe='')"
    )).scalar() or 0

    # 6. Timesheets (last 30 days)
    with_ts = db.execute(text(
        "SELECT COUNT(DISTINCT employee_id) FROM timesheets WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND status='APPROVED'"
    )).scalar() or 0

    # 7. Skill embeddings
    with_emb = db.execute(text("SELECT COUNT(*) FROM employee_skill_embeddings")).scalar() or 0

    # 8. Employee metadata
    no_role = db.execute(text(
        "SELECT COUNT(*) FROM employees WHERE is_active_version=true AND account_status=true AND date_of_resignation IS NULL AND (canonical_role IS NULL OR canonical_role='nan')"
    )).scalar() or 0

    # Build gaps list
    gaps = [
        {
            "id": "skills",
            "area": "Employee Skills",
            "metric": f"{emp_total - with_skills} of {emp_total} employees have no assessed skills",
            "count": emp_total - with_skills,
            "total": emp_total,
            "pct_complete": round(with_skills / emp_total * 100, 1),
            "severity": "critical",
            "impact": "AI recommendations score these employees at 0 or neutral — they rarely surface as candidates",
            "action": "Run skill assessments for untagged employees, prioritise delivery roles",
        },
        {
            "id": "pipeline_duration",
            "area": "Pipeline Duration",
            "metric": f"{pipe_no_duration} of {pipe_total} pipeline roles have no duration_weeks",
            "count": pipe_no_duration,
            "total": pipe_total,
            "pct_complete": round((pipe_total - pipe_no_duration) / pipe_total * 100, 1),
            "severity": "high",
            "impact": "Revenue forecast defaults to 12 weeks — inaccurate prorated revenue projections",
            "action": "EMs/Commercial to fill in estimated engagement duration when creating pipeline entries",
        },
        {
            "id": "pipeline_skills",
            "area": "Pipeline Required Skills",
            "metric": f"{pipe_no_skills} of {pipe_total} pipeline roles have no required_skills",
            "count": pipe_no_skills,
            "total": pipe_total,
            "pct_complete": round((pipe_total - pipe_no_skills) / pipe_total * 100, 1),
            "severity": "high",
            "impact": "Falls back to LLM inference for skill matching — slower and less precise",
            "action": "Add required skills when submitting pipeline requests",
        },
        {
            "id": "competency",
            "area": "Competency Scores",
            "metric": f"{emp_total - with_comp} of {emp_total} employees have no competency scores",
            "count": emp_total - with_comp,
            "total": emp_total,
            "pct_complete": round(with_comp / emp_total * 100, 1),
            "severity": "high",
            "impact": "Scoring uses weaker formula (no competency component) for 70% of employees",
            "action": "Expand competency framework beyond current 3 roles to all delivery roles",
        },
        {
            "id": "project_coe",
            "area": "Project COE Tags",
            "metric": f"{proj_no_coe} of {proj_total} projects have no proposition_coe",
            "count": proj_no_coe,
            "total": proj_total,
            "pct_complete": round((proj_total - proj_no_coe) / proj_total * 100, 1),
            "severity": "medium",
            "impact": "Cannot attribute projects to COEs for gap analysis and KB proofs",
            "action": "PMO to backfill COE tags from project team composition",
        },
        {
            "id": "coe_tags",
            "area": "Employee COE Tags",
            "metric": f"{emp_total - with_coe} of {emp_total} employees have no COE tag via skills",
            "count": emp_total - with_coe,
            "total": emp_total,
            "pct_complete": round(with_coe / emp_total * 100, 1),
            "severity": "medium",
            "impact": "COE gap model under-reports supply — relies on role-based inference fallback",
            "action": "Assign primary COE during skill assessment or onboarding",
        },
        {
            "id": "timesheets",
            "area": "Recent Timesheets",
            "metric": f"{emp_total - with_ts} of {emp_total} employees have no approved timesheets in last 30 days",
            "count": emp_total - with_ts,
            "total": emp_total,
            "pct_complete": round(with_ts / emp_total * 100, 1),
            "severity": "medium",
            "impact": "Productivity score = 0, availability cross-check may be inaccurate",
            "action": "Ensure all active employees submit timesheets weekly",
        },
        {
            "id": "embeddings",
            "area": "Skill Embeddings",
            "metric": f"{emp_total - with_emb} of {emp_total} employees have no skill embeddings",
            "count": emp_total - with_emb,
            "total": emp_total,
            "pct_complete": round(with_emb / emp_total * 100, 1),
            "severity": "medium",
            "impact": "Semantic skill matching only works for employees with embeddings",
            "action": "Run ETL: python -m etl.build_skill_embeddings (requires skills data first)",
        },
        {
            "id": "employee_metadata",
            "area": "Employee Metadata",
            "metric": f"{no_role} employees missing canonical_role",
            "count": no_role,
            "total": emp_total,
            "pct_complete": round((emp_total - no_role) / emp_total * 100, 1),
            "severity": "low",
            "impact": "Excluded from role-filtered recommendations",
            "action": "HR to update missing role assignments in source system",
        },
    ]

    # Overall score = weighted average of pct_complete
    # Critical=3x, High=2x, Medium=1x, Low=0.5x
    weight_map = {"critical": 3, "high": 2, "medium": 1, "low": 0.5}
    weighted_sum = sum(g["pct_complete"] * weight_map[g["severity"]] for g in gaps)
    weight_total = sum(weight_map[g["severity"]] for g in gaps)
    overall_score = round(weighted_sum / weight_total, 0) if weight_total > 0 else 0

    return {
        "overall_score": int(overall_score),
        "total_gaps": len([g for g in gaps if g["pct_complete"] < 100]),
        "critical_gaps": len([g for g in gaps if g["severity"] == "critical" and g["pct_complete"] < 80]),
        "gaps": gaps,
    }


@router.get("/data-health/detail")
def data_health_detail(gap: str, db: Session = Depends(get_db)):
    """Return affected rows for a specific data gap — used by drill-down modal."""

    if gap == "skills":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location, e.department_name
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND e.employee_id NOT IN (
                  SELECT DISTINCT employee_id FROM employee_skills
                  WHERE is_assessed = true AND score IS NOT NULL AND score > 0
              )
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Without Skills Data",
            "explanation": "Active employees with no assessed skill scores in employee_skills. These employees cannot be scored accurately by the AI recommendation engine — they receive a skill_score of 0 or SKILL_NEUTRAL (0.15).",
            "columns": ["employee_id", "job_name", "role", "location", "department"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "department": r.department_name} for r in rows],
        }

    elif gap == "pipeline_duration":
        rows = db.execute(text("""
            SELECT id, client_name, role_code_raw, canonical_roles, likely_start_date, status
            FROM pipeline_requests
            WHERE duration_weeks IS NULL
            ORDER BY client_name, id
        """)).fetchall()
        return {
            "title": "Pipeline Roles Missing Duration",
            "explanation": "Pipeline requests where duration_weeks is NULL. The revenue forecast defaults to 12 weeks for these, which may under/over-estimate prorated revenue.",
            "columns": ["id", "client", "role", "start_date", "status"],
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "—", "status": r.status} for r in rows],
        }

    elif gap == "pipeline_skills":
        rows = db.execute(text("""
            SELECT id, client_name, role_code_raw, canonical_roles, likely_start_date, status
            FROM pipeline_requests
            WHERE required_skills IS NULL OR required_skills = 'nan'
            ORDER BY client_name, id
        """)).fetchall()
        return {
            "title": "Pipeline Roles Missing Required Skills",
            "explanation": "Pipeline requests where required_skills is NULL or 'nan'. The system falls back to GPT-4o inference to guess required skills — this is slower and less precise than having explicit skill requirements.",
            "columns": ["id", "client", "role", "start_date", "status"],
            "data": [{"id": r.id, "client": r.client_name, "role": r.role_code_raw, "start_date": r.likely_start_date.isoformat() if r.likely_start_date else "—", "status": r.status} for r in rows],
        }

    elif gap == "competency":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND e.employee_id NOT IN (
                  SELECT DISTINCT employee_id FROM employee_competencies WHERE score IS NOT NULL
              )
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Without Competency Scores",
            "explanation": "Active employees with no competency assessment. The scoring formula falls back to skill×0.65 + avail×0.25 + prod×0.10 (no competency component), which is less discriminating.",
            "columns": ["employee_id", "job_name", "role", "location"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location} for r in rows],
        }

    elif gap == "project_coe":
        rows = db.execute(text("""
            SELECT project_id, client_id, project_status, project_start_date, project_end_date
            FROM projects
            WHERE is_active_version = true
              AND (proposition_coe IS NULL OR proposition_coe = '')
            ORDER BY project_start_date DESC NULLS LAST
            LIMIT 200
        """)).fetchall()
        return {
            "title": "Projects Missing COE Tag",
            "explanation": "Projects with no proposition_coe. These cannot be properly attributed to a Centre of Excellence for gap analysis or KB proofs.",
            "columns": ["project_id", "client", "status", "start", "end"],
            "data": [{"project_id": r.project_id, "client": r.client_id, "status": r.project_status, "start": r.project_start_date.isoformat() if r.project_start_date else "—", "end": r.project_end_date.isoformat() if r.project_end_date else "—"} for r in rows],
        }

    elif gap == "coe_tags":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND e.employee_id NOT IN (
                  SELECT DISTINCT employee_id FROM employee_skills
                  WHERE coe IS NOT NULL AND TRIM(coe) != ''
              )
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Without COE Tag",
            "explanation": "Active employees with no COE assignment in employee_skills. The COE gap model uses role-based inference as fallback, but explicit tags are more accurate.",
            "columns": ["employee_id", "job_name", "role", "location"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location} for r in rows],
        }

    elif gap == "timesheets":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND e.employee_id NOT IN (
                  SELECT DISTINCT employee_id FROM timesheets
                  WHERE date >= CURRENT_DATE - INTERVAL '30 days' AND status = 'APPROVED'
              )
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Without Recent Timesheets",
            "explanation": "Active employees with no approved timesheet entries in the last 30 days. Their productivity score will be 0, and the availability cross-check cannot verify if they are actually working.",
            "columns": ["employee_id", "job_name", "role", "location"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location} for r in rows],
        }

    elif gap == "embeddings":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND e.employee_id NOT IN (
                  SELECT DISTINCT employee_id FROM employee_skill_embeddings
              )
            ORDER BY e.canonical_role, e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Without Skill Embeddings",
            "explanation": "Active employees with no vector embedding in employee_skill_embeddings. Semantic skill matching (ANN search) cannot find these employees — only formula-based scoring applies.",
            "columns": ["employee_id", "job_name", "role", "location"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location} for r in rows],
        }

    elif gap == "employee_metadata":
        rows = db.execute(text("""
            SELECT e.employee_id, e.job_name, e.canonical_role, e.location, e.department_name
            FROM employees e
            WHERE e.is_active_version = true AND e.account_status = true
              AND e.date_of_resignation IS NULL
              AND (e.canonical_role IS NULL OR e.canonical_role = 'nan')
            ORDER BY e.employee_id
        """)).fetchall()
        return {
            "title": "Employees Missing Metadata",
            "explanation": "Active employees with missing canonical_role. They are excluded from role-filtered recommendations and cannot be properly categorised.",
            "columns": ["employee_id", "job_name", "role", "location", "department"],
            "data": [{"employee_id": r.employee_id, "job_name": r.job_name, "role": r.canonical_role, "location": r.location, "department": r.department_name} for r in rows],
        }

    return {"title": "Unknown", "explanation": "", "columns": [], "data": []}
