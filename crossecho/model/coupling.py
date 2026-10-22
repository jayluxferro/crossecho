"""SWAP-path effective coupling computation via Schrieffer-Wolff transformation.

For a path of qubits [q_0, q_1, ..., q_d] where q_0 is an attacker qubit
and q_d is a victim qubit, the effective ZZ coupling after iterative
SW transformations decays approximately as:

    ζ_eff(d) ≈ ζ_0 · exp(-d / d_0)

or, more precisely, as the product of neighbor couplings divided by
the product of intermediate detunings:

    ζ_eff ≈ ζ_{0,1} · Π_{k=1}^{d-1} (g_{k,k+1} / Δ_{k,k+1})
"""

import numpy as np

from crossecho.graph import shortest_swap_path


def effective_zz_path(
    coupling_map: list[tuple[int, int]],
    zz_pairs: dict[tuple[int, int], float],
    attacker_qubits: list[int],
    victim_qubits: list[int],
    g_default: float = 0.02,
    frequencies: dict[int, float] | None = None,
) -> tuple[float, int]:
    """Compute effective ZZ coupling via SWAP path between attacker and victim.

    Finds the shortest SWAP-path distance between any attacker qubit and any
    victim qubit, then computes the effective ZZ coupling along that path.

    The effective coupling is computed as:

        ζ_eff = ζ_{0,1} · Π_{k=1}^{d-1} (g_{k,k+1} / |Δ_{k,k+1}|)

    where ζ_{0,1} is the direct ZZ coupling between the first pair along the
    path, and the product term captures the suppression from intermediate hops.

    Args:
        coupling_map: List of (i, j) physically connected qubit pairs.
        zz_pairs: Direct ZZ coupling strengths for neighbor pairs, keyed by (i,j).
        attacker_qubits: Qubit indices assigned to the attacker circuit.
        victim_qubits: Qubit indices assigned to the victim circuit.
        g_default: Default coupling g in GHz for pairs without computed ZZ.
        frequencies: Qubit frequencies ω_i in GHz (for detuning computation).

    Returns:
        (ζ_eff, distance) where ζ_eff is the effective ZZ coupling in GHz
        and distance is the SWAP-path length in hops.
    """
    best_distance = float("inf")
    best_path: list[int] = []

    for a in attacker_qubits:
        for v in victim_qubits:
            path = shortest_swap_path(coupling_map, a, v)
            if path and len(path) - 1 < best_distance:
                best_distance = len(path) - 1
                best_path = path

    if not best_path:
        return 0.0, -1

    distance = int(best_distance)

    if distance == 0:
        return float("inf"), 0

    first_pair = (best_path[0], best_path[1])
    zeta_first = zz_pairs.get(
        first_pair,
        zz_pairs.get((best_path[1], best_path[0]), None),
    )
    if zeta_first is None:
        zeta_first = 0.001

    suppression = 1.0
    for k in range(1, distance):
        qi = best_path[k]
        qj = best_path[k + 1]

        g = g_default
        zz_direct = zz_pairs.get((qi, qj), zz_pairs.get((qj, qi), None))
        if zz_direct is not None:
            pass  # g estimated from zz inversion if needed; use default for now

        if frequencies:
            detuning = abs(frequencies.get(qi, 5.0) - frequencies.get(qj, 5.0))
        else:
            detuning = 0.2

        if detuning < 1e-9:
            detuning = 1e-9

        suppression *= g / detuning

    zeta_eff = abs(zeta_first) * suppression
    return zeta_eff, distance


def fit_decay_constant(
    distances: np.ndarray,
    zz_effective: np.ndarray,
) -> tuple[float, float]:
    """Fit exponential decay ζ(d) = ζ_0 * exp(-d / d_0).

    Uses linear regression on log-transformed data:
    log(ζ) = log(ζ_0) - (1/d_0) * d

    Args:
        distances: Array of SWAP-path distances (≥ 1).
        zz_effective: Corresponding effective ZZ couplings.

    Returns:
        (ζ_0, d_0) where ζ_0 is the nearest-neighbor coupling and
        d_0 is the decay constant in hops.
    """
    valid = (distances > 0) & (zz_effective > 0)
    if np.sum(valid) < 2:
        return 0.0, 0.0

    d_valid = distances[valid]
    z_valid = np.log(zz_effective[valid])

    coeffs = np.polyfit(d_valid, z_valid, 1)
    b = -coeffs[0]
    a = coeffs[1]

    zeta_0 = float(np.exp(a))
    d_0 = float(1.0 / b) if b > 0 else float("inf")

    return zeta_0, d_0
