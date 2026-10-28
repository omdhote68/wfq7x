"""Query-level logic shared by routes: validation, matching (cached), aggregation."""
from __future__ import annotations

from datetime import date, datetime

import numpy as np
import pandas as pd
from fastapi import HTTPException

from .config import Settings
from .selection import build_matched, cutoff_for_delivery_day, delivery_day_of
from .store import DataStore


class Service:
    def __init__(self, store: DataStore, settings: Settings):
        self.store, self.s = store, settings
        self._cache: dict[tuple, pd.DataFrame] = {}

    # ---- validation -------------------------------------------------------
    def resolve_range(self, start: date | None, end: date | None) -> tuple[date, date]:
        p0, p1 = date.fromisoformat(self.s.period_start), date.fromisoformat(self.s.period_end)
        start, end = start or p0, end or p1
        if start > end:
            raise HTTPException(400, "start must be on or before end")
        if start < p0 or end > p1:
            raise HTTPException(400, f"Date range must lie within {p0} to {p1} (delivery dates)")
        return start, end

    def resolve_cutoff(self, hour: int | None, minute: int | None) -> tuple[int, int]:
        h = self.s.cutoff_hour if hour is None else hour
        m = self.s.cutoff_minute if minute is None else minute
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise HTTPException(400, "cutoff_hour must be 0-23 and cutoff_minute 0-59")
        return h, m

    # ---- matching ---------------------------------------------------------
    def matched(self, start: date, end: date, hour: int, minute: int) -> pd.DataFrame:
        key = (start, end, hour, minute, self.store.source)
        if key not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[key] = build_matched(
                self.store.actuals, self.store.forecasts, start, end, hour, minute,
                self.s.cutoff_tz, self.s.mape_min_actual_mw)
        return self._cache[key]

    def cutoff_text(self, hour: int, minute: int) -> str:
        return f"{hour:02d}:{minute:02d} {self.s.cutoff_tz} on the day before delivery"

    # ---- time series ------------------------------------------------------
    def timeseries(self, m: pd.DataFrame, granularity: str) -> list[dict]:
        if granularity == "half_hour":
            return [
                {"t": r.start_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "actual_mw": _n(r.actual_mw), "forecast_mw": _n(r.forecast_mw),
                 "error_mw": _n(r.error_mw),
                 "publish_time": None if pd.isna(r.publish_time) else r.publish_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                 "n": 1}
                for r in m.itertuples()
            ]
        # aggregate only over intervals where both exist so means are comparable
        ok = m[m["quality"] == "ok"].copy()
        local = ok["start_time"].dt.tz_convert(self.s.cutoff_tz)
        if granularity == "day":
            key = local.dt.strftime("%Y-%m-%d")
        else:
            key = local.dt.tz_localize(None).dt.to_period("W-SUN").dt.start_time.dt.strftime("%Y-%m-%d")
        out = []
        for k, g in ok.groupby(key, sort=True):
            out.append({"t": k, "actual_mw": _n(g.actual_mw.mean()), "forecast_mw": _n(g.forecast_mw.mean()),
                        "error_mw": _n(g.error_mw.mean()), "publish_time": None, "n": int(len(g))})
        return out

    # ---- revisions --------------------------------------------------------
    def revisions(self, delivery: date, hour: int, minute: int, start_time: datetime | None,
                  max_vintages: int) -> dict:
        tz = self.s.cutoff_tz
        cutoff = cutoff_for_delivery_day(delivery, hour, minute, tz)
        f, a = self.store.forecasts, self.store.actuals
        fd = f[delivery_day_of(f["start_time"], tz) == delivery] if not f.empty else f
        ad = a[delivery_day_of(a["start_time"], tz) == delivery] if not a.empty else a
        base = {"data_source": self.store.source, "delivery_date": delivery.isoformat(), "cutoff": cutoff}
        if start_time is not None:
            st = pd.Timestamp(start_time)
            st = st.tz_localize("UTC") if st.tzinfo is None else st.tz_convert("UTC")
            fi = fd[fd["start_time"] == st].sort_values("publish_time")
            act = ad[ad["start_time"] == st]
            actual_v = None if act.empty else float(act["actual_mw"].iloc[0])
            elig = fi[fi["publish_time"] <= cutoff]
            sel_pub = elig["publish_time"].max() if not elig.empty else None
            vint = []
            for r in fi.itertuples():
                err = None if actual_v is None else r.forecast_mw - actual_v
                vint.append({"publish_time": r.publish_time,
                             "is_day_ahead_vintage": sel_pub is not None and r.publish_time == sel_pub,
                             "after_cutoff": bool(r.publish_time > cutoff),
                             "mae_mw": None if err is None else abs(err), "bias_mw": err, "n": 1,
                             "points": [{"t": st.strftime("%Y-%m-%dT%H:%M:%SZ"), "forecast_mw": float(r.forecast_mw),
                                         "horizon_h": float((st - r.publish_time).total_seconds() / 3600)}]})
            return {**base, "mode": "interval",
                    "actual": [] if actual_v is None else [{"t": st.strftime("%Y-%m-%dT%H:%M:%SZ"), "actual_mw": actual_v}],
                    "vintages": vint}
        pubs = sorted(fd["publish_time"].unique())
        elig_pubs = [p for p in pubs if p <= cutoff]
        sel_pub = max(elig_pubs) if elig_pubs else None
        if len(pubs) > max_vintages:
            keep = set(np.array(pubs, dtype=object)[np.linspace(0, len(pubs) - 1, max_vintages).round().astype(int)])
            if sel_pub is not None:
                keep.add(sel_pub)
            pubs = sorted(keep)
        amap = dict(zip(ad["start_time"], ad["actual_mw"]))
        vint = []
        for p in pubs:
            g = fd[fd["publish_time"] == p].sort_values("start_time")
            errs = [fv - amap[t] for t, fv in zip(g["start_time"], g["forecast_mw"]) if t in amap]
            vint.append({"publish_time": p, "is_day_ahead_vintage": sel_pub is not None and p == sel_pub,
                         "after_cutoff": bool(p > cutoff),
                         "mae_mw": float(np.mean(np.abs(errs))) if errs else None,
                         "bias_mw": float(np.mean(errs)) if errs else None, "n": len(errs),
                         "points": [{"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "forecast_mw": float(v)}
                                    for t, v in zip(g["start_time"], g["forecast_mw"])]})
        return {**base, "mode": "day",
                "actual": [{"t": t.strftime("%Y-%m-%dT%H:%M:%SZ"), "actual_mw": float(v)}
                           for t, v in zip(ad["start_time"], ad["actual_mw"])],
                "vintages": vint}


def _n(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) or pd.isna(x) else round(float(x), 3)
