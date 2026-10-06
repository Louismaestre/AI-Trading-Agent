import datetime
from collections.abc import Callable
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.tools import AgentTools
from app.llm import FakeLLM
from app.market_clock import session_open, trading_days
from app.models import (
    DailyPrice,
    Instrument,
    Order,
    OrderSide,
    OrderStatus,
    Position,
    Replay,
    ReplayKind,
    ReplayStatus,
)
from app.schemas.agents import AnalystDecision, QuantityProposal
from app.services.agent_service import AgentService
from app.services.baselines import random_decision
from app.services.fees import compute_fees, money
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.replay_service import (
    MissingReplayPricesError,
    ReplayService,
    ReplayStartsTooEarlyError,
    decision_days,
    fail_interrupted_replays,
)

START = datetime.date(2026, 9, 15)
END = datetime.date(2026, 9, 17)
CUTOFF = datetime.date(2025, 4, 1)
_HOLD = AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")


def _service(db_session: Session, llm: FakeLLM, lookback_sessions: int = 0) -> ReplayService:
    InstrumentService(db_session).sync_universe()
    return ReplayService(
        db_session,
        agents=AgentService(db_session, llm=llm),
        knowledge_cutoff=CUTOFF,
        lookback_sessions=lookback_sessions,
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


def _seed_range(
    session: Session,
    ticker: str,
    days: list[datetime.date],
    price_for: Callable[[datetime.date], Decimal],
) -> None:
    instrument = session.scalar(select(Instrument).where(Instrument.ticker == ticker))
    assert instrument is not None
    for day in days:
        price = price_for(day)
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


def test_fail_interrupted_replays_marks_running_rows(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([]))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("100"))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, tickers=["MC.PA"])
    replay.status = ReplayStatus.RUNNING
    db_session.commit()

    assert fail_interrupted_replays(db_session) == 1
    db_session.refresh(replay)
    assert replay.status is ReplayStatus.FAILED
    assert replay.error_message is not None
    assert "restarted" in replay.error_message


def test_create_refuses_when_indicator_lookback_is_missing(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([]), lookback_sessions=50)
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("100"))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    portfolio = PortfolioService(db_session).create("demo")

    with pytest.raises(MissingReplayPricesError, match="50"):
        service.create(portfolio.id, START, END, tickers=["MC.PA"])


def test_create_refuses_a_start_before_stored_prices(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([]))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    portfolio = PortfolioService(db_session).create("demo")

    with pytest.raises(MissingReplayPricesError, match="2026-09-15"):
        service.create(
            portfolio.id,
            datetime.date(2026, 9, 1),
            END,
            tickers=["MC.PA"],
        )


def test_failed_replay_keeps_the_exception_message(db_session: Session) -> None:
    class _Boom:
        def run_agents(self, *_args: object, **_kwargs: object) -> list[object]:
            raise RuntimeError("ollama down")

    InstrumentService(db_session).sync_universe()
    service = ReplayService(
        db_session,
        agents=_Boom(),  # type: ignore[arg-type]
        knowledge_cutoff=CUTOFF,
        lookback_sessions=0,
    )
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("100"))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, tickers=["MC.PA"])

    with pytest.raises(RuntimeError, match="ollama down"):
        service.run(replay.id, tickers=["MC.PA"])

    assert replay.status is ReplayStatus.FAILED
    assert replay.error_message == "RuntimeError: ollama down"


def test_replay_starting_on_or_before_the_cutoff_is_refused(db_session: Session) -> None:
    live = _service(db_session, FakeLLM([]))
    portfolio = PortfolioService(db_session).create("demo")

    with pytest.raises(ReplayStartsTooEarlyError):
        live.create(portfolio.id, CUTOFF, END)


def test_replay_curve_after_a_first_day_buy_is_hand_computable(db_session: Session) -> None:
    llm = FakeLLM(
        [
            AnalystDecision(action="BUY", confidence=0.9, target_weight=0.1, rationale="buy"),
            QuantityProposal(quantity=100, rationale="size"),
        ]
    )
    service = _service(db_session, llm)
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("100"))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 16), Decimal("100"))
    _seed_daily(db_session, "MC.PA", END, Decimal("120"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END)

    service.run(replay.id, tickers=["MC.PA"])

    points = service.list_equity(replay.id)
    fill_price = money(Decimal("100") * Decimal("1.0005"))
    amount = money(Decimal(100) * fill_price)
    fees = compute_fees(OrderSide.BUY, amount)
    cash = money(portfolio.initial_capital - amount - fees)
    assert replay.status is ReplayStatus.DONE
    assert replay.days_done == 3
    assert [point.total_value for point in points] == [
        portfolio.initial_capital,
        money(cash + Decimal(100) * Decimal("100")),
        money(cash + Decimal(100) * Decimal("120")),
    ]
    order = db_session.scalar(select(Order).where(Order.portfolio_id == portfolio.id))
    assert order is not None
    assert order.status is OrderStatus.FILLED
    assert order.quantity == 100


def test_as_of_hides_prices_after_the_simulated_day(db_session: Session) -> None:
    _service(db_session, FakeLLM([]))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 16), Decimal("999"))
    opened = session_open(START)
    assert opened is not None
    tools = AgentTools(
        PortfolioService(db_session),
        MarketDataService(db_session),
        PortfolioService(db_session).create("demo").id,
        opened,
    )

    history = MarketDataService(db_session).get_history("MC.PA", START, limit=10)

    assert tools.get_last_price("MC.PA") == Decimal("100.0000")
    assert [bar.date for bar in history] == [START]


def test_create_opens_an_equal_weight_buy_and_hold_book(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([]))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("500"))
    _seed_daily(db_session, "OR.PA", datetime.date(2026, 9, 14), Decimal("500"))
    _seed_daily(db_session, "MC.PA", START, Decimal("500"))
    _seed_daily(db_session, "OR.PA", START, Decimal("500"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, tickers=["MC.PA", "OR.PA"])

    assert replay.kind is ReplayKind.AGENTS
    assert replay.benchmark_replay_id is not None
    assert replay.sma_replay_id is not None
    assert replay.random_replay_id is not None
    hold = db_session.get(Replay, replay.benchmark_replay_id)
    sma = db_session.get(Replay, replay.sma_replay_id)
    rnd = db_session.get(Replay, replay.random_replay_id)
    assert hold is not None
    assert sma is not None
    assert rnd is not None
    assert hold.kind is ReplayKind.BUY_AND_HOLD
    assert sma.kind is ReplayKind.SMA_CROSS
    assert rnd.kind is ReplayKind.RANDOM
    held = list(
        db_session.scalars(select(Position).where(Position.portfolio_id == hold.portfolio_id))
    )
    assert {row.quantity for row in held} == {99}
    assert len(held) == 2
    agent_positions = list(
        db_session.scalars(select(Position).where(Position.portfolio_id == portfolio.id))
    )
    assert agent_positions == []


def test_ten_percent_drop_sells_at_the_next_open(db_session: Session) -> None:
    service = _service(
        db_session,
        FakeLLM(
            [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
        ),
    )
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("100"))
    _seed_daily(db_session, "MC.PA", START, Decimal("100"))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 16), Decimal("90"))
    _seed_daily(db_session, "MC.PA", END, Decimal("90"))
    portfolio = PortfolioService(db_session).create("demo")
    instrument = db_session.scalar(select(Instrument).where(Instrument.ticker == "MC.PA"))
    assert instrument is not None
    db_session.add(
        Position(
            portfolio_id=portfolio.id,
            instrument_id=instrument.id,
            quantity=10,
            average_cost=Decimal("100"),
        )
    )
    db_session.commit()
    replay = service.create(portfolio.id, START, END, tickers=["MC.PA"])

    service.run(replay.id, tickers=["MC.PA"])

    sells = list(
        db_session.scalars(
            select(Order).where(Order.portfolio_id == portfolio.id, Order.side == OrderSide.SELL)
        )
    )
    assert len(sells) == 1
    assert sells[0].quantity == 10
    assert sells[0].status is OrderStatus.FILLED
    assert sells[0].executed_at is not None
    assert sells[0].executed_at.date() == END
    leftover = db_session.scalar(select(Position).where(Position.portfolio_id == portfolio.id))
    assert leftover is None


def test_buy_and_hold_replay_places_no_further_orders(db_session: Session) -> None:
    service = _service(
        db_session,
        FakeLLM(
            [AnalystDecision(action="HOLD", confidence=0.4, target_weight=0, rationale="wait")]
        ),
    )
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 14), Decimal("500"))
    _seed_daily(db_session, "MC.PA", START, Decimal("500"))
    _seed_daily(db_session, "MC.PA", datetime.date(2026, 9, 16), Decimal("500"))
    _seed_daily(db_session, "MC.PA", END, Decimal("500"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, tickers=["MC.PA"])
    assert replay.benchmark_replay_id is not None
    hold = db_session.get(Replay, replay.benchmark_replay_id)
    assert hold is not None
    before = db_session.scalar(
        select(func.count(Order.id)).where(Order.portfolio_id == hold.portfolio_id)
    )

    service.run(replay.id, tickers=["MC.PA"])

    after = db_session.scalar(
        select(func.count(Order.id)).where(Order.portfolio_id == hold.portfolio_id)
    )
    assert after == before
    assert after == 1
    scored = service.metrics(replay.id)
    assert scored.order_count == 0
    hold_metrics = service.metrics(hold.id)
    assert hold_metrics.order_count == 1
    assert hold_metrics.hit_rate is None
    assert hold_metrics.fees_paid > 0
    assert replay.sma_replay_id is not None
    sma = db_session.get(Replay, replay.sma_replay_id)
    assert sma is not None
    sma_metrics = service.metrics(sma.id)
    assert sma_metrics.order_count == 0
    assert sma.status is ReplayStatus.DONE


def test_random_replay_matches_the_seeded_decisions(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([_HOLD, _HOLD, _HOLD]))
    for day in (datetime.date(2026, 9, 14), START, datetime.date(2026, 9, 16), END):
        _seed_daily(db_session, "MC.PA", day, Decimal("500"))
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, decision_frequency="DAILY", tickers=["MC.PA"])
    assert replay.random_replay_id is not None
    rnd = db_session.get(Replay, replay.random_replay_id)
    assert rnd is not None

    service.run(replay.id, tickers=["MC.PA"])

    held = False
    in_flight = False
    expected_buys = 0
    for day in decision_days(trading_days(START, END), "DAILY"):
        if in_flight:
            in_flight = False
            continue
        pick = random_decision("MC.PA", day, rnd.id, held, 1.0)
        if pick.action == "BUY" and not held:
            expected_buys += 1
            held = True
            in_flight = True
        elif pick.action == "SELL" and held:
            held = False
            in_flight = True
    buys = list(
        db_session.scalars(
            select(Order).where(Order.portfolio_id == rnd.portfolio_id, Order.side == OrderSide.BUY)
        )
    )
    assert len(buys) == expected_buys


def test_sma_replay_buys_after_a_fast_cross_above(db_session: Session) -> None:
    service = _service(db_session, FakeLLM([_HOLD, _HOLD, _HOLD]))
    history = trading_days(datetime.date(2026, 6, 1), END)
    before_start = [day for day in history if day <= START]
    fast = set(before_start[-20:])

    def price_for(day: datetime.date) -> Decimal:
        return Decimal("200") if day in fast or day > START else Decimal("100")

    _seed_range(db_session, "MC.PA", history, price_for)
    portfolio = PortfolioService(db_session).create("demo")
    replay = service.create(portfolio.id, START, END, decision_frequency="DAILY", tickers=["MC.PA"])
    assert replay.sma_replay_id is not None

    service.run(replay.id, tickers=["MC.PA"])

    sma = db_session.get(Replay, replay.sma_replay_id)
    assert sma is not None
    buys = list(
        db_session.scalars(
            select(Order).where(Order.portfolio_id == sma.portfolio_id, Order.side == OrderSide.BUY)
        )
    )
    assert len(buys) == 1
    assert buys[0].status is OrderStatus.FILLED
