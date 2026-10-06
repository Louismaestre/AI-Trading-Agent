"""Database tables. Run `make migration m="..."` after any change."""

import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
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


class LiveSessionStatus(StrEnum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"


class LiveSessionKind(StrEnum):
    AGENTS = "AGENTS"
    BUY_AND_HOLD = "BUY_AND_HOLD"


class ReplayStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"


class ReplayKind(StrEnum):
    AGENTS = "AGENTS"
    BUY_AND_HOLD = "BUY_AND_HOLD"


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
    reports: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    debate: Mapped[list[object] | None] = mapped_column(JSONB, nullable=True)
    risk: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

    portfolio: Mapped[Portfolio] = relationship(back_populates="decisions")
    instrument: Mapped[Instrument] = relationship()
    order: Mapped[Order | None] = relationship(back_populates="decision")


class LiveSession(TimestampedModel):
    """One live run of the agents on a portfolio, during market hours."""

    __tablename__ = "live_sessions"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    interval_minutes: Mapped[int] = mapped_column(Integer, default=15)
    status: Mapped[LiveSessionStatus] = mapped_column(
        Enum(LiveSessionStatus, native_enum=False, length=16)
    )
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    last_slot: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    kind: Mapped[LiveSessionKind] = mapped_column(
        Enum(LiveSessionKind, native_enum=False, length=16), default=LiveSessionKind.AGENTS
    )
    benchmark_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("live_sessions.id", ondelete="SET NULL")
    )

    portfolio: Mapped[Portfolio] = relationship()
    equity_points: Mapped[list["EquityPoint"]] = relationship(back_populates="session")
    benchmark_session: Mapped["LiveSession | None"] = relationship(
        remote_side="LiveSession.id", foreign_keys=[benchmark_session_id]
    )


class Replay(TimestampedModel):
    """One historical run of the agents on a portfolio (daily or weekly decisions)."""

    __tablename__ = "replays"

    portfolio_id: Mapped[int] = mapped_column(ForeignKey("portfolios.id", ondelete="CASCADE"))
    start_date: Mapped[datetime.date] = mapped_column()
    end_date: Mapped[datetime.date] = mapped_column()
    decision_frequency: Mapped[str] = mapped_column(String(16), default="WEEKLY")
    status: Mapped[ReplayStatus] = mapped_column(Enum(ReplayStatus, native_enum=False, length=16))
    days_done: Mapped[int] = mapped_column(Integer, default=0)
    days_total: Mapped[int] = mapped_column(Integer, default=0)
    current_date: Mapped[datetime.date | None] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(String(2000))
    kind: Mapped[ReplayKind] = mapped_column(
        Enum(ReplayKind, native_enum=False, length=16), default=ReplayKind.AGENTS
    )
    benchmark_replay_id: Mapped[int | None] = mapped_column(
        ForeignKey("replays.id", ondelete="SET NULL")
    )

    portfolio: Mapped[Portfolio] = relationship()
    equity_points: Mapped[list["EquityPoint"]] = relationship(back_populates="replay")
    benchmark_replay: Mapped["Replay | None"] = relationship(
        remote_side="Replay.id", foreign_keys=[benchmark_replay_id]
    )


class Fundamental(TimestampedModel):
    """One quarterly filing. Visible in replay only after period_end + publication delay."""

    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("instrument_id", "period_end"),)

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    period_end: Mapped[datetime.date] = mapped_column()
    revenue: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    gross_profit: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    operating_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    net_income: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    diluted_eps: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    total_debt: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    total_equity: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    operating_cash_flow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))

    instrument: Mapped[Instrument] = relationship()


class NewsArticle(TimestampedModel):
    """One headline tied to an instrument. Hidden in replay when published after `as_of`."""

    __tablename__ = "news_articles"
    __table_args__ = (
        UniqueConstraint("instrument_id", "url"),
        Index("ix_news_articles_instrument_id_published_at", "instrument_id", "published_at"),
    )

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    published_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str | None] = mapped_column(String(2000))
    url: Mapped[str] = mapped_column(String(1000))

    instrument: Mapped[Instrument] = relationship()


class EquityPoint(TimestampedModel):
    """Portfolio mark-to-market taken at a live cycle or a replay close."""

    __tablename__ = "equity_points"
    __table_args__ = (
        CheckConstraint(
            "(session_id IS NULL) != (replay_id IS NULL)",
            name="one_owner",
        ),
    )

    session_id: Mapped[int | None] = mapped_column(
        ForeignKey("live_sessions.id", ondelete="CASCADE")
    )
    replay_id: Mapped[int | None] = mapped_column(ForeignKey("replays.id", ondelete="CASCADE"))
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    cash: Mapped[Decimal] = mapped_column(Numeric(14, 4))

    session: Mapped[LiveSession | None] = relationship(back_populates="equity_points")
    replay: Mapped[Replay | None] = relationship(back_populates="equity_points")
