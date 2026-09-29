from decimal import Decimal

from app.agents.tools import enforce_quantity, target_buy_quantity, target_sell_quantity


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
