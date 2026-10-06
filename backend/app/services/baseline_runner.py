"""Turn a baseline AnalystDecision into an order. No LLM."""

import datetime
from collections.abc import Sequence

from app.agents.tools import AgentTools, target_buy_quantity, target_sell_quantity
from app.indicators import technical_summary
from app.models import OrderSide, OrderStatus, ReplayKind
from app.schemas.agents import AnalystDecision
from app.services.baselines import equal_weight, random_decision, sma_crossover_decision
from app.services.fees import FEE_BUFFER
from app.services.market_data_service import MarketDataService, UnknownTickerError
from app.services.portfolio_service import PortfolioService

HISTORY_LIMIT = 80


def run_baseline_day(
    portfolios: PortfolioService,
    market: MarketDataService,
    portfolio_id: int,
    as_of: datetime.date,
    moment: datetime.datetime,
    tickers: Sequence[str],
    kind: ReplayKind,
    seed: int,
) -> None:
    """One decision day for SMA or random. Same broker path as the agents."""
    tools = AgentTools(portfolios, market, portfolio_id, moment)
    weight = equal_weight(len(tickers))
    for ticker in tickers:
        try:
            bars = market.get_history(ticker, as_of, limit=HISTORY_LIMIT)
        except UnknownTickerError:
            continue
        if not bars:
            continue
        if _pending_for(tools, ticker):
            continue
        summary = technical_summary(bars)
        held = tools.get_position(ticker) is not None
        if kind is ReplayKind.SMA_CROSS:
            decision = sma_crossover_decision(summary, held, weight)
        else:
            decision = random_decision(ticker, as_of, seed, held, weight)
        _apply(tools, ticker, decision)


def _pending_for(tools: AgentTools, ticker: str) -> bool:
    return any(
        order.status is OrderStatus.PENDING and order.instrument.ticker == ticker
        for order in tools.portfolios.list_orders(tools.portfolio_id)
    )


def _apply(tools: AgentTools, ticker: str, decision: AnalystDecision) -> None:
    if decision.action == "HOLD":
        return
    price = tools.get_last_price(ticker)
    if price is None:
        return
    position = tools.get_position(ticker)
    if decision.action == "BUY":
        if position is not None:
            return
        budget = tools.get_total_value() * FEE_BUFFER
        quantity = target_buy_quantity(budget, price, decision.target_weight)
        if quantity >= 1:
            tools.place_order(ticker, OrderSide.BUY, quantity)
        return
    if position is None:
        return
    quantity = target_sell_quantity(
        position.quantity, tools.get_total_value(), price, decision.target_weight
    )
    if quantity >= 1:
        tools.place_order(ticker, OrderSide.SELL, quantity)
