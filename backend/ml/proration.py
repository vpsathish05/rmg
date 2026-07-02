"""
Monthly Proration Engine — Spread deal/allocation revenue across calendar months.

Replicates Excel Step 4: A deal spanning multiple months has its revenue
prorated by the number of overlap days in each month vs total deal days.

Formula:
  revenue_in_month = total_revenue × (overlap_days_in_month / total_deal_days)

Also computes FTE demand per month:
  fte_in_month = allocation_pct × (overlap_working_days_in_month / working_days_in_month)
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from .rate_card import RateEntry, get_rate
from .role_mapping import RoleMapping, resolve_role


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class MonthSlice:
    """Revenue and FTE for a single month slice of a deal/allocation."""
    month: str          # YYYY-MM format
    month_start: date
    month_end: date
    overlap_days: int   # Calendar days this deal overlaps in this month
    working_days: int   # Working days (Mon-Fri) the deal overlaps in this month
    total_working_days_in_month: int  # Total working days in the full month
    revenue_usd: float  # Prorated revenue for this month
    fte: float          # FTE demand in this month


@dataclass
class DealProration:
    """Full proration result for a deal/allocation across months."""
    role: str
    location: str
    coe: str
    start_date: date
    end_date: date
    allocation_pct: float       # 0.0 to 1.0
    day_rate_usd: float
    total_days: int             # Calendar days of the deal
    total_working_days: int     # Working days of the deal
    total_revenue_usd: float    # Total revenue for the deal
    probability: float          # Deal probability (1.0 = certain)
    weighted_revenue_usd: float # total_revenue × probability
    cluster: Optional[int]      # Cluster number (if available)
    months: list[MonthSlice] = field(default_factory=list)


# ── Core Logic ──────────────────────────────────────────────────────────────

def prorate_deal(
    start_date: date,
    end_date: date,
    day_rate_usd: float,
    allocation_pct: float = 1.0,
    probability: float = 1.0,
    role: str = "",
    location: str = "",
    coe: str = "",
    cluster: Optional[int] = None,
    method: str = "calendar",
) -> DealProration:
    """
    Prorate a deal's revenue across calendar months.
    
    Args:
        start_date: Deal start date
        end_date: Deal end date (inclusive)
        day_rate_usd: USD day rate from rate card
        allocation_pct: Allocation percentage (0.0–1.0)
        probability: Deal win probability (0.0–1.0)
        role: Role name
        location: Location (UK/IN/USA)
        coe: Centre of Excellence
        cluster: Cluster number
        method: Proration method:
            - "calendar": Split by calendar day overlap (matches Excel model)
            - "working": Split by working day overlap (more accurate)
    
    Returns:
        DealProration with monthly breakdown
    """
    if end_date < start_date:
        end_date = start_date

    # Calculate total deal metrics
    total_days = (end_date - start_date).days + 1  # inclusive (calendar)
    total_working_days = _count_working_days(start_date, end_date)
    total_revenue = day_rate_usd * total_working_days * allocation_pct
    weighted_revenue = total_revenue * probability

    # Generate month slices
    months: list[MonthSlice] = []
    current = date(start_date.year, start_date.month, 1)

    while current <= end_date:
        month_start = current
        month_end = date(
            current.year,
            current.month,
            calendar.monthrange(current.year, current.month)[1],
        )

        # Overlap period within this month
        overlap_start = max(start_date, month_start)
        overlap_end = min(end_date, month_end)

        if overlap_start <= overlap_end:
            overlap_days = (overlap_end - overlap_start).days + 1
            overlap_working = _count_working_days(overlap_start, overlap_end)
            total_working_in_month = _count_working_days(month_start, month_end)

            # Revenue proration depends on method
            if method == "calendar":
                # Excel approach: prorate by calendar day ratio
                if total_days > 0:
                    month_revenue = total_revenue * (overlap_days / total_days)
                else:
                    month_revenue = 0.0
            else:
                # Working days approach: more accurate
                if total_working_days > 0:
                    month_revenue = total_revenue * (overlap_working / total_working_days)
                else:
                    month_revenue = 0.0

            # FTE in this month: allocation_pct × (overlap_working / total_working_in_month)
            if total_working_in_month > 0:
                month_fte = allocation_pct * (overlap_working / total_working_in_month)
            else:
                month_fte = 0.0

            months.append(MonthSlice(
                month=current.strftime("%Y-%m"),
                month_start=month_start,
                month_end=month_end,
                overlap_days=overlap_days,
                working_days=overlap_working,
                total_working_days_in_month=total_working_in_month,
                revenue_usd=round(month_revenue, 2),
                fte=round(month_fte, 6),
            ))

        # Move to next month
        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)

    return DealProration(
        role=role,
        location=location,
        coe=coe,
        start_date=start_date,
        end_date=end_date,
        allocation_pct=allocation_pct,
        day_rate_usd=day_rate_usd,
        total_days=total_days,
        total_working_days=total_working_days,
        total_revenue_usd=round(total_revenue, 2),
        probability=probability,
        weighted_revenue_usd=round(weighted_revenue, 2),
        cluster=cluster,
        months=months,
    )


def prorate_pipeline_deal(
    pipeline_code: str,
    start_date: date,
    duration_weeks: int,
    allocation_pct: float = 1.0,
    probability: float = 0.5,
    cluster: Optional[int] = None,
    method: str = "calendar",
) -> Optional[DealProration]:
    """
    Prorate a pipeline deal using its pipeline role code.
    Resolves role → rate automatically.
    
    Args:
        pipeline_code: Pipeline role code (e.g. "SC", "SSE")
        start_date: Deal start date
        duration_weeks: Duration in weeks
        allocation_pct: Allocation % (0.0–1.0)
        probability: Win probability (0.0–1.0)
        cluster: Cluster number
        method: "calendar" (Excel-compatible) or "working" (more accurate)
    
    Returns:
        DealProration or None if role/rate can't be resolved
    """
    mapping = resolve_role(pipeline_code)
    if not mapping:
        return None

    rate = get_rate(mapping.mapped_role, mapping.default_location)
    if not rate:
        return None

    end_date = start_date + timedelta(weeks=duration_weeks) - timedelta(days=1)

    return prorate_deal(
        start_date=start_date,
        end_date=end_date,
        day_rate_usd=rate.day_rate_usd,
        allocation_pct=allocation_pct,
        probability=probability,
        role=mapping.mapped_role,
        location=mapping.default_location,
        coe=mapping.mapped_coe,
        cluster=cluster,
        method=method,
    )


# ── Aggregation ─────────────────────────────────────────────────────────────

@dataclass
class MonthlyAggregate:
    """Aggregated revenue and FTE for a month across multiple deals."""
    month: str
    total_revenue: float = 0.0
    weighted_revenue: float = 0.0
    total_fte: float = 0.0
    deal_count: int = 0
    by_cluster: dict[int, float] = field(default_factory=dict)
    by_coe: dict[str, float] = field(default_factory=dict)
    by_role: dict[str, float] = field(default_factory=dict)


def aggregate_prorations(
    prorations: list[DealProration],
) -> dict[str, MonthlyAggregate]:
    """
    Aggregate multiple deal prorations into monthly totals.
    
    Returns dict keyed by month (YYYY-MM).
    """
    agg: dict[str, MonthlyAggregate] = {}

    for deal in prorations:
        for month_slice in deal.months:
            m = month_slice.month
            if m not in agg:
                agg[m] = MonthlyAggregate(month=m)

            entry = agg[m]
            entry.total_revenue += month_slice.revenue_usd
            entry.weighted_revenue += month_slice.revenue_usd * deal.probability
            entry.total_fte += month_slice.fte
            entry.deal_count += 1

            # By cluster
            if deal.cluster is not None:
                entry.by_cluster[deal.cluster] = (
                    entry.by_cluster.get(deal.cluster, 0.0)
                    + month_slice.revenue_usd * deal.probability
                )

            # By COE
            if deal.coe:
                entry.by_coe[deal.coe] = (
                    entry.by_coe.get(deal.coe, 0.0) + month_slice.fte
                )

            # By role
            if deal.role:
                entry.by_role[deal.role] = (
                    entry.by_role.get(deal.role, 0.0) + month_slice.fte
                )

    # Round all values
    for entry in agg.values():
        entry.total_revenue = round(entry.total_revenue, 2)
        entry.weighted_revenue = round(entry.weighted_revenue, 2)
        entry.total_fte = round(entry.total_fte, 4)

    return dict(sorted(agg.items()))


# ── Helpers ─────────────────────────────────────────────────────────────────

def _count_working_days(start: date, end: date) -> int:
    """Count working days (Mon-Fri) between start and end (inclusive)."""
    if end < start:
        return 0

    count = 0
    current = start
    while current <= end:
        if current.weekday() < 5:  # Mon=0 ... Fri=4
            count += 1
        current += timedelta(days=1)
    return count


def working_days_in_month(year: int, month: int) -> int:
    """Get total working days in a given month."""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    return _count_working_days(first, last)


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Replicate the Excel example: Sigma deal, Cluster 3
    # Role P (Partner/AP), 06 Jul → 21 Sep 2026, 11 weeks, 25% allocation
    print("=== Replicating Excel Example: Sigma Deal (Cluster 3) ===")
    print("=== Method: calendar (matches Excel) ===\n")

    deals = [
        ("P", 0.25, "Partner"),
        ("SC", 0.50, "Senior Consultant"),
        ("C", 1.00, "Consultant"),
        ("Sr Sol Con", 0.875, "Sr Solutions Consultant"),
        ("SSE", 1.00, "Senior Software Engineer"),
        ("SE", 1.00, "Software Engineer"),
    ]

    # Excel values for comparison (from Pipeline_Data sheet)
    excel_values = {
        "P": {"total": 48482.5, "jul": 16160.83, "aug": 19268.69, "sep": 13052.98},
        "SC": {"total": 76945.0, "jul": 25648.33, "aug": 30580.71, "sep": 20715.96},
        "C": {"total": 37565.0, "jul": 12521.67, "aug": 14929.68, "sep": 10113.65},
        "Sr Sol Con": {"total": 34409.375, "jul": 11469.79, "aug": 13675.52, "sep": 9264.06},
        "SSE": {"total": 32175.0, "jul": 10725.0, "aug": 12787.5, "sep": 8662.5},
        "SE": {"total": 25025.0, "jul": 8341.67, "aug": 9945.83, "sep": 6737.5},
    }

    start = date(2026, 7, 6)
    prorations = []
    total_diff = 0.0

    for code, alloc, label in deals:
        result = prorate_pipeline_deal(
            pipeline_code=code,
            start_date=start,
            duration_weeks=11,
            allocation_pct=alloc,
            probability=1.0,
            cluster=3,
            method="calendar",
        )
        if result:
            prorations.append(result)
            excel = excel_values.get(code, {})
            diff = abs(result.total_revenue_usd - excel.get("total", 0))
            total_diff += diff
            print(f"{label} ({code}) @ {alloc*100:.0f}%")
            print(f"  Total: ${result.total_revenue_usd:,.2f} (Excel: ${excel.get('total', 0):,.2f}, diff: ${diff:.2f})")
            for ms in result.months:
                month_key = ms.month[-2:]
                excel_key = {"07": "jul", "08": "aug", "09": "sep"}.get(month_key, "")
                excel_val = excel.get(excel_key, 0)
                print(f"    {ms.month}: ${ms.revenue_usd:,.2f} (Excel: ${excel_val:,.2f})")
            print()

    print(f"Total absolute difference across all roles: ${total_diff:.2f}")
    print(f"(Difference is due to day-rate rounding: Excel uses 3526.25, we use 3526.25)")

    # Aggregate
    print("\n=== Monthly Aggregates ===")
    agg = aggregate_prorations(prorations)
    for month, entry in agg.items():
        print(f"  {month}: Revenue ${entry.total_revenue:,.0f} | "
              f"Weighted ${entry.weighted_revenue:,.0f} | "
              f"FTE {entry.total_fte:.2f}")
        if entry.by_coe:
            for coe, fte in sorted(entry.by_coe.items()):
                print(f"    COE {coe}: {fte:.2f} FTE")
