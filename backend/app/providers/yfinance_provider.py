"""Downloads market data from Yahoo Finance. The only module that knows about yfinance."""

import datetime
from decimal import Decimal
from typing import cast

import pandas as pd
import yfinance as yf

from app.schemas.market import Bar


def fetch_daily_bars(ticker: str, start: datetime.date, end: datetime.date) -> list[Bar]:
    """Daily bars from `start` to `end`, both included. Empty list if Yahoo has no data."""
    yahoo_ticker = yf.Ticker(ticker)
    # yfinance excludes `end`, so ask for one more day.
    frame = yahoo_ticker.history(start=start, end=end + datetime.timedelta(days=1), interval="1d")
    return _to_bars(frame)


def _to_bars(frame: pd.DataFrame) -> list[Bar]:
    """Convert a yfinance DataFrame into Bars, skipping incomplete rows."""
    if frame.empty:
        return []
    bars = []
    for timestamp, row in frame.dropna().iterrows():
        bars.append(
            Bar(
                # yfinance always indexes by Timestamp; the pandas stubs can't know it.
                date=cast(pd.Timestamp, timestamp).date(),
                open=_to_decimal(row["Open"]),
                high=_to_decimal(row["High"]),
                low=_to_decimal(row["Low"]),
                close=_to_decimal(row["Close"]),
                volume=int(row["Volume"]),
            )
        )
    return bars


def _to_decimal(value: float) -> Decimal:
    """Round to the 4 decimals stored in database, going through str to avoid float noise."""
    return Decimal(str(round(value, 4)))
