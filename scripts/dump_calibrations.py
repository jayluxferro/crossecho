#!/usr/bin/env python
"""Dump IBM Quantum calibration snapshots to data/calibrations/.

Fetches live ``backend.properties()`` for the backends used in the paper and
writes one JSON file per backend, so the calibration snapshots can be archived
alongside the experimental results.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from crossecho.config import IBM_CHANNEL, IBM_INSTANCE, IBM_QUANTUM_API_KEY

BACKENDS = ("ibm_fez", "ibm_marrakesh")
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "calibrations"


def _nduv_to_dict(nduv) -> dict:
    return {
        "name": nduv.name,
        "value": nduv.value,
        "unit": nduv.unit,
        "date": str(nduv.date),
    }


def dump_backend(service, name: str) -> dict:
    backend = service.backend(name)
    props = backend.properties()
    cfg = backend.configuration()
    coupling_map = list(cfg.coupling_map) if cfg.coupling_map is not None else []
    return {
        "backend_name": props.backend_name,
        "backend_version": props.backend_version,
        "num_qubits": cfg.num_qubits,
        "coupling_map": [list(edge) for edge in coupling_map],
        "last_update_date": str(props.last_update_date),
        "fetched_at": datetime.now(tz=UTC).isoformat(),
        "qubits": [[_nduv_to_dict(n) for n in qubit] for qubit in props.qubits],
        "gates": [
            {
                "gate": g.gate,
                "qubits": list(g.qubits),
                "parameters": [_nduv_to_dict(p) for p in g.parameters],
            }
            for g in props.gates
        ],
    }


def main() -> None:
    if not IBM_QUANTUM_API_KEY:
        raise SystemExit("IBM_QUANTUM_API_KEY is not set in the environment.")

    from qiskit_ibm_runtime import QiskitRuntimeService

    service = QiskitRuntimeService(
        channel=IBM_CHANNEL, token=IBM_QUANTUM_API_KEY, instance=IBM_INSTANCE
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for name in BACKENDS:
        snapshot = dump_backend(service, name)
        out_path = OUT_DIR / f"{name}_calibration.json"
        out_path.write_text(json.dumps(snapshot, indent=2))
        print(
            f"wrote {out_path.name} "
            f"({snapshot['num_qubits']} qubits, {len(snapshot['gates'])} gates, "
            f"last_update={snapshot['last_update_date']})"
        )


if __name__ == "__main__":
    main()
