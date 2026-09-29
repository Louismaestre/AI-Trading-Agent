"""One live cycle: refresh prices, run agents if the market is open, store equity."""

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.llm import StructuredLLM
from app.market_clock import ensure_aware, is_market_open
from app.models import EquityPoint, LiveSession, LiveSessionStatus
from app.services.agent_service import AgentService
from app.services.market_data_service import MarketDataService
from app.services.portfolio_service import PortfolioService

DEFAULT_INTERVAL_MINUTES = 15
INTRADAY_LOOKBACK = datetime.timedelta(days=2)


class UnknownLiveSessionError(LookupError):
    """No live session exists for this id."""


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

    def create(
        self, portfolio_id: int, interval_minutes: int = DEFAULT_INTERVAL_MINUTES
    ) -> LiveSession:
        self._portfolios.get(portfolio_id)
        row = LiveSession(
            portfolio_id=portfolio_id,
            interval_minutes=interval_minutes,
            status=LiveSessionStatus.RUNNING,
            started_at=datetime.datetime.now(datetime.UTC),
        )
        self._session.add(row)
        self._session.commit()
        return row

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

    def _get(self, session_id: int) -> LiveSession:
        row = self._session.get(LiveSession, session_id)
        if row is None:
            raise UnknownLiveSessionError(session_id)
        return row
