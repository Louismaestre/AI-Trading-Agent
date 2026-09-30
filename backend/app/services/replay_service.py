"""Replay the same agents over past sessions. Only the clock changes vs live."""

import datetime
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.llm import StructuredLLM
from app.market_clock import session_close, session_open, trading_days
from app.models import EquityPoint, Replay, ReplayStatus
from app.services.agent_service import AgentService
from app.services.portfolio_service import PortfolioService

WEEKLY = "WEEKLY"


class UnknownReplayError(LookupError):
    """No replay exists for this id."""


class ReplayStartsTooEarlyError(ValueError):
    """The replay starts on or before the model knowledge cutoff."""


class EmptyReplayRangeError(ValueError):
    """No Euronext session falls in the requested period."""


def first_session_of_each_week(days: Sequence[datetime.date]) -> list[datetime.date]:
    """One decision day per ISO week: the first session in that week."""
    chosen: list[datetime.date] = []
    seen: set[tuple[int, int]] = set()
    for day in days:
        iso = day.isocalendar()
        key = (iso.year, iso.week)
        if key in seen:
            continue
        seen.add(key)
        chosen.append(day)
    return chosen


class ReplayService:
    def __init__(
        self,
        session: Session,
        llm: StructuredLLM | None = None,
        agents: AgentService | None = None,
        knowledge_cutoff: datetime.date | None = None,
    ) -> None:
        self._session = session
        self._portfolios = PortfolioService(session)
        self._agents = agents or AgentService(session, llm=llm)
        self._cutoff = knowledge_cutoff or get_settings().llm_knowledge_cutoff

    def create(
        self,
        portfolio_id: int,
        start: datetime.date,
        end: datetime.date,
        decision_frequency: str = WEEKLY,
    ) -> Replay:
        self._portfolios.get(portfolio_id)
        if start <= self._cutoff:
            raise ReplayStartsTooEarlyError(
                f"Replay start {start.isoformat()} must be after {self._cutoff.isoformat()}"
            )
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        days = trading_days(start, end)
        if not days:
            raise EmptyReplayRangeError(f"{start.isoformat()} .. {end.isoformat()}")
        row = Replay(
            portfolio_id=portfolio_id,
            start_date=start,
            end_date=end,
            decision_frequency=decision_frequency,
            status=ReplayStatus.PENDING,
            days_done=0,
            days_total=len(days),
        )
        self._session.add(row)
        self._session.commit()
        return row

    def run(self, replay_id: int, tickers: Sequence[str] | None = None) -> Replay:
        replay = self.get(replay_id)
        days = trading_days(replay.start_date, replay.end_date)
        decisions = set(first_session_of_each_week(days))
        replay.status = ReplayStatus.RUNNING
        self._session.commit()
        try:
            for index, day in enumerate(days, start=1):
                self._step(replay, day, day in decisions, tickers)
                replay.days_done = index
                replay.current_date = day
                self._session.commit()
        except Exception:
            replay.status = ReplayStatus.FAILED
            self._session.commit()
            raise
        replay.status = ReplayStatus.DONE
        self._session.commit()
        return replay

    def get(self, replay_id: int) -> Replay:
        row = self._session.get(Replay, replay_id)
        if row is None:
            raise UnknownReplayError(replay_id)
        return row

    def list_equity(self, replay_id: int) -> list[EquityPoint]:
        self.get(replay_id)
        statement = (
            select(EquityPoint)
            .where(EquityPoint.replay_id == replay_id)
            .order_by(EquityPoint.recorded_at.asc(), EquityPoint.id.asc())
        )
        return list(self._session.scalars(statement))

    def _step(
        self,
        replay: Replay,
        day: datetime.date,
        decide: bool,
        tickers: Sequence[str] | None,
    ) -> None:
        opened = session_open(day)
        closed = session_close(day)
        if opened is None or closed is None:
            return
        self._portfolios.execute_pending_orders(replay.portfolio_id, opened)
        snapshot = self._portfolios.snapshot(replay.portfolio_id, closed)
        self._session.add(
            EquityPoint(
                replay_id=replay.id,
                recorded_at=closed,
                total_value=snapshot.total_value,
                cash=snapshot.portfolio.cash,
            )
        )
        if decide:
            self._agents.run_agents(replay.portfolio_id, day, tickers=tickers)
