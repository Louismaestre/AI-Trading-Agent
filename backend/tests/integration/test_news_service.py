import datetime

import pytest
from sqlalchemy.orm import Session

from app.agents.tools import AgentTools
from app.schemas.news import NewsItem
from app.services.instrument_service import InstrumentService
from app.services.market_data_service import MarketDataService, UnknownTickerError
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService

AS_OF = datetime.datetime(2026, 7, 15, 10, 0, tzinfo=datetime.UTC)


def _item(title: str, when: datetime.datetime, url: str) -> NewsItem:
    return NewsItem(
        published_at=when,
        source="Les Echos",
        title=title,
        summary="Sales rose.",
        url=url,
    )


class _Fetch:
    def __init__(self, items: list[NewsItem]) -> None:
        self.items = items
        self.calls: list[str] = []

    def __call__(self, ticker: str) -> list[NewsItem]:
        self.calls.append(ticker)
        return list(self.items)


@pytest.fixture
def service(db_session: Session) -> NewsService:
    InstrumentService(db_session).sync_universe()
    return NewsService(db_session, fetch=_Fetch([]))


def test_articles_after_as_of_are_hidden(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()
    fetch = _Fetch(
        [
            _item("Before", AS_OF - datetime.timedelta(hours=2), "https://example.com/before"),
            _item("After", AS_OF + datetime.timedelta(hours=2), "https://example.com/after"),
        ]
    )
    live = NewsService(db_session, fetch=fetch)
    live.sync("MC.PA")

    recent = live.get_recent("MC.PA", AS_OF)

    assert [item.title for item in recent] == ["Before"]


def test_near_duplicate_titles_are_dropped(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()
    fetch = _Fetch(
        [
            _item("LVMH beats forecasts", AS_OF.replace(hour=8), "https://example.com/a"),
            _item("LVMH beats forecasts!", AS_OF.replace(hour=9), "https://example.com/b"),
        ]
    )
    live = NewsService(db_session, fetch=fetch)
    live.sync("MC.PA")

    recent = live.get_recent("MC.PA", AS_OF)

    assert [item.title for item in recent] == ["LVMH beats forecasts!"]


def test_unknown_ticker_is_rejected(service: NewsService) -> None:
    with pytest.raises(UnknownTickerError):
        service.get_recent("NOPE.PA", AS_OF)


def test_agent_tools_hide_articles_after_as_of(db_session: Session) -> None:
    InstrumentService(db_session).sync_universe()
    live = NewsService(
        db_session,
        fetch=_Fetch(
            [
                _item("Before", AS_OF - datetime.timedelta(hours=1), "https://example.com/before"),
                _item("After", AS_OF + datetime.timedelta(hours=1), "https://example.com/after"),
            ]
        ),
    )
    live.sync("MC.PA")
    tools = AgentTools(
        PortfolioService(db_session),
        MarketDataService(db_session),
        PortfolioService(db_session).create("demo").id,
        AS_OF,
        news=live,
    )

    headlines = tools.get_news("MC.PA")

    assert [item.title for item in headlines] == ["Before"]
    assert all(item.published_at <= AS_OF for item in headlines)
