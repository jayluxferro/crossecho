"""IBM Quantum backend runner via qiskit-ibm-runtime."""

import os
import time
from datetime import UTC, datetime

from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2

from crossecho.runner.base import BackendRunner, JobResult


class IBMBackendRunner(BackendRunner):
    """IBM Quantum backend runner authenticated via IBM_QUANTUM_API_KEY env var.

    Uses the Qiskit Runtime primitives (SamplerV2) for efficient circuit execution.
    Handles session management, retries, and comprehensive metadata logging.
    """

    def __init__(
        self,
        backend_name: str,
        instance: str | None = None,
        api_key: str | None = None,
    ) -> None:
        api_key = api_key or os.environ.get("IBM_QUANTUM_API_KEY", "")
        if not api_key:
            raise ValueError(
                "IBM_QUANTUM_API_KEY environment variable is not set. "
                "Set it or pass api_key to IBMBackendRunner()."
            )

        self._backend_name = backend_name
        self._service = QiskitRuntimeService(
            channel="ibm_quantum_platform",
            token=api_key,
            instance="crn:v1:bluemix:public:quantum-computing:us-east:a/7221ded921194519ab616233348f387c:8bf53556-2f06-472e-be1e-133f86473ea6::",
        )
        self._backend = self._service.backend(backend_name)
        self._coupling_map = self._backend.configuration().coupling_map

    def run(
        self,
        circuits: list[QuantumCircuit],
        shots: int,
        optim_level: int = 1,
    ) -> JobResult:
        transpiled = transpile(
            circuits,
            backend=self._backend,
            optimization_level=optim_level,
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                job_start = time.monotonic()
                sampler = SamplerV2(mode=self._backend)
                job = sampler.run(transpiled, shots=shots)
                result = job.result()
                job_end = time.monotonic()

                counts_list: list[dict[str, int]] = []
                for pub_result in result:
                    # Qiskit 2.x: pub_result.data.c for classical register 'c'
                    if hasattr(pub_result.data, 'meas'):
                        pub_counts = pub_result.data.meas.get_counts()
                    elif hasattr(pub_result.data, 'c'):
                        pub_counts = pub_result.data.c.get_counts()
                    else:
                        pub_counts = list(pub_result.data.get_counts())[0]
                    counts_list.append(pub_counts)

                job_id = job.job_id()
                metrics = job.metrics()
                queue_time = metrics.get("time_in_queue", 0.0)
                exec_time = job_end - job_start

                return JobResult(
                    counts=counts_list,
                    metadata={
                        "shots": shots,
                        "job_id": job_id,
                        "queue_time_s": queue_time,
                        "execution_time_s": exec_time,
                        "calibration_timestamp": datetime.now(tz=UTC),
                        "backend_name": self._backend_name,
                    },
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2**attempt * 5
                    time.sleep(wait)
                    continue
                raise RuntimeError(
                    f"IBM job failed after {max_retries} attempts: {e}"
                ) from e

        raise RuntimeError("IBM job failed")

    def calibration_snapshot(self) -> dict:
        props = self._backend.properties()
        return props.to_dict()

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def coupling_map(self) -> list[tuple[int, int]]:
        return self._coupling_map
