import datetime

import pytest
from sqlalchemy.orm import Session

from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService, UnknownTickerError
from app.universe import UNIVERSE
from tests.fakes import FakeProvider

MONDAY = datetime.date(2026, 9, 7)
FRIDAY = datetime.date(2026, 9, 11)
SUNDAY = datetime.date(2026, 9, 13)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def service(db_session: Session, provider: FakeProvider) -> MarketDataService:
    InstrumentService(db_session).sync_universe()
    return MarketDataService(db_session, fetch_bars=provider)


def test_sync_stores_the_downloaded_bars(service: MarketDataService) -> None:
    assert service.sync_prices("MC.PA", MONDAY, FRIDAY) == 5
    assert len(service.get_history("MC.PA", FRIDAY, limit=10)) == 5


def test_second_sync_does_not_call_the_provider(
    service: MarketDataService, provider: FakeProvider
) -> None:
    service.sync_prices("MC.PA", MONDAY, FRIDAY)

    assert service.sync_prices("MC.PA", MONDAY, FRIDAY) == 0
    assert len(provider.calls) == 1


def test_sync_only_downloads_the_missing_days(
    service: MarketDataService, provider: FakeProvider
) -> None:
    wednesday = MONDAY + datetime.timedelta(days=2)
    service.sync_prices("MC.PA", MONDAY, wednesday)

    assert service.sync_prices("MC.PA", MONDAY, FRIDAY) == 2
    assert provider.calls[-1] == ("MC.PA", wednesday + datetime.timedelta(days=1), FRIDAY)


def test_sync_without_trading_day_stores_nothing(service: MarketDataService) -> None:
    saturday = FRIDAY + datetime.timedelta(days=1)

    assert service.sync_prices("MC.PA", saturday, SUNDAY) == 0


def test_sync_universe_covers_every_instrument(service: MarketDataService) -> None:
    assert service.sync_universe_prices(MONDAY, FRIDAY) == 5 * len(UNIVERSE)


def test_history_never_returns_future_bars(service: MarketDataService) -> None:
    service.sync_prices("MC.PA", MONDAY, FRIDAY)

    for as_of in (MONDAY + datetime.timedelta(days=n) for n in range(5)):
        bars = service.get_history("MC.PA", as_of, limit=10)
        assert bars[-1].date == as_of
        assert all(bar.date <= as_of for bar in bars)


def test_history_on_sunday_ends_on_friday(service: MarketDataService) -> None:
    service.sync_prices("MC.PA", MONDAY, SUNDAY)

    assert service.get_history("MC.PA", SUNDAY, limit=10)[-1].date == FRIDAY


def test_history_returns_the_latest_bars_oldest_first(service: MarketDataService) -> None:
    service.sync_prices("MC.PA", MONDAY, FRIDAY)

    dates = [bar.date for bar in service.get_history("MC.PA", FRIDAY, limit=3)]

    assert dates == [FRIDAY - datetime.timedelta(days=n) for n in (2, 1, 0)]


def test_unknown_ticker_raises(service: MarketDataService) -> None:
    with pytest.raises(UnknownTickerError):
        service.get_history("NOPE.PA", FRIDAY, limit=10)
