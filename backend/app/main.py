"""API entry point. Run with `make run`, docs on http://localhost:8000/docs."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_engine
from app.routers import agents, health, instruments, live, market, portfolios
from app.scheduler import start_scheduler, stop_scheduler
from app.services.instrument_service import InstrumentService


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logging.basicConfig(
        level=get_settings().log_level,
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )
    with Session(get_engine()) as session:
        instrument_service = InstrumentService(session)
        instrument_service.sync_universe()
    if get_settings().app_env != "test":
        start_scheduler()
    yield
    stop_scheduler()
    get_engine().dispose()


def create_app() -> FastAPI:
    """A factory rather than a global, so each test can build its own app."""
    app = FastAPI(title="AI-Trading-Agent", lifespan=lifespan)

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    app.include_router(health.router, prefix="/api/v1")
    app.include_router(instruments.router, prefix="/api/v1")
    app.include_router(market.router, prefix="/api/v1")
    app.include_router(portfolios.router, prefix="/api/v1")
    app.include_router(agents.router, prefix="/api/v1")
    app.include_router(live.router, prefix="/api/v1")
    return app


app = create_app()
