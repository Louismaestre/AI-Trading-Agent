from decimal import Decimal

from app.models import AgentAction
from app.services.fees import money
from app.services.metrics import (
    annualized_volatility,
    daily_returns,
    hit_rate,
    max_drawdown,
    prediction_correct,
    sharpe_ratio,
    sortino_ratio,
    total_return,
)


def test_max_drawdown_is_a_quarter_when_the_curve_falls_from_120_to_90() -> None:
    assert max_drawdown([Decimal("100"), Decimal("120"), Decimal("90")]) == Decimal("0.2500")


def test_total_return_uses_the_first_and_last_points() -> None:
    assert total_return([Decimal("100"), Decimal("110")]) == Decimal("0.1000")


def test_empty_curve_has_no_return_or_drawdown() -> None:
    assert total_return([]) == Decimal("0")
    assert max_drawdown([]) == Decimal("0")


def test_hit_rate_is_none_without_directional_calls() -> None:
    assert hit_rate([]) is None
    assert hit_rate([True, False]) == Decimal("0.5000")


def test_prediction_correct_scores_buy_and_sell_only() -> None:
    assert prediction_correct(AgentAction.BUY, Decimal("100"), Decimal("110")) is True
    assert prediction_correct(AgentAction.SELL, Decimal("100"), Decimal("90")) is True
    assert prediction_correct(AgentAction.HOLD, Decimal("100"), Decimal("110")) is None


def test_flat_curve_has_zero_sharpe_and_sortino() -> None:
    returns = daily_returns([Decimal("100"), Decimal("100"), Decimal("100")])
    assert returns == [Decimal("0"), Decimal("0")]
    assert annualized_volatility(returns) == Decimal("0.0000")
    assert sharpe_ratio(returns) == Decimal("0.0000")
    assert sortino_ratio(returns) == Decimal("0.0000")


def test_sharpe_matches_a_hand_computed_series() -> None:
    returns = daily_returns([Decimal("100"), Decimal("103"), Decimal("105.06")])
    assert returns == [Decimal("0.03"), Decimal("0.02")]
    expected = money((Decimal("0.025") / Decimal("0.00005").sqrt()) * Decimal(252).sqrt())
    assert sharpe_ratio(returns) == expected
    assert sortino_ratio(returns) is None


def test_sortino_uses_only_returns_below_the_target() -> None:
    returns = daily_returns([Decimal("100"), Decimal("103"), Decimal("100.94")])
    assert returns == [Decimal("0.03"), Decimal("-0.02")]
    expected = money((Decimal("0.005") / Decimal("0.0002").sqrt()) * Decimal(252).sqrt())
    assert sortino_ratio(returns) == expected


def test_one_return_has_no_sharpe() -> None:
    assert sharpe_ratio([Decimal("0.01")]) is None
    assert annualized_volatility([Decimal("0.01")]) is None
