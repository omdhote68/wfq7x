"""Download real Elexon data to local JSON files (the cache the API reads from)."""
from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta, timezone

from .config import Settings
from .elexon import fetch_fuelhh_wind, fetch_windfor

ACTUALS_FILE = "fuelhh_wind.json"
FORECASTS_FILE = "windfor.json"


def download_real_data(s: Settings, start: date | None = None, end: date | None = None,
                       lookback_days: int = 3) -> tuple[int, int]:
    """Fetch WIND actuals for delivery dates start..end and WINDFOR vintages published from
    `lookback_days` before start to the end of `end`. Raises ElexonError on failure."""
    start = start or date.fromisoformat(s.period_start)
    end = end or date.fromisoformat(s.period_end)
    actuals = fetch_fuelhh_wind(start, end, s.elexon_base_url, s.http_timeout_s, s.http_retries)
    pf = datetime.combine(start - timedelta(days=lookback_days), time(0), timezone.utc)
    pt = datetime.combine(end + timedelta(days=1), time(0), timezone.utc)
    forecasts = fetch_windfor(pf, pt, s.elexon_base_url, s.http_timeout_s, s.http_retries)
    if actuals and forecasts:  # never overwrite a good cache with an empty response
        out = s.real_data_dir
        out.mkdir(parents=True, exist_ok=True)
        (out / ACTUALS_FILE).write_text(json.dumps(actuals))
        (out / FORECASTS_FILE).write_text(json.dumps(forecasts))
    return len(actuals), len(forecasts)
