# Independent project audit

Audit date: 2026-10-28

## Summary

The ZIP contains a substantial implementation of the assignment: React + TypeScript frontend, FastAPI backend, Elexon ingestion/client modules, cutoff-aware forecast selection, metric calculations, a Docker Compose setup, unit/API tests, README, and a two-part demo script.

The project is **not submission-ready yet**, primarily because real Elexon data has not been fetched or verified, frontend dependencies could not be installed in this environment, and there is no verified public repository, deployment, or video URL.

## Checks run during this audit

| Check | Result |
|---|---|
| Python compilation (`python -m compileall -q backend/app backend/scripts`) | Passed |
| Backend + API test suite (`python -m pytest -q`) after audit fixes | **35 passed** |
| Live Elexon requests | Not verified: runtime DNS/network resolution to `data.elexon.co.uk` failed |
| Frontend npm install/build/tests | Not run: npm install could not complete in the restricted network environment; no `node_modules` or lockfile was produced |
| Docker build/run | Not run: Docker CLI is not installed in this environment |
| GitHub publication, hosting deployment, YouTube upload | Not done; no credentials or authenticated hosting context available |

## Data and calculation review

### Sound design elements

- The code keeps delivery `startTime` separate from forecast `publishTime`.
- The decision cutoff is explicitly labelled as an assumption: 09:00 Europe/London on D-1. It is configurable and is not presented as an official market rule.
- The selector uses the latest forecast where `publishTime <= cutoff`; it does not fall back to a post-cutoff forecast.
- The expected grid is created in UK local time and converted to UTC, accounting for DST interval counts.
- Actuals are filtered to `fuelType == WIND` in the ingestion client.
- Error is consistently forecast minus actual; MAE/RMSE/bias use matched rows only.
- Half-hourly average MW is converted to MWh using a 0.5-hour factor.
- MAPE excludes actual values below a configurable 100 MW threshold and reports excluded counts.
- Synthetic data is clearly marked in the application and must not be used as real findings.

### Unresolved data risks

1. The Elexon request parameters and actual historical result shape have not been confirmed by a live request from this environment. Run the fetch script from a machine with network access and inspect row counts and timestamps.
2. The analysis depends on WINDFOR retaining the forecast vintages needed to reconstruct the D-1 cutoff. Confirm that the fetched data contains multiple historical `publishTime` values per delivery `startTime`; otherwise the retrospective analysis may have low coverage or may not be possible from that endpoint alone.
3. The 09:00 D-1 cutoff is an explicit analytical assumption because the assignment does not state a precise clock time.
4. MAPE uses a 100 MW actual-generation threshold to avoid unstable percentages around zero. This is a documented methodological choice, not an assignment-mandated threshold.

## Fix made during audit

`backend/app/elexon.py` previously retried all HTTP 4xx responses, even though invalid request parameters do not become valid through retrying. It also silently treated a JSON object without a list-valued `data` field as an empty dataset. The client now fails immediately for non-retryable 4xx responses and rejects malformed object responses explicitly. Regression tests were added. The full Python suite passes: 35 tests.

## Required before submission

1. On a network-enabled machine, run the fetch script and verify non-empty actuals and forecast rows for January 2026.
2. Check forecast vintage coverage and the selected day-ahead cutoff vintage; inspect missing-forecast counts and confirm the UI shows real-data mode, not the synthetic banner.
3. Run frontend `npm install`, `npm test`, `npm run typecheck`, and `npm run build`; resolve any errors.
4. Run `docker compose up --build` and test `/api/health` and the dashboard.
5. Create and verify the public anonymous GitHub repository.
6. Deploy the frontend and backend, set `VITE_API_BASE_URL` and production `CORS_ORIGINS`, then verify both URLs.
7. Record and upload the two-part unlisted demo (maximum 10 minutes) and verify access in an incognito window.
8. Complete the submission yourself. The Microsoft submission form was not accessed as instructed.
