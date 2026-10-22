"""Test IBM Quantum connection — save in a test script for debugging."""

import os
import socket
import sys

# 1. Verify env
token = os.environ.get("IBM_QUANTUM_API_KEY", "")
if not token:
    print("ERROR: IBM_QUANTUM_API_KEY not set")
    sys.exit(1)
print(f"Token: ***{token[-8:]} (length={len(token)})")

# 2. DNS check
for host in ["cloud.ibm.com", "api.quantum-computing.ibm.com", "auth.quantum-computing.ibm.com"]:
    try:
        ip = socket.getaddrinfo(host, 443)
        print(f"DNS {host}: OK -> {ip[0][4]}")
    except Exception as e:
        print(f"DNS {host}: FAIL -> {e}")

# 3. pyproject versions
print(f"Python: {sys.version}")
from importlib.metadata import version
print(f"qiskit: {version('qiskit')}")
print(f"qiskit-ibm-runtime: {version('qiskit-ibm-runtime')}")

# 4. Connect
print("\nConnecting to IBM Quantum...")
from qiskit_ibm_runtime import QiskitRuntimeService

channel = os.environ.get("IBM_CHANNEL", "ibm_quantum_platform")
instance = os.environ.get("IBM_INSTANCE", "ibm-q/open/main")

service = QiskitRuntimeService(
    channel=channel,
    token=token,
    instance=instance,
)
print(f"Connected. Listing backends...")
backends = service.backends()
print(f"\n{len(backends)} backends found:")
for b in backends:
    cfg = b.configuration()
    print(f"  {b.name:24s}  qubits={cfg.num_qubits:3d}  status={b.status().status}")
