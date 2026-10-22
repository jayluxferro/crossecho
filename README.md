# CrossEcho

**Predictive modelling of crosstalk side-channel leakage on multi-tenant superconducting QPUs.**

CrossEcho is a forward predictive model that forecasts the magnitude of crosstalk side-channel leakage on shared superconducting quantum processors *before* measurement. Given device calibration data, attacker–victim qubit placement, and victim circuit properties, it derives effective ZZ-coupling strengths from transmon perturbation theory, propagates calibration uncertainty with Monte Carlo sampling, and returns a predicted total-variation-distance leakage value with a confidence interval.

The model is evaluated with a dual hold-out protocol — held-out placement configurations *and* calibration snapshots — on real quantum hardware (IBM Heron r2 and Origin WK_C180_2).

This repository contains the code and the raw experimental data used in the paper. The paper itself is published separately (see [Citation](#citation)).

## Repository contents

```
crossecho/       Python package: circuits, leakage model, runners, metrics, viz
data/            Raw experiment results (JSON) from the IBM and Origin runs
scripts/         Entry points: run the pipeline, submit IBM jobs, test connectivity
tests/           Unit tests
```

## Installation

Requires Python 3.12+. Dependencies are managed with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

## Configuration

Before running against hardware, set these environment variables:

| Variable | Required | Default | Description |
|---|---|---|---|
| `IBM_QUANTUM_API_KEY` | yes | — | IBM Quantum API token |
| `IBM_CHANNEL` | no | `ibm_quantum_platform` | Qiskit Runtime channel |
| `IBM_INSTANCE` | no | `ibm-q/open/main` | IBM Quantum instance / CRN |
| `ORIGIN_QC_API_KEY` | no | — | Origin Quantum Cloud API token |

```bash
export IBM_QUANTUM_API_KEY=...
export IBM_CHANNEL=ibm_quantum_platform
export IBM_INSTANCE=crn:v1:...
```

## Reproducing the results

```bash
# Full pipeline: IBM calibration -> Aer noise model -> experiment -> evaluation
uv run python scripts/run_pipeline.py

# Submit the experiment matrix to IBM Quantum hardware
uv run python scripts/submit_ibm_experiment.py

# Verify IBM connectivity and environment
uv run python scripts/test_ibm_connection.py

# Run the test suite
uv run pytest
```

## Responsible use

Crosstalk leakage is a symmetric capability: the same model informs an attacker optimising probe placement and a provider assessing scheduling risk. The work includes a mitigation proposal (coarse frequency binning) aimed at the model's dominant uncertainty source. Please use this code responsibly and coordinate any deployment findings with the relevant cloud providers.

## Citation

If you use this code or data, please cite the paper:

> _Citation and DOI will be added once the paper is published._

## License

[MIT](LICENSE)
