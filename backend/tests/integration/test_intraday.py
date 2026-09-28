import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService
from app.universe import UNIVERSE
from tests.fakes import FakeIntradayProvider

# Tuesday 29 September 2026, 10:00 in Paris; the fake serves 10:00, 10:05 and 10:10.
TEN = datetime.datetime(2026, 9, 29, 8, 0, tzinfo=datetime.UTC)
MINUTES = datetime.timedelta(minutes=1)


@pytest.fixture
def provider() -> FakeIntradayProvider:
    return FakeIntradayProvider(first=TEN, count=3)


@pytest.fixture
def service(db_session: Session, provider: FakeIntradayProvider) -> MarketDataService:
    InstrumentService(db_session).sync_universe()
    return MarketDataService(db_session, fetch_intraday=provider)


def test_sync_stores_the_bars(service: MarketDataService) -> None:
    assert service.sync_intraday("MC.PA", TEN) == 3
    assert len(service.get_intraday("MC.PA", TEN, TEN + 60 * MINUTES)) == 3


def test_next_sync_starts_from_the_last_stored_bar(
    service: MarketDataService, provider: FakeIntradayProvider
) -> None:
    service.sync_intraday("MC.PA", TEN)
    service.sync_intraday("MC.PA", TEN)

    # The last bar may have been stored while in progress, so it is downloaded again.
    assert provider.calls[-1] == ("MC.PA", TEN + 10 * MINUTES)


def test_resync_updates_a_bar_stored_in_progress(
    service: MarketDataService, provider: FakeIntradayProvider
) -> None:
    service.sync_intraday("MC.PA", TEN)
    provider.bars[-1] = provider.bars[-1].model_copy(update={"close": Decimal("99")})

    service.sync_intraday("MC.PA", TEN)

    assert service.get_intraday("MC.PA", TEN, TEN + 60 * MINUTES)[-1].close == Decimal("99")


def test_sync_universe_covers_every_instrument(service: MarketDataService) -> None:
    assert service.sync_universe_intraday(TEN) == 3 * len(UNIVERSE)


@pytest.mark.parametrize(
    ("as_of", "expected_close"),
    [
        (TEN + 4 * MINUTES, None),  # 10:00 bar still in progress
        (TEN + 5 * MINUTES, Decimal("0")),  # 10:00 bar just finished
        (TEN + 12 * MINUTES, Decimal("5")),  # 10:10 bar in progress, 10:05 is the latest
        (TEN + 60 * MINUTES, Decimal("10")),  # after the last bar
    ],
)
def test_latest_price_never_uses_an_unfinished_bar(
    service: MarketDataService, as_of: datetime.datetime, expected_close: Decimal | None
) -> None:
    service.sync_intraday("MC.PA", TEN)

    assert service.get_latest_price("MC.PA", as_of) == expected_close


def test_naive_datetime_is_rejected(service: MarketDataService) -> None:
    with pytest.raises(ValueError, match="Timezone-aware"):
        service.get_latest_price("MC.PA", datetime.datetime(2026, 9, 29, 10, 0))
