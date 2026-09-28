"""French-style trading costs. Rates are constants so they stay easy to change."""

from decimal import Decimal

from app.models import OrderSide

BROKERAGE_RATE = Decimal("0.001")
BROKERAGE_MINIMUM = Decimal("1.00")
# French financial-transaction tax on purchases of large listed companies (2025+).
FTT_RATE = Decimal("0.004")

_CENTS = Decimal("0.0001")


def money(value: Decimal) -> Decimal:
    """Round to the 4 decimals stored in the database."""
    return value.quantize(_CENTS)


def compute_fees(side: OrderSide, amount: Decimal) -> Decimal:
    """Brokerage (0.1 %, €1 minimum) plus the 0.4 % FTT on buys only."""
    brokerage = max(amount * BROKERAGE_RATE, BROKERAGE_MINIMUM)
    ftt = amount * FTT_RATE if side is OrderSide.BUY else Decimal(0)
    return money(brokerage + ftt)
