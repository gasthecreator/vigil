# ADR 0014: Radiotherapy Treatment Continuity Harm Model and CP-SAT Scheduler

## Status
Accepted

## Context
In resource-constrained cancer centres (such as Nigeria with ~280 linear accelerator shortfall per IAEA guidelines; see evidence E6 and Master Plan §6.7), linear accelerators suffer frequent unexpected breakdowns lasting days to weeks. When a machine breaks down:
1. Active curative radiotherapy courses are abruptly interrupted, risking accelerated tumor clonogen repopulation (Withers $\gamma$-factor effect).
2. Incoming adjuvant and palliative patients face expanding waiting lists.
3. In the absence of an algorithmic continuity policy, decisions often default to ad-hoc triage, informal triage, or First-Come-First-Served (FCFS) queues that neglect biological doubling times and disproportionately harm patients with aggressive subtypes (e.g. TNBC) or acute palliative crises (e.g. spinal cord compression).

We require an automated, mathematically grounded scheduler (Module M7) that minimizes expected excess biological harm and preserves clinical continuity while strictly enforcing equity and fairness.

## Decision

### 1. Piecewise Harm-of-Delay Model
We implement `ContinuityHarmModel` in `vigil_ml.continuity`, modeling piecewise excess recurrence hazard:
- **Grace Periods:** 8 weeks (56 days) for post-lumpectomy adjuvant and post-mastectomy radiation; 6 weeks (42 days) for curative TNBC; 0 days for acute palliative metastases.
- **Evidence Base:** Grounded in meta-analyses (E8: Mackillop et al., *Clin Oncol* 2016, local recurrence $RR \approx 1.08$/month, 95% CI 1.02–1.14) for lumpectomy. Unretrieved PMRT/TNBC parameters are explicitly flagged with `evidence_level = "ASSUMPTION"`.
- **Interruption Penalties:** Excess unplanned gap days beyond routine weekend breaks (2 days) incur a daily clonogen repopulation penalty.

### 2. Constraint Programming with OR-Tools CP-SAT
We implement `RadiotherapyScheduler` in `vigil_ml.scheduler` using Google OR-Tools CP-SAT (`cp_model.CpModel`):
- **Decision Variables:** Binary slot assignments $x_{p, d, m} \in \{0, 1\}$ mapping patient $p$ to machine $m$ on day $d$.
- **Hard Capacity & Operational Constraints:** Daily machine slots cannot exceed operational capacity; down machines provide 0 slots.
- **Treatment Contiguity:** Ongoing courses deliver fractions on consecutive weekdays; gaps are penalized.
- **Physics Plan Stability:** Re-assigning an ongoing patient from their current machine to an alternate machine requires a physics quality assurance re-plan and beam calibration, penalized via $\lambda_{\text{switch}}$.

### 3. Explicit Fairness and Anti-Bias Guarantees
- **Zero Weighting on Financial / Insurance Status:** Payment tier, insurance provider, and social status are strictly excluded from the decision variables, constraints, and objective function.
- **Bounded Wait Disparity:** The solver enforces that the difference in mean wait times across demographic or geographic subgroups cannot exceed an equity bound $\Delta_{\text{equity}}$.
- **No-Starvation Invariant ($W_{\max}$):** Every registered patient is assigned a hard upper bound $W_{\max}$ preventing indefinite postponement of lower-urgency adjuvant cases.

### 4. Marginal Harm Transparency
For each scheduling decision, the solver outputs the marginal harm $\Delta H_{p}$ and an interpretable clinical rationale explaining why patient $A$ was prioritized over patient $B$.

## Consequences
- **Positive:** Reduces expected excess cancer recurrence and acute complication rates during machine breakdowns compared to FCFS and greedy heuristics.
- **Positive:** Guaranteed algorithmic fairness with verifiable absence of wealth bias.
- **Positive:** Deterministic, reproducible optimization via CP-SAT with sub-second solve times for departmental horizons.
- **Dependency Impact:** Adds `ortools>=9.9.0` to `packages/vigil-ml/pyproject.toml` for CP-SAT constraint programming. Downstream consumers (`apps/api`, `scripts`) re-verified and passing all test suites.
- **Negative:** CP-SAT requires integer scaling of floating-point probabilities (handled via $10^4$ scaling factor).
