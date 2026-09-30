import datetime
from zoneinfo import ZoneInfo

import pytest

from app.market_clock import (
    is_market_open,
    last_close,
    next_open,
    session_close,
    session_open,
    trading_days,
)

PARIS = ZoneInfo("Europe/Paris")


def _paris(*args: int) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=PARIS)


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (_paris(2026, 9, 29, 10, 0), True),  # Tuesday morning
        (_paris(2026, 9, 29, 9, 0), True),  # opening minute
        (_paris(2026, 9, 29, 17, 30), False),  # closing minute: session is over
        (_paris(2026, 9, 29, 18, 0), False),  # Tuesday evening
        (_paris(2026, 10, 3, 10, 0), False),  # Saturday
        (_paris(2026, 12, 25, 10, 0), False),  # Christmas
        (_paris(2026, 12, 24, 15, 0), False),  # Christmas Eve closes early
    ],
)
def test_is_market_open(moment: datetime.datetime, expected: bool) -> None:
    assert is_market_open(moment) is expected


def test_same_instant_in_utc_gives_same_answer() -> None:
    paris_ten = _paris(2026, 9, 29, 10, 0)

    assert is_market_open(paris_ten.astimezone(datetime.UTC)) is True


def test_next_open_after_friday_close_is_monday_morning() -> None:
    assert next_open(_paris(2026, 10, 2, 18, 0)) == _paris(2026, 10, 5, 9, 0)


def test_last_close_on_saturday_is_friday_evening() -> None:
    assert last_close(_paris(2026, 10, 3, 10, 0)) == _paris(2026, 10, 2, 17, 30)


def test_results_are_in_utc() -> None:
    assert next_open(_paris(2026, 10, 2, 18, 0)).tzinfo == datetime.UTC


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="Timezone-aware"):
        is_market_open(datetime.datetime(2026, 9, 29, 10, 0))


def test_session_open_on_a_trading_day() -> None:
    assert session_open(datetime.date(2026, 10, 5)) == _paris(2026, 10, 5, 9, 0)


def test_session_open_on_a_holiday_is_missing() -> None:
    assert session_open(datetime.date(2026, 12, 25)) is None


def test_session_close_on_a_trading_day() -> None:
    assert session_close(datetime.date(2026, 10, 5)) == _paris(2026, 10, 5, 17, 30)


def test_trading_days_skips_the_weekend() -> None:
    days = trading_days(datetime.date(2026, 10, 2), datetime.date(2026, 10, 5))

    assert days == [datetime.date(2026, 10, 2), datetime.date(2026, 10, 5)]
