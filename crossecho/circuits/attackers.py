"""Attacker circuit generators: idle probe, single-CNOT probe, entangling probe.

Attackers are designed to be small (6–50% of victim width) and to probe
crosstalk leakage at varying sensitivity levels.
"""

import numpy as np
from qiskit import QuantumCircuit

from crossecho.circuits.base import CircuitGenerator


class IdleProbe(CircuitGenerator):
    """Minimal attacker: initialize, idle, measure.

    The idle probe detects crosstalk via phase accumulation on its qubits
    without applying any gates of its own. This is the most sensitive probe
    for pure ZZ-coupling leakage (no self-induced decoherence).

    Args:
        num_qubits: Number of attacker qubits (1–4 typical).
    """

    def generate(self, **params: object) -> QuantumCircuit:
        qc = QuantumCircuit(self._num_qubits, self._num_qubits)

        # Initialize in superposition to be sensitive to phase noise
        qc.h(range(self._num_qubits))

        # Identity gates as explicit idle markers (ensures the circuit
        # actually runs for the full victim execution duration)
        qc.barrier(range(self._num_qubits))
        for _ in range(2):
            for q in range(self._num_qubits):
                qc.id(q)
        qc.barrier(range(self._num_qubits))

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc


class SingleCNOTProbe(CircuitGenerator):
    """Attacker with a single CNOT between two attacker qubits.

    The CNOT probe is more sensitive to ZZ coupling because the two-qubit
    gate amplifies phase errors. This is the attacker from the SWAP Attack
    paper's active mode.

    Args:
        num_qubits: Total attacker qubits (2–4 typical). Requires ≥ 2.
    """

    def __init__(self, num_qubits: int) -> None:
        if num_qubits < 2:
            raise ValueError("SingleCNOTProbe requires at least 2 qubits")
        super().__init__(num_qubits)

    def generate(self, **params: object) -> QuantumCircuit:
        qc = QuantumCircuit(self._num_qubits, self._num_qubits)

        # Prepare all qubits in superposition
        qc.h(range(self._num_qubits))

        # Single CNOT between first two attacker qubits
        qc.cx(0, 1)

        # Additional single-qubit rotations for phase sensitivity
        for q in range(self._num_qubits):
            qc.rz(np.pi / 4, q)

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc


class EntanglingProbe(CircuitGenerator):
    """Attacker with alternating CNOT layers (a "victim-lite").

    The entangling probe applies CNOTs between adjacent attacker qubits,
    creating its own small entangled state. This is the most active probe
    and most closely mimics a small victim circuit — highest sensitivity
    but also highest self-noise.

    Args:
        num_qubits: Total attacker qubits (2–6 typical).
        cnot_layers: Number of CNOT layer pairs (1–3).
        seed: Random seed for angle selection.
    """

    def __init__(
        self,
        num_qubits: int,
        cnot_layers: int = 2,
        seed: int | None = 42,
    ) -> None:
        if num_qubits < 2:
            raise ValueError("EntanglingProbe requires at least 2 qubits")
        super().__init__(num_qubits)
        self._cnot_layers = cnot_layers
        self._seed = seed

    def generate(self, **params: object) -> QuantumCircuit:
        layers = int(params.get("cnot_layers", self._cnot_layers))
        seed = params.get("seed", self._seed)
        if seed is not None:
            seed = int(seed)  # type: ignore[assignment]
        rng = np.random.default_rng(seed)

        qc = QuantumCircuit(self._num_qubits, self._num_qubits)

        # Superposition initialization
        qc.h(range(self._num_qubits))

        for _ in range(layers):
            # Even-indexed CNOTs: (0,1), (2,3), ...
            for q in range(0, self._num_qubits - 1, 2):
                qc.cx(q, q + 1)

            # Rotation layer
            for q in range(self._num_qubits):
                angle = rng.uniform(0, np.pi / 2)
                qc.rz(angle, q)

            # Odd-indexed CNOTs: (1,2), (3,4), ...
            for q in range(1, self._num_qubits - 1, 2):
                qc.cx(q, q + 1)

            # Rotation layer
            for q in range(self._num_qubits):
                angle = rng.uniform(0, np.pi / 2)
                qc.rz(angle, q)

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc
