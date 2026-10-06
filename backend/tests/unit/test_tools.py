import datetime
from decimal import Decimal
from unittest.mock import MagicMock

from app.agents.tools import AgentTools, enforce_quantity, target_buy_quantity, target_sell_quantity
from app.services.risk_rules import RiskBook


def test_ten_percent_of_100k_at_500_is_20_shares() -> None:
    assert target_buy_quantity(Decimal("100000"), Decimal("500"), 0.1) == 20


def test_aberrant_quantity_is_replaced_by_the_target() -> None:
    check = enforce_quantity(proposed=1000, expected=20)
    assert check.accepted == 20
    assert check.corrected is True
    assert check.proposed == 1000


def test_matching_proposal_is_not_corrected() -> None:
    check = enforce_quantity(proposed=20, expected=20)
    assert check.accepted == 20
    assert check.corrected is False


def test_zero_weight_or_price_buys_nothing() -> None:
    assert target_buy_quantity(Decimal("100000"), Decimal("500"), 0) == 0
    assert target_buy_quantity(Decimal("100000"), Decimal("0"), 0.1) == 0


def test_sell_quantity_brings_the_position_down_to_the_target_weight() -> None:
    # Keep 20 shares (10 % of 100k at 500), so sell 10 of the 30 held.
    assert target_sell_quantity(30, Decimal("100000"), Decimal("500"), 0.1) == 10
    assert target_sell_quantity(30, Decimal("100000"), Decimal("500"), 0) == 30


def test_get_risk_book_delegates_to_the_risk_service() -> None:
    book = RiskBook(
        ticker="MC.PA",
        sector="Luxury",
        total_value=Decimal("100000"),
        cash=Decimal("100000"),
        positions=(),
        orders_today=0,
    )
    risk = MagicMock()
    risk.book_for.return_value = book
    as_of = datetime.datetime(2026, 9, 15, 12, 0, tzinfo=datetime.UTC)
    tools = AgentTools(MagicMock(), MagicMock(), 1, as_of, risk=risk)

    assert tools.get_risk_book("MC.PA") is book
    risk.book_for.assert_called_once_with(1, "MC.PA", as_of)
