"""Effect-size calculations (ConstructionPlan §A.2 target: d >= 1.0)."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def cohens_d(high: Sequence[float], low: Sequence[float]) -> float:
    """Cohen's d using pooled SD (n-1 denominator)."""
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    n_h, n_l = len(h), len(l)
    if n_h < 2 or n_l < 2:
        return float("nan")
    s_h2 = h.var(ddof=1)
    s_l2 = l.var(ddof=1)
    s_pooled = np.sqrt(((n_h - 1) * s_h2 + (n_l - 1) * s_l2) / (n_h + n_l - 2))
    if s_pooled == 0:
        return float("nan")
    return float((h.mean() - l.mean()) / s_pooled)


def hedges_g(high: Sequence[float], low: Sequence[float]) -> float:
    """Hedges' g = Cohen's d with small-sample bias correction."""
    d = cohens_d(high, low)
    n_h, n_l = len(high), len(low)
    j = 1.0 - 3.0 / (4.0 * (n_h + n_l) - 9.0)
    return d * j


def bootstrap_ci(
    high: Sequence[float],
    low: Sequence[float],
    n_boot: int = 5000,
    ci: float = 0.95,
    random_state: int = 42,
) -> tuple[float, float]:
    """Bootstrap 95% CI for Cohen's d."""
    rng = np.random.default_rng(random_state)
    h = np.asarray(high, dtype=float)
    l = np.asarray(low, dtype=float)
    n_h, n_l = len(h), len(l)
    boots = np.empty(n_boot)
    for i in range(n_boot):
        hh = rng.choice(h, n_h, replace=True)
        ll = rng.choice(l, n_l, replace=True)
        boots[i] = cohens_d(hh, ll)
    lo_q = (1 - ci) / 2
    hi_q = 1 - lo_q
    lo = float(np.nanquantile(boots, lo_q))
    hi = float(np.nanquantile(boots, hi_q))
    return lo, hi


def effect_size_report(
    high: Sequence[float], low: Sequence[float], *, n_boot: int = 5000
) -> dict:
    """Full effect-size summary for one comparison."""
    d = cohens_d(high, low)
    g = hedges_g(high, low)
    ci_lo, ci_hi = bootstrap_ci(high, low, n_boot=n_boot)
    return {
        "n_high": len(high),
        "n_low": len(low),
        "mean_high": float(np.mean(high)),
        "mean_low": float(np.mean(low)),
        "std_high": float(np.std(high, ddof=1)) if len(high) > 1 else 0.0,
        "std_low": float(np.std(low, ddof=1)) if len(low) > 1 else 0.0,
        "cohens_d": d,
        "hedges_g": g,
        "ci_95_lo": ci_lo,
        "ci_95_hi": ci_hi,
        "meets_threshold": d >= 1.0,
    }
