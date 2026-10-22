# Prior Art — CrossEcho Novelty

A summary of the closest prior work and CrossEcho's specific novelty relative to it.

---

## (a) Paper Summaries

### 1. SWAP Attack (arXiv:2502.10115)

**Authors:** Wei Hu, Wang, Suman Dutta, Walid El Maouaki, Anupam Chattopadhyay

**Summary:** This work identifies the SWAP path between qubits as the root cause of crosstalk leakage on shared quantum devices, demonstrating impact over long topological distances on IBM hardware. They develop active attacks (a single CNOT gate with strategic placement reduces Grover's algorithm output accuracy by 81.62%) and passive attacks (a circuit as small as 6.25% of the victim's achieves 100% accuracy in predicting victim circuit size). Their modeling identifies which qubits are susceptible to crosstalk, but the core contribution is the *attack demonstration*, not a forward predictive model — the modeling serves vulnerability identification, not leakage magnitude forecasting.

### 2. Crosstalk-induced Side Channel Threats in Multi-Tenant NISQ Computers (arXiv:2412.10507)

**Authors:** Navnil Choudhury, Chaithanya Naik Mude, Santosh Das, Pooja Choudhary Tikkireddi, Swamit Tannu, Kanad Basu

**Summary:** First demonstration of crosstalk as an exploitable side-channel in multi-tenant NISQ systems. The attacker observes crosstalk signatures (inferred CNOT gate presence in the victim circuit) and feeds them into a graph-based learning model that classifies the victim's algorithm identity, achieving up to 85.7% accuracy across 336 benchmark circuits. The contribution is *victim fingerprinting via graph learning on observed crosstalk* — classification of what the victim is running, not prediction of leakage magnitude. No device model is involved; the graph model operates purely on empirically observed signatures.

### 3. Pulse-to-Circuit Characterization of Stealthy Crosstalk Attack (arXiv:2509.11407)

**Authors:** Syed Emad Uddin Shubha, Tasnuva Farheen

**Summary:** This paper presents an end-to-end framework for mapping physical pulse-level crosstalk attacks to interpretable logical error channels. The pipeline comprises density-matrix simulation, quantum process tomography (QPT), and a novel isometry-based circuit extraction method. They identify an asymmetric two-qubit adversarial mechanism (driver + catalyst) and demonstrate that these attacks can reduce quantum protocol accuracy to random guessing while remaining stealthy under realistic hardware variations. This is the closest prior work to CrossEcho — it operates at the pulse level and produces a circuit-level model. However, it is fundamentally **post-hoc**: the pipeline *reconstructs* the error channel after running the attack by performing full process tomography and fitting an effective circuit. It is an inverse problem (measure → reconstruct → model), not a forward prediction.

### 4. Crosstalk Attacks and Defence in a Shared Quantum Computing Environment (arXiv:2402.02753)

**Authors:** Benjamin Harper, Behnam Tonekaboni, Bahar Goldozian, Martin Sevior, Muhammad Usman

**Summary:** Characterizes crosstalk noise through tomography on IBM hardware, builds an enhanced crosstalk simulation model benchmarked against real measurements, and evaluates three defense strategies (circuit separation, reinforcement-learning-based qubit allocation, and spectator qubits). The simulation model is calibrated to observed tomography data — it reproduces measured crosstalk behavior rather than predicting it from first-principles device parameters. The contribution is primarily the defense evaluation, not a predictive leakage framework.

---

## (b) Contribution Mapping Table

| Paper | Core contribution | Model type | Predictive or post-hoc? | Hold-out evaluation? | CrossEcho relationship |
|-------|-------------------|------------|------------------------|----------------------|------------------------|
| SWAP Attack (2502.10115) | SWAP-path crosstalk attack on IBM hardware; vulnerability identification | SWAP-path susceptibility model | Descriptive (identifies vulnerable qubits) | No | CrossEcho borrows the SWAP-path framing and the ~6% attacker threshold; goes beyond by predicting leakage *magnitude* |
| Crosstalk Side Channels (2412.10507) | Graph-learning fingerprinting of victim circuits from crosstalk signatures | Graph classifier for algorithm identity | Post-hoc classification of observed signatures | No (within-dataset split) | CrossEcho targets leakage magnitude prediction, not algorithm classification; model is physics-based, not a graph learner |
| **Pulse-to-Circuit Characterization (2509.11407)** | **Pulse-level attack → QPT → logical error channel extraction** | **Isometry-based circuit extraction from tomography** | **Post-hoc reconstruction** | **No** | **Closest prior art. CrossEcho inverts the direction: parameters → leakage (forward), not measure → characterize (inverse).**
| Crosstalk Attacks and Defence (2402.02753) | Tomography-calibrated crosstalk simulation; defense evaluation | Simulation calibrated to measurements | Post-hoc (reproduces observed behavior) | No | CrossEcho's model predicts from calibration, not calibrated to match measurements; forecasting evaluation is the differentiator |

---

## (c) The One Thing CrossEcho Does That None of Them Do

**CrossEcho builds a forward predictive model that takes device calibration data + attacker/victim qubit placement + victim gate density as input and outputs a forecasted crosstalk leakage metric with calibrated error bars, evaluated on genuinely unseen (placement, calibration-day) pairs — not on in-sample data.**

The specific gap with arXiv:2509.11407 is the direction of inference:

- **arXiv:2509.11407** runs the attack → performs full QPT to measure the induced error channel → fits an isometry-based logical circuit model to the reconstructed channel. This is an **inverse problem**: given the outcome, reconstruct what happened. The pipeline has no mechanism to generalize across placements or calibration days without re-running the full simulation/tomography chain. There is no closed-form or learned forward mapping from (parameters) → (leakage).

- **CrossEcho** builds a **forward model**: given calibration parameters (ω_i, α_i, g_ij, T1, T2), qubit placement, and victim gate density, it outputs a predicted leakage L with uncertainty. The model is evaluated by holding out **both** specific qubit placement configurations **and** entire calibration days, then computing forecasting RMSE. This tests whether the model generalizes in geometry space (new placements) and time (new calibration snapshots) — neither of which 2509.11407 does.

Concretely, the novel contribution is:
1. A **forward** ZZ-coupling / SWAP-path effective coupling model derived from the transmon Hamiltonian via perturbation theory
2. **Dual hold-out forecasting evaluation** — placements AND calibration days held out from training
3. **Calibrated error bars** — Monte Carlo propagation of calibration uncertainty through the model, validated for coverage
4. **Quantitative forecasting metrics** (RMSE, distance decay constant, attacker efficiency threshold) reported on unseen data, not in-sample fit statistics

If arXiv:2509.11407 is "what happened when I attacked this qubit pair?" then CrossEcho is "what *will* happen if I attack *that* qubit pair on *a different day*?"
