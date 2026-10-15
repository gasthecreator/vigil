# Study S10 Pre-Registration: Multi-Site Synthetic Trial & Federated Learning Feasibility (M12)

**Study ID:** S10_MULTISITE_SYNTHETIC_TRIAL  
**Protocol Version:** 1.0  
**Status:** PRE-REGISTERED (PRIOR TO EXECUTION)  
**Date:** 2026-10-15  
**Governing Documents:** `docs/MASTER_PLAN.md` §14 WP3.5; `docs/ML_PROGRAM.md` §3.5, §6, §9  

---

## 1. Study Objective and Research Question
Health data governance, cross-border privacy regulations (e.g. NDPA, GDPR, HIPAA), and institutional barriers frequently prevent pooling raw patient laboratory trajectories into a centralized database. Model M12 envisions a federated architecture where models train across decentralized clinical centers with partial pooling of global parameters while keeping patient-level electronic health records localized.

**Core Question:** Can federated partial pooling across heterogeneous clinical environments achieve surveillance accuracy competitive with centralized pooling (utility drop $\le 3\text{ percentage points}$ AUC), while substantially outperforming isolated site-level training, particularly in under-resourced community and mission facilities?

---

## 2. Pre-Registered Hypotheses
1. **H1 (Local Silo Failure):** Models trained strictly on local data in low-volume, under-resourced centers (Rural Mission Hospital, Community Clinic) will underperform by $> 0.10$ IPCW ROC-AUC due to small sample sizes ($N \le 100$) and high missingness.
2. **H2 (Federated Parity):** Federated partial pooling (local site parameters private, shared kinetic and survival hyperparameters aggregated via FedAvg / hierarchical empirical Bayes) will match centralized pooled performance within $0.02$ IPCW ROC-AUC across all participating sites.
3. **H3 (Equity Boost for Under-Resourced Sites):** Participating in the federated network will provide the largest relative performance gain ($> +0.08$ AUC) to the lowest-resource facility by borrowing statistical strength from tertiary academic centers.

---

## 3. Participating Clinic Archetypes (Simulated Consortium)
1. **Site A: Urban Tertiary Academic Hospital** ($N = 1,200$, 8 visits/yr, 5% missingness, complete 7-analyte panel).
2. **Site B: Regional General Hospital** ($N = 600$, 4 visits/yr, 15% missingness, standard 5-analyte panel).
3. **Site C: Rural Mission Hospital** ($N = 150$, 2 visits/yr, 40% missingness, basic 3-analyte panel + symptoms).
4. **Site D: Private Comprehensive Cancer Center** ($N = 400$, 6 visits/yr, 2% missingness, full multi-marker panel).
5. **Site E: Community Primary Care Outreach Center** ($N = 150$, 3 visits/yr, 30% missingness, routine liver/bone enzymes only).

---

## 4. Evaluated Training Paradigms
- **Paradigm 1 (Local Only):** Each clinic trains an independent model exclusively on its internal data.
- **Paradigm 2 (Centralized Pooling):** Unconstrained centralized pool of all patient data from all 5 sites (unrealistic ceiling).
- **Paradigm 3 (M12 Federated Partial Pooling):** Decentralized model training with hierarchical parameter aggregation across 10 communication rounds.

---

## 5. Primary and Secondary Endpoints
1. **Primary Metric:** IPCW Time-Dependent ROC-AUC at 365 days evaluated on site-specific held-out test splits.
2. **Secondary Metrics:**
   - Worst-site AUC (evaluating health equity across the network).
   - Expected Calibration Error (ECE) per site.
   - Utility drop ($\Delta \text{AUC} = \text{AUC}_{\text{centralized}} - \text{AUC}_{\text{federated}}$).

---

## 6. Pre-Registered Decision Criteria
Per `docs/ML_PROGRAM.md` §6:
- If the utility cost of federation exceeds $3\text{ percentage points}$ AUC ($\Delta \text{AUC} > 0.03$), M12 will ship solely as a federated evaluation framework rather than an automated decentralized training system.
