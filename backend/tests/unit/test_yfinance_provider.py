import datetime
from decimal import Decimal

import pandas as pd

from app.providers.yfinance_provider import _to_bars


def _frame(rows: list[dict[str, float]], dates: list[str]) -> pd.DataFrame:
    """Fake yfinance output: Timestamp index in Paris time, capitalized columns."""
    index = pd.DatetimeIndex(pd.to_datetime(dates)).tz_localize("Europe/Paris")
    return pd.DataFrame(rows, index=index)


def _row(close: float = 610.25) -> dict[str, float]:
    return {
        "Open": 600.1,
        "High": 612.5,
        "Low": 598.0,
        "Close": close,
        "Volume": 450000.0,
        "Dividends": 0.0,
        "Stock Splits": 0.0,
    }


def test_converts_each_row_into_a_bar() -> None:
    bars = _to_bars(_frame([_row(), _row()], ["2026-09-01", "2026-09-02"]))

    assert [bar.date for bar in bars] == [datetime.date(2026, 9, 1), datetime.date(2026, 9, 2)]
    assert bars[0].open == Decimal("600.1")
    assert bars[0].close == Decimal("610.25")
    assert bars[0].volume == 450000


def test_prices_are_rounded_to_four_decimals() -> None:
    bars = _to_bars(_frame([_row(close=612.4999847412109)], ["2026-09-01"]))

    assert bars[0].close == Decimal("612.5")


def test_rows_with_missing_values_are_skipped() -> None:
    bars = _to_bars(_frame([_row(), _row(close=float("nan"))], ["2026-09-01", "2026-09-02"]))

    assert [bar.date for bar in bars] == [datetime.date(2026, 9, 1)]


def test_empty_frame_gives_no_bars() -> None:
    assert _to_bars(pd.DataFrame()) == []
