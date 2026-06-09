"""Time-series analysis engine for Instagram reference monitoring.

This module is intentionally free of any web / database / network concerns.
Everything operates on plain ``pandas.Series`` objects indexed by a
``DatetimeIndex`` so the analytics are deterministic and unit-testable.

The functions here form the analytical core of the service: regularising
irregular snapshots onto a fixed grid, smoothing, growth/momentum metrics,
rolling z-score anomaly detection and a Holt double-exponential-smoothing
forecast (implemented in NumPy so we don't pull in statsmodels).
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Series preparation
# ---------------------------------------------------------------------------


def to_series(points: list[tuple[Any, float]], name: str = "value") -> pd.Series:
    """Build a sorted, datetime-indexed series from ``(timestamp, value)`` pairs.

    Duplicate timestamps are collapsed to their mean so that two snapshots
    captured within the same instant don't create a degenerate index.
    """
    if not points:
        return pd.Series(dtype="float64", name=name)

    index = pd.to_datetime([p[0] for p in points], utc=True)
    values = pd.to_numeric([p[1] for p in points], errors="coerce")
    series = pd.Series(values, index=index, name=name)
    series = series.groupby(level=0).mean().sort_index()
    return series


def resample_series(series: pd.Series, freq: str = "1D", how: str = "last") -> pd.Series:
    """Regularise an irregularly sampled series onto a fixed ``freq`` grid.

    Snapshots arrive whenever the collector happens to run, so before any
    windowed maths we project them onto an evenly spaced grid. Gaps are
    forward-filled because cumulative metrics (followers, total likes) persist
    until the next observation.
    """
    if series.empty:
        return series

    agg = {"last": "last", "mean": "mean", "max": "max", "sum": "sum"}.get(how, "last")
    resampled = series.resample(freq).agg(agg)
    return resampled.ffill()


# ---------------------------------------------------------------------------
# Smoothing
# ---------------------------------------------------------------------------


def moving_average(series: pd.Series, window: int = 7) -> pd.Series:
    """Simple moving average; ``min_periods=1`` so early points aren't dropped."""
    if series.empty:
        return series
    window = max(1, int(window))
    return series.rolling(window=window, min_periods=1).mean()


def ema(series: pd.Series, span: int = 7) -> pd.Series:
    """Exponential moving average (more weight on recent observations)."""
    if series.empty:
        return series
    span = max(1, int(span))
    return series.ewm(span=span, adjust=False).mean()


# ---------------------------------------------------------------------------
# Growth & momentum
# ---------------------------------------------------------------------------


def growth_metrics(series: pd.Series) -> dict[str, float | None]:
    """Headline growth figures over the full observed window."""
    clean = series.dropna()
    if len(clean) < 2:
        return {
            "start": float(clean.iloc[0]) if len(clean) else None,
            "current": float(clean.iloc[-1]) if len(clean) else None,
            "absolute_change": None,
            "percent_change": None,
            "avg_daily_growth": None,
            "cagr_daily_pct": None,
        }

    start = float(clean.iloc[0])
    current = float(clean.iloc[-1])
    absolute = current - start
    percent = (absolute / start * 100.0) if start else None

    span_days = (clean.index[-1] - clean.index[0]).total_seconds() / 86400.0
    avg_daily = absolute / span_days if span_days > 0 else None

    cagr_daily = None
    if span_days > 0 and start > 0 and current > 0:
        cagr_daily = ((current / start) ** (1.0 / span_days) - 1.0) * 100.0

    return {
        "start": start,
        "current": current,
        "absolute_change": absolute,
        "percent_change": percent,
        "avg_daily_growth": avg_daily,
        "cagr_daily_pct": cagr_daily,
    }


def momentum(series: pd.Series, window: int = 7) -> pd.Series:
    """Rate of change vs ``window`` steps ago, as a percentage.

    Positive momentum means the metric is accelerating relative to its level
    one window ago; it's the signal that flags an account "heating up".
    """
    if series.empty:
        return series
    window = max(1, int(window))
    shifted = series.shift(window)
    with np.errstate(divide="ignore", invalid="ignore"):
        roc = (series - shifted) / shifted.replace(0, np.nan) * 100.0
    return roc


# ---------------------------------------------------------------------------
# Anomaly detection
# ---------------------------------------------------------------------------


@dataclass
class Anomaly:
    timestamp: str
    value: float
    zscore: float
    direction: str  # "spike" or "drop"


def rolling_zscore_anomalies(
    series: pd.Series, window: int = 14, threshold: float = 2.5
) -> list[Anomaly]:
    """Flag points whose rolling z-score exceeds ``threshold``.

    Uses a trailing window so an anomaly is judged only against the behaviour
    that preceded it (no look-ahead). Useful for catching a viral post or a
    sudden follower drop.
    """
    clean = series.dropna()
    if len(clean) < max(3, window // 2):
        return []

    window = max(2, int(window))
    roll = clean.rolling(window=window, min_periods=max(2, window // 2))
    mean = roll.mean()
    std = roll.std(ddof=0)

    anomalies: list[Anomaly] = []
    for ts, value in clean.items():
        m = mean.get(ts)
        s = std.get(ts)
        if m is None or s is None or not np.isfinite(s) or s == 0:
            continue
        z = (value - m) / s
        if abs(z) >= threshold:
            anomalies.append(
                Anomaly(
                    timestamp=pd.Timestamp(ts).isoformat(),
                    value=float(value),
                    zscore=float(z),
                    direction="spike" if z > 0 else "drop",
                )
            )
    return anomalies


# ---------------------------------------------------------------------------
# Forecasting (Holt's linear trend / double exponential smoothing)
# ---------------------------------------------------------------------------


@dataclass
class Forecast:
    timestamps: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)
    method: str = "holt_linear"
    alpha: float = 0.5
    beta: float = 0.3


def holt_forecast(
    series: pd.Series,
    horizon: int = 7,
    alpha: float = 0.5,
    beta: float = 0.3,
    freq: str | None = None,
) -> Forecast:
    """Forecast ``horizon`` future steps with Holt's linear method.

    Double exponential smoothing captures both level and trend, which fits
    follower / engagement curves better than a flat mean. Implemented directly
    so the only runtime dependency is NumPy.
    """
    clean = series.dropna()
    if len(clean) < 2:
        return Forecast(method="insufficient_data", alpha=alpha, beta=beta)

    values = clean.to_numpy(dtype="float64")

    level = values[0]
    trend = values[1] - values[0]
    for y in values[1:]:
        prev_level = level
        level = alpha * y + (1 - alpha) * (level + trend)
        trend = beta * (level - prev_level) + (1 - beta) * trend

    # Infer the cadence of the history to place future timestamps.
    if freq is not None:
        step = pd.tseries.frequencies.to_offset(freq)
        future_index = pd.date_range(
            start=clean.index[-1], periods=horizon + 1, freq=step
        )[1:]
    else:
        if len(clean.index) >= 2:
            delta = clean.index[-1] - clean.index[-2]
        else:
            delta = pd.Timedelta(days=1)
        future_index = [clean.index[-1] + delta * (h + 1) for h in range(horizon)]

    forecasts = [float(level + (h + 1) * trend) for h in range(horizon)]
    return Forecast(
        timestamps=[pd.Timestamp(t).isoformat() for t in future_index],
        values=forecasts,
        method="holt_linear",
        alpha=alpha,
        beta=beta,
    )


# ---------------------------------------------------------------------------
# Top-level summary
# ---------------------------------------------------------------------------


def _series_to_records(series: pd.Series) -> list[dict[str, Any]]:
    return [
        {"t": pd.Timestamp(ts).isoformat(), "v": (None if pd.isna(v) else float(v))}
        for ts, v in series.items()
    ]


def analyze(
    points: list[tuple[Any, float]],
    *,
    freq: str = "1D",
    ma_window: int = 7,
    ema_span: int = 7,
    momentum_window: int = 7,
    anomaly_window: int = 14,
    anomaly_threshold: float = 2.5,
    forecast_horizon: int = 7,
    name: str = "value",
) -> dict[str, Any]:
    """Run the full analysis pipeline and return a JSON-serialisable dict.

    This is the single entry point the API layer calls; everything above is a
    composable building block that this function wires together.
    """
    raw = to_series(points, name=name)
    series = resample_series(raw, freq=freq)

    ma = moving_average(series, window=ma_window)
    ema_s = ema(series, span=ema_span)
    mom = momentum(series, window=momentum_window)
    anomalies = rolling_zscore_anomalies(
        series, window=anomaly_window, threshold=anomaly_threshold
    )
    forecast = holt_forecast(series, horizon=forecast_horizon, freq=freq)

    last_momentum = None
    mom_clean = mom.dropna()
    if not mom_clean.empty:
        last_momentum = float(mom_clean.iloc[-1])

    return {
        "name": name,
        "freq": freq,
        "count": int(series.dropna().shape[0]),
        "series": _series_to_records(series),
        "moving_average": _series_to_records(ma),
        "ema": _series_to_records(ema_s),
        "momentum": _series_to_records(mom),
        "latest_momentum_pct": last_momentum,
        "growth": growth_metrics(series),
        "anomalies": [asdict(a) for a in anomalies],
        "forecast": asdict(forecast),
        "trend": _classify_trend(series),
    }


def _classify_trend(series: pd.Series) -> str:
    """Cheap human-readable label derived from a least-squares slope."""
    clean = series.dropna()
    if len(clean) < 2:
        return "unknown"
    x = np.arange(len(clean), dtype="float64")
    y = clean.to_numpy(dtype="float64")
    slope = np.polyfit(x, y, 1)[0]
    scale = np.mean(np.abs(y)) or 1.0
    norm = slope / scale
    if norm > 0.01:
        return "rising"
    if norm < -0.01:
        return "falling"
    return "flat"
