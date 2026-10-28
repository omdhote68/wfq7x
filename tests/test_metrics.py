import math

import pandas as pd

from app.metrics import compute_metrics, error_distribution, trend


def frame(rows):
    df = pd.DataFrame(rows, columns=["start_time", "actual_mw", "forecast_mw"])
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    df["error_mw"] = df.forecast_mw - df.actual_mw
    df["quality"] = "ok"
    return df


ROWS = [("2026-01-01T00:00:00Z", 1000, 1100), ("2026-01-01T00:30:00Z", 2000, 1800),
        ("2026-01-01T01:00:00Z", 0, 50), ("2026-01-02T00:00:00Z", 500, 500)]


def test_core_metrics_hand_computed():
    m = compute_metrics(frame(ROWS), mape_min_actual_mw=100, min_sample=2)
    errs = [100, -200, 50, 0]
    assert m["mae_mw"] == 87.5
    assert m["rmse_mw"] == round(math.sqrt(sum(e * e for e in errs) / 4), 4)
    assert m["bias_mw"] == -12.5
    # MAPE excludes the zero actual: (10% + 10% + 0%) / 3
    assert m["mape_n"] == 3 and m["mape_excluded"] == 1
    assert abs(m["mape_pct"] - 6.6667) < 1e-3
    assert m["over_pct"] == 50.0 and m["under_pct"] == 25.0


def test_energy_uses_half_hour_factor_not_raw_sum():
    m = compute_metrics(frame(ROWS), min_sample=1)
    assert m["actual_energy_mwh"] == (1000 + 2000 + 0 + 500) * 0.5
    assert m["forecast_energy_mwh"] == (1100 + 1800 + 50 + 500) * 0.5


def test_coverage_and_missing_values():
    df = frame(ROWS)
    miss = df.iloc[:1].copy()
    miss["quality"], miss["forecast_mw"], miss["error_mw"] = "missing_forecast", None, None
    allm = pd.concat([df, miss], ignore_index=True)
    m = compute_metrics(allm, min_sample=1)
    assert m["intervals_expected"] == 5 and m["intervals_matched"] == 4 and m["coverage_pct"] == 80.0


def test_empty_and_small_sample_flags():
    empty = frame(ROWS).iloc[:0]
    m = compute_metrics(empty)
    assert m["mae_mw"] is None and m["intervals_matched"] == 0 and "No matched" in m["sample_note"]
    small = compute_metrics(frame(ROWS), min_sample=100)
    assert small["sample_adequate"] is False and "not statistically reliable" in small["sample_note"]


def test_all_actuals_below_mape_threshold_gives_null_mape():
    m = compute_metrics(frame([("2026-01-01T00:00:00Z", 0, 10)]), mape_min_actual_mw=100, min_sample=1)
    assert m["mape_pct"] is None and m["mae_mw"] == 10


def test_trend_daily_and_weekly():
    d = trend(frame(ROWS), "day", 100)
    assert [r["period"] for r in d] == ["2026-01-01", "2026-01-02"]
    assert d[0]["n"] == 3 and d[1]["mae_mw"] == 0
    w = trend(frame(ROWS), "week", 100)
    assert len(w) == 1 and w[0]["period"] == "2025-12-29"  # Monday of ISO week


def test_error_distribution_counts_sum_to_n():
    dist = error_distribution(frame(ROWS), 100)
    assert sum(b["count"] for b in dist) == 4
