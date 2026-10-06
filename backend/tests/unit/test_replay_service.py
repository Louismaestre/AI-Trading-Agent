import datetime

from app.services.replay_service import decision_days, first_session_of_each_week


def test_first_session_of_each_week_keeps_the_opening_day() -> None:
    days = [
        datetime.date(2026, 9, 16),
        datetime.date(2026, 9, 17),
        datetime.date(2026, 9, 18),
        datetime.date(2026, 9, 21),
        datetime.date(2026, 9, 22),
    ]

    assert first_session_of_each_week(days) == [
        datetime.date(2026, 9, 16),
        datetime.date(2026, 9, 21),
    ]


def test_daily_frequency_keeps_every_session() -> None:
    days = [datetime.date(2026, 9, 16), datetime.date(2026, 9, 17)]
    assert decision_days(days, "DAILY") == days
    assert decision_days(days, "WEEKLY") == [datetime.date(2026, 9, 16)]
