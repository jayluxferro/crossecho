"""Data schemas for experiment runs and calibration snapshots."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExperimentRun:
    """One cell in the experiment matrix: a single (victim, attacker, placement) run."""

    timestamp: datetime
    backend_name: str
    calibration_timestamp: datetime

    # Victim circuit
    victim_type: str
    victim_qubits: list[int]
    victim_num_qubits: int
    victim_depth: int
    victim_2q_gate_density: float

    # Attacker circuit
    attacker_type: str
    attacker_qubits: list[int]
    attacker_num_qubits: int
    attacker_size_ratio: float  # attacker_qubits / victim_qubits

    # Placement
    swap_path_distance: int

    # Execution
    shots: int
    job_id: str = ""
    queue_time_s: float = 0.0
    execution_time_s: float = 0.0

    # Model prediction (set before running)
    predicted_leakage: float | None = None
    predicted_leakage_std: float | None = None

    # Measurements (set after running)
    measured_counts_victim_present: dict[str, int] = field(default_factory=dict)
    measured_counts_victim_absent: dict[str, int] = field(default_factory=dict)
    measured_leakage: float | None = None

    # Hold-out flags
    hold_out_placement: bool = False
    hold_out_calibration: bool = False


@dataclass
class CalibrationSnapshot:
    """Parsed device calibration data for the leakage model."""

    backend_name: str
    timestamp: datetime
    qubit_frequencies: dict[int, float]  # qubit -> ω (GHz)
    anharmonicities: dict[int, float]  # qubit -> α (GHz), = -E_C
    t1_times: dict[int, float]  # qubit -> T1 (µs)
    t2_times: dict[int, float]  # qubit -> T2 (µs)
    gate_errors: dict[tuple[int, int], float]  # qubit pair -> 2Q gate error rate
    readout_errors: dict[int, float]  # qubit -> readout error probability
    coupling_map: list[tuple[int, int]]  # physically connected qubit pairs
    raw_properties: dict = field(default_factory=dict)  # full backend.properties() dump
