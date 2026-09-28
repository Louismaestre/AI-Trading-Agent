"""Market data shapes shared by the providers, services and API."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

# Length of an intraday bar: its close is only known once this time has elapsed.
INTRADAY_INTERVAL = datetime.timedelta(minutes=5)


class Ohlcv(BaseModel):
    """Open, high, low, close prices and traded volume over a period."""

    # Allows model_validate(row) on a database row.
    model_config = ConfigDict(from_attributes=True)

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int


class Bar(Ohlcv):
    """One trading day."""

    date: datetime.date


class IntradayBar(Ohlcv):
    """One 5-minute bar starting at `timestamp` (UTC)."""

    timestamp: datetime.datetime


class MarketStatus(BaseModel):
    """Euronext Paris state at `now`; all times in UTC."""

    now: datetime.datetime
    is_open: bool
    next_open: datetime.datetime
    last_close: datetime.datetime
