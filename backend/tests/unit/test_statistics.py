from decimal import Decimal

from app.services.statistics import bootstrap_sharpe_ci, sharpe_difference, summarize_repeats


def test_identical_series_are_not_significantly_different() -> None:
    returns = [Decimal("0.01"), Decimal("-0.005")] * 20
    compared = sharpe_difference(returns, returns, samples=200, seed=1)
    assert compared is not None
    assert compared.p_value == Decimal("1.0000")
    assert compared.significant is False


def test_a_clearly_better_series_is_significant() -> None:
    good = [Decimal("0.02"), Decimal("0.01")] * 30
    bad = [Decimal("-0.02"), Decimal("-0.01")] * 30
    compared = sharpe_difference(good, bad, samples=200, seed=1)
    assert compared is not None
    assert compared.p_value == Decimal("0.0000")
    assert compared.significant is True


def test_bootstrap_interval_covers_a_flat_sharpe() -> None:
    returns = [Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")]
    interval = bootstrap_sharpe_ci(returns, samples=100, seed=1)
    assert interval is not None
    assert interval.low <= Decimal("0") <= interval.high


def test_repeat_summary_is_the_mean_and_sample_std() -> None:
    scored = summarize_repeats([Decimal("0.10"), Decimal("0.20")])
    assert scored is not None
    assert scored.count == 2
    assert scored.mean_return == Decimal("0.1500")
    assert scored.std_return == Decimal("0.0707")
