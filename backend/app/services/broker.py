"""How an order gets a fill price. Only SimulatedBroker is implemented for now."""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.market_clock import ensure_aware, session_open
from app.models import DailyPrice, IntradayPrice, OrderSide
from app.services.fees import money

# Simulated adverse move between decision and fill (buy pays more, sell receives less).
SLIPPAGE_RATE = Decimal("0.0005")


@dataclass(frozen=True)
class Fill:
    """A price the broker can actually trade, strictly after the decision."""

    executed_at: datetime.datetime
    price: Decimal


class Broker(Protocol):
    def fill(
        self,
        side: OrderSide,
        instrument_id: int,
        decision_at: datetime.datetime,
        now: datetime.datetime,
    ) -> Fill | None:
        """First known price after `decision_at` that is available by `now`, plus slippage."""


class SimulatedBroker:
    """Uses stored bars. Never fills on the price that was visible at decision time."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def fill(
        self,
        side: OrderSide,
        instrument_id: int,
        decision_at: datetime.datetime,
        now: datetime.datetime,
    ) -> Fill | None:
        raw = self._first_price(instrument_id, ensure_aware(decision_at), ensure_aware(now))
        if raw is None:
            return None
        executed_at, price = raw
        return Fill(executed_at=executed_at, price=_apply_slippage(side, price))

    def _first_price(
        self,
        instrument_id: int,
        decision_at: datetime.datetime,
        now: datetime.datetime,
    ) -> tuple[datetime.datetime, Decimal] | None:
        if now <= decision_at:
            return None
        return self._first_intraday(instrument_id, decision_at, now) or self._first_daily_open(
            instrument_id, decision_at, now
        )

    def _first_intraday(
        self,
        instrument_id: int,
        decision_at: datetime.datetime,
        now: datetime.datetime,
    ) -> tuple[datetime.datetime, Decimal] | None:
        bar = self._session.scalar(
            select(IntradayPrice)
            .where(
                IntradayPrice.instrument_id == instrument_id,
                IntradayPrice.timestamp > decision_at,
                IntradayPrice.timestamp <= now,
            )
            .order_by(IntradayPrice.timestamp.asc())
            .limit(1)
        )
        if bar is None:
            return None
        return bar.timestamp, bar.open

    def _first_daily_open(
        self,
        instrument_id: int,
        decision_at: datetime.datetime,
        now: datetime.datetime,
    ) -> tuple[datetime.datetime, Decimal] | None:
        """Next session open after the decision, once that session has started."""
        bars = self._session.scalars(
            select(DailyPrice)
            .where(DailyPrice.instrument_id == instrument_id)
            .order_by(DailyPrice.date.asc())
        )
        for bar in bars:
            opened_at = session_open(bar.date)
            if opened_at is None or opened_at <= decision_at or opened_at > now:
                continue
            return opened_at, bar.open
        return None


def _apply_slippage(side: OrderSide, price: Decimal) -> Decimal:
    if side is OrderSide.BUY:
        return money(price * (1 + SLIPPAGE_RATE))
    return money(price * (1 - SLIPPAGE_RATE))
