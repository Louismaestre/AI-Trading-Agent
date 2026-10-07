"""Performance numbers computed from an equity curve and a list of decisions."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import pairwise

from app.models import AgentAction
from app.services.calibration import CalibrationBucket
from app.services.fees import money

_ZERO = Decimal("0")
SESSIONS_PER_YEAR = 252
_SQRT_SESSIONS = Decimal(SESSIONS_PER_YEAR).sqrt()


@dataclass(frozen=True)
class ReplayMetrics:
    total_return: Decimal
    max_drawdown: Decimal
    order_count: int
    fees_paid: Decimal
    hit_rate: Decimal | None
    volatility: Decimal | None
    sharpe: Decimal | None
    sortino: Decimal | None
    calibration: list[CalibrationBucket] | None


def daily_returns(values: Sequence[Decimal]) -> list[Decimal]:
    """Close-to-close simple returns. Skips a zero starting value."""
    out: list[Decimal] = []
    for previous, current in pairwise(values):
        if previous == 0:
            continue
        out.append((current - previous) / previous)
    return out


def annualized_volatility(returns: Sequence[Decimal]) -> Decimal | None:
    """Sample standard deviation of daily returns, scaled to 252 sessions."""
    spread = _sample_std(returns)
    if spread is None:
        return None
    return money(spread * _SQRT_SESSIONS)


def sharpe_ratio(returns: Sequence[Decimal], risk_free: Decimal = _ZERO) -> Decimal | None:
    """Annualized (mean excess return) / sample volatility. Zero when both are zero."""
    return _annualized_ratio(returns, _sample_std(returns), risk_free)


def sortino_ratio(returns: Sequence[Decimal], risk_free: Decimal = _ZERO) -> Decimal | None:
    """Annualized (mean excess return) / downside deviation. Zero when both are zero."""
    target = _daily_risk_free(risk_free)
    return _annualized_ratio(returns, _downside_dev(returns, target), risk_free, target)


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


def _annualized_ratio(
    returns: Sequence[Decimal],
    risk: Decimal | None,
    risk_free: Decimal,
    target: Decimal | None = None,
) -> Decimal | None:
    if not returns or risk is None:
        return None
    excess = _mean(returns) - (target if target is not None else _daily_risk_free(risk_free))
    if risk == 0:
        return _ZERO if excess == 0 else None
    return money((excess / risk) * _SQRT_SESSIONS)


def _daily_risk_free(annual: Decimal) -> Decimal:
    return annual / Decimal(SESSIONS_PER_YEAR)


def _mean(values: Sequence[Decimal]) -> Decimal:
    return sum(values, start=_ZERO) / Decimal(len(values))


def _sample_std(values: Sequence[Decimal]) -> Decimal | None:
    if len(values) < 2:
        return None
    mu = _mean(values)
    variance = sum((item - mu) ** 2 for item in values) / Decimal(len(values) - 1)
    return variance.sqrt()


def _downside_dev(returns: Sequence[Decimal], target: Decimal) -> Decimal | None:
    if not returns:
        return None
    variance = sum(min(item - target, _ZERO) ** 2 for item in returns) / Decimal(len(returns))
    return variance.sqrt()
