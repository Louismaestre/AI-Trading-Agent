import datetime
from collections.abc import Iterator
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.llm import FakeLLM
from app.main import create_app
from app.models import DailyPrice, Instrument, LiveSession, LiveSessionStatus
from app.routers.live import get_live_service
from app.schemas.agents import AnalystDecision
from app.services.instrument_service import InstrumentService
from app.services.live_service import LiveService
from app.services.market_data_service import MarketDataService

PARIS = ZoneInfo("Europe/Paris")
TUESDAY = datetime.datetime(2026, 9, 29, 10, 0, tzinfo=PARIS)


@pytest.fixture
def service(db_session: Session) -> LiveService:
    InstrumentService(db_session).sync_universe()
    return LiveService(
        db_session,
        llm=FakeLLM(
            [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
        ),
        market=MarketDataService(db_session, fetch_intraday=lambda _ticker, _start: []),
    )


@pytest.fixture
def client(db_session: Session, service: LiveService) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_live_service] = lambda: service
    yield TestClient(app)


def _seed_daily(session: Session, ticker: str, day: datetime.date, price: Decimal) -> None:
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    assert instrument is not None
    session.add(
        DailyPrice(
            instrument_id=instrument.id,
            date=day,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000,
        )
    )
    session.commit()


def test_live_session_lifecycle(client: TestClient, db_session: Session) -> None:
    created = client.post(
        "/api/v1/live-sessions",
        json={"name": "demo", "initial_capital": "50000", "interval_minutes": 15},
    )
    assert created.status_code == 201
    body = created.json()
    session_id = body["id"]
    assert body["status"] == "RUNNING"
    assert body["kind"] == "AGENTS"
    assert body["interval_minutes"] == 15
    assert body["cash"] == "50000.0000"
    assert body["total_value"] == "50000.0000"
    assert body["benchmark_session_id"] is not None

    listed = client.get(
        f"/api/v1/live-sessions/{session_id}",
        params={"now": TUESDAY.isoformat()},
    )
    assert listed.status_code == 200
    assert listed.json()["next_cycle_at"] == TUESDAY.replace(minute=15).isoformat()

    paused = client.post(f"/api/v1/live-sessions/{session_id}/pause")
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"
    assert paused.json()["next_cycle_at"] is None
    twin = db_session.get(LiveSession, body["benchmark_session_id"])
    assert twin is not None
    assert twin.status is LiveSessionStatus.PAUSED

    resumed = client.post(f"/api/v1/live-sessions/{session_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "RUNNING"

    stopped = client.post(f"/api/v1/live-sessions/{session_id}/stop")
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "STOPPED"
    assert client.post(f"/api/v1/live-sessions/{session_id}/pause").status_code == 409
    assert client.post(f"/api/v1/live-sessions/{session_id}/resume").status_code == 409


def test_unknown_live_session_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/live-sessions/999999").status_code == 404
    assert client.get("/api/v1/live-sessions/999999/equity").status_code == 404
    assert client.get("/api/v1/live-sessions/999999/decisions").status_code == 404
    assert client.post("/api/v1/live-sessions/999999/stop").status_code == 404


def test_equity_and_decisions_after_a_cycle(
    client: TestClient, db_session: Session, service: LiveService
) -> None:
    _seed_daily(db_session, "MC.PA", TUESDAY.date(), Decimal("610"))
    session_id = client.post("/api/v1/live-sessions", json={"name": "demo"}).json()["id"]
    service.run_cycle(session_id, TUESDAY, tickers=["MC.PA"])

    equity = client.get(f"/api/v1/live-sessions/{session_id}/equity")
    decisions = client.get(f"/api/v1/live-sessions/{session_id}/decisions")

    assert equity.status_code == 200
    assert len(equity.json()) == 1
    assert equity.json()[0]["total_value"] == "100000.0000"
    assert decisions.status_code == 200
    assert decisions.json()[0]["ticker"] == "MC.PA"
    assert decisions.json()[0]["action"] == "HOLD"
