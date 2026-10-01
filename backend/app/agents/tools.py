"""Portfolio and market lookups used by the buyer and seller. No trading logic here."""

import datetime
from dataclasses import dataclass
from decimal import Decimal

from app.models import Order, OrderSide
from app.schemas.fundamentals import FundamentalSnapshot
from app.schemas.news import NewsItem
from app.services.fundamentals_service import FundamentalsService
from app.services.market_data_service import MarketDataService
from app.services.news_service import NewsService
from app.services.portfolio_service import PortfolioService, PositionView


@dataclass(frozen=True)
class QuantityCheck:
    proposed: int
    accepted: int
    corrected: bool


def target_buy_quantity(total_value: Decimal, price: Decimal, target_weight: float) -> int:
    """Whole shares so that the position is `target_weight` of `total_value`."""
    if price <= 0 or target_weight <= 0:
        return 0
    budget = total_value * Decimal(str(target_weight))
    return int(budget // price)


def target_sell_quantity(
    position_qty: int, total_value: Decimal, price: Decimal, target_weight: float
) -> int:
    """Shares to sell so the leftover position matches `target_weight`."""
    keep = target_buy_quantity(total_value, price, target_weight)
    return max(0, position_qty - keep)


def enforce_quantity(proposed: int, expected: int) -> QuantityCheck:
    """Always keep the Python size. Record whether the agent disagreed."""
    accepted = max(0, expected)
    return QuantityCheck(proposed=proposed, accepted=accepted, corrected=proposed != accepted)


@dataclass
class AgentTools:
    """Bound to one portfolio and one `as_of`. Delegates to the existing services."""

    portfolios: PortfolioService
    market: MarketDataService
    portfolio_id: int
    as_of: datetime.datetime
    fundamentals: FundamentalsService | None = None
    news: NewsService | None = None

    def get_last_price(self, ticker: str) -> Decimal | None:
        price = self.market.get_latest_price(ticker, self.as_of)
        if price is not None:
            return price
        history = self.market.get_history(ticker, self.as_of.date(), limit=1)
        return history[0].close if history else None

    def get_cash(self) -> Decimal:
        return self.portfolios.get(self.portfolio_id).cash

    def get_total_value(self) -> Decimal:
        return self.portfolios.snapshot(self.portfolio_id, self.as_of).total_value

    def get_fundamentals(self, ticker: str) -> FundamentalSnapshot | None:
        """Filings already public at `as_of`. None if no fundamentals service is bound."""
        if self.fundamentals is None:
            return None
        return self.fundamentals.get_snapshot(ticker, self.as_of.date())

    def get_news(self, ticker: str, days: int = 7, limit: int = 15) -> list[NewsItem]:
        """Headlines already published at `as_of`. Empty if no news service is bound."""
        if self.news is None:
            return []
        return self.news.get_recent(ticker, self.as_of, days=days, limit=limit)

    def get_position(self, ticker: str) -> PositionView | None:
        snapshot = self.portfolios.snapshot(self.portfolio_id, self.as_of)
        return next((item for item in snapshot.positions if item.ticker == ticker), None)

    def place_order(self, ticker: str, side: OrderSide, quantity: int) -> Order:
        if quantity < 1:
            raise ValueError("quantity must be >= 1")
        return self.portfolios.place_order(self.portfolio_id, ticker, side, quantity, self.as_of)
