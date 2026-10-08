"""Sharpe confidence intervals and paired tests against a replay's twins."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Replay, ReplayKind, ReplayStatus
from app.services.metrics import daily_returns, total_return
from app.services.replay_service import ReplayService, UnknownReplayError
from app.services.statistics import (
    RepeatSummary,
    SharpeComparison,
    SharpeInterval,
    bootstrap_sharpe_ci,
    sharpe_difference,
    summarize_repeats,
)


@dataclass(frozen=True)
class ReplaySignificance:
    replay_id: int
    batch_id: str | None
    repeat_index: int | None
    sharpe_ci: SharpeInterval | None
    vs_hold: SharpeComparison | None
    vs_sma: SharpeComparison | None
    vs_random: SharpeComparison | None
    batch: RepeatSummary | None
    batch_replay_ids: list[int]


class SignificanceService:
    def __init__(self, session: Session, risk_free_rate: Decimal | None = None) -> None:
        self._session = session
        self._replays = ReplayService(session, risk_free_rate=risk_free_rate)
        settings = get_settings()
        self._risk_free = risk_free_rate if risk_free_rate is not None else settings.risk_free_rate

    def for_replay(self, replay_id: int) -> ReplaySignificance:
        replay = self._replays.get(replay_id)
        returns = self._returns(replay_id)
        siblings = self.list_batch(replay.batch_id) if replay.batch_id else []
        finished = [
            total_return([point.total_value for point in self._replays.list_equity(row.id)])
            for row in siblings
            if row.status is ReplayStatus.DONE
        ]
        return ReplaySignificance(
            replay_id=replay.id,
            batch_id=replay.batch_id,
            repeat_index=replay.repeat_index,
            sharpe_ci=bootstrap_sharpe_ci(returns, self._risk_free, seed=replay.id),
            vs_hold=self._versus(returns, replay.benchmark_replay_id, replay.id),
            vs_sma=self._versus(returns, replay.sma_replay_id, replay.id + 1),
            vs_random=self._versus(returns, replay.random_replay_id, replay.id + 2),
            batch=summarize_repeats(finished),
            batch_replay_ids=[row.id for row in siblings],
        )

    def list_batch(self, batch_id: str) -> list[Replay]:
        statement = (
            select(Replay)
            .where(Replay.batch_id == batch_id, Replay.kind == ReplayKind.AGENTS)
            .order_by(Replay.repeat_index.asc(), Replay.id.asc())
        )
        return list(self._session.scalars(statement))

    def _versus(
        self,
        strategy: list[Decimal],
        baseline_id: int | None,
        seed: int,
    ) -> SharpeComparison | None:
        if baseline_id is None:
            return None
        try:
            baseline = self._returns(baseline_id)
        except UnknownReplayError:
            return None
        return sharpe_difference(strategy, baseline, self._risk_free, seed=seed)

    def _returns(self, replay_id: int) -> list[Decimal]:
        return daily_returns([point.total_value for point in self._replays.list_equity(replay_id)])
