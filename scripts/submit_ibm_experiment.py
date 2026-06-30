#!/usr/bin/env python
"""Submit CrossEcho experiment to IBM Quantum hardware.

Builds the experiment matrix, predicts leakage, transpiles circuits,
submits as batched jobs, and saves job IDs for later result checking.

Usage:
    uv run python scripts/submit_ibm_experiment.py
    uv run python scripts/submit_ibm_experiment.py --check  # check results
"""
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

# ── Config ─────────────────────────────────────────────────────────
BACKEND_NAME = "ibm_marrakesh"
SHOTS_PER_CELL = 2000
JOBS_FILE = Path(f"data/ibm_jobs_{BACKEND_NAME}.json")
RESULTS_FILE = Path(f"data/ibm_results_{BACKEND_NAME}.json")


# ── IBM Connection ─────────────────────────────────────────────────
def get_service():
    from qiskit_ibm_runtime import QiskitRuntimeService

    return QiskitRuntimeService(
        channel="ibm_quantum_platform",
        token=os.environ["IBM_QUANTUM_API_KEY"],
        instance="crn:v1:bluemix:public:quantum-computing:us-east:a/7221ded921194519ab616233348f387c:8bf53556-2f06-472e-be1e-133f86473ea6::",
    )


def check_results():
    """Check submitted job statuses and collect results."""
    if not JOBS_FILE.exists():
        print(f"No jobs file at {JOBS_FILE}")
        return

    service = get_service()
    jobs_data = json.loads(JOBS_FILE.read_text())

    from crossecho.model.metrics import tvd

    results = []
    for entry in jobs_data:
        job_id = entry["job_id"]
        try:
            job = service.job(job_id)
            status = job.status()
            print(f"  {job_id}: {status}")

            if status == "DONE":
                result = job.result()
                counts_present = []
                counts_absent = []
                for pub_result in result:
                    counts_present.append(
                        pub_result.data.meas_present.get_counts()
                    )
                    counts_absent.append(
                        pub_result.data.meas_absent.get_counts()
                    )

                # Compute TVD
                for i, cell_meta in enumerate(entry["cells"]):
                    measured = tvd(counts_present[i], counts_absent[i])
                    cell_meta["measured_tvd"] = float(measured)
                    cell_meta["counts_present"] = counts_present[i]
                    cell_meta["counts_absent"] = counts_absent[i]
                    print(f"    cell {i}: TVD={measured:.4f}")

                results.append(
                    {
                        "job_id": job_id,
                        "status": "DONE",
                        "cells": entry["cells"],
                    }
                )
            elif status in ("CANCELLED", "ERROR"):
                print(f"    Job failed: {status}")
                results.append({"job_id": job_id, "status": status, "cells": []})
            else:
                results.append(
                    {"job_id": job_id, "status": status, "cells": []}
                )

        except Exception as e:
            print(f"  {job_id}: ERROR - {e}")
            results.append({"job_id": job_id, "status": f"ERROR: {e}", "cells": []})

    RESULTS_FILE.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to {RESULTS_FILE}")


def build_and_submit():
    """Build experiment matrix and submit to IBM hardware."""
    from qiskit import QuantumCircuit, transpile

    service = get_service()
    backend = service.backend(BACKEND_NAME)
    print(f"Backend: {backend.name} ({backend.configuration().num_qubits} qubits)")

    # ── Get calibration ────────────────────────────────────────────
    props = backend.properties()
    cfg = backend.configuration()
    cmap = cfg.coupling_map

    # Pick a small connected subgraph near the center of the chip
    # Use first 8-qubit connected component from coupling map
    connected_qubits = set()
    for i, j in cmap:
        connected_qubits.add(i)
        connected_qubits.add(j)
        if len(connected_qubits) >= 8:
            break
    sub_qubits = sorted(connected_qubits)[:8]
    sub_cmap = [(i, j) for i, j in cmap if i in sub_qubits and j in sub_qubits]

    # Extract calibration
    t1s, t2s, ro_errs = {}, {}, {}
    for q in sub_qubits:
        for nduv in props.qubits[q]:
            if nduv.name == "T1":
                t1s[q] = nduv.value * 1e-6
            elif nduv.name == "T2":
                t2s[q] = nduv.value * 1e-6
            elif nduv.name == "readout_error":
                ro_errs[q] = nduv.value

    print(f"Subgraph: {len(sub_qubits)}q, {len(sub_cmap)} edges")
    print(
        f"T1: {min(t1s.values())*1e6:.0f}-{max(t1s.values())*1e6:.0f}us | "
        f"T2: {min(t2s.values())*1e6:.0f}-{max(t2s.values())*1e6:.0f}us"
    )
    print(f"Sub-qubits: {sub_qubits}")
    print(f"Sub-cmap: {sub_cmap}")

    # ── Build calibration snapshot ─────────────────────────────────
    from crossecho.model.calibration import CalibrationSnapshot

    cal = CalibrationSnapshot(
        backend_name=BACKEND_NAME,
        timestamp=datetime.now(tz=UTC),
        qubit_frequencies={q: 5.0 + 0.15 * (q % 20) for q in sub_qubits},
        anharmonicities={q: -0.3 for q in sub_qubits},
        t1_times={q: t1s[q] * 1e6 for q in sub_qubits},
        t2_times={q: t2s[q] * 1e6 for q in sub_qubits},
        gate_errors={},
        readout_errors=ro_errs,
        coupling_map=sub_cmap,
        raw_properties={"source": BACKEND_NAME},
    )

    # ── Build experiment matrix ────────────────────────────────────
    from crossecho.model.leakage import predict_leakage
    from crossecho.circuits.victims import LayeredCNOTVictim
    from crossecho.circuits.attackers import IdleProbe, SingleCNOTProbe

    # Place victim on 3 contiguous qubits, attacker at varying distances
    # Reserve qubit 0-2 for victim, then 3,4,5 at increasing distance
    matrix = []
    for distance in [1, 2]:
        for attacker_type in ["idle", "single_cnot"]:
            a_size = 1 if attacker_type == "idle" else 2
            phys_victim = sub_qubits[:3]  # first 3 qubits

            gap = distance - 1
            a_start = 3 + gap
            if a_start + a_size > len(sub_qubits):
                continue
            phys_attacker = sub_qubits[a_start : a_start + a_size]

            # Verify connectivity via coupling map
            # SWAP path must exist
            from crossecho.model.coupling import effective_zz_path
            from crossecho.model.perturbation import compute_all_pairwise_zz

            zz_pairs = compute_all_pairwise_zz(
                sub_cmap,
                cal.qubit_frequencies,
                cal.anharmonicities,
            )
            zeta_eff, d = effective_zz_path(
                sub_cmap,
                zz_pairs,
                phys_attacker,
                phys_victim,
                frequencies=cal.qubit_frequencies,
            )

            if d < 0:
                print(f"  SKIP: no path between {phys_victim} and {phys_attacker}")
                continue

            v_gen = LayeredCNOTVictim(3, density=0.3, layers=2, seed=distance)
            v_gen.generate()
            a_gen = (
                IdleProbe(a_size)
                if attacker_type == "idle"
                else SingleCNOTProbe(a_size)
            )
            a_gen.generate()

            l_pred, l_std = predict_leakage(
                calibration=cal,
                victim_qubits=phys_victim,
                attacker_qubits=phys_attacker,
                victim_2q_gate_density=v_gen.two_qubit_gate_density,
                victim_depth=v_gen.depth,
                attacker_type=attacker_type,
                n_monte_carlo=100,
            )

            n_total = len(sub_qubits)

            # Strip measurements before composing
            def strip_meas(qc):
                out = QuantumCircuit(qc.num_qubits)
                for inst in qc.data:
                    if inst.operation.name not in ("measure", "barrier"):
                        out.append(
                            inst.operation,
                            inst.qubits,
                            inst.clbits if inst.clbits else (),
                        )
                return out

            v_clean = strip_meas(v_gen.circuit)
            a_clean = strip_meas(a_gen.circuit)

            # Victim present: both circuits, measure only attacker
            qc_present = QuantumCircuit(n_total, a_size)
            qc_present.compose(v_clean, qubits=phys_victim, inplace=True)
            qc_present.compose(a_clean, qubits=phys_attacker, inplace=True)
            qc_present.measure(phys_attacker, range(a_size))

            # Victim absent: only attacker, measure attacker
            qc_absent = QuantumCircuit(n_total, a_size)
            qc_absent.compose(a_clean, qubits=phys_attacker, inplace=True)
            qc_absent.measure(phys_attacker, range(a_size))

            matrix.append(
                {
                    "victim_qubits": phys_victim,
                    "attacker_qubits": phys_attacker,
                    "attacker_type": attacker_type,
                    "swap_path_distance": d,
                    "predicted_leakage": l_pred,
                    "predicted_leakage_std": l_std,
                    "qc_present": qc_present,
                    "qc_absent": qc_absent,
                }
            )

            print(
                f"  {attacker_type:14s}  v={phys_victim}  a={phys_attacker}  "
                f"d={d}  pred_L={l_pred:.4f}+/-{l_std:.4f}"
            )

    if not matrix:
        print("No valid cells in matrix — check coupling map connectivity.")
        return

    # ── Submit as batched jobs ─────────────────────────────────────
    from qiskit_ibm_runtime import SamplerV2
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager

    pm = generate_preset_pass_manager(optimization_level=1, backend=backend)

    all_circuits = []
    for cell in matrix:
        all_circuits.append(cell["qc_present"])
        all_circuits.append(cell["qc_absent"])

    print(f"\nTranspiling {len(all_circuits)} circuits for {backend.name}...")
    transpiled = transpile(all_circuits, backend=backend, optimization_level=1)
    print(f"Transpiled. Submitting as single batch job...")

    sampler = SamplerV2(mode=backend)
    job = sampler.run(transpiled, shots=SHOTS_PER_CELL)
    job_id = job.job_id()

    print(f"\n✓ Job submitted!")
    print(f"  Job ID: {job_id}")
    print(f"  Backend: {backend.name}")
    print(f"  Circuits: {len(transpiled)}")
    print(f"  Shots per circuit: {SHOTS_PER_CELL}")
    print(f"  Estimated QPU time: ~{len(transpiled) * SHOTS_PER_CELL * 5e-6:.1f}s")
    print(f"\n  Check status: uv run python scripts/submit_ibm_experiment.py --check")

    # Save job metadata
    jobs_data = [
        {
            "job_id": job_id,
            "backend": BACKEND_NAME,
            "submitted_at": datetime.now(tz=UTC).isoformat(),
            "shots": SHOTS_PER_CELL,
            "num_circuits": len(transpiled),
            "cells": [
                {k: v for k, v in cell.items() if k not in ("qc_present", "qc_absent")}
                for cell in matrix
            ],
        }
    ]
    JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    JOBS_FILE.write_text(json.dumps(jobs_data, indent=2, default=str))
    print(f"  Job metadata saved to: {JOBS_FILE}")


# ── Main ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    if "--check" in sys.argv:
        check_results()
    else:
        build_and_submit()
