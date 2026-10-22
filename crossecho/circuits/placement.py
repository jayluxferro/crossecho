"""Qubit placement resolution against coupling maps.

Given a device coupling map, find valid non-overlapping qubit assignments
for victim and attacker circuits at controlled topological distances.
"""

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from crossecho.graph import build_adjacency, shortest_swap_path


@dataclass
class Placement:
    """A valid (victim_qubits, attacker_qubits) assignment on a coupling map."""

    victim_qubits: list[int]
    attacker_qubits: list[int]
    swap_path_distance: int

    def __post_init__(self) -> None:
        # Ensure non-overlapping
        if set(self.victim_qubits) & set(self.attacker_qubits):
            raise ValueError("Victim and attacker qubits must not overlap")


def compute_swap_path_distance(
    coupling_map: list[tuple[int, int]],
    attacker_qubits: list[int],
    victim_qubits: list[int],
) -> int:
    """Compute the shortest SWAP-path distance between any attacker and victim qubit.

    Args:
        coupling_map: List of (i, j) connected qubit pairs.
        attacker_qubits: Qubit indices used by the attacker.
        victim_qubits: Qubit indices used by the victim.

    Returns:
        Shortest distance in hops, or -1 if disconnected.
    """
    best = float("inf")
    for a in attacker_qubits:
        for v in victim_qubits:
            path = shortest_swap_path(coupling_map, a, v)
            if path:
                dist = len(path) - 1
                if dist < best:
                    best = dist
    return int(best) if best < float("inf") else -1


def _find_connected_subgraphs(
    adjacency: dict[int, list[int]],
    size: int,
    max_subgraphs: int = 100,
) -> list[list[int]]:
    """Find connected subgraphs of a given size using DFS.

    Args:
        adjacency: Adjacency list {qubit: [neighbors]}.
        size: Number of qubits in each subgraph.
        max_subgraphs: Maximum number of subgraphs to return.

    Returns:
        List of qubit lists, each a connected subset.
    """
    all_qubits = sorted(adjacency.keys())
    subgraphs: list[list[int]] = []

    def _dfs(start: int, current: frozenset[int]) -> None:
        if len(subgraphs) >= max_subgraphs:
            return
        if len(current) == size:
            subgraphs.append(sorted(current))
            return
        # Try adding neighbors
        neighbors: set[int] = set()
        for q in current:
            neighbors.update(adjacency.get(q, []))
        for n in sorted(neighbors - set(current)):
            if n >= start:  # avoid duplicates
                _dfs(start, current | {n})

    for start in all_qubits:
        _dfs(start, frozenset([start]))

    return subgraphs


def resolve_placement(
    coupling_map: list[tuple[int, int]],
    victim_num_qubits: int,
    attacker_num_qubits: int,
    min_distance: int = 1,
    max_distance: int | None = None,
    max_placements: int = 5,
    seed: int | None = 42,
) -> list[Placement]:
    """Find valid non-overlapping qubit placements at various distances.

    Algorithm:
    1. Enumerate connected subgraphs of size (victim + attacker).
    2. For each subgraph, try all ways to split into victim and attacker sets.
    3. Compute SWAP-path distance for each split.
    4. Return placements binned by distance, up to max_placements per bin.

    Args:
        coupling_map: List of (i, j) physically connected qubit pairs.
        victim_num_qubits: Number of qubits needed by the victim.
        attacker_num_qubits: Number of qubits needed by the attacker.
        min_distance: Minimum SWAP-path distance (default 1 for adjacent).
        max_distance: Maximum distance to consider. If None, no upper bound.
        max_placements: Maximum placements to return per distance bin.
        seed: Random seed for deterministic shuffling.

    Returns:
        List of Placement objects, sorted by distance.
    """
    adjacency = build_adjacency(coupling_map)
    total_qubits = victim_num_qubits + attacker_num_qubits

    # Find candidate subgraphs
    candidates = _find_connected_subgraphs(adjacency, total_qubits)

    placements_by_dist: dict[int, list[Placement]] = {}
    rng = np.random.default_rng(seed)

    for subgraph in candidates:
        # Try all ways to split subgraph into victim and attacker
        subgraph_set = set(subgraph)
        for victim_indices in combinations(range(total_qubits), victim_num_qubits):
            victim_set = {subgraph[i] for i in victim_indices}
            attacker_set = subgraph_set - victim_set

            distance = compute_swap_path_distance(
                coupling_map, list(attacker_set), list(victim_set)
            )

            if distance < min_distance:
                continue
            if max_distance is not None and distance > max_distance:
                continue

            placement = Placement(
                victim_qubits=sorted(victim_set),
                attacker_qubits=sorted(attacker_set),
                swap_path_distance=distance,
            )

            if distance not in placements_by_dist:
                placements_by_dist[distance] = []
            placements_by_dist[distance].append(placement)

    # Shuffle and truncate per distance bin
    result: list[Placement] = []
    for dist in sorted(placements_by_dist.keys()):
        dist_placements = placements_by_dist[dist]
        rng.shuffle(dist_placements)
        result.extend(dist_placements[:max_placements])

    return result
