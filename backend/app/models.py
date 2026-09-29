"""Database tables. Run `make migration m="..."` after any change."""

import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import TimestampedModel


class OrderSide(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(StrEnum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    REJECTED = "REJECTED"


class AgentAction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Instrument(TimestampedModel):
    """A tracked stock or index, e.g. `MC.PA` (LVMH) or `^FCHI` (CAC 40)."""

    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    isin: Mapped[str | None] = mapped_column(String(12), unique=True)
    sector: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(default=True)


class OhlcvColumns:
    """Price and volume columns shared by daily and intraday bars."""

    open: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    volume: Mapped[int] = mapped_column(BigInteger)


class DailyPrice(OhlcvColumns, TimestampedModel):
    """One OHLCV bar per instrument and trading day."""

    __tablename__ = "daily_prices"
    __table_args__ = (UniqueConstraint("instrument_id", "date"),)

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    date: Mapped[datetime.date] = mapped_column()


class IntradayPrice(OhlcvColumns, TimestampedModel):
    """One 5-minute OHLCV bar per instrument; `timestamp` is the start of the bar, in UTC."""

    __tablename__ = "intraday_prices"
    __table_args__ = (UniqueConstraint("instrument_id", "timestamp"),)

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))


class Portfolio(TimestampedModel):
    """Simulated portfolio: cash plus the positions built by filled orders."""

    __tablename__ = "portfolios"

    name: Mapped[str] = mapped_column(String(200))
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    cash: Mapped[Decimal] = mapped_column(Numeric(14, 4))

    positions: Mapped[list["Position"]] = relationship(back_populates="portfolio")
    orders: Mapped[list["Order"]] = relationship(back_populates="portfolio")
    decisions: Mapped[list["AgentDecision"]] = relationship(back_populates="portfolio")


class Position(TimestampedModel):
    """Shares held in one instrument. Removed when the quantity falls to zero."""

    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("portfolio_id", "instrument_id"),)

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    portfolio: Mapped[Portfolio] = relationship(back_populates="positions")
    instrument: Mapped[Instrument] = relationship()


class Order(TimestampedModel):
    """One buy or sell decision, waiting for a later price, filled, or rejected."""

    __tablename__ = "orders"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"))
    side: Mapped[OrderSide] = mapped_column(Enum(OrderSide, native_enum=False, length=8))
    quantity: Mapped[int] = mapped_column(Integer)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, native_enum=False, length=16))
    decision_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    executed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    execution_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    fees: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    rejection_reason: Mapped[str | None] = mapped_column(String(200))

    portfolio: Mapped[Portfolio] = relationship(back_populates="orders")
    instrument: Mapped[Instrument] = relationship()
    decision: Mapped["AgentDecision | None"] = relationship(back_populates="order", uselist=False)


class AgentDecision(TimestampedModel):
    """One analyst decision for a ticker, optionally linked to the order it produced."""

    __tablename__ = "agent_decisions"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="RESTRICT"))
    as_of: Mapped[datetime.date] = mapped_column()
    action: Mapped[AgentAction] = mapped_column(Enum(AgentAction, native_enum=False, length=8))
    confidence: Mapped[float] = mapped_column()
    target_weight: Mapped[float] = mapped_column()
    rationale: Mapped[str] = mapped_column(String(2000))
    llm_model: Mapped[str] = mapped_column(String(100))
    duration_ms: Mapped[int] = mapped_column(Integer)
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))

    portfolio: Mapped[Portfolio] = relationship(back_populates="decisions")
    instrument: Mapped[Instrument] = relationship()
    order: Mapped[Order | None] = relationship(back_populates="decision")
