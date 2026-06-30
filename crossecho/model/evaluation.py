"""Model evaluation: hold-out splits, ablation, error bar calibration.

Implements the dual hold-out design that is CrossEcho's key
novelty mechanism:
- Hold-out placements: exclude specific qubit placement configurations
- Hold-out calibration days: exclude entire calibration snapshots from training
"""

from __future__ import annotations

import numpy as np

from crossecho.model.leakage import predict_leakage
from crossecho.model.metrics import forecasting_rmse, tvd


def split_hold_out_placements(
    runs: list,
    hold_out_placement_configs: set[tuple[int, ...]] | None = None,
    seed: int = 42,
) -> tuple[list, list]:
    """Split runs into train and hold-out placement sets.

    Args:
        runs: List of ExperimentRun objects.
        hold_out_placement_configs: Specific (victim_qubits, attacker_qubits) tuples
                                   to hold out. If None, randomly selects ~20%.
        seed: Random seed.

    Returns:
        (train_runs, hold_out_runs) tuple.
    """
    rng = np.random.default_rng(seed)

    if hold_out_placement_configs is None:
        # Auto-select ~20% of unique placement configs
        configs = set()
        for run in runs:
            key = (tuple(run.victim_qubits), tuple(run.attacker_qubits))
            configs.add(key)

        n_hold = max(1, int(len(configs) * 0.2))
        config_list = sorted(configs)
        rng.shuffle(config_list)
        hold_out_placement_configs = set(config_list[:n_hold])

    train = []
    hold_out = []
    for run in runs:
        key = (tuple(run.victim_qubits), tuple(run.attacker_qubits))
        if key in hold_out_placement_configs:
            run.hold_out_placement = True
            hold_out.append(run)
        else:
            train.append(run)

    return train, hold_out


def split_hold_out_calibration(
    runs: list,
    hold_out_cal_timestamps: set | None = None,
) -> tuple[list, list]:
    """Split runs into train and hold-out calibration day sets.

    Args:
        runs: List of ExperimentRun objects.
        hold_out_cal_timestamps: Specific calibration timestamps to hold out.
                                 If None, holds out the last calibration day.

    Returns:
        (train_runs, hold_out_runs) tuple.
    """
    if hold_out_cal_timestamps is None:
        timestamps = sorted({run.calibration_timestamp for run in runs})
        if len(timestamps) <= 1:
            return runs, []
        hold_out_cal_timestamps = {timestamps[-1]}

    train = []
    hold_out = []
    for run in runs:
        if run.calibration_timestamp in hold_out_cal_timestamps:
            run.hold_out_calibration = True
            hold_out.append(run)
        else:
            train.append(run)

    return train, hold_out


def compute_measured_leakage(
    run: ExperimentRun,  # noqa: F821
) -> float:
    """Compute measured TVD from recorded counts."""
    if run.measured_leakage is not None:
        return run.measured_leakage

    present = run.measured_counts_victim_present
    absent = run.measured_counts_victim_absent

    if not present or not absent:
        return 0.0

    measured = tvd(present, absent)
    run.measured_leakage = measured
    return measured


def evaluate_forecasting(
    analytics_runs: list,
    calibration_snapshots: dict,
) -> dict:
    """Evaluate the analytic model's forecasting performance.

    For each run, uses predict_leakage() with the appropriate calibration
    snapshot and compares against measured leakage.

    Args:
        analytics_runs: List of ExperimentRun objects with measured counts.
        calibration_snapshots: Dict mapping calibration_timestamp → CalibrationSnapshot.

    Returns:
        Dict with keys: overall_rmse, placement_rmse, calibration_rmse,
        y_true, y_pred, predictions.
    """
    y_true = []
    y_pred = []

    for run in analytics_runs:
        cal = calibration_snapshots.get(run.calibration_timestamp)
        if cal is None:
            continue

        l_pred, _ = predict_leakage(
            calibration=cal,
            victim_qubits=run.victim_qubits,
            attacker_qubits=run.attacker_qubits,
            victim_2q_gate_density=run.victim_2q_gate_density,
            victim_depth=run.victim_depth,
            attacker_type=run.attacker_type,
            n_monte_carlo=100,
        )

        l_measured = compute_measured_leakage(run)
        run.predicted_leakage = l_pred
        run.measured_leakage = l_measured

        y_true.append(l_measured)
        y_pred.append(l_pred)

    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)

    overall_rmse = forecasting_rmse(y_true_arr, y_pred_arr)

    # Per-hold-out-type RMSE
    placement_runs = [r for r in analytics_runs if r.hold_out_placement]
    cal_runs = [r for r in analytics_runs if r.hold_out_calibration]

    placement_rmse = 0.0
    if placement_runs:
        p_true = np.array([r.measured_leakage or 0.0 for r in placement_runs])
        p_pred = np.array([r.predicted_leakage or 0.0 for r in placement_runs])
        placement_rmse = forecasting_rmse(p_true, p_pred)

    calibration_rmse = 0.0
    if cal_runs:
        c_true = np.array([r.measured_leakage or 0.0 for r in cal_runs])
        c_pred = np.array([r.predicted_leakage or 0.0 for r in cal_runs])
        calibration_rmse = forecasting_rmse(c_true, c_pred)

    return {
        "overall_rmse": overall_rmse,
        "placement_rmse": placement_rmse,
        "calibration_rmse": calibration_rmse,
        "y_true": y_true_arr,
        "y_pred": y_pred_arr,
        "n_predictions": len(y_true),
    }


def run_ablation(
    analytics_runs: list,
    calibration_snapshots: dict,
) -> dict:
    """Run ablation experiments comparing model variants.

    Returns:
        Dict mapping model_name → {"rmse": float, "type": str}.
    """
    # Null model: predict constant mean leakage
    y_true_null = []
    y_pred_null = []
    for run in analytics_runs:
        l_measured = compute_measured_leakage(run)
        if l_measured is not None:
            y_true_null.append(l_measured)
            y_pred_null.append(0.1)  # constant baseline

    null_rmse = forecasting_rmse(
        np.array(y_true_null), np.array(y_pred_null)
    ) if y_true_null else 1.0

    # Full model
    full = evaluate_forecasting(analytics_runs, calibration_snapshots)

    return {
        "null_constant": {"rmse": null_rmse, "type": "ablation"},
        "full_model": {"rmse": full["overall_rmse"], "type": "full"},
    }
