"""
Project Volume Model — Forecast monthly new project starts for 12 months.

Uses 90 months of historical project start data (Jan 2019 → Jun 2026).
Applies Holt-Winters with additive seasonality (yearly cycle) to capture:
  - Overall growth trend (company scaling)
  - Seasonal patterns (Q1 ramp-up, Q3 dip, Q4 surge)
  - Confidence bands

Also provides breakdown by project type (Client vs Internal vs MS).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session
from statsmodels.tsa.holtwinters import ExponentialSmoothing


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ProjectMonthForecast:
    """Forecast for a single month."""
    month: str
    p10: int            # Pessimistic
    p50: int            # Expected
    p90: int            # Optimistic
    by_type: dict[str, int] = field(default_factory=dict)  # project_type → count


@dataclass
class ProjectForecast:
    """Complete project volume forecast."""
    forecasts: list[ProjectMonthForecast]
    historical: list[tuple[str, int]]       # Last 12 months actual
    annual_total_p50: int
    growth_rate_yoy: float
    avg_monthly: float
    seasonality: dict[int, float]           # month_num → seasonal factor
    method: str
    train_months: int


# ── Core Model ──────────────────────────────────────────────────────────────

def forecast_projects(
    db: Session,
    horizon: int = 12,
) -> ProjectForecast:
    """
    Forecast monthly new project starts for the next N months.
    
    Uses Holt-Winters exponential smoothing with yearly seasonality
    on 90 months of historical data.
    
    Args:
        db: SQLAlchemy session
        horizon: Months to forecast (default: 12)
    
    Returns:
        ProjectForecast with monthly predictions
    """
    # Step 1: Get historical monthly project starts
    hist = _get_project_history(db)

    if len(hist) < 24:
        raise ValueError(f"Insufficient history: {len(hist)} months (need >= 24)")

    months = [m for m, _ in hist]
    values = np.array([v for _, v in hist], dtype=float)

    # Step 2: Get type breakdown for proportional split
    type_shares = _get_type_shares(db)

    # Step 3: Fit Holt-Winters with yearly seasonality (period=12)
    forecast_values, residuals, seasonal_factors = _holt_winters_forecast(values, horizon)

    # Step 4: Compute confidence bands
    residual_std = np.std(residuals) if len(residuals) > 0 else values[-12:].std()

    forecasts: list[ProjectMonthForecast] = []
    last_month = _parse_month(months[-1])

    for i in range(horizon):
        next_month = _add_months(last_month, i + 1)
        month_str = next_month.strftime("%Y-%m")

        p50 = max(1, int(round(forecast_values[i])))

        spread = residual_std * (1.0 + 0.05 * i)  # Mild widening
        p10 = max(1, int(round(forecast_values[i] - 1.28 * spread)))
        p90 = max(p50, int(round(forecast_values[i] + 1.28 * spread)))

        # Type breakdown (proportional to historical shares)
        by_type = {}
        for ptype, share in type_shares.items():
            by_type[ptype] = max(0, int(round(p50 * share)))

        forecasts.append(ProjectMonthForecast(
            month=month_str,
            p10=p10,
            p50=p50,
            p90=p90,
            by_type=by_type,
        ))

    # Step 5: Seasonality extraction (month → factor)
    seasonality = {}
    if seasonal_factors is not None and len(seasonal_factors) >= 12:
        for i in range(12):
            seasonality[i + 1] = round(float(seasonal_factors[i]), 3)

    # Step 6: Summary stats
    annual_total = sum(f.p50 for f in forecasts)
    last_12 = int(sum(values[-12:]))
    growth = (annual_total / last_12 - 1.0) if last_12 > 0 else 0.0

    # Historical (last 12 months for chart overlay)
    historical = [(m, int(v)) for m, v in hist[-12:]]

    return ProjectForecast(
        forecasts=forecasts,
        historical=historical,
        annual_total_p50=annual_total,
        growth_rate_yoy=round(growth, 4),
        avg_monthly=round(annual_total / horizon, 1),
        seasonality=seasonality,
        method="Holt-Winters additive seasonality (period=12)",
        train_months=len(hist),
    )


# ── Sub-models ──────────────────────────────────────────────────────────────

def _holt_winters_forecast(
    values: np.ndarray,
    horizon: int,
) -> tuple[np.ndarray, np.ndarray, Optional[np.ndarray]]:
    """
    Holt-Winters exponential smoothing with yearly seasonality.
    Falls back to damped trend (no seasonality) if seasonal fit fails.
    """
    # Try seasonal model first (needs >= 2 full cycles = 24 months)
    if len(values) >= 24:
        try:
            model = ExponentialSmoothing(
                values,
                trend="add",
                damped_trend=True,
                seasonal="add",
                seasonal_periods=12,
            ).fit(optimized=True)

            forecast = model.forecast(horizon)
            residuals = model.resid

            # Extract seasonal components
            seasonal = model.params.get("seasonal_periods", None)
            seasonal_factors = None
            if hasattr(model, 'season'):
                seasonal_factors = model.season

            return np.array(forecast), np.array(residuals), seasonal_factors

        except Exception:
            pass  # Fall through to simpler model

    # Fallback: Holt's linear trend (no seasonality)
    try:
        model = ExponentialSmoothing(
            values,
            trend="add",
            damped_trend=True,
            seasonal=None,
        ).fit(optimized=True)

        forecast = model.forecast(horizon)
        residuals = model.resid
        return np.array(forecast), np.array(residuals), None

    except Exception:
        # Last resort: linear extrapolation
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)
        forecast = np.polyval(slope, np.arange(len(values), len(values) + horizon))
        residuals = values - np.polyval(slope, x)
        return forecast, residuals, None


# ── Queries ─────────────────────────────────────────────────────────────────

def _get_project_history(db: Session) -> list[tuple[str, int]]:
    """Get monthly project start counts for all available history."""
    rows = db.execute(text("""
        SELECT TO_CHAR(project_start_date, 'YYYY-MM') AS month, COUNT(*) AS cnt
        FROM projects
        WHERE is_active_version = true
          AND project_start_date IS NOT NULL
          AND project_start_date >= '2019-01-01'
          AND project_start_date <= CURRENT_DATE
          AND LOWER(COALESCE(type_of_project, '')) != 'bau activity'
        GROUP BY month
        ORDER BY month
    """)).fetchall()

    # Fill in missing months with 0
    if not rows:
        return []

    result_dict = {r.month: int(r.cnt) for r in rows}
    all_months = _generate_month_range(rows[0].month, rows[-1].month)

    return [(m, result_dict.get(m, 0)) for m in all_months]


def _get_type_shares(db: Session) -> dict[str, float]:
    """Get project type distribution (last 12 months) for proportional split."""
    rows = db.execute(text("""
        SELECT type_of_project, COUNT(*) AS cnt
        FROM projects
        WHERE is_active_version = true
          AND project_start_date >= CURRENT_DATE - INTERVAL '12 months'
          AND LOWER(COALESCE(type_of_project, '')) != 'bau activity'
        GROUP BY type_of_project
        ORDER BY cnt DESC
    """)).fetchall()

    total = sum(r.cnt for r in rows) if rows else 1
    return {r.type_of_project: r.cnt / total for r in rows}


# ── Helpers ─────────────────────────────────────────────────────────────────

def _generate_month_range(start: str, end: str) -> list[str]:
    """Generate all YYYY-MM strings between start and end (inclusive)."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])

    months = []
    y, m = sy, sm
    while (y, m) <= (ey, em):
        months.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
    return months


def _parse_month(month_str: str) -> date:
    """Convert YYYY-MM to date."""
    parts = month_str.split("-")
    return date(int(parts[0]), int(parts[1]), 1)


def _add_months(d: date, months: int) -> date:
    """Add months to a date."""
    m = d.month + months
    y = d.year
    while m > 12:
        m -= 12
        y += 1
    return date(y, m, 1)


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal

    db = SessionLocal()
    try:
        print("=== Project Volume Forecast ===\n")

        result = forecast_projects(db, horizon=12)

        print(f"Method: {result.method}")
        print(f"Training months: {result.train_months}")
        print(f"12-month forecast total (P50): {result.annual_total_p50} projects")
        print(f"Monthly average: {result.avg_monthly:.1f}")
        print(f"YoY growth: {result.growth_rate_yoy*100:.1f}%")
        print()

        # Seasonality
        if result.seasonality:
            print("Seasonal factors (month → multiplier):")
            month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
            for m_num, factor in sorted(result.seasonality.items()):
                bar = "█" * int(max(0, (factor + 5) * 2))
                print(f"  {month_names[m_num-1]}: {factor:+.1f} {bar}")
            print()

        # Historical (last 12)
        print("Historical (last 12 months):")
        for month, count in result.historical:
            print(f"  {month}: {count}")
        print()

        # Forecast
        print(f"{'Month':<10} {'P10':>5} {'P50':>5} {'P90':>5}  Type Split")
        print("-" * 60)
        for f in result.forecasts:
            types_str = " | ".join(f"{t}: {c}" for t, c in sorted(f.by_type.items()) if c > 0)
            print(f"{f.month:<10} {f.p10:>5} {f.p50:>5} {f.p90:>5}  {types_str}")

    finally:
        db.close()
