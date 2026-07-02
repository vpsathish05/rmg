"""
Revenue Forecast Model — 12-month revenue prediction with confidence bands.

Approach:
  1. Holt's Linear Trend (Exponential Smoothing) on calibrated revenue series
  2. Linear Regression with headcount as leading indicator
  3. Ensemble: weighted combination of both for P50, with ±spread for P10/P90

Training Data:
  - Calibrated monthly revenue (actuals where available, FTE-estimated otherwise)
  - Monthly headcount (leading indicator — hiring precedes revenue)
  - Uses only months up to last known actual for training

Output:
  - 12-month forward forecast (P10 / P50 / P90)
  - Total annual forecast
  - Growth rate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from sklearn.linear_model import LinearRegression

from ..data_prep import HistoricalData


# ── Data classes ────────────────────────────────────────────────────────────

@dataclass
class ForecastPoint:
    """Single month forecast."""
    month: str           # YYYY-MM
    p10: float           # 10th percentile (pessimistic)
    p50: float           # 50th percentile (median/expected)
    p90: float           # 90th percentile (optimistic)


@dataclass
class RevenueForecast:
    """Complete revenue forecast result."""
    forecasts: list[ForecastPoint]
    model_version: str
    training_months: int
    last_actual_month: str
    last_actual_value: float
    annual_total_p50: float      # Sum of P50 for 12 months
    growth_rate_yoy: float       # Year-over-year growth implied
    method: str                  # Description of method used
    # Model diagnostics
    train_mape: float = 0.0      # Mean absolute % error on training data
    trend_monthly: float = 0.0   # Monthly growth trend ($)


# ── Model ───────────────────────────────────────────────────────────────────

def forecast_revenue(
    history: HistoricalData,
    headcount: Optional[dict[str, int]] = None,
    horizon: int = 12,
) -> RevenueForecast:
    """
    Generate 12-month revenue forecast from historical data.
    
    Uses ensemble of:
      - Holt's linear trend exponential smoothing
      - Headcount-based linear regression (if headcount data available)
    
    Args:
        history: HistoricalData from data_prep.reconstruct_revenue()
        headcount: Monthly headcount dict (YYYY-MM → count), optional
        horizon: Forecast horizon in months (default: 12)
    
    Returns:
        RevenueForecast with P10/P50/P90 per month
    """
    # Build training series — use calibrated revenue, stop at last actual
    calibrated = history.get_calibrated_series()

    # Find the last month with actual data
    last_actual_month = max(history.actuals.keys()) if history.actuals else ""
    last_actual_value = history.actuals.get(last_actual_month, 0.0)

    # Filter training data: only use months up to (and including) last actual
    if last_actual_month:
        train_data = [(m, v) for m, v in calibrated if m <= last_actual_month]
    else:
        # No actuals — use all calibrated data minus last month (unreliable)
        train_data = calibrated[:-1] if len(calibrated) > 2 else calibrated

    if len(train_data) < 6:
        raise ValueError(f"Insufficient training data: {len(train_data)} months (need >= 6)")

    months = [m for m, _ in train_data]
    values = np.array([v for _, v in train_data], dtype=float)

    # ── Model 1: Holt's Linear Trend ───────────────────────────────────────
    holt_forecast, holt_residuals = _holt_forecast(values, horizon)

    # ── Model 2: Headcount Regression ──────────────────────────────────────
    reg_forecast = None
    if headcount and len(headcount) >= 6:
        reg_forecast, reg_residuals = _headcount_regression(
            months, values, headcount, horizon, last_actual_month
        )

    # ── Ensemble ───────────────────────────────────────────────────────────
    if reg_forecast is not None:
        # Weight: 60% Holt (time-series), 40% regression (headcount-driven)
        ensemble = 0.6 * holt_forecast + 0.4 * reg_forecast
        residuals = holt_residuals  # Use Holt residuals for spread
    else:
        ensemble = holt_forecast
        residuals = holt_residuals

    # ── Confidence bands ───────────────────────────────────────────────────
    # Use residual std to estimate prediction intervals
    # Wider for further-out predictions
    residual_std = np.std(residuals) if len(residuals) > 0 else values[-6:].std()
    
    forecasts: list[ForecastPoint] = []
    last_month_date = _month_str_to_date(last_actual_month or months[-1])

    for i in range(horizon):
        # Next month
        next_month = _add_months(last_month_date, i + 1)
        month_str = next_month.strftime("%Y-%m")

        p50 = float(max(ensemble[i], 0))  # Can't have negative revenue

        # Spread increases with horizon (uncertainty grows)
        spread_factor = 1.0 + 0.08 * i  # 8% wider per month out
        spread = residual_std * spread_factor

        p10 = float(max(p50 - 1.28 * spread, 0))  # ~10th percentile
        p90 = float(p50 + 1.28 * spread)           # ~90th percentile

        forecasts.append(ForecastPoint(
            month=month_str,
            p10=round(p10, 2),
            p50=round(p50, 2),
            p90=round(p90, 2),
        ))

    # ── Diagnostics ────────────────────────────────────────────────────────
    # MAPE on training (in-sample fit)
    if len(holt_residuals) > 0 and np.any(values[-len(holt_residuals):] > 0):
        fitted_values = values[-len(holt_residuals):]
        mape = np.mean(np.abs(holt_residuals / fitted_values)) * 100
    else:
        mape = 0.0

    # Monthly trend
    if len(values) >= 2:
        trend = (values[-1] - values[-6]) / 6 if len(values) >= 6 else (values[-1] - values[0]) / len(values)
    else:
        trend = 0.0

    # Annual total and growth
    annual_total = sum(f.p50 for f in forecasts)
    last_12_actual = sum(values[-12:]) if len(values) >= 12 else sum(values) * (12 / len(values))
    growth_rate = (annual_total / last_12_actual - 1.0) if last_12_actual > 0 else 0.0

    return RevenueForecast(
        forecasts=forecasts,
        model_version="v1.0-holt-ensemble",
        training_months=len(train_data),
        last_actual_month=last_actual_month,
        last_actual_value=last_actual_value,
        annual_total_p50=round(annual_total, 2),
        growth_rate_yoy=round(growth_rate, 4),
        method="Holt Linear Trend + Headcount Regression Ensemble" if reg_forecast is not None
               else "Holt Linear Trend Exponential Smoothing",
        train_mape=round(mape, 2),
        trend_monthly=round(trend, 2),
    )


# ── Sub-models ──────────────────────────────────────────────────────────────

def _holt_forecast(values: np.ndarray, horizon: int) -> tuple[np.ndarray, np.ndarray]:
    """
    Holt's Linear Trend exponential smoothing.
    Good for series with clear trend but limited seasonality signal.
    """
    try:
        # Damped trend to prevent runaway extrapolation
        model = ExponentialSmoothing(
            values,
            trend="add",
            damped_trend=True,
            seasonal=None,  # No seasonality with < 24 months
        ).fit(optimized=True)

        forecast = model.forecast(horizon)
        residuals = model.resid

        return np.array(forecast), np.array(residuals)

    except Exception:
        # Fallback: simple linear extrapolation
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)
        forecast = np.polyval(slope, np.arange(len(values), len(values) + horizon))
        residuals = values - np.polyval(slope, x)
        return forecast, residuals


def _headcount_regression(
    months: list[str],
    values: np.ndarray,
    headcount: dict[str, int],
    horizon: int,
    last_actual_month: str,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Linear regression: Revenue ~ f(headcount, time_index).
    Headcount is a leading indicator — more people → more revenue capacity.
    """
    # Build feature matrix for training period
    hc_values = []
    rev_values = []
    time_indices = []

    for i, month in enumerate(months):
        if month in headcount:
            hc_values.append(headcount[month])
            rev_values.append(values[i])
            time_indices.append(i)

    if len(hc_values) < 4:
        return None, np.array([])

    X_train = np.column_stack([hc_values, time_indices])
    y_train = np.array(rev_values)

    model = LinearRegression()
    model.fit(X_train, y_train)

    residuals = y_train - model.predict(X_train)

    # Forecast: project headcount forward
    # Use last known headcount + trend
    last_hc = max(headcount.values())
    hc_trend = _estimate_headcount_trend(headcount)

    last_idx = len(months) - 1
    future_X = []
    for i in range(horizon):
        future_hc = last_hc + hc_trend * (i + 1)
        future_idx = last_idx + i + 1
        future_X.append([future_hc, future_idx])

    forecast = model.predict(np.array(future_X))
    return forecast, residuals


def _estimate_headcount_trend(headcount: dict[str, int]) -> float:
    """Estimate monthly headcount growth rate from recent months."""
    if len(headcount) < 3:
        return 0.0

    sorted_months = sorted(headcount.items())
    # Use last 6 months for trend
    recent = sorted_months[-6:]
    if len(recent) < 2:
        return 0.0

    hc_values = [v for _, v in recent]
    # Monthly change
    changes = [hc_values[i+1] - hc_values[i] for i in range(len(hc_values)-1)]
    return np.median(changes)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _month_str_to_date(month_str: str) -> date:
    """Convert YYYY-MM to date (first of month)."""
    parts = month_str.split("-")
    return date(int(parts[0]), int(parts[1]), 1)


def _add_months(d: date, months: int) -> date:
    """Add months to a date."""
    month = d.month + months
    year = d.year
    while month > 12:
        month -= 12
        year += 1
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


# ── CLI test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__file__).rsplit("/ml/", 1)[0])

    from app.database import SessionLocal
    from ml.data_prep import reconstruct_revenue, get_monthly_headcount

    db = SessionLocal()
    try:
        print("=== Revenue Forecast Model ===\n")

        # Get historical data
        history = reconstruct_revenue(db, months_back=30)
        headcount = get_monthly_headcount(db, months_back=30)

        print(f"Training data: {history.start_month} → {max(history.actuals.keys())}")
        print(f"Actuals available: {len(history.actuals)} months")
        print(f"Headcount data: {len(headcount)} months")
        print()

        # Generate forecast
        result = forecast_revenue(history, headcount, horizon=12)

        print(f"Method: {result.method}")
        print(f"Training months: {result.training_months}")
        print(f"Training MAPE: {result.train_mape:.1f}%")
        print(f"Monthly trend: ${result.trend_monthly:,.0f}")
        print(f"Last actual: {result.last_actual_month} = ${result.last_actual_value:,.0f}")
        print()

        print(f"{'Month':<10} {'P10':>12} {'P50 (Expected)':>16} {'P90':>12}")
        print("-" * 55)
        for f in result.forecasts:
            print(f"{f.month:<10} ${f.p10:>10,.0f} ${f.p50:>14,.0f} ${f.p90:>10,.0f}")

        print(f"\n{'─' * 55}")
        print(f"{'12-Month Total (P50):':<30} ${result.annual_total_p50:>14,.0f}")
        print(f"{'YoY Growth Rate:':<30} {result.growth_rate_yoy*100:>14.1f}%")
        print(f"{'Monthly Average (P50):':<30} ${result.annual_total_p50/12:>14,.0f}")

    finally:
        db.close()
