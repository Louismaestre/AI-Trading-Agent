import datetime
from decimal import Decimal

from app.schemas.agents import TechnicalSummary
from app.services.baselines import equal_weight, random_decision, sma_crossover_decision

DAY = datetime.date(2026, 6, 2)


def _summary(fast: Decimal | None, slow: Decimal | None) -> TechnicalSummary:
    return TechnicalSummary(
        last_date=DAY,
        last_close=Decimal("100"),
        sma_20=fast,
        sma_50=slow,
    )


def test_sma_buys_when_fast_is_above_slow() -> None:
    decision = sma_crossover_decision(_summary(Decimal("110"), Decimal("100")), False, 0.25)
    assert decision.action == "BUY"
    assert decision.target_weight == 0.25


def test_sma_sells_when_fast_is_below_slow_and_held() -> None:
    decision = sma_crossover_decision(_summary(Decimal("90"), Decimal("100")), True, 0.25)
    assert decision.action == "SELL"
    assert decision.target_weight == 0


def test_sma_holds_when_fast_is_below_slow_and_flat() -> None:
    decision = sma_crossover_decision(_summary(Decimal("90"), Decimal("100")), False, 0.25)
    assert decision.action == "HOLD"


def test_sma_holds_when_averages_are_missing() -> None:
    assert sma_crossover_decision(_summary(None, None), True, 0.25).action == "HOLD"
    assert sma_crossover_decision(_summary(Decimal("110"), None), False, 0.25).action == "HOLD"


def test_random_is_stable_for_the_same_seed() -> None:
    first = random_decision("MC.PA", DAY, 7, False, 0.5)
    second = random_decision("MC.PA", DAY, 7, False, 0.5)
    assert first == second


def test_random_does_not_sell_when_flat() -> None:
    for seed in range(80):
        decision = random_decision("MC.PA", DAY, seed, False, 0.5)
        assert decision.action in ("BUY", "HOLD")


def test_equal_weight_splits_the_book() -> None:
    assert equal_weight(4) == 0.25
    assert equal_weight(0) == 0
