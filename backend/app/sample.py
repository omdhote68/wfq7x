"""SYNTHETIC sample data - for UI development and tests ONLY. Not Elexon data.

Generates a deterministic wind-like series and forecast vintages whose error shrinks as the
publish time approaches delivery. Every API response derived from it is labelled
data_source="sample".
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def make_sample(start: str = "2026-01-01", end: str = "2026-01-31", seed: int = 7):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(f"{start}T00:00:00Z", f"{end}T23:30:00Z", freq="30min")
    n = len(idx)
    # slow weather regime + diurnal ripple, bounded to a plausible 0..~20 GW range
    walk = np.cumsum(rng.normal(0, 180, n))
    walk = (walk - walk.mean()) / (walk.std() + 1e-9)
    truth = np.clip(8500 + 4200 * walk + 600 * np.sin(np.arange(n) * 2 * np.pi / 48), 150, 20000)
    actual = pd.DataFrame({"startTime": idx.strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "fuelType": "WIND", "generation": truth.round(0)})
    frames = []
    pub_hours = [0, 6, 12, 18]  # sparse vintages every 6h across the 3 days before delivery
    first_pub = idx[0].normalize() - pd.Timedelta(days=3)
    pubs = pd.DatetimeIndex([first_pub + pd.Timedelta(days=d, hours=h)
                             for d in range(0, (idx[-1].normalize() - first_pub).days + 1)
                             for h in pub_hours])
    for p in pubs:
        horizon = (idx - p).total_seconds() / 3600.0
        mask = (horizon >= 0) & (horizon <= 72)
        if not mask.any():
            continue
        sd = 250 + 70 * horizon[mask]  # error grows with horizon
        f = np.clip(truth[mask] + 150 + rng.normal(0, sd), 0, None)  # small +150 MW bias
        frames.append(pd.DataFrame({"startTime": idx[mask].strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "publishTime": p.strftime("%Y-%m-%dT%H:%M:%SZ"),
                                    "generation": f.round(0)}))
    return actual, pd.concat(frames, ignore_index=True)
