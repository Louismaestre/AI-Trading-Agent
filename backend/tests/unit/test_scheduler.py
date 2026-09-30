import datetime
from zoneinfo import ZoneInfo

from app.scheduler import close_mark_at, next_trigger, release, try_acquire

PARIS = ZoneInfo("Europe/Paris")


def _paris(*args: int) -> datetime.datetime:
    return datetime.datetime(*args, tzinfo=PARIS)


def test_next_trigger_during_the_session_is_the_next_slot() -> None:
    assert next_trigger(_paris(2026, 9, 29, 10, 7), 15) == _paris(2026, 9, 29, 10, 15)


def test_next_trigger_after_the_close_skips_the_night() -> None:
    assert next_trigger(_paris(2026, 9, 29, 18, 0), 15) == _paris(2026, 9, 30, 9, 0)


def test_next_trigger_on_saturday_skips_the_weekend() -> None:
    assert next_trigger(_paris(2026, 10, 3, 10, 0), 15) == _paris(2026, 10, 5, 9, 0)


def test_next_trigger_on_christmas_skips_the_holiday() -> None:
    assert next_trigger(_paris(2026, 12, 25, 10, 0), 15) == _paris(2026, 12, 28, 9, 0)


def test_next_trigger_near_the_close_jumps_to_the_next_open() -> None:
    # 17:30 is already closed, so the 17:15 slot's successor is not tradable.
    assert next_trigger(_paris(2026, 9, 29, 17, 20), 15) == _paris(2026, 9, 30, 9, 0)


def test_close_mark_shortly_after_the_bell() -> None:
    assert close_mark_at(_paris(2026, 9, 29, 17, 40)) == _paris(2026, 9, 29, 17, 30)


def test_close_mark_is_skipped_while_the_market_is_open() -> None:
    assert close_mark_at(_paris(2026, 9, 29, 10, 0)) is None


def test_close_mark_is_skipped_the_next_morning() -> None:
    assert close_mark_at(_paris(2026, 10, 3, 10, 0)) is None


def test_a_session_cannot_run_two_cycles_at_once() -> None:
    assert try_acquire(42) is True
    assert try_acquire(42) is False
    release(42)
    assert try_acquire(42) is True
    release(42)
