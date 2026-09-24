"""Database tables. Run `make migration m="..."` after any change."""

import datetime
from decimal import Decimal

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.schema import UniqueConstraint
from sqlalchemy.sql.schema import ForeignKey
from sqlalchemy.types import BigInteger, Numeric

from app.database import TimestampedModel


class Instrument(TimestampedModel):
    """A tracked stock or index, e.g. `MC.PA` (LVMH) or `^FCHI` (CAC 40)."""

    __tablename__ = "instruments"

    ticker: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    isin: Mapped[str | None] = mapped_column(String(12), unique=True)
    sector: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_active: Mapped[bool] = mapped_column(default=True)


class DailyPrice(TimestampedModel):
    """One OHLCV bar per instrument and trading day."""

    __tablename__ = "daily_prices"

    instrument_id: Mapped[int] = mapped_column(ForeignKey("instruments.id", ondelete="CASCADE"))
    date: Mapped[datetime.date] = mapped_column()
    __table_args__ = (UniqueConstraint("instrument_id", "date"),)
    open: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    high: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    low: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    close: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    volume: Mapped[int] = mapped_column(BigInteger)
