"""Quarterly filings from Yahoo Finance. yfinance returns the latest restated figures.

There is no filing date: callers must apply `fundamentals_publication_delay_days`.
"""

import datetime
from collections.abc import Sequence
from decimal import Decimal
from typing import Any

import pandas as pd
import yfinance as yf

from app.schemas.fundamentals import FundamentalPeriod
from app.services.fees import money

_REVENUE = ("Total Revenue", "Operating Revenue", "TotalRevenue")
_GROSS = ("Gross Profit", "GrossProfit")
_OPERATING = ("Operating Income", "OperatingIncome")
_NET = ("Net Income", "Net Income Common Stockholders", "NetIncome")
_EPS = ("Diluted EPS", "Basic EPS", "DilutedEPS", "BasicEPS")
_DEBT = ("Total Debt", "TotalDebt")
_EQUITY = (
    "Stockholders Equity",
    "Common Stock Equity",
    "Total Equity Gross Minority Interest",
    "StockholdersEquity",
)
_CASH_FLOW = (
    "Operating Cash Flow",
    "Cash Flow From Continuing Operating Activities",
    "OperatingCashFlow",
)


def fetch_fundamentals(ticker: str) -> list[FundamentalPeriod]:
    """Latest restated quarters. Empty if Yahoo has nothing for this ticker."""
    yahoo = yf.Ticker(ticker)
    return statements_from_frames(
        yahoo.quarterly_income_stmt,
        yahoo.quarterly_balance_sheet,
        yahoo.quarterly_cashflow,
    )


def statements_from_frames(
    income: pd.DataFrame,
    balance: pd.DataFrame,
    cashflow: pd.DataFrame,
) -> list[FundamentalPeriod]:
    """Map yfinance frames (columns = period ends) to periods. Used by tests without Yahoo."""
    ends = _period_ends(income, balance, cashflow)
    return [
        FundamentalPeriod(
            period_end=end,
            revenue=_cell(income, end, _REVENUE),
            gross_profit=_cell(income, end, _GROSS),
            operating_income=_cell(income, end, _OPERATING),
            net_income=_cell(income, end, _NET),
            diluted_eps=_cell(income, end, _EPS),
            total_debt=_cell(balance, end, _DEBT),
            total_equity=_cell(balance, end, _EQUITY),
            operating_cash_flow=_cell(cashflow, end, _CASH_FLOW),
        )
        for end in ends
    ]


def _period_ends(*frames: pd.DataFrame) -> list[datetime.date]:
    found: set[datetime.date] = set()
    for frame in frames:
        if frame is None or frame.empty:
            continue
        for column in frame.columns:
            found.add(_as_date(column))
    return sorted(found, reverse=True)


def _cell(frame: pd.DataFrame, period_end: datetime.date, aliases: Sequence[str]) -> Decimal | None:
    if frame is None or frame.empty:
        return None
    column = _matching_column(frame, period_end)
    if column is None:
        return None
    for name in aliases:
        if name not in frame.index:
            continue
        raw = frame.loc[name, column]
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        return money(Decimal(str(raw)))
    return None


def _matching_column(frame: pd.DataFrame, period_end: datetime.date) -> Any | None:
    for column in frame.columns:
        if _as_date(column) == period_end:
            return column
    return None


def _as_date(value: object) -> datetime.date:
    if isinstance(value, datetime.datetime):
        return value.date()
    if isinstance(value, datetime.date):
        return value
    return pd.Timestamp(str(value)).date()
