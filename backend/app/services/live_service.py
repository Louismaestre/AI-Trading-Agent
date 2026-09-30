"""One live cycle: refresh prices, run agents if the market is open, store equity."""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.tools import target_buy_quantity
from app.llm import StructuredLLM
from app.market_clock import ensure_aware, is_market_open, last_close
from app.models import (
    AgentDecision,
    EquityPoint,
    LiveSession,
    LiveSessionKind,
    LiveSessionStatus,
    OrderSide,
)
from app.services.agent_service import AgentService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import DEFAULT_CAPITAL, PortfolioService, PortfolioView
from app.universe import tradable_tickers

# Leave room for brokerage + FTT so equal-weight buys do not exhaust cash.
_FEE_BUFFER = Decimal("0.994")

DEFAULT_INTERVAL_MINUTES = 15
INTRADAY_LOOKBACK = datetime.timedelta(days=2)


class UnknownLiveSessionError(LookupError):
    """No live session exists for this id."""


class InvalidLiveSessionStateError(ValueError):
    """The requested status change is not allowed from the current status."""

    def __init__(self, current: LiveSessionStatus, target: LiveSessionStatus) -> None:
        super().__init__(f"Cannot move a {current.value} session to {target.value}")
        self.current = current
        self.target = target


@dataclass(frozen=True)
class CycleResult:
    ran: bool
    reason: str
    decision_count: int
    equity_id: int | None


def cycle_slot(now: datetime.datetime, interval_minutes: int) -> datetime.datetime:
    """Floor `now` to the start of its analysis slot (e.g. 10:07 / 15 min → 10:00)."""
    now = ensure_aware(now)
    if interval_minutes < 1:
        raise ValueError("interval_minutes must be >= 1")
    total = now.hour * 60 + now.minute
    floored = (total // interval_minutes) * interval_minutes
    return now.replace(hour=floored // 60, minute=floored % 60, second=0, microsecond=0)


class LiveService:
    def __init__(
        self,
        session: Session,
        llm: StructuredLLM | None = None,
        market: MarketDataService | None = None,
        agents: AgentService | None = None,
    ) -> None:
        self._session = session
        self._portfolios = PortfolioService(session)
        self._market = market or MarketDataService(session)
        self._agents = agents or AgentService(session, llm=llm)

    def start(
        self,
        name: str = "Live",
        initial_capital: Decimal = DEFAULT_CAPITAL,
        interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
        now: datetime.datetime | None = None,
        tickers: Sequence[str] | None = None,
    ) -> LiveSession:
        """Create a portfolio and open the agent session plus its buy-and-hold twin."""
        portfolio = self._portfolios.create(name, initial_capital)
        return self.create(portfolio.id, interval_minutes, now, tickers)

    def create(
        self,
        portfolio_id: int,
        interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
        now: datetime.datetime | None = None,
        tickers: Sequence[str] | None = None,
    ) -> LiveSession:
        """Start an agent session and a buy-and-hold twin with the same capital."""
        now = ensure_aware(now or datetime.datetime.now(datetime.UTC))
        source = self._portfolios.get(portfolio_id)
        benchmark = self._portfolios.create(f"{source.name} (buy and hold)", source.initial_capital)
        self.open_equal_weight(benchmark.id, now, tickers or tradable_tickers())
        hold = self._new_session(benchmark.id, interval_minutes, now, LiveSessionKind.BUY_AND_HOLD)
        agents = self._new_session(
            portfolio_id, interval_minutes, now, LiveSessionKind.AGENTS, hold.id
        )
        self._session.commit()
        return agents

    def _new_session(
        self,
        portfolio_id: int,
        interval_minutes: int,
        now: datetime.datetime,
        kind: LiveSessionKind,
        benchmark_session_id: int | None = None,
    ) -> LiveSession:
        row = LiveSession(
            portfolio_id=portfolio_id,
            interval_minutes=interval_minutes,
            status=LiveSessionStatus.RUNNING,
            started_at=now,
            kind=kind,
            benchmark_session_id=benchmark_session_id,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def open_equal_weight(
        self, portfolio_id: int, now: datetime.datetime, tickers: Sequence[str]
    ) -> None:
        priced = [(ticker, price) for ticker in tickers if (price := self._last_price(ticker, now))]
        if not priced:
            return
        capital = self._portfolios.get(portfolio_id).initial_capital
        usable = capital * _FEE_BUFFER
        weight = 1 / len(priced)
        decision_at = last_close(now)
        for ticker, price in priced:
            quantity = target_buy_quantity(usable, price, weight)
            if quantity < 1:
                continue
            self._portfolios.place_order(portfolio_id, ticker, OrderSide.BUY, quantity, decision_at)
        self._portfolios.execute_pending_orders(portfolio_id, now)

    def _last_price(self, ticker: str, now: datetime.datetime) -> Decimal | None:
        price = self._market.get_latest_price(ticker, now)
        if price is not None:
            return price
        history = self._market.get_history(ticker, now.date(), limit=1)
        return history[0].close if history else None

    def run_cycle(
        self,
        session_id: int,
        now: datetime.datetime,
        tickers: Sequence[str] | None = None,
    ) -> CycleResult:
        now = ensure_aware(now)
        live = self._get(session_id)
        if live.status is not LiveSessionStatus.RUNNING:
            return CycleResult(False, "not_running", 0, None)
        if not is_market_open(now):
            return CycleResult(False, "closed", 0, None)
        slot = cycle_slot(now, live.interval_minutes)
        if live.last_slot is not None and live.last_slot == slot:
            return CycleResult(False, "duplicate_slot", 0, None)

        self._market.sync_universe_intraday(now - INTRADAY_LOOKBACK)
        self._portfolios.execute_pending_orders(live.portfolio_id, now)
        decisions = []
        if live.kind is LiveSessionKind.AGENTS:
            decisions = self._agents.run_agents(live.portfolio_id, now, tickers=tickers)
        snapshot = self._portfolios.snapshot(live.portfolio_id, now)
        point = EquityPoint(
            session_id=live.id,
            recorded_at=now,
            total_value=snapshot.total_value,
            cash=snapshot.portfolio.cash,
        )
        live.last_slot = slot
        self._session.add(point)
        self._session.commit()
        return CycleResult(True, "ok", len(decisions), point.id)

    def mark_at_close(self, session_id: int, close: datetime.datetime) -> EquityPoint | None:
        """Store the close valuation once per session and close timestamp."""
        close = ensure_aware(close)
        live = self._get(session_id)
        existing = self._session.scalar(
            select(EquityPoint).where(
                EquityPoint.session_id == live.id, EquityPoint.recorded_at == close
            )
        )
        if existing is not None:
            return None
        snapshot = self._portfolios.snapshot(live.portfolio_id, close)
        point = EquityPoint(
            session_id=live.id,
            recorded_at=close,
            total_value=snapshot.total_value,
            cash=snapshot.portfolio.cash,
        )
        self._session.add(point)
        self._session.commit()
        return point

    def get(self, session_id: int) -> LiveSession:
        return self._get(session_id)

    def portfolio_snapshot(self, portfolio_id: int, now: datetime.datetime) -> PortfolioView:
        return self._portfolios.snapshot(portfolio_id, now)

    def pause(self, session_id: int) -> LiveSession:
        return self._transition(session_id, {LiveSessionStatus.RUNNING}, LiveSessionStatus.PAUSED)

    def resume(self, session_id: int) -> LiveSession:
        return self._transition(session_id, {LiveSessionStatus.PAUSED}, LiveSessionStatus.RUNNING)

    def stop(self, session_id: int) -> LiveSession:
        return self._transition(
            session_id,
            {LiveSessionStatus.RUNNING, LiveSessionStatus.PAUSED},
            LiveSessionStatus.STOPPED,
        )

    def list_equity(self, session_id: int) -> list[EquityPoint]:
        live = self._get(session_id)
        statement = (
            select(EquityPoint)
            .where(EquityPoint.session_id == live.id)
            .order_by(EquityPoint.recorded_at.asc(), EquityPoint.id.asc())
        )
        return list(self._session.scalars(statement))

    def list_decisions(self, session_id: int) -> list[AgentDecision]:
        live = self._get(session_id)
        return self._agents.list_decisions(live.portfolio_id)

    def _transition(
        self,
        session_id: int,
        allowed: set[LiveSessionStatus],
        target: LiveSessionStatus,
    ) -> LiveSession:
        live = self._get(session_id)
        if live.status not in allowed:
            raise InvalidLiveSessionStateError(live.status, target)
        live.status = target
        if live.benchmark_session_id is not None:
            twin = self._session.get(LiveSession, live.benchmark_session_id)
            if twin is not None:
                twin.status = target
        self._session.commit()
        return live

    def _get(self, session_id: int) -> LiveSession:
        row = self._session.get(LiveSession, session_id)
        if row is None:
            raise UnknownLiveSessionError(session_id)
        return row
