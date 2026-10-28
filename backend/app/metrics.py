"""Accuracy metrics. Convention: error = forecast - actual (MW).
Positive error = over-forecast, negative = under-forecast.
Energy: half-hourly average MW x 0.5 h = MWh. Sums of MW are never labelled MWh.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

HALF_HOUR_H = 0.5


def _f(x) -> float | None:
    if x is None:
        return None
    x = float(x)
    return None if math.isnan(x) or math.isinf(x) else round(x, 4)


def compute_metrics(m: pd.DataFrame, mape_min_actual_mw: float = 100.0, min_sample: int = 100) -> dict:
    total = len(m)
    ok = m[m["quality"] == "ok"]
    n = len(ok)
    out: dict = {
        "intervals_expected": int(total),
        "intervals_matched": int(n),
        "coverage_pct": _f(n / total * 100) if total else None,
        "actual_energy_mwh": _f(m["actual_mw"].sum(skipna=True) * HALF_HOUR_H),
        "forecast_energy_mwh": _f(m["forecast_mw"].sum(skipna=True) * HALF_HOUR_H),
        "matched_actual_energy_mwh": _f(ok["actual_mw"].sum() * HALF_HOUR_H) if n else None,
        "matched_forecast_energy_mwh": _f(ok["forecast_mw"].sum() * HALF_HOUR_H) if n else None,
        "mape_min_actual_mw": mape_min_actual_mw,
        "sample_adequate": n >= min_sample,
        "sample_note": None,
    }
    if n == 0:
        out.update(mae_mw=None, rmse_mw=None, mape_pct=None, bias_mw=None, mape_n=0,
                   mape_excluded=0, over_pct=None, under_pct=None, mean_over_mw=None,
                   mean_under_mw=None, p90_abs_error_mw=None, bias_pct_of_actual=None)
        out["sample_note"] = "No matched intervals in the selected range."
        return out
    err = ok["error_mw"].to_numpy(dtype=float)
    act = ok["actual_mw"].to_numpy(dtype=float)
    valid = act >= mape_min_actual_mw
    over, under = err > 0, err < 0
    out.update(
        mae_mw=_f(np.mean(np.abs(err))),
        rmse_mw=_f(math.sqrt(np.mean(err**2))),
        bias_mw=_f(np.mean(err)),
        mape_pct=_f(np.mean(np.abs(err[valid]) / act[valid]) * 100) if valid.any() else None,
        mape_n=int(valid.sum()),
        mape_excluded=int((~valid).sum()),
        over_pct=_f(over.mean() * 100),
        under_pct=_f(under.mean() * 100),
        mean_over_mw=_f(err[over].mean()) if over.any() else None,
        mean_under_mw=_f(err[under].mean()) if under.any() else None,
        p90_abs_error_mw=_f(np.percentile(np.abs(err), 90)),
        bias_pct_of_actual=_f(err.sum() / act.sum() * 100) if act.sum() else None,
    )
    if n < min_sample:
        out["sample_note"] = (
            f"Only {n} matched intervals (<{min_sample}); treat metrics as indicative, "
            "not statistically reliable."
        )
    return out


def _agg(g: pd.DataFrame, mape_min: float) -> dict:
    ok = g[g["quality"] == "ok"]
    n = len(ok)
    if n == 0:
        return {"n": 0, "mae_mw": None, "rmse_mw": None, "bias_mw": None,
                "mape_pct": None, "actual_mean_mw": None, "forecast_mean_mw": None}
    err = ok["error_mw"].to_numpy(float)
    act = ok["actual_mw"].to_numpy(float)
    v = act >= mape_min
    return {
        "n": int(n),
        "mae_mw": _f(np.mean(np.abs(err))),
        "rmse_mw": _f(math.sqrt(np.mean(err**2))),
        "bias_mw": _f(np.mean(err)),
        "mape_pct": _f(np.mean(np.abs(err[v]) / act[v]) * 100) if v.any() else None,
        "actual_mean_mw": _f(act.mean()),
        "forecast_mean_mw": _f(ok["forecast_mw"].mean()),
    }


def trend(m: pd.DataFrame, freq: str, mape_min: float, tz: str = "Europe/London") -> list[dict]:
    """freq: 'day' | 'week' (ISO week starting Monday). Returns per-period accuracy."""
    if m.empty:
        return []
    local = m["start_time"].dt.tz_convert(tz)
    if freq == "day":
        key = local.dt.strftime("%Y-%m-%d")
    elif freq == "week":
        key = (local.dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time).dt.strftime("%Y-%m-%d")
    else:
        raise ValueError("freq must be 'day' or 'week'")
    rows = []
    for k, g in m.groupby(key, sort=True):
        rows.append({"period": k, **_agg(g, mape_min)})
    return rows


def by_hour_of_day(m: pd.DataFrame, mape_min: float, tz: str = "Europe/London") -> list[dict]:
    if m.empty:
        return []
    hr = m["start_time"].dt.tz_convert(tz).dt.hour
    return [{"hour": int(h), **_agg(g, mape_min)} for h, g in m.groupby(hr, sort=True)]


def error_distribution(m: pd.DataFrame, bin_width_mw: float = 250.0) -> list[dict]:
    ok = m[m["quality"] == "ok"]
    if ok.empty:
        return []
    err = ok["error_mw"].to_numpy(float)
    lo = math.floor(err.min() / bin_width_mw) * bin_width_mw
    hi = math.ceil((err.max() + 1e-9) / bin_width_mw) * bin_width_mw
    edges = np.arange(lo, hi + bin_width_mw, bin_width_mw)
    counts, edges = np.histogram(err, bins=edges)
    return [
        {"bin_start_mw": float(edges[i]), "bin_end_mw": float(edges[i + 1]), "count": int(c)}
        for i, c in enumerate(counts)
    ]
