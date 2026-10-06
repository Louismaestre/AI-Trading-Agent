"""Store headlines and serve them without leaking anything published after `as_of`."""

import datetime
from collections.abc import Callable, Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import Instrument, NewsArticle
from app.providers.news_provider import fetch_news
from app.schemas.news import NewsBrief, NewsItem
from app.services.market_data_service import UnknownTickerError
from app.services.news_text import as_of_moment, drop_near_duplicates, format_brief
from app.universe import tradable_tickers

FetchNews = Callable[[str], list[NewsItem]]

DEFAULT_DAYS = 7
DEFAULT_LIMIT = 15


class NewsService:
    def __init__(self, session: Session, fetch: FetchNews = fetch_news) -> None:
        self._session = session
        self._fetch = fetch

    def sync(self, ticker: str) -> int:
        """Download headlines and upsert them. Returns the number of articles written."""
        instrument = self._instrument(ticker)
        items = self._fetch(ticker)
        self._upsert(instrument.id, items)
        return len(items)

    def sync_universe(self, tickers: Sequence[str] | None = None) -> int:
        return sum(self.sync(ticker) for ticker in tickers or tradable_tickers())

    def get_recent(
        self,
        ticker: str,
        as_of: datetime.date | datetime.datetime,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_LIMIT,
    ) -> list[NewsItem]:
        """Newest first, already public at `as_of`, de-duplicated, capped at `limit`."""
        instrument = self._instrument(ticker)
        end = as_of_moment(as_of)
        start = end - datetime.timedelta(days=days)
        statement = (
            select(NewsArticle)
            .where(
                NewsArticle.instrument_id == instrument.id,
                NewsArticle.published_at >= start,
                NewsArticle.published_at <= end,
            )
            .order_by(NewsArticle.published_at.desc())
        )
        stored = [NewsItem.model_validate(row) for row in self._session.scalars(statement)]
        return drop_near_duplicates(stored)[:limit]

    def format_recent(
        self,
        ticker: str,
        as_of: datetime.date | datetime.datetime,
        days: int = DEFAULT_DAYS,
        limit: int = DEFAULT_LIMIT,
    ) -> list[NewsBrief]:
        return [
            NewsBrief(
                published_at=item.published_at,
                source=item.source,
                title=item.title,
                summary=item.summary,
                brief=format_brief(item),
            )
            for item in self.get_recent(ticker, as_of, days, limit)
        ]

    def _instrument(self, ticker: str) -> Instrument:
        instrument = self._session.scalar(select(Instrument).where(Instrument.ticker == ticker))
        if instrument is None:
            raise UnknownTickerError(ticker)
        return instrument

    def _upsert(self, instrument_id: int, items: Sequence[NewsItem]) -> None:
        if not items:
            return
        rows = [{"instrument_id": instrument_id, **item.model_dump()} for item in items]
        statement = insert(NewsArticle).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=["instrument_id", "url"],
            set_={
                "published_at": statement.excluded.published_at,
                "source": statement.excluded.source,
                "title": statement.excluded.title,
                "summary": statement.excluded.summary,
            },
        )
        self._session.execute(statement)
        self._session.commit()
