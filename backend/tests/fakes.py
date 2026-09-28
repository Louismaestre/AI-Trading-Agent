"""Test doubles shared by several test files."""

import datetime
from decimal import Decimal

from app.schemas.market import INTRADAY_INTERVAL, Bar, IntradayBar


class FakeProvider:
    """Replaces yfinance: one bar per weekday, close = day of month. Records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime.date, datetime.date]] = []

    def __call__(self, ticker: str, start: datetime.date, end: datetime.date) -> list[Bar]:
        self.calls.append((ticker, start, end))
        days = (start + datetime.timedelta(days=n) for n in range((end - start).days + 1))
        return [make_bar(day) for day in days if day.weekday() < 5]


class FakeIntradayProvider:
    """Replaces yfinance intraday: serves `count` 5-minute bars from `first`, close = minute."""

    def __init__(self, first: datetime.datetime, count: int) -> None:
        self.bars = [make_intraday_bar(first + n * INTRADAY_INTERVAL) for n in range(count)]
        self.calls: list[tuple[str, datetime.datetime]] = []

    def __call__(self, ticker: str, start: datetime.datetime) -> list[IntradayBar]:
        self.calls.append((ticker, start))
        return [bar for bar in self.bars if bar.timestamp >= start]


def make_bar(day: datetime.date) -> Bar:
    price = Decimal(day.day)
    return Bar(date=day, open=price, high=price, low=price, close=price, volume=1000)


def make_intraday_bar(timestamp: datetime.datetime) -> IntradayBar:
    price = Decimal(timestamp.minute)
    return IntradayBar(
        timestamp=timestamp, open=price, high=price, low=price, close=price, volume=100
    )
