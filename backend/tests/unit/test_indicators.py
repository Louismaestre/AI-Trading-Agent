import datetime
from decimal import Decimal

import pandas as pd
import pytest

from app.indicators import atr, ema, rsi, sma, technical_summary, trailing_return
from app.schemas.market import Bar


def _closes(*values: float) -> pd.Series:
    return pd.Series(values, dtype="float64")


def _bars(*closes: float) -> list[Bar]:
    start = datetime.date(2026, 1, 2)
    return [
        Bar(
            date=start + datetime.timedelta(days=index),
            open=Decimal(str(close)),
            high=Decimal(str(close)),
            low=Decimal(str(close)),
            close=Decimal(str(close)),
            volume=1000,
        )
        for index, close in enumerate(closes)
    ]


def test_sma_of_five_values_is_the_hand_computed_mean() -> None:
    # (1 + 2 + 3 + 4 + 5) / 5 = 3
    result = sma(_closes(1, 2, 3, 4, 5), window=5)
    assert result.iloc[-1] == pytest.approx(3.0)
    assert pd.isna(result.iloc[3])


def test_rsi_of_a_strictly_rising_series_is_100() -> None:
    # 15 closes → 14 positive changes, enough to fill a 14-period RSI.
    result = rsi(_closes(*range(1, 16)))
    assert result.iloc[-1] == pytest.approx(100.0)


def test_rsi_of_a_strictly_falling_series_is_0() -> None:
    result = rsi(_closes(*range(15, 0, -1)))
    assert result.iloc[-1] == pytest.approx(0.0)


def test_later_prices_do_not_change_earlier_indicators() -> None:
    first = _closes(10, 11, 12, 13, 14)
    second = _closes(10, 11, 12, 13, 99)
    for index in (2, 3):
        assert sma(first, 3).iloc[index] == sma(second, 3).iloc[index]
        assert ema(first, 3).iloc[index] == ema(second, 3).iloc[index]
        assert trailing_return(first, 2).iloc[index] == trailing_return(second, 2).iloc[index]


def test_ema_span_2_matches_the_recursive_formula() -> None:
    # alpha = 2 / (2 + 1) = 2/3; first seed is the first close.
    # ema1 = 2/3 * 2 + 1/3 * 1 = 5/3
    result = ema(_closes(1, 2), window=2)
    assert result.iloc[-1] == pytest.approx(5 / 3)


def test_five_day_return_is_close_over_close_five_bars_ago() -> None:
    # 110 / 100 - 1 = 0.10
    result = trailing_return(_closes(100, 101, 102, 103, 104, 110), period=5)
    assert result.iloc[-1] == pytest.approx(0.10)


def test_atr_of_a_flat_range_is_the_high_low_spread() -> None:
    bars = [
        Bar(
            date=datetime.date(2026, 1, 2) + datetime.timedelta(days=index),
            open=Decimal("11"),
            high=Decimal("12"),
            low=Decimal("10"),
            close=Decimal("11"),
            volume=1000,
        )
        for index in range(15)
    ]
    assert atr(bars) == Decimal("2")


def test_atr_needs_window_plus_one_bars() -> None:
    assert atr(_bars(*range(14))) is None


def test_technical_summary_needs_at_least_one_bar() -> None:
    with pytest.raises(ValueError, match="at least one bar"):
        technical_summary([])


def test_technical_summary_reports_price_above_sma_20() -> None:
    # 19 days at 100, then 120: SMA 20 = (19 * 100 + 120) / 20 = 101
    closes = [100.0] * 19 + [120.0]
    summary = technical_summary(_bars(*closes))
    assert summary.last_close == Decimal("120")
    assert summary.sma_20 == Decimal("101")
    assert summary.sma_50 is None
    assert "price above SMA 20" in summary.signals
    assert "price above SMA 50" not in summary.signals


def test_technical_summary_flags_oversold_rsi() -> None:
    summary = technical_summary(_bars(*range(20, 0, -1)))
    assert summary.rsi_14 == Decimal("0")
    assert "RSI oversold" in summary.signals
