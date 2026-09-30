import datetime
from decimal import Decimal

from app.schemas.fundamentals import FundamentalPeriod
from app.services.fundamental_ratios import (
    is_known,
    known_at,
    known_statements,
    leverage,
    net_margin,
    pe_ratio,
    revenue_growth,
)

PERIOD_END = datetime.date(2026, 6, 30)
JULY_15 = datetime.date(2026, 7, 15)
SEPTEMBER_1 = datetime.date(2026, 9, 1)
DELAY = 60


def _period(
    period_end: datetime.date,
    *,
    revenue: str | None = "1000",
    net_income: str | None = "100",
    diluted_eps: str | None = "2.5",
    total_debt: str | None = "400",
    total_equity: str | None = "800",
) -> FundamentalPeriod:
    return FundamentalPeriod(
        period_end=period_end,
        revenue=None if revenue is None else Decimal(revenue),
        net_income=None if net_income is None else Decimal(net_income),
        diluted_eps=None if diluted_eps is None else Decimal(diluted_eps),
        total_debt=None if total_debt is None else Decimal(total_debt),
        total_equity=None if total_equity is None else Decimal(total_equity),
    )


def test_june_quarter_is_hidden_on_15_july_and_public_on_1_september() -> None:
    assert known_at(PERIOD_END, DELAY) == datetime.date(2026, 8, 29)
    assert not is_known(PERIOD_END, JULY_15, DELAY)
    assert is_known(PERIOD_END, SEPTEMBER_1, DELAY)


def test_known_statements_drop_filings_still_inside_the_delay() -> None:
    june = _period(PERIOD_END)
    march = _period(datetime.date(2026, 3, 31))

    visible = known_statements([june, march], JULY_15, DELAY)

    assert [row.period_end for row in visible] == [datetime.date(2026, 3, 31)]


def test_pe_uses_the_given_price_not_a_later_one() -> None:
    quarters = [
        _period(datetime.date(2026, 3, 31), diluted_eps="2.5"),
        _period(datetime.date(2025, 12, 31), diluted_eps="2.5"),
        _period(datetime.date(2025, 9, 30), diluted_eps="2.5"),
        _period(datetime.date(2025, 6, 30), diluted_eps="2.5"),
    ]

    assert pe_ratio(Decimal("100"), quarters) == Decimal("10.0000")
    assert pe_ratio(Decimal("200"), quarters) == Decimal("20.0000")


def test_pe_needs_four_quarters_with_eps() -> None:
    quarters = [_period(datetime.date(2026, 3, 31))] * 3
    assert pe_ratio(Decimal("100"), quarters) is None


def test_revenue_growth_compares_to_the_same_quarter_a_year_earlier() -> None:
    statements = [
        _period(datetime.date(2026, 6, 30), revenue="1200"),
        _period(datetime.date(2026, 3, 31), revenue="1100"),
        _period(datetime.date(2025, 12, 31), revenue="1050"),
        _period(datetime.date(2025, 9, 30), revenue="1000"),
        _period(datetime.date(2025, 6, 30), revenue="1000"),
    ]
    assert revenue_growth(statements) == Decimal("0.2000")


def test_net_margin_and_leverage_use_the_latest_known_quarter() -> None:
    latest = _period(
        datetime.date(2026, 3, 31),
        revenue="1000",
        net_income="100",
        total_debt="400",
        total_equity="800",
    )
    assert net_margin([latest]) == Decimal("0.1000")
    assert leverage([latest]) == Decimal("0.5000")
