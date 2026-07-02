"""
Historical Revenue Reconstruction — Build 30-month revenue time series
from allocations × rate card × working days.

Logic:
  For each month in the 30-month window:
    1. Find all BILLABLE allocations active in that month (non-BAU)
    2. Map each employee's canonical_role + location → rate card day rate
    3. Compute: revenue = day_rate × overlap_working_days × allocation_pct
    4. Sum across all allocations to get monthly total

Also produces:
  - Monthly FTE by role
  - Monthly headcount
  - Monthly project count
  - Revenue by location and role breakdown
"""

from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .rate_card import RateEntry, load_rate_card, _normalize_location
from .proration import _count_working_days, working_days_in_month


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class MonthlyRevenue:
    """Reconstructed revenue and metrics for a single month."""
    month: str                          # YYYY-MM
    total_revenue_usd: float = 0.0
    billable_fte: float = 0.0
    headcount: int = 0                  # unique employees with any allocation
    project_count: int = 0              # unique projects
    by_role: dict[str, float] = field(default_factory=dict)   # role → revenue
    by_location: dict[str, float] = field(default_factory=dict)  # loc → revenue
    by_coe: dict[str, float] = field(default_factory=dict)    # coe → FTE


@dataclass
class HistoricalData:
    """Complete historical dataset for model training."""
    months: list[MonthlyRevenue]
    start_month: str
    end_month: str
    total_months: int
    # Actuals from Revenue_Trend sheet (Jan-Jun 2026)
    actuals: dict[str, float] = field(default_factory=dict)
    # Calibration: median ratio of actual / reconstructed (for months where both exist)
    calibration_factor: float = 1.0

    def get_calibrated_series(self) -> list[tuple[str, float]]:
        """
        Return calibrated monthly revenue series.
        Uses actual where available, otherwise uses revenue-per-FTE estimation.
        
        Strategy:
        - For months with actuals: use actuals directly
        - For months without actuals: estimate using avg revenue-per-FTE
          from months where we have both actual and FTE data
        """
        # Compute revenue-per-FTE from months with both actual + FTE data
        rev_per_fte_samples = []
        for m in self.months:
            if m.month in self.actuals and m.billable_fte > 0:
                rev_per_fte_samples.append(self.actuals[m.month] / m.billable_fte)

        # Use median revenue-per-FTE as the estimator
        if rev_per_fte_samples:
            rev_per_fte_samples.sort()
            mid = len(rev_per_fte_samples) // 2
            rev_per_fte = rev_per_fte_samples[mid]
        else:
            # Fallback: use calibration factor on raw reconstruction
            rev_per_fte = None

        series = []
        for m in self.months:
            if m.month in self.actuals:
                series.append((m.month, self.actuals[m.month]))
            elif rev_per_fte and m.billable_fte > 0:
                # Estimate revenue from FTE × typical revenue-per-FTE
                estimated = m.billable_fte * rev_per_fte
                series.append((m.month, round(estimated, 2)))
            else:
                # Last resort: use raw reconstruction × calibration
                series.append((m.month, round(m.total_revenue_usd * self.calibration_factor, 2)))
        return series


# ── Role → Rate Mapping ─────────────────────────────────────────────────────

# Map employee canonical_role → rate card role name
# (handles naming differences between HR system and rate card)
_CANONICAL_TO_RATE_ROLE: dict[str, str] = {
    # Direct matches
    "Associate Consultant": "Associate Consultant",
    "Associate Partner": "Associate Partner",
    "Consultant": "Consultant",
    "Manager": "Manager",
    "Principal": "Principal",
    "Principal Technology Architect": "Principal Technology Architect",
    "Senior Associate Consultant": "Senior Associate Consultant",
    "Senior Consultant": "Senior Consultant",
    "Senior Software Engineer": "Senior Software Engineer",
    "Senior Solutions Consultant": "Senior Solutions Consultant",
    "Software Engineer": "Software Engineer",
    "Solutions Consultant": "Solutions Consultant",
    "Solutions Enabler": "Solutions Enabler",
    "Technical Solutions Architect": "Technical Solutions Architect",
    "Technology Solutions Architect": "Technical Solutions Architect",
    # Approximate mappings
    "Trainee Software Engineer": "Software Engineer",  # Closest available
    "Principal Architect": "Principal Technology Architect",
    "Partner": "Associate Partner",  # No separate Partner rate
    "Leadership": "Associate Partner",
    # Non-billable roles (map to None → skip)
}

# Location mapping: employee location → rate card location
_LOCATION_MAP: dict[str, str] = {
    "Chennai": "IN",
    "London": "UK",
    "New York": "USA",
}


def _map_to_rate_key(canonical_role: str, location: str) -> Optional[tuple[str, str]]:
    """Map an employee's role + location to a rate card key."""
    # Map role
    rate_role = _CANONICAL_TO_RATE_ROLE.get(canonical_role)
    if not rate_role:
        # Try case-insensitive match
        for k, v in _CANONICAL_TO_RATE_ROLE.items():
            if k.lower() == canonical_role.lower():
                rate_role = v
                break
    if not rate_role:
        return None

    # Map location
    rate_loc = _LOCATION_MAP.get(location)
    if not rate_loc:
        rate_loc = _normalize_location(location) if location else None
    if not rate_loc:
        return None

    return (rate_role, rate_loc)


# ── Core Reconstruction ─────────────────────────────────────────────────────

def reconstruct_revenue(
    db: Session,
    months_back: int = 30,
    end_date: Optional[date] = None,
) -> HistoricalData:
    """
    Reconstruct monthly revenue from allocation data × rate card.
    
    For each month, finds all BILLABLE allocations active in that month,
    maps employee role+location to a day rate, and computes:
      revenue = day_rate × working_days_in_overlap × (allocation_pct / 100)
    
    Args:
        db: SQLAlchemy session
        months_back: Number of months of history to reconstruct
        end_date: End date for the reconstruction window (default: today)
    
    Returns:
        HistoricalData with monthly revenue series
    """
    if end_date is None:
        end_date = date.today()

    # Load rate card
    rates = load_rate_card()

    # Calculate start date
    start_year = end_date.year
    start_month = end_date.month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = date(start_year, start_month, 1)

    # Query: all billable allocations with employee info in the window
    # This is a single query that gets all allocations that overlap with our window
    query = text("""
        SELECT
            a.employee_id,
            a.project_id,
            a.allocation_pct,
            a.start_date AS alloc_start,
            a.end_date AS alloc_end,
            e.canonical_role,
            e.location,
            e.employee_id
        FROM allocations a
        JOIN employees e ON e.employee_id = a.employee_id AND e.is_active_version = true
        JOIN projects p ON p.project_id = a.project_id AND p.is_active_version = true
        WHERE a.is_active_version = true
          AND a.is_active = true
          AND a.resourcing_status = 'BILLABLE'
          AND LOWER(COALESCE(p.type_of_project, '')) != 'bau activity'
          AND a.start_date <= :window_end
          AND (a.end_date IS NULL OR a.end_date >= :window_start)
          AND e.canonical_role IS NOT NULL
          AND e.canonical_role != 'nan'
    """)

    rows = db.execute(query, {
        "window_start": start_date,
        "window_end": end_date,
    }).fetchall()

    # Process each month
    monthly_data: dict[str, MonthlyRevenue] = {}
    current = start_date

    while current <= end_date:
        month_key = current.strftime("%Y-%m")
        month_first = current
        month_last = date(
            current.year,
            current.month,
            calendar.monthrange(current.year, current.month)[1],
        )

        month_entry = MonthlyRevenue(month=month_key)
        employees_in_month = set()
        projects_in_month = set()

        for row in rows:
            alloc_start = row.alloc_start
            alloc_end = row.alloc_end or date(2099, 12, 31)  # open-ended
            alloc_pct = float(row.allocation_pct or 0) / 100.0

            # Check if this allocation overlaps with this month
            if alloc_start > month_last or alloc_end < month_first:
                continue

            # Calculate overlap
            overlap_start = max(alloc_start, month_first)
            overlap_end = min(alloc_end, month_last)
            overlap_working = _count_working_days(overlap_start, overlap_end)
            total_working = working_days_in_month(current.year, current.month)

            if overlap_working <= 0 or total_working <= 0:
                continue

            # Map to rate
            rate_key = _map_to_rate_key(row.canonical_role, row.location)
            if not rate_key:
                continue

            rate_entry = rates.get(rate_key)
            if not rate_entry:
                continue

            # Compute revenue for this allocation in this month
            revenue = rate_entry.day_rate_usd * overlap_working * alloc_pct
            fte = alloc_pct * (overlap_working / total_working)

            # Accumulate
            month_entry.total_revenue_usd += revenue
            month_entry.billable_fte += fte
            employees_in_month.add(row.employee_id)
            projects_in_month.add(row.project_id)

            # By role
            role_name = rate_key[0]
            month_entry.by_role[role_name] = (
                month_entry.by_role.get(role_name, 0.0) + revenue
            )

            # By location
            loc_name = rate_key[1]
            month_entry.by_location[loc_name] = (
                month_entry.by_location.get(loc_name, 0.0) + revenue
            )

        month_entry.headcount = len(employees_in_month)
        month_entry.project_count = len(projects_in_month)
        month_entry.total_revenue_usd = round(month_entry.total_revenue_usd, 2)
        month_entry.billable_fte = round(month_entry.billable_fte, 4)

        monthly_data[month_key] = month_entry

        # Next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    # Sort by month
    sorted_months = [monthly_data[k] for k in sorted(monthly_data.keys())]

    # Load actuals from Revenue_Trend (Jan-Jun 2026)
    actuals = _load_revenue_actuals()

    # Compute calibration factor: actual / reconstructed for months where we have both
    calibration_factors = []
    for month_key, actual_rev in actuals.items():
        if month_key in monthly_data and monthly_data[month_key].total_revenue_usd > 0:
            factor = actual_rev / monthly_data[month_key].total_revenue_usd
            calibration_factors.append(factor)

    # Use median calibration factor to adjust historical estimates
    calibration = 1.0
    if calibration_factors:
        calibration_factors.sort()
        mid = len(calibration_factors) // 2
        calibration = calibration_factors[mid]  # median

    return HistoricalData(
        months=sorted_months,
        start_month=sorted_months[0].month if sorted_months else "",
        end_month=sorted_months[-1].month if sorted_months else "",
        total_months=len(sorted_months),
        actuals=actuals,
        calibration_factor=calibration,
    )


# ── Revenue Actuals (from Excel) ───────────────────────────────────────────

def _load_revenue_actuals() -> dict[str, float]:
    """
    Load known actual revenue from Revenue_Trend sheet (Jan-Jun 2026).
    Returns dict: YYYY-MM → revenue USD.
    """
    from pathlib import Path
    import openpyxl

    filepath = Path(__file__).resolve().parent.parent.parent / "docs" / "pricing" / "Cluster_Revenue_COE_Forecast.xlsx"
    if not filepath.exists():
        return {}

    try:
        wb = openpyxl.load_workbook(filepath, data_only=True, read_only=True)
        ws = wb["Revenue_Trend"]

        actuals: dict[str, float] = {}
        # Rows 4-9: Jan-Jun 2026, Col C = Actual Revenue
        month_map = {
            "Jan-2026": "2026-01",
            "Feb-2026": "2026-02",
            "Mar-2026": "2026-03",
            "Apr-2026": "2026-04",
            "May-2026": "2026-05",
            "Jun-2026": "2026-06",
        }

        for row in ws.iter_rows(min_row=4, max_row=15, values_only=True):
            month_label = row[0]
            actual = row[2]  # Col C = Actual Revenue
            if month_label and actual:
                month_key = month_map.get(str(month_label).strip())
                if month_key:
                    actuals[month_key] = float(actual)

        wb.close()
        return actuals
    except Exception:
        return {}


# ── Supplementary Queries ───────────────────────────────────────────────────

def get_monthly_headcount(
    db: Session,
    months_back: int = 30,
    end_date: Optional[date] = None,
) -> dict[str, int]:
    """Get monthly headcount (active employees) for the window."""
    if end_date is None:
        end_date = date.today()

    start_year = end_date.year
    start_month = end_date.month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = date(start_year, start_month, 1)

    try:
        rows = db.execute(text("""
            SELECT TO_CHAR(d, 'YYYY-MM') AS month,
                   (SELECT COUNT(*) FROM employees
                    WHERE is_active_version = true
                      AND account_status = true
                      AND date_of_join <= d + INTERVAL '1 month' - INTERVAL '1 day'
                      AND (date_of_resignation IS NULL OR date_of_resignation >= d)
                   ) AS headcount
            FROM generate_series(
                CAST(:start_d AS date),
                CAST(:end_d AS date),
                '1 month'::interval
            ) AS d
            ORDER BY d
        """), {"start_d": start_date.isoformat(), "end_d": end_date.isoformat()}).fetchall()
        return {r.month: int(r.headcount) for r in rows}
    except Exception:
        return {}


def get_monthly_project_starts(
    db: Session,
    months_back: int = 90,
    end_date: Optional[date] = None,
) -> dict[str, int]:
    """Get monthly new project starts (non-BAU) for time-series model."""
    if end_date is None:
        end_date = date.today()

    start_year = end_date.year
    start_month = end_date.month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = date(start_year, start_month, 1)

    try:
        rows = db.execute(text("""
            SELECT TO_CHAR(project_start_date, 'YYYY-MM') AS month, COUNT(*) AS cnt
            FROM projects
            WHERE is_active_version = true
              AND project_start_date IS NOT NULL
              AND project_start_date >= CAST(:start_d AS date)
              AND project_start_date <= CAST(:end_d AS date)
              AND LOWER(COALESCE(type_of_project, '')) != 'bau activity'
            GROUP BY month ORDER BY month
        """), {"start_d": start_date.isoformat(), "end_d": end_date.isoformat()}).fetchall()
        return {r.month: int(r.cnt) for r in rows}
    except Exception:
        return {}


def get_monthly_attrition(
    db: Session,
    months_back: int = 30,
    end_date: Optional[date] = None,
) -> dict[str, int]:
    """Get monthly resignations for attrition modeling."""
    if end_date is None:
        end_date = date.today()

    start_year = end_date.year
    start_month = end_date.month - months_back
    while start_month <= 0:
        start_month += 12
        start_year -= 1
    start_date = date(start_year, start_month, 1)

    try:
        rows = db.execute(text("""
            SELECT TO_CHAR(date_of_resignation, 'YYYY-MM') AS month, COUNT(*) AS cnt
            FROM employees
            WHERE is_active_version = true
              AND date_of_resignation IS NOT NULL
              AND date_of_resignation >= CAST(:start_d AS date)
              AND date_of_resignation <= CAST(:end_d AS date)
            GROUP BY month ORDER BY month
        """), {"start_d": start_date.isoformat(), "end_d": end_date.isoformat()}).fetchall()
        return {r.month: int(r.cnt) for r in rows}
    except Exception:
        return {}


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        print("=== Reconstructing 30-Month Revenue History ===\n")
        history = reconstruct_revenue(db, months_back=30)

        print(f"Window: {history.start_month} → {history.end_month} ({history.total_months} months)")
        print(f"Calibration factor: {history.calibration_factor:.4f}")
        print(f"(Median ratio of actual/reconstructed for Jan-Jun 2026)\n")

        print(f"{'Month':<10} {'Reconstructed':>14} {'Calibrated':>14} {'Actual':>14} {'FTE':>8} {'HC':>5}")
        print("-" * 70)

        calibrated_series = history.get_calibrated_series()
        for (month, cal_rev), m in zip(calibrated_series, history.months):
            actual = history.actuals.get(m.month)
            actual_str = f"${actual:,.0f}" if actual else "—"
            print(f"{m.month:<10} ${m.total_revenue_usd:>12,.0f} ${cal_rev:>12,.0f} {actual_str:>14} "
                  f"{m.billable_fte:>8.1f} {m.headcount:>5}")

        # Summary
        print(f"\nCalibrated revenue (training signal for model):")
        print(f"  Earliest: {calibrated_series[0][0]} = ${calibrated_series[0][1]:,.0f}")
        print(f"  Latest:   {calibrated_series[-1][0]} = ${calibrated_series[-1][1]:,.0f}")
        total_cal = sum(r for _, r in calibrated_series)
        print(f"  30-month total: ${total_cal:,.0f}")
        print(f"  Monthly average: ${total_cal / len(calibrated_series):,.0f}")

        # Also get supplementary data
        print("\n=== Monthly Headcount (last 6) ===")
        hc = get_monthly_headcount(db, months_back=30)
        if hc:
            for month in sorted(hc.keys())[-6:]:
                print(f"  {month}: {hc[month]}")
        else:
            print("  (query failed or no data)")

        print("\n=== Monthly Attrition (last 6) ===")
        attrition = get_monthly_attrition(db, months_back=30)
        if attrition:
            for month in sorted(attrition.keys())[-6:]:
                print(f"  {month}: {attrition[month]} resignations")
        else:
            print("  (no resignations in window)")

    finally:
        db.close()
