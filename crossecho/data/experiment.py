"""Experiment matrix builder: defines the (victim, attacker, placement) grid."""

from dataclasses import dataclass

from crossecho.circuits.placement import resolve_placement


@dataclass
class ExperimentCell:
    """One cell in the experiment matrix."""

    victim_type: str
    victim_num_qubits: int
    victim_qubits: list[int]
    attacker_type: str
    attacker_num_qubits: int
    attacker_qubits: list[int]
    attacker_size_ratio: float
    swap_path_distance: int
    shots: int
    predicted_leakage: float | None = None
    predicted_leakage_std: float | None = None


def build_experiment_matrix(
    victim_configs: list[tuple[str, dict]],
    attacker_configs: list[tuple[str, dict]],
    coupling_map: list[tuple[int, int]],
    distance_bins: list[tuple[float, float]] | None = None,
    shots_per_cell: int = 5000,
    max_placements_per_distance: int = 5,
    seed: int = 42,
) -> list[ExperimentCell]:
    """Build the full experiment matrix across all dimensions.

    Dimensions: victim_type × attacker_type × placement × distance.

    Args:
        victim_configs: List of (type_name, params) tuples. Params must include
                       'num_qubits'. Example: [("grover", {"num_qubits": 3}), ...].
        attacker_configs: List of (type_name, params) tuples.
        coupling_map: List of (i, j) connected qubit pairs.
        distance_bins: Optional (min_dist, max_dist) bins. If None, uses all distances.
        shots_per_cell: Number of shots per experiment cell.
        max_placements_per_distance: Max placements to return per distance bin.
        seed: Random seed for reproducible placement selection.

    Returns:
        List of ExperimentCell objects defining the experiment matrix.
    """
    cells: list[ExperimentCell] = []

    for victim_type, victim_params in victim_configs:
        v_n_qubits = victim_params.get("num_qubits", 4)
        for attacker_type, attacker_params in attacker_configs:
            a_n_qubits = attacker_params.get("num_qubits", 2)
            attacker_ratio = a_n_qubits / v_n_qubits

            # Find valid placements
            placements = resolve_placement(
                coupling_map=coupling_map,
                victim_num_qubits=v_n_qubits,
                attacker_num_qubits=a_n_qubits,
                max_placements=max_placements_per_distance * 3,
                seed=seed,
            )

            # Filter by distance bins if specified
            for placement in placements:
                dist = placement.swap_path_distance
                if distance_bins is not None:
                    # Check if distance falls within any bin
                    in_bin = any(
                        lo <= dist <= hi for lo, hi in distance_bins
                    )
                    if not in_bin:
                        continue

                cell = ExperimentCell(
                    victim_type=victim_type,
                    victim_num_qubits=v_n_qubits,
                    victim_qubits=placement.victim_qubits,
                    attacker_type=attacker_type,
                    attacker_num_qubits=a_n_qubits,
                    attacker_qubits=placement.attacker_qubits,
                    attacker_size_ratio=attacker_ratio,
                    swap_path_distance=dist,
                    shots=shots_per_cell,
                )
                cells.append(cell)

    return cells


def summarize_matrix(cells: list[ExperimentCell]) -> dict:
    """Return summary statistics of the experiment matrix.

    Returns dict with keys: total_cells, total_shots, unique_distances,
    victim_types, attacker_types.
    """
    if not cells:
        return {
            "total_cells": 0,
            "total_shots": 0,
            "unique_distances": [],
            "victim_types": [],
            "attacker_types": [],
        }

    return {
        "total_cells": len(cells),
        "total_shots": sum(c.shots for c in cells),
        "unique_distances": sorted({c.swap_path_distance for c in cells}),
        "victim_types": sorted({c.victim_type for c in cells}),
        "attacker_types": sorted({c.attacker_type for c in cells}),
    }
