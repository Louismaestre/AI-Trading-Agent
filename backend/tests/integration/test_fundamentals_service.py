import datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DailyPrice, Fundamental, Instrument
from app.schemas.fundamentals import FundamentalPeriod
from app.services.fundamentals_service import FundamentalsService
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService, UnknownTickerError

JUNE = datetime.date(2026, 6, 30)
JULY_15 = datetime.date(2026, 7, 15)
SEPTEMBER_1 = datetime.date(2026, 9, 1)
DELAY = 60


def _period(
    period_end: datetime.date,
    *,
    diluted_eps: str = "2.5",
    revenue: str = "1000",
    net_income: str = "100",
) -> FundamentalPeriod:
    return FundamentalPeriod(
        period_end=period_end,
        revenue=Decimal(revenue),
        net_income=Decimal(net_income),
        diluted_eps=Decimal(diluted_eps),
        total_debt=Decimal("400"),
        total_equity=Decimal("800"),
    )


class _Fetch:
    def __init__(self, periods: list[FundamentalPeriod]) -> None:
        self.periods = periods
        self.calls: list[str] = []

    def __call__(self, ticker: str) -> list[FundamentalPeriod]:
        self.calls.append(ticker)
        return list(self.periods)


@pytest.fixture
def service(db_session: Session) -> FundamentalsService:
    InstrumentService(db_session).sync_universe()
    return FundamentalsService(db_session, fetch=_Fetch([]), delay_days=DELAY)


def _seed_price(session: Session, ticker: str, day: datetime.date, price: Decimal) -> None:
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


def test_june_quarter_is_hidden_on_15_july_and_visible_on_1_september(
    db_session: Session,
) -> None:
    fetch = _Fetch([_period(JUNE)])
    live = FundamentalsService(db_session, fetch=fetch, delay_days=DELAY)
    InstrumentService(db_session).sync_universe()
    live.sync("MC.PA")

    july = live.get_snapshot("MC.PA", JULY_15)
    september = live.get_snapshot("MC.PA", SEPTEMBER_1)

    assert july.statements == []
    assert [row.period_end for row in september.statements] == [JUNE]


def test_pe_uses_the_as_of_close_not_a_later_price(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()
    fetch = _Fetch(
        [
            _period(datetime.date(2026, 3, 31)),
            _period(datetime.date(2025, 12, 31)),
            _period(datetime.date(2025, 9, 30)),
            _period(datetime.date(2025, 6, 30)),
        ]
    )
    live = FundamentalsService(db_session, fetch=fetch, delay_days=DELAY)
    live.sync("MC.PA")
    _seed_price(db_session, "MC.PA", JULY_15, Decimal("100"))
    _seed_price(db_session, "MC.PA", SEPTEMBER_1, Decimal("200"))

    july = live.get_snapshot("MC.PA", JULY_15)
    september = live.get_snapshot("MC.PA", SEPTEMBER_1)

    assert july.price == Decimal("100.0000")
    assert september.price == Decimal("200.0000")
    assert july.pe_ratio == Decimal("10.0000")
    assert september.pe_ratio == Decimal("20.0000")


def test_sync_upserts_the_same_period(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()
    first = FundamentalsService(db_session, fetch=_Fetch([_period(JUNE, revenue="1000")]))
    first.sync("MC.PA")
    second = FundamentalsService(db_session, fetch=_Fetch([_period(JUNE, revenue="1100")]))
    second.sync("MC.PA")

    row = db_session.scalar(select(Fundamental))
    assert row is not None
    assert row.revenue == Decimal("1100.0000")
    assert db_session.scalar(select(func.count(Fundamental.id))) == 1


def test_unknown_ticker_is_rejected(service: FundamentalsService) -> None:
    with pytest.raises(UnknownTickerError):
        service.get_snapshot("NOPE.PA", JULY_15)


def test_market_history_is_reused(db_session: Session) -> None:
    """The close comes from MarketDataService.get_history, not a side channel."""
    InstrumentService(db_session).sync_universe()
    live = FundamentalsService(db_session, fetch=_Fetch([]), market=MarketDataService(db_session))
    _seed_price(db_session, "MC.PA", JULY_15, Decimal("42"))

    snapshot = live.get_snapshot("MC.PA", JULY_15)

    assert snapshot.price == Decimal("42.0000")
