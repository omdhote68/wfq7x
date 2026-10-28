import pytest

pytest.importorskip("fastapi", reason="fastapi not installed")
pytest.importorskip("httpx", reason="httpx not installed")
pytest.importorskip("pydantic_settings", reason="pydantic-settings not installed")

from app.elexon import ElexonError, _get_json  # noqa: E402

DAY = {"start": "2026-01-10", "end": "2026-01-10"}


def test_health_and_meta(client):
    assert client.get("/api/health").json() == {"status": "ok", "data_source": "sample", "version": "1.0.0"}
    m = client.get("/api/meta").json()
    assert m["data_source"] == "sample" and "ASSUMPTION" in m["cutoff_rule"] and "Elexon" in m["attribution"]


def test_matched_pagination_and_fields(client):
    r = client.get("/api/matched", params={**DAY, "page_size": 10, "page": 1}).json()
    assert r["total"] == 48 and len(r["items"]) == 10
    first = r["items"][0]
    assert first["forecast_mw"] == 3000 and first["actual_mw"] == 2500 and first["error_mw"] == 500
    assert first["publish_time"].startswith("2026-01-09T09:00")
    p5 = client.get("/api/matched", params={**DAY, "page_size": 10, "page": 5}).json()
    assert len(p5["items"]) == 8


def test_matched_filters(client):
    r = client.get("/api/matched", params={**DAY, "quality": "ok"}).json()
    assert r["total"] == 2
    r = client.get("/api/matched", params={**DAY, "direction": "over"}).json()
    assert r["total"] == 2
    r = client.get("/api/matched", params={**DAY, "search": "00:30"}).json()
    assert r["total"] == 1


def test_metrics_endpoint(client):
    m = client.get("/api/metrics", params=DAY).json()
    assert m["intervals_matched"] == 2 and m["mae_mw"] == 500.0 and m["sample_adequate"] is False
    assert m["actual_energy_mwh"] == (2500 + 0 + 4000) * 0.5


def test_cutoff_override_changes_selection(client):
    r = client.get("/api/matched", params={**DAY, "cutoff_hour": 8, "cutoff_minute": 45, "page_size": 1}).json()
    assert r["items"][0]["forecast_mw"] == 2000


def test_invalid_filters(client):
    assert client.get("/api/metrics", params={"start": "2026-01-10", "end": "2026-01-05"}).status_code == 400
    assert client.get("/api/metrics", params={"start": "2025-12-01", "end": "2026-01-05"}).status_code == 400
    assert client.get("/api/metrics", params={"start": "not-a-date"}).status_code == 422
    assert client.get("/api/metrics", params={**DAY, "cutoff_hour": 25}).status_code == 400
    assert client.get("/api/matched", params={**DAY, "page": 0}).status_code == 422
    assert client.get("/api/matched", params={**DAY, "page_size": 100000}).status_code == 422


def test_csv_export(client):
    r = client.get("/api/matched/export.csv", params={**DAY, "quality": "ok"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("start_time,actual_mw,forecast_mw,publish_time") and len(lines) == 3
    assert lines[1].endswith(",sample")


def test_timeseries_granularity(client):
    hh = client.get("/api/timeseries", params=DAY).json()
    assert len(hh["points"]) == 48
    d = client.get("/api/timeseries", params={**DAY, "granularity": "day"}).json()
    assert len(d["points"]) == 1 and d["points"][0]["n"] == 2
    assert client.get("/api/timeseries", params={**DAY, "granularity": "year"}).status_code == 422


def test_accuracy_endpoint(client):
    a = client.get("/api/accuracy", params=DAY).json()
    assert len(a["daily"]) == 1 and a["distribution"] and a["by_hour"]


def test_revisions_interval_marks_day_ahead_vintage(client):
    r = client.get("/api/revisions", params={"delivery_date": "2026-01-10", "start_time": "2026-01-10T00:00:00Z"}).json()
    by_pub = {v["publish_time"][:16]: v for v in r["vintages"]}
    assert len(r["vintages"]) == 4
    assert by_pub["2026-01-09T09:00"]["is_day_ahead_vintage"] is True
    late = by_pub["2026-01-09T09:30"]
    assert late["after_cutoff"] is True and late["is_day_ahead_vintage"] is False
    assert r["actual"][0]["actual_mw"] == 2500


def test_revisions_day_mode(client):
    r = client.get("/api/revisions", params={"delivery_date": "2026-01-10"}).json()
    assert r["mode"] == "day" and sum(v["is_day_ahead_vintage"] for v in r["vintages"]) == 1


def test_revisions_outside_period_rejected(client):
    assert client.get("/api/revisions", params={"delivery_date": "2026-03-01"}).status_code == 400


# ---- Elexon client error handling (no network) ----------------------------
class FakeResp:
    def __init__(self, status=200, body=None, text="mock response"):
        self.status_code, self._b, self.text = status, body, text

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx
            raise httpx.HTTPStatusError("x", request=None, response=None)

    def json(self):
        return self._b


class FakeClient:
    def __init__(self, seq):
        self.seq, self.calls = list(seq), 0

    def get(self, url, params=None):
        self.calls += 1
        item = self.seq.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_elexon_retries_then_succeeds(monkeypatch):
    import httpx
    monkeypatch.setattr("app.elexon.time.sleep", lambda s: None)
    c = FakeClient([FakeResp(503), httpx.ConnectTimeout("t"), FakeResp(200, [{"a": 1}])])
    assert _get_json(c, "u", {}, 4) == [{"a": 1}] and c.calls == 3


def test_elexon_raises_after_retries(monkeypatch):
    monkeypatch.setattr("app.elexon.time.sleep", lambda s: None)
    c = FakeClient([FakeResp(500)] * 3)
    with pytest.raises(ElexonError):
        _get_json(c, "u", {}, 3)
    assert c.calls == 3


def test_elexon_rejects_unexpected_shape(monkeypatch):
    monkeypatch.setattr("app.elexon.time.sleep", lambda s: None)
    with pytest.raises(ElexonError):
        _get_json(FakeClient([FakeResp(200, "oops")]), "u", {}, 1)


def test_elexon_unwraps_data_envelope():
    assert _get_json(FakeClient([FakeResp(200, {"data": [1, 2]})]), "u", {}, 1) == [1, 2]


def test_elexon_does_not_retry_non_retryable_4xx(monkeypatch):
    from app.elexon import ElexonRequestError
    monkeypatch.setattr("app.elexon.time.sleep", lambda s: None)
    c = FakeClient([FakeResp(400, text="invalid date range"), FakeResp(200, [])])
    with pytest.raises(ElexonRequestError, match="HTTP 400"):
        _get_json(c, "u", {}, 4)
    assert c.calls == 1


def test_elexon_rejects_unexpected_object_shape():
    with pytest.raises(ElexonError, match="response object"):
        _get_json(FakeClient([FakeResp(200, {"unexpected": []})]), "u", {}, 1)
