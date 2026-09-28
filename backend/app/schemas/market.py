"""Market data shapes shared by the providers, services and API."""

import datetime
from decimal import Decimal

from pydantic import BaseModel


class Bar(BaseModel):
    """One OHLCV bar: open, high, low, close prices and traded volume over a period."""

    date: datetime.date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
