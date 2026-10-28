"""Day-ahead forecast vintage selection and actual/forecast matching.

Terminology (kept strictly separate everywhere):
  start_time   - delivery (target) half-hour, UTC. From Elexon `startTime`.
  publish_time - when the forecast was created, UTC. From Elexon `publishTime`.
  cutoff       - historical day-ahead decision time for a delivery day D:
                 (D - 1 day) at cutoff_hour:cutoff_minute Europe/London, converted to UTC.
A forecast is eligible only if publish_time <= cutoff (no look-ahead).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

UTC = ZoneInfo("UTC")


def to_utc_series(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s, utc=True, errors="coerce")


def clean_actuals(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep WIND only, normalise timestamps, drop null/duplicate rows (keep last)."""
    cols = ["start_time", "actual_mw"]
    if raw.empty:
        return pd.DataFrame(columns=cols)
    df = raw.copy()
    if "fuelType" in df.columns:
        df = df[df["fuelType"].astype(str).str.upper() == "WIND"]
    df["start_time"] = to_utc_series(df["startTime"])
    df["actual_mw"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["start_time", "actual_mw"])
    df = df.drop_duplicates(subset=["start_time"], keep="last")
    return df[cols].sort_values("start_time").reset_index(drop=True)


def clean_forecasts(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalise timestamps, drop nulls, dedupe (start_time, publish_time) keeping last."""
    cols = ["start_time", "publish_time", "forecast_mw"]
    if raw.empty:
        return pd.DataFrame(columns=cols)
    df = raw.copy()
    df["start_time"] = to_utc_series(df["startTime"])
    df["publish_time"] = to_utc_series(df["publishTime"])
    df["forecast_mw"] = pd.to_numeric(df["generation"], errors="coerce")
    df = df.dropna(subset=["start_time", "publish_time", "forecast_mw"])
    df = df.drop_duplicates(subset=["start_time", "publish_time"], keep="last")
    return df[cols].sort_values(["start_time", "publish_time"]).reset_index(drop=True)


def expand_hourly_forecasts(forecasts: pd.DataFrame) -> pd.DataFrame:
    """Apply hourly WINDFOR values to both half-hour slots in each delivery hour.

    Expansion is only applied to forecast vintages whose observed delivery cadence
    is hourly. Existing half-hourly vintages are left unchanged.
    """
    if forecasts.empty:
        return forecasts.copy()

    expanded = [forecasts]
    for _, vintage in forecasts.groupby("publish_time", sort=False):
        starts = vintage["start_time"].drop_duplicates().sort_values()
        if len(starts) < 2:
            continue
        steps = starts.diff().dropna()
        if steps.median() != pd.Timedelta(hours=1):
            continue

        half_hour = vintage.copy()
        half_hour["start_time"] += pd.Timedelta(minutes=30)
        existing = set(zip(vintage["start_time"], vintage["publish_time"]))
        half_hour = half_hour[
            ~half_hour.apply(lambda row: (row["start_time"], row["publish_time"]) in existing, axis=1)
        ]
        expanded.append(half_hour)

    return (
        pd.concat(expanded, ignore_index=True)
        .drop_duplicates(["start_time", "publish_time"], keep="first")
        .sort_values(["start_time", "publish_time"])
        .reset_index(drop=True)
    )


def cutoff_for_delivery_day(
    delivery_day: date, hour: int, minute: int, tz: str = "Europe/London"
) -> datetime:
    """Cutoff (UTC) for deliveries on `delivery_day`: previous day at hour:minute local."""
    local = datetime.combine(delivery_day - timedelta(days=1), time(hour, minute), ZoneInfo(tz))
    return local.astimezone(UTC)


def delivery_day_of(start_times: pd.Series, tz: str = "Europe/London") -> pd.Series:
    return start_times.dt.tz_convert(tz).dt.date


def select_day_ahead(
    forecasts: pd.DataFrame, hour: int = 9, minute: int = 0, tz: str = "Europe/London"
) -> pd.DataFrame:
    """For each start_time pick the latest forecast with publish_time <= cutoff.

    Returns columns: start_time, publish_time, forecast_mw, cutoff, horizon_h.
    Intervals with no eligible forecast are simply absent (they surface as missing
    forecasts downstream; we never fall back to a later vintage).
    """
    cols = ["start_time", "publish_time", "forecast_mw", "cutoff", "horizon_h"]
    if forecasts.empty:
        return pd.DataFrame(columns=cols)
    df = forecasts.copy()
    day = delivery_day_of(df["start_time"], tz)
    cutoff_map = {d: cutoff_for_delivery_day(d, hour, minute, tz) for d in day.unique()}
    df["cutoff"] = pd.to_datetime(day.map(cutoff_map), utc=True)
    eligible = df[df["publish_time"] <= df["cutoff"]]
    if eligible.empty:
        return pd.DataFrame(columns=cols)
    eligible = eligible.sort_values(["start_time", "publish_time"])
    sel = eligible.groupby("start_time", as_index=False).tail(1).copy()
    sel["horizon_h"] = (sel["start_time"] - sel["publish_time"]).dt.total_seconds() / 3600.0
    return sel[cols].sort_values("start_time").reset_index(drop=True)


def expected_grid(start: date, end: date, tz: str = "Europe/London") -> pd.DatetimeIndex:
    """All half-hour starts (UTC) for local days start..end inclusive (handles DST days)."""
    s = datetime.combine(start, time(0, 0), ZoneInfo(tz)).astimezone(UTC)
    e = datetime.combine(end + timedelta(days=1), time(0, 0), ZoneInfo(tz)).astimezone(UTC)
    return pd.date_range(s, e, freq="30min", inclusive="left", tz="UTC")


def build_matched(
    actuals: pd.DataFrame,
    forecasts: pd.DataFrame,
    start: date,
    end: date,
    hour: int = 9,
    minute: int = 0,
    tz: str = "Europe/London",
    mape_min_actual_mw: float = 100.0,
) -> pd.DataFrame:
    """Full expected half-hourly grid left-joined with actuals and selected forecasts.

    error = forecast - actual (MW). pct_error is NaN when actual < mape_min_actual_mw.
    quality: ok | missing_actual | missing_forecast | missing_both
    """
    grid = pd.DataFrame({"start_time": expected_grid(start, end, tz)})
    sel = select_day_ahead(forecasts, hour, minute, tz)
    m = grid.merge(actuals, on="start_time", how="left").merge(sel, on="start_time", how="left")
    m["error_mw"] = m["forecast_mw"] - m["actual_mw"]
    m["abs_error_mw"] = m["error_mw"].abs()
    valid_pct = m["actual_mw"] >= mape_min_actual_mw
    m["pct_error"] = np.where(valid_pct, m["error_mw"] / m["actual_mw"] * 100.0, np.nan)
    has_a, has_f = m["actual_mw"].notna(), m["forecast_mw"].notna()
    m["quality"] = np.select(
        [has_a & has_f, ~has_a & has_f, has_a & ~has_f],
        ["ok", "missing_actual", "missing_forecast"],
        default="missing_both",
    )
    return m
