import datetime
from collections.abc import Iterator
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import create_app
from app.models import IntradayPrice, OrderSide
from app.routers.portfolios import get_portfolio_service
from app.services.instrument_service import InstrumentService
from app.services.portfolio_service import PortfolioService

PARIS = ZoneInfo("Europe/Paris")
TEN = datetime.datetime(2026, 9, 29, 10, 0, tzinfo=PARIS)


@pytest.fixture
def service(db_session: Session) -> PortfolioService:
    InstrumentService(db_session).sync_universe()
    return PortfolioService(db_session)


@pytest.fixture
def client(db_session: Session, service: PortfolioService) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_portfolio_service] = lambda: service
    yield TestClient(app)


def _seed_bar(
    session: Session, service: PortfolioService, moment: datetime.datetime, price: Decimal
) -> None:
    instrument = service._get_tradable_instrument("MC.PA")
    session.add(
        IntradayPrice(
            instrument_id=instrument.id,
            timestamp=moment.astimezone(datetime.UTC),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=100,
        )
    )
    session.commit()


def test_create_and_read_portfolio(client: TestClient) -> None:
    created = client.post("/api/v1/portfolios", json={"name": "demo"})
    portfolio_id = created.json()["id"]

    response = client.get(f"/api/v1/portfolios/{portfolio_id}")

    assert created.status_code == 201
    assert response.status_code == 200
    assert response.json()["cash"] == "100000.0000"
    assert response.json()["positions"] == []
    assert response.json()["total_value"] == "100000.0000"


def test_unknown_portfolio_is_404(client: TestClient) -> None:
    assert client.get("/api/v1/portfolios/999999").status_code == 404


def test_place_order_fills_when_a_later_bar_exists(
    client: TestClient, db_session: Session, service: PortfolioService
) -> None:
    _seed_bar(db_session, service, TEN + datetime.timedelta(minutes=5), Decimal("100"))
    portfolio_id = client.post("/api/v1/portfolios", json={"name": "demo"}).json()["id"]

    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders",
        json={
            "ticker": "MC.PA",
            "side": "BUY",
            "quantity": 10,
            "decision_at": (TEN + datetime.timedelta(minutes=2)).isoformat(),
            "execute_at": (TEN + datetime.timedelta(minutes=6)).isoformat(),
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "FILLED"
    assert response.json()["ticker"] == "MC.PA"

    portfolio = client.get(f"/api/v1/portfolios/{portfolio_id}").json()
    assert len(portfolio["positions"]) == 1
    assert portfolio["positions"][0]["quantity"] == 10

    orders = client.get(f"/api/v1/portfolios/{portfolio_id}/orders")
    assert len(orders.json()) == 1
    assert orders.json()[0]["side"] == OrderSide.BUY


def test_pending_order_fills_on_later_execute(
    client: TestClient, db_session: Session, service: PortfolioService
) -> None:
    _seed_bar(db_session, service, TEN + datetime.timedelta(minutes=5), Decimal("100"))
    portfolio_id = client.post("/api/v1/portfolios", json={"name": "demo"}).json()["id"]
    placed = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders",
        json={
            "ticker": "MC.PA",
            "side": "BUY",
            "quantity": 1,
            "decision_at": (TEN + datetime.timedelta(minutes=2)).isoformat(),
            "execute_at": (TEN + datetime.timedelta(minutes=2)).isoformat(),
        },
    )
    executed = client.post(
        f"/api/v1/portfolios/{portfolio_id}/execute",
        json={"at": (TEN + datetime.timedelta(minutes=6)).isoformat()},
    )

    assert placed.json()["status"] == "PENDING"
    assert executed.status_code == 200
    assert executed.json()[0]["status"] == "FILLED"


def test_unknown_ticker_is_404(client: TestClient) -> None:
    portfolio_id = client.post("/api/v1/portfolios", json={"name": "demo"}).json()["id"]

    response = client.post(
        f"/api/v1/portfolios/{portfolio_id}/orders",
        json={"ticker": "NOPE.PA", "side": "BUY", "quantity": 1},
    )

    assert response.status_code == 404
