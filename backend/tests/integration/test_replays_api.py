import datetime
from collections.abc import Iterator, Sequence
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.llm import FakeLLM
from app.main import create_app
from app.models import DailyPrice, Instrument, Replay
from app.routers.replays import get_replay_service
from app.schemas.agents import AnalystDecision
from app.services.agent_service import AgentService
from app.services.instrument_service import InstrumentService
from app.services.portfolio_service import DEFAULT_CAPITAL
from app.services.replay_service import WEEKLY, ReplayService

START = "2026-09-15"
END = "2026-09-17"


class _ReplayService(ReplayService):
    """Limit the HTTP fixture to one ticker so FakeLLM stays deterministic."""

    def start(
        self,
        name: str = "Replay",
        initial_capital: Decimal = DEFAULT_CAPITAL,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
        tickers: Sequence[str] | None = None,
        decision_frequency: str = WEEKLY,
    ) -> Replay:
        return super().start(
            name,
            initial_capital,
            start,
            end,
            tickers or ["MC.PA"],
            decision_frequency,
        )

    def run(self, replay_id: int, tickers: Sequence[str] | None = None) -> Replay:
        return super().run(replay_id, tickers or ["MC.PA"])


@pytest.fixture
def service(db_session: Session) -> ReplayService:
    InstrumentService(db_session).sync_universe()
    return _ReplayService(
        db_session,
        agents=AgentService(
            db_session,
            llm=FakeLLM(
                [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
            ),
        ),
        knowledge_cutoff=datetime.date(2025, 4, 1),
        lookback_sessions=0,
    )


@pytest.fixture
def client(db_session: Session, service: ReplayService) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_replay_service] = lambda: service
    yield TestClient(app)


def _seed_daily(session: Session, ticker: str, day: str, price: Decimal) -> None:
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    assert instrument is not None
    session.add(
        DailyPrice(
            instrument_id=instrument.id,
            date=datetime.date.fromisoformat(day),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000,
        )
    )
    session.commit()


def test_replay_api_runs_to_done(client: TestClient, db_session: Session) -> None:
    for day in ("2026-09-14", START, "2026-09-16", END):
        _seed_daily(db_session, "MC.PA", day, Decimal("100"))

    created = client.post(
        "/api/v1/replays",
        json={
            "name": "demo",
            "initial_capital": "100000",
            "start": START,
            "end": END,
            "decision_frequency": "WEEKLY",
        },
    )
    assert created.status_code == 201
    body = created.json()
    replay_id = body["id"]
    assert body["status"] == "DONE"
    assert body["days_done"] == 3
    assert body["metrics"] is not None
    assert body["benchmark_replay_id"] is not None
    assert body["sma_replay_id"] is not None
    assert body["random_replay_id"] is not None

    listed = client.get(f"/api/v1/replays/{replay_id}")
    equity = client.get(f"/api/v1/replays/{replay_id}/equity")
    decisions = client.get(f"/api/v1/replays/{replay_id}/decisions")
    metrics = client.get(f"/api/v1/replays/{replay_id}/metrics")

    assert listed.status_code == 200
    assert len(equity.json()) == 3
    assert decisions.json()[0]["action"] == "HOLD"
    assert metrics.status_code == 200
    assert metrics.json()["order_count"] == 0


def test_replay_without_prices_is_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/replays",
        json={"name": "demo", "start": START, "end": END, "decision_frequency": "WEEKLY"},
    )
    assert response.status_code == 400
    assert "prices" in response.json()["detail"].lower()


def test_replay_before_cutoff_is_400(client: TestClient) -> None:
    response = client.post(
        "/api/v1/replays",
        json={"name": "demo", "start": "2024-01-01", "end": "2024-01-10"},
    )
    assert response.status_code == 400


def test_unknown_replay_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/replays/999999").status_code == 404
    assert client.get("/api/v1/replays/999999/equity").status_code == 404
    assert client.get("/api/v1/replays/999999/decisions").status_code == 404
    assert client.get("/api/v1/replays/999999/metrics").status_code == 404
