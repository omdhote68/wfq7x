# Wind Forecast Desk — day-ahead wind forecast analytics (GB)

A pilot web application for a UK utility's **day-ahead power procurement team**. It answers two questions:

1. *What was the latest national wind-generation forecast available when the day-ahead purchase decision had to be made?*
2. *How accurate are those forecasts, quantitatively, so the uncertainty can be priced into the decision?*

Scope is limited, as the assignment specifies, to **national-level wind actuals and forecasts from Elexon BMRS** for **delivery dates 1–31 January 2026** (half-hourly).

> **AI assistance disclosure:** this project was designed and implemented with the help of AI tools (Anthropic's Claude), as permitted and required to be stated by the assignment. All code, numbers and claims should be reviewed by the author before submission.

## Status (read this first)

| Item | Status |
|---|---|
| Backend (FastAPI) and frontend (React/Vite/TS) source | Written |
| Backend pure-logic tests (selection, cutoff, metrics) | **17 pass** (see `docs/TEST_REPORT.md`) |
| Backend API + Elexon-client tests | Written, **not yet run** (the authoring sandbox could not install FastAPI/httpx) |
| Frontend build, type-check, tests | Written, **not yet run** (the sandbox could not reach npm) |
| Live Elexon API calls | **Not verified.** The sandbox blocked `data.elexon.co.uk`. Endpoint parameters are written from Elexon's conventions and must be checked with `python -m scripts.fetch_elexon_data` |
| Real data / real findings | **None yet.** Until real files exist the app shows a banner: *SYNTHETIC DEMO DATA* |
| Docker build, deployment, GitHub URL, YouTube video | **Not done** (see `docs/TEST_REPORT.md`) |

Nothing in this repository should be presented as verified real-data output until step 1 below has been run.

## Quick start

```bash
# 1. Fetch the real data (needs internet access to data.elexon.co.uk; no API key)
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m scripts.fetch_elexon_data        # writes data/real/*.json (git-ignored)

# 2. Run the API (without real files it serves clearly-labelled synthetic sample data)
uvicorn app.main:app --reload --port 8000

# 3. Run the UI (new terminal)
cd frontend && npm install && npm run dev  # http://localhost:5173 (proxies /api to :8000)
```

**Docker:** `cp .env.example .env && docker compose up --build` → UI on http://localhost:8080, API on http://localhost:8000/docs. The `./data` folder is mounted into the backend, so real data fetched on the host is picked up automatically (set `FETCH_ON_STARTUP=true` to fetch inside the container instead).

## Data sources

- Actuals: [FUELHH stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), rows with `fuelType = WIND`; fields `startTime`, `generation` (MW).
- Forecasts: [WINDFOR stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream); fields `startTime` (delivery), `publishTime` (when created), `generation` (MW).
- Attribution: *Contains BMRS data © Elexon Limited copyright and database right.*

No other dataset is used. No API key is needed.

## Methodology

**Timestamps.** Everything is parsed to UTC. `startTime` = delivery time; `publishTime` = forecast creation time. They are separate columns throughout. The fetched WINDFOR data is hourly; each hourly value is reused for the following half-hour slot to align it with FUELHH actuals. This carry-forward is an explicit assumption, not a half-hour forecast supplied by Elexon.

**Day-ahead cutoff (an assumption, not a verified market rule).** For delivery day *D* (UK local day) the cutoff is **09:00 Europe/London on D−1** (`CUTOFF_HOUR`, `CUTOFF_MINUTE`, `CUTOFF_TZ`; also adjustable per request and in the UI). The assignment says only that decisions are made "one day before the delivery day".

**Vintage selection.** For each delivery half-hour, take the forecast with the greatest `publishTime ≤ cutoff`. Later publications are never used (no look-ahead). If none exists the interval is reported `missing_forecast`; there is no fallback to a later vintage. The selected `publishTime`, cutoff and horizon are kept on every row.

**Matching and quality.** A full half-hourly calendar for the requested UK days (DST-aware: 46/50 intervals on clock-change days) is left-joined with actuals and selected forecasts. Hourly forecast values are carried into the second half-hour of each hour; this makes interval coverage complete where the underlying hourly values are present but does not add forecast detail. Quality: `ok`, `missing_actual`, `missing_forecast`, `missing_both`. Non-WIND rows, nulls, unparseable timestamps and duplicates (last wins) are dropped before matching.

**Metrics** (error = forecast − actual, MW; positive = over-forecast), over matched intervals *n*:

- MAE = mean(|e|); RMSE = √mean(e²); Bias = mean(e)
- MAPE = mean(|e| / actual) × 100, **only where actual ≥ 100 MW** (`MAPE_MIN_ACTUAL_MW`); excluded count is shown
- Energy (MWh) = Σ(MW) × 0.5 h. Sums of MW are never labelled MWh
- Coverage = matched intervals ÷ expected intervals
- Under 100 matched intervals the API flags results as indicative, not statistically reliable

## Architecture

```
React (Vite, TS, Tailwind, Recharts) ──HTTP /api──▶ FastAPI ──▶ pandas pipeline ──▶ data/real/*.json (cache)
                                                        ▲                                  ▲
                                                        └── scripts/fetch_elexon_data ──▶ Elexon BMRS
```
The frontend contains no data-processing logic; all selection and metrics are computed in the backend.

**API:** `GET /api/health`, `/api/meta`, `/api/actuals`, `/api/forecasts`, `/api/matched` (filter, search, sort, paginate), `/api/matched/export.csv`, `/api/metrics`, `/api/timeseries?granularity=half_hour|day|week`, `/api/accuracy`, `/api/revisions?delivery_date=…[&start_time=…]`. Interactive docs at `/docs`.

## Files and directories

```
backend/app/config.py        environment-based settings
backend/app/elexon.py        Elexon client: timeouts, retries with backoff, chunking
backend/app/ingest.py        downloads and caches real data
backend/app/sample.py        SYNTHETIC data for UI development only
backend/app/store.py         loads real files, else labelled sample
backend/app/selection.py     cleaning, cutoff, vintage selection, matching
backend/app/metrics.py       accuracy metrics, trends, distribution
backend/app/service.py       validation, caching, time series, revisions
backend/app/api.py           routes;  main.py = app factory, CORS, JSON logging
backend/scripts/             fetch_elexon_data.py
tests/                       pytest suites (selection, metrics, API, client)
frontend/src/components/     KPI cards, chart, accuracy, revisions, explorer, methodology
docs/                        TEST_REPORT.md, DEMO_SCRIPT.md
docker-compose.yml, .env.example, backend/Procfile, frontend/vercel.json
```

## Environment variables

See `.env.example`. Key ones: `DATA_MODE` (auto|real|sample), `FETCH_ON_STARTUP`, `CUTOFF_HOUR/MINUTE/TZ`, `MAPE_MIN_ACTUAL_MW`, `CORS_ORIGINS`, `ELEXON_BASE_URL`, `HTTP_TIMEOUT_S`, `HTTP_RETRIES`, and (frontend build) `VITE_API_BASE_URL`. No secrets exist or are required.

## Tests

```bash
pip install -r backend/requirements.txt && python -m pytest          # backend
cd frontend && npm install && npm test && npm run typecheck && npm run build
```

## Deployment

- **Backend (Render):** create a Blueprint from this repository using `render.yaml`. The service fetches the configured Elexon period on startup (`DATA_MODE=real`, `FETCH_ON_STARTUP=true`); its filesystem is ephemeral, so it re-fetches after restart. `CORS_ORIGINS` should contain the exact deployed frontend origin.
- **Frontend (Vercel):** import this repository and set the project root directory to `frontend`. Add `VITE_API_BASE_URL` with the deployed Render service URL (no trailing slash), then redeploy.
- The frontend is not usable for live analytics until the backend is deployed and `VITE_API_BASE_URL` is configured.

## Known limitations and assumptions

- Cutoff time is an assumption; check sensitivity with the cutoff control.
- WINDFOR must retain multiple publish vintages per delivery half-hour for this analysis to be meaningful. This is **unverified** until the real fetch has run. If the endpoint returns too few vintages, the analysis will show many `missing_forecast` rows and the limitation should be stated in the video.
- Elexon request parameters are unverified against the live service (see Status).
- Half-hours are autocorrelated; one month is a short sample.
- The in-memory cache is per process; the app is single-tenant and read-only.
