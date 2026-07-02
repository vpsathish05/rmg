"""
ML Forecast Prediction — Generate predictions from all models.

Usage:
  cd backend && source .venv/bin/activate
  PYTHONPATH=. python3 -m ml.predict [--horizon 12] [--format json|table]

Generates 12-month predictions and outputs them in a readable format.
Can be used for:
  - CLI inspection of current forecasts
  - JSON export for external tools
  - Scheduled batch predictions
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from ml.data_prep import reconstruct_revenue, get_monthly_headcount
from ml.pipeline_calc import calculate_pipeline_revenue
from ml.models.revenue_forecast import forecast_revenue
from ml.models.cluster_model import forecast_by_cluster
from ml.models.project_forecast import forecast_projects
from ml.models.resource_forecast import forecast_resources
from ml.models.coe_gap_model import forecast_coe_gap


def predict(horizon: int = 12, output_format: str = "table") -> dict:
    """Run all models and return predictions."""
    db = SessionLocal()
    try:
        # Data
        history = reconstruct_revenue(db, months_back=30)
        headcount = get_monthly_headcount(db, months_back=30)
        pipeline = calculate_pipeline_revenue(db, future_only=False)

        # Models
        rev = forecast_revenue(history, headcount, horizon=horizon)
        clusters = forecast_by_cluster(rev, pipeline)
        projects = forecast_projects(db, horizon=horizon)
        resources = forecast_resources(db, pipeline, horizon=horizon)
        coe_gap = forecast_coe_gap(db, pipeline, horizon=horizon)

        predictions = {
            "generated_at": datetime.now().isoformat(),
            "horizon_months": horizon,
            "revenue": {
                "annual_total_p50": rev.annual_total_p50,
                "growth_rate_yoy": rev.growth_rate_yoy,
                "monthly": [
                    {"month": f.month, "p10": f.p10, "p50": f.p50, "p90": f.p90}
                    for f in rev.forecasts
                ],
            },
            "clusters": {
                str(cl): {
                    "total": clusters.total_by_cluster[cl],
                    "weight": clusters.avg_weights[cl],
                }
                for cl in sorted(clusters.clusters.keys())
            },
            "projects": {
                "annual_total": projects.annual_total_p50,
                "monthly": [
                    {"month": f.month, "p50": f.p50}
                    for f in projects.forecasts
                ],
            },
            "resources": {
                "avg_fte": resources.avg_monthly_fte,
                "utilization": resources.avg_utilization,
                "hiring_gap": resources.hiring_gap,
            },
            "coe_gap": {
                "hiring_needs": coe_gap.hiring_needs,
                "gaps": coe_gap.total_gap_by_coe,
            },
        }

        if output_format == "table":
            _print_table(predictions, rev, projects, resources, coe_gap)
        elif output_format == "json":
            print(json.dumps(predictions, indent=2, default=str))

        return predictions

    finally:
        db.close()


def _print_table(predictions, rev, projects, resources, coe_gap):
    """Print predictions in a readable table format."""
    print(f"\n{'═'*60}")
    print(f"  ML FORECAST PREDICTIONS — {predictions['horizon_months']}-Month Horizon")
    print(f"  Generated: {predictions['generated_at'][:19]}")
    print(f"{'═'*60}\n")

    # Revenue
    print("┌─ REVENUE FORECAST ─────────────────────────────────────┐")
    print(f"│  12-Month Total (P50): ${rev.annual_total_p50/1e6:.1f}M")
    print(f"│  YoY Growth: +{rev.growth_rate_yoy*100:.1f}%")
    print(f"│  Monthly Trend: +${rev.trend_monthly/1e3:.0f}K/mo")
    print(f"│")
    print(f"│  {'Month':<8} {'P10':>10} {'P50':>10} {'P90':>10}")
    print(f"│  {'─'*42}")
    for f in rev.forecasts[:6]:
        print(f"│  {f.month:<8} ${f.p10/1e6:>8.2f}M ${f.p50/1e6:>8.2f}M ${f.p90/1e6:>8.2f}M")
    if len(rev.forecasts) > 6:
        print(f"│  ... ({len(rev.forecasts)-6} more months)")
    print(f"└{'─'*56}┘\n")

    # Projects
    print("┌─ PROJECT FORECAST ─────────────────────────────────────┐")
    print(f"│  12-Month Total: {projects.annual_total_p50} projects")
    print(f"│  Monthly Avg: {projects.avg_monthly:.0f}")
    print(f"│  YoY Growth: +{projects.growth_rate_yoy*100:.1f}%")
    print(f"└{'─'*56}┘\n")

    # Resources
    print("┌─ RESOURCE DEMAND ──────────────────────────────────────┐")
    print(f"│  Avg Monthly FTE: {resources.avg_monthly_fte:.0f}")
    print(f"│  Utilization: {resources.avg_utilization:.1f}%")
    print(f"│  Total Hiring Gap: {sum(resources.hiring_gap.values())}")
    if resources.hiring_gap:
        print(f"│  Top needs:")
        for role, gap in sorted(resources.hiring_gap.items(), key=lambda x: -x[1])[:5]:
            print(f"│    {role}: +{gap}")
    print(f"└{'─'*56}┘\n")

    # COE Gap
    print("┌─ COE SUPPLY/DEMAND GAP ────────────────────────────────┐")
    print(f"│  Total Hiring Need: {sum(coe_gap.hiring_needs.values())}")
    if coe_gap.hiring_needs:
        for coe, need in sorted(coe_gap.hiring_needs.items(), key=lambda x: -x[1]):
            print(f"│    {coe}: +{need}")
    print(f"└{'─'*56}┘")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate ML forecast predictions")
    parser.add_argument("--horizon", type=int, default=12, help="Forecast horizon in months")
    parser.add_argument("--format", choices=["table", "json"], default="table", help="Output format")
    args = parser.parse_args()

    predict(horizon=args.horizon, output_format=args.format)
