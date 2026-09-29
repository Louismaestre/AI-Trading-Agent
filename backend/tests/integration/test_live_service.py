import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.llm import FakeLLM
from app.models import AgentDecision, DailyPrice, EquityPoint, Instrument, Order
from app.schemas.agents import AnalystDecision
from app.services.agent_service import AgentService
from app.services.instrument_service import InstrumentService
from app.services.live_service import LiveService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService

PARIS = ZoneInfo("Europe/Paris")
TUESDAY = datetime.datetime(2026, 9, 29, 10, 0, tzinfo=PARIS)
SATURDAY = datetime.datetime(2026, 10, 3, 10, 0, tzinfo=PARIS)


def _service(db_session: Session, llm: FakeLLM) -> LiveService:
    InstrumentService(db_session).sync_universe()
    return LiveService(
        db_session,
        agents=AgentService(db_session, llm=llm),
        market=MarketDataService(db_session, fetch_intraday=lambda _ticker, _start: []),
    )


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


def _hold() -> AnalystDecision:
    return AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")


def test_tuesday_cycle_records_a_decision_and_equity(db_session: Session) -> None:
    live = _service(db_session, FakeLLM([_hold()]))
    _seed_daily(db_session, "MC.PA", TUESDAY.date(), Decimal("610"))
    portfolio = PortfolioService(db_session).create("demo")
    session = live.create(portfolio.id)

    result = live.run_cycle(session.id, TUESDAY, tickers=["MC.PA"])

    assert result.ran is True
    assert result.decision_count == 1
    assert result.equity_id is not None
    assert db_session.scalar(select(func.count()).select_from(AgentDecision)) == 1
    assert db_session.scalar(select(func.count()).select_from(EquityPoint)) == 1


def test_saturday_cycle_does_nothing(db_session: Session) -> None:
    live = _service(db_session, FakeLLM([_hold()]))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 10, 2), Decimal("610"))
    portfolio = PortfolioService(db_session).create("demo")
    session = live.create(portfolio.id)

    result = live.run_cycle(session.id, SATURDAY, tickers=["MC.PA"])

    assert result.ran is False
    assert result.reason == "closed"
    assert db_session.scalar(select(func.count()).select_from(AgentDecision)) == 0
    assert db_session.scalar(select(func.count()).select_from(EquityPoint)) == 0


def test_same_slot_does_not_duplicate_decisions_or_orders(db_session: Session) -> None:
    live = _service(db_session, FakeLLM([_hold(), _hold()]))
    _seed_daily(db_session, "MC.PA", TUESDAY.date(), Decimal("610"))
    portfolio = PortfolioService(db_session).create("demo")
    session = live.create(portfolio.id)

    first = live.run_cycle(session.id, TUESDAY, tickers=["MC.PA"])
    later = TUESDAY.replace(minute=7)
    second = live.run_cycle(session.id, later, tickers=["MC.PA"])

    assert first.ran is True
    assert second.ran is False
    assert second.reason == "duplicate_slot"
    assert db_session.scalar(select(func.count()).select_from(AgentDecision)) == 1
    assert db_session.scalar(select(func.count()).select_from(Order)) == 0
    assert db_session.scalar(select(func.count()).select_from(EquityPoint)) == 1
