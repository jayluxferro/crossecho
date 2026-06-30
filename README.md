# Project CrossEcho — Predictive Pulse-Level Model of Crosstalk Side-Channel Leakage on Shared QPUs

**Spec version:** 1.0
**Self-contained:** yes. An agent can execute this without the other four specs.
**Project type:** Quantum hardware security — attack / measurement study.

---

## 1. One-line novel claim

The SWAP-path coupling that causes crosstalk on superconducting QPUs leaks a victim circuit's structure in a way that can be **predicted from a pulse-level model of the device**, not merely observed empirically — turning crosstalk from an observed nuisance into a quantitatively predictable side-channel.

The contribution is a *predictive leakage model* (given device calibration + attacker/victim placement → predicted leakage), validated against measured leakage. Prior work demonstrates leakage exists; the gap is a model that forecasts it.

## 2. Why this is novel (and the honest risk)

Prior art to read and explicitly differentiate from before writing any code (MANDATORY GATE — see §10):
- SWAP Attack (arXiv:2502.10115) — active/passive crosstalk side-channel, IBM hardware.
- Crosstalk-induced Side Channel Threats in Multi-Tenant NISQ Computers (arXiv:2412.10507) — graph-learning fingerprinting.
- Pulse-to-Circuit Characterization of Stealthy Crosstalk Attack (arXiv:2509.11407) — pulse-level characterization + detection.
- Crosstalk Attacks and Defence in a Shared Quantum Computing Environment (arXiv:2402.02753).

**Honest risk:** arXiv:2509.11407 already does pulse-level characterization. CrossEcho is only novel if it delivers a *predictive* model with forecasting error bars on unseen placements/calibrations, rather than post-hoc characterization of an observed attack. If the agent cannot articulate, in §10, a concrete difference from 2509.11407, it must STOP and report rather than produce a near-duplicate.

## 3. Threat model

- Multi-tenant QPU where attacker and victim circuits are co-located on the same chip in one job or back-to-back scheduling window.
- Attacker controls only its own circuit (qubit choice within allocation, gate sequence). No elevated privileges, no pulse-level access beyond what the standard cloud SDK exposes.
- Attacker observes only its own measurement outcomes.
- Goal: infer victim circuit properties (size, presence/location of two-qubit gates, identity of algorithm class) from attacker-side measurement statistics.

## 4. Scientific questions

1. Can a model parameterized by device calibration (T1, T2, coupling map, gate errors, ZZ coupling strengths) predict the *magnitude* of attacker-observed leakage for a given attacker–victim qubit placement?
2. How does predicted vs. measured leakage degrade with topological distance along the SWAP path?
3. What is the smallest attacker circuit (as a fraction of victim size) that still yields a model-predicted-significant leakage signal?

## 5. Method

### 5.1 Leakage model (the core deliverable)
- Build a static predictor: input = device calibration snapshot + attacker/victim placement + victim gate density; output = predicted leakage metric (see §7).
- Start with an analytic ZZ-coupling/SWAP-path model; if insufficient, fit a small regression (ridge / gradient-boosted trees) over measured (placement, calibration) → leakage pairs. Keep it interpretable; a black-box deep net defeats the "predictive model" framing.
- Hold out placements and calibration days for genuine forecasting evaluation. Report forecasting error, not just fit.

### 5.2 Victim circuits (canonical, reproducible)
- Grover (3–5 qubits), Simon (small), QFT, and a generic layered CNOT circuit with tunable two-qubit gate density.
- Keep all victim circuits shallow enough to run within the compute budget (§8).

### 5.3 Attacker circuits
- Idle-with-readout probe; single-CNOT probe; small entangling probe. Vary size from 6% to 50% of victim width.

### 5.4 Experimental matrix
- For each (victim, attacker placement, distance) cell: collect attacker-side statistics over N shots.
- Repeat across ≥3 calibration snapshots (different days/backends) to enable forecasting evaluation.

## 6. QPU platforms

- **Primary:** IBM Quantum (superconducting). Budget ~10 s QPU time → this means many short jobs of shallow circuits, NOT one long job. Plan shot counts accordingly (see §8). Use `qiskit` + `qiskit-ibm-runtime`. Record full backend properties (`backend.properties()`) with every job — the calibration snapshot IS the model input.
- **Secondary (optional, strengthens results, NOT the headline):** Origin Quantum (superconducting, China) via the `pyqpanda` / Origin cloud SDK, budget ~100 s. Use it to test whether the leakage model *form* transfers to a chip with a different topology and calibration regime. Frame in the paper as "evaluated on a second independent superconducting architecture" — a robustness check, never the central novelty.
- Simulator: use `qiskit-aer` with a noise model derived from real `backend.properties()` for development and to pre-budget shots before spending hardware time.

## 7. Metrics

- **Leakage metric L:** total variation distance (or KL) between attacker-side output distribution with victim present vs. absent. Define one primary metric, report one secondary.
- **Forecasting error:** RMSE of predicted L vs. measured L on held-out placements/calibrations.
- **Attacker efficiency:** minimum attacker/victim size ratio for L above a significance threshold (bootstrap CI over shots).
- **Distance decay:** L as a function of SWAP-path length; fit decay constant.

## 8. Compute budgeting (critical — budgets are tiny)

- IBM ~10 s and Origin ~100 s are *execution* seconds; treat shots as the scarce resource. Pre-compute on the Aer noise model the number of shots needed for a target CI width, then spend hardware only on the final matrix.
- Prefer many circuits batched per job to amortize latency.
- Log every job's shot count, backend, calibration timestamp, and queue metadata to a results DB (sqlite or parquet).

## 9. Deliverables

1. `crossecho/` Python package: circuit generators, runner (IBM + Origin backends behind one interface), results DB, leakage-model trainer/evaluator.
2. Results dataset (parquet) + calibration snapshots.
3. Figures: predicted-vs-measured leakage, distance decay, attacker-efficiency curve.
4. Paper draft (intro, threat model, model, experiments, related-work differentiation, limitations).
5. `PRIOR_ART.md` from §10.

## 10. MANDATORY prior-art gate (do this first)

Before writing code, produce `PRIOR_ART.md` containing: (a) a 3–5 sentence summary of each paper in §2; (b) a table mapping each paper's contribution to CrossEcho's; (c) an explicit statement of the one thing CrossEcho does that none of them do. If (c) cannot be filled convincingly, STOP and report to the human — do not build a replication.

## 11. Limitations to state honestly in the paper

- Tiny QPU budget caps circuit size; results are NISQ-scale, not asymptotic.
- A predictive model fit on a few calibration snapshots may not generalize across chip generations; say so.
- Cloud scheduling may not co-locate attacker/victim as assumed; document the actual scheduling behavior observed.
