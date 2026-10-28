from datetime import date

import numpy as np
import pandas as pd

from app.selection import (build_matched, clean_actuals, clean_forecasts, cutoff_for_delivery_day,
                           expand_hourly_forecasts, expected_grid, select_day_ahead)
from conftest import raw_actuals, raw_forecasts


def test_cutoff_is_previous_day_local_time_in_utc():
    c = cutoff_for_delivery_day(date(2026, 1, 10), 9, 0)
    assert c.isoformat() == "2026-01-09T09:00:00+00:00"
    # BST: 09:00 London is 08:00 UTC
    assert cutoff_for_delivery_day(date(2026, 7, 10), 9, 0).isoformat() == "2026-07-09T08:00:00+00:00"


def test_selects_latest_eligible_and_excludes_after_cutoff(small_store):
    sel = select_day_ahead(small_store.forecasts, 9, 0).set_index("start_time")
    first = sel.loc[pd.Timestamp("2026-01-10T00:00:00Z")]
    assert first.forecast_mw == 3000  # at-cutoff included, 09:30 (9999) excluded
    assert first.publish_time == pd.Timestamp("2026-01-09T09:00:00Z")
    assert first.horizon_h == 15.0


def test_never_falls_back_to_post_cutoff_forecast(small_store):
    sel = select_day_ahead(small_store.forecasts, 9, 0)
    assert pd.Timestamp("2026-01-10T01:00:00Z") not in set(sel.start_time)
    assert 7777 not in set(sel.forecast_mw) and 9999 not in set(sel.forecast_mw)


def test_cutoff_is_configurable(small_store):
    sel = select_day_ahead(small_store.forecasts, 8, 45).set_index("start_time")
    assert sel.loc[pd.Timestamp("2026-01-10T00:00:00Z")].forecast_mw == 2000
    late = select_day_ahead(small_store.forecasts, 10, 0).set_index("start_time")
    assert late.loc[pd.Timestamp("2026-01-10T00:00:00Z")].forecast_mw == 9999
    assert late.loc[pd.Timestamp("2026-01-10T01:00:00Z")].forecast_mw == 7777


def test_clean_actuals_filters_wind_dedupes_and_drops_nulls():
    df = clean_actuals(raw_actuals([
        ("2026-01-01T00:00:00Z", "WIND", 100), ("2026-01-01T00:00:00Z", "WIND", 110),  # dup keeps last
        ("2026-01-01T00:00:00Z", "NUCLEAR", 5000), ("2026-01-01T00:30:00Z", "WIND", None),
        ("bad-date", "WIND", 3),
    ]))
    assert list(df.actual_mw) == [110.0]


def test_clean_forecasts_dedupes_and_drops_nulls():
    df = clean_forecasts(raw_forecasts([
        ("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", 1), ("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", 2),
        ("2026-01-02T00:30:00Z", "2026-01-01T00:00:00Z", None), ("2026-01-02T00:30:00Z", None, 5),
    ]))
    assert len(df) == 1 and df.forecast_mw.iloc[0] == 2


def test_hourly_forecasts_are_reused_for_following_half_hour():
    df = clean_forecasts(raw_forecasts([
        ("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", 100),
        ("2026-01-02T01:00:00Z", "2026-01-01T00:00:00Z", 200),
    ]))

    expanded = expand_hourly_forecasts(df).set_index("start_time")

    assert expanded.loc[pd.Timestamp("2026-01-02T00:00:00Z")].forecast_mw == 100
    assert expanded.loc[pd.Timestamp("2026-01-02T00:30:00Z")].forecast_mw == 100
    assert expanded.loc[pd.Timestamp("2026-01-02T01:00:00Z")].forecast_mw == 200
    assert expanded.loc[pd.Timestamp("2026-01-02T01:30:00Z")].forecast_mw == 200


def test_half_hour_forecasts_are_not_expanded():
    df = clean_forecasts(raw_forecasts([
        ("2026-01-02T00:00:00Z", "2026-01-01T00:00:00Z", 100),
        ("2026-01-02T00:30:00Z", "2026-01-01T00:00:00Z", 150),
        ("2026-01-02T01:00:00Z", "2026-01-01T00:00:00Z", 200),
    ]))

    assert len(expand_hourly_forecasts(df)) == len(df)


def test_hourly_forecasts_match_both_half_hour_actuals():
    actuals = clean_actuals(raw_actuals([
        ("2026-01-02T00:00:00Z", "WIND", 110),
        ("2026-01-02T00:30:00Z", "WIND", 120),
        ("2026-01-02T01:00:00Z", "WIND", 130),
        ("2026-01-02T01:30:00Z", "WIND", 140),
    ]))
    forecasts = expand_hourly_forecasts(clean_forecasts(raw_forecasts([
        ("2026-01-02T00:00:00Z", "2026-01-01T08:00:00Z", 100),
        ("2026-01-02T01:00:00Z", "2026-01-01T08:00:00Z", 200),
    ])))

    matched = build_matched(actuals, forecasts, date(2026, 1, 2), date(2026, 1, 2))
    first_four = matched.iloc[:4]

    assert (first_four.quality == "ok").all()
    assert list(first_four.forecast_mw) == [100, 100, 200, 200]


def test_expected_grid_january_has_48_per_day():
    assert len(expected_grid(date(2026, 1, 1), date(2026, 1, 31))) == 48 * 31


def test_expected_grid_handles_dst():
    assert len(expected_grid(date(2026, 3, 29), date(2026, 3, 29))) == 46  # spring forward
    assert len(expected_grid(date(2026, 10, 25), date(2026, 10, 25))) == 50  # fall back


def test_matching_quality_flags_and_error_sign(small_store):
    m = build_matched(small_store.actuals, small_store.forecasts, date(2026, 1, 10), date(2026, 1, 10), 9, 0)
    assert len(m) == 48
    r0 = m[m.start_time == pd.Timestamp("2026-01-10T00:00:00Z")].iloc[0]
    assert r0.quality == "ok" and r0.error_mw == 500 and r0.abs_error_mw == 500  # 3000 - 2500
    r1 = m[m.start_time == pd.Timestamp("2026-01-10T00:30:00Z")].iloc[0]
    assert r1.actual_mw == 0 and r1.error_mw == 500 and np.isnan(r1.pct_error)  # zero actual: no pct
    r2 = m[m.start_time == pd.Timestamp("2026-01-10T01:00:00Z")].iloc[0]
    assert r2.quality == "missing_forecast" and np.isnan(r2.error_mw)
    assert (m.quality == "missing_both").sum() == 45


def test_pct_error_threshold(small_store):
    m = build_matched(small_store.actuals, small_store.forecasts, date(2026, 1, 10), date(2026, 1, 10), 9, 0,
                      mape_min_actual_mw=100)
    r0 = m[m.start_time == pd.Timestamp("2026-01-10T00:00:00Z")].iloc[0]
    assert round(r0.pct_error, 6) == 20.0
