"""Tests for data store and experiment matrix."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path

import pytest

from crossecho.data.experiment import (
    build_experiment_matrix,
    summarize_matrix,
)
from crossecho.data.schema import ExperimentRun
from crossecho.data.store import ResultsStore


class TestExperimentMatrix:
    """Tests for experiment matrix builder."""

    @pytest.fixture
    def linear_coupling(self) -> list[tuple[int, int]]:
        return [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 6), (6, 7)]

    def test_build_matrix_produces_cells(self, linear_coupling):
        victim_configs = [("grover", {"num_qubits": 3})]
        attacker_configs = [("idle", {"num_qubits": 1})]

        cells = build_experiment_matrix(
            victim_configs=victim_configs,
            attacker_configs=attacker_configs,
            coupling_map=linear_coupling,
            max_placements_per_distance=3,
            seed=42,
        )

        assert len(cells) > 0
        for cell in cells:
            assert cell.victim_type == "grover"
            assert cell.attacker_type == "idle"
            assert len(cell.victim_qubits) == 3
            assert len(cell.attacker_qubits) == 1

    def test_build_matrix_with_distance_bins(self, linear_coupling):
        victim_configs = [("qft", {"num_qubits": 3})]
        attacker_configs = [("single_cnot", {"num_qubits": 2})]

        cells = build_experiment_matrix(
            victim_configs=victim_configs,
            attacker_configs=attacker_configs,
            coupling_map=linear_coupling,
            distance_bins=[(1, 2)],  # only nearby placements
            max_placements_per_distance=2,
            seed=42,
        )

        for cell in cells:
            assert 1 <= cell.swap_path_distance <= 2

    def test_summarize_matrix(self, linear_coupling):
        cells = build_experiment_matrix(
            victim_configs=[("grover", {"num_qubits": 3})],
            attacker_configs=[("idle", {"num_qubits": 1})],
            coupling_map=linear_coupling,
            max_placements_per_distance=3,
        )

        summary = summarize_matrix(cells)
        assert summary["total_cells"] > 0
        assert summary["total_shots"] > 0
        assert "grover" in summary["victim_types"]


class TestResultsStore:
    """Tests for sqlite results store."""

    @pytest.fixture
    def store(self) -> ResultsStore:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            store = ResultsStore(str(db_path))
            store.init_db()
            yield store

    def test_record_and_query(self, store):
        run = ExperimentRun(
            timestamp=datetime.now(tz=UTC),
            backend_name="test_backend",
            calibration_timestamp=datetime.now(tz=UTC),
            victim_type="grover",
            victim_qubits=[0, 1, 2],
            victim_num_qubits=3,
            victim_depth=10,
            victim_2q_gate_density=0.3,
            attacker_type="idle",
            attacker_qubits=[4, 5],
            attacker_num_qubits=2,
            attacker_size_ratio=0.67,
            swap_path_distance=2,
            shots=5000,
            predicted_leakage=0.05,
            predicted_leakage_std=0.01,
        )

        store.record_run(run)
        results = store.query_runs(victim_type="grover")
        assert len(results) == 1
        assert results[0].victim_type == "grover"
        assert results[0].predicted_leakage == 0.05
        assert results[0].victim_qubits == [0, 1, 2]

    def test_record_multiple(self, store):
        runs = []
        for i in range(5):
            runs.append(
                ExperimentRun(
                    timestamp=datetime.now(tz=UTC),
                    backend_name="test",
                    calibration_timestamp=datetime.now(tz=UTC),
                    victim_type="qft",
                    victim_qubits=[0, 1, 2, 3],
                    victim_num_qubits=4,
                    victim_depth=15,
                    victim_2q_gate_density=0.2,
                    attacker_type="single_cnot",
                    attacker_qubits=[5, 6],
                    attacker_num_qubits=2,
                    attacker_size_ratio=0.5,
                    swap_path_distance=i + 1,
                    shots=5000,
                )
            )

        store.record_runs(runs)
        assert len(store.query_runs()) == 5

    def test_parquet_export(self, store):
        run = ExperimentRun(
            timestamp=datetime.now(tz=UTC),
            backend_name="test",
            calibration_timestamp=datetime.now(tz=UTC),
            victim_type="grover",
            victim_qubits=[0, 1],
            victim_num_qubits=2,
            victim_depth=5,
            victim_2q_gate_density=0.1,
            attacker_type="idle",
            attacker_qubits=[3],
            attacker_num_qubits=1,
            attacker_size_ratio=0.5,
            swap_path_distance=2,
            shots=1000,
        )
        store.record_run(run)

        with tempfile.TemporaryDirectory() as tmp:
            pq_path = Path(tmp) / "test.parquet"
            store.export_to_parquet(str(pq_path))
            assert pq_path.exists()
            assert pq_path.stat().st_size > 0


class TestExperimentRunSchema:
    """Tests for the ExperimentRun dataclass."""

    def test_defaults(self):
        run = ExperimentRun(
            timestamp=datetime.now(tz=UTC),
            backend_name="test",
            calibration_timestamp=datetime.now(tz=UTC),
            victim_type="grover",
            victim_qubits=[0, 1],
            victim_num_qubits=2,
            victim_depth=10,
            victim_2q_gate_density=0.3,
            attacker_type="idle",
            attacker_qubits=[3],
            attacker_num_qubits=1,
            attacker_size_ratio=0.5,
            swap_path_distance=2,
            shots=5000,
        )

        assert run.measured_leakage is None
        assert run.predicted_leakage is None
        assert run.job_id == ""
        assert run.hold_out_placement is False
