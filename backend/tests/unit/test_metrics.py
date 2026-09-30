from decimal import Decimal

from app.models import AgentAction
from app.services.metrics import hit_rate, max_drawdown, prediction_correct, total_return


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
