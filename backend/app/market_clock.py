"""Euronext Paris trading hours and holidays, from the official exchange calendar."""

import datetime
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd

# Euronext Paris in the exchange-calendars naming (ISO 10383 market code).
EXCHANGE = "XPAR"


@lru_cache
def _calendar() -> xcals.ExchangeCalendar:
    # Building the calendar takes about a second, so it is done once.
    return xcals.get_calendar(EXCHANGE)


def is_market_open(now: datetime.datetime) -> bool:
    """True during a trading session (holidays and early closes included)."""
    return bool(_calendar().is_open_on_minute(_to_timestamp(now)))


def next_open(now: datetime.datetime) -> datetime.datetime:
    """Start of the next session strictly after `now`, in UTC."""
    return _to_datetime(_calendar().next_open(_to_timestamp(now)))


def last_close(now: datetime.datetime) -> datetime.datetime:
    """End of the latest session strictly before `now`, in UTC."""
    return _to_datetime(_calendar().previous_close(_to_timestamp(now)))


def ensure_aware(moment: datetime.datetime) -> datetime.datetime:
    """Reject naive datetimes: without a timezone, "10:00" is ambiguous."""
    if moment.tzinfo is None:
        raise ValueError(f"Timezone-aware datetime required, got naive {moment.isoformat()}")
    return moment


def _to_timestamp(now: datetime.datetime) -> pd.Timestamp:
    return pd.Timestamp(ensure_aware(now))


def _to_datetime(timestamp: pd.Timestamp) -> datetime.datetime:
    return timestamp.tz_convert(datetime.UTC).to_pydatetime()
