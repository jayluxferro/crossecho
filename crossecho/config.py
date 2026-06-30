"""Configuration: environment variables and project defaults."""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
RESULTS_PATH = DATA_DIR / "results.parquet"
CALIBRATIONS_DIR = DATA_DIR / "calibrations"

# API keys (from environment)
IBM_QUANTUM_API_KEY = os.environ.get("IBM_QUANTUM_API_KEY", "")
ORIGIN_QC_API_KEY = os.environ.get("ORIGIN_QC_API_KEY", "")

# IBM Quantum defaults
IBM_DEFAULT_INSTANCE = os.environ.get("IBM_INSTANCE", "ibm-q/open/main")

# Shot budgeting
DEFAULT_TARGET_CI_WIDTH = 0.02  # target CI half-width on TVD [0,1] scale
MIN_SHOTS_PER_CELL = 1000
MAX_SHOTS_PER_CELL = 32000

# Experiment defaults
DEFAULT_VICTIM_QUBITS_RANGE = (3, 8)
DEFAULT_ATTACKER_SIZE_RATIOS = [0.06, 0.125, 0.25, 0.5]
DEFAULT_CALIBRATION_SNAPSHOTS = 3

# Model defaults
ANALYTIC_RMSE_THRESHOLD = 0.15  # fallback to ML if analytic model RMSE exceeds this
ERROR_BAR_COVERAGE_TARGET = 0.95
