"""Tests for circuit generators."""

import pytest

from crossecho.circuits.attackers import EntanglingProbe, IdleProbe, SingleCNOTProbe
from crossecho.circuits.placement import (
    compute_swap_path_distance,
    resolve_placement,
)
from crossecho.circuits.victims import (
    GroverVictim,
    LayeredCNOTVictim,
    QFTVictim,
    SimonVictim,
)


class TestCircuitGeneratorBase:
    """Tests for the abstract base class."""

    def test_raises_on_generate_before_circuit(self):
        """Accessing circuit before generate() should raise."""
        gen = IdleProbe(2)
        with pytest.raises(RuntimeError):
            _ = gen.circuit

    def test_num_qubits(self):
        gen = IdleProbe(3)
        assert gen.num_qubits == 3

    def test_invalid_num_qubits(self):
        with pytest.raises(ValueError):
            IdleProbe(0)


class TestVictimCircuits:
    """Tests for all four victim circuit generators."""

    def test_grover_generates_valid_circuit(self):
        gen = GroverVictim(3, iterations=1)
        qc = gen.generate()
        assert qc.num_qubits == 3
        assert gen.depth > 0
        assert gen.total_gates > 0

    def test_grover_5q(self):
        gen = GroverVictim(5, iterations=2)
        qc = gen.generate()
        assert qc.num_qubits == 5
        assert qc.num_clbits == 5
        # With 2 iterations, should produce a substantial circuit
        assert gen.depth > 10

    def test_simon_generates_valid_circuit(self):
        gen = SimonVictim(6, hidden_string="101")
        qc = gen.generate()
        assert qc.num_qubits == 6
        assert gen.two_qubit_gate_count > 0

    def test_simon_deterministic(self):
        """Simon circuit with same hidden string should be identical."""
        gen1 = SimonVictim(6, hidden_string="110")
        gen2 = SimonVictim(6, hidden_string="110")
        qc1 = gen1.generate()
        qc2 = gen2.generate()
        assert qc1 == qc2

    def test_qft_generates_valid_circuit(self):
        gen = QFTVictim(4)
        qc = gen.generate()
        assert qc.num_qubits == 4
        # QFT has many controlled rotations (2Q gates)
        assert gen.two_qubit_gate_count > 0

    def test_qft_inverse(self):
        gen_fwd = QFTVictim(4, inverse=False)
        gen_inv = QFTVictim(4, inverse=True)
        qc_fwd = gen_fwd.generate()
        qc_inv = gen_inv.generate()
        # Inverse QFT should have different structure
        assert qc_fwd != qc_inv

    def test_layered_cnot_density_range(self):
        """Higher density should produce more 2Q gates."""
        gen_low = LayeredCNOTVictim(6, density=0.1, layers=2, seed=42)
        gen_high = LayeredCNOTVictim(6, density=0.5, layers=2, seed=42)
        gen_low.generate()
        gen_high.generate()
        assert gen_high.two_qubit_gate_count >= gen_low.two_qubit_gate_count

    def test_layered_cnot_reproducible(self):
        """Same seed should produce same circuit."""
        gen1 = LayeredCNOTVictim(6, density=0.3, layers=3, seed=42)
        gen2 = LayeredCNOTVictim(6, density=0.3, layers=3, seed=42)
        gen1.generate()
        gen2.generate()
        # Check gate count equality (circuit equality is tricky with params)
        assert gen1.two_qubit_gate_count == gen2.two_qubit_gate_count
        assert gen1.total_gates == gen2.total_gates


class TestAttackerCircuits:
    """Tests for all three attacker circuit generators."""

    def test_idle_probe_has_no_two_qubit_gates(self):
        gen = IdleProbe(3)
        gen.generate()
        assert gen.two_qubit_gate_count == 0
        assert gen.two_qubit_gate_density == 0.0

    def test_idle_probe_size_range(self):
        for n in range(1, 5):
            gen = IdleProbe(n)
            qc = gen.generate()
            assert qc.num_qubits == n

    def test_single_cnot_probe_has_one_cnot(self):
        gen = SingleCNOTProbe(3)
        gen.generate()
        assert gen.two_qubit_gate_count >= 1

    def test_single_cnot_probe_requires_two_qubits(self):
        with pytest.raises(ValueError):
            SingleCNOTProbe(1)

    def test_entangling_probe(self):
        gen = EntanglingProbe(4, cnot_layers=2)
        gen.generate()
        assert gen.two_qubit_gate_count >= 4  # at least 2 CNOTs per layer

    def test_entangling_probe_requires_two_qubits(self):
        with pytest.raises(ValueError):
            EntanglingProbe(1)


class TestPlacement:
    """Tests for qubit placement resolution."""

    @pytest.fixture
    def linear_coupling(self) -> list[tuple[int, int]]:
        """5-qubit linear chain: 0-1-2-3-4."""
        return [(0, 1), (1, 2), (2, 3), (3, 4)]

    @pytest.fixture
    def grid_coupling(self) -> list[tuple[int, int]]:
        """3x3 grid coupling map."""
        return [
            (0, 1), (1, 2),
            (0, 3), (1, 4), (2, 5),
            (3, 4), (4, 5),
            (3, 6), (4, 7), (5, 8),
            (6, 7), (7, 8),
        ]

    def test_compute_distance_adjacent(self, linear_coupling):
        dist = compute_swap_path_distance(linear_coupling, [0], [1])
        assert dist == 1

    def test_compute_distance_far(self, linear_coupling):
        dist = compute_swap_path_distance(linear_coupling, [0], [4])
        assert dist == 4

    def test_compute_distance_disconnected(self):
        coupling = [(0, 1), (2, 3)]
        dist = compute_swap_path_distance(coupling, [0], [3])
        assert dist == -1

    def test_resolve_placement_linear(self, linear_coupling):
        placements = resolve_placement(
            linear_coupling,
            victim_num_qubits=2,
            attacker_num_qubits=1,
            max_placements=3,
            seed=42,
        )
        assert len(placements) > 0
        for p in placements:
            assert len(p.victim_qubits) == 2
            assert len(p.attacker_qubits) == 1
            assert p.swap_path_distance >= 1

    def test_resolve_placement_grid(self, grid_coupling):
        placements = resolve_placement(
            grid_coupling,
            victim_num_qubits=3,
            attacker_num_qubits=2,
            max_placements=3,
            seed=42,
        )
        assert len(placements) > 0
        # Should find at least distance=1 placements on a connected grid
        distances = {p.swap_path_distance for p in placements}
        assert 1 in distances

    def test_placement_non_overlapping(self, linear_coupling):
        placements = resolve_placement(
            linear_coupling,
            victim_num_qubits=2,
            attacker_num_qubits=2,
            max_placements=5,
        )
        for p in placements:
            assert not (set(p.victim_qubits) & set(p.attacker_qubits))

    def test_placement_no_valid(self):
        """No valid placements when circuit too large for coupling map."""
        coupling = [(0, 1)]
        placements = resolve_placement(
            coupling,
            victim_num_qubits=3,
            attacker_num_qubits=3,
        )
        assert len(placements) == 0
