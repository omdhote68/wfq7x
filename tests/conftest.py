import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.selection import clean_actuals, clean_forecasts  # noqa: E402  (pandas/numpy only)


def raw_actuals(rows):
    return pd.DataFrame([{"startTime": t, "fuelType": ft, "generation": g} for t, ft, g in rows])


def raw_forecasts(rows):
    return pd.DataFrame([{"startTime": s, "publishTime": p, "generation": g} for s, p, g in rows])


@pytest.fixture
def small_store():
    """Hand-crafted frames (no web framework needed). Delivery day 2026-01-10, cutoff 2026-01-09 09:00Z."""
    return SimpleNamespace(
        source="sample", note="test",
        actuals=clean_actuals(raw_actuals([
            ("2026-01-10T00:00:00Z", "WIND", 2500),
            ("2026-01-10T00:30:00Z", "WIND", 0),
            ("2026-01-10T00:30:00Z", "SOLAR", 5),
            ("2026-01-10T01:00:00Z", "WIND", 4000),
        ])),
        forecasts=clean_forecasts(raw_forecasts([
            ("2026-01-10T00:00:00Z", "2026-01-08T12:00:00Z", 1000),
            ("2026-01-10T00:00:00Z", "2026-01-09T08:30:00Z", 2000),
            ("2026-01-10T00:00:00Z", "2026-01-09T09:00:00Z", 3000),  # exactly at cutoff -> eligible
            ("2026-01-10T00:00:00Z", "2026-01-09T09:30:00Z", 9999),  # after cutoff -> excluded
            ("2026-01-10T00:30:00Z", "2026-01-09T08:00:00Z", 500),
            ("2026-01-10T01:00:00Z", "2026-01-09T09:30:00Z", 7777),  # only post-cutoff -> missing
        ])),
    )


@pytest.fixture
def client(small_store):
    pytest.importorskip("fastapi", reason="fastapi not installed in this environment")
    pytest.importorskip("pydantic_settings", reason="pydantic-settings not installed")
    pytest.importorskip("httpx", reason="httpx (TestClient dependency) not installed")
    from fastapi.testclient import TestClient

    from app.config import Settings
    from app.main import create_app
    from app.store import DataStore

    settings = Settings(data_mode="sample", cutoff_hour=9, cutoff_minute=0)
    st = DataStore(settings)
    st.actuals, st.forecasts, st.source, st.note = (small_store.actuals, small_store.forecasts,
                                                    "sample", "test")
    with TestClient(create_app(settings, st)) as c:
        yield c
