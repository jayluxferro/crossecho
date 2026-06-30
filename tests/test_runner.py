"""Tests for backend runners."""

import pytest
from qiskit import QuantumCircuit

from crossecho.runner.aer import AerBackendRunner


class TestAerBackendRunner:
    """Tests for the Aer simulator backend."""

    @pytest.fixture
    def coupling_map(self) -> list[tuple[int, int]]:
        return [(0, 1), (1, 2)]

    @pytest.fixture
    def aer(self, coupling_map) -> AerBackendRunner:
        return AerBackendRunner(coupling_map, seed=42)

    def test_backend_name(self, aer):
        assert aer.backend_name == "aer_simulator"

    def test_run_single_circuit(self, aer):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.measure([0, 1], [0, 1])

        result = aer.run([qc], shots=100)
        assert len(result.counts) == 1
        assert sum(result.counts[0].values()) == 100
        assert result.metadata["shots"] == 100
        assert result.metadata["execution_time_s"] >= 0

    def test_run_reproducible(self, aer):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.measure([0, 1], [0, 1])

        r1 = aer.run([qc], shots=500)
        r2 = aer.run([qc], shots=500)

        # With same seed, results should be identical
        assert r1.counts == r2.counts

    def test_estimate_shots_sensible(self, aer):
        qc = QuantumCircuit(2, 2)
        qc.h(0)
        qc.measure([0, 1], [0, 1])

        n = aer.estimate_shots_for_ci([qc], target_ci_width=0.02)
        # Should be in a reasonable range
        assert 500 <= n <= 50000

    def test_calibration_snapshot(self, aer):
        cal = aer.calibration_snapshot()
        assert "coupling_map" in cal
        assert cal["source"] == "aer"


class TestJobResult:
    """Tests for the JobResult dataclass."""

    def test_default_metadata(self):
        from crossecho.runner.base import JobResult

        result = JobResult(counts=[{"00": 50, "11": 50}])
        assert result.metadata == {}
        assert result.counts[0]["00"] == 50
