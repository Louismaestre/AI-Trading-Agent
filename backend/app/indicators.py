"""Causal technical indicators. Each value uses only prices up to that bar."""

from collections.abc import Sequence
from decimal import Decimal
from itertools import pairwise

import pandas as pd

from app.schemas.agents import TechnicalSummary
from app.schemas.market import Bar

SMA_FAST = 20
SMA_SLOW = 50
EMA_FAST = 12
RSI_WINDOW = 14
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RETURN_SHORT = 5
RETURN_LONG = 20
VOL_WINDOW = 20
ATR_WINDOW = 14

RSI_OVERSOLD = Decimal("30")
RSI_OVERBOUGHT = Decimal("70")


def sma(closes: pd.Series, window: int) -> pd.Series:
    """Simple moving average; NaN until `window` closes are available."""
    return closes.rolling(window=window, min_periods=window).mean()


def ema(closes: pd.Series, window: int) -> pd.Series:
    """Exponential moving average (adjust=False, standard recursive form)."""
    return closes.ewm(span=window, adjust=False, min_periods=window).mean()


def rsi(closes: pd.Series, window: int = RSI_WINDOW) -> pd.Series:
    """Wilder RSI. A strictly rising series reaches 100; a falling one reaches 0."""
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss
    values = 100 - (100 / (1 + rs))
    values = values.mask((avg_loss == 0) & (avg_gain > 0), 100.0)
    return values.mask((avg_loss == 0) & (avg_gain == 0), 50.0)


def macd(
    closes: pd.Series,
    fast: int = MACD_FAST,
    slow: int = MACD_SLOW,
    signal: int = MACD_SIGNAL,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, and histogram."""
    line = ema(closes, fast) - ema(closes, slow)
    signal_line = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, signal_line, line - signal_line


def trailing_return(closes: pd.Series, period: int) -> pd.Series:
    """(close / close_n_bars_ago) - 1."""
    return closes.pct_change(periods=period)


def volatility(closes: pd.Series, window: int = VOL_WINDOW) -> pd.Series:
    """Standard deviation of daily returns over `window` bars."""
    return closes.pct_change().rolling(window=window, min_periods=window).std()


def atr(bars: Sequence[Bar], window: int = ATR_WINDOW) -> Decimal | None:
    """Wilder ATR. Needs `window + 1` bars (true range uses the previous close)."""
    ordered = sorted(bars, key=lambda bar: bar.date)
    if len(ordered) < window + 1:
        return None
    ranges: list[float] = []
    for previous, current in pairwise(ordered):
        high = float(current.high)
        low = float(current.low)
        prev_close = float(previous.close)
        ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    series = pd.Series(ranges, dtype="float64")
    wilder = series.ewm(alpha=1 / window, adjust=False, min_periods=window).mean()
    return _last_decimal(wilder)


def technical_summary(bars: Sequence[Bar]) -> TechnicalSummary:
    """Last-bar snapshot plus a few plain-language signals."""
    if not bars:
        raise ValueError("technical_summary requires at least one bar")

    ordered = sorted(bars, key=lambda bar: bar.date)
    closes = pd.Series([float(bar.close) for bar in ordered], dtype="float64")
    last = ordered[-1]
    macd_line, macd_signal, macd_hist = macd(closes)
    sma_20 = _last_decimal(sma(closes, SMA_FAST))
    sma_50 = _last_decimal(sma(closes, SMA_SLOW))
    rsi_14 = _last_decimal(rsi(closes))
    macd_value = _last_decimal(macd_line)
    signal_value = _last_decimal(macd_signal)

    return TechnicalSummary(
        last_date=last.date,
        last_close=last.close,
        sma_20=sma_20,
        sma_50=sma_50,
        ema_12=_last_decimal(ema(closes, EMA_FAST)),
        rsi_14=rsi_14,
        macd=macd_value,
        macd_signal=signal_value,
        macd_histogram=_last_decimal(macd_hist),
        return_5d=_last_decimal(trailing_return(closes, RETURN_SHORT)),
        return_20d=_last_decimal(trailing_return(closes, RETURN_LONG)),
        volatility_20d=_last_decimal(volatility(closes)),
        signals=_signals(last.close, sma_20, sma_50, rsi_14, macd_value, signal_value),
    )


def _last_decimal(series: pd.Series) -> Decimal | None:
    if series.empty:
        return None
    value = series.iloc[-1]
    if pd.isna(value):
        return None
    return Decimal(str(round(float(value), 4)))


def _signals(
    last_close: Decimal,
    sma_20: Decimal | None,
    sma_50: Decimal | None,
    rsi_14: Decimal | None,
    macd_value: Decimal | None,
    macd_signal: Decimal | None,
) -> list[str]:
    signals: list[str] = []
    _compare(signals, last_close, sma_20, "price above SMA 20", "price below SMA 20")
    _compare(signals, last_close, sma_50, "price above SMA 50", "price below SMA 50")
    _compare(signals, sma_20, sma_50, "SMA 20 above SMA 50", "SMA 20 below SMA 50")
    if rsi_14 is not None:
        if rsi_14 >= RSI_OVERBOUGHT:
            signals.append("RSI overbought")
        elif rsi_14 <= RSI_OVERSOLD:
            signals.append("RSI oversold")
    _compare(signals, macd_value, macd_signal, "MACD bullish", "MACD bearish")
    return signals


def _compare(
    signals: list[str],
    left: Decimal | None,
    right: Decimal | None,
    above: str,
    below: str,
) -> None:
    if left is None or right is None:
        return
    if left > right:
        signals.append(above)
    elif left < right:
        signals.append(below)
