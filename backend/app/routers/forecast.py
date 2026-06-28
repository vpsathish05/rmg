from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, text
from app.database import get_db
from app.models.pipeline import PipelineRequest

router = APIRouter()


@router.get("")
def list_pipeline(db: Session = Depends(get_db)):
    rows = db.execute(select(PipelineRequest)).scalars().all()
    return rows


@router.get("/outlook")
def pipeline_outlook(db: Session = Depends(get_db)):
    """6-month demand outlook: requests grouped by month × role with weighted FTE."""
    rows = db.execute(text("""
        SELECT
            TO_CHAR(DATE_TRUNC('month', likely_start_date), 'YYYY-MM') AS month,
            COALESCE(role_code_raw, 'Unknown')                           AS role,
            COUNT(*)                                                      AS request_count,
            ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0)::numeric, 2) AS total_fte,
            ROUND(SUM(
                COALESCE(allocation_pct, 100) / 100.0
                * COALESCE(probability_weight, 0.5)
            )::numeric, 2)                                               AS weighted_fte
        FROM pipeline_requests
        WHERE likely_start_date IS NOT NULL
          AND likely_start_date >= CURRENT_DATE
          AND likely_start_date <= CURRENT_DATE + INTERVAL '6 months'
        GROUP BY DATE_TRUNC('month', likely_start_date), COALESCE(role_code_raw, 'Unknown')
        ORDER BY month, total_fte DESC
    """)).fetchall()

    # Reshape into { month: string, roles: { role: {count, fte, weighted_fte} }[] }
    months: dict = {}
    for r in rows:
        m = r.month
        if m not in months:
            months[m] = {"month": m, "total_fte": 0.0, "weighted_fte": 0.0, "roles": []}
        months[m]["roles"].append({
            "role": r.role,
            "request_count": int(r.request_count),
            "total_fte": float(r.total_fte),
            "weighted_fte": float(r.weighted_fte),
        })
        months[m]["total_fte"] = round(months[m]["total_fte"] + float(r.total_fte), 2)
        months[m]["weighted_fte"] = round(months[m]["weighted_fte"] + float(r.weighted_fte), 2)

    return list(months.values())



# Average billing rate assumption (USD per FTE per month)
_BILLING_RATE_MONTHLY = 12000


@router.get("/insights")
def forecast_insights(db: Session = Depends(get_db)):
    """Advanced forecast analytics: funnel, capacity gap, revenue at risk, hot deals, alerts."""

    # 1. Funnel by deal stage
    funnel_rows = db.execute(text("""
        SELECT COALESCE(deal_stage, 'Unknown') AS stage,
               COUNT(*) AS roles,
               ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0 * COALESCE(probability_weight, 0.5))::numeric, 1) AS weighted_fte
        FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
        GROUP BY deal_stage
        ORDER BY weighted_fte DESC
    """)).fetchall()
    funnel = [{"stage": r.stage, "roles": int(r.roles), "weighted_fte": float(r.weighted_fte)} for r in funnel_rows]

    # 2. Capacity gap by canonical_role (demand vs bench)
    demand_rows = db.execute(text("""
        SELECT UNNEST(canonical_roles) AS role,
               ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0)::numeric, 1) AS demand_fte
        FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
          AND likely_start_date IS NOT NULL
          AND likely_start_date <= CURRENT_DATE + INTERVAL '3 months'
        GROUP BY role ORDER BY demand_fte DESC LIMIT 8
    """)).fetchall()

    bench_rows = db.execute(text("""
        SELECT e.canonical_role AS role, COUNT(*) AS bench
        FROM employees e
        LEFT JOIN allocations a ON a.employee_id = e.employee_id
          AND a.is_active = true AND a.is_active_version = true
          AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
        WHERE e.account_status = true AND e.is_active_version = true
          AND e.date_of_resignation IS NULL AND e.canonical_role IS NOT NULL
        GROUP BY e.canonical_role
        HAVING COALESCE(SUM(a.allocation_pct), 0) = 0
    """)).fetchall()
    bench_map = {r.role: int(r.bench) for r in bench_rows}

    capacity_gap = []
    for r in demand_rows:
        bench = bench_map.get(r.role, 0)
        capacity_gap.append({
            "role": r.role,
            "demand": float(r.demand_fte),
            "bench": bench,
            "gap": round(float(r.demand_fte) - bench, 1),
        })

    # 3. Revenue at risk (unresourced × probability × billing rate)
    rev_row = db.execute(text("""
        SELECT
            COUNT(*) AS unresourced_roles,
            ROUND(SUM(COALESCE(allocation_pct, 100) / 100.0 * COALESCE(probability_weight, 0.5))::numeric, 1) AS weighted_fte,
            ROUND(SUM(COALESCE(duration_weeks, 12) / 4.0 * COALESCE(allocation_pct, 100) / 100.0 * COALESCE(probability_weight, 0.5))::numeric, 1) AS weighted_fte_months
        FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
    """)).fetchone()
    revenue_at_risk = round(float(rev_row.weighted_fte_months or 0) * _BILLING_RATE_MONTHLY)

    # 4. Hot deals (high prob, starting soon, not resourced)
    hot_rows = db.execute(text("""
        SELECT client_name, role_code_raw, canonical_roles,
               probability_weight, likely_start_date, duration_weeks, allocation_pct
        FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
          AND probability_weight >= 0.7
          AND likely_start_date IS NOT NULL
          AND likely_start_date <= CURRENT_DATE + INTERVAL '3 months'
        ORDER BY likely_start_date, probability_weight DESC
        LIMIT 12
    """)).fetchall()
    hot_deals = [{
        "client": r.client_name,
        "role": r.role_code_raw,
        "probability": float(r.probability_weight) if r.probability_weight else None,
        "start_date": r.likely_start_date.isoformat() if r.likely_start_date else None,
        "duration_weeks": r.duration_weeks,
        "allocation_pct": float(r.allocation_pct) if r.allocation_pct else 100,
    } for r in hot_rows]

    # 5. Smart alerts
    alerts = []
    # Alert: high-prob deals starting within 30 days with no resource
    urgent = db.execute(text("""
        SELECT COUNT(*) FROM pipeline_requests
        WHERE LOWER(status) = 'not resourced'
          AND probability_weight >= 0.7
          AND likely_start_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
    """)).scalar()
    if urgent and urgent > 0:
        alerts.append({"type": "urgent", "message": f"{urgent} high-probability deal(s) start within 30 days with no resource assigned"})

    # Alert: capacity gap
    for cg in capacity_gap[:3]:
        if cg["gap"] > 2:
            alerts.append({"type": "gap", "message": f"{cg['role']}: need {cg['demand']} FTE but only {cg['bench']} on bench (gap: {cg['gap']})"})

    # Alert: revenue at risk
    if revenue_at_risk > 50000:
        alerts.append({"type": "revenue", "message": f"${revenue_at_risk:,.0f} potential revenue at risk from unresourced roles"})

    return {
        "funnel": funnel,
        "capacity_gap": capacity_gap,
        "revenue_at_risk": revenue_at_risk,
        "unresourced_roles": int(rev_row.unresourced_roles or 0),
        "weighted_fte": float(rev_row.weighted_fte or 0),
        "hot_deals": hot_deals,
        "alerts": alerts,
    }
