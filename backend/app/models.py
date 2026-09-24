"""Database tables. Run `make migration m="..."` after any change."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

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
