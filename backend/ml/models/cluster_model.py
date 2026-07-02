"""
Cluster Weight Model — Decompose total revenue into cluster-level forecasts.

Replicates and extends Excel Step 6:
  Forecast[Cluster, Month] = Total_Revenue_Trend[Month] × Cluster_Weight[Cluster, Month]

Where cluster weights come from the pipeline's bottom-up revenue split.
For months with no pipeline data, falls back to the average weight across
all months that have data.

Enhancement over Excel:
  - Smoothed weights (exponential decay for missing months instead of hard fallback)
  - 12-month horizon (Excel only does 6)
  - Confidence bands propagated from revenue model
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from ..pipeline_calc import PipelineResult, PipelineMonth
from ..models.revenue_forecast import RevenueForecast, ForecastPoint


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ClusterMonth:
    """Revenue forecast for a single cluster in a single month."""
    month: str
    cluster: int
    weight: float          # This cluster's share of total (0.0 - 1.0)
    revenue_p10: float
    revenue_p50: float
    revenue_p90: float


@dataclass
class ClusterForecast:
    """Complete cluster-level revenue decomposition."""
    clusters: dict[int, list[ClusterMonth]]     # cluster → monthly forecasts
    weights_by_month: dict[str, dict[int, float]]  # month → {cluster: weight}
    avg_weights: dict[int, float]                # cluster → 6-month avg weight
    total_by_cluster: dict[int, float]           # cluster → 12-month P50 total
    method: str


# ── Core Model ──────────────────────────────────────────────────────────────

def forecast_by_cluster(
    revenue_forecast: RevenueForecast,
    pipeline: PipelineResult,
) -> ClusterForecast:
    """
    Decompose the total revenue forecast into cluster-level predictions.
    
    Method (same as Excel, extended to 12 months):
    1. Compute each cluster's share of bottom-up pipeline revenue per month
    2. For months with pipeline data: use that month's actual cluster share
    3. For months without pipeline data: use the average share across all months
    4. Multiply total forecast × cluster weight → cluster forecast
    
    Args:
        revenue_forecast: Total revenue forecast from revenue_forecast model
        pipeline: Pipeline calculation result with cluster breakdown
    
    Returns:
        ClusterForecast with per-cluster monthly predictions
    """
    # Step 1: Extract cluster weights from pipeline data
    # For each month that has pipeline data, compute relative cluster shares
    all_clusters = set()
    month_cluster_rev: dict[str, dict[int, float]] = {}

    for month, pm in pipeline.months.items():
        if pm.by_cluster:
            month_cluster_rev[month] = dict(pm.by_cluster)
            all_clusters.update(pm.by_cluster.keys())

    if not all_clusters:
        # No cluster data at all — equal split
        all_clusters = {1, 2, 3, 4, 5}

    # Step 2: Compute weights per month
    weights_by_month: dict[str, dict[int, float]] = {}

    for month, cluster_rev in month_cluster_rev.items():
        total_rev = sum(cluster_rev.values())
        if total_rev > 0:
            weights = {cl: rev / total_rev for cl, rev in cluster_rev.items()}
        else:
            weights = {cl: 1.0 / len(all_clusters) for cl in all_clusters}

        # Ensure all clusters are represented (0 weight if missing)
        for cl in all_clusters:
            if cl not in weights:
                weights[cl] = 0.0

        weights_by_month[month] = weights

    # Step 3: Compute average weights (fallback for months with no pipeline)
    avg_weights: dict[int, float] = {}
    for cl in sorted(all_clusters):
        weights_for_cluster = [
            w.get(cl, 0.0) for w in weights_by_month.values()
        ]
        if weights_for_cluster:
            avg_weights[cl] = np.mean(weights_for_cluster)
        else:
            avg_weights[cl] = 1.0 / len(all_clusters)

    # Normalize avg weights to sum to 1.0
    total_avg = sum(avg_weights.values())
    if total_avg > 0:
        avg_weights = {cl: w / total_avg for cl, w in avg_weights.items()}

    # Step 4: Assign weights for each forecast month
    forecast_months = [f.month for f in revenue_forecast.forecasts]
    final_weights: dict[str, dict[int, float]] = {}

    for month in forecast_months:
        if month in weights_by_month:
            # This month has pipeline data — use actual cluster shares
            final_weights[month] = weights_by_month[month]
        else:
            # No pipeline data — use smoothed fallback
            # Try to blend: weight toward the last month with data
            blended = _blend_weights(month, weights_by_month, avg_weights, all_clusters)
            final_weights[month] = blended

    # Step 5: Apply weights to total forecast → cluster forecasts
    clusters: dict[int, list[ClusterMonth]] = {cl: [] for cl in sorted(all_clusters)}
    total_by_cluster: dict[int, float] = {cl: 0.0 for cl in sorted(all_clusters)}

    for fp in revenue_forecast.forecasts:
        month_weights = final_weights.get(fp.month, avg_weights)

        for cl in sorted(all_clusters):
            w = month_weights.get(cl, 0.0)

            cm = ClusterMonth(
                month=fp.month,
                cluster=cl,
                weight=round(w, 6),
                revenue_p10=round(fp.p10 * w, 2),
                revenue_p50=round(fp.p50 * w, 2),
                revenue_p90=round(fp.p90 * w, 2),
            )
            clusters[cl].append(cm)
            total_by_cluster[cl] += cm.revenue_p50

    # Round totals
    total_by_cluster = {cl: round(v, 2) for cl, v in total_by_cluster.items()}

    return ClusterForecast(
        clusters=clusters,
        weights_by_month=final_weights,
        avg_weights=avg_weights,
        total_by_cluster=total_by_cluster,
        method="Pipeline-derived cluster weights with average fallback (Excel Step 6 extended)",
    )


# ── Helpers ─────────────────────────────────────────────────────────────────

def _blend_weights(
    target_month: str,
    weights_by_month: dict[str, dict[int, float]],
    avg_weights: dict[int, float],
    all_clusters: set[int],
) -> dict[int, float]:
    """
    Blend cluster weights for a month without pipeline data.
    
    Strategy:
    - If this month is close to months with data, bias toward those
    - If far away, revert to average
    - Ensures smooth transitions rather than hard jumps
    """
    if not weights_by_month:
        return dict(avg_weights)

    # Find the closest month with pipeline data
    sorted_pipeline_months = sorted(weights_by_month.keys())
    last_data_month = sorted_pipeline_months[-1]

    # How many months away from last data?
    distance = _month_distance(last_data_month, target_month)

    if distance <= 0:
        # Target is before or at last pipeline month — shouldn't happen normally
        return weights_by_month.get(target_month, dict(avg_weights))

    # Exponential decay toward average: closer months use last-known, far ones use avg
    # decay_factor: 1.0 at distance=1, approaching 0 as distance grows
    decay = np.exp(-0.3 * distance)  # ~0.74 at 1mo, ~0.55 at 2mo, ~0.22 at 5mo

    # Blend: last_data_weights × decay + avg_weights × (1 - decay)
    last_weights = weights_by_month[last_data_month]
    blended: dict[int, float] = {}

    for cl in all_clusters:
        last_w = last_weights.get(cl, 0.0)
        avg_w = avg_weights.get(cl, 0.0)
        blended[cl] = last_w * decay + avg_w * (1 - decay)

    # Normalize to sum to 1.0
    total = sum(blended.values())
    if total > 0:
        blended = {cl: w / total for cl, w in blended.items()}

    return blended


def _month_distance(month_a: str, month_b: str) -> int:
    """Compute distance in months between two YYYY-MM strings."""
    ya, ma = int(month_a[:4]), int(month_a[5:7])
    yb, mb = int(month_b[:4]), int(month_b[5:7])
    return (yb - ya) * 12 + (mb - ma)


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal
    from ml.data_prep import reconstruct_revenue, get_monthly_headcount
    from ml.models.revenue_forecast import forecast_revenue
    from ml.pipeline_calc import calculate_pipeline_revenue

    db = SessionLocal()
    try:
        print("=== Cluster Weight Model ===\n")

        # Get inputs
        history = reconstruct_revenue(db, months_back=30)
        headcount = get_monthly_headcount(db, months_back=30)
        rev_forecast = forecast_revenue(history, headcount, horizon=12)
        pipeline = calculate_pipeline_revenue(db, future_only=False)

        # Run cluster model
        result = forecast_by_cluster(rev_forecast, pipeline)

        # Show weights
        print("Average Cluster Weights (from pipeline):")
        for cl, w in sorted(result.avg_weights.items()):
            print(f"  Cluster {cl}: {w*100:.1f}%")

        print(f"\nMethod: {result.method}")
        print()

        # Show forecast table (like Excel output)
        months = [f.month for f in rev_forecast.forecasts]
        header = f"{'Cluster':<12}" + "".join(f"{m[5:]:>10}" for m in months[:6]) + f"{'12-Mo Total':>14}"
        print(header)
        print("-" * len(header))

        grand_total = 0.0
        for cl in sorted(result.clusters.keys()):
            cl_months = result.clusters[cl]
            row = f"Cluster {cl:<4}"
            for cm in cl_months[:6]:
                row += f"${cm.revenue_p50/1e6:>8.2f}M"
            row += f"  ${result.total_by_cluster[cl]/1e6:>9.2f}M"
            print(row)
            grand_total += result.total_by_cluster[cl]

        print("-" * len(header))
        totals_row = f"{'TOTAL':<12}"
        for fp in rev_forecast.forecasts[:6]:
            totals_row += f"${fp.p50/1e6:>8.2f}M"
        totals_row += f"  ${grand_total/1e6:>9.2f}M"
        print(totals_row)

        # Compare with Excel
        print("\n=== Excel Comparison (6-month totals, USD) ===")
        excel_totals = {1: 3_251_321, 2: 2_816_626, 3: 5_774_749, 4: 1_576_335, 5: 14_835_740}
        for cl in sorted(result.clusters.keys()):
            our_6mo = sum(cm.revenue_p50 for cm in result.clusters[cl][:6])
            excel_6mo = excel_totals.get(cl, 0)
            print(f"  Cluster {cl}: Ours ${our_6mo/1e6:.2f}M | Excel ${excel_6mo/1e6:.2f}M")

    finally:
        db.close()
