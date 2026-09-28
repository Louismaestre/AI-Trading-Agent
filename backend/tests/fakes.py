"""Test doubles shared by several test files."""

import datetime
from decimal import Decimal

from app.schemas.market import Bar


class FakeProvider:
    """Replaces yfinance: one bar per weekday, close = day of month. Records every call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, datetime.date, datetime.date]] = []

    def __call__(self, ticker: str, start: datetime.date, end: datetime.date) -> list[Bar]:
        self.calls.append((ticker, start, end))
        days = (start + datetime.timedelta(days=n) for n in range((end - start).days + 1))
        return [make_bar(day) for day in days if day.weekday() < 5]


def make_bar(day: datetime.date) -> Bar:
    price = Decimal(day.day)
    return Bar(date=day, open=price, high=price, low=price, close=price, volume=1000)
