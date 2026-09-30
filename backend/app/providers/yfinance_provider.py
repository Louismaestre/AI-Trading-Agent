"""Downloads market data from Yahoo Finance.

Euronext quotes from Yahoo are delayed by about 15 minutes. Fundamentals live in
`fundamentals_provider` (same source, different tables).
"""

import datetime
from collections.abc import Iterator
from decimal import Decimal
from typing import Any, cast

import pandas as pd
import yfinance as yf

from app.schemas.market import Bar, IntradayBar


def fetch_daily_bars(ticker: str, start: datetime.date, end: datetime.date) -> list[Bar]:
    """Daily bars from `start` to `end`, both included. Empty list if Yahoo has no data."""
    yahoo_ticker = yf.Ticker(ticker)
    # yfinance excludes `end`, so ask for one more day.
    frame = yahoo_ticker.history(start=start, end=end + datetime.timedelta(days=1), interval="1d")
    return _to_bars(frame)


def fetch_intraday_bars(ticker: str, start: datetime.datetime) -> list[IntradayBar]:
    """5-minute bars from `start` to now. Yahoo only keeps the last 60 days."""
    frame = yf.Ticker(ticker).history(start=start, interval="5m")
    return _to_intraday_bars(frame)


def _to_bars(frame: pd.DataFrame) -> list[Bar]:
    """Convert a yfinance DataFrame into Bars, skipping incomplete rows."""
    return [Bar(date=timestamp.date(), **ohlcv) for timestamp, ohlcv in _rows(frame)]


def _to_intraday_bars(frame: pd.DataFrame) -> list[IntradayBar]:
    """Same as `_to_bars`, keeping the time of day, converted to UTC."""
    return [
        IntradayBar(timestamp=timestamp.tz_convert(datetime.UTC).to_pydatetime(), **ohlcv)
        for timestamp, ohlcv in _rows(frame)
    ]


def _rows(frame: pd.DataFrame) -> Iterator[tuple[pd.Timestamp, dict[str, Any]]]:
    """Complete rows of a yfinance DataFrame as (timestamp, OHLCV fields)."""
    if frame.empty:
        return
    for timestamp, row in frame.dropna().iterrows():
        # yfinance always indexes by Timestamp; the pandas stubs can't know it.
        yield (
            cast(pd.Timestamp, timestamp),
            {
                "open": _to_decimal(row["Open"]),
                "high": _to_decimal(row["High"]),
                "low": _to_decimal(row["Low"]),
                "close": _to_decimal(row["Close"]),
                "volume": int(row["Volume"]),
            },
        )


def _to_decimal(value: float) -> Decimal:
    """Round to the 4 decimals stored in database, going through str to avoid float noise."""
    return Decimal(str(round(value, 4)))
