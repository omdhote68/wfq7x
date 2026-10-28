# Test report (authoring sandbox)

Environment: Linux sandbox, Python 3.13 (pandas 3.0.5, numpy 2.5.3, pytest 9.1.1), Node 22. **Outbound access was restricted**: `data.elexon.co.uk`, `pypi.org` and the npm registry all returned HTTP 403 from the egress proxy (policy denial), so FastAPI, httpx, pydantic-settings and all npm packages could not be installed and the live API could not be called.

| Check | Command | Result |
|---|---|---|
| Backend pure-logic tests (selection, cutoff, DST grid, dedupe/nulls, metrics, trends) | `python3 -I -m pytest -q` | **17 passed**, 1 module skipped |
| API + Elexon-client tests (`tests/test_api.py`) | same | **Skipped**: fastapi/httpx not installed. Not executed, so not evidence of correctness |
| Python syntax of all backend modules | `python3 -m py_compile backend/app/*.py backend/scripts/*.py` | OK (syntax only) |
| Pipeline smoke test on **synthetic** data (1,488 intervals; 0 selected forecasts published after cutoff) | ad-hoc script | Ran; numbers are synthetic and carry no business meaning |
| `docker compose config -q` | | Valid (static check only) |
| `docker compose up --build` | | **Not run** (image pulls blocked) |
| Frontend `npm test`, `npm run typecheck`, `npm run build` | | **Not run** (npm blocked) |
| Live Elexon integration | `python -m scripts.fetch_elexon_data` | **Not run**; must be run on a machine with access |

## Unresolved / to do by the author

1. Run `python -m scripts.fetch_elexon_data`; if it reports empty results or HTTP 4xx, compare parameters with the endpoint docs and adjust `backend/app/elexon.py`.
2. Install dependencies, run `pytest` (all suites), `npm test`, `npm run typecheck`, `npm run build`; fix anything that fails (the frontend has never been compiled).
3. Verify `docker compose up --build`.
4. Deploy, create the public repo, record the video.
