import datetime
from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.llm import FakeLLM
from app.main import create_app
from app.models import DailyPrice, Instrument
from app.routers.agents import get_agent_service
from app.schemas.agents import AnalystDecision, QuantityProposal
from app.services.agent_service import AgentService
from app.services.instrument_service import InstrumentService
from app.services.portfolio_service import PortfolioService

AS_OF = datetime.date(2026, 9, 15)


@pytest.fixture
def service(db_session: Session) -> AgentService:
    InstrumentService(db_session).sync_universe()
    llm = FakeLLM(
        [
            AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait"),
            AnalystDecision(action="BUY", confidence=0.8, target_weight=0.1, rationale="buy OR"),
            QuantityProposal(quantity=20, rationale="size"),
            AnalystDecision(action="SELL", confidence=0.6, target_weight=0, rationale="no pos"),
        ]
    )
    return AgentService(db_session, llm=llm)


@pytest.fixture
def client(db_session: Session, service: AgentService) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_agent_service] = lambda: service
    yield TestClient(app)


def _seed_daily(session: Session, ticker: str, price: Decimal) -> None:
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    assert instrument is not None
    session.add(
        DailyPrice(
            instrument_id=instrument.id,
            date=AS_OF,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000,
        )
    )
    session.commit()


def test_run_agents_stores_decisions_and_a_buy_order(
    db_session: Session, service: AgentService
) -> None:
    for ticker, price in (("MC.PA", "610"), ("OR.PA", "400"), ("AIR.PA", "140")):
        _seed_daily(db_session, ticker, Decimal(price))
    portfolio = PortfolioService(db_session).create("demo")

    records = service.run_agents(portfolio.id, AS_OF, tickers=["MC.PA", "OR.PA", "AIR.PA"])

    assert [record.action.value for record in records] == ["HOLD", "BUY", "SELL"]
    assert records[0].order_id is None
    assert records[1].order_id is not None
    assert records[2].order_id is None
    listed = service.list_decisions(portfolio.id)
    assert len(listed) == 3
    assert {item.instrument.ticker for item in listed} == {"MC.PA", "OR.PA", "AIR.PA"}


def test_run_agents_api(client: TestClient, db_session: Session, service: AgentService) -> None:
    _seed_daily(db_session, "MC.PA", Decimal("610"))
    portfolio_id = PortfolioService(db_session).create("demo").id

    path = f"/api/v1/portfolios/{portfolio_id}/run-agents?as_of={AS_OF.isoformat()}"
    response = client.post(path)

    assert response.status_code == 201
    body = response.json()
    assert body[0]["ticker"] == "MC.PA"
    assert body[0]["action"] == "HOLD"
    assert body[0]["created_at"]
    listed = client.get(f"/api/v1/portfolios/{portfolio_id}/decisions")
    assert listed.status_code == 200
    assert listed.json()[0]["rationale"] == "wait"


def test_decision_detail_includes_the_specialist_trace(
    client: TestClient, db_session: Session, service: AgentService
) -> None:
    _seed_daily(db_session, "MC.PA", Decimal("610"))
    portfolio = PortfolioService(db_session).create("demo")
    records = service.run_agents(portfolio.id, AS_OF, tickers=["MC.PA"])

    response = client.get(f"/api/v1/decisions/{records[0].id}")

    assert response.status_code == 200
    body = response.json()
    assert body["ticker"] == "MC.PA"
    assert body["reports"]["sentiment"]["stance"] == "NEUTRAL"
    assert body["debate"] == []
    assert body["risk"] is None


def test_unknown_decision_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/decisions/999999")
    assert response.status_code == 404
