"""Visualization for CrossEcho paper figures."""

from crossecho.viz.attacker_efficiency import plot_attacker_efficiency
from crossecho.viz.distance_decay import plot_distance_decay
from crossecho.viz.predicted_vs_measured import plot_predicted_vs_measured

__all__ = [
    "plot_predicted_vs_measured",
    "plot_distance_decay",
    "plot_attacker_efficiency",
]
