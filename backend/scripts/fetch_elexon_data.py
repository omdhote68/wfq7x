"""Download real Elexon data for the analysis window into data/real/.

Usage (from backend/):  python -m scripts.fetch_elexon_data [--start 2026-01-01 --end 2026-01-31]
"""
from __future__ import annotations

import argparse
import logging
from datetime import date

from app.config import get_settings
from app.elexon import ElexonError
from app.ingest import download_real_data


def main() -> int:
    s = get_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=s.period_start)
    ap.add_argument("--end", default=s.period_end)
    ap.add_argument("--lookback-days", type=int, default=3)
    a = ap.parse_args()
    logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        na, nf = download_real_data(s, date.fromisoformat(a.start), date.fromisoformat(a.end), a.lookback_days)
    except ElexonError as e:
        print(f"FAILED: {e}")
        return 1
    if not na or not nf:
        print(f"WARNING: empty result (WIND actuals={na}, WINDFOR rows={nf}); nothing saved. "
              "Check endpoint parameters against the Elexon docs.")
        return 2
    print(f"Saved {na} WIND actual rows and {nf} WINDFOR rows to {s.real_data_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
