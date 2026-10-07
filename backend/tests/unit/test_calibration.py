from decimal import Decimal

from app.services.calibration import calibrate_confidence


def test_perfect_high_confidence_fills_the_last_bucket() -> None:
    buckets = calibrate_confidence([(0.9, True), (1.0, True)])
    assert [bucket.count for bucket in buckets] == [0, 0, 0, 0, 2]
    assert buckets[-1].hit_rate == Decimal("1.0000")
    assert buckets[-1].mean_confidence == Decimal("0.9500")


def test_low_confidence_misses_stay_in_the_first_bins() -> None:
    buckets = calibrate_confidence([(0.1, False), (0.5, True)])
    assert buckets[0].count == 1
    assert buckets[0].hit_rate == Decimal("0.0000")
    assert buckets[2].count == 1
    assert buckets[2].hit_rate == Decimal("1.0000")


def test_empty_pairs_still_return_five_empty_bins() -> None:
    buckets = calibrate_confidence([])
    assert len(buckets) == 5
    assert all(bucket.count == 0 for bucket in buckets)
    assert all(bucket.hit_rate is None for bucket in buckets)
