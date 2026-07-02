"""
Pipeline Revenue Calculator — Prorate all pipeline deals with probability weighting.

Queries pipeline_requests from the database, resolves each role to a rate,
and prorates revenue across months using the proration engine.

Outputs:
  - Monthly pipeline revenue (raw + probability-weighted)
  - By cluster, by COE, by role
  - FTE demand per month
  - Deal-level detail for drill-down
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from .rate_card import get_rate, load_rate_card
from .role_mapping import resolve_role, load_role_mapping
from .proration import (
    DealProration,
    MonthlyAggregate,
    prorate_deal,
    aggregate_prorations,
)


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class PipelineMonth:
    """Aggregated pipeline revenue/demand for a single month."""
    month: str
    raw_revenue: float = 0.0        # Total revenue (no probability weighting)
    weighted_revenue: float = 0.0   # Revenue × probability
    total_fte: float = 0.0          # Total FTE demand
    weighted_fte: float = 0.0       # FTE × probability
    deal_lines: int = 0             # Number of role-lines
    by_cluster: dict[int, float] = field(default_factory=dict)   # cluster → weighted_rev
    by_coe: dict[str, float] = field(default_factory=dict)       # coe → weighted_fte
    by_role: dict[str, float] = field(default_factory=dict)      # role → weighted_fte


@dataclass
class PipelineResult:
    """Complete pipeline calculation result."""
    months: dict[str, PipelineMonth]      # YYYY-MM → PipelineMonth
    prorations: list[DealProration]        # All individual deal prorations
    total_deals: int                       # Number of unique deals processed
    total_role_lines: int                  # Total role-lines processed
    unresolved_codes: list[str]            # Pipeline codes that couldn't be mapped
    coverage_pct: float                    # % of role-lines successfully mapped
    total_weighted_revenue: float          # Sum of all weighted monthly revenue
    total_weighted_fte: float              # Sum of all weighted monthly FTE


# ── Core Calculator ─────────────────────────────────────────────────────────

def calculate_pipeline_revenue(
    db: Session,
    status_filter: str = "not resourced",
    future_only: bool = True,
) -> PipelineResult:
    """
    Calculate prorated pipeline revenue from all pipeline_requests.
    
    Args:
        db: SQLAlchemy session
        status_filter: Filter by status (default: 'not resourced')
        future_only: Only include deals with start date >= today
    
    Returns:
        PipelineResult with monthly aggregation and deal-level detail
    """
    # Query pipeline requests
    query = text("""
        SELECT
            id,
            cluster,
            client_name,
            role_code_raw,
            allocation_pct,
            probability_weight,
            likely_start_date,
            duration_weeks,
            status,
            deal_stage,
            canonical_roles
        FROM pipeline_requests
        WHERE LOWER(COALESCE(status, '')) = :status
          AND likely_start_date IS NOT NULL
    """)

    params = {"status": status_filter.lower()}

    rows = db.execute(query, params).fetchall()

    # Process each pipeline role-line
    prorations: list[DealProration] = []
    unresolved: list[str] = []
    total_lines = 0
    resolved_lines = 0

    for row in rows:
        total_lines += 1

        start_date = row.likely_start_date
        if future_only and start_date < date.today():
            # Skip past deals unless explicitly included
            continue

        duration_weeks = int(row.duration_weeks) if row.duration_weeks else 12  # Default 12 weeks
        allocation_pct = float(row.allocation_pct or 100) / 100.0
        probability = float(row.probability_weight or 0.5)
        cluster = int(row.cluster) if row.cluster else None
        role_code = row.role_code_raw or ""

        # Resolve the role code to a rate
        mapping = resolve_role(role_code)
        if not mapping:
            # Try canonical_roles as fallback
            resolved = _try_canonical_fallback(role_code, row.canonical_roles)
            if not resolved:
                if role_code and role_code not in unresolved:
                    unresolved.append(role_code)
                continue
            mapping = resolved

        rate = get_rate(mapping.mapped_role, mapping.default_location)
        if not rate:
            if role_code not in unresolved:
                unresolved.append(role_code)
            continue

        # Calculate end date
        end_date = start_date + timedelta(weeks=duration_weeks) - timedelta(days=1)

        # Prorate the deal
        proration = prorate_deal(
            start_date=start_date,
            end_date=end_date,
            day_rate_usd=rate.day_rate_usd,
            allocation_pct=allocation_pct,
            probability=probability,
            role=mapping.mapped_role,
            location=mapping.default_location,
            coe=mapping.mapped_coe,
            cluster=cluster,
            method="calendar",
        )

        prorations.append(proration)
        resolved_lines += 1

    # Aggregate into monthly totals
    months: dict[str, PipelineMonth] = {}

    for deal in prorations:
        for ms in deal.months:
            m = ms.month
            if m not in months:
                months[m] = PipelineMonth(month=m)

            entry = months[m]
            entry.raw_revenue += ms.revenue_usd
            entry.weighted_revenue += ms.revenue_usd * deal.probability
            entry.total_fte += ms.fte
            entry.weighted_fte += ms.fte * deal.probability
            entry.deal_lines += 1

            # By cluster
            if deal.cluster is not None:
                entry.by_cluster[deal.cluster] = (
                    entry.by_cluster.get(deal.cluster, 0.0)
                    + ms.revenue_usd * deal.probability
                )

            # By COE (FTE-based)
            if deal.coe:
                entry.by_coe[deal.coe] = (
                    entry.by_coe.get(deal.coe, 0.0) + ms.fte * deal.probability
                )

            # By role (FTE-based)
            if deal.role:
                entry.by_role[deal.role] = (
                    entry.by_role.get(deal.role, 0.0) + ms.fte * deal.probability
                )

    # Round values
    for entry in months.values():
        entry.raw_revenue = round(entry.raw_revenue, 2)
        entry.weighted_revenue = round(entry.weighted_revenue, 2)
        entry.total_fte = round(entry.total_fte, 4)
        entry.weighted_fte = round(entry.weighted_fte, 4)

    # Sort months
    months = dict(sorted(months.items()))

    # Summary stats
    total_weighted_rev = sum(m.weighted_revenue for m in months.values())
    total_weighted_fte = sum(m.weighted_fte for m in months.values())
    coverage = (resolved_lines / total_lines * 100) if total_lines > 0 else 0.0

    return PipelineResult(
        months=months,
        prorations=prorations,
        total_deals=len(set(r.id for r in rows)) if rows else 0,
        total_role_lines=total_lines,
        unresolved_codes=unresolved,
        coverage_pct=round(coverage, 1),
        total_weighted_revenue=round(total_weighted_rev, 2),
        total_weighted_fte=round(total_weighted_fte, 4),
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _try_canonical_fallback(
    role_code: str,
    canonical_roles: Optional[list] = None,
) -> Optional[object]:
    """Try to resolve using canonical_roles array if role_code mapping fails."""
    if not canonical_roles:
        return None

    # canonical_roles is a PostgreSQL array of role names
    # Try to find one that matches a rate card entry
    from .role_mapping import RoleMapping
    from .rate_card import _normalize_location

    rates = load_rate_card()

    for canon_role in canonical_roles:
        if not canon_role:
            continue
        canon_role = str(canon_role).strip()

        # Check if it directly matches a rate card role
        for (rate_role, loc), _ in rates.items():
            if canon_role.lower() == rate_role.lower():
                # Create a synthetic mapping
                return RoleMapping(
                    pipeline_code=role_code,
                    mapped_role=rate_role,
                    default_location=loc,
                    mapped_coe=_infer_coe(rate_role),
                    confidence="Low - canonical fallback",
                )

    return None


def _infer_coe(role: str) -> str:
    """Infer COE from role name (heuristic fallback)."""
    role_lower = role.lower()
    if "software" in role_lower or "engineer" in role_lower or "architect" in role_lower:
        return "Full Stack"
    elif "consultant" in role_lower and "solution" not in role_lower:
        return "Consulting"
    elif "solution" in role_lower:
        return "Power BI & Consulting"
    elif "enabler" in role_lower:
        return "Data Engineering"
    elif "partner" in role_lower or "principal" in role_lower:
        return "GTM"
    elif "manager" in role_lower:
        return "Consulting"
    return "Unknown"


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        print("=== Pipeline Revenue Calculator ===\n")

        result = calculate_pipeline_revenue(db, future_only=True)

        print(f"Total role-lines: {result.total_role_lines}")
        print(f"Resolved: {result.total_role_lines - len(result.unresolved_codes)} "
              f"({result.coverage_pct}%)")
        print(f"Unresolved codes: {result.unresolved_codes[:10]}")
        print(f"Total deals prorated: {len(result.prorations)}")
        print(f"Total weighted revenue: ${result.total_weighted_revenue:,.0f}")
        print(f"Total weighted FTE: {result.total_weighted_fte:.1f}")
        print()

        print(f"{'Month':<10} {'Raw Rev':>14} {'Weighted Rev':>14} {'FTE':>8} {'W-FTE':>8} {'Lines':>6}")
        print("-" * 65)
        for month, entry in result.months.items():
            print(f"{month:<10} ${entry.raw_revenue:>12,.0f} ${entry.weighted_revenue:>12,.0f} "
                  f"{entry.total_fte:>8.1f} {entry.weighted_fte:>8.1f} {entry.deal_lines:>6}")

        # Cluster breakdown
        print("\n=== Revenue by Cluster (weighted, full period) ===")
        cluster_totals: dict[int, float] = {}
        for entry in result.months.values():
            for cl, rev in entry.by_cluster.items():
                cluster_totals[cl] = cluster_totals.get(cl, 0) + rev
        for cl in sorted(cluster_totals.keys()):
            print(f"  Cluster {cl}: ${cluster_totals[cl]:,.0f}")

        # COE breakdown
        print("\n=== FTE Demand by COE (weighted, full period) ===")
        coe_totals: dict[str, float] = {}
        for entry in result.months.values():
            for coe, fte in entry.by_coe.items():
                coe_totals[coe] = coe_totals.get(coe, 0) + fte
        for coe in sorted(coe_totals.keys(), key=lambda c: -coe_totals[c]):
            print(f"  {coe:<25}: {coe_totals[coe]:.1f} FTE-months")

    finally:
        db.close()
