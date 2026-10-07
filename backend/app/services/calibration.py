"""Confidence vs next-day hit rate. Empty when there is no directional call."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.services.fees import money

_BUCKETS = (
    (Decimal("0.0"), Decimal("0.2")),
    (Decimal("0.2"), Decimal("0.4")),
    (Decimal("0.4"), Decimal("0.6")),
    (Decimal("0.6"), Decimal("0.8")),
    (Decimal("0.8"), Decimal("1.0")),
)


@dataclass(frozen=True)
class CalibrationBucket:
    low: Decimal
    high: Decimal
    count: int
    hit_rate: Decimal | None
    mean_confidence: Decimal | None


def calibrate_confidence(pairs: Sequence[tuple[float, bool]]) -> list[CalibrationBucket]:
    """Five bins of 0.2. A confidence of 1.0 lands in the last bin."""
    grouped: list[list[tuple[float, bool]]] = [[] for _ in _BUCKETS]
    for confidence, correct in pairs:
        index = min(int(Decimal(str(confidence)) / Decimal("0.2")), len(_BUCKETS) - 1)
        grouped[index].append((confidence, correct))
    return [_bucket(low, high, rows) for (low, high), rows in zip(_BUCKETS, grouped, strict=True)]


def _bucket(low: Decimal, high: Decimal, rows: Sequence[tuple[float, bool]]) -> CalibrationBucket:
    if not rows:
        return CalibrationBucket(low=low, high=high, count=0, hit_rate=None, mean_confidence=None)
    wins = sum(1 for _, correct in rows if correct)
    mean = sum((Decimal(str(confidence)) for confidence, _ in rows), start=Decimal("0")) / Decimal(
        len(rows)
    )
    return CalibrationBucket(
        low=low,
        high=high,
        count=len(rows),
        hit_rate=money(Decimal(wins) / Decimal(len(rows))),
        mean_confidence=money(mean),
    )
