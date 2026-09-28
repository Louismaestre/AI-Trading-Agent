"""Creates portfolios and turns decisions into cash and position changes."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.market_clock import ensure_aware
from app.models import Instrument, Order, OrderSide, OrderStatus, Portfolio, Position
from app.services.broker import Broker, SimulatedBroker
from app.services.fees import compute_fees, money
from app.services.market_data_service import MarketDataService, UnknownTickerError

DEFAULT_CAPITAL = Decimal("100000.00")
INDEX_TICKER_PREFIX = "^"

REASON_INSUFFICIENT_CASH = "insufficient cash"
REASON_INSUFFICIENT_SHARES = "insufficient shares"
REASON_INDEX_NOT_TRADABLE = "index is not tradable"
REASON_FEES_EXCEED_PROCEEDS = "fees exceed proceeds"


class UnknownPortfolioError(LookupError):
    """No portfolio exists for this id."""


@dataclass(frozen=True)
class PositionView:
    ticker: str
    quantity: int
    average_cost: Decimal
    market_price: Decimal
    value: Decimal


@dataclass(frozen=True)
class PortfolioView:
    portfolio: Portfolio
    market_value: Decimal
    total_value: Decimal
    positions: list[PositionView]


class PortfolioService:
    def __init__(self, session: Session, broker: Broker | None = None) -> None:
        self._session = session
        self._market = MarketDataService(session)
        self._broker: Broker = broker or SimulatedBroker(session)

    def create(self, name: str, initial_capital: Decimal = DEFAULT_CAPITAL) -> Portfolio:
        portfolio = Portfolio(name=name, initial_capital=initial_capital, cash=initial_capital)
        self._session.add(portfolio)
        self._session.commit()
        return portfolio

    def get(self, portfolio_id: int) -> Portfolio:
        return self._get_portfolio(portfolio_id)

    def list_orders(self, portfolio_id: int) -> list[Order]:
        self._get_portfolio(portfolio_id)
        statement = (
            select(Order)
            .options(joinedload(Order.instrument))
            .where(Order.portfolio_id == portfolio_id)
            .order_by(Order.decision_at.desc(), Order.id.desc())
        )
        return list(self._session.scalars(statement).unique().all())

    def place_order(
        self,
        portfolio_id: int,
        ticker: str,
        side: OrderSide,
        quantity: int,
        decision_at: datetime.datetime,
    ) -> Order:
        """Record a PENDING (or immediately REJECTED) order. Does not look up a price."""
        portfolio = self._get_portfolio(portfolio_id)
        instrument = self._get_tradable_instrument(ticker)
        order = Order(
            portfolio_id=portfolio.id,
            instrument_id=instrument.id,
            side=side,
            quantity=quantity,
            status=OrderStatus.PENDING,
            decision_at=ensure_aware(decision_at),
        )
        if instrument.ticker.startswith(INDEX_TICKER_PREFIX):
            order.status = OrderStatus.REJECTED
            order.rejection_reason = REASON_INDEX_NOT_TRADABLE
        self._session.add(order)
        self._session.commit()
        return order

    def execute_pending_orders(self, portfolio_id: int, now: datetime.datetime) -> list[Order]:
        """Fill or reject every PENDING order that has a later price available by `now`."""
        now = ensure_aware(now)
        self._get_portfolio(portfolio_id)
        pending = list(
            self._session.scalars(
                select(Order)
                .where(Order.portfolio_id == portfolio_id, Order.status == OrderStatus.PENDING)
                .order_by(Order.decision_at.asc(), Order.id.asc())
            )
        )
        for order in pending:
            self._try_execute(order, now)
        self._session.commit()
        return pending

    def get_order(self, portfolio_id: int, order_id: int) -> Order:
        self._get_portfolio(portfolio_id)
        order = self._session.scalar(
            select(Order)
            .options(joinedload(Order.instrument))
            .where(Order.id == order_id, Order.portfolio_id == portfolio_id)
        )
        if order is None:
            raise LookupError(order_id)
        return order

    def snapshot(self, portfolio_id: int, as_of: datetime.datetime) -> PortfolioView:
        """Cash plus positions marked at the latest price known at `as_of`."""
        as_of = ensure_aware(as_of)
        portfolio = self._get_portfolio(portfolio_id)
        views: list[PositionView] = []
        market_value = Decimal(0)
        positions = self._session.scalars(
            select(Position)
            .options(joinedload(Position.instrument))
            .where(Position.portfolio_id == portfolio_id)
        )
        for position in positions:
            price = self._mark_price(position.instrument.ticker, as_of, position.average_cost)
            value = money(position.quantity * price)
            market_value += value
            views.append(
                PositionView(
                    ticker=position.instrument.ticker,
                    quantity=position.quantity,
                    average_cost=position.average_cost,
                    market_price=price,
                    value=value,
                )
            )
        market_value = money(market_value)
        return PortfolioView(
            portfolio=portfolio,
            market_value=market_value,
            total_value=money(portfolio.cash + market_value),
            positions=views,
        )

    def _try_execute(self, order: Order, now: datetime.datetime) -> None:
        fill = self._broker.fill(order.side, order.instrument_id, order.decision_at, now)
        if fill is None:
            return
        amount = money(order.quantity * fill.price)
        fees = compute_fees(order.side, amount)
        portfolio = self._get_portfolio(order.portfolio_id)
        reason = self._rejection_reason(order, portfolio, amount, fees)
        if reason is not None:
            order.status = OrderStatus.REJECTED
            order.rejection_reason = reason
            order.executed_at = fill.executed_at
            order.execution_price = fill.price
            order.fees = fees
            return
        self._apply_fill(portfolio, order, fill.price, fees)
        order.status = OrderStatus.FILLED
        order.executed_at = fill.executed_at
        order.execution_price = fill.price
        order.fees = fees

    def _rejection_reason(
        self, order: Order, portfolio: Portfolio, amount: Decimal, fees: Decimal
    ) -> str | None:
        if order.side is OrderSide.BUY:
            if portfolio.cash < amount + fees:
                return REASON_INSUFFICIENT_CASH
            return None
        position = self._position(portfolio.id, order.instrument_id)
        if position is None or position.quantity < order.quantity:
            return REASON_INSUFFICIENT_SHARES
        if amount < fees:
            return REASON_FEES_EXCEED_PROCEEDS
        return None

    def _apply_fill(
        self, portfolio: Portfolio, order: Order, price: Decimal, fees: Decimal
    ) -> None:
        amount = money(order.quantity * price)
        if order.side is OrderSide.BUY:
            portfolio.cash = money(portfolio.cash - amount - fees)
            self._add_shares(portfolio.id, order.instrument_id, order.quantity, price)
        else:
            portfolio.cash = money(portfolio.cash + amount - fees)
            self._remove_shares(portfolio.id, order.instrument_id, order.quantity)

    def _add_shares(
        self, portfolio_id: int, instrument_id: int, quantity: int, price: Decimal
    ) -> None:
        position = self._position(portfolio_id, instrument_id)
        if position is None:
            self._session.add(
                Position(
                    portfolio_id=portfolio_id,
                    instrument_id=instrument_id,
                    quantity=quantity,
                    average_cost=price,
                )
            )
            return
        total_cost = position.quantity * position.average_cost + quantity * price
        position.quantity += quantity
        position.average_cost = money(total_cost / position.quantity)

    def _remove_shares(self, portfolio_id: int, instrument_id: int, quantity: int) -> None:
        position = self._position(portfolio_id, instrument_id)
        assert position is not None
        position.quantity -= quantity
        if position.quantity == 0:
            self._session.delete(position)

    def _position(self, portfolio_id: int, instrument_id: int) -> Position | None:
        return self._session.scalar(
            select(Position).where(
                Position.portfolio_id == portfolio_id, Position.instrument_id == instrument_id
            )
        )

    def _mark_price(self, ticker: str, as_of: datetime.datetime, fallback: Decimal) -> Decimal:
        latest = self._market.get_latest_price(ticker, as_of)
        if latest is not None:
            return latest
        history = self._market.get_history(ticker, as_of.date(), limit=1)
        if history:
            return history[0].close
        return fallback

    def _get_portfolio(self, portfolio_id: int) -> Portfolio:
        portfolio = self._session.get(Portfolio, portfolio_id)
        if portfolio is None:
            raise UnknownPortfolioError(portfolio_id)
        return portfolio

    def _get_tradable_instrument(self, ticker: str) -> Instrument:
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            raise UnknownTickerError(ticker)
        return instrument
