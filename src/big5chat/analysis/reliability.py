"""Reliability metrics: Cronbach alpha, ICC3,k (ConstructionPlan §A.2)."""

from __future__ import annotations

from typing import Sequence

import numpy as np


def cronbach_alpha(item_scores: np.ndarray | Sequence[Sequence[float]]) -> float:
    """Cronbach's alpha.

    Args:
        item_scores: 2D array, shape (n_subjects, n_items).

    Returns:
        Alpha in [0, 1] (can be negative for pathological data).
    """
    x = np.asarray(item_scores, dtype=float)
    if x.ndim != 2 or x.shape[1] < 2:
        return float("nan")
    n_items = x.shape[1]
    item_vars = x.var(axis=0, ddof=1)
    total_var = x.sum(axis=1).var(ddof=1)
    if total_var == 0:
        return float("nan")
    return float((n_items / (n_items - 1)) * (1.0 - item_vars.sum() / total_var))


def icc3k(ratings: np.ndarray | Sequence[Sequence[float]]) -> float:
    """ICC(3,k): two-way mixed, consistency, average of k raters.

    Args:
        ratings: 2D array, shape (n_targets, k_raters). Here 'raters' can be
            paraphrase variants or repetitions of the same measurement.

    Formula (Shrout & Fleiss 1979):
        ICC(3,k) = (MS_R - MS_E) / MS_R
    """
    x = np.asarray(ratings, dtype=float)
    if x.ndim != 2 or x.shape[1] < 2:
        return float("nan")
    n, k = x.shape
    grand_mean = x.mean()
    row_means = x.mean(axis=1)
    col_means = x.mean(axis=0)

    ss_total = ((x - grand_mean) ** 2).sum()
    ss_rows = k * ((row_means - grand_mean) ** 2).sum()
    ss_cols = n * ((col_means - grand_mean) ** 2).sum()
    ss_error = ss_total - ss_rows - ss_cols

    ms_rows = ss_rows / (n - 1)
    ms_error = ss_error / ((n - 1) * (k - 1))

    if ms_rows == 0:
        return float("nan")
    return float((ms_rows - ms_error) / ms_rows)
