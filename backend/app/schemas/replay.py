"""API shapes for historical replays."""

import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.models import ReplayKind, ReplayStatus
from app.services.portfolio_service import DEFAULT_CAPITAL

DecisionFrequency = Literal["DAILY", "WEEKLY"]


class CreateReplayRequest(BaseModel):
    name: str = Field(default="Replay", min_length=1, max_length=200)
    initial_capital: Decimal = Field(default=DEFAULT_CAPITAL, gt=0)
    start: datetime.date
    end: datetime.date
    decision_frequency: DecisionFrequency = "DAILY"


class CalibrationBucketResponse(BaseModel):
    low: Decimal
    high: Decimal
    count: int
    hit_rate: Decimal | None
    mean_confidence: Decimal | None


class ReplayMetricsResponse(BaseModel):
    total_return: Decimal
    max_drawdown: Decimal
    order_count: int
    fees_paid: Decimal
    hit_rate: Decimal | None
    volatility: Decimal | None
    sharpe: Decimal | None
    sortino: Decimal | None
    calibration: list[CalibrationBucketResponse] | None = None


class ReplayResponse(BaseModel):
    id: int
    portfolio_id: int
    kind: ReplayKind
    status: ReplayStatus
    start_date: datetime.date
    end_date: datetime.date
    days_done: int
    days_total: int
    current_date: datetime.date | None
    decision_frequency: str
    error_message: str | None = None
    benchmark_replay_id: int | None
    sma_replay_id: int | None
    random_replay_id: int | None
    experiment_id: str | None = None
    batch_id: str | None = None
    repeat_index: int | None = None
    metrics: ReplayMetricsResponse | None = None


class ExperimentRunResponse(BaseModel):
    batch_id: str
    repeats: list[ReplayResponse]


class SharpeIntervalResponse(BaseModel):
    low: Decimal
    high: Decimal


class SharpeComparisonResponse(BaseModel):
    p_value: Decimal
    significant: bool


class RepeatSummaryResponse(BaseModel):
    count: int
    mean_return: Decimal
    std_return: Decimal | None
    replay_ids: list[int]


class ReplaySignificanceResponse(BaseModel):
    replay_id: int
    batch_id: str | None
    repeat_index: int | None
    sharpe_ci: SharpeIntervalResponse | None
    vs_hold: SharpeComparisonResponse | None
    vs_sma: SharpeComparisonResponse | None
    vs_random: SharpeComparisonResponse | None
    batch: RepeatSummaryResponse | None
