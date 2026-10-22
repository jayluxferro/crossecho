"""Figure 3: Attacker efficiency curve."""

import matplotlib.pyplot as plt
import numpy as np


def plot_attacker_efficiency(
    size_ratios: np.ndarray,
    leakage: np.ndarray,
    significance_threshold: float = 0.05,
    title: str = "Attacker Efficiency: Leakage vs Attacker/Victim Size Ratio",
    output_path: str | None = None,
) -> plt.Figure:
    """Plot leakage as function of attacker/victim size ratio.

    Args:
        size_ratios: Attacker/victim qubit count ratios.
        leakage: Measured TVD values.
        significance_threshold: TVD threshold for "significant" leakage.
        title: Plot title.
        output_path: If set, save figure.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(7, 5))

    # Scatter
    ax.scatter(
        size_ratios, leakage, c="steelblue", alpha=0.5, s=30,
    )

    # Binned mean
    bins = np.array([0.05, 0.1, 0.15, 0.25, 0.35, 0.5])
    bin_centers = (bins[:-1] + bins[1:]) / 2
    means = np.zeros(len(bin_centers))
    for i in range(len(bin_centers)):
        mask = (size_ratios >= bins[i]) & (size_ratios < bins[i + 1])
        if mask.sum() > 0:
            means[i] = leakage[mask].mean()
        else:
            means[i] = np.nan

    valid = ~np.isnan(means)
    ax.plot(
        bin_centers[valid], means[valid],
        "o-", color="darkblue", linewidth=2, markersize=8,
        label="Mean leakage per size bin",
    )

    # Significance threshold
    ax.axhline(
        significance_threshold, color="red", linestyle="--", alpha=0.5,
        label=f"Significance threshold (TVD = {significance_threshold})",
    )

    # Find minimum viable attacker size
    above = means > significance_threshold
    if above.any():
        min_viable = bin_centers[np.where(above)[0][0]]
        ax.axvline(
            min_viable, color="green", linestyle=":", alpha=0.5,
            label=f"Min viable: {min_viable:.2f}",
        )

    ax.set_xlabel("Attacker / Victim Size Ratio (qubits)")
    ax.set_ylabel("Leakage (TVD)")
    ax.set_title(title)
    ax.legend(fontsize=9)
    ax.grid(True, alpha=0.2)

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    return fig
