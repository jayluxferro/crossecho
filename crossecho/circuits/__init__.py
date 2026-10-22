"""Circuit generators for CrossEcho victim and attacker circuits."""

from crossecho.circuits.attackers import (
    EntanglingProbe,
    IdleProbe,
    SingleCNOTProbe,
)
from crossecho.circuits.base import CircuitGenerator
from crossecho.circuits.placement import (
    Placement,
    compute_swap_path_distance,
    resolve_placement,
)
from crossecho.circuits.victims import (
    GroverVictim,
    LayeredCNOTVictim,
    QFTVictim,
    SimonVictim,
)

__all__ = [
    "CircuitGenerator",
    "GroverVictim",
    "SimonVictim",
    "QFTVictim",
    "LayeredCNOTVictim",
    "IdleProbe",
    "SingleCNOTProbe",
    "EntanglingProbe",
    "Placement",
    "resolve_placement",
    "compute_swap_path_distance",
]
