"""Results database: sqlite3 read/write and parquet export."""

import json
import sqlite3
from datetime import datetime

from crossecho.data.schema import ExperimentRun

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS experiment_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    backend_name TEXT NOT NULL,
    calibration_timestamp TEXT NOT NULL,
    victim_type TEXT NOT NULL,
    victim_qubits TEXT NOT NULL,
    victim_num_qubits INTEGER NOT NULL,
    victim_depth INTEGER NOT NULL,
    victim_2q_gate_density REAL NOT NULL,
    attacker_type TEXT NOT NULL,
    attacker_qubits TEXT NOT NULL,
    attacker_num_qubits INTEGER NOT NULL,
    attacker_size_ratio REAL NOT NULL,
    swap_path_distance INTEGER NOT NULL,
    shots INTEGER NOT NULL,
    job_id TEXT NOT NULL DEFAULT '',
    queue_time_s REAL NOT NULL DEFAULT 0.0,
    execution_time_s REAL NOT NULL DEFAULT 0.0,
    predicted_leakage REAL,
    predicted_leakage_std REAL,
    measured_counts_victim_present TEXT NOT NULL DEFAULT '{}',
    measured_counts_victim_absent TEXT NOT NULL DEFAULT '{}',
    measured_leakage REAL,
    hold_out_placement INTEGER NOT NULL DEFAULT 0,
    hold_out_calibration INTEGER NOT NULL DEFAULT 0
);
"""


class ResultsStore:
    """Sqlite-backed results store with parquet export.

    Uses sqlite3 from the stdlib (no SQLAlchemy dependency) for
    transactional inserts during long-running batch jobs.
    """

    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def init_db(self) -> None:
        """Create schema if not exists."""
        conn = self._get_conn()
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()

    def record_run(self, run: ExperimentRun) -> None:
        """Insert a single experiment run."""
        self.record_runs([run])

    def record_runs(self, runs: list[ExperimentRun]) -> None:
        """Insert multiple experiment runs in a transaction."""
        conn = self._get_conn()
        with conn:
            for run in runs:
                conn.execute(
                    """INSERT INTO experiment_runs (
                        timestamp, backend_name, calibration_timestamp,
                        victim_type, victim_qubits, victim_num_qubits,
                        victim_depth, victim_2q_gate_density,
                        attacker_type, attacker_qubits, attacker_num_qubits,
                        attacker_size_ratio, swap_path_distance,
                        shots, job_id, queue_time_s, execution_time_s,
                        predicted_leakage, predicted_leakage_std,
                        measured_counts_victim_present,
                        measured_counts_victim_absent,
                        measured_leakage,
                        hold_out_placement, hold_out_calibration
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )""",
                    (
                        run.timestamp.isoformat(),
                        run.backend_name,
                        run.calibration_timestamp.isoformat(),
                        run.victim_type,
                        json.dumps(run.victim_qubits),
                        run.victim_num_qubits,
                        run.victim_depth,
                        run.victim_2q_gate_density,
                        run.attacker_type,
                        json.dumps(run.attacker_qubits),
                        run.attacker_num_qubits,
                        run.attacker_size_ratio,
                        run.swap_path_distance,
                        run.shots,
                        run.job_id,
                        run.queue_time_s,
                        run.execution_time_s,
                        run.predicted_leakage,
                        run.predicted_leakage_std,
                        json.dumps(run.measured_counts_victim_present),
                        json.dumps(run.measured_counts_victim_absent),
                        run.measured_leakage,
                        int(run.hold_out_placement),
                        int(run.hold_out_calibration),
                    ),
                )

    def query_runs(self, **filters: object) -> list[ExperimentRun]:
        """Query runs with optional column=value filters."""
        conn = self._get_conn()
        query = "SELECT * FROM experiment_runs"
        params: list[object] = []
        if filters:
            clauses = [f"{k} = ?" for k in filters]
            query += " WHERE " + " AND ".join(clauses)
            params = list(filters.values())

        cursor = conn.execute(query, params)
        return [self._row_to_run(row) for row in cursor.fetchall()]

    def export_to_parquet(self, parquet_path: str) -> None:
        """Export all runs to a parquet file for analysis."""
        import pandas as pd

        conn = self._get_conn()
        df = pd.read_sql_query("SELECT * FROM experiment_runs", conn)
        df.to_parquet(parquet_path)

    @property
    def conn(self) -> sqlite3.Connection:
        return self._get_conn()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    @staticmethod
    def _row_to_run(row: sqlite3.Row) -> ExperimentRun:
        """Convert a sqlite3 row to an ExperimentRun."""
        return ExperimentRun(
            timestamp=datetime.fromisoformat(row["timestamp"]),
            backend_name=row["backend_name"],
            calibration_timestamp=datetime.fromisoformat(
                row["calibration_timestamp"]
            ),
            victim_type=row["victim_type"],
            victim_qubits=json.loads(row["victim_qubits"]),
            victim_num_qubits=row["victim_num_qubits"],
            victim_depth=row["victim_depth"],
            victim_2q_gate_density=row["victim_2q_gate_density"],
            attacker_type=row["attacker_type"],
            attacker_qubits=json.loads(row["attacker_qubits"]),
            attacker_num_qubits=row["attacker_num_qubits"],
            attacker_size_ratio=row["attacker_size_ratio"],
            swap_path_distance=row["swap_path_distance"],
            shots=row["shots"],
            job_id=row["job_id"],
            queue_time_s=row["queue_time_s"],
            execution_time_s=row["execution_time_s"],
            predicted_leakage=row["predicted_leakage"],
            predicted_leakage_std=row["predicted_leakage_std"],
            measured_counts_victim_present=json.loads(
                row["measured_counts_victim_present"]
            ),
            measured_counts_victim_absent=json.loads(
                row["measured_counts_victim_absent"]
            ),
            measured_leakage=row["measured_leakage"],
            hold_out_placement=bool(row["hold_out_placement"]),
            hold_out_calibration=bool(row["hold_out_calibration"]),
        )
