#!/usr/bin/env python
"""Full CrossEcho pipeline: IBM cal → Aer noise model → experiment → evaluation."""
import numpy as np
from datetime import UTC, datetime

# ── IBM calibration ───────────────────────────────────────────────
from qiskit_ibm_runtime import QiskitRuntimeService
from crossecho.config import IBM_CHANNEL, IBM_INSTANCE, IBM_QUANTUM_API_KEY

service = QiskitRuntimeService(
    channel=IBM_CHANNEL, token=IBM_QUANTUM_API_KEY, instance=IBM_INSTANCE,
)
backend = service.backend("ibm_fez")
props = backend.properties()
cfg = backend.configuration()

full_cmap = cfg.coupling_map
all_qubits = set()
for i, j in full_cmap:
    all_qubits.add(i); all_qubits.add(j)
    if len(all_qubits) >= 20: break
all_qubits = sorted(all_qubits)[:20]

t1s, t2s, ro_errs = {}, {}, {}
for q in all_qubits:
    for nduv in props.qubits[q]:
        if nduv.name == "T1": t1s[q] = nduv.value * 1e-6
        elif nduv.name == "T2": t2s[q] = nduv.value * 1e-6
        elif nduv.name == "readout_error": ro_errs[q] = nduv.value

print(f"IBM cal: {len(all_qubits)}q, T1={min(t1s.values())*1e6:.0f}-{max(t1s.values())*1e6:.0f}us, "
      f"T2={min(t2s.values())*1e6:.0f}-{max(t2s.values())*1e6:.0f}us")

from crossecho.model.calibration import CalibrationSnapshot
cal = CalibrationSnapshot(
    backend_name="ibm_fez", timestamp=datetime.now(tz=UTC),
    qubit_frequencies={q: (5.0 + 0.15*q/100) for q in all_qubits},
    anharmonicities={q: -0.3 for q in all_qubits},
    t1_times={q: t1s[q]*1e6 for q in all_qubits},
    t2_times={q: t2s[q]*1e6 for q in all_qubits},
    gate_errors={}, readout_errors=ro_errs,
    coupling_map=[(i,j) for i,j in full_cmap if i in all_qubits and j in all_qubits],
    raw_properties={"source": "ibm_fez"},
)

from crossecho.circuits.victims import LayeredCNOTVictim
from crossecho.circuits.attackers import IdleProbe, SingleCNOTProbe
from crossecho.model.leakage import predict_leakage
from crossecho.model.metrics import tvd
from crossecho.data.schema import ExperimentRun
from qiskit import QuantumCircuit
from qiskit_aer.noise import NoiseModel, thermal_relaxation_error, ReadoutError
from crossecho.runner.aer import AerBackendRunner


def strip_meas(qc):
    out = QuantumCircuit(qc.num_qubits)
    for inst in qc.data:
        if inst.operation.name not in ("measure", "barrier"):
            out.append(inst.operation, inst.qubits, inst.clbits if inst.clbits else ())
    return out


victim_size = 3
runs = []

for distance in [1, 2, 3]:
    for attacker_type in ["idle", "single_cnot"]:
        a_size = 1 if attacker_type == "idle" else 2
        phys_victim = [0, 1, 2]
        gap = distance - 1
        phys_attacker = (
            [victim_size + gap]
            if attacker_type == "idle"
            else [victim_size + gap, victim_size + gap + 1]
        )
        max_q = max(phys_victim + phys_attacker)
        if max_q >= 7:
            continue

        n_total = victim_size + a_size
        v_gen = LayeredCNOTVictim(victim_size, density=0.3, layers=2, seed=distance)
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

        all_phys = phys_victim + phys_attacker
        phys_to_virt = {p: i for i, p in enumerate(all_phys)}

        noise_model = NoiseModel()
        for p in all_phys:
            v = phys_to_virt[p]
            t1, t2 = t1s[p], t2s[p]
            noise_model.add_quantum_error(
                thermal_relaxation_error(t1, t2, 3.5e-8),
                ["id", "rz", "sx", "x", "h"],
                [v],
            )
            p_ro = ro_errs.get(p, 0.015)
            noise_model.add_readout_error(
                ReadoutError([[1 - p_ro, p_ro], [p_ro, 1 - p_ro]]), [v]
            )

        for i in range(len(all_phys) - 1):
            pi, pj = all_phys[i], all_phys[i + 1]
            vi, vj = phys_to_virt[pi], phys_to_virt[pj]
            noise_model.add_quantum_error(
                thermal_relaxation_error(t1s[pi], t2s[pi], 6.8e-8).tensor(
                    thermal_relaxation_error(t1s[pj], t2s[pj], 6.8e-8)
                ),
                ["cz"],
                [vi, vj],
            )

        # NOTE: thermal relaxation (T1/T2) models independent decoherence only.
        # ZZ crosstalk between qubits requires a correlated noise mechanism that
        # Aer's standard NoiseModel does not natively support across arbitrary pairs.
        # The crosstalk signal is measured on real hardware (IBM/Origin), where
        # the physical ZZ coupling is present. Aer with backend noise is used for:
        #   1. Development & pipeline validation
        #   2. Shot pre-budgeting (Phase 4.5)
        #   3. Baseline: TVD ≈ 0 without crosstalk confirms we're measuring real effect

        virt_cmap = [(i, i + 1) for i in range(n_total - 1)]
        runner = AerBackendRunner(
            coupling_map=virt_cmap, noise_model=noise_model, seed=42
        )

        virt_victim = [phys_to_virt[p] for p in phys_victim]
        virt_attacker = [phys_to_virt[p] for p in phys_attacker]

        qc_p = QuantumCircuit(n_total, a_size)
        qc_p.compose(strip_meas(v_gen.circuit), qubits=virt_victim, inplace=True)
        qc_p.compose(strip_meas(a_gen.circuit), qubits=virt_attacker, inplace=True)
        qc_p.measure(virt_attacker, range(a_size))

        qc_a = QuantumCircuit(n_total, a_size)
        qc_a.compose(strip_meas(a_gen.circuit), qubits=virt_attacker, inplace=True)
        qc_a.measure(virt_attacker, range(a_size))

        r_p = runner.run([qc_p], shots=2000)
        r_a = runner.run([qc_a], shots=2000)
        measured = tvd(r_p.counts[0], r_a.counts[0])

        runs.append(
            ExperimentRun(
                timestamp=datetime.now(tz=UTC),
                backend_name="aer_ibm_fez",
                calibration_timestamp=cal.timestamp,
                victim_type="layered_cnot",
                victim_qubits=phys_victim,
                victim_num_qubits=victim_size,
                victim_depth=v_gen.depth,
                victim_2q_gate_density=v_gen.two_qubit_gate_density,
                attacker_type=attacker_type,
                attacker_qubits=phys_attacker,
                attacker_num_qubits=a_size,
                attacker_size_ratio=a_size / victim_size,
                swap_path_distance=distance,
                shots=2000,
                predicted_leakage=l_pred,
                predicted_leakage_std=l_std,
                measured_counts_victim_present=r_p.counts[0],
                measured_counts_victim_absent=r_a.counts[0],
                measured_leakage=measured,
            )
        )

# ── Evaluate ──────────────────────────────────────────────────────
from crossecho.model.evaluation import (
    evaluate_forecasting,
    run_ablation,
    split_hold_out_placements,
)

cal_snapshots = {cal.timestamp: cal}
train, hold_out = split_hold_out_placements(runs, seed=42)
all_runs = train + hold_out
results = evaluate_forecasting(all_runs, cal_snapshots)
ablations = run_ablation(all_runs, cal_snapshots)

null_rmse = ablations.get("null_constant", {}).get("rmse", 1.0)
full_rmse = ablations.get("full_model", {}).get("rmse", 1.0)
imp = (1 - full_rmse / max(null_rmse, 1e-9)) * 100

print(f"\n=== FORECASTING RESULTS (Aer + real ibm_fez noise) ===")
print(f"Cells: {results['n_predictions']}")
print(f"Overall RMSE:              {results['overall_rmse']:.4f}")
print(f"Placement hold-out RMSE:   {results['placement_rmse']:.4f}")
print(f"Null model RMSE:           {null_rmse:.4f}")
print(f"Full model improvement:    {imp:.0f}%")
print(f"\n=== ALL CELLS ===")
for run in sorted(runs, key=lambda r: r.measured_leakage or 0, reverse=True):
    print(
        f"  {run.attacker_type:14s}  d={run.swap_path_distance}  "
        f"pred={run.predicted_leakage:.4f}+/-{run.predicted_leakage_std:.4f}  "
        f"meas={run.measured_leakage:.4f}  HO={run.hold_out_placement}"
    )

yt = [round(v, 4) for v in results["y_true"].tolist()]
yp = [round(v, 4) for v in results["y_pred"].tolist()]
print(f"\ny_true: {yt}")
print(f"y_pred: {yp}")
print(f"RMSE: {results['overall_rmse']:.4f}")
