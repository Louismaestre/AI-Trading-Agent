"""Shapes for quarterly filings and the point-in-time snapshot shown to agents."""

import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class FundamentalPeriod(BaseModel):
    """One quarter as stored. `period_end` is the close of the reporting period, not the filing."""

    model_config = ConfigDict(from_attributes=True)

    period_end: datetime.date
    revenue: Decimal | None = None
    gross_profit: Decimal | None = None
    operating_income: Decimal | None = None
    net_income: Decimal | None = None
    diluted_eps: Decimal | None = None
    total_debt: Decimal | None = None
    total_equity: Decimal | None = None
    operating_cash_flow: Decimal | None = None


class FundamentalSnapshot(BaseModel):
    """Filings known at `as_of`, plus ratios that use the price of that same day."""

    as_of: datetime.date
    price: Decimal | None
    statements: list[FundamentalPeriod]
    pe_ratio: Decimal | None
    revenue_growth: Decimal | None
    net_margin: Decimal | None
    leverage: Decimal | None
