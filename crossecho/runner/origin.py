"""Origin Quantum Cloud backend runner via pyqpanda3."""

import os
import time
from datetime import UTC, datetime

from crossecho.runner.base import BackendRunner, JobResult


class OriginBackendRunner(BackendRunner):
    """Origin Quantum Cloud backend runner.

    Connects to Origin Quantum Cloud (originqc.com.cn) via pyqpanda3.
    Supports real quantum chips (WK_C180 superconducting, HanYuan_01 optical)
    and simulators (full_amplitude, partial_amplitude, single_amplitude).

    Auth via ORIGIN_QC_API_KEY environment variable.
    """

    def __init__(
        self,
        backend_name: str,
        api_key: str | None = None,
    ) -> None:
        """Initialize Origin backend runner.

        Args:
            backend_name: Origin backend name (e.g., "WK_C180", "full_amplitude").
            api_key: Origin API key. Defaults from ORIGIN_QC_API_KEY env.

        Raises:
            ValueError: If no API key is available.
        """
        from pyqpanda3.qcloud import QCloudService

        api_key = api_key or os.environ.get("ORIGIN_QC_API_KEY", "")
        if not api_key:
            raise ValueError(
                "ORIGIN_QC_API_KEY environment variable is not set. "
                "Set it or pass api_key to OriginBackendRunner()."
            )

        self._backend_name = backend_name
        self._service = QCloudService(api_key=api_key)
        self._backend = self._service.backend(backend_name)

    def run(
        self,
        circuits: list,
        shots: int,
        optim_level: int = 1,
    ) -> JobResult:
        """Execute circuits on the Origin Quantum Cloud backend.

        Circuits must be pyqpanda3 QProg objects or Qiskit QuantumCircuit
        objects that can be converted.

        Args:
            circuits: List of pyqpanda3 QProg objects.
            shots: Number of shots per circuit.
            optim_level: Ignored for Origin (no transpiler optimization).

        Returns:
            JobResult with counts and metadata.
        """
        from pyqpanda3.core import QProg
        from pyqpanda3.qcloud import QCloudJob

        job_start = time.monotonic()
        all_counts: list[dict[str, int]] = []
        job_ids: list[str] = []

        for circuit in circuits:
            if isinstance(circuit, QProg):
                prog = circuit
            else:
                # Assume it's a pyqpanda3-compatible circuit
                prog = circuit

            job: QCloudJob = self._backend.run(prog, shots=shots)
            result = job.result()

            # pyqpanda3 v0.3.x: get_counts() may return empty;
            # use get_probs() and convert to counts
            raw_counts = result.get_counts()
            if raw_counts:
                counts = raw_counts
            else:
                probs = result.get_probs()
                counts = {k: round(v * shots) for k, v in probs.items()}

            job_ids.append(job.task_id if hasattr(job, "task_id") else "origin_job")

            all_counts.append(counts)

        elapsed = time.monotonic() - job_start

        return JobResult(
            counts=all_counts,
            metadata={
                "shots": shots,
                "job_id": ",".join(job_ids),
                "queue_time_s": 0.0,
                "execution_time_s": elapsed,
                "calibration_timestamp": datetime.now(tz=UTC),
                "backend_name": self._backend_name,
            },
        )

    def calibration_snapshot(self) -> dict:
        """Return chip info as calibration snapshot."""
        try:
            ci = self._backend.chip_info
            return {
                "backend_name": self._backend_name,
                "chip_id": getattr(ci, "chip_id", "unknown"),
                "source": "origin_qcloud",
            }
        except Exception:
            return {"backend_name": self._backend_name, "source": "origin_qcloud"}

    @property
    def backend_name(self) -> str:
        return self._backend_name
