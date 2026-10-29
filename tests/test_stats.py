import math
import random
import statistics

import pytest

from eruc import stats


@pytest.mark.parametrize("sigma", [0.2, 0.6, 1.0])
def test_median_is_pinned_whatever_sigma(sigma):
    assert stats.lognormal_quantile(165, sigma, 0.5) == pytest.approx(165)
    assert stats.lognormal_exceed(165, sigma, 165) == pytest.approx(0.5)


def test_known_quantile():
    # exp(0.6 * z_0.9) with z_0.9 = 1.2815516
    assert stats.lognormal_quantile(100, 0.6, 0.9) == pytest.approx(100 * math.exp(0.6 * 1.2815516), rel=1e-6)


def test_quantiles_monotone_in_p_and_interval_widens_with_sigma():
    qs = [stats.lognormal_quantile(150, 0.6, p) for p in (0.05, 0.25, 0.5, 0.75, 0.95)]
    assert qs == sorted(qs)
    narrow = stats.interval(150, 0.4)
    wide = stats.interval(150, 0.8)
    assert wide[0] < narrow[0] < 150 < narrow[1] < wide[1]


def test_exceed_matches_quantile():
    t = stats.lognormal_quantile(200, 0.7, 0.8)
    assert stats.lognormal_exceed(200, 0.7, t) == pytest.approx(0.2)


def test_bad_inputs_rejected():
    with pytest.raises(ValueError):
        stats.lognormal_quantile(0, 0.6, 0.5)
    with pytest.raises(ValueError):
        stats.lognormal_quantile(100, 0.6, 1.0)
    with pytest.raises(ValueError):
        stats.median_se(100, 0.6, 0)


def test_median_se_matches_simulation():
    rng = random.Random(7)
    m, sigma, n, reps = 160.0, 0.6, 400, 1500
    meds = [statistics.median(rng.lognormvariate(math.log(m), sigma) for _ in range(n)) for _ in range(reps)]
    assert statistics.stdev(meds) == pytest.approx(stats.median_se(m, sigma, n), rel=0.1)


def test_share_longer_direction_and_ties():
    vals = [100, 120, 120, 200]
    assert stats.share_longer(100, vals) == pytest.approx((3 + 0.5) / 4)  # short wait ranks well
    assert stats.share_longer(200, vals) == pytest.approx(0.5 / 4)
    assert stats.share_longer(120, vals) == pytest.approx((1 + 1) / 4)


def test_type7_quantiles():
    assert stats.quantiles([1, 2, 3, 4], [0, 0.5, 1, 0.25]) == [1, 2.5, 4, 1.75]


def test_haversine_nyc_chicago():
    assert stats.haversine_miles(40.7128, -74.0060, 41.8781, -87.6298) == pytest.approx(711, abs=3)


def test_share_longer_than_others_excludes_self():
    s = sorted([100, 120, 120, 200])
    assert stats.share_longer_than_others(100, s) == 1.0
    assert stats.share_longer_than_others(200, s) == 0.0
    assert stats.share_longer_than_others(120, s) == pytest.approx((1 + 0.5) / 3)
    assert stats.share_longer_than_others(100, [100]) is None
    with pytest.raises(ValueError):
        stats.share_longer_than_others(150, s)
