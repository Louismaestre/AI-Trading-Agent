"""Shapes shared by the indicator layer and, later, the trading agents."""

import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Action = Literal["BUY", "SELL", "HOLD"]


class TechnicalSummary(BaseModel):
    """Readable snapshot of a price series, meant to be given to an LLM."""

    last_date: datetime.date
    last_close: Decimal
    sma_20: Decimal | None = None
    sma_50: Decimal | None = None
    ema_12: Decimal | None = None
    rsi_14: Decimal | None = None
    macd: Decimal | None = None
    macd_signal: Decimal | None = None
    macd_histogram: Decimal | None = None
    return_5d: Decimal | None = None
    return_20d: Decimal | None = None
    volatility_20d: Decimal | None = None
    signals: list[str] = Field(default_factory=list)


class AnalystDecision(BaseModel):
    action: Action
    confidence: float = Field(ge=0, le=1)
    target_weight: float = Field(ge=0, le=1)
    rationale: str


Stance = Literal["BULLISH", "BEARISH", "NEUTRAL"]


class AnalystReport(BaseModel):
    """Opinion from a specialist analyst. It does not place an order."""

    stance: Stance
    confidence: float = Field(ge=0, le=1)
    rationale: str


class PriorYearContext(BaseModel):
    """Completed calendar year before `as_of`. None of these figures leak the current year."""

    year: int
    ticker: str
    ticker_return: Decimal | None
    index_ticker: str
    index_return: Decimal | None


class QuantityProposal(BaseModel):
    """How many shares the buyer or seller wants to trade now."""

    quantity: int = Field(ge=0)
    rationale: str


class AgentDecisionResponse(BaseModel):
    id: int
    ticker: str
    as_of: datetime.date
    created_at: datetime.datetime
    action: Action
    confidence: float
    target_weight: float
    rationale: str
    llm_model: str
    duration_ms: int
    order_id: int | None
