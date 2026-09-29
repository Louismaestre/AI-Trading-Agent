"""Shapes shared by the indicator layer and, later, the trading agents."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


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
