"""Stores daily and intraday prices and serves them without ever leaking future data."""

import datetime
from collections.abc import Callable, Sequence
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.market_clock import ensure_aware
from app.models import DailyPrice, Instrument, IntradayPrice
from app.providers.yfinance_provider import fetch_daily_bars, fetch_intraday_bars
from app.schemas.market import INTRADAY_INTERVAL, Bar, IntradayBar, Ohlcv
from app.services.instrument_service import InstrumentService

FetchBars = Callable[[str, datetime.date, datetime.date], list[Bar]]
FetchIntradayBars = Callable[[str, datetime.datetime], list[IntradayBar]]


class UnknownTickerError(LookupError):
    """The ticker is not in the instruments table."""


class MarketDataService:
    def __init__(
        self,
        session: Session,
        fetch_bars: FetchBars = fetch_daily_bars,
        fetch_intraday: FetchIntradayBars = fetch_intraday_bars,
    ) -> None:
        self._session = session
        self._fetch_bars = fetch_bars
        self._fetch_intraday = fetch_intraday

    # --- Daily bars ---

    def sync_prices(self, ticker: str, start: datetime.date, end: datetime.date) -> int:
        """Download missing bars in `[start, end]`, including days before the first stored bar."""
        instrument = self._get_instrument(ticker)
        first_date, last_date = self._session.execute(
            select(func.min(DailyPrice.date), func.max(DailyPrice.date)).where(
                DailyPrice.instrument_id == instrument.id
            )
        ).one()
        if first_date is None or last_date is None:
            return self._store_daily(instrument.id, ticker, start, end)

        stored = 0
        if start < first_date:
            stored += self._store_daily(
                instrument.id, ticker, start, first_date - datetime.timedelta(days=1)
            )
        first_missing = last_date + datetime.timedelta(days=1)
        if first_missing <= end:
            stored += self._store_daily(instrument.id, ticker, first_missing, end)
        return stored

    def daily_span(
        self, tickers: Sequence[str]
    ) -> tuple[datetime.date | None, datetime.date | None]:
        """Earliest and latest stored daily bar among `tickers`. Both None if the table is empty."""
        first, last = self._session.execute(
            select(func.min(DailyPrice.date), func.max(DailyPrice.date))
            .join(Instrument, Instrument.id == DailyPrice.instrument_id)
            .where(Instrument.ticker.in_(list(tickers)))
        ).one()
        return first, last

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

    def calendar_return(self, ticker: str, year: int, as_of: datetime.date) -> Decimal | None:
        """Close-to-close return of `year`. None until that year is over at `as_of`."""
        if year >= as_of.year:
            return None
        bars = self.get_prices(ticker, datetime.date(year, 1, 1), datetime.date(year, 12, 31))
        if len(bars) < 2 or bars[0].close == 0:
            return None
        return (bars[-1].close / bars[0].close) - Decimal("1")

    # --- Intraday (5-minute) bars ---

    def sync_intraday(self, ticker: str, start: datetime.datetime) -> int:
        """Download 5-minute bars since `start` (or since the last stored one) and store them."""
        instrument = self._get_instrument(ticker)
        start = ensure_aware(start)

        last_timestamp = self._session.scalar(
            select(func.max(IntradayPrice.timestamp)).where(
                IntradayPrice.instrument_id == instrument.id
            )
        )
        # The last stored bar is downloaded again: it may have been saved while still in progress.
        since = start if last_timestamp is None else max(start, last_timestamp)

        bars = self._fetch_intraday(ticker, since)
        self._upsert(IntradayPrice, "timestamp", instrument.id, bars)
        return len(bars)

    def sync_universe_intraday(self, start: datetime.datetime) -> int:
        """Sync the 5-minute bars of every instrument. Returns the total number stored."""
        instruments = InstrumentService(self._session).list_instruments()
        return sum(self.sync_intraday(instrument.ticker, start) for instrument in instruments)

    def get_intraday(
        self, ticker: str, start: datetime.datetime, end: datetime.datetime
    ) -> list[IntradayBar]:
        """Stored 5-minute bars starting between `start` and `end`, oldest first."""
        instrument = self._get_instrument(ticker)
        statement = (
            select(IntradayPrice)
            .where(
                IntradayPrice.instrument_id == instrument.id,
                IntradayPrice.timestamp.between(ensure_aware(start), ensure_aware(end)),
            )
            .order_by(IntradayPrice.timestamp.asc())
        )
        return [IntradayBar.model_validate(price) for price in self._session.scalars(statement)]

    def get_latest_price(self, ticker: str, as_of: datetime.datetime) -> Decimal | None:
        """Close of the latest 5-minute bar already finished at `as_of`. None if there is none."""
        instrument = self._get_instrument(ticker)
        # A bar starting at 10:00 only has its close at 10:05: bars still in progress are excluded.
        finished_before = ensure_aware(as_of) - INTRADAY_INTERVAL
        return self._session.scalar(
            select(IntradayPrice.close)
            .where(
                IntradayPrice.instrument_id == instrument.id,
                IntradayPrice.timestamp <= finished_before,
            )
            .order_by(IntradayPrice.timestamp.desc())
            .limit(1)
        )

    # --- Helpers ---

    def _store_daily(
        self, instrument_id: int, ticker: str, start: datetime.date, end: datetime.date
    ) -> int:
        if start > end:
            return 0
        bars = self._fetch_bars(ticker, start, end)
        self._upsert(DailyPrice, "date", instrument_id, bars)
        return len(bars)

    def _get_instrument(self, ticker: str) -> Instrument:
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            raise UnknownTickerError(ticker)
        return instrument

    def _upsert(
        self,
        table: type[DailyPrice] | type[IntradayPrice],
        time_column: str,
        instrument_id: int,
        bars: Sequence[Ohlcv],
    ) -> None:
        """Insert the bars, or overwrite their prices if already stored (Yahoo revises them)."""
        if not bars:
            return
        rows = [{"instrument_id": instrument_id, **bar.model_dump()} for bar in bars]
        statement = insert(table).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=["instrument_id", time_column],
            set_={field: statement.excluded[field] for field in Ohlcv.model_fields},
        )
        self._session.execute(statement)
        self._session.commit()
