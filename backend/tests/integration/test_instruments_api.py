import datetime
from collections.abc import Iterator
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import get_session
from app.main import create_app
from app.routers.instruments import get_fundamentals_service, get_market_data_service
from app.schemas.fundamentals import FundamentalPeriod
from app.services.fundamentals_service import FundamentalsService
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService
from app.universe import UNIVERSE
from tests.fakes import FakeIntradayProvider, FakeProvider

PRICES_URL = "/api/v1/instruments/MC.PA/prices"
INTRADAY_URL = "/api/v1/instruments/MC.PA/intraday"
TEN = datetime.datetime(2026, 9, 29, 8, 0, tzinfo=datetime.UTC)


@pytest.fixture
def client(db_session: Session) -> Iterator[TestClient]:
    """API wired to the test transaction and to fake providers instead of Yahoo."""
    InstrumentService(db_session).sync_universe()
    app = create_app()
    app.dependency_overrides[get_session] = lambda: db_session
    app.dependency_overrides[get_market_data_service] = lambda: MarketDataService(
        db_session,
        fetch_bars=FakeProvider(),
        fetch_intraday=FakeIntradayProvider(first=TEN, count=3),
    )
    app.dependency_overrides[get_fundamentals_service] = lambda: FundamentalsService(
        db_session,
        fetch=lambda _ticker: [
            FundamentalPeriod(period_end=datetime.date(2026, 6, 30), revenue=Decimal("1000"))
        ],
        delay_days=60,
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


def test_sync_then_read_intraday(client: TestClient) -> None:
    sync = client.post("/api/v1/instruments/sync-intraday", json={"start": TEN.isoformat()})
    end = TEN + datetime.timedelta(hours=1)
    bars = client.get(INTRADAY_URL, params={"start": TEN.isoformat(), "end": end.isoformat()})

    assert sync.json()["bars_stored"] == 3 * len(UNIVERSE)
    assert bars.status_code == 200
    assert [bar["timestamp"] for bar in bars.json()] == [
        "2026-09-29T08:00:00Z",
        "2026-09-29T08:05:00Z",
        "2026-09-29T08:10:00Z",
    ]


def test_intraday_without_timezone_is_422(client: TestClient) -> None:
    response = client.get(INTRADAY_URL, params={"start": "2026-09-29T10:00:00"})

    assert response.status_code == 422


def test_intraday_of_unknown_ticker_is_404(client: TestClient) -> None:
    response = client.get("/api/v1/instruments/NOPE.PA/intraday", params={"start": TEN.isoformat()})

    assert response.status_code == 404


def test_sync_then_read_fundamentals_respects_the_publication_delay(client: TestClient) -> None:
    sync = client.post("/api/v1/instruments/sync-fundamentals")
    july = client.get("/api/v1/instruments/MC.PA/fundamentals", params={"as_of": "2026-07-15"})
    september = client.get("/api/v1/instruments/MC.PA/fundamentals", params={"as_of": "2026-09-01"})

    assert sync.status_code == 200
    assert sync.json()["periods_stored"] > 0
    assert july.json()["statements"] == []
    assert september.json()["statements"][0]["period_end"] == "2026-06-30"


def test_fundamentals_of_unknown_ticker_is_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/instruments/NOPE.PA/fundamentals", params={"as_of": "2026-07-15"}
    )

    assert response.status_code == 404
