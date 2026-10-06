import datetime
from decimal import Decimal

import pandas as pd

from app.providers.fundamentals_provider import statements_from_frames


def test_maps_yfinance_rows_onto_periods() -> None:
    columns = [pd.Timestamp("2026-06-30"), pd.Timestamp("2026-03-31")]
    income = pd.DataFrame(
        [[1200.0, 1000.0], [150.0, 80.0], [3.5, 2.0]],
        index=["Total Revenue", "Net Income", "Diluted EPS"],
        columns=columns,
    )
    balance = pd.DataFrame(
        [[400.0, 350.0], [800.0, 700.0]],
        index=["Total Debt", "Stockholders Equity"],
        columns=columns,
    )
    cashflow = pd.DataFrame([[90.0, 70.0]], index=["Operating Cash Flow"], columns=columns)

    periods = statements_from_frames(income, balance, cashflow)

    assert [row.period_end for row in periods] == [
        datetime.date(2026, 6, 30),
        datetime.date(2026, 3, 31),
    ]
    assert periods[0].revenue == Decimal("1200.0000")
    assert periods[0].net_income == Decimal("150.0000")
    assert periods[0].diluted_eps == Decimal("3.5000")
    assert periods[0].total_debt == Decimal("400.0000")
    assert periods[0].total_equity == Decimal("800.0000")
    assert periods[0].operating_cash_flow == Decimal("90.0000")


def test_empty_frames_give_no_periods() -> None:
    empty = pd.DataFrame()
    assert statements_from_frames(empty, empty, empty) == []
