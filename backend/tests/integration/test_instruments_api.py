from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import create_app
from app.routers.instruments import get_market_data_service
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService
from app.universe import UNIVERSE
from tests.fakes import FakeProvider

PRICES_URL = "/api/v1/instruments/MC.PA/prices"


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API wired to the test transaction and to a fake provider instead of Yahoo."""
    InstrumentService(db_session).sync_universe()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_market_data_service] = lambda: MarketDataService(
        db_session, fetch_bars=FakeProvider()
    )
    # No `with`: the startup sync would use the real database instead of the test one.
    yield TestClient(app)


def test_list_instruments(client: TestClient) -> None:
    response = client.get("/api/v1/instruments")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == len(UNIVERSE)
    assert "id" not in body[0]


def test_sync_then_read_prices(client: TestClient) -> None:
    sync = client.post("/api/v1/instruments/sync-prices", json={"start": "2026-09-07"})
    prices = client.get(PRICES_URL, params={"start": "2026-09-08", "end": "2026-09-10"})

    assert sync.status_code == 200
    assert sync.json()["bars_stored"] > 0
    assert prices.status_code == 200
    assert [bar["date"] for bar in prices.json()] == ["2026-09-08", "2026-09-09", "2026-09-10"]


def test_sync_with_empty_body_uses_default_period(client: TestClient) -> None:
    response = client.post("/api/v1/instruments/sync-prices", json={})

    assert response.status_code == 200
    assert response.json()["bars_stored"] > 0


def test_prices_of_unknown_ticker_is_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/instruments/NOPE.PA/prices", params={"start": "2026-09-01", "end": "2026-09-10"}
    )

    assert response.status_code == 404


def test_invalid_date_is_422(client: TestClient) -> None:
    response = client.get(PRICES_URL, params={"start": "abc", "end": "2026-09-10"})

    assert response.status_code == 422
