"""Deterministic unit tests for the time-series engine (no network/DB)."""

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from app import timeseries as ts


def _linear_points(n=30, start=1000, step=50, day0=None):
    day0 = day0 or datetime(2026, 1, 1, tzinfo=timezone.utc)
    return [(day0 + timedelta(days=i), start + i * step) for i in range(n)]


def test_to_series_sorts_and_dedupes():
    day0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [
        (day0 + timedelta(days=2), 30.0),
        (day0, 10.0),
        (day0, 20.0),  # duplicate timestamp -> mean with the line above
    ]
    s = ts.to_series(points)
    assert list(s.index) == sorted(s.index)
    assert s.iloc[0] == pytest.approx(15.0)  # mean of 10 and 20
    assert s.iloc[-1] == 30.0


def test_to_series_empty():
    assert ts.to_series([]).empty


def test_resample_fills_gaps():
    day0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    points = [(day0, 100.0), (day0 + timedelta(days=3), 130.0)]
    s = ts.resample_series(ts.to_series(points), freq="1D")
    assert len(s) == 4  # day 0,1,2,3
    assert s.iloc[1] == 100.0  # forward filled
    assert s.iloc[-1] == 130.0


def test_moving_average_smooths():
    s = ts.resample_series(ts.to_series(_linear_points()), freq="1D")
    ma = ts.moving_average(s, window=5)
    assert len(ma) == len(s)
    assert not ma.isna().any()  # min_periods=1
    # On a linear series the MA lags the raw value but stays monotone.
    assert ma.is_monotonic_increasing


def test_growth_metrics_linear():
    points = _linear_points(n=11, start=1000, step=100)  # 1000 -> 2000 over 10 days
    s = ts.resample_series(ts.to_series(points), freq="1D")
    g = ts.growth_metrics(s)
    assert g["start"] == 1000
    assert g["current"] == 2000
    assert g["absolute_change"] == 1000
    assert g["percent_change"] == pytest.approx(100.0)
    assert g["avg_daily_growth"] == pytest.approx(100.0)


def test_growth_metrics_insufficient():
    g = ts.growth_metrics(ts.to_series([(datetime(2026, 1, 1, tzinfo=timezone.utc), 5.0)]))
    assert g["absolute_change"] is None


def test_momentum_positive_on_growth():
    s = ts.resample_series(ts.to_series(_linear_points()), freq="1D")
    mom = ts.momentum(s, window=7).dropna()
    assert (mom > 0).all()


def test_anomaly_detection_flags_spike():
    points = _linear_points(n=30, start=1000, step=10)
    # inject a large spike at day 20
    points[20] = (points[20][0], 100000.0)
    s = ts.resample_series(ts.to_series(points), freq="1D")
    anomalies = ts.rolling_zscore_anomalies(s, window=10, threshold=2.5)
    assert any(a.direction == "spike" for a in anomalies)
    assert any(abs(a.value - 100000.0) < 1 for a in anomalies)


def test_no_anomaly_on_clean_linear():
    s = ts.resample_series(ts.to_series(_linear_points(n=40)), freq="1D")
    # A pure ramp has a stable rolling deviation; nothing should breach 3 sigma.
    anomalies = ts.rolling_zscore_anomalies(s, window=10, threshold=3.0)
    assert anomalies == []


def test_holt_forecast_continues_trend():
    points = _linear_points(n=20, start=1000, step=50)
    s = ts.resample_series(ts.to_series(points), freq="1D")
    fc = ts.holt_forecast(s, horizon=5, freq="1D")
    assert fc.method == "holt_linear"
    assert len(fc.values) == 5
    assert len(fc.timestamps) == 5
    # Forecast should keep climbing and stay near the +50/day slope.
    assert fc.values[0] < fc.values[-1]
    diffs = np.diff(fc.values)
    assert np.allclose(diffs, diffs[0])  # constant step
    assert fc.values[0] == pytest.approx(2000.0, rel=0.05)  # next after last (1950)


def test_holt_forecast_insufficient():
    fc = ts.holt_forecast(ts.to_series([(datetime(2026, 1, 1, tzinfo=timezone.utc), 5.0)]))
    assert fc.method == "insufficient_data"


def test_classify_trend():
    rising = ts.resample_series(ts.to_series(_linear_points(start=100, step=10)), freq="1D")
    falling = ts.resample_series(ts.to_series(_linear_points(start=1000, step=-10)), freq="1D")
    flat = ts.resample_series(
        ts.to_series([(datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(days=i), 500.0) for i in range(10)]),
        freq="1D",
    )
    assert ts._classify_trend(rising) == "rising"
    assert ts._classify_trend(falling) == "falling"
    assert ts._classify_trend(flat) == "flat"


def test_analyze_end_to_end():
    points = _linear_points(n=30, start=1000, step=40)
    result = ts.analyze(points, freq="1D", forecast_horizon=7)
    assert result["count"] == 30
    assert result["trend"] == "rising"
    assert len(result["forecast"]["values"]) == 7
    assert result["growth"]["absolute_change"] == pytest.approx(29 * 40)
    assert result["latest_momentum_pct"] is not None
    # everything must be JSON-serialisable (no numpy/pandas leaking out)
    import json

    json.dumps(result)


def test_analyze_empty():
    result = ts.analyze([])
    assert result["count"] == 0
    assert result["trend"] == "unknown"
