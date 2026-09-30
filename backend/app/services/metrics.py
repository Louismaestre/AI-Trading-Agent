"""Performance numbers computed from an equity curve and a list of decisions."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.models import AgentAction
from app.services.fees import money

_ZERO = Decimal("0")


@dataclass(frozen=True)
class ReplayMetrics:
    total_return: Decimal
    max_drawdown: Decimal
    order_count: int
    fees_paid: Decimal
    hit_rate: Decimal | None


def total_return(values: Sequence[Decimal]) -> Decimal:
    """(last - first) / first. Zero when the curve is empty or starts at 0."""
    if len(values) < 2 or values[0] == 0:
        return _ZERO
    return money((values[-1] - values[0]) / values[0])


def max_drawdown(values: Sequence[Decimal]) -> Decimal:
    """Largest peak-to-trough drop as a fraction of the peak (120 then 90 → 0.25)."""
    peak = None
    worst = _ZERO
    for value in values:
        if peak is None or value > peak:
            peak = value
            continue
        if peak == 0:
            continue
        drop = (peak - value) / peak
        if drop > worst:
            worst = drop
    return money(worst)


def hit_rate(outcomes: Sequence[bool]) -> Decimal | None:
    """Share of directional calls that were correct. None when there is no call."""
    if not outcomes:
        return None
    wins = sum(1 for hit in outcomes if hit)
    return money(Decimal(wins) / Decimal(len(outcomes)))


def prediction_correct(action: AgentAction, close_at: Decimal, close_after: Decimal) -> bool | None:
    """BUY expects a rise, SELL a fall. HOLD is not scored."""
    if action is AgentAction.HOLD:
        return None
    if action is AgentAction.BUY:
        return close_after > close_at
    return close_after < close_at
