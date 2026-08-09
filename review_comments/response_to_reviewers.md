# Response to Reviewers

**Manuscript:** CrossEcho: Predictive Modelling of Crosstalk Side-Channel Leakage on Multi-Tenant Superconducting QPUs
**Journal:** Quantum Engineering (Wiley)
**Date:** August 2026

We thank both reviewers for their careful reading and constructive feedback. We have addressed all comments in detail below. Each reviewer comment is reproduced in bold, followed by our response and a description of the corresponding changes to the manuscript.

---

## Reviewer 1

---

### Comment 1

> **Given that the readout-only control is a key methodology in your protocol, does it mean measurement only (or measurement-induced crosstalk)? How to realize it in practice, by rule or some technics?**

**Response:**

We thank the reviewer for this important clarification question. The readout-only control is a **control experiment**, not part of the crosstalk attack or detection protocol itself. Its purpose is to isolate and quantify measurement-induced (readout) crosstalk so that it can be disambiguated from gate-induced ZZ crosstalk. The key idea is straightforward: if the victim circuit has zero gates, any non-zero TVD measured in the attacker's statistics cannot arise from gate-induced ZZ coupling (there are no victim gates to induce it) and must therefore be attributed to the readout chain.

In practice, the control is realized as follows:

1. **Qubit allocation:** Victim qubits $\mathcal{V}$ and attacker qubits $\mathcal{A}$ are allocated on the QPU identically to the gate-crosstalk experiments.
2. **Victim circuit:** Qubits in $\mathcal{V}$ are initialised to the computational ground state $|0\rangle^{\otimes n_V}$ and never operated on---zero gates, zero microwave pulses.
3. **Attacker circuit:** The attacker probe circuit executes identically to the gate-crosstalk experiments (idle or single-CNOT probe, same shot count).
4. **Measurement:** Only the attacker qubits $\mathcal{A}$ are measured, identical to the gate-crosstalk experiments.
5. **Leakage quantification:** TVD between the attacker's measurement distribution in this configuration and the attacker-alone (victim absent) configuration quantifies the readout-only leakage baseline.

The disambiguation works because the two crosstalk mechanisms produce **qualitatively different distance-decay signatures** (Section 5.3 of the revised manuscript): gate-induced ZZ coupling decays exponentially with SWAP-path distance ($d_0 \approx 1$--$2$ hops), while readout crosstalk---mediated by the frequency-multiplexed measurement feedline, JPA chain, and ADC paths---is approximately distance-independent ($d_0 \gg 10$ hops).

**Changes to manuscript:** We have added a more detailed step-by-step description of the control realisation in Section 5.3 and clarified that the control is an experimental methodology, not part of the attack protocol. We have also added explicit language distinguishing "measurement-induced readout crosstalk" (the physical effect) from the "readout-only control" (the experimental technique used to isolate it).

---

### Comment 2

> **Now that you use the measurement-induced crosstalk, does it mean that your protocol is in an indeterministic way?**

**Response:**

No, the protocol is not indeterministic. We believe there may be a terminological misunderstanding that we should clarify in the revised manuscript.

The readout-only control is used to **separate and quantify** measurement-induced crosstalk as a background effect, not to rely on it. The forward predictive model itself (the CrossEcho protocol) predicts gate-induced ZZ crosstalk leakage from device calibration data---this prediction is deterministic given the inputs (qubit frequencies, coupling strengths, circuit parameters). The Monte Carlo component propagates **epistemic uncertainty** (uncertainty in the input parameters due to limited calibration data), not intrinsic quantum randomness.

The attacker's distinguishing game (Section 3) does involve quantum measurement randomness, but this is fully characterised by the shot-count statistics and the TVD framework. The accumulated ZZ phase itself is a deterministic consequence of the Hamiltonian evolution; the randomness enters only through the projective measurement at the end. This is no more "indeterministic" than any other quantum measurement---and the same statistical framework (TVD, Neyman--Pearson, Chernoff bounds) applies.

To be explicit about the distinction:
- **Gate-induced ZZ crosstalk** (deterministic phase accumulation $\rightarrow$ measured via population statistics)
- **Readout crosstalk** (classical/microwave parasitic coupling $\rightarrow$ measured as a distance-independent baseline)
- **Monte Carlo propagation** (epistemic uncertainty quantification, not quantum indeterminism)

**Changes to manuscript:** We have added a clarification paragraph in Section 5.3 explicitly distinguishing deterministic phase accumulation from measurement randomness, and added language in Section 4.4 clarifying that the Monte Carlo propagation addresses epistemic (parameter) uncertainty, not intrinsic quantum indeterminism.

---

### Comment 3

> **You claimed that 'Cross-architecture validation on the Origin Quantum Cloud WK_C180_2 processor reveals an order-of-magnitude increase in crosstalk magnitude relative to IBM, directly confirming the architecture-dependence that the model identifies as its dominant uncertainty source'. What is the cross-architecture? Is it related to your protocol or quantum processors? If the previous one, it is not appropriate to use two different quantum hardware, i.e. Origin Quantum Cloud WK_C180_2 processor and IBM Quantum Heron r2 processors, to validate this conclusion.**

**Response:**

We appreciate this comment, which identifies an ambiguity in our terminology. "Cross-architecture" in our manuscript refers to **different quantum processor architectures**---specifically, IBM's heavy-hexagonal topology (used in Heron r2) versus Origin's 2D grid topology (used in WK_C180_2). It is not a claim about the CrossEcho protocol itself being "cross-architecture" in some protocol-level sense.

The logic of our validation is as follows:

1. The perturbation-theory model (Eqs. 4--6) predicts that crosstalk magnitude depends on qubit frequencies ($\omega_i$), coupling strengths ($g_{ij}$), and lattice topology---all of which vary across processor architectures.
2. If crosstalk were dominated by readout crosstalk alone (which is architecture-independent, being mediated by the classical measurement chain), we would expect similar TVD magnitudes on any superconducting processor with comparable readout fidelity, regardless of qubit topology.
3. The observation of an order-of-magnitude difference between IBM Heron r2 and Origin WK_C180_2 directly **falsifies** the architecture-independence hypothesis and supports the architecture-dependence prediction of the perturbation-theory model.

Using two genuinely different hardware platforms is precisely the **correct** way to test an architecture-dependence claim---testing on only one architecture would leave the claim untested. We have clarified this logic in the revised manuscript.

**Changes to manuscript:** We have rewritten the relevant passages to replace "cross-architecture" with explicit language: "cross-processor-architecture validation" or "architecture comparison between IBM (heavy-hex) and Origin (2D grid) topologies." We have also added a sentence in Section 6.4 explaining why testing on two different architectures is the appropriate validation strategy for the architecture-dependence hypothesis.

---

### Comment 4

> **What is the Origin Quantum Cloud WK_C180_2 processor?**

**Response:**

The Origin Quantum Cloud WK_C180_2 is a 180-qubit superconducting transmon processor accessible through the Origin Quantum Cloud platform (https://qcloud.originqc.com.cn). We have expanded its description in the revised manuscript. Key specifications:

- **Qubit count:** 180 superconducting transmon qubits
- **Topology:** 2D rectangular grid (as opposed to IBM's heavy-hexagonal lattice)
- **Qubit type:** Fixed-frequency transmons (no tunable couplers)
- **Native gate set:** CZ (controlled-Z) and RPhi (single-qubit rotation with arbitrary phase)
- **Readout:** Dispersive readout via frequency-multiplexed resonators on a common feedline
- **Access:** Python SDK `pyqpanda3` v0.3.5
- **Calibration data exposed:** Limited compared to IBM; qubit frequencies and gate fidelities are partially available through the API

We selected WK_C180_2 for architectural contrast with IBM's Heron r2 because: (i) the denser 2D-grid connectivity produces larger baseline capacitive coupling between qubits, (ii) the fixed-frequency design (without tunable couplers) provides less dynamical crosstalk suppression than IBM's tunable-coupler architecture, and (iii) the estimated inter-qubit detuning ($\Delta \approx 200$--$300$ MHz) is smaller than IBM's engineered $\Delta \gtrsim 500$ MHz, producing larger ZZ coupling via the $\Delta^{-2}$ dependence in Eq.~4.

**Changes to manuscript:** We have added a dedicated paragraph describing the WK_C180_2 processor and the rationale for its selection as a cross-architecture comparison platform in Section 5.2.

---

### Comment 5

> **You introduced a terminology of 'crossecho', and does it have something to do with the similar concept 'echo' in quantum communication?**

**Response:**

We thank the reviewer for this observation. The name "CrossEcho" is **not** directly related to the "echo" concept in quantum communication (Hahn spin echoes, dynamical decoupling, or echo-based entanglement purification protocols). We recognise that the term "echo" carries established meaning in the quantum information community, and we have clarified the intended meaning in the revised manuscript.

The "echo" in CrossEcho is a descriptive metaphor for the physical mechanism:

- **"Cross"** refers to **crosstalk**---the unwanted inter-qubit coupling that propagates through the coupling fabric.
- **"Echo"** refers to the fact that a victim's gate operations leave an **imprint** on neighbouring attacker qubits through ZZ phase accumulation. Just as an acoustic echo is a delayed copy of a sound reflecting off a surface, the ZZ phase on the attacker's qubits is a "copy" of the victim's gate activity propagating through the coupling graph.

Physically, the mechanism is **phase accumulation** ($\Phi_{\mathrm{acc}} = 2\pi|\zeta_{\mathrm{eff}}|t_{\mathrm{gate}}\rho_{\mathrm{2Q}} D n_V s$, Eq.~9), not population transfer (which would be a SWAP or iSWAP interaction). The accumulated phase is detected as a change in the attacker's measurement statistics (population difference after state tomography).

There is a loose analogy with spin echoes: both involve controlled phase evolution. In a Hahn echo, a $\pi$-pulse refocuses dephasing by reversing the sign of the system--environment interaction. In CrossEcho, the ZZ coupling imprints a phase on the attacker qubits that is proportional to the victim's two-qubit gate count. However, the mechanisms are fundamentally different---CrossEcho does not involve any echo pulse sequence or refocusing.

**Changes to manuscript:** We have added a clear definition of the "echo" terminology in Section 1 (Introduction), explicitly stating that it refers to phase accumulation imprinted through the coupling fabric, and distinguishing it from the Hahn/spin-echo concept in quantum communication.

---

## Reviewer 2

---

### Comment 1

> **The Monte Carlo sampling assumes normal distributions for $g_{ij}$ and $\Delta_{ij}$. Justify this Gaussian assumption, or briefly discuss how non-Gaussian fabrication variability would alter uncertainty bounds.**

**Response:**

We thank the reviewer for this methodological question. The Gaussian assumption is a pragmatic first-order choice, and we have added a justification and a discussion of non-Gaussian effects in the revised manuscript (Section 4.4).

**Justification of the Gaussian assumption:**

1. **Fabrication physics:** Josephson junction resistance ($R_n$), which sets the Josephson energy $E_J$ and therefore the qubit frequency $\omega_q \propto \sqrt{E_J E_C}$, is determined by the oxidation tunnel barrier thickness. For nominally identical junctions on the same wafer, barrier thickness variations have been experimentally characterised to follow approximately normal distributions (Osman et al., 2023; Alghadeer et al., 2025).

2. **Central Limit Theorem:** The qubit frequency $\omega_q$ and coupling strength $g_{ij}$ depend on multiple independent fabrication steps (junction oxidation, capacitor lithography, resonator definition). By the Central Limit Theorem, the aggregate distribution tends toward Gaussian even if individual step distributions are not.

3. **Maximum entropy:** In the absence of detailed foundry distribution data (which is proprietary to IBM and Origin), the Gaussian distribution is the maximum-entropy (least-informative) distribution for a given mean and variance. Any other choice would implicitly encode additional assumptions not supported by available data.

**Effect of non-Gaussian variability:**

If the true fabrication distribution deviates from Gaussian, our uncertainty bounds would be affected as follows:

- **Heavy-tailed distributions (e.g., log-normal):** The tails of the predicted TVD distribution would be wider than our 2$\sigma$ Gaussian intervals, meaning our confidence intervals would be **anti-conservative** (they would understate the true uncertainty). The mean prediction $L_{\mathrm{pred}}$ could also be biased if the distribution is skewed.
- **Bimodal distributions (e.g., two fabrication batches with different mean parameters):** The mean prediction could be misleading, falling between two clusters. In this case, the model should be stratified by fabrication batch.
- **Bounded uniform distributions (e.g., if $\Delta$ is constrained by design to $[500, 700]$ MHz):** Our Gaussian intervals would be **conservative** (they would overstate the uncertainty), since the true distribution would have lighter tails than Gaussian.

For the present work, the dominant error is not the shape of the input distribution but the systematic offset in its mean ($\bar{g}$ and $\bar{\Delta}$ are estimated without access to actual qubit frequencies). As noted in Section 7.1, frequency opaqueness contributes $\sim$90\% of the model error budget, dwarfing any distribution-shape effects. Future work with access to fabrication data or coarse frequency bins from providers would enable empirical calibration of the input distributions.

**Changes to manuscript:** We have added a paragraph in Section 4.4 justifying the Gaussian assumption and a paragraph discussing the effect of non-Gaussian variability on the uncertainty bounds.

---

### Comment 2

> **Figure 4 shows non-monotonic TVD fluctuations across SWAP distances for both gate and readout crosstalk. Add a short discussion on the origins of this noise (binomial sampling error, per-qubit readout fidelity variation) and how increased shot counts smooth this distance profile.**

**Response:**

We agree that the non-monotonic fluctuations in Figure 4 (now Figure 3 in the revised manuscript) merit explicit discussion. We have added a paragraph in Section 6.2 addressing the three noise sources and their shot-count scaling.

**Origins of the non-monotonic fluctuations:**

1. **Binomial sampling error:** At $N = 2000$ shots, the standard error of a single TVD measurement is $\sigma_{\mathrm{TVD}} \approx 1/\sqrt{N} \approx 0.022$ (in the worst case of uniform distribution). This is comparable to the measured TVD values themselves ($0.005$--$0.057$), meaning individual cell measurements are noise-dominated. This is the primary source of the fluctuations.

2. **Per-qubit readout fidelity variation:** Different qubits on the same processor have different readout error rates (typically $1$--$5\%$ on IBM Heron r2). A cell placed on qubits with higher readout error will show higher apparent TVD even if the true crosstalk is identical, producing cell-to-cell scatter at the same distance.

3. **Per-path coherence variation:** Two paths with the same hop-count $d$ may traverse intermediate qubits with different $T_1$ and $T_2$ values, producing different effective $\zeta_{\mathrm{eff}}$ via decoherence during SWAP-path propagation.

**Effect of increased shot counts:**

The binomial sampling error scales as $\propto 1/\sqrt{N}$. Increasing from $N = 2000$ to $N = 20{,}000$ would reduce the per-cell standard error from $\sim 0.022$ to $\sim 0.007$, and to $N = 10^5$ would reduce it to $\sim 0.003$. At $10^5$ shots, the binomial noise would be well below the typical measured TVD values, and the underlying distance-decay profile would emerge clearly.

Per-qubit readout fidelity variation could be partially corrected by normalising each cell's TVD by the geometric mean of its qubits' readout error rates: $\mathrm{TVD}_{\mathrm{norm}} = \mathrm{TVD}_{\mathrm{meas}} / \sqrt{\epsilon_{\mathrm{ro},q_1} \epsilon_{\mathrm{ro},q_2}}$. This is straightforward to implement (readout error rates are exposed by the IBM API) and would remove one source of spurious cell-to-cell variation. We did not apply this correction in the present analysis to keep the pipeline simple, but we note it as an available refinement for future studies.

**Changes to manuscript:** We have added a paragraph in Section 6.2 discussing the origins of the non-monotonic fluctuations and their shot-count scaling, and a sentence noting the readout-normalisation option.

---

### Comment 3

> **Table 5 compares TVD metrics against classification accuracy from prior attack papers, but does not convert earlier accuracy results into equivalent TVD bounds for direct side-by-side comparison. Add a brief supplementary calculation to unify cross-study leakage quantification.**

**Response:**

This is an excellent suggestion. We have added a supplementary calculation that converts prior accuracy-based metrics into equivalent TVD lower bounds, enabling direct quantitative comparison. The calculation is included in Section 6.5 and summarised in the revised Table 5.

**Method:** For a binary hypothesis test with $N$ independent measurements, classification accuracy $A$ is bounded above by the total variation distance via the Neyman--Pearson lemma and Chernoff bound:

$$A \leq \frac{1}{2} + \frac{1}{2} \min(1, N \cdot \mathrm{TVD})$$

Rearranging, the minimum TVD required to achieve accuracy $A$ (a lower bound on the actual TVD) is:

$$\mathrm{TVD}_{\mathrm{min}} \geq \max\left(0, \frac{2A - 1}{N}\right)$$

**Application to prior studies:** Hu et al. (2025) report $100\%$ circuit-size prediction accuracy. With $N \approx 2000$ shots per measurement and $k = 4$ circuit-size classes, the effective binary classification accuracy is $\approx 99\%$ (multi-class to binary reduction). This gives $\mathrm{TVD}_{\mathrm{min}} \geq 0.00049$. Choudhury et al. (2024) report $85.7\%$ algorithm classification accuracy across $336$ benchmark circuits with $N \approx 4000$. This gives $\mathrm{TVD}_{\mathrm{min}} \geq 0.00018$.

Our measured TVD range of $0.005$--$0.057$ is **10--300$\times$ above these lower bounds**, confirming consistency: the TVD values we measure are more than sufficient to support the classification accuracies reported in prior work. We note that these are **lower bounds**; actual TVD values in prior studies are likely higher because (i) the classifier optimises over multiple measurements, (ii) the bound is loose for small $N$, and (iii) the reported accuracies may involve multi-class rather than binary classification.

**Changes to manuscript:** We have added the TVD--accuracy conversion method as a paragraph in Section 6.5 and expanded Table 5 to include a column with the equivalent TVD lower bounds for each prior study.

---

### Comment 4

> **Standardize shorthands on first use: ZZ coupling, TVD, NISQ, QPU, RMSE, SWAP-path distance, JPA, ADC.**

**Response:**

We thank the reviewer for this careful check. We have performed a full pass over the manuscript to ensure all abbreviations are defined on first use. The `\abbr{}` block on page 1 of the original manuscript listed many but not all abbreviations; we have expanded it and verified each abbreviation's first-use location.

Specifically:
- **ZZ coupling:** Defined in the abstract and again in Section 2.1 (first technical use)
- **TVD (Total Variation Distance):** Defined in the abstract and Section 3.2
- **NISQ (Noisy Intermediate-Scale Quantum):** Defined in the abstract and Section 1
- **QPU (Quantum Processing Unit):** Defined in the abstract and Section 1
- **RMSE (Root-Mean-Square Error):** Defined in the abstract and Section 5.4
- **SWAP-path distance:** Defined in Section 4.2 (first use of Eq. 6)
- **JPA (Josephson Parametric Amplifier):** Defined in Section 2.3
- **ADC (Analogue-to-Digital Converter):** Defined in Section 2.3

We have also verified that all abbreviations used in figures and tables are defined in the surrounding text.

**Changes to manuscript:** We have added missing first-use definitions and updated the `\abbr{}` block to be comprehensive. We have verified every abbreviation used in the manuscript has a single, clear first-use definition.

---

### Comment 5

> **Remove redundant repetitive descriptions of the readout-only control experiment across Section 5, 6 and 7; consolidate core methodology once and cross-reference later sections.**

**Response:**

We agree that the original manuscript contained redundant descriptions. The readout-only control was described in three places: Section 5.3 (methods), Section 6.2 (results), and Section 7 (discussion). We have now consolidated as follows:

- **Section 5.3 (Methods):** Contains the **complete, authoritative description** of the readout-only control---rationale, step-by-step procedure, physical mechanisms isolated, and expected distance-decay signatures. This is the single source of truth.
- **Section 6.2 (Results):** Reports the findings from the control experiment (flat distance decay, $d_0 \gg 10$, statistical tests) with a **single-sentence cross-reference** to Section 5.3 for the methodology, rather than re-describing it.
- **Section 7 (Discussion):** Discusses implications of the control results for prior work and future methodology, **cross-referencing** Section 5.3 rather than re-describing the experiment.

This follows the standard IMRaD structure: Methods describe what was done, Results report what was found, Discussion interprets what it means.

**Changes to manuscript:** We have removed the redundant methodology descriptions from Sections 6.2 and 7, replacing each with a one-sentence cross-reference to Section 5.3, and verified that the consolidated description in Section 5.3 is complete and self-contained.

---

### Comment 6

> **The term "echo" in "CrossEcho" is evocative but not rigorously defined---clarify whether it refers to phase accumulation, population transfer, or both.**

**Response:**

This comment aligns with Reviewer 1's Comment 5, and we have addressed both through a unified clarification in the revised manuscript.

The "echo" in CrossEcho refers specifically to **phase accumulation**---the ZZ phase $\Phi_{\mathrm{acc}}$ imprinted on the attacker's qubits by the victim's two-qubit gate operations, propagating through the coupling fabric. It is **not** population transfer (that would require a resonant SWAP or iSWAP interaction, which is a different coupling mechanism). The accumulated phase is detected as a change in the attacker's measurement statistics (population difference) after computational-basis measurement.

We have added the following definition in Section 1:

> "The project name CrossEcho reflects this mechanism: crosstalk across the coupling topology creates an **echo**---a ZZ phase accumulated on the attacker's qubits in proportion to the victim's two-qubit gate count---of one user's computation in another user's measurement outcomes. The term refers to phase accumulation ($\Phi_{\mathrm{acc}}$ in Eq.~9), not population transfer, and is distinct from the Hahn/spin-echo concept in quantum communication and dynamical decoupling."

**Changes to manuscript:** We have added a precise definition of "echo" in Section 1, explicitly stating it refers to ZZ phase accumulation (not population transfer) and distinguishing it from Hahn echoes. This is cross-referenced in the abstract.

---

### Comment 7

> **Compared with IBM Quantum Heron r2 processors, what are the differences of Origin Quantum Cloud? What are the respective advantages and disadvantages of each quantum cloud?**

**Response:**

We thank the reviewer for this question, which prompted us to add a substantive comparison that strengthens the cross-architecture analysis. We have added a comparison table and discussion in Section 5.2.

**Summary of differences:**

| Feature | IBM Heron r2 | Origin WK_C180_2 |
|---------|-------------|------------------|
| Qubit count | 156 | 180 |
| Topology | Heavy-hexagonal | 2D rectangular grid |
| Connectivity | 2--3 neighbours/qubit | 4 neighbours/qubit (bulk) |
| Coupler type | Tunable | Fixed |
| Native 2Q gate | ECR (echoed cross-resonance) | CZ + RPhi |
| Frequency engineering | $\Delta \gtrsim 500$ MHz | $\Delta \approx 200$--$300$ MHz (est.) |
| Typical ZZ coupling | $\sim$10--50 kHz | $\sim$100--500 kHz (est.) |
| SDK | Qiskit Runtime | pyqpanda3 |
| Readout | Dispersive, multiplexed | Dispersive, multiplexed |
| Calibration data exposed | T1, T2, gate/readout errors | Limited (partial) |
| User community | Large, well-documented | Smaller, growing |
| QPU access model | Open + premium plans | Academic programme |

**Advantages of IBM Heron r2:**
- Tunable couplers enable dynamical ZZ suppression, reducing baseline crosstalk
- Engineered frequency detuning ($\Delta \gtrsim 500$ MHz) further suppresses ZZ via the $\Delta^{-2}$ dependence
- Mature SDK (Qiskit) with extensive documentation and community support
- Rich calibration data exposed through the API enables detailed noise modelling
- Heavy-hex topology supports efficient surface-code error correction

**Disadvantages of IBM Heron r2:**
- Heavy-hex connectivity limits qubit allocation flexibility (fewer neighbours per qubit)
- QPU time is competitive and queue times can be long during peak usage
- Frequency opaqueness limits independent crosstalk modelling (as discussed in Section 7.1)

**Advantages of Origin WK_C180_2:**
- Denser 2D-grid connectivity provides more qubit allocation options
- Academic access programme provides dedicated QPU time
- Native CZ gate offers an alternative entangling primitive to the CNOT/ECR family

**Disadvantages of Origin WK_C180_2:**
- Fixed-frequency transmons without tunable couplers → larger baseline $g$, higher ZZ crosstalk
- Smaller inter-qubit detuning → larger $|\zeta|$ via the $\Delta^{-2}$ dependence
- Limited calibration data exposed through the API restricts independent noise characterisation
- Smaller user community and less mature SDK

**Relevance to our study:** The 15$\times$ CNOT TVD excess on Origin relative to IBM is a direct consequence of these architectural differences: denser connectivity (larger $g$) and smaller detuning (smaller $\Delta$) combine via Eq.~4 to produce $\sim$10--25$\times$ larger $|\zeta|$. This validates the perturbation-theory model's central claim: crosstalk magnitude is strongly architecture-dependent.

**Changes to manuscript:** We have added a comparison table and discussion in Section 5.2, and cross-referenced this comparison in the cross-architecture results discussion (Section 6.4).

---

## Additional Changes

In addition to the reviewer-requested changes, we have made the following improvements:

1. **Updated the `\abbr{}` block** to be comprehensive, including all abbreviations used in the manuscript.
2. **Verified all references** against Crossref and arXiv, correcting any inconsistencies.
3. **Added a dedicated "Data Availability" statement** consistent with Wiley's data policy.
4. **Standardised figure cross-references** to use the correct numbering after consolidation.

We believe these revisions have substantially improved the clarity, rigour, and completeness of the manuscript. We thank both reviewers again for their time and constructive input.

---

**Corresponding Author:**
Justice Owusu Agyemang
Quantum and Assistive Technologies Lab
Kwame Nkrumah University of Science and Technology
justice.agyemang@knust.edu.gh
