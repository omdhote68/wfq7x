import csv
import io
from datetime import date, datetime
from typing import Literal, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from . import metrics as M
from .schemas import Health, MatchedPage, Meta, Metrics, Revisions, TimeSeries
from .service import Service

router = APIRouter(prefix="/api")


def svc(request: Request) -> Service:
    return request.app.state.service


class Window:
    """Shared validated query parameters (date range + cutoff)."""

    def __init__(self, start: Optional[date] = None, end: Optional[date] = None,
                 cutoff_hour: Optional[int] = Query(None, description="Local hour of day-ahead cutoff (0-23)"),
                 cutoff_minute: Optional[int] = Query(None, description="Minute of cutoff (0-59)"),
                 s: Service = Depends(svc)):
        self.s = s
        self.start, self.end = s.resolve_range(start, end)
        self.h, self.m = s.resolve_cutoff(cutoff_hour, cutoff_minute)

    @property
    def matched(self) -> pd.DataFrame:
        return self.s.matched(self.start, self.end, self.h, self.m)


def _page(df: pd.DataFrame, page: int, size: int) -> pd.DataFrame:
    return df.iloc[(page - 1) * size: page * size]


def _rows(df: pd.DataFrame) -> list[dict]:
    out = []
    for r in df.itertuples():
        d = r._asdict()
        d.pop("Index", None)
        out.append({k: (None if (not isinstance(v, (str, pd.Timestamp)) and pd.isna(v)) or v is pd.NaT else v)
                    for k, v in d.items()})
    return out


@router.get("/health", response_model=Health)
def health(s: Service = Depends(svc)):
    return Health(status="ok", data_source=s.store.source)


@router.get("/meta", response_model=Meta)
def meta(s: Service = Depends(svc)):
    c = s.s
    return Meta(data_source=s.store.source, data_note=s.store.note, period_start=c.period_start,
                period_end=c.period_end, cutoff_hour=c.cutoff_hour, cutoff_minute=c.cutoff_minute,
                cutoff_tz=c.cutoff_tz, mape_min_actual_mw=c.mape_min_actual_mw,
                cutoff_rule=("ASSUMPTION (not a verified market rule): for delivery day D, the latest forecast "
                             f"published at or before {c.cutoff_hour:02d}:{c.cutoff_minute:02d} {c.cutoff_tz} on D-1."))


@router.get("/actuals")
def actuals(w: Window = Depends(), page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
    a = w.s.store.actuals
    lo = w.matched["start_time"].min(); hi = w.matched["start_time"].max()
    a = a[(a["start_time"] >= lo) & (a["start_time"] <= hi)]
    return {"total": len(a), "page": page, "page_size": page_size, "data_source": w.s.store.source,
            "unit": "MW (half-hourly average power)", "items": _rows(_page(a, page, page_size))}


@router.get("/forecasts")
def forecasts(w: Window = Depends(), page: int = Query(1, ge=1), page_size: int = Query(100, ge=1, le=1000)):
    """All forecast vintages (publish_time) for deliveries in range."""
    f = w.s.store.forecasts
    lo = w.matched["start_time"].min(); hi = w.matched["start_time"].max()
    f = f[(f["start_time"] >= lo) & (f["start_time"] <= hi)]
    return {"total": len(f), "page": page, "page_size": page_size, "data_source": w.s.store.source,
            "unit": "MW", "items": _rows(_page(f, page, page_size))}


def _filter_matched(m: pd.DataFrame, quality: Optional[str], search: Optional[str],
                    min_abs_error: Optional[float], direction: Optional[str], tz: str) -> pd.DataFrame:
    if quality:
        m = m[m["quality"] == quality]
    if direction == "over":
        m = m[m["error_mw"] > 0]
    elif direction == "under":
        m = m[m["error_mw"] < 0]
    if min_abs_error is not None:
        m = m[m["abs_error_mw"] >= min_abs_error]
    if search:
        txt = m["start_time"].dt.tz_convert(tz).dt.strftime("%Y-%m-%d %H:%M")
        m = m[txt.str.contains(search.strip(), case=False, regex=False)]
    return m


@router.get("/matched", response_model=MatchedPage)
def matched(w: Window = Depends(), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500),
            quality: Optional[Literal["ok", "missing_actual", "missing_forecast", "missing_both"]] = None,
            direction: Optional[Literal["over", "under"]] = None, min_abs_error: Optional[float] = Query(None, ge=0),
            search: Optional[str] = Query(None, max_length=32), sort: Literal["asc", "desc"] = "asc"):
    m = _filter_matched(w.matched, quality, search, min_abs_error, direction, w.s.s.cutoff_tz)
    if sort == "desc":
        m = m.iloc[::-1]
    return MatchedPage(total=len(m), page=page, page_size=page_size, data_source=w.s.store.source,
                       items=_rows(_page(m, page, page_size)))


@router.get("/matched/export.csv")
def export_csv(w: Window = Depends(), quality: Optional[str] = None, direction: Optional[Literal["over", "under"]] = None,
               min_abs_error: Optional[float] = Query(None, ge=0), search: Optional[str] = Query(None, max_length=32)):
    m = _filter_matched(w.matched, quality, search, min_abs_error, direction, w.s.s.cutoff_tz)
    cols = ["start_time", "actual_mw", "forecast_mw", "publish_time", "cutoff", "horizon_h",
            "error_mw", "abs_error_mw", "pct_error", "quality"]
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(cols + ["data_source"])
    for r in m[cols].itertuples(index=False):
        wr.writerow(["" if (not isinstance(v, str) and pd.isna(v)) else (v.isoformat() if hasattr(v, "isoformat") else v)
                     for v in r] + [w.s.store.source])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="wind_forecast_vs_actual.csv"'})


@router.get("/metrics", response_model=Metrics)
def metrics(w: Window = Depends()):
    c = w.s.s
    res = M.compute_metrics(w.matched, c.mape_min_actual_mw, c.min_sample_for_stats)
    return Metrics(data_source=w.s.store.source, cutoff_used=w.s.cutoff_text(w.h, w.m), **res)


@router.get("/timeseries", response_model=TimeSeries)
def timeseries(w: Window = Depends(), granularity: Literal["half_hour", "day", "week"] = "half_hour"):
    return TimeSeries(data_source=w.s.store.source, granularity=granularity,
                      points=w.s.timeseries(w.matched, granularity))


@router.get("/accuracy")
def accuracy(w: Window = Depends(), bin_width_mw: float = Query(250.0, gt=0, le=5000)):
    mm = w.s.s.mape_min_actual_mw
    return {"data_source": w.s.store.source,
            "daily": M.trend(w.matched, "day", mm, w.s.s.cutoff_tz),
            "weekly": M.trend(w.matched, "week", mm, w.s.s.cutoff_tz),
            "by_hour": M.by_hour_of_day(w.matched, mm, w.s.s.cutoff_tz),
            "distribution": M.error_distribution(w.matched, bin_width_mw)}


@router.get("/revisions", response_model=Revisions)
def revisions(delivery_date: date, cutoff_hour: Optional[int] = None, cutoff_minute: Optional[int] = None,
              start_time: Optional[datetime] = Query(None, description="ISO UTC interval start; omit for whole day"),
              max_vintages: int = Query(8, ge=1, le=24), s: Service = Depends(svc)):
    s.resolve_range(delivery_date, delivery_date)
    h, m = s.resolve_cutoff(cutoff_hour, cutoff_minute)
    return s.revisions(delivery_date, h, m, start_time, max_vintages)
