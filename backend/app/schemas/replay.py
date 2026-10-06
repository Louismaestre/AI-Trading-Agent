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


class ReplayMetricsResponse(BaseModel):
    total_return: Decimal
    max_drawdown: Decimal
    order_count: int
    fees_paid: Decimal
    hit_rate: Decimal | None


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
    metrics: ReplayMetricsResponse | None = None
