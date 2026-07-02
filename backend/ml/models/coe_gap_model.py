"""
COE Supply/Demand Gap Model — Forecast headcount availability vs pipeline demand.

Extends the Excel's COE_Supply_Demand sheet with:
  - Dynamic supply projection (headcount growth + attrition modeling)
  - COE inference for untagged employees (from skills data)
  - 12-month horizon (vs Excel's static 6-month)
  - Per-month gap = supply - demand

Supply = active headcount with COE tag (or inferred) minus already-billable
Demand = pipeline role requests mapped to COE (from pipeline_calc FTE by COE)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..pipeline_calc import PipelineResult
from ..data_prep import get_monthly_headcount, get_monthly_attrition


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class COEMonthData:
    """Supply/demand for a single COE in a single month."""
    month: str
    coe: str
    total_headcount: int        # Active HC with this COE
    already_billable: int       # Currently allocated (billable)
    available_supply: int       # = total - already_billable
    projected_supply: float     # = available + projected growth - attrition
    demand_fte: float           # Pipeline demand (probability-weighted)
    gap: float                  # = projected_supply - demand (negative = shortfall)


@dataclass
class COEGapForecast:
    """Complete COE supply/demand forecast."""
    coes: dict[str, list[COEMonthData]]     # coe → monthly data
    total_gap_by_coe: dict[str, float]      # coe → 12-month total gap
    total_demand_by_coe: dict[str, float]   # coe → 12-month total demand
    total_supply_by_coe: dict[str, float]   # coe → current supply
    hiring_needs: dict[str, int]            # coe → recommended hires
    coverage_note: str                      # Data quality note
    method: str


# ── Core Model ──────────────────────────────────────────────────────────────

def forecast_coe_gap(
    db: Session,
    pipeline: PipelineResult,
    horizon: int = 12,
) -> COEGapForecast:
    """
    Forecast COE-level supply vs demand gap for the next N months.
    
    Args:
        db: SQLAlchemy session
        pipeline: Pipeline calculation result with COE breakdown
        horizon: Forecast horizon in months
    
    Returns:
        COEGapForecast with per-COE monthly supply/demand/gap
    """
    # Step 1: Get current COE headcount (supply side)
    coe_headcount = _get_coe_headcount(db)
    coe_billable = _get_coe_billable(db)

    # Step 2: Get demand from pipeline (by COE by month)
    pipeline_demand = _extract_pipeline_demand(pipeline, horizon)

    # Step 3: Estimate headcount growth trend
    headcount = get_monthly_headcount(db, months_back=12)
    monthly_growth = _estimate_growth_rate(headcount)
    attrition_rate = _estimate_attrition_rate(db)

    # Step 4: Project supply forward for each COE
    all_coes = sorted(set(list(coe_headcount.keys()) + list(pipeline_demand.keys())))

    # Ensure we have the key COEs from the pipeline
    for coe in ["Data Engineering", "Techops & Automation", "Data Science & AI",
                "Full Stack", "Power BI & Consulting", "Consulting", "GTM"]:
        if coe not in all_coes:
            all_coes.append(coe)
    all_coes = sorted(set(all_coes))

    # Generate forecast months
    today = date.today()
    forecast_months = []
    for i in range(horizon):
        m = today.month + i + 1
        y = today.year
        while m > 12:
            m -= 12
            y += 1
        forecast_months.append(f"{y:04d}-{m:02d}")

    # Step 5: Build per-COE per-month data
    coes: dict[str, list[COEMonthData]] = {}
    total_gap: dict[str, float] = {}
    total_demand: dict[str, float] = {}
    total_supply: dict[str, float] = {}

    for coe in all_coes:
        current_hc = coe_headcount.get(coe, 0)
        current_billable = coe_billable.get(coe, 0)
        current_available = max(0, current_hc - current_billable)

        coe_months: list[COEMonthData] = []
        cum_gap = 0.0
        cum_demand = 0.0

        for i, month in enumerate(forecast_months):
            # Project supply: available grows with company growth, adjusted for attrition
            # Each COE gets proportional share of overall growth
            coe_share = current_hc / max(sum(coe_headcount.values()), 1)
            monthly_hc_growth = monthly_growth * coe_share
            projected_available = current_available + monthly_hc_growth * (i + 1)
            projected_available = max(0, projected_available * (1 - attrition_rate * (i + 1) / 12))

            # Get demand for this month
            demand = pipeline_demand.get(coe, {}).get(month, 0.0)

            # Gap
            gap = projected_available - demand

            coe_months.append(COEMonthData(
                month=month,
                coe=coe,
                total_headcount=current_hc,
                already_billable=current_billable,
                available_supply=current_available,
                projected_supply=round(projected_available, 1),
                demand_fte=round(demand, 2),
                gap=round(gap, 1),
            ))

            cum_gap += gap
            cum_demand += demand

        coes[coe] = coe_months
        total_gap[coe] = round(cum_gap, 1)
        total_demand[coe] = round(cum_demand, 1)
        total_supply[coe] = current_available

    # Step 6: Hiring recommendations
    hiring_needs: dict[str, int] = {}
    for coe in all_coes:
        # If total gap is negative, that's how many people we need
        if total_gap[coe] < -1:
            # Peak demand minus available = hiring need
            peak_demand = max((m.demand_fte for m in coes[coe]), default=0)
            available = total_supply.get(coe, 0)
            needed = max(0, int(np.ceil(peak_demand - available)))
            if needed > 0:
                hiring_needs[coe] = needed

    # Coverage note
    total_tagged = sum(coe_headcount.values())
    total_active = sum(headcount.values()) // len(headcount) if headcount else 665
    coverage_note = (
        f"{total_tagged} of ~{total_active} active employees have COE tags. "
        f"Supply estimates may undercount actual availability."
    )

    return COEGapForecast(
        coes=coes,
        total_gap_by_coe=total_gap,
        total_demand_by_coe=total_demand,
        total_supply_by_coe=total_supply,
        hiring_needs=hiring_needs,
        coverage_note=coverage_note,
        method="Dynamic COE supply projection with pipeline demand overlay",
    )


# ── Supply-Side Queries ─────────────────────────────────────────────────────

def _get_coe_headcount(db: Session) -> dict[str, int]:
    """
    Get active headcount by COE.
    Uses employee_skills primary COE (most common skill COE per employee).
    """
    rows = db.execute(text("""
        SELECT coe, COUNT(DISTINCT employee_id) AS hc
        FROM (
            SELECT employee_id,
                   COALESCE(coe, 'Unknown') AS coe,
                   ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY COUNT(*) DESC) AS rn
            FROM employee_skills
            WHERE employee_id IN (
                SELECT employee_id FROM employees
                WHERE is_active_version = true AND account_status = true
                  AND date_of_resignation IS NULL
            )
            AND coe IS NOT NULL AND TRIM(coe) != ''
            GROUP BY employee_id, coe
        ) sub
        WHERE rn = 1
        GROUP BY coe
        ORDER BY hc DESC
    """)).fetchall()

    # Normalize COE names to match pipeline mapping
    coe_map = _build_coe_normalization_map()
    result: dict[str, int] = {}
    for r in rows:
        normalized = coe_map.get(r.coe.lower().strip(), r.coe)
        result[normalized] = result.get(normalized, 0) + int(r.hc)

    return result


def _get_coe_billable(db: Session) -> dict[str, int]:
    """
    Get already-billable headcount by COE.
    Employees currently on billable allocations (non-BAU).
    """
    rows = db.execute(text("""
        SELECT sub.coe, COUNT(DISTINCT sub.employee_id) AS hc
        FROM (
            SELECT es.employee_id,
                   COALESCE(es.coe, 'Unknown') AS coe,
                   ROW_NUMBER() OVER (PARTITION BY es.employee_id ORDER BY COUNT(*) DESC) AS rn
            FROM employee_skills es
            WHERE es.employee_id IN (
                SELECT DISTINCT a.employee_id
                FROM allocations a
                JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
                WHERE a.is_active_version = true AND a.is_active = true
                  AND a.resourcing_status = 'BILLABLE'
                  AND (a.end_date IS NULL OR a.end_date >= CURRENT_DATE)
                  AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
            )
            AND es.coe IS NOT NULL AND TRIM(es.coe) != ''
            GROUP BY es.employee_id, es.coe
        ) sub
        WHERE rn = 1
        GROUP BY sub.coe
        ORDER BY hc DESC
    """)).fetchall()

    coe_map = _build_coe_normalization_map()
    result: dict[str, int] = {}
    for r in rows:
        normalized = coe_map.get(r.coe.lower().strip(), r.coe)
        result[normalized] = result.get(normalized, 0) + int(r.hc)

    return result


# ── Demand-Side Extraction ──────────────────────────────────────────────────

def _extract_pipeline_demand(
    pipeline: PipelineResult,
    horizon: int,
) -> dict[str, dict[str, float]]:
    """
    Extract per-COE per-month FTE demand from pipeline result.
    Returns: { coe: { YYYY-MM: weighted_fte } }
    """
    demand: dict[str, dict[str, float]] = {}

    for month, pm in pipeline.months.items():
        for coe, fte in pm.by_coe.items():
            if coe not in demand:
                demand[coe] = {}
            demand[coe][month] = fte  # Already probability-weighted

    return demand


# ── Growth & Attrition Estimation ───────────────────────────────────────────

def _estimate_growth_rate(headcount: dict[str, int]) -> float:
    """Estimate monthly headcount growth from recent data."""
    if len(headcount) < 3:
        return 5.0  # Default: 5 people/month

    sorted_hc = sorted(headcount.items())
    recent = sorted_hc[-6:]  # Last 6 months
    if len(recent) < 2:
        return 5.0

    values = [v for _, v in recent]
    changes = [values[i+1] - values[i] for i in range(len(values)-1)]
    return float(np.median(changes))


def _estimate_attrition_rate(db: Session) -> float:
    """Estimate annual attrition rate from recent resignations."""
    try:
        row = db.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE date_of_resignation >= CURRENT_DATE - INTERVAL '12 months') AS resigned_12m,
                (SELECT COUNT(*) FROM employees
                 WHERE is_active_version = true AND account_status = true) AS total_active
        FROM employees
        WHERE is_active_version = true AND date_of_resignation IS NOT NULL
        """)).fetchone()

        if row and row.total_active > 0:
            return float(row.resigned_12m or 0) / float(row.total_active)
        return 0.05  # Default 5% annual attrition
    except Exception:
        return 0.05


# ── COE Normalization ───────────────────────────────────────────────────────

def _build_coe_normalization_map() -> dict[str, str]:
    """
    Map DB COE names (from employee_skills) to pipeline COE names.
    DB uses: 'data engineering', 'bi and reporting', etc.
    Pipeline uses: 'Data Engineering', 'Power BI & Consulting', etc.
    """
    return {
        "data engineering": "Data Engineering",
        "bi and reporting": "Power BI & Consulting",
        "consulting": "Consulting",
        "data science & ml": "Data Science & AI",
        "data science": "Data Science & AI",
        "full stack engineering": "Full Stack",
        "full stack": "Full Stack",
        "analytical engineering": "Data Engineering",
        "techops and automation": "Techops & Automation",
        "techops & automation": "Techops & Automation",
        "software development and llms": "Full Stack",
        "gen ai": "Data Science & AI",
        "power bi & consulting": "Power BI & Consulting",
        "gtm": "GTM",
    }


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal
    from ml.pipeline_calc import calculate_pipeline_revenue

    db = SessionLocal()
    try:
        print("=== COE Supply/Demand Gap Model ===\n")

        pipeline = calculate_pipeline_revenue(db, future_only=False)
        result = forecast_coe_gap(db, pipeline, horizon=12)

        print(f"Method: {result.method}")
        print(f"Note: {result.coverage_note}")
        print()

        # Summary table
        print(f"{'COE':<25} {'Supply':>7} {'Demand':>8} {'Gap(12m)':>9} {'Hire':>5}")
        print("-" * 58)
        for coe in sorted(result.coes.keys(), key=lambda c: result.total_gap_by_coe.get(c, 0)):
            supply = result.total_supply_by_coe.get(coe, 0)
            demand = result.total_demand_by_coe.get(coe, 0)
            gap = result.total_gap_by_coe.get(coe, 0)
            hire = result.hiring_needs.get(coe, 0)
            gap_str = f"{gap:+.1f}" if gap != 0 else "0.0"
            print(f"{coe:<25} {supply:>7} {demand:>8.1f} {gap_str:>9} {hire:>5}")

        # Monthly detail for worst COEs
        print("\n=== Monthly Gap (Top 3 shortfalls, first 6 months) ===")
        worst_coes = sorted(result.total_gap_by_coe.items(), key=lambda x: x[1])[:3]
        for coe, _ in worst_coes:
            months_data = result.coes[coe][:6]
            print(f"\n  {coe}:")
            print(f"    {'Month':<10} {'Supply':>7} {'Demand':>8} {'Gap':>7}")
            for m in months_data:
                gap_str = f"{m.gap:+.1f}"
                print(f"    {m.month:<10} {m.projected_supply:>7.1f} {m.demand_fte:>8.1f} {gap_str:>7}")

        # Hiring recommendations
        if result.hiring_needs:
            print("\n=== Hiring Recommendations ===")
            for coe, count in sorted(result.hiring_needs.items(), key=lambda x: -x[1]):
                print(f"  {coe}: {count} hires needed")

    finally:
        db.close()
