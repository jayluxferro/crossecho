"""Victim circuit generators: Grover, Simon, QFT, Layered CNOT.

All victims produce reproducible circuits suitable for evaluating crosstalk
leakage at NISQ scales (3–8 qubits, shallow depths).
"""

import numpy as np
from qiskit import QuantumCircuit
from qiskit.circuit.library import MCMT
from qiskit.circuit.library.standard_gates import XGate
from qiskit.synthesis.qft import synth_qft_full

from crossecho.circuits.base import CircuitGenerator


class GroverVictim(CircuitGenerator):
    """Grover's search algorithm victim circuit.

    Multi-controlled gates are decomposed into 1Q and 2Q gates
    via Qiskit's MCMT decomposition.

    Args:
        num_qubits: Number of search qubits (3–5 typical).
        iterations: Number of Grover iterations (1–2 for NISQ scale).
        marked_state: Optional specific state to mark. If None, uses |1...1⟩.
    """

    def __init__(
        self,
        num_qubits: int,
        iterations: int = 1,
        marked_state: int | None = None,
    ) -> None:
        super().__init__(num_qubits)
        self._iterations = iterations
        self._marked_state = marked_state

    @staticmethod
    def _apply_mcz(qc: QuantumCircuit, controls: list[int], target: int) -> None:
        """Multi-controlled Z gate decomposed to native gates.

        MCZ = H(target) · MCX · H(target)
        """
        qc.h(target)
        if len(controls) == 1:
            qc.cx(controls[0], target)
        elif len(controls) == 2:
            # CCX (Toffoli) with standard decomposition into CNOTs + T gates
            # The H(target) sandwich is handled by the caller (_apply_mcz)
            qc.cx(controls[1], target)
            qc.tdg(target)
            qc.cx(controls[0], target)
            qc.t(target)
            qc.cx(controls[1], target)
            qc.tdg(target)
            qc.cx(controls[0], target)
            qc.t(controls[1])
            qc.t(target)
            qc.cx(controls[0], controls[1])
            qc.t(controls[0])
            qc.tdg(controls[1])
            qc.cx(controls[0], controls[1])
        else:
            mcmt = MCMT(XGate(), num_ctrl_qubits=len(controls), num_target_qubits=1)
            qc.compose(
                mcmt.decompose().decompose(),
                qubits=controls + [target],
                inplace=True,
            )
        qc.h(target)

    def generate(self, **params: object) -> QuantumCircuit:
        iterations = int(params.get("iterations", self._iterations))
        marked = params.get("marked_state", self._marked_state)
        if marked is None:
            marked = (1 << self._num_qubits) - 1

        qc = QuantumCircuit(self._num_qubits, self._num_qubits)
        qc.h(range(self._num_qubits))

        controls = list(range(self._num_qubits - 1))
        target = self._num_qubits - 1

        for _ in range(iterations):
            marked_bits = bin(marked)[2:].zfill(self._num_qubits)
            for i, bit in enumerate(reversed(marked_bits)):
                if bit == "0":
                    qc.x(i)

            self._apply_mcz(qc, controls, target)

            for i, bit in enumerate(reversed(marked_bits)):
                if bit == "0":
                    qc.x(i)

            qc.h(range(self._num_qubits))
            qc.x(range(self._num_qubits))
            self._apply_mcz(qc, controls, target)
            qc.x(range(self._num_qubits))
            qc.h(range(self._num_qubits))

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc


class SimonVictim(CircuitGenerator):
    """Simon's algorithm victim circuit.

    Args:
        num_qubits: Total qubits (4–6 typical). Split into input + ancilla.
        hidden_string: The secret string s. If None, randomly chosen.
    """

    def __init__(
        self,
        num_qubits: int,
        hidden_string: str | None = None,
    ) -> None:
        super().__init__(num_qubits)
        if hidden_string is None:
            rng = np.random.default_rng()
            bits = rng.integers(0, 2, size=num_qubits)
            hidden_string = "".join(str(b) for b in bits)
        self._hidden_string = hidden_string

    def generate(self, **params: object) -> QuantumCircuit:
        hidden = str(params.get("hidden_string", self._hidden_string))
        n_input = self._num_qubits // 2
        n_ancilla = self._num_qubits - n_input
        hidden_input = hidden[:n_input]

        qc = QuantumCircuit(self._num_qubits, n_input)
        qc.h(range(n_input))

        for a_idx in range(n_ancilla):
            for i_idx, bit in enumerate(hidden_input):
                if bit == "1":
                    qc.cx(i_idx, n_input + a_idx)

        qc.h(range(n_input))
        qc.measure(range(n_input), range(n_input))
        self._circuit = qc
        return qc


class QFTVictim(CircuitGenerator):
    """Quantum Fourier Transform victim circuit.

    Uses synth_qft_full for a fully decomposed circuit.

    Args:
        num_qubits: Number of qubits (4–6 typical).
        inverse: If True, apply inverse QFT.
    """

    def __init__(self, num_qubits: int, inverse: bool = False) -> None:
        super().__init__(num_qubits)
        self._inverse = inverse

    def generate(self, **params: object) -> QuantumCircuit:
        inverse = bool(params.get("inverse", self._inverse))

        qc = QuantumCircuit(self._num_qubits, self._num_qubits)
        qc.h(range(self._num_qubits))

        qft_circuit = synth_qft_full(num_qubits=self._num_qubits, do_swaps=True)
        if inverse:
            qft_circuit = qft_circuit.inverse()
        qc.compose(qft_circuit, inplace=True)

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc


class LayeredCNOTVictim(CircuitGenerator):
    """Layered CNOT victim with tunable two-qubit gate density.

    This is the most important victim circuit — it allows sweeping 2Q gate
    density as an independent variable for the leakage model.

    Args:
        num_qubits: Number of qubits (4–8 typical).
        density: Fraction of possible CNOTs to apply per layer (0.1–0.5).
        layers: Number of CNOT layers (2–4).
        seed: Random seed for reproducible pair selection.
    """

    def __init__(
        self,
        num_qubits: int,
        density: float = 0.3,
        layers: int = 3,
        seed: int | None = 42,
    ) -> None:
        super().__init__(num_qubits)
        self._density = density
        self._layers = layers
        self._seed = seed

    def generate(self, **params: object) -> QuantumCircuit:
        density = float(params.get("density", self._density))
        layers = int(params.get("layers", self._layers))
        seed = params.get("seed", self._seed)
        if seed is not None:
            seed = int(seed)  # type: ignore[assignment]
        rng = np.random.default_rng(seed)

        qc = QuantumCircuit(self._num_qubits, self._num_qubits)
        qc.h(range(self._num_qubits))

        for _layer_idx in range(layers):
            n_pairs = max(1, int(density * self._num_qubits))
            used_controls: set[int] = set()
            for _ in range(n_pairs):
                available = [q for q in range(self._num_qubits) if q not in used_controls]
                if len(available) < 2:
                    break
                ctrl, tgt = rng.choice(available, size=2, replace=False)
                qc.cx(int(ctrl), int(tgt))
                used_controls.add(int(ctrl))
                used_controls.add(int(tgt))

            for q in range(self._num_qubits):
                angle = rng.uniform(0, 2 * np.pi)
                qc.rz(angle, q)

        qc.measure(range(self._num_qubits), range(self._num_qubits))
        self._circuit = qc
        return qc
