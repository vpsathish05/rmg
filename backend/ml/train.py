"""
ML Forecast Training Orchestrator — Runs all models and validates outputs.

Usage:
  cd backend && source .venv/bin/activate
  PYTHONPATH=. python3 -m ml.train

This script:
  1. Loads historical data from the database
  2. Trains all forecast models (revenue, cluster, resource, project, COE gap)
  3. Prints model diagnostics and key metrics
  4. Optionally saves results to JSON cache for fast API serving
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from ml.data_prep import reconstruct_revenue, get_monthly_headcount
from ml.pipeline_calc import calculate_pipeline_revenue
from ml.models.revenue_forecast import forecast_revenue
from ml.models.cluster_model import forecast_by_cluster
from ml.models.project_forecast import forecast_projects
from ml.models.resource_forecast import forecast_resources
from ml.models.coe_gap_model import forecast_coe_gap


CACHE_DIR = Path(__file__).resolve().parent / "_cache"


def train_all(save_cache: bool = True) -> dict:
    """
    Run all ML forecast models end-to-end.
    
    Returns:
        Summary dict with key metrics from each model.
    """
    db = SessionLocal()
    results = {}

    try:
        print("=" * 60)
        print("  ML FORECAST — TRAINING ALL MODELS")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()

        total_start = time.time()

        # ── Step 1: Data Preparation ──────────────────────────────────────
        print("[1/6] Reconstructing revenue history...")
        t0 = time.time()
        history = reconstruct_revenue(db, months_back=30)
        headcount = get_monthly_headcount(db, months_back=30)
        print(f"       → {history.total_months} months, {len(history.actuals)} actuals "
              f"({time.time()-t0:.1f}s)")

        # ── Step 2: Pipeline Calculation ──────────────────────────────────
        print("[2/6] Calculating pipeline revenue...")
        t0 = time.time()
        pipeline = calculate_pipeline_revenue(db, future_only=False)
        print(f"       → {len(pipeline.prorations)} deals, "
              f"${pipeline.total_weighted_revenue:,.0f} weighted "
              f"({time.time()-t0:.1f}s)")

        # ── Step 3: Revenue Forecast ──────────────────────────────────────
        print("[3/6] Training revenue model...")
        t0 = time.time()
        rev_forecast = forecast_revenue(history, headcount, horizon=12)
        print(f"       → {rev_forecast.method}")
        print(f"       → MAPE: {rev_forecast.train_mape:.1f}%, "
              f"12-mo P50: ${rev_forecast.annual_total_p50:,.0f}, "
              f"YoY: +{rev_forecast.growth_rate_yoy*100:.1f}% "
              f"({time.time()-t0:.1f}s)")
        results["revenue"] = {
            "annual_total_p50": rev_forecast.annual_total_p50,
            "growth_rate_yoy": rev_forecast.growth_rate_yoy,
            "train_mape": rev_forecast.train_mape,
            "method": rev_forecast.method,
        }

        # ── Step 4: Cluster Decomposition ─────────────────────────────────
        print("[4/6] Computing cluster weights...")
        t0 = time.time()
        cluster_forecast = forecast_by_cluster(rev_forecast, pipeline)
        print(f"       → {len(cluster_forecast.clusters)} clusters")
        for cl, total in sorted(cluster_forecast.total_by_cluster.items()):
            weight = cluster_forecast.avg_weights.get(cl, 0)
            print(f"         C{cl}: ${total/1e6:.1f}M ({weight*100:.1f}%)")
        print(f"       ({time.time()-t0:.1f}s)")
        results["clusters"] = {
            "count": len(cluster_forecast.clusters),
            "total_by_cluster": cluster_forecast.total_by_cluster,
            "avg_weights": cluster_forecast.avg_weights,
        }

        # ── Step 5: Project Forecast ──────────────────────────────────────
        print("[5/6] Training project volume model...")
        t0 = time.time()
        proj_forecast = forecast_projects(db, horizon=12)
        print(f"       → {proj_forecast.train_months} months trained, "
              f"{proj_forecast.annual_total_p50} projects/year, "
              f"+{proj_forecast.growth_rate_yoy*100:.1f}% YoY "
              f"({time.time()-t0:.1f}s)")
        results["projects"] = {
            "annual_total_p50": proj_forecast.annual_total_p50,
            "growth_rate_yoy": proj_forecast.growth_rate_yoy,
            "avg_monthly": proj_forecast.avg_monthly,
        }

        # ── Step 6: Resource + COE Gap ────────────────────────────────────
        print("[6/6] Training resource & COE models...")
        t0 = time.time()
        resource_forecast = forecast_resources(db, pipeline, horizon=12)
        coe_forecast = forecast_coe_gap(db, pipeline, horizon=12)
        total_hiring = sum(coe_forecast.hiring_needs.values())
        print(f"       → Resources: avg {resource_forecast.avg_monthly_fte:.0f} FTE/mo, "
              f"{resource_forecast.avg_utilization:.1f}% util")
        print(f"       → COE Gap: {total_hiring} hires needed "
              f"({time.time()-t0:.1f}s)")
        results["resources"] = {
            "avg_monthly_fte": resource_forecast.avg_monthly_fte,
            "avg_utilization": resource_forecast.avg_utilization,
            "total_hiring_gap": sum(resource_forecast.hiring_gap.values()),
        }
        results["coe_gap"] = {
            "total_hiring_needs": total_hiring,
            "hiring_needs": coe_forecast.hiring_needs,
        }

        # ── Summary ──────────────────────────────────────────────────────
        elapsed = time.time() - total_start
        print()
        print("=" * 60)
        print(f"  TRAINING COMPLETE — {elapsed:.1f}s total")
        print("=" * 60)
        print(f"  Revenue (12-mo): ${rev_forecast.annual_total_p50/1e6:.1f}M (+{rev_forecast.growth_rate_yoy*100:.0f}% YoY)")
        print(f"  Projects (12-mo): {proj_forecast.annual_total_p50} ({proj_forecast.avg_monthly:.0f}/mo)")
        print(f"  Resources: {resource_forecast.avg_monthly_fte:.0f} FTE/mo @ {resource_forecast.avg_utilization:.0f}% util")
        print(f"  Hiring need: {total_hiring} (COE) + {sum(resource_forecast.hiring_gap.values())} (role-level)")
        print("=" * 60)

        # ── Save cache ────────────────────────────────────────────────────
        if save_cache:
            _save_cache(results, rev_forecast, proj_forecast, cluster_forecast)

        results["elapsed_seconds"] = round(elapsed, 1)
        results["computed_at"] = datetime.now().isoformat()
        return results

    finally:
        db.close()


def _save_cache(results: dict, rev_forecast, proj_forecast, cluster_forecast):
    """Save model outputs to JSON cache for fast API serving."""
    CACHE_DIR.mkdir(exist_ok=True)

    # Summary
    cache_file = CACHE_DIR / "summary.json"
    with open(cache_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\n  Cache saved: {cache_file}")


# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    train_all(save_cache=True)
