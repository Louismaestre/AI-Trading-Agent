"""Point-in-time visibility and ratios. Pure functions so replay cannot leak later filings."""

import datetime
from collections.abc import Sequence
from decimal import Decimal

from app.schemas.fundamentals import FundamentalPeriod
from app.services.fees import money


def known_at(period_end: datetime.date, delay_days: int) -> datetime.date:
    """First calendar day the quarter is treated as public."""
    return period_end + datetime.timedelta(days=delay_days)


def is_known(period_end: datetime.date, as_of: datetime.date, delay_days: int) -> bool:
    return known_at(period_end, delay_days) <= as_of


def known_statements(
    statements: Sequence[FundamentalPeriod],
    as_of: datetime.date,
    delay_days: int,
) -> list[FundamentalPeriod]:
    """Newest first, only quarters already public at `as_of`."""
    visible = [row for row in statements if is_known(row.period_end, as_of, delay_days)]
    return sorted(visible, key=lambda row: row.period_end, reverse=True)


def pe_ratio(price: Decimal | None, statements: Sequence[FundamentalPeriod]) -> Decimal | None:
    """Price / TTM diluted EPS. Needs four known quarters; `price` must be the as_of close."""
    if price is None or price <= 0:
        return None
    last_four = list(statements)[:4]
    if len(last_four) < 4:
        return None
    eps: list[Decimal] = []
    for row in last_four:
        if row.diluted_eps is None:
            return None
        eps.append(row.diluted_eps)
    trailing = sum(eps, start=Decimal("0"))
    if trailing <= 0:
        return None
    return money(price / trailing)


def revenue_growth(statements: Sequence[FundamentalPeriod]) -> Decimal | None:
    """Latest quarter vs the same quarter a year earlier (four quarters back)."""
    if len(statements) < 5:
        return None
    latest, year_ago = statements[0].revenue, statements[4].revenue
    if latest is None or year_ago is None or year_ago == 0:
        return None
    return money(latest / year_ago - 1)


def net_margin(statements: Sequence[FundamentalPeriod]) -> Decimal | None:
    if not statements:
        return None
    latest = statements[0]
    if latest.revenue is None or latest.net_income is None or latest.revenue == 0:
        return None
    return money(latest.net_income / latest.revenue)


def leverage(statements: Sequence[FundamentalPeriod]) -> Decimal | None:
    if not statements:
        return None
    latest = statements[0]
    if latest.total_debt is None or latest.total_equity is None or latest.total_equity <= 0:
        return None
    return money(latest.total_debt / latest.total_equity)
