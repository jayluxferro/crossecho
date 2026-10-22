"""Graph utilities: adjacency building and shortest path on coupling maps."""

import heapq
from collections import defaultdict


def build_adjacency(
    coupling_map: list[tuple[int, int]],
) -> dict[int, list[int]]:
    """Build undirected adjacency list from coupling map."""
    adj: dict[int, list[int]] = defaultdict(list)
    for i, j in coupling_map:
        adj[i].append(j)
        adj[j].append(i)
    return adj


def shortest_swap_path(
    coupling_map: list[tuple[int, int]],
    source: int,
    target: int,
) -> list[int]:
    """Find the shortest path between source and target along the coupling map.

    Uses Dijkstra's algorithm with unit edge weights.

    Args:
        coupling_map: List of (i, j) coupled qubit pairs.
        source: Starting qubit index.
        target: Target qubit index.

    Returns:
        List of qubit indices [source, ..., target] along the path, or
        empty list if no path exists.
    """
    if source == target:
        return [source]

    adj = build_adjacency(coupling_map)
    if source not in adj or target not in adj:
        return []

    pq: list[tuple[float, int]] = [(0, source)]
    dist: dict[int, float] = {source: 0}
    prev: dict[int, int | None] = {source: None}

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, float("inf")):
            continue
        if u == target:
            break
        for v in adj.get(u, []):
            new_d = d + 1
            if new_d < dist.get(v, float("inf")):
                dist[v] = new_d
                prev[v] = u
                heapq.heappush(pq, (new_d, v))

    if target not in prev:
        return []

    path = []
    u: int | None = target
    while u is not None:
        path.append(u)
        u = prev[u]
    path.reverse()
    return path
