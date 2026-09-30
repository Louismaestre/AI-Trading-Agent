import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.live_service import cycle_slot

PARIS = ZoneInfo("Europe/Paris")


def test_cycle_slot_floors_to_the_interval() -> None:
    now = datetime.datetime(2026, 9, 29, 10, 7, 30, tzinfo=PARIS)
    assert cycle_slot(now, 15) == datetime.datetime(2026, 9, 29, 10, 0, tzinfo=PARIS)


def test_cycle_slot_keeps_an_exact_boundary() -> None:
    now = datetime.datetime(2026, 9, 29, 10, 15, tzinfo=PARIS)
    assert cycle_slot(now, 15) == now.replace(second=0, microsecond=0)


def test_cycle_slot_rejects_a_naive_datetime() -> None:
    with pytest.raises(ValueError, match="Timezone-aware"):
        cycle_slot(datetime.datetime(2026, 9, 29, 10, 0), 15)
