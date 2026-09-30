"""API shapes for live trading sessions."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models import LiveSessionKind, LiveSessionStatus
from app.services.live_service import DEFAULT_INTERVAL_MINUTES
from app.services.portfolio_service import DEFAULT_CAPITAL


class CreateLiveSessionRequest(BaseModel):
    name: str = Field(default="Live", min_length=1, max_length=200)
    initial_capital: Decimal = Field(default=DEFAULT_CAPITAL, gt=0)
    interval_minutes: int = Field(default=DEFAULT_INTERVAL_MINUTES, ge=1, le=240)


class LiveSessionResponse(BaseModel):
    id: int
    portfolio_id: int
    kind: LiveSessionKind
    status: LiveSessionStatus
    interval_minutes: int
    started_at: datetime.datetime
    last_slot: datetime.datetime | None
    next_cycle_at: datetime.datetime | None
    total_value: Decimal
    cash: Decimal
    benchmark_session_id: int | None


class EquityPointResponse(BaseModel):
    id: int
    recorded_at: datetime.datetime
    total_value: Decimal
    cash: Decimal
