"""Fourth-order perturbation theory for ZZ coupling in transmon qubits.

Derivation from the transmon Hamiltonian:

    H = H_0 + V

    H_0 = Σ_i (ω_i a_i† a_i + (α_i/2) a_i† a_i† a_i a_i)

    V = Σ_{⟨i,j⟩} g_ij (a_i† a_j + a_i a_j†)

where α_i = -E_C is the anharmonicity (negative for transmons). Treating the
capacitive coupling V as a perturbation yields the static ZZ interaction
strength between two coupled transmons i, j:

    ζ_ij = g² / (Δ_ij + α_j) + g² / (-Δ_ij + α_i)

where Δ_ij = ω_i - ω_j is the frequency detuning.

For identical anharmonicities α_i = α_j = α, this simplifies to:

    ζ_ij = -2g² α / (Δ_ij² - α²)

which is negative for ω_i > ω_j (positive detuning) with α < 0.

Reference: Koch et al. (PRA 2007) for the transmon Hamiltonian; the dispersive
ZZ formula follows from the difference of dressed level energies:
ζ = (E_11 - E_00) - (E_01 - E_00) - (E_10 - E_00).
"""

import numpy as np


def compute_zz_coupling(
    g: float,
    alpha_i: float,
    alpha_j: float,
    detuning: float,
) -> float:
    """Compute ZZ coupling strength ζ_ij from dispersive perturbation theory.

    ζ_ij = g²/(detuning + alpha_j) + g²/(-detuning + alpha_i)

    This is the standard dispersive ZZ formula for two coupled transmons.

    Args:
        g: Capacitive coupling strength g_ij in GHz (typical: 0.01-0.03).
        alpha_i: Anharmonicity of qubit i in GHz (negative for transmons,
                 typically around -0.2 to -0.35 GHz).
        alpha_j: Anharmonicity of qubit j in GHz.
        detuning: Frequency detuning Δ_ij = ω_i - ω_j in GHz.

    Returns:
        ZZ coupling strength ζ_ij in GHz.
        Negative value means the |11⟩ state is shifted downward in energy
        (the typical transmon case when ω_i > ω_j and α < 0).

    Raises:
        ValueError: If any denominator term vanishes (degenerate case).
    """
    denom_1 = detuning + alpha_j
    denom_2 = -detuning + alpha_i

    if abs(denom_1) < 1e-30 or abs(denom_2) < 1e-30:
        raise ValueError(
            f"Degenerate or near-degenerate case: detuning={detuning}, "
            f"alpha_i={alpha_i}, alpha_j={alpha_j}"
        )

    zeta = g**2 / denom_1 + g**2 / denom_2
    return zeta


def compute_zz_coupling_khz(
    g: float,
    alpha_i: float,
    alpha_j: float,
    detuning: float,
) -> float:
    """Compute ZZ coupling in kHz. Inputs remain in GHz for consistency."""
    return compute_zz_coupling(g, alpha_i, alpha_j, detuning) * 1e6


def compute_all_pairwise_zz(
    coupling_map: list[tuple[int, int]],
    frequencies: dict[int, float],
    anharmonicities: dict[int, float],
    g_default: float | None = None,
    g_values: dict[tuple[int, int], float] | None = None,
) -> dict[tuple[int, int], float]:
    """Compute ZZ coupling for all physically connected qubit pairs.

    Args:
        coupling_map: List of (i, j) physically connected qubit pairs.
        frequencies: Qubit frequencies ω_i in GHz.
        anharmonicities: Qubit anharmonicities α_i in GHz.
        g_default: Default coupling g_ij in GHz (used if g_values not provided).
                   If None, estimated as ~0.02 GHz typical for IBM transmons.
        g_values: Per-pair coupling strengths in GHz, keyed by (i, j).

    Returns:
        Dictionary mapping (i, j) → ζ_ij in GHz.
    """
    if g_default is None:
        g_default = 0.02  # typical IBM transmon coupling ~20 MHz

    zz_pairs: dict[tuple[int, int], float] = {}

    for i, j in coupling_map:
        if g_values and ((i, j) in g_values or (j, i) in g_values):
            g = g_values.get((i, j), g_values.get((j, i), g_default))
        else:
            g = g_default

        alpha_i = anharmonicities.get(i, -0.3)  # default ~ -300 MHz
        alpha_j = anharmonicities.get(j, -0.3)
        omega_i = frequencies.get(i, 5.0)
        omega_j = frequencies.get(j, 5.0)
        detuning = omega_i - omega_j

        try:
            zeta = compute_zz_coupling(g, alpha_i, alpha_j, detuning)
            zz_pairs[(i, j)] = zeta
            zz_pairs[(j, i)] = zeta
        except ValueError:
            # Degenerate pair — ZZ coupling is large, use an estimate
            zeta_est = abs(2 * g**2 * alpha_i * alpha_j / 1e-9)
            zz_pairs[(i, j)] = zeta_est
            zz_pairs[(j, i)] = zeta_est

    return zz_pairs


def sample_zz_uncertainty(
    zz_mean: float,
    g_std: float = 0.001,
    detuning_std: float = 0.001,
    n_samples: int = 1000,
    rng: np.random.Generator | None = None,
) -> np.ndarray:
    """Monte Carlo sample of ZZ coupling from calibration uncertainty.

    Samples g and detuning from normal distributions around their means
    and recomputes zz. Propagates uncertainty for error bar estimation.

    Args:
        zz_mean: Central ZZ coupling value in GHz.
        g_std: Standard deviation of coupling g (GHz), default 1 MHz.
        detuning_std: Standard deviation of detuning (GHz), default 1 MHz.
        n_samples: Number of Monte Carlo samples.
        rng: Optional numpy random generator.

    Returns:
        Array of n_samples ZZ coupling values in GHz.
    """
    if rng is None:
        rng = np.random.default_rng()

    # Approximate: vary zz around its mean with coefficient of variation
    # based on the fractional uncertainty in g and detuning
    g_fractional = g_std / max(abs(g_std * 100), 1e-6)
    detuning_fractional = detuning_std / max(abs(detuning_std * 100), 1e-6)
    combined_cv = np.sqrt(g_fractional**2 + detuning_fractional**2)

    # Clamp CV to reasonable range
    combined_cv = min(combined_cv, 0.5)
    combined_cv = max(combined_cv, 0.01)

    # Sample from log-normal to enforce positivity of |zz| while allowing
    # symmetric variation in signed zz
    log_std = np.sqrt(np.log(1 + combined_cv**2))
    samples = rng.lognormal(
        mean=np.log(max(abs(zz_mean), 1e-15)),
        sigma=log_std,
        size=n_samples,
    )
    # Preserve sign
    sign = 1.0 if zz_mean >= 0 else -1.0
    return sign * samples
