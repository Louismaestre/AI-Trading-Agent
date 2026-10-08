"""Bootstrap Sharpe intervals and a paired test against a baseline."""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.services.fees import money
from app.services.metrics import sharpe_ratio

_ZERO = Decimal("0")
SAMPLES = 1000
SIGNIFICANCE = Decimal("0.05")


@dataclass(frozen=True)
class SharpeInterval:
    low: Decimal
    high: Decimal


@dataclass(frozen=True)
class SharpeComparison:
    p_value: Decimal
    significant: bool


@dataclass(frozen=True)
class RepeatSummary:
    count: int
    mean_return: Decimal
    std_return: Decimal | None


def bootstrap_sharpe_ci(
    returns: Sequence[Decimal],
    risk_free: Decimal = _ZERO,
    *,
    samples: int = SAMPLES,
    seed: int = 0,
    level: Decimal = Decimal("0.95"),
) -> SharpeInterval | None:
    """Percentile interval of annualized Sharpe from resampled daily returns."""
    scores = _bootstrap_sharpes(returns, risk_free, samples, seed)
    if len(scores) < 20:
        return None
    ordered = sorted(scores)
    tail = (Decimal("1") - level) / Decimal("2")
    lo = int(tail * Decimal(len(ordered)))
    hi = min(len(ordered) - 1, int((Decimal("1") - tail) * Decimal(len(ordered))))
    return SharpeInterval(low=money(ordered[lo]), high=money(ordered[hi]))


def sharpe_difference(
    strategy: Sequence[Decimal],
    baseline: Sequence[Decimal],
    risk_free: Decimal = _ZERO,
    *,
    samples: int = SAMPLES,
    seed: int = 0,
) -> SharpeComparison | None:
    """Two-sided paired bootstrap of Sharpe(strategy) - Sharpe(baseline)."""
    n = min(len(strategy), len(baseline))
    if n < 2:
        return None
    left = list(strategy)[:n]
    right = list(baseline)[:n]
    rng = random.Random(seed)
    diffs: list[Decimal] = []
    for _ in range(samples):
        picks = [rng.randrange(n) for _ in range(n)]
        a = sharpe_ratio([left[i] for i in picks], risk_free)
        b = sharpe_ratio([right[i] for i in picks], risk_free)
        if a is None or b is None:
            continue
        diffs.append(a - b)
    if not diffs:
        return None
    below = sum(1 for item in diffs if item <= 0) / Decimal(len(diffs))
    above = sum(1 for item in diffs if item >= 0) / Decimal(len(diffs))
    p_value = money(min(Decimal("1"), Decimal("2") * min(below, above)))
    return SharpeComparison(p_value=p_value, significant=p_value < SIGNIFICANCE)


def summarize_repeats(returns: Sequence[Decimal]) -> RepeatSummary | None:
    """Mean and sample standard deviation of total returns across repeats."""
    if not returns:
        return None
    mean = sum(returns, start=_ZERO) / Decimal(len(returns))
    if len(returns) < 2:
        return RepeatSummary(count=len(returns), mean_return=money(mean), std_return=None)
    variance = sum((item - mean) ** 2 for item in returns) / Decimal(len(returns) - 1)
    return RepeatSummary(
        count=len(returns), mean_return=money(mean), std_return=money(variance.sqrt())
    )


def _bootstrap_sharpes(
    returns: Sequence[Decimal],
    risk_free: Decimal,
    samples: int,
    seed: int,
) -> list[Decimal]:
    items = list(returns)
    if len(items) < 2:
        return []
    rng = random.Random(seed)
    scores: list[Decimal] = []
    for _ in range(samples):
        draw = [items[rng.randrange(len(items))] for _ in range(len(items))]
        score = sharpe_ratio(draw, risk_free)
        if score is not None:
            scores.append(score)
    return scores
