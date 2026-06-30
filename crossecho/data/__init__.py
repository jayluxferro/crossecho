"""Experiment data management: schema, store, and matrix builder."""

from crossecho.data.experiment import ExperimentCell, build_experiment_matrix
from crossecho.data.schema import ExperimentRun
from crossecho.data.store import ResultsStore

__all__ = ["ExperimentRun", "ResultsStore", "ExperimentCell", "build_experiment_matrix"]
