"""Figure 1: Predicted vs measured leakage scatter plot."""

import matplotlib.pyplot as plt
import numpy as np


def plot_predicted_vs_measured(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    hold_out_mask: np.ndarray | None = None,
    title: str = "Predicted vs Measured Crosstalk Leakage",
    output_path: str | None = None,
) -> plt.Figure:
    """Scatter plot of predicted L vs measured L, with error bars.

    Args:
        y_true: Measured TVD values.
        y_pred: Predicted TVD values.
        hold_out_mask: Boolean mask for hold-out points (colored differently).
        title: Plot title.
        output_path: If set, save figure to this path.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(6, 6))

    if hold_out_mask is None:
        hold_out_mask = np.zeros(len(y_true), dtype=bool)

    train_mask = ~hold_out_mask
    ax.scatter(
        y_pred[train_mask], y_true[train_mask],
        c="steelblue", label="Training", alpha=0.7, s=40,
    )
    ax.scatter(
        y_pred[hold_out_mask], y_true[hold_out_mask],
        c="crimson", marker="s", label="Hold-out", alpha=0.9, s=50,
    )

    # Diagonal reference line
    lims = [0, max(1.0, max(y_true.max(), y_pred.max()) * 1.1)]
    ax.plot(lims, lims, "k--", alpha=0.3, label="y = x")

    ax.set_xlabel("Predicted Leakage (TVD)")
    ax.set_ylabel("Measured Leakage (TVD)")
    ax.set_title(title)
    ax.legend()
    ax.set_xlim(lims)
    ax.set_ylim(lims)
    ax.grid(True, alpha=0.2)

    # Annotate RMSE
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    ax.text(
        0.05, 0.95, f"RMSE = {rmse:.4f}",
        transform=ax.transAxes, fontsize=11,
        verticalalignment="top",
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.8},
    )

    fig.tight_layout()
    if output_path:
        fig.savefig(output_path, dpi=150, bbox_inches="tight")
    return fig
