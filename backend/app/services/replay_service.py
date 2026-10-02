"""Replay the same agents over past sessions. Only the clock changes vs live."""

import datetime
import logging
from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.indicators import SMA_SLOW
from app.llm import StructuredLLM
from app.market_clock import session_close, session_open, trading_days
from app.models import AgentDecision, EquityPoint, Replay, ReplayKind, ReplayStatus
from app.services.agent_service import AgentService
from app.services.fees import money
from app.services.live_service import LiveService
from app.services.market_data_service import MarketDataService
from app.services.metrics import (
    ReplayMetrics,
    hit_rate,
    max_drawdown,
    prediction_correct,
    total_return,
)
from app.services.portfolio_service import DEFAULT_CAPITAL, PortfolioService
from app.universe import tradable_tickers

DAILY = "DAILY"
WEEKLY = "WEEKLY"
FREQUENCIES = (DAILY, WEEKLY)
_ERROR_LIMIT = 2000
logger = logging.getLogger(__name__)


class UnknownReplayError(LookupError):
    """No replay exists for this id."""


class ReplayStartsTooEarlyError(ValueError):
    """The replay starts on or before the model knowledge cutoff."""


class EmptyReplayRangeError(ValueError):
    """No Euronext session falls in the requested period."""


class MissingReplayPricesError(ValueError):
    """The stored daily bars do not cover the replay start."""


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


def fail_interrupted_replays(session: Session) -> int:
    """Mark jobs left RUNNING after a process restart so the UI does not wait forever."""
    rows = list(session.scalars(select(Replay).where(Replay.status == ReplayStatus.RUNNING)))
    for row in rows:
        row.status = ReplayStatus.FAILED
        row.error_message = "Interrupted when the API restarted."
    if rows:
        session.commit()
    return len(rows)


def decision_days(days: Sequence[datetime.date], frequency: str) -> list[datetime.date]:
    """Which sessions trigger `run_agents`. Unknown frequencies are rejected."""
    if frequency == DAILY:
        return list(days)
    if frequency == WEEKLY:
        return first_session_of_each_week(days)
    raise ValueError(f"Unknown decision frequency: {frequency}")


class ReplayService:
    def __init__(
        self,
        session: Session,
        llm: StructuredLLM | None = None,
        agents: AgentService | None = None,
        knowledge_cutoff: datetime.date | None = None,
        lookback_sessions: int | None = None,
    ) -> None:
        self._session = session
        self._portfolios = PortfolioService(session)
        self._agents = agents or AgentService(session, llm=llm)
        self._market = MarketDataService(session)
        self._cutoff = knowledge_cutoff or get_settings().llm_knowledge_cutoff
        self._lookback_sessions = SMA_SLOW if lookback_sessions is None else lookback_sessions

    def create(
        self,
        portfolio_id: int,
        start: datetime.date,
        end: datetime.date,
        decision_frequency: str = WEEKLY,
        tickers: Sequence[str] | None = None,
    ) -> Replay:
        source = self._portfolios.get(portfolio_id)
        if start <= self._cutoff:
            raise ReplayStartsTooEarlyError(
                f"Replay start {start.isoformat()} must be after {self._cutoff.isoformat()}"
            )
        if decision_frequency not in FREQUENCIES:
            raise ValueError(f"Unknown decision frequency: {decision_frequency}")
        if end < start:
            raise ValueError("end_date must be on or after start_date")
        days = trading_days(start, end)
        if not days:
            raise EmptyReplayRangeError(
                f"No Euronext session between {start.isoformat()} and {end.isoformat()} "
                "(weekend or holiday). Pick a range that includes a trading day."
            )
        universe = list(tickers or tradable_tickers())
        self._require_prices(start, universe)
        hold_book = self._portfolios.create(f"{source.name} (buy and hold)", source.initial_capital)
        opened = session_open(days[0])
        if opened is not None:
            LiveService(self._session).open_equal_weight(hold_book.id, opened, universe)
        hold = self._new_replay(
            hold_book.id, start, end, decision_frequency, len(days), ReplayKind.BUY_AND_HOLD
        )
        agents = self._new_replay(
            portfolio_id, start, end, decision_frequency, len(days), ReplayKind.AGENTS, hold.id
        )
        self._session.commit()
        return agents

    def start(
        self,
        name: str = "Replay",
        initial_capital: Decimal = DEFAULT_CAPITAL,
        start: datetime.date | None = None,
        end: datetime.date | None = None,
        tickers: Sequence[str] | None = None,
        decision_frequency: str = WEEKLY,
    ) -> Replay:
        """Create a portfolio and open the agent replay plus its buy-and-hold twin."""
        if start is None or end is None:
            raise ValueError("start and end are required")
        portfolio = self._portfolios.create(name, initial_capital)
        return self.create(
            portfolio.id, start, end, decision_frequency=decision_frequency, tickers=tickers
        )

    def run(self, replay_id: int, tickers: Sequence[str] | None = None) -> Replay:
        replay = self.get(replay_id)
        self._run_loop(replay, tickers)
        if replay.benchmark_replay_id is not None:
            self._run_loop(self.get(replay.benchmark_replay_id), tickers)
        return replay

    def metrics(self, replay_id: int) -> ReplayMetrics:
        replay = self.get(replay_id)
        values = [point.total_value for point in self.list_equity(replay_id)]
        orders = self._portfolios.list_orders(replay.portfolio_id)
        fees = money(
            sum((order.fees for order in orders if order.fees is not None), start=Decimal("0"))
        )
        return ReplayMetrics(
            total_return=total_return(values),
            max_drawdown=max_drawdown(values),
            order_count=len(orders),
            fees_paid=fees,
            hit_rate=self._hit_rate(replay),
        )

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

    def list_decisions(self, replay_id: int) -> list[AgentDecision]:
        replay = self.get(replay_id)
        return self._agents.list_decisions(replay.portfolio_id)

    def _new_replay(
        self,
        portfolio_id: int,
        start: datetime.date,
        end: datetime.date,
        decision_frequency: str,
        days_total: int,
        kind: ReplayKind,
        benchmark_replay_id: int | None = None,
    ) -> Replay:
        row = Replay(
            portfolio_id=portfolio_id,
            start_date=start,
            end_date=end,
            decision_frequency=decision_frequency,
            status=ReplayStatus.PENDING,
            days_done=0,
            days_total=days_total,
            kind=kind,
            benchmark_replay_id=benchmark_replay_id,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def _run_loop(self, replay: Replay, tickers: Sequence[str] | None) -> None:
        days = trading_days(replay.start_date, replay.end_date)
        decide_on = (
            set(decision_days(days, replay.decision_frequency))
            if replay.kind is ReplayKind.AGENTS
            else set()
        )
        replay.status = ReplayStatus.RUNNING
        replay.error_message = None
        self._session.commit()
        try:
            for index, day in enumerate(days, start=1):
                self._step(replay, day, day in decide_on, tickers)
                replay.days_done = index
                replay.current_date = day
                self._session.commit()
        except Exception as exc:
            replay.status = ReplayStatus.FAILED
            replay.error_message = _format_error(exc)
            self._session.commit()
            logger.exception("Replay %s failed on %s", replay.id, replay.current_date)
            raise
        replay.status = ReplayStatus.DONE
        self._session.commit()

    def _require_prices(self, start: datetime.date, tickers: Sequence[str]) -> None:
        first, last = self._market.daily_span(tickers)
        if first is None or last is None or last < start:
            raise MissingReplayPricesError(
                f"No daily prices covering {start.isoformat()}. "
                "POST /api/v1/instruments/sync-prices first (it backfills earlier days)."
            )
        if first > start:
            raise MissingReplayPricesError(
                f"Daily prices start on {first.isoformat()}, after the replay start "
                f"{start.isoformat()}. Sync a longer history or start later."
            )
        needed = self._lookback_start(start)
        if needed is not None and first > needed:
            raise MissingReplayPricesError(
                f"Need about {self._lookback_sessions} sessions before {start.isoformat()} "
                f"for SMA/RSI/MACD (history starts {first.isoformat()}). "
                "POST /api/v1/instruments/sync-prices first."
            )

    def _lookback_start(self, start: datetime.date) -> datetime.date | None:
        if self._lookback_sessions < 1:
            return None
        prior = trading_days(
            start - datetime.timedelta(days=180), start - datetime.timedelta(days=1)
        )
        if len(prior) < self._lookback_sessions:
            return prior[0] if prior else None
        return prior[-self._lookback_sessions]

    def _hit_rate(self, replay: Replay) -> Decimal | None:
        if replay.kind is not ReplayKind.AGENTS:
            return None
        days = trading_days(replay.start_date, replay.end_date)
        outcomes: list[bool] = []
        for record in self._agents.list_decisions(replay.portfolio_id):
            following = next((day for day in days if day > record.as_of), None)
            if following is None:
                continue
            close_at = self._close_on(record.instrument.ticker, record.as_of)
            close_after = self._close_on(record.instrument.ticker, following)
            if close_at is None or close_after is None:
                continue
            scored = prediction_correct(record.action, close_at, close_after)
            if scored is not None:
                outcomes.append(scored)
        return hit_rate(outcomes)

    def _close_on(self, ticker: str, day: datetime.date) -> Decimal | None:
        bars = self._market.get_history(ticker, day, limit=1)
        if not bars or bars[-1].date != day:
            return None
        return bars[-1].close

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


def _format_error(exc: BaseException) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if len(text) <= _ERROR_LIMIT:
        return text
    return text[: _ERROR_LIMIT - 1] + "…"
