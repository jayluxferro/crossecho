"""Leakage prediction: combine ZZ coupling model → leakage metric.

The predicted leakage L (total variation distance between attacker measurements
with victim present vs. absent) is computed from the effective ZZ coupling
between attacker and victim qubits.

For the idle-probe attacker:
    L ≈ π · ζ_eff · t_gate · n_2q_gates

where t_gate is the characteristic gate time (~100-500 ns for IBM transmons)
and n_2q_gates is the number of two-qubit gates in the victim circuit.

For CNOT-based probes, the leakage is enhanced by the probe's sensitivity
to ZZ phase accumulation. The error bars come from Monte Carlo propagation
of calibration uncertainty.
"""

import numpy as np

from crossecho.data.schema import CalibrationSnapshot
from crossecho.model.coupling import effective_zz_path
from crossecho.model.perturbation import (
    compute_all_pairwise_zz,
    sample_zz_uncertainty,
)

# Typical gate times for IBM superconducting qubits (seconds)
DEFAULT_SINGLE_QUBIT_GATE_TIME = 3.5e-8  # 35 ns
DEFAULT_TWO_QUBIT_GATE_TIME = 3.5e-7    # 350 ns (ECR gate)


def predict_leakage(
    calibration: CalibrationSnapshot,
    victim_qubits: list[int],
    attacker_qubits: list[int],
    victim_2q_gate_density: float,
    victim_depth: int,
    attacker_type: str = "idle",
    n_monte_carlo: int = 1000,
) -> tuple[float, float]:
    """Predict crosstalk leakage given calibration and circuit placement.

    Pipeline:
    1. Compute all pairwise ZZ couplings from calibration.
    2. Find the shortest SWAP path between attacker and victim qubits.
    3. Compute effective ZZ coupling along that path.
    4. Translate ζ_eff → predicted total variation distance L.
    5. Propagate calibration uncertainty via Monte Carlo → L_std.

    Args:
        calibration: Parsed device calibration snapshot.
        victim_qubits: Qubit indices used by the victim circuit.
        attacker_qubits: Qubit indices used by the attacker circuit.
        victim_2q_gate_density: Fraction of victim gates that are two-qubit.
        victim_depth: Circuit depth (layers) of the victim circuit.
        attacker_type: One of "idle", "single_cnot", "entangling".
        n_monte_carlo: Number of Monte Carlo samples for uncertainty.

    Returns:
        (L_mean, L_std) — predicted total variation distance and its
        standard deviation from calibration uncertainty.
    """
    # Step 1: Compute all pairwise ZZ couplings
    zz_pairs = compute_all_pairwise_zz(
        coupling_map=calibration.coupling_map,
        frequencies=calibration.qubit_frequencies,
        anharmonicities=calibration.anharmonicities,
    )

    # Step 2 & 3: Effective ZZ coupling along SWAP path
    zeta_eff, distance = effective_zz_path(
        coupling_map=calibration.coupling_map,
        zz_pairs=zz_pairs,
        attacker_qubits=attacker_qubits,
        victim_qubits=victim_qubits,
        frequencies=calibration.qubit_frequencies,
    )

    if distance < 0:
        # No path found — attacker/victim disconnected
        return 0.0, 0.0

    if np.isinf(zeta_eff):
        # Same qubit — maximal leakage
        return 1.0, 0.01

    # Step 4: Translate coupling to leakage
    # L ≈ π * ζ_eff * t_2q * n_2q_gates (phase accumulation model)
    # n_2q_gates ≈ victim_2q_gate_density * victim_depth * n_victim_qubits
    n_victim_qubits = len(victim_qubits)
    n_2q_gates = victim_2q_gate_density * victim_depth * n_victim_qubits

    # Convert ζ_eff from GHz to rad/s
    zeta_rad_per_s = zeta_eff * 1e9 * 2 * np.pi

    # Phase accumulated per gate: φ = ζ * t_gate
    phase_per_gate = zeta_rad_per_s * DEFAULT_TWO_QUBIT_GATE_TIME

    # Total phase accumulation from all victim 2Q gates
    total_phase = phase_per_gate * n_2q_gates

    # Attacker sensitivity factor
    if attacker_type == "idle":
        sensitivity = 1.0
    elif attacker_type == "single_cnot":
        sensitivity = 2.0  # CNOT is more sensitive to ZZ
    elif attacker_type == "entangling":
        sensitivity = 2.5
    else:
        sensitivity = 1.0

    # Leakage ~ sin²(phase/2) gives TVD-like behavior
    # For small phase, this is approximately (phase/2)²
    l_mean = float(np.sin(total_phase * sensitivity / 2) ** 2)
    l_mean = min(l_mean, 1.0)

    # Step 5: Monte Carlo uncertainty
    if n_monte_carlo > 0:
        l_samples = np.empty(n_monte_carlo)
        rng = np.random.default_rng()
        for k in range(n_monte_carlo):
            # Perturb the ZZ coupling with calibration uncertainty
            zeta_sample = sample_zz_uncertainty(
                zz_mean=zeta_eff,
                g_std=0.001,  # 1 MHz uncertainty in g
                detuning_std=0.002,  # 2 MHz uncertainty in detuning
                n_samples=1,
                rng=rng,
            )[0]
            z_s_rad = abs(zeta_sample) * 1e9 * 2 * np.pi
            phase_s = z_s_rad * DEFAULT_TWO_QUBIT_GATE_TIME * n_2q_gates
            l_samples[k] = float(np.sin(phase_s * sensitivity / 2) ** 2)

        l_samples = np.clip(l_samples, 0, 1)
        l_std = float(np.std(l_samples))
    else:
        # Analytical approximation: propagate coefficient of variation
        cv = 0.15  # ~15% relative uncertainty from calibration
        l_std = l_mean * cv

    return l_mean, l_std


def compute_victim_absent_counts(
    attacker_counts: dict[str, int],
    n_qubits: int,
    rng: np.random.Generator | None = None,
) -> dict[str, int]:
    """Generate synthetic 'victim absent' counts from an ideal distribution.

    When we cannot directly measure victim-absent on hardware (victim is
    always co-scheduled), we estimate it from the ideal uniform or noise-model
    distribution.

    Args:
        attacker_counts: Measured counts with victim present.
        n_qubits: Number of attacker qubits.
        rng: Optional random generator.

    Returns:
        Synthetic counts for the victim-absent case.
    """
    if rng is None:
        rng = np.random.default_rng()

    total_shots = sum(attacker_counts.values())
    n_outcomes = 2**n_qubits
    uniform_per_outcome = total_shots // n_outcomes

    absent_counts: dict[str, int] = {}
    for i in range(n_outcomes):
        key = format(i, f"0{n_qubits}b")
        absent_counts[key] = uniform_per_outcome

    # Distribute remainder
    remainder = total_shots - uniform_per_outcome * n_outcomes
    for i in range(remainder):
        key = format(i, f"0{n_qubits}b")
        absent_counts[key] += 1

    return absent_counts
