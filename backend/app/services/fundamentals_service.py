"""Store quarterly filings and serve them without leaking quarters not yet public at `as_of`."""

import datetime
from collections.abc import Callable, Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Fundamental, Instrument
from app.providers.fundamentals_provider import fetch_fundamentals
from app.schemas.fundamentals import FundamentalPeriod, FundamentalSnapshot
from app.services.fundamental_ratios import (
    known_statements,
    leverage,
    net_margin,
    pe_ratio,
    revenue_growth,
)
from app.services.market_data_service import MarketDataService, UnknownTickerError
from app.universe import tradable_tickers

FetchFundamentals = Callable[[str], list[FundamentalPeriod]]


class FundamentalsService:
    def __init__(
        self,
        session: Session,
        fetch: FetchFundamentals = fetch_fundamentals,
        market: MarketDataService | None = None,
        delay_days: int | None = None,
    ) -> None:
        self._session = session
        self._fetch = fetch
        self._market = market or MarketDataService(session)
        self._delay = (
            delay_days
            if delay_days is not None
            else get_settings().fundamentals_publication_delay_days
        )

    def sync(self, ticker: str) -> int:
        """Download restated quarters and upsert them. Returns the number of periods written."""
        instrument = self._instrument(ticker)
        periods = self._fetch(ticker)
        self._upsert(instrument.id, periods)
        return len(periods)

    def sync_universe(self, tickers: Sequence[str] | None = None) -> int:
        """Sync every tradable ticker (not the index). Returns the total number written."""
        return sum(self.sync(ticker) for ticker in tickers or tradable_tickers())

    def get_snapshot(self, ticker: str, as_of: datetime.date) -> FundamentalSnapshot:
        """Filings already public at `as_of`, with ratios priced on that day's close."""
        stored = self._stored(ticker)
        visible = known_statements(stored, as_of, self._delay)
        price = self._price_on(ticker, as_of)
        return FundamentalSnapshot(
            as_of=as_of,
            price=price,
            statements=visible,
            pe_ratio=pe_ratio(price, visible),
            revenue_growth=revenue_growth(visible),
            net_margin=net_margin(visible),
            leverage=leverage(visible),
        )

    def _stored(self, ticker: str) -> list[FundamentalPeriod]:
        instrument = self._instrument(ticker)
        statement = (
            select(Fundamental)
            .where(Fundamental.instrument_id == instrument.id)
            .order_by(Fundamental.period_end.desc())
        )
        return [FundamentalPeriod.model_validate(row) for row in self._session.scalars(statement)]

    def _price_on(self, ticker: str, as_of: datetime.date) -> Decimal | None:
        bars = self._market.get_history(ticker, as_of, limit=1)
        return bars[-1].close if bars else None

    def _instrument(self, ticker: str) -> Instrument:
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            raise UnknownTickerError(ticker)
        return instrument

    def _upsert(self, instrument_id: int, periods: Sequence[FundamentalPeriod]) -> None:
        if not periods:
            return
        rows = [{"instrument_id": instrument_id, **period.model_dump()} for period in periods]
        statement = insert(Fundamental).values(rows)
        fields = list(FundamentalPeriod.model_fields)
        fields.remove("period_end")
        statement = statement.on_conflict_do_update(
            index_elements=["instrument_id", "period_end"],
            set_={field: statement.excluded[field] for field in fields},
        )
        self._session.execute(statement)
        self._session.commit()
