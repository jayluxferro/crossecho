"""Figure 2: Distance decay of crosstalk leakage."""

import matplotlib.pyplot as plt
import numpy as np


def plot_distance_decay(
    distances: np.ndarray,
    leakage: np.ndarray,
    predicted_leakage: np.ndarray | None = None,
    distance_bins: np.ndarray | None = None,
    title: str = "Crosstalk Leakage vs SWAP-Path Distance",
    output_path: str | None = None,
) -> plt.Figure:
    """Plot leakage as a function of SWAP-path distance with decay fit.

    Args:
        distances: SWAP-path distances for each data point.
        leakage: Measured TVD values.
        predicted_leakage: Optional model predictions for overlay curve.
        distance_bins: Optional bin edges for binned mean/std.
        title: Plot title.
        output_path: If set, save figure.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(7, 5))

    # Scatter individual points
    ax.scatter(
        distances, leakage, c="steelblue", alpha=0.4, s=20,
        label="Measured",
    )

    # Binned statistics if bins provided
    if distance_bins is not None:
        bin_centers = (distance_bins[:-1] + distance_bins[1:]) / 2
        means = np.zeros(len(bin_centers))
        stds = np.zeros(len(bin_centers))
        for i in range(len(bin_centers)):
            mask = (distances >= distance_bins[i]) & (distances < distance_bins[i + 1])
            if mask.sum() > 0:
                means[i] = leakage[mask].mean()
                stds[i] = leakage[mask].std()
            else:
                means[i] = np.nan
                stds[i] = np.nan

        valid = ~np.isnan(means)
        ax.errorbar(
            bin_centers[valid], means[valid], yerr=stds[valid],
            fmt="o-", color="darkblue", capsize=4, linewidth=2,
            label="Binned mean ± std",
        )

    # Predicted curve
    if predicted_leakage is not None:
        sort_idx = np.argsort(distances)
        ax.plot(
            np.array(distances)[sort_idx], np.array(predicted_leakage)[sort_idx],
            "r-", linewidth=2, alpha=0.7,
            label="Model prediction ζ(d) = ζ₀·exp(-d/d₀)",
        )

    ax.set_xlabel("SWAP-Path Distance (hops)")
    ax.set_ylabel("Leakage (TVD)")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    return fig
