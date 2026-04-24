"""Tests for analysis layer."""

import numpy as np

from big5chat.analysis.effect_size import bootstrap_ci, cohens_d, hedges_g
from big5chat.analysis.reliability import cronbach_alpha, icc3k
from big5chat.analysis.validity import convergent_correlation, discriminant_delta


def test_cohens_d_known_value():
    # Two groups with mean diff = 2, pooled sd = 1 => d = 2
    high = [3.0, 4.0, 5.0, 6.0]
    low = [1.0, 2.0, 3.0, 4.0]
    d = cohens_d(high, low)
    assert 1.5 < d < 2.5


def test_hedges_g_smaller_than_d():
    high = [3.0, 4.0, 5.0, 6.0]
    low = [1.0, 2.0, 3.0, 4.0]
    d = cohens_d(high, low)
    g = hedges_g(high, low)
    assert abs(g) < abs(d)


def test_bootstrap_ci_brackets_d():
    rng = np.random.default_rng(0)
    high = rng.normal(5, 1, 30).tolist()
    low = rng.normal(3, 1, 30).tolist()
    d = cohens_d(high, low)
    lo, hi = bootstrap_ci(high, low, n_boot=500)
    assert lo <= d <= hi


def test_cronbach_alpha_high_consistency():
    rng = np.random.default_rng(0)
    true_score = rng.normal(0, 1, 50)
    items = np.column_stack([true_score + rng.normal(0, 0.2, 50) for _ in range(6)])
    alpha = cronbach_alpha(items)
    assert alpha > 0.8


def test_cronbach_alpha_noise_low():
    rng = np.random.default_rng(0)
    items = rng.normal(0, 1, (50, 6))
    alpha = cronbach_alpha(items)
    assert alpha < 0.3


def test_icc3k_high_when_raters_agree():
    rng = np.random.default_rng(0)
    targets = rng.normal(0, 1, 20)
    ratings = np.column_stack([targets + rng.normal(0, 0.1, 20) for _ in range(3)])
    assert icc3k(ratings) > 0.8


def test_convergent_correlation_perfect():
    method_a = {"O": [1, 2, 3, 4, 5], "C": [5, 4, 3, 2, 1],
                "E": [1, 2, 3, 4, 5], "A": [1, 2, 3, 4, 5],
                "N": [1, 2, 3, 4, 5]}
    r = convergent_correlation(method_a, method_a)
    assert abs(r["mean_r"] - 1.0) < 1e-6


def test_discriminant_delta_returns_keys():
    scores = {
        "O": [1, 2, 3, 4, 5],
        "C": [2, 3, 4, 5, 1],
        "E": [5, 1, 4, 2, 3],
        "A": [1, 3, 5, 2, 4],
        "N": [2, 4, 1, 5, 3],
    }
    d = discriminant_delta(scores)
    assert "cross_r_mean_abs" in d
    assert "delta_simplified" in d
