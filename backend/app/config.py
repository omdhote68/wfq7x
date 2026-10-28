"""Environment-based settings. No credentials: Elexon Insights API is public/keyless."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Data
    data_mode: str = "auto"  # auto | real | sample
    real_data_dir: Path = REPO_ROOT / "data" / "real"
    sample_data_dir: Path = REPO_ROOT / "data" / "sample"
    cache_dir: Path = REPO_ROOT / "data" / "cache"

    fetch_on_startup: bool = False  # download real data on boot if local files are missing

    # Elexon
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    http_timeout_s: float = 30.0
    http_retries: int = 4

    # Analysis window (delivery dates)
    period_start: str = "2026-01-01"
    period_end: str = "2026-01-31"

    # Day-ahead decision cutoff: local clock time (Europe/London) on the day BEFORE delivery.
    # ASSUMPTION - not a verified market rule. Configurable per request too.
    cutoff_hour: int = 9
    cutoff_minute: int = 0
    cutoff_tz: str = "Europe/London"

    # Metrics
    mape_min_actual_mw: float = 100.0  # actuals below this are excluded from MAPE
    min_sample_for_stats: int = 100

    # API
    cors_origins: str = "http://localhost:5173,http://localhost:3000"
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()
