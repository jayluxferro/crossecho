"""Abstract base class for circuit generators."""

from abc import ABC, abstractmethod

from qiskit import QuantumCircuit


class CircuitGenerator(ABC):
    """Abstract base for victim and attacker circuit generators.

    Each generator produces a QuantumCircuit given a number of qubits and
    optional parameters, and reports its two-qubit gate statistics.
    """

    def __init__(self, num_qubits: int) -> None:
        if num_qubits < 1:
            raise ValueError(f"num_qubits must be >= 1, got {num_qubits}")
        self._num_qubits = num_qubits
        self._circuit: QuantumCircuit | None = None

    @property
    def num_qubits(self) -> int:
        return self._num_qubits

    @abstractmethod
    def generate(self, **params: object) -> QuantumCircuit:
        """Build and return the circuit. Stores result internally."""

    @property
    def circuit(self) -> QuantumCircuit:
        if self._circuit is None:
            raise RuntimeError("generate() must be called before accessing circuit")
        return self._circuit

    @property
    def depth(self) -> int:
        return self.circuit.depth()

    @property
    def total_gates(self) -> int:
        return sum(1 for _ in self.circuit)

    @property
    def two_qubit_gate_count(self) -> int:
        return sum(1 for inst in self.circuit if inst.operation.num_qubits == 2)

    @property
    def two_qubit_gate_density(self) -> float:
        total = self.total_gates
        if total == 0:
            return 0.0
        return self.two_qubit_gate_count / total
