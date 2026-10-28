"""Elexon BMRS Insights API client (public, keyless).

IMPORTANT: written from Elexon's published conventions but NOT live-verified in the
authoring environment (egress to data.elexon.co.uk was blocked). Assumptions to verify
with `python -m scripts.fetch_elexon_data`:
  - Base URL https://data.elexon.co.uk/bmrs/api/v1
  - /datasets/FUELHH/stream accepts settlementDateFrom/To and fuelType; returns a JSON
    array with startTime, settlementDate, settlementPeriod, fuelType, generation (MW).
  - /datasets/WINDFOR/stream accepts publishDateTimeFrom/To; returns a JSON array with
    startTime, publishTime, generation (MW). Multiple publishTime vintages may exist per
    startTime - this is what makes a historical day-ahead cut-off analysis possible.
Requests are chunked to stay within any per-request range limits.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime, timedelta, timezone

import httpx

log = logging.getLogger("app.elexon")


class ElexonError(RuntimeError):
    """Base error for failed Elexon requests or unexpected response data."""


class ElexonRequestError(ElexonError):
    """Non-retryable client/request error (for example, HTTP 400)."""


def _get_json(client: httpx.Client, url: str, params: dict, retries: int) -> list[dict]:
    delay = 1.0
    last: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            r = client.get(url, params=params)
            if r.status_code == 429 or r.status_code >= 500:
                # Rate limits and server errors can be transient, so retry these.
                raise ElexonError(f"Retryable HTTP {r.status_code} from Elexon")
            if r.status_code >= 400:
                # Invalid query parameters and other 4xx responses will not improve
                # after retrying; surface them immediately instead of wasting time.
                raise ElexonRequestError(f"Non-retryable HTTP {r.status_code} from Elexon: {r.text[:300]}")
            body = r.json()
            if isinstance(body, dict):  # non-stream endpoints wrap in {"data": [...]}
                if "data" not in body or not isinstance(body["data"], list):
                    raise ElexonError("Unexpected response object (expected a list or an object with list-valued 'data')")
                body = body["data"]
            if not isinstance(body, list):
                raise ElexonError("Unexpected response shape (expected JSON array)")
            return body
        except ElexonRequestError:
            raise
        except (httpx.HTTPError, ElexonError, ValueError) as e:
            last = e
            log.warning("elexon request failed", extra={"attempt": attempt, "url": url, "err": str(e)})
            if attempt < retries:
                time.sleep(delay)
                delay *= 2
    raise ElexonError(f"Elexon request failed after {retries} attempts: {last}")


def _chunks(start: date, end: date, days: int):
    cur = start
    while cur <= end:
        nxt = min(cur + timedelta(days=days - 1), end)
        yield cur, nxt
        cur = nxt + timedelta(days=1)


def fetch_fuelhh_wind(start: date, end: date, base_url: str, timeout: float = 30.0, retries: int = 4,
                      chunk_days: int = 7) -> list[dict]:
    rows: list[dict] = []
    with httpx.Client(timeout=timeout) as c:
        for a, b in _chunks(start, end, chunk_days):
            part = _get_json(c, f"{base_url}/datasets/FUELHH/stream",
                             {"settlementDateFrom": a.isoformat(), "settlementDateTo": b.isoformat(),
                              "fuelType": "WIND"}, retries)
            log.info("fetched FUELHH", extra={"from": str(a), "to": str(b), "rows": len(part)})
            rows += [r for r in part if str(r.get("fuelType", "")).upper() == "WIND"]
    return rows


def fetch_windfor(publish_from: datetime, publish_to: datetime, base_url: str, timeout: float = 30.0,
                  retries: int = 4, chunk_days: int = 3) -> list[dict]:
    rows: list[dict] = []
    cur = publish_from
    with httpx.Client(timeout=timeout) as c:
        while cur < publish_to:
            nxt = min(cur + timedelta(days=chunk_days), publish_to)
            fmt = "%Y-%m-%dT%H:%M:%SZ"
            part = _get_json(c, f"{base_url}/datasets/WINDFOR/stream",
                             {"publishDateTimeFrom": cur.astimezone(timezone.utc).strftime(fmt),
                              "publishDateTimeTo": nxt.astimezone(timezone.utc).strftime(fmt)}, retries)
            log.info("fetched WINDFOR", extra={"from": cur.isoformat(), "rows": len(part)})
            rows += part
            cur = nxt
    return rows
