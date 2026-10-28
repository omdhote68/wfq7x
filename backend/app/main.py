from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api import router
from .config import Settings, get_settings
from .service import Service
from .store import DataStore


class JsonFormatter(logging.Formatter):
    _std = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}

    def format(self, r: logging.LogRecord) -> str:
        d = {"ts": self.formatTime(r), "level": r.levelname, "logger": r.name, "msg": r.getMessage()}
        d.update({k: v for k, v in r.__dict__.items() if k not in self._std})
        return json.dumps(d, default=str)


def configure_logging(level: str) -> None:
    h = logging.StreamHandler()
    h.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [h]
    root.setLevel(level.upper())


def create_app(settings: Settings | None = None, store: DataStore | None = None) -> FastAPI:
    s = settings or get_settings()
    configure_logging(s.log_level)
    log = logging.getLogger("app")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        st = store or DataStore(s)
        if store is None:
            try:
                st.load()
            except FileNotFoundError as e:
                log.error("data load failed", extra={"err": str(e)})
                raise
        app.state.service = Service(st, s)
        yield

    app = FastAPI(title="Wind Forecast Procurement API", version="1.0.0", lifespan=lifespan,
                  description="National wind actuals (FUELHH) vs day-ahead forecasts (WINDFOR) from Elexon BMRS.")
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in s.cors_origins.split(",") if o.strip()],
                       allow_methods=["GET"], allow_headers=["*"])

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        t0 = time.perf_counter()
        resp = await call_next(request)
        log.info("request", extra={"path": request.url.path, "status": resp.status_code,
                                   "ms": round((time.perf_counter() - t0) * 1000, 1)})
        return resp

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception):
        log.exception("unhandled error")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})

    app.include_router(router)
    return app


app = create_app()
