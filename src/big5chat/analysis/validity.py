"""Convergent & discriminant validity (ConstructionPlan §A.2, §G.2)."""

from __future__ import annotations

import numpy as np
from scipy import stats


DIMS = ["O", "C", "E", "A", "N"]


def convergent_correlation(
    method_a: dict[str, list[float]],
    method_b: dict[str, list[float]],
) -> dict[str, float]:
    """Pearson r between two measurement methods for each dimension.

    Args:
        method_a: Dict dim -> list of scores from method A (e.g., BFI self-report).
        method_b: Dict dim -> list of scores from method B (e.g., TRAIT MCQ).
            Lists must be equal length, aligned per subject/profile.

    Returns:
        Dict with per-dim r and mean r (r_bar).
    """
    result: dict[str, float] = {}
    rs = []
    for dim in DIMS:
        a = method_a.get(dim, [])
        b = method_b.get(dim, [])
        if len(a) < 3 or len(a) != len(b):
            result[dim] = float("nan")
            continue
        r, _ = stats.pearsonr(a, b)
        result[dim] = float(r)
        if not np.isnan(r):
            rs.append(r)
    result["mean_r"] = float(np.mean(rs)) if rs else float("nan")
    return result


def discriminant_delta(
    scores: dict[str, list[float]],
) -> dict[str, float]:
    """Compute Serapio-Garcia-style Δ = mean(same-dim r) − mean(cross-dim r).

    Args:
        scores: Dict dim -> per-profile score list. To compute both same-dim
            correlations and cross-dim correlations, pass the wide-format data
            with one score per (dim, profile). Profiles must align across dims.

    Returns:
        Dict with 'within_r' (identity = 1.0 trivially, so ignored) and
        'cross_r_mean' (absolute), and 'delta' = 1 - mean(|cross|).

    NOTE: This is a simplified Δ. A full implementation would use two separate
    measurement methods per dimension and compute within-dim r̄ across methods.
    See ConstructionPlan §A.2 for the exact definition.
    """
    result: dict[str, float] = {}
    cross_rs: list[float] = []
    for i, d1 in enumerate(DIMS):
        for d2 in DIMS[i + 1 :]:
            a = scores.get(d1, [])
            b = scores.get(d2, [])
            if len(a) < 3 or len(a) != len(b):
                continue
            r, _ = stats.pearsonr(a, b)
            if not np.isnan(r):
                cross_rs.append(abs(r))
    mean_cross = float(np.mean(cross_rs)) if cross_rs else float("nan")
    result["cross_r_mean_abs"] = mean_cross
    # Simplified Δ: assumes within-dim convergent r ≈ 1 if same method compared
    # against itself; researchers should substitute the real within-method r̄.
    result["delta_simplified"] = 1.0 - mean_cross
    return result
