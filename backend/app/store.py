"""Loads cleaned actuals/forecasts from real files if present, else labelled synthetic sample."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd

from .config import Settings
from .sample import make_sample
from .selection import clean_actuals, clean_forecasts, expand_hourly_forecasts

log = logging.getLogger("app.store")

from .elexon import ElexonError
from .ingest import ACTUALS_FILE, FORECASTS_FILE, download_real_data


class DataStore:
    def __init__(self, settings: Settings):
        self.s = settings
        self.actuals = pd.DataFrame(columns=["start_time", "actual_mw"])
        self.forecasts = pd.DataFrame(columns=["start_time", "publish_time", "forecast_mw"])
        self.source = "none"
        self.note = ""

    def _real_available(self) -> bool:
        d = Path(self.s.real_data_dir)
        return (d / ACTUALS_FILE).exists() and (d / FORECASTS_FILE).exists()

    def load(self) -> "DataStore":
        mode = self.s.data_mode
        if mode != "sample" and self.s.fetch_on_startup and not self._real_available():
            try:
                na, nf = download_real_data(self.s)
                log.info("startup fetch complete", extra={"actuals": na, "forecasts": nf})
            except ElexonError as e:
                log.error("startup fetch failed", extra={"err": str(e)})
        if mode == "real" or (mode == "auto" and self._real_available()):
            if not self._real_available():
                raise FileNotFoundError(
                    f"DATA_MODE=real but {ACTUALS_FILE}/{FORECASTS_FILE} missing in {self.s.real_data_dir}. "
                    "Run: python -m scripts.fetch_elexon_data")
            d = Path(self.s.real_data_dir)
            self.actuals = clean_actuals(pd.DataFrame(json.loads((d / ACTUALS_FILE).read_text())))
            self.forecasts = expand_hourly_forecasts(
                clean_forecasts(pd.DataFrame(json.loads((d / FORECASTS_FILE).read_text())))
            )
            self.source = "real"
            self.note = ("Elexon BMRS FUELHH (WIND) and WINDFOR, loaded from local files. "
                         "Hourly WINDFOR values are reused for the following half-hour slot.")
        else:
            a, f = make_sample(self.s.period_start, self.s.period_end)
            self.actuals, self.forecasts = clean_actuals(a), clean_forecasts(f)
            self.source = "sample"
            self.note = ("SYNTHETIC DEMO DATA - not Elexon data. For UI development only. "
                         "Run `python -m scripts.fetch_elexon_data` and restart to use real data.")
        log.info("data loaded", extra={"source": self.source, "actuals": len(self.actuals),
                                       "forecasts": len(self.forecasts)})
        return self
