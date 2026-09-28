"""Stores daily prices and serves them without ever leaking future data."""

import datetime
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import DailyPrice, Instrument
from app.providers.yfinance_provider import fetch_daily_bars
from app.schemas.market import Bar
from app.services.instrument_service import InstrumentService

FetchBars = Callable[[str, datetime.date, datetime.date], list[Bar]]


class UnknownTickerError(LookupError):
    """The ticker is not in the instruments table."""


class MarketDataService:
    def __init__(self, session: Session, fetch_bars: FetchBars = fetch_daily_bars) -> None:
        self._session = session
        self._fetch_bars = fetch_bars

    def sync_prices(self, ticker: str, start: datetime.date, end: datetime.date) -> int:
        """Download the missing bars up to `end` and store them. Returns the number stored."""
        instrument = self._get_instrument(ticker)

        last_date = self._session.scalar(
            select(func.max(DailyPrice.date)).where(DailyPrice.instrument_id == instrument.id)
        )
        first_missing = start if last_date is None else last_date + datetime.timedelta(days=1)
        if first_missing > end:
            return 0

        bars = self._fetch_bars(ticker, first_missing, end)
        if not bars:
            return 0

        rows = [{"instrument_id": instrument.id, **bar.model_dump()} for bar in bars]
        statement = insert(DailyPrice).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[DailyPrice.instrument_id, DailyPrice.date],
            set_={
                "open": statement.excluded.open,
                "high": statement.excluded.high,
                "low": statement.excluded.low,
                "close": statement.excluded.close,
                "volume": statement.excluded.volume,
            },
        )
        self._session.execute(statement)
        self._session.commit()
        return len(bars)

    def sync_universe_prices(self, start: datetime.date, end: datetime.date) -> int:
        """Sync every instrument. Returns the total number of bars stored."""
        instruments = InstrumentService(self._session).list_instruments()
        return sum(self.sync_prices(instrument.ticker, start, end) for instrument in instruments)

    def get_history(self, ticker: str, as_of: datetime.date, limit: int) -> list[Bar]:
        """The `limit` latest bars dated on or before `as_of`, oldest first."""
        instrument = self._get_instrument(ticker)
        statement = (
            select(DailyPrice)
            .where(DailyPrice.instrument_id == instrument.id, DailyPrice.date <= as_of)
            .order_by(DailyPrice.date.desc())
            .limit(limit)
        )
        newest_first = self._session.scalars(statement).all()
        return [Bar.model_validate(price) for price in reversed(newest_first)]

    def get_prices(self, ticker: str, start: datetime.date, end: datetime.date) -> list[Bar]:
        """Stored bars between `start` and `end` (both included), oldest first."""
        instrument = self._get_instrument(ticker)
        statement = (
            select(DailyPrice)
            .where(DailyPrice.instrument_id == instrument.id, DailyPrice.date.between(start, end))
            .order_by(DailyPrice.date.asc())
        )
        oldest_first = self._session.scalars(statement).all()
        return [Bar.model_validate(price) for price in oldest_first]

    def _get_instrument(self, ticker: str) -> Instrument:
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            raise UnknownTickerError(ticker)
        return instrument
