"""Applies stop-loss in the engine. No LLM here."""

import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.indicators import atr
from app.market_clock import last_close, session_close, trading_days
from app.models import Order, OrderSide, OrderStatus
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService
from app.services.risk_rules import (
    PositionRisk,
    RiskBook,
    RiskLimits,
    stop_loss_tickers,
)
from app.universe import UNIVERSE


class RiskService:
    def __init__(
        self,
        session: Session,
        portfolios: PortfolioService | None = None,
        market: MarketDataService | None = None,
        limits: RiskLimits | None = None,
    ) -> None:
        self._session = session
        self._portfolios = portfolios or PortfolioService(session)
        self._market = market or MarketDataService(session)
        self._limits = limits or RiskLimits()

    def book_for(
        self,
        portfolio_id: int,
        ticker: str,
        as_of: datetime.datetime,
    ) -> RiskBook:
        """Snapshot the book for `enforce`. Prices stop at `as_of`."""
        snapshot = self._portfolios.snapshot(portfolio_id, as_of)
        positions = tuple(
            PositionRisk(
                ticker=item.ticker,
                sector=self._sector(item.ticker),
                value=item.value,
                quantity=item.quantity,
                average_cost=item.average_cost,
                market_price=item.market_price,
            )
            for item in snapshot.positions
        )
        bars = self._market.get_history(ticker, as_of.date(), limit=40)
        last_price = self._market.get_latest_price(ticker, as_of)
        if last_price is None and bars:
            last_price = bars[-1].close
        return RiskBook(
            ticker=ticker,
            sector=self._sector(ticker),
            total_value=snapshot.total_value,
            cash=snapshot.portfolio.cash,
            positions=positions,
            orders_today=self._orders_on(portfolio_id, as_of.date()),
            atr=atr(bars) if bars else None,
            last_price=last_price,
        )

    def trigger_stop_losses(self, portfolio_id: int, now: datetime.datetime) -> list[Order]:
        """Sell names whose previous close is at least `stop_loss` below cost."""
        previous = self._previous_session(now.date())
        if previous is None:
            return []
        decided_at = session_close(previous) or last_close(now)
        snapshot = self._portfolios.snapshot(portfolio_id, decided_at)
        marked = [
            PositionRisk(
                ticker=item.ticker,
                sector=self._sector(item.ticker),
                value=item.value,
                quantity=item.quantity,
                average_cost=item.average_cost,
                market_price=self._close_on(item.ticker, previous) or item.market_price,
            )
            for item in snapshot.positions
        ]
        placed: list[Order] = []
        for ticker in stop_loss_tickers(marked, self._limits.stop_loss):
            held = next(item for item in marked if item.ticker == ticker)
            if self._has_pending_sell(portfolio_id, ticker):
                continue
            placed.append(
                self._portfolios.place_order(
                    portfolio_id, ticker, OrderSide.SELL, held.quantity, decided_at
                )
            )
        return placed

    def _previous_session(self, day: datetime.date) -> datetime.date | None:
        prior = trading_days(day - datetime.timedelta(days=14), day - datetime.timedelta(days=1))
        return prior[-1] if prior else None

    def _close_on(self, ticker: str, day: datetime.date) -> Decimal | None:
        bars = self._market.get_history(ticker, day, limit=1)
        if not bars or bars[-1].date != day:
            return None
        return bars[-1].close

    def _orders_on(self, portfolio_id: int, day: datetime.date) -> int:
        orders = self._portfolios.list_orders(portfolio_id)
        return sum(1 for order in orders if order.decision_at.date() == day)

    def _has_pending_sell(self, portfolio_id: int, ticker: str) -> bool:
        statement = (
            select(Order)
            .options(joinedload(Order.instrument))
            .where(
                Order.portfolio_id == portfolio_id,
                Order.status == OrderStatus.PENDING,
                Order.side == OrderSide.SELL,
            )
        )
        return any(order.instrument.ticker == ticker for order in self._session.scalars(statement))

    def _sector(self, ticker: str) -> str:
        entry = next((item for item in UNIVERSE if item.ticker == ticker), None)
        return entry.sector if entry is not None else "Unknown"
