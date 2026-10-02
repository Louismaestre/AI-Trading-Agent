import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import DailyPrice, IntradayPrice, OrderSide, OrderStatus
from app.services.broker import SLIPPAGE_RATE
from app.services.fees import compute_fees, money
from app.services.instrument_service import InstrumentService
from app.services.portfolio_service import (
    REASON_INDEX_NOT_TRADABLE,
    REASON_INSUFFICIENT_CASH,
    REASON_INSUFFICIENT_SHARES,
    PortfolioService,
)

PARIS = ZoneInfo("Europe/Paris")
TICKER = "MC.PA"


def _paris(*args: int) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=PARIS)


def _later(start: datetime.datetime, minutes: int) -> datetime.datetime:
    return start + datetime.timedelta(minutes=minutes)


def _service(session: Session) -> PortfolioService:
    InstrumentService(session).sync_universe()
    return PortfolioService(session)


def _instrument_id(service: PortfolioService, ticker: str = TICKER) -> int:
    return service._get_tradable_instrument(ticker).id


def _intraday(
    session: Session, instrument_id: int, moment: datetime.datetime, price: Decimal
) -> None:
    session.add(
        IntradayPrice(
            instrument_id=instrument_id,
            timestamp=moment.astimezone(datetime.UTC),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=100,
        )
    )
    session.commit()


def _daily(session: Session, instrument_id: int, day: datetime.date, price: Decimal) -> None:
    session.add(
        DailyPrice(
            instrument_id=instrument_id,
            date=day,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=1000,
        )
    )
    session.commit()


def _slipped(side: OrderSide, price: Decimal) -> Decimal:
    if side is OrderSide.BUY:
        return money(price * (1 + SLIPPAGE_RATE))
    return money(price * (1 - SLIPPAGE_RATE))


def _place_and_execute(
    service: PortfolioService,
    portfolio_id: int,
    side: OrderSide,
    quantity: int,
    decision_at: datetime.datetime,
    now: datetime.datetime,
    ticker: str = TICKER,
) -> object:
    order = service.place_order(portfolio_id, ticker, side, quantity, decision_at)
    service.execute_pending_orders(portfolio_id, now)
    return service.get_order(portfolio_id, order.id)


def test_buy_then_sell_updates_cash_net_of_fees(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")
    instrument_id = _instrument_id(service)
    ten = _paris(2026, 9, 29, 10, 0)
    _intraday(db_session, instrument_id, _later(ten, 5), Decimal("100"))
    _intraday(db_session, instrument_id, _later(ten, 15), Decimal("120"))

    buy = _place_and_execute(
        service, portfolio.id, OrderSide.BUY, 10, _later(ten, 2), _later(ten, 6)
    )
    sell = _place_and_execute(
        service, portfolio.id, OrderSide.SELL, 10, _later(ten, 12), _later(ten, 16)
    )

    buy_price = _slipped(OrderSide.BUY, Decimal("100"))
    sell_price = _slipped(OrderSide.SELL, Decimal("120"))
    buy_amount = money(10 * buy_price)
    sell_amount = money(10 * sell_price)
    expected_cash = money(
        Decimal("100000")
        - buy_amount
        - compute_fees(OrderSide.BUY, buy_amount)
        + sell_amount
        - compute_fees(OrderSide.SELL, sell_amount)
    )

    assert buy.status is OrderStatus.FILLED
    assert sell.status is OrderStatus.FILLED
    assert service.get(portfolio.id).cash == expected_cash
    assert service.snapshot(portfolio.id, _later(ten, 16)).positions == []


def test_oversized_buy_is_rejected(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo", initial_capital=Decimal("1000"))
    ten = _paris(2026, 9, 29, 10, 0)
    _intraday(db_session, _instrument_id(service), _later(ten, 5), Decimal("100"))

    order = _place_and_execute(
        service, portfolio.id, OrderSide.BUY, 20, _later(ten, 2), _later(ten, 6)
    )

    assert order.status is OrderStatus.REJECTED
    assert order.rejection_reason == REASON_INSUFFICIENT_CASH
    assert service.get(portfolio.id).cash == Decimal("1000.0000")


def test_selling_more_than_held_is_rejected(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")
    ten = _paris(2026, 9, 29, 10, 0)
    _intraday(db_session, _instrument_id(service), _later(ten, 5), Decimal("100"))

    order = _place_and_execute(
        service, portfolio.id, OrderSide.SELL, 1, _later(ten, 2), _later(ten, 6)
    )

    assert order.status is OrderStatus.REJECTED
    assert order.rejection_reason == REASON_INSUFFICIENT_SHARES


def test_order_at_10_02_fills_on_the_10_05_bar(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")
    instrument_id = _instrument_id(service)
    ten = _paris(2026, 9, 29, 10, 0)
    _intraday(db_session, instrument_id, ten, Decimal("90"))
    _intraday(db_session, instrument_id, _later(ten, 5), Decimal("110"))

    order = _place_and_execute(
        service, portfolio.id, OrderSide.BUY, 1, _later(ten, 2), _later(ten, 6)
    )

    assert order.status is OrderStatus.FILLED
    assert order.executed_at == _later(ten, 5).astimezone(datetime.UTC)
    assert order.execution_price == _slipped(OrderSide.BUY, Decimal("110"))


def test_friday_evening_order_fills_at_monday_open(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")
    _daily(db_session, _instrument_id(service), datetime.date(2026, 10, 5), Decimal("400"))

    order = _place_and_execute(
        service,
        portfolio.id,
        OrderSide.BUY,
        1,
        _paris(2026, 10, 2, 18, 0),
        _paris(2026, 10, 5, 10, 0),
    )

    assert order.status is OrderStatus.FILLED
    assert order.executed_at == _paris(2026, 10, 5, 9, 0).astimezone(datetime.UTC)
    assert order.execution_price == _slipped(OrderSide.BUY, Decimal("400"))


def test_two_buys_set_the_average_cost(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")
    instrument_id = _instrument_id(service)
    ten = _paris(2026, 9, 29, 10, 0)
    _intraday(db_session, instrument_id, _later(ten, 5), Decimal("100"))
    _intraday(db_session, instrument_id, _later(ten, 15), Decimal("120"))

    _place_and_execute(
        service, portfolio.id, OrderSide.BUY, 10, _later(ten, 2), _later(ten, 6)
    )
    _place_and_execute(
        service, portfolio.id, OrderSide.BUY, 10, _later(ten, 12), _later(ten, 16)
    )

    first = _slipped(OrderSide.BUY, Decimal("100"))
    second = _slipped(OrderSide.BUY, Decimal("120"))
    view = service.snapshot(portfolio.id, _later(ten, 16))

    assert len(view.positions) == 1
    assert view.positions[0].quantity == 20
    assert view.positions[0].average_cost == money((10 * first + 10 * second) / 20)


def test_index_order_is_rejected(db_session: Session) -> None:
    service = _service(db_session)
    portfolio = service.create("demo")

    order = service.place_order(
        portfolio.id, "^FCHI", OrderSide.BUY, 1, _paris(2026, 9, 29, 10, 2)
    )

    assert order.status is OrderStatus.REJECTED
    assert order.rejection_reason == REASON_INDEX_NOT_TRADABLE
