# Demo video script (unlisted YouTube, ≤ 10 min total)

**Before recording:** run the real data fetch, start the app, and confirm the amber *SYNTHETIC DEMO DATA* banner is **gone**. Read every `[FILL: …]` value off the dashboard; do not say a number you have not seen on screen. If the real data shows few forecast vintages, say so (see "If results are weaker than hoped").

## Part 1 — Customer presentation (target 4:30)

| Time | Screen action | Script |
|---|---|---|
| 0:00 | Overview tab | "Your team buys power in the day-ahead market, a day before delivery. Wind output is weather-driven, so every purchase relies on a forecast. Two questions matter: what forecast did we actually have at decision time, and how wrong is it likely to be?" |
| 0:40 | Point at filter bar and cutoff | "We reconstruct the decision point. For each half-hour, we use only the latest national wind forecast published before the day-ahead cutoff, currently 09:00 UK time the day before. Nothing published later leaks in. The cutoff is adjustable." |
| 1:20 | KPI cards | "Across [FILL: dates] the grid produced [FILL: actual GWh] of wind; the decision-time forecast implied [FILL: forecast GWh]. Mean absolute error is [FILL: MAE] MW, RMSE [FILL: RMSE] MW, and bias [FILL: bias, with sign] MW. Coverage is [FILL: coverage]% of half-hours." |
| 2:00 | Actual vs forecast chart; switch to daily, hover a miss | "Teal is the forecast you'd have had; black is what happened. Hovering shows delivery time, forecast, actual, when the forecast was published, and the error. Error is always forecast minus actual." |
| 2:40 | Accuracy tab | "Over-forecasts happened [FILL: over %] of the time, under-forecasts [FILL: under %]. Nine in ten half-hours missed by less than [FILL: p90] MW. The worst days were [FILL: from daily chart]." |
| 3:30 | Revisions tab, pick a notable day | "Here is how successive forecasts for one day changed. The thick line is the decision-time vintage; dashed lines arrived after you had to commit. [FILL: describe whether later vintages were closer, using the vintage table MAEs.]" |
| 4:10 | Explorer, export CSV | "Every number is traceable to a half-hour row and exportable for your own models." |
| 4:25 | Methodology tab | "Method, assumptions and Elexon attribution are documented in-app. Our next step would be sizing a buffer for the procurement volume from these error statistics." Close. |

**Rules for findings:** state only what the screen shows. Mention the one-month sample and the assumed cutoff once. Do not call results statistically significant.

## Part 2 — Technical review (target 4:30)

| Time | Screen action | Script |
|---|---|---|
| 0:00 | README architecture diagram | "React/Vite/TypeScript frontend, FastAPI backend with pandas. The frontend only renders; all selection and metrics live in the backend." |
| 0:40 | `backend/app/elexon.py` | "Keyless Elexon client with timeouts, exponential-backoff retries, and chunked requests. `ingest.py` caches results to local JSON and never overwrites a good cache with an empty response." |
| 1:20 | `selection.py` | "Timestamps are UTC. Delivery time and publish time are separate fields. The cutoff is D-1 at a configurable local time; I keep the greatest `publishTime ≤ cutoff` per `startTime`. No fallback to later vintages. Matching is on a full DST-aware calendar so gaps show as missing." |
| 2:10 | `metrics.py` | "Error is forecast minus actual. MAPE excludes small actuals under a threshold and reports the exclusion count. Energy is MW times 0.5 hours." |
| 2:50 | `api.py`, `/docs` | "Pydantic models, validated date ranges returning 400, pagination, CSV export, CORS from env, JSON logs." |
| 3:20 | `tests/` and terminal | "Tests cover cutoff boundary (exactly at cutoff is eligible), post-cutoff exclusion, duplicates, nulls, zero actuals, invalid ranges, retry behaviour. [FILL: state exactly which suites you ran and their results.]" |
| 3:55 | docker-compose, Procfile, vercel.json | "Compose runs both services with health checks; Vercel serves the frontend and a Heroku-style host the API. [FILL: say whether deployment is live.]" |
| 4:15 | README limitations | "Known limits: assumed cutoff, one month of data, reliance on WINDFOR keeping multiple vintages. To extend: add a new metric in `metrics.py` and an endpoint in `api.py`." |

## If results are weaker than hoped
If WINDFOR returned few vintages or coverage is low, say so plainly in both parts. That limitation is a finding.

## Recording and upload checklist
1. Record screen + mic (OBS or QuickTime), 1080p, two takes ≤ 5 min each, or one ≤ 10 min file with a clear spoken "Part 2" break.
2. Upload to YouTube → Visibility **Unlisted**.
3. Open the link in an incognito window to verify access.
4. Put the link in the README and in the submission (done by you; the form was not accessed by this tool).

*Status: no video has been recorded or uploaded.*
