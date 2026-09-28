from decimal import Decimal

from app.models import OrderSide
from app.services.fees import compute_fees


def test_buy_pays_brokerage_and_ftt() -> None:
    # 0.1 % of 10_000 = 10, plus 0.4 % FTT = 40.
    assert compute_fees(OrderSide.BUY, Decimal("10000")) == Decimal("50.0000")


def test_tiny_buy_hits_the_one_euro_brokerage_minimum() -> None:
    # 0.1 % of 100 = 0.10 → €1 minimum, plus 0.4 % FTT = 0.40.
    assert compute_fees(OrderSide.BUY, Decimal("100")) == Decimal("1.4000")


def test_sell_has_no_ftt() -> None:
    assert compute_fees(OrderSide.SELL, Decimal("1000")) == Decimal("1.0000")
