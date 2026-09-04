"""
cascadeid.utils.numerical

Vectorized numerical safety utilities.

Every arithmetic operation in CascadeID that could produce NaN, Inf,
division-by-zero, or overflow must go through these guards.

Rules:
- Never silently replace a bad value with 0.0 without the caller knowing.
- Return np.nan where a value genuinely cannot be computed.
- Raise ValueError for programming errors (wrong array shapes, etc.).
- All functions are stateless and importable with no side effects.
"""

from __future__ import annotations

import numpy as np


# ──────────────────────────────────────────────────────────────────────────────
# Scalar safe operations
# ──────────────────────────────────────────────────────────────────────────────

def safe_divide(numerator: float, denominator: float, fallback: float = np.nan) -> float:
    """
    Divide numerator / denominator.
    Returns fallback (default np.nan) when denominator is zero or either
    argument is non-finite.
    """
    if not (np.isfinite(numerator) and np.isfinite(denominator)):
        return fallback
    if denominator == 0.0:
        return fallback
    return numerator / denominator


def safe_log(x: float, base: float = np.e, fallback: float = np.nan) -> float:
    """
    Compute log_base(x).
    Returns fallback when x <= 0 or x is non-finite.
    """
    if not np.isfinite(x) or x <= 0.0:
        return fallback
    if base == np.e:
        return float(np.log(x))
    if not np.isfinite(base) or base <= 0.0 or base == 1.0:
        return fallback
    return float(np.log(x) / np.log(base))


def safe_sqrt(x: float, fallback: float = np.nan) -> float:
    """Square root. Returns fallback for negative or non-finite input."""
    if not np.isfinite(x) or x < 0.0:
        return fallback
    return float(np.sqrt(x))


# ──────────────────────────────────────────────────────────────────────────────
# Array safe operations
# ──────────────────────────────────────────────────────────────────────────────

def safe_mean(arr: np.ndarray) -> float:
    """
    Mean of finite values in arr.
    Returns np.nan if arr is empty or all values are non-finite.
    """
    if arr.size == 0:
        return np.nan
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.nan
    return float(np.mean(finite))


def safe_std(arr: np.ndarray, ddof: int = 1) -> float:
    """
    Standard deviation of finite values.
    Returns np.nan for fewer than ddof+1 finite observations.
    Returns 0.0 for a single unique value (constant array).
    """
    if arr.size == 0:
        return np.nan
    finite = arr[np.isfinite(arr)]
    if finite.size <= ddof:
        return np.nan
    result = float(np.std(finite, ddof=ddof))
    # Guard against numerical noise producing tiny negative under sqrt
    return max(result, 0.0)


def safe_var(arr: np.ndarray, ddof: int = 1) -> float:
    """Variance of finite values. Returns np.nan for insufficient observations."""
    if arr.size == 0:
        return np.nan
    finite = arr[np.isfinite(arr)]
    if finite.size <= ddof:
        return np.nan
    return float(np.var(finite, ddof=ddof))


def safe_median(arr: np.ndarray) -> float:
    """Median of finite values. Returns np.nan if no finite values."""
    if arr.size == 0:
        return np.nan
    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        return np.nan
    return float(np.median(finite))


def safe_normalize(arr: np.ndarray, fallback: float = np.nan) -> np.ndarray:
    """
    L2-normalize a 1D array.
    Returns array of fallback values if norm is zero or non-finite.
    """
    if arr.size == 0:
        return arr.copy()
    norm = float(np.linalg.norm(arr))
    if not np.isfinite(norm) or norm == 0.0:
        return np.full_like(arr, fallback, dtype=np.float64)
    return arr / norm


def check_finite(arr: np.ndarray, name: str = "array") -> np.ndarray:
    """
    Assert all values in arr are finite.
    Raises ValueError listing the offending indices.
    """
    bad = ~np.isfinite(arr)
    if bad.any():
        bad_indices = np.where(bad)[0].tolist()
        raise ValueError(
            f"{name} contains non-finite values at indices {bad_indices[:10]}"
            f"{'...' if len(bad_indices) > 10 else ''}"
        )
    return arr


def clip_to_finite(arr: np.ndarray, fill: float = 0.0) -> np.ndarray:
    """Replace NaN and Inf with fill. Use only where loss of NaN is acceptable."""
    out = arr.copy()
    out[~np.isfinite(out)] = fill
    return out


def count_finite(arr: np.ndarray) -> int:
    """Count finite (non-NaN, non-Inf) values."""
    return int(np.isfinite(arr).sum())


def has_sufficient_variance(arr: np.ndarray, min_std: float = 1e-10) -> bool:
    """
    Return True if the array has enough variance to be meaningful in correlation.
    A constant array has zero variance and should not be correlated.
    """
    if arr.size < 2:
        return False
    finite = arr[np.isfinite(arr)]
    if finite.size < 2:
        return False
    return float(np.std(finite)) > min_std


# ──────────────────────────────────────────────────────────────────────────────
# Entropy
# ──────────────────────────────────────────────────────────────────────────────

def shannon_entropy(counts: np.ndarray) -> float:
    """
    Shannon entropy H = -Σ p_i log(p_i) for a count array.

    Args:
        counts: Non-negative integer or float counts. Zeros are ignored.

    Returns:
        Entropy in nats, or np.nan if counts sum to zero.
    """
    counts = np.asarray(counts, dtype=np.float64)
    total = counts.sum()
    if total <= 0.0 or not np.isfinite(total):
        return np.nan
    probs = counts / total
    # Only include positive probabilities (log(0) is undefined)
    mask = probs > 0.0
    return float(-np.sum(probs[mask] * np.log(probs[mask])))


# ──────────────────────────────────────────────────────────────────────────────
# Correlation (used by correlation engine, but also directly in tests)
# ──────────────────────────────────────────────────────────────────────────────

def pearson_correlation(x: np.ndarray, y: np.ndarray) -> float:
    """
    Pearson correlation between two 1D arrays of equal length.

    Returns np.nan if:
    - Arrays are empty or length < 2
    - Either array has zero or near-zero variance
    - Result is non-finite
    """
    if x.size != y.size:
        raise ValueError(f"Arrays must have equal length: {x.size} vs {y.size}")
    if x.size < 2:
        return np.nan
    if not has_sufficient_variance(x) or not has_sufficient_variance(y):
        return np.nan

    # Use only positions where both are finite
    mask = np.isfinite(x) & np.isfinite(y)
    n_valid = mask.sum()
    if n_valid < 2:
        return np.nan

    xv, yv = x[mask], y[mask]
    if not has_sufficient_variance(xv) or not has_sufficient_variance(yv):
        return np.nan

    result = float(np.corrcoef(xv, yv)[0, 1])
    return result if np.isfinite(result) else np.nan


def weighted_pearson_correlation(
    x: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
) -> float:
    """
    Weighted Pearson correlation.
    Weights must be non-negative; zero weights exclude a position.

    Returns np.nan on insufficient data or zero variance.
    """
    if x.size != y.size or x.size != weights.size:
        raise ValueError("x, y, weights must have equal length")

    mask = np.isfinite(x) & np.isfinite(y) & np.isfinite(weights) & (weights > 0)
    if mask.sum() < 2:
        return np.nan

    xv, yv, wv = x[mask], y[mask], weights[mask]
    w_sum = wv.sum()
    if w_sum <= 0.0:
        return np.nan

    x_mean = np.sum(wv * xv) / w_sum
    y_mean = np.sum(wv * yv) / w_sum

    cov_xy = np.sum(wv * (xv - x_mean) * (yv - y_mean)) / w_sum
    var_x = np.sum(wv * (xv - x_mean) ** 2) / w_sum
    var_y = np.sum(wv * (yv - y_mean) ** 2) / w_sum

    denom = safe_sqrt(var_x * var_y)
    return safe_divide(cov_xy, denom)