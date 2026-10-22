"""Metrics: total variation distance, KL divergence, bootstrap CI, RMSE."""

from collections.abc import Callable

import numpy as np


def tvd(counts_a: dict[str, int], counts_b: dict[str, int]) -> float:
    """Total variation distance between two empirical count distributions.

    TVD = 0.5 * sum_i |p_i - q_i|, bounded in [0, 1].
    For disjoint supports (no shared keys), TVD = 1.
    """
    all_keys = set(counts_a) | set(counts_b)
    total_a = sum(counts_a.values())
    total_b = sum(counts_b.values())

    if total_a == 0 or total_b == 0:
        return 1.0 if total_a != total_b else 0.0

    diff = 0.0
    for key in all_keys:
        p = counts_a.get(key, 0) / total_a
        q = counts_b.get(key, 0) / total_b
        diff += abs(p - q)

    return 0.5 * diff


def kl_divergence(counts_p: dict[str, int], counts_q: dict[str, int]) -> float:
    """Kullback-Leibler divergence D_KL(P || Q) from empirical counts.

    Adds a small constant to avoid log(0). Returns inf if Q has zero support
    where P has non-zero probability.
    """
    total_p = sum(counts_p.values())
    total_q = sum(counts_q.values())

    if total_p == 0:
        return 0.0
    if total_q == 0:
        return float("inf")

    epsilon = 1e-12
    kl = 0.0
    for key, count_p in counts_p.items():
        p = count_p / total_p
        q = counts_q.get(key, 0) / total_q
        if p > 0:
            if q == 0:
                return float("inf")
            kl += p * np.log(p / max(q, epsilon))

    return kl


def bootstrap_ci(
    data: np.ndarray,
    statistic_fn: Callable[..., float],
    n_resamples: int = 2000,
    confidence: float = 0.95,
    rng: np.random.Generator | None = None,
) -> tuple[float, float, float]:
    """Bootstrap confidence interval for a statistic.

    Args:
        data: 1D array of observations.
        statistic_fn: Function computing a scalar statistic from a data array.
        n_resamples: Number of bootstrap resamples.
        confidence: Confidence level (default 0.95 for 95% CI).
        rng: Optional numpy random generator for reproducibility.

    Returns:
        (lower, mean, upper) tuple.
    """
    if rng is None:
        rng = np.random.default_rng()

    n = len(data)
    boot_stats = np.empty(n_resamples)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        boot_stats[i] = statistic_fn(data[idx])

    mean_val = float(np.mean(boot_stats))
    alpha = (1 - confidence) / 2
    lower = float(np.percentile(boot_stats, 100 * alpha))
    upper = float(np.percentile(boot_stats, 100 * (1 - alpha)))

    return lower, mean_val, upper


def forecasting_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root mean squared error for forecasting evaluation.

    RMSE = sqrt(mean((y_true - y_pred)^2))
    """
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mean_absolute_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean absolute error."""
    return float(np.mean(np.abs(y_true - y_pred)))
