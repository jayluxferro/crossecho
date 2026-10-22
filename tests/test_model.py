"""Tests for the analytic leakage model."""

import numpy as np
import pytest

from crossecho.graph import shortest_swap_path
from crossecho.model.calibration import CalibrationSnapshot, calibration_from_aer
from crossecho.model.coupling import (
    effective_zz_path,
    fit_decay_constant,
)
from crossecho.model.leakage import predict_leakage
from crossecho.model.metrics import bootstrap_ci, forecasting_rmse, kl_divergence, tvd
from crossecho.model.perturbation import (
    compute_all_pairwise_zz,
    compute_zz_coupling,
    compute_zz_coupling_khz,
    sample_zz_uncertainty,
)


class TestZZCoupling:
    """Tests for 4th-order perturbation theory ZZ coupling."""

    def test_zz_coupling_sign_and_magnitude(self):
        """ZZ coupling should be ~10-1000 kHz for typical IBM parameters."""
        # Typical IBM transmon: g=20MHz, alpha=-300MHz, detuning=200MHz
        g = 0.02  # 20 MHz in GHz
        alpha_i = -0.3  # -300 MHz
        alpha_j = -0.3
        detuning = 0.2  # 200 MHz

        zeta_ghz = compute_zz_coupling(g, alpha_i, alpha_j, detuning)
        zeta_khz = compute_zz_coupling_khz(g, alpha_i, alpha_j, detuning)

        # Sign: with ω_i > ω_j (positive detuning) and α < 0, ZZ is negative
        assert zeta_ghz < 0
        # Should be in the ~1-5000 kHz range
        assert 1 < abs(zeta_khz) < 5000
        # Consistency check
        assert abs(zeta_khz - zeta_ghz * 1e6) < 1e-9

    def test_zz_coupling_symmetric(self):
        """ZZ coupling should be symmetric: ζ_ij = ζ_ji."""
        g = 0.02
        alpha_i = -0.3
        alpha_j = -0.35
        detuning_ij = 0.2  # ω_i - ω_j
        detuning_ji = -0.2  # ω_j - ω_i

        zeta_ij = compute_zz_coupling(g, alpha_i, alpha_j, detuning_ij)
        zeta_ji = compute_zz_coupling(g, alpha_j, alpha_i, detuning_ji)

        # Both should be negative (same physics from either direction)
        assert zeta_ij < 0
        assert zeta_ji < 0
        # Symmetric
        assert abs(zeta_ij - zeta_ji) < 1e-15

    def test_zz_coupling_larger_g_increases_coupling(self):
        """Stronger capacitive coupling → larger |ZZ|."""
        alpha_i = -0.3
        alpha_j = -0.3
        detuning = 0.2

        zeta_small = abs(compute_zz_coupling(0.01, alpha_i, alpha_j, detuning))
        zeta_large = abs(compute_zz_coupling(0.03, alpha_i, alpha_j, detuning))

        # g → 3x should increase |zz| → 9x (quadratic in g)
        ratio = zeta_large / zeta_small
        assert 8 < ratio < 10

    def test_zz_coupling_smaller_detuning_increases_coupling(self):
        """Closer frequencies → larger |ZZ| coupling."""
        g = 0.02
        alpha_i = -0.3
        alpha_j = -0.3

        zeta_far = abs(compute_zz_coupling(g, alpha_i, alpha_j, 1.0))
        zeta_near = abs(compute_zz_coupling(g, alpha_i, alpha_j, 0.1))

        # Closer detuning → larger coupling
        assert zeta_near > zeta_far

    def test_zz_coupling_degenerate_raises(self):
        """Detuning equal to -alpha should raise ValueError (resonance)."""
        g = 0.02
        alpha_i = -0.3
        alpha_j = -0.3

        # denom_2 = -Δ + α_i = 0 when Δ = α_i = -0.3
        with pytest.raises(ValueError):
            compute_zz_coupling(g, alpha_i, alpha_j, -0.3)

    def test_compute_all_pairwise_zz(self):
        """All pairwise ZZ couplings should be computed."""
        coupling_map = [(0, 1), (1, 2), (2, 3)]
        frequencies = {0: 5.0, 1: 5.2, 2: 4.9, 3: 5.1}
        anharmonicities = {q: -0.3 for q in range(4)}

        zz_pairs = compute_all_pairwise_zz(
            coupling_map, frequencies, anharmonicities
        )

        assert len(zz_pairs) == 6  # 3 pairs * 2 directions
        for i, j in coupling_map:
            assert (i, j) in zz_pairs
            assert (j, i) in zz_pairs

    def test_sample_zz_uncertainty(self):
        """Monte Carlo samples should be centered near the mean."""
        rng = np.random.default_rng(42)
        samples = sample_zz_uncertainty(
            zz_mean=0.0001,  # 100 kHz in GHz
            n_samples=5000,
            rng=rng,
        )

        assert len(samples) == 5000
        # Mean should be close to nominal
        assert abs(np.mean(samples) - 0.0001) < 0.0001
        # All samples should be positive (log-normal sampling)
        assert np.all(samples > 0)


class TestSwapPath:
    """Tests for SWAP-path computation."""

    def test_shortest_path_linear(self):
        """Shortest path on a linear chain."""
        coupling_map = [(0, 1), (1, 2), (2, 3), (3, 4)]
        path = shortest_swap_path(coupling_map, 0, 4)
        assert path == [0, 1, 2, 3, 4]

    def test_shortest_path_loop(self):
        """Shortest path on a loop — should pick the shorter route."""
        coupling_map = [(0, 1), (1, 2), (2, 3), (3, 0)]
        path = shortest_swap_path(coupling_map, 0, 2)
        # Can go 0→1→2 or 0→3→2, both distance 2
        assert len(path) - 1 == 2

    def test_shortest_path_disconnected(self):
        """Disconnected qubits return empty path."""
        coupling_map = [(0, 1), (2, 3)]
        path = shortest_swap_path(coupling_map, 0, 3)
        assert path == []

    def test_shortest_path_same_qubit(self):
        """Same source and target returns single-element path."""
        path = shortest_swap_path([(0, 1)], 0, 0)
        assert path == [0]

    def test_effective_zz_path_decays_with_distance(self):
        """Effective ZZ coupling should decrease with distance."""
        coupling_map = [(0, 1), (1, 2), (2, 3), (3, 4)]
        frequencies = {q: 5.0 + 0.2 * q for q in range(5)}
        anharmonicities = {q: -0.3 for q in range(5)}
        zz_pairs = compute_all_pairwise_zz(coupling_map, frequencies, anharmonicities)

        # Nearby attacker
        zeta_near, d_near = effective_zz_path(
            coupling_map, zz_pairs, [0], [1], frequencies=frequencies
        )
        # Far attacker
        zeta_far, d_far = effective_zz_path(
            coupling_map, zz_pairs, [0], [4], frequencies=frequencies
        )

        assert d_near == 1
        assert d_far == 4
        assert abs(zeta_near) > abs(zeta_far) * 10  # significant decay

    def test_fit_decay_constant(self):
        """Exponential decay fit should recover the input parameters."""
        d_0_true = 1.5  # decay constant in hops
        zeta_0_true = 1e-4  # 100 kHz in GHz
        distances = np.array([1, 2, 3, 4, 5])
        zz_eff = zeta_0_true * np.exp(-distances / d_0_true)
        # Add small noise
        rng = np.random.default_rng(42)
        zz_eff *= rng.normal(1, 0.01, size=len(zz_eff))

        zeta_0, d_0 = fit_decay_constant(distances, zz_eff)

        assert abs(zeta_0 - zeta_0_true) / zeta_0_true < 0.05
        assert abs(d_0 - d_0_true) / d_0_true < 0.15


class TestLeakagePrediction:
    """Tests for leakage prediction pipeline."""

    @pytest.fixture
    def sample_calibration(self) -> CalibrationSnapshot:
        """Build a synthetic calibration for a 5-qubit linear chain."""
        coupling_map = [(0, 1), (1, 2), (2, 3), (3, 4)]
        return calibration_from_aer(
            backend_name="test_backend",
            noise_model_info={
                "frequencies": {q: 5.0 + 0.15 * q for q in range(5)},
                "anharmonicities": {q: -0.3 for q in range(5)},
                "t1": {q: 100.0 for q in range(5)},
                "t2": {q: 80.0 for q in range(5)},
            },
            coupling_map=coupling_map,
        )

    def test_predict_leakage_returns_bounded_values(self, sample_calibration):
        """Leakage prediction should return values in [0, 1]."""
        l_mean, l_std = predict_leakage(
            calibration=sample_calibration,
            victim_qubits=[0, 1, 2],
            attacker_qubits=[3, 4],
            victim_2q_gate_density=0.3,
            victim_depth=20,
            attacker_type="idle",
        )

        assert 0 <= l_mean <= 1
        assert l_std >= 0

    def test_predict_leakage_increases_with_gate_density(self, sample_calibration):
        """More 2Q gates in victim → more leakage (for small phase regime)."""
        # Use very low densities to stay in the small-phase regime (sin²(x) ≈ x²)
        l_low, _ = predict_leakage(
            calibration=sample_calibration,
            victim_qubits=[0, 1],
            attacker_qubits=[3, 4],
            victim_2q_gate_density=0.02,
            victim_depth=5,
        )
        l_high, _ = predict_leakage(
            calibration=sample_calibration,
            victim_qubits=[0, 1],
            attacker_qubits=[3, 4],
            victim_2q_gate_density=0.05,
            victim_depth=5,
        )

        assert l_high > l_low

    def test_predict_leakage_disconnected_returns_zero(self, sample_calibration):
        """Disconnected attacker/victim should return zero leakage."""
        # Modify calibration to separate the chain
        disconnected_cal = calibration_from_aer(
            backend_name="test_disconnected",
            noise_model_info={
                "frequencies": {q: 5.0 for q in range(6)},
            },
            coupling_map=[(0, 1), (2, 3), (3, 4)],  # no path 0,1 → 2,3,4
        )
        l_mean, l_std = predict_leakage(
            calibration=disconnected_cal,
            victim_qubits=[0, 1],
            attacker_qubits=[3, 4],
            victim_2q_gate_density=0.3,
            victim_depth=10,
        )

        assert l_mean == 0.0

    def test_predict_leakage_same_qubit_maximal(self, sample_calibration):
        """Attacker and victim on same qubit → maximal leakage."""
        l_mean, _ = predict_leakage(
            calibration=sample_calibration,
            victim_qubits=[0, 1],
            attacker_qubits=[0, 2],
            victim_2q_gate_density=0.3,
            victim_depth=10,
        )

        assert l_mean >= 0.5  # Very high leakage for shared qubit


class TestMetrics:
    """Tests for statistical metrics."""

    def test_tvd_identical(self):
        """TVD of identical distributions should be 0."""
        counts = {"00": 500, "01": 500}
        assert tvd(counts, counts) == 0.0

    def test_tvd_disjoint(self):
        """TVD of disjoint distributions should be 1."""
        a = {"00": 1000}
        b = {"11": 1000}
        assert tvd(a, b) == 1.0

    def test_tvd_partial_overlap(self):
        """TVD should be between 0 and 1 for partial overlap."""
        a = {"00": 700, "01": 300}
        b = {"00": 300, "01": 700}
        tv = tvd(a, b)
        assert abs(tv - 0.4) < 1e-10

    def test_tvd_empty(self):
        """Empty counts should be handled."""
        assert tvd({}, {}) == 0.0
        assert tvd({"00": 100}, {}) == 1.0

    def test_kl_divergence(self):
        """KL divergence should be non-negative."""
        p = {"00": 700, "01": 300}
        q = {"00": 500, "01": 500}
        kl = kl_divergence(p, q)
        assert kl >= 0
        # D_KL(P||P) = 0
        assert abs(kl_divergence(p, p)) < 1e-10

    def test_kl_divergence_inf(self):
        """KL should be inf when Q has zero where P has non-zero."""
        p = {"00": 1000}
        q = {"11": 1000}
        assert kl_divergence(p, q) == float("inf")

    def test_bootstrap_ci(self):
        """Bootstrap CI should contain the true mean."""
        rng = np.random.default_rng(42)
        data = rng.normal(0.5, 0.1, size=100)
        lower, mean_val, upper = bootstrap_ci(
            data, np.mean, n_resamples=1000, rng=rng
        )
        assert lower < mean_val < upper
        # 95% CI should contain the sample mean
        assert mean_val > 0.4
        assert mean_val < 0.6

    def test_forecasting_rmse(self):
        """RMSE should compute correctly."""
        y_true = np.array([0.1, 0.2, 0.3])
        y_pred = np.array([0.12, 0.18, 0.33])
        rmse = forecasting_rmse(y_true, y_pred)
        expected = np.sqrt(np.mean((y_true - y_pred) ** 2))
        assert abs(rmse - expected) < 1e-10
