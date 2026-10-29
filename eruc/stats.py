"""Classical statistics used by the prototype. No fitting, no training.

The key fact: CMS OP-18b is ONE number per hospital, the median minutes from
ED arrival to ED departure for discharged patients. CMS publishes no spread.
Any interval built here is therefore conditional on an ASSUMED dispersion
(sigma of a lognormal whose median is pinned at OP-18b). The site shows that
assumption, lets the reader move it, and reports the range across a plausible
band rather than one confident number.
"""
from __future__ import annotations

import math
from bisect import bisect_left, bisect_right
from statistics import NormalDist

_N = NormalDist()

# Assumed dispersion of individual visit times around the hospital median.
# These are assumptions, not estimates: CMS does not publish a spread and no
# literature value is cited. Shown and adjustable in the UI.
SIGMA_DEFAULT = 0.6
SIGMA_LOW = 0.4
SIGMA_HIGH = 0.8


def lognormal_quantile(median: float, sigma: float, p: float) -> float:
    """p-quantile of a lognormal with the given median (exp(mu)) and sigma."""
    if median <= 0 or sigma < 0 or not 0 < p < 1:
        raise ValueError("need median > 0, sigma >= 0, 0 < p < 1")
    return median * math.exp(sigma * _N.inv_cdf(p))


def lognormal_exceed(median: float, sigma: float, t: float) -> float:
    """P(T > t) for T lognormal with the given median and sigma."""
    if t <= 0:
        return 1.0
    if sigma == 0:
        return 1.0 if median > t else 0.0
    return 1.0 - _N.cdf((math.log(t) - math.log(median)) / sigma)


def interval(median: float, sigma: float, coverage: float = 0.8) -> tuple[float, float]:
    a = (1 - coverage) / 2
    return lognormal_quantile(median, sigma, a), lognormal_quantile(median, sigma, 1 - a)


def median_se(median: float, sigma: float, n: int) -> float:
    """Large-sample standard error of a sample median under the lognormal.

    SE = 1 / (2 f(m) sqrt(n)), and the lognormal density at its median is
    f(m) = 1 / (m * sigma * sqrt(2*pi)), so SE = m * sigma * sqrt(pi / (2n)).
    """
    if n <= 0:
        raise ValueError("n must be positive")
    return median * sigma * math.sqrt(math.pi / (2 * n))


def share_longer(x: float, values: list[float]) -> float:
    """Share of hospitals whose median is LONGER than x (ties count half).

    Read as: this hospital's median total ED time is shorter than
    share_longer(x) of the hospitals in the comparison group.
    """
    if not values:
        raise ValueError("empty comparison group")
    gt = sum(1 for v in values if v > x)
    eq = sum(1 for v in values if v == x)
    return (gt + 0.5 * eq) / len(values)


def share_longer_than_others(x: float, sorted_values: list[float]) -> float | None:
    """share_longer for a hospital that is itself one of sorted_values.

    The hospital is left out of its own comparison group, so the shortest of
    n hospitals is "shorter than 100% of the others". Ties with other hospitals
    count half. Returns None when there is no other hospital to compare with.
    """
    n = len(sorted_values)
    if n < 2:
        return None
    lo, hi = bisect_left(sorted_values, x), bisect_right(sorted_values, x)
    if lo == hi:
        raise ValueError("x must be one of the values")
    gt = n - hi
    eq_others = hi - lo - 1
    return (gt + 0.5 * eq_others) / (n - 1)


def quantiles(values: list[float], probs: list[float]) -> list[float]:
    """Linear-interpolation sample quantiles (type 7, the R / numpy default)."""
    s = sorted(values)
    n = len(s)
    out = []
    for p in probs:
        h = (n - 1) * p
        lo = math.floor(h)
        hi = min(lo + 1, n - 1)
        out.append(s[lo] + (h - lo) * (s[hi] - s[lo]))
    return out


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 3958.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))
