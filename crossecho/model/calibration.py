"""Calibration snapshot parsing: backend.properties() → model inputs.

IBM Qiskit's BackendProperties provides qubit properties (T1, T2, frequency,
anharmonicity, readout error) and gate properties (gate error, gate length).

This module parses the nested dict structure into a flat CalibrationSnapshot
suitable for the leakage model.
"""

from datetime import UTC, datetime

from crossecho.data.schema import CalibrationSnapshot


def parse_backend_properties(
    backend_name: str,
    backend_properties: dict,
    coupling_map: list[tuple[int, int]],
) -> CalibrationSnapshot:
    """Parse qiskit BackendProperties into a structured CalibrationSnapshot.

    Extracts qubit frequencies ω_i, anharmonicities α_i, T1/T2 times,
    two-qubit gate error rates, and readout error probabilities.

    The backend_properties dict is typically obtained via:
        props = backend.properties()
        props_dict = props.to_dict()

    Args:
        backend_name: Human-readable backend name (e.g., "ibm_brisbane").
        backend_properties: Dictionary from BackendProperties.to_dict().
        coupling_map: List of (i, j) physically connected qubit pairs.

    Returns:
        CalibrationSnapshot with parsed model inputs.
    """
    qubits_data = backend_properties.get("qubits", [])
    gates_data = backend_properties.get("gates", [])

    frequencies: dict[int, float] = {}
    anharmonicities: dict[int, float] = {}
    t1_times: dict[int, float] = {}
    t2_times: dict[int, float] = {}
    readout_errors: dict[int, float] = {}
    gate_errors: dict[tuple[int, int], float] = {}

    for qubit_idx, qubit_info in enumerate(qubits_data):
        # Each qubit entry is a list of [NDValue, NDValue, ...] for each property
        for prop in qubit_info:
            name = prop.get("name", "")
            value = prop.get("value", 0.0)
            if isinstance(value, (int, float)):
                val = float(value)
                if name == "T1":
                    t1_times[qubit_idx] = val
                elif name == "T2":
                    t2_times[qubit_idx] = val
                elif name == "frequency":
                    frequencies[qubit_idx] = val / 1e9  # Hz → GHz
                elif name == "anharmonicity":
                    anharmonicities[qubit_idx] = val / 1e9  # Hz → GHz
                elif name == "readout_error":
                    readout_errors[qubit_idx] = val

    # If anharmonicities weren't directly available, estimate from E_C
    # Typical transmon anharmonicity: -E_C ≈ -200 to -350 MHz
    for q in frequencies:
        if q not in anharmonicities:
            anharmonicities[q] = -0.3  # default -300 MHz in GHz

    # Parse gate properties for two-qubit gate error rates
    for gate_entry in gates_data:
        gate_name = gate_entry.get("gate", "")
        qubits = gate_entry.get("qubits", [])
        if gate_name in ("cx", "ecr", "cz") and len(qubits) == 2:
            # Each gate has parameters list
            params = gate_entry.get("parameters", [])
            for p in params:
                if p.get("name") == "gate_error":
                    gate_errors[(qubits[0], qubits[1])] = float(p.get("value", 0.0))
                    gate_errors[(qubits[1], qubits[0])] = float(p.get("value", 0.0))

    return CalibrationSnapshot(
        backend_name=backend_name,
        timestamp=datetime.now(tz=UTC),
        qubit_frequencies=frequencies,
        anharmonicities=anharmonicities,
        t1_times=t1_times,
        t2_times=t2_times,
        gate_errors=gate_errors,
        readout_errors=readout_errors,
        coupling_map=coupling_map,
        raw_properties=backend_properties,
    )


def calibration_from_aer(
    backend_name: str,
    noise_model_info: dict,
    coupling_map: list[tuple[int, int]],
) -> CalibrationSnapshot:
    """Create a CalibrationSnapshot from Aer noise model parameters.

    This is a convenience for building model inputs from simulated noise
    data when real hardware isn't available.

    Args:
        backend_name: Identifier for the simulated backend.
        noise_model_info: Dict with optional keys: frequencies, anharmonicities,
                         t1, t2, gate_errors, readout_errors.
        coupling_map: Coupling map.

    Returns:
        Synthetic CalibrationSnapshot.
    """
    n_qubits = max(max(pair) for pair in coupling_map) + 1

    frequencies = noise_model_info.get(
        "frequencies",
        {q: 5.0 for q in range(n_qubits)},
    )
    anharmonicities = noise_model_info.get(
        "anharmonicities",
        {q: -0.3 for q in range(n_qubits)},
    )
    t1 = noise_model_info.get("t1", {q: 100.0 for q in range(n_qubits)})
    t2 = noise_model_info.get("t2", {q: 80.0 for q in range(n_qubits)})
    gate_errs = noise_model_info.get("gate_errors", {})
    ro_errs = noise_model_info.get(
        "readout_errors", {q: 0.02 for q in range(n_qubits)}
    )

    return CalibrationSnapshot(
        backend_name=backend_name,
        timestamp=datetime.now(tz=UTC),
        qubit_frequencies=frequencies,
        anharmonicities=anharmonicities,
        t1_times=t1,
        t2_times=t2,
        gate_errors=gate_errs,
        readout_errors=ro_errs,
        coupling_map=coupling_map,
        raw_properties=noise_model_info,
    )
