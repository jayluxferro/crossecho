"""Backend runner abstraction over Aer, IBM, and Origin QPUs."""

from crossecho.runner.aer import AerBackendRunner
from crossecho.runner.base import BackendRunner, JobResult

__all__ = ["BackendRunner", "JobResult", "AerBackendRunner"]
