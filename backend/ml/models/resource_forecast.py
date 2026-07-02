"""
Resource Demand Model — 12-month FTE forecast by role.

Combines:
  1. Historical allocation trend (Holt smoothing on monthly billable FTE per role)
  2. Pipeline demand signal (probability-weighted FTE from pipeline_calc)
  3. Hiring gap = projected demand - current headcount × utilization target

Output:
  - Total FTE demand per month (next 12)
  - Per-role breakdown (top 15 canonical roles)
  - Bench forecast (headcount - allocated)
  - Hiring gap per role
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from ..pipeline_calc import PipelineResult
from ..data_prep import get_monthly_headcount


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class RoleMonth:
    """FTE forecast for a single role in a single month."""
    month: str
    role: str
    historical_fte: float     # Trend-based FTE projection
    pipeline_fte: float       # Pipeline demand signal
    blended_fte: float        # Combined forecast


@dataclass
class ResourceMonth:
    """Aggregate resource metrics for a single month."""
    month: str
    total_fte: float
    bench_count: float        # Projected bench (HC - allocated)
    utilization_pct: float    # allocated / total HC
    by_role: dict[str, float] = field(default_factory=dict)


@dataclass
class ResourceForecast:
    """Complete resource demand forecast."""
    months: list[ResourceMonth]
    role_forecasts: dict[str, list[RoleMonth]]   # role → monthly data
    hiring_gap: dict[str, int]                    # role → hire count needed
    total_fte_12m: float
    avg_monthly_fte: float
    avg_utilization: float
    method: str


# ── Core Model ──────────────────────────────────────────────────────────────

def forecast_resources(
    db: Session,
    pipeline: PipelineResult,
    horizon: int = 12,
) -> ResourceForecast:
    """
    Generate 12-month resource demand forecast by role.
    
    Args:
        db: SQLAlchemy session
        pipeline: Pipeline calculation result
        horizon: Months to forecast
    
    Returns:
        ResourceForecast with per-role monthly FTE predictions
    """
    # Step 1: Get historical monthly FTE by role (last 18 months)
    hist_fte = _get_historical_fte_by_role(db, months_back=18)

    # Step 2: Get current headcount by role
    role_headcount = _get_role_headcount(db)

    # Step 3: Get overall headcount for utilization calc
    headcount = get_monthly_headcount(db, months_back=12)
    current_hc = max(headcount.values()) if headcount else 665

    # Step 4: Extract pipeline demand by role
    pipeline_by_role = _extract_pipeline_role_demand(pipeline)

    # Step 5: Generate forecast months
    today = date.today()
    forecast_months = []
    for i in range(horizon):
        m = today.month + i + 1
        y = today.year
        while m > 12:
            m -= 12
            y += 1
        forecast_months.append(f"{y:04d}-{m:02d}")

    # Step 6: Forecast each role
    all_roles = sorted(set(list(hist_fte.keys()) + list(pipeline_by_role.keys())))
    # Focus on top roles by recent FTE
    role_recent_fte = {}
    for role, monthly in hist_fte.items():
        if monthly:
            recent = list(monthly.values())[-6:]
            role_recent_fte[role] = np.mean(recent) if recent else 0
    top_roles = sorted(role_recent_fte.keys(), key=lambda r: -role_recent_fte.get(r, 0))[:15]

    # Add any pipeline roles not in top list
    for role in pipeline_by_role:
        if role not in top_roles:
            top_roles.append(role)

    role_forecasts: dict[str, list[RoleMonth]] = {}
    monthly_totals: dict[str, float] = {m: 0.0 for m in forecast_months}

    for role in top_roles:
        role_months: list[RoleMonth] = []
        hist_series = hist_fte.get(role, {})
        pipeline_role = pipeline_by_role.get(role, {})

        # Forecast historical trend
        hist_forecast = _forecast_role_trend(hist_series, horizon)

        for i, month in enumerate(forecast_months):
            hist_val = hist_forecast[i] if i < len(hist_forecast) else (hist_forecast[-1] if hist_forecast else 0)
            pipe_val = pipeline_role.get(month, 0.0)

            # Blend: historical trend + pipeline signal
            # Pipeline is additive (it's NEW demand on top of existing)
            blended = max(0, hist_val + pipe_val * 0.5)

            role_months.append(RoleMonth(
                month=month,
                role=role,
                historical_fte=round(hist_val, 2),
                pipeline_fte=round(pipe_val, 2),
                blended_fte=round(blended, 2),
            ))
            monthly_totals[month] += blended

        role_forecasts[role] = role_months

    # Step 7: Build monthly aggregates
    # Estimate headcount growth
    hc_growth = _estimate_hc_growth(headcount)
    months_data: list[ResourceMonth] = []

    for i, month in enumerate(forecast_months):
        total_fte = monthly_totals[month]
        projected_hc = current_hc + hc_growth * (i + 1)
        bench = max(0, projected_hc - total_fte)
        utilization = total_fte / projected_hc if projected_hc > 0 else 0

        by_role = {
            role: role_forecasts[role][i].blended_fte
            for role in top_roles
            if role in role_forecasts and i < len(role_forecasts[role])
        }

        months_data.append(ResourceMonth(
            month=month,
            total_fte=round(total_fte, 1),
            bench_count=round(bench, 0),
            utilization_pct=round(utilization * 100, 1),
            by_role=by_role,
        ))

    # Step 8: Hiring gap per role
    utilization_target = 0.80  # 80% target utilization
    hiring_gap: dict[str, int] = {}
    for role in top_roles:
        if role not in role_forecasts:
            continue
        peak_demand = max((rm.blended_fte for rm in role_forecasts[role]), default=0)
        current_supply = role_headcount.get(role, 0) * utilization_target
        gap = peak_demand - current_supply
        if gap > 1:
            hiring_gap[role] = int(np.ceil(gap))

    # Summary
    total_fte_12m = sum(m.total_fte for m in months_data)
    avg_monthly = total_fte_12m / horizon if horizon > 0 else 0
    avg_util = np.mean([m.utilization_pct for m in months_data]) if months_data else 0

    return ResourceForecast(
        months=months_data,
        role_forecasts=role_forecasts,
        hiring_gap=hiring_gap,
        total_fte_12m=round(total_fte_12m, 1),
        avg_monthly_fte=round(avg_monthly, 1),
        avg_utilization=round(avg_util, 1),
        method="Holt trend per role + pipeline demand overlay",
    )


# ── Historical FTE Query ────────────────────────────────────────────────────

def _get_historical_fte_by_role(
    db: Session,
    months_back: int = 18,
) -> dict[str, dict[str, float]]:
    """
    Get monthly billable FTE by canonical role for the last N months.
    Returns: { role: { YYYY-MM: fte } }
    """
    today = date.today()
    start_year = today.year
    start_month = today.month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = date(start_year, start_month, 1)

    rows = db.execute(text("""
        WITH months AS (
            SELECT generate_series(
                CAST(:start_d AS date),
                CURRENT_DATE,
                '1 month'::interval
            )::date AS month_start
        )
        SELECT TO_CHAR(m.month_start, 'YYYY-MM') AS month,
               e.canonical_role AS role,
               ROUND(SUM(a.allocation_pct / 100.0)::numeric, 2) AS fte
        FROM months m
        JOIN allocations a ON a.is_active_version = true
            AND a.is_active = true
            AND a.resourcing_status = 'BILLABLE'
            AND a.start_date <= m.month_start + INTERVAL '1 month' - INTERVAL '1 day'
            AND (a.end_date IS NULL OR a.end_date >= m.month_start)
        JOIN employees e ON e.employee_id = a.employee_id
            AND e.is_active_version = true
            AND e.canonical_role IS NOT NULL
            AND e.canonical_role != 'nan'
        JOIN projects p ON p.project_id = a.project_id
            AND p.is_active_version = true
            AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
        GROUP BY m.month_start, e.canonical_role
        ORDER BY m.month_start, fte DESC
    """), {"start_d": start_date.isoformat()}).fetchall()

    result: dict[str, dict[str, float]] = {}
    for r in rows:
        role = r.role
        if role not in result:
            result[role] = {}
        result[role][r.month] = float(r.fte)

    return result


def _get_role_headcount(db: Session) -> dict[str, int]:
    """Get current active headcount by canonical role."""
    rows = db.execute(text("""
        SELECT canonical_role, COUNT(*) AS hc
        FROM employees
        WHERE is_active_version = true
          AND account_status = true
          AND date_of_resignation IS NULL
          AND canonical_role IS NOT NULL
          AND canonical_role != 'nan'
        GROUP BY canonical_role
        ORDER BY hc DESC
    """)).fetchall()

    return {r.canonical_role: int(r.hc) for r in rows}


# ── Pipeline Demand Extraction ──────────────────────────────────────────────

def _extract_pipeline_role_demand(
    pipeline: PipelineResult,
) -> dict[str, dict[str, float]]:
    """
    Extract per-role per-month FTE from pipeline.
    Maps pipeline roles back to canonical roles.
    Returns: { canonical_role: { YYYY-MM: weighted_fte } }
    """
    # Pipeline uses rate-card role names; map to canonical roles
    _PIPELINE_TO_CANONICAL = {
        "Associate Partner": "Associate Partner",
        "Principal": "Principal",
        "Manager": "Manager",
        "Senior Consultant": "Senior Consultant",
        "Consultant": "Consultant",
        "Senior Associate Consultant": "Senior Associate Consultant",
        "Associate Consultant": "Associate Consultant",
        "Senior Solutions Consultant": "Senior Solutions Consultant",
        "Solutions Consultant": "Solutions Consultant",
        "Solutions Enabler": "Solutions Enabler",
        "Senior Software Engineer": "Senior Software Engineer",
        "Software Engineer": "Software Engineer",
        "Principal Technology Architect": "Principal Technology Architect",
        "Technical Solutions Architect": "Technology Solutions Architect",
    }

    demand: dict[str, dict[str, float]] = {}

    for month, pm in pipeline.months.items():
        for role, fte in pm.by_role.items():
            canonical = _PIPELINE_TO_CANONICAL.get(role, role)
            if canonical not in demand:
                demand[canonical] = {}
            demand[canonical][month] = demand[canonical].get(month, 0) + fte

    return demand


# ── Forecasting ─────────────────────────────────────────────────────────────

def _forecast_role_trend(
    hist_series: dict[str, float],
    horizon: int,
) -> list[float]:
    """Forecast a single role's FTE using Holt's linear trend."""
    if not hist_series or len(hist_series) < 3:
        # Not enough data — return last known value or 0
        if hist_series:
            last_val = list(hist_series.values())[-1]
            return [last_val] * horizon
        return [0.0] * horizon

    values = np.array(list(hist_series.values()), dtype=float)

    try:
        model = ExponentialSmoothing(
            values,
            trend="add",
            damped_trend=True,
            seasonal=None,
        ).fit(optimized=True)
        forecast = model.forecast(horizon)
        return [max(0, float(v)) for v in forecast]
    except Exception:
        # Fallback: linear extrapolation
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)
        forecast = np.polyval(slope, np.arange(len(values), len(values) + horizon))
        return [max(0, float(v)) for v in forecast]


def _estimate_hc_growth(headcount: dict[str, int]) -> float:
    """Estimate monthly headcount growth."""
    if len(headcount) < 3:
        return 5.0
    sorted_hc = sorted(headcount.items())
    recent = sorted_hc[-6:]
    values = [v for _, v in recent]
    changes = [values[i+1] - values[i] for i in range(len(values)-1)]
    return float(np.median(changes)) if changes else 5.0


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal
    from ml.pipeline_calc import calculate_pipeline_revenue

    db = SessionLocal()
    try:
        print("=== Resource Demand Model ===\n")

        pipeline = calculate_pipeline_revenue(db, future_only=False)
        result = forecast_resources(db, pipeline, horizon=12)

        print(f"Method: {result.method}")
        print(f"12-month total FTE demand: {result.total_fte_12m:.0f}")
        print(f"Monthly average FTE: {result.avg_monthly_fte:.1f}")
        print(f"Average utilization: {result.avg_utilization:.1f}%")
        print()

        # Monthly summary
        print(f"{'Month':<10} {'Total FTE':>10} {'Bench':>7} {'Util%':>6}")
        print("-" * 36)
        for m in result.months[:6]:
            print(f"{m.month:<10} {m.total_fte:>10.1f} {m.bench_count:>7.0f} {m.utilization_pct:>5.1f}%")
        print("  ...")
        for m in result.months[-3:]:
            print(f"{m.month:<10} {m.total_fte:>10.1f} {m.bench_count:>7.0f} {m.utilization_pct:>5.1f}%")

        # Top roles
        print(f"\n{'Role':<30} {'Avg FTE':>8} {'Peak':>6}")
        print("-" * 48)
        role_avgs = []
        for role, months in result.role_forecasts.items():
            avg = np.mean([m.blended_fte for m in months])
            peak = max(m.blended_fte for m in months)
            role_avgs.append((role, avg, peak))
        role_avgs.sort(key=lambda x: -x[1])
        for role, avg, peak in role_avgs[:10]:
            print(f"{role:<30} {avg:>8.1f} {peak:>6.1f}")

        # Hiring gap
        if result.hiring_gap:
            print("\n=== Hiring Gap (demand > current supply × 80%) ===")
            for role, gap in sorted(result.hiring_gap.items(), key=lambda x: -x[1]):
                print(f"  {role}: +{gap} hires needed")

    finally:
        db.close()
