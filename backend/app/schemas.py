from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Quality = Literal["ok", "missing_actual", "missing_forecast", "missing_both"]


class Health(BaseModel):
    status: Literal["ok"]
    data_source: str
    version: str = "1.0.0"


class Meta(BaseModel):
    data_source: Literal["real", "sample", "none"]
    data_note: str
    period_start: str
    period_end: str
    cutoff_hour: int
    cutoff_minute: int
    cutoff_tz: str
    cutoff_rule: str
    error_convention: str = "forecast error = forecast - actual (MW); positive = over-forecast"
    mape_min_actual_mw: float
    attribution: str = "Contains BMRS data © Elexon Limited copyright and database right. Source: Elexon BMRS Insights API."


class MatchedRow(BaseModel):
    start_time: datetime
    actual_mw: Optional[float]
    forecast_mw: Optional[float]
    publish_time: Optional[datetime]
    cutoff: Optional[datetime]
    horizon_h: Optional[float]
    error_mw: Optional[float]
    abs_error_mw: Optional[float]
    pct_error: Optional[float]
    quality: Quality


class Page(BaseModel):
    total: int
    page: int
    page_size: int
    data_source: str
    items: list


class MatchedPage(Page):
    items: list[MatchedRow]


class Metrics(BaseModel):
    data_source: str
    cutoff_used: str
    intervals_expected: int
    intervals_matched: int
    coverage_pct: Optional[float]
    actual_energy_mwh: Optional[float]
    forecast_energy_mwh: Optional[float]
    matched_actual_energy_mwh: Optional[float]
    matched_forecast_energy_mwh: Optional[float]
    mae_mw: Optional[float]
    rmse_mw: Optional[float]
    mape_pct: Optional[float]
    mape_n: int
    mape_excluded: int
    mape_min_actual_mw: float
    bias_mw: Optional[float]
    bias_pct_of_actual: Optional[float]
    over_pct: Optional[float]
    under_pct: Optional[float]
    mean_over_mw: Optional[float]
    mean_under_mw: Optional[float]
    p90_abs_error_mw: Optional[float]
    sample_adequate: bool
    sample_note: Optional[str]


class TSPoint(BaseModel):
    t: str
    actual_mw: Optional[float]
    forecast_mw: Optional[float]
    error_mw: Optional[float]
    publish_time: Optional[str] = None
    n: int


class TimeSeries(BaseModel):
    data_source: str
    granularity: str
    unit: str = "MW (mean of half-hourly average power)"
    points: list[TSPoint]


class Vintage(BaseModel):
    publish_time: datetime
    is_day_ahead_vintage: bool
    after_cutoff: bool
    mae_mw: Optional[float]
    bias_mw: Optional[float]
    n: int
    points: list[dict]


class Revisions(BaseModel):
    data_source: str
    delivery_date: str
    cutoff: datetime
    mode: Literal["day", "interval"]
    actual: list[dict]
    vintages: list[Vintage]
