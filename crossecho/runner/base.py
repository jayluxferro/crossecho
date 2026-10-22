"""Backend runner abstract base class."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class JobResult:
    """Result of running circuits on a backend."""

    counts: list[dict[str, int]]
    metadata: dict = field(default_factory=dict)
    # metadata typically contains: shots, job_id, queue_time_s, execution_time_s,
    # calibration_timestamp, backend_name


class BackendRunner(ABC):
    """Abstract interface for quantum backends (Aer, IBM, Origin)."""

    @abstractmethod
    def run(
        self,
        circuits: list,
        shots: int,
        optim_level: int = 1,
    ) -> JobResult:
        """Execute circuits and return measurement counts."""

    @abstractmethod
    def calibration_snapshot(self) -> dict:
        """Return a snapshot of the current backend calibration."""

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend identifier."""
