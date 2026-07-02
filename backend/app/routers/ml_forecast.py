"""
ML Forecast API Router — Serves all ML forecasting model outputs.

Endpoints:
  GET /api/forecast/ml/revenue          → 12-month revenue forecast (P10/P50/P90)
  GET /api/forecast/ml/revenue/clusters → Revenue by cluster × month
  GET /api/forecast/ml/projects         → 12-month project start predictions
  GET /api/forecast/ml/resources        → 12-month FTE demand by role + hiring gap
  GET /api/forecast/ml/coe-gap          → COE supply vs demand gap
  GET /api/forecast/ml/summary          → Combined dashboard KPIs
  GET /api/forecast/ml/actuals          → Historical revenue actuals
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter()


# ── Revenue Forecast ────────────────────────────────────────────────────────

@router.get("/revenue")
def get_revenue_forecast(db: Session = Depends(get_db)):
    """12-month total revenue forecast with P10/P50/P90 confidence bands."""
    from ml.data_prep import reconstruct_revenue, get_monthly_headcount
    from ml.models.revenue_forecast import forecast_revenue

    history = reconstruct_revenue(db, months_back=30)
    headcount = get_monthly_headcount(db, months_back=30)
    result = forecast_revenue(history, headcount, horizon=12)

    return {
        "method": result.method,
        "model_version": result.model_version,
        "training_months": result.training_months,
        "last_actual_month": result.last_actual_month,
        "last_actual_value": result.last_actual_value,
        "annual_total_p50": result.annual_total_p50,
        "growth_rate_yoy": result.growth_rate_yoy,
        "train_mape": result.train_mape,
        "trend_monthly": result.trend_monthly,
        "forecasts": [
            {
                "month": f.month,
                "p10": f.p10,
                "p50": f.p50,
                "p90": f.p90,
            }
            for f in result.forecasts
        ],
    }


# ── Revenue by Cluster ──────────────────────────────────────────────────────

@router.get("/revenue/clusters")
def get_cluster_forecast(db: Session = Depends(get_db)):
    """Revenue decomposed by cluster × month."""
    from ml.data_prep import reconstruct_revenue, get_monthly_headcount
    from ml.models.revenue_forecast import forecast_revenue
    from ml.pipeline_calc import calculate_pipeline_revenue
    from ml.models.cluster_model import forecast_by_cluster

    history = reconstruct_revenue(db, months_back=30)
    headcount = get_monthly_headcount(db, months_back=30)
    rev_forecast = forecast_revenue(history, headcount, horizon=12)
    pipeline = calculate_pipeline_revenue(db, future_only=False)
    result = forecast_by_cluster(rev_forecast, pipeline)

    return {
        "method": result.method,
        "avg_weights": result.avg_weights,
        "total_by_cluster": result.total_by_cluster,
        "clusters": {
            cl: [
                {
                    "month": cm.month,
                    "weight": cm.weight,
                    "revenue_p10": cm.revenue_p10,
                    "revenue_p50": cm.revenue_p50,
                    "revenue_p90": cm.revenue_p90,
                }
                for cm in months
            ]
            for cl, months in result.clusters.items()
        },
    }


# ── Project Volume Forecast ─────────────────────────────────────────────────

@router.get("/projects")
def get_project_forecast(db: Session = Depends(get_db)):
    """12-month project start predictions with seasonality."""
    from ml.models.project_forecast import forecast_projects

    result = forecast_projects(db, horizon=12)

    return {
        "method": result.method,
        "train_months": result.train_months,
        "annual_total_p50": result.annual_total_p50,
        "growth_rate_yoy": result.growth_rate_yoy,
        "avg_monthly": result.avg_monthly,
        "seasonality": result.seasonality,
        "historical": [{"month": m, "count": c} for m, c in result.historical],
        "forecasts": [
            {
                "month": f.month,
                "p10": f.p10,
                "p50": f.p50,
                "p90": f.p90,
                "by_type": f.by_type,
            }
            for f in result.forecasts
        ],
    }


# ── Resource Demand ─────────────────────────────────────────────────────────

@router.get("/resources")
def get_resource_forecast(db: Session = Depends(get_db)):
    """12-month FTE demand by role + hiring gap."""
    from ml.pipeline_calc import calculate_pipeline_revenue
    from ml.models.resource_forecast import forecast_resources

    pipeline = calculate_pipeline_revenue(db, future_only=False)
    result = forecast_resources(db, pipeline, horizon=12)

    return {
        "method": result.method,
        "total_fte_12m": result.total_fte_12m,
        "avg_monthly_fte": result.avg_monthly_fte,
        "avg_utilization": result.avg_utilization,
        "hiring_gap": result.hiring_gap,
        "months": [
            {
                "month": m.month,
                "total_fte": m.total_fte,
                "bench_count": m.bench_count,
                "utilization_pct": m.utilization_pct,
                "by_role": m.by_role,
            }
            for m in result.months
        ],
    }


# ── COE Supply/Demand Gap ──────────────────────────────────────────────────

@router.get("/coe-gap")
def get_coe_gap(db: Session = Depends(get_db)):
    """COE supply vs demand gap with hiring recommendations."""
    from ml.pipeline_calc import calculate_pipeline_revenue
    from ml.models.coe_gap_model import forecast_coe_gap

    pipeline = calculate_pipeline_revenue(db, future_only=False)
    result = forecast_coe_gap(db, pipeline, horizon=12)

    return {
        "method": result.method,
        "coverage_note": result.coverage_note,
        "hiring_needs": result.hiring_needs,
        "total_gap_by_coe": result.total_gap_by_coe,
        "total_demand_by_coe": result.total_demand_by_coe,
        "total_supply_by_coe": result.total_supply_by_coe,
        "coes": {
            coe: [
                {
                    "month": m.month,
                    "total_headcount": m.total_headcount,
                    "already_billable": m.already_billable,
                    "available_supply": m.available_supply,
                    "projected_supply": m.projected_supply,
                    "demand_fte": m.demand_fte,
                    "gap": m.gap,
                }
                for m in months
            ]
            for coe, months in result.coes.items()
        },
    }


# ── Summary (combined KPIs) ────────────────────────────────────────────────

@router.get("/summary")
def get_forecast_summary(db: Session = Depends(get_db)):
    """Combined ML forecast KPIs for dashboard."""
    from ml.data_prep import reconstruct_revenue, get_monthly_headcount
    from ml.models.revenue_forecast import forecast_revenue
    from ml.pipeline_calc import calculate_pipeline_revenue
    from ml.models.project_forecast import forecast_projects
    from ml.models.resource_forecast import forecast_resources
    from ml.models.coe_gap_model import forecast_coe_gap

    # Revenue
    history = reconstruct_revenue(db, months_back=30)
    headcount = get_monthly_headcount(db, months_back=30)
    rev = forecast_revenue(history, headcount, horizon=12)

    # Pipeline
    pipeline = calculate_pipeline_revenue(db, future_only=False)

    # Projects
    proj = forecast_projects(db, horizon=12)

    # Resources
    resources = forecast_resources(db, pipeline, horizon=12)

    # COE Gap
    coe_gap = forecast_coe_gap(db, pipeline, horizon=12)

    return {
        "revenue": {
            "annual_total_p50": rev.annual_total_p50,
            "growth_rate_yoy": rev.growth_rate_yoy,
            "next_month_p50": rev.forecasts[0].p50 if rev.forecasts else 0,
            "last_actual": rev.last_actual_value,
            "trend_monthly": rev.trend_monthly,
        },
        "projects": {
            "annual_total_p50": proj.annual_total_p50,
            "growth_rate_yoy": proj.growth_rate_yoy,
            "avg_monthly": proj.avg_monthly,
        },
        "resources": {
            "avg_monthly_fte": resources.avg_monthly_fte,
            "avg_utilization": resources.avg_utilization,
            "total_hiring_gap": sum(resources.hiring_gap.values()),
            "top_hiring_roles": dict(
                sorted(resources.hiring_gap.items(), key=lambda x: -x[1])[:5]
            ),
        },
        "coe_gap": {
            "total_hiring_needs": sum(coe_gap.hiring_needs.values()),
            "worst_coes": dict(
                sorted(coe_gap.total_gap_by_coe.items(), key=lambda x: x[1])[:3]
            ),
            "coverage_note": coe_gap.coverage_note,
        },
        "pipeline": {
            "total_weighted_revenue": pipeline.total_weighted_revenue,
            "total_weighted_fte": pipeline.total_weighted_fte,
            "months_covered": len(pipeline.months),
        },
    }


# ── Actuals (historical) ───────────────────────────────────────────────────

@router.get("/actuals")
def get_actuals(db: Session = Depends(get_db)):
    """Historical revenue actuals + calibrated series for chart overlay."""
    from ml.data_prep import reconstruct_revenue

    history = reconstruct_revenue(db, months_back=30)
    calibrated = history.get_calibrated_series()

    return {
        "actuals": [
            {"month": m, "revenue": v}
            for m, v in sorted(history.actuals.items())
        ],
        "calibrated": [
            {"month": m, "revenue": round(v, 2)}
            for m, v in calibrated
        ],
        "calibration_factor": history.calibration_factor,
    }
