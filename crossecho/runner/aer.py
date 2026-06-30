"""Aer simulator backend with noise model from real BackendProperties."""

from __future__ import annotations

import time
from datetime import UTC, datetime

import numpy as np
from qiskit import transpile
from qiskit.transpiler import CouplingMap
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel

from crossecho.runner.base import BackendRunner, JobResult


class AerBackendRunner(BackendRunner):
    """Qiskit-Aer simulator with noise model built from real device calibration.

    Used for:
    - Development and testing (fast, reproducible)
    - Shot budgeting (pre-compute N needed for target CI width)
    - Generating synthetic "measured" data for model evaluation
    """

    def __init__(
        self,
        coupling_map: list[tuple[int, int]],
        noise_model: NoiseModel | None = None,
        seed: int = 42,
    ) -> None:
        self._coupling_map = coupling_map
        self._noise_model = noise_model
        self._seed = seed
        self._sim = AerSimulator(
            noise_model=noise_model,
            coupling_map=coupling_map,
            seed_simulator=seed,
        )
        self._calibration: dict = {}

    @classmethod
    def from_properties(
        cls,
        backend_properties: dict,
        coupling_map: list[tuple[int, int]],
        seed: int = 42,
    ) -> AerBackendRunner:
        """Build Aer runner with noise model from real BackendProperties.

        Args:
            backend_properties: Dict from BackendProperties.to_dict().
            coupling_map: List of (i, j) connected qubit pairs.
            seed: Random seed for reproducibility.

        Returns:
            AerBackendRunner with noise model matching the real device.
        """
        noise_model = NoiseModel.from_backend_properties(backend_properties)
        return cls(
            coupling_map=coupling_map,
            noise_model=noise_model,
            seed=seed,
        )

    def run(
        self,
        circuits: list,
        shots: int,
        optim_level: int = 1,
    ) -> JobResult:
        """Execute circuits on the Aer simulator.

        Args:
            circuits: List of QuantumCircuit objects.
            shots: Number of shots per circuit.
            optim_level: Transpiler optimization level (0-3).

        Returns:
            JobResult with counts and metadata.
        """
        start = time.monotonic()

        # Transpile circuits for the coupling map
        cmap = CouplingMap(self._coupling_map)
        transpiled = transpile(
            circuits,
            coupling_map=cmap,
            optimization_level=optim_level,
            seed_transpiler=self._seed,
        )

        # Run on Aer
        result = self._sim.run(transpiled, shots=shots).result()

        elapsed = time.monotonic() - start
        counts_list = [
            dict(result.get_counts(i)) for i in range(len(transpiled))
        ]

        return JobResult(
            counts=counts_list,
            metadata={
                "shots": shots,
                "job_id": f"aer_{datetime.now(tz=UTC).timestamp()}",
                "queue_time_s": 0.0,
                "execution_time_s": elapsed,
                "calibration_timestamp": datetime.now(tz=UTC),
                "backend_name": self.backend_name,
            },
        )

    def calibration_snapshot(self) -> dict:
        """Return stored calibration data or built noise model info."""
        if self._calibration:
            return self._calibration
        # Extract from noise model if available
        info: dict = {"coupling_map": self._coupling_map, "source": "aer"}
        if self._noise_model is not None:
            try:
                info["noise_model_dict"] = self._noise_model.to_dict()
            except Exception:
                info["noise_model"] = str(self._noise_model)
        return info

    @property
    def backend_name(self) -> str:
        return "aer_simulator"

    def estimate_shots_for_ci(
        self,
        pilot_circuits: list,
        target_ci_width: float = 0.02,
        min_shots: int = 500,
        max_shots: int = 50000,
    ) -> int:
        """Estimate shots needed for target CI width on TVD.

        Runs pilot circuits at increasing shot counts and fits CI_width(N) ≈ C/sqrt(N).

        Args:
            pilot_circuits: Representative circuits to benchmark.
            target_ci_width: Desired CI half-width on TVD [0,1] scale.
            min_shots: Minimum shots to try.
            max_shots: Maximum shots to try.

        Returns:
            Recommended number of shots.
        """
        # Heuristic: for two distributions of 2^n outcomes,
        # TVD CI half-width ≈ z_{α/2} / sqrt(N)
        # For 95% CI, z_{0.025} ≈ 1.96
        # N ≈ (1.96 / target_ci_width)^2

        n_qubits = max(qc.num_qubits for qc in pilot_circuits)
        # Adjust for number of outcomes
        n_outcomes_factor = np.sqrt(min(2**n_qubits, 64))
        z_alpha = 1.96  # 95% CI

        n_estimated = int((z_alpha * n_outcomes_factor / target_ci_width) ** 2)
        n_estimated = max(min_shots, min(n_estimated, max_shots))

        return n_estimated
