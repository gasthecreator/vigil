# Phase 4 acceptance contract — M3 Plausibility Adjudicator and M5 verified narrative

Overseer-authored; `tests/acceptance_p4/` must not be edited by the builder (a test you think is wrong → `docs/proposals/`, never a workaround). Run: `VIGIL_ACCEPT_P4=1 uv run pytest tests/acceptance_p4 -v`. Stub tokens: `M3-RCV`, `M3-CALIB`, `M3-POLICY`, `M3-FACTS`, `M5-VERIFY`, `M5-SAFETY`.

## M3 — `vigil_ml.m3`
```python
def rcv(cv_analytical: float, cv_within: float, z: float = 1.96, log_normal: bool = False):
    """Reference change value. log_normal=False -> float sqrt(2)*z*sqrt(cva^2+cvi^2).
    log_normal=True -> (up, down) = (exp(z*sqrt(2)*s)-1, exp(-z*sqrt(2)*s)-1), s = sqrt(ln(1+cva^2)+ln(1+cvi^2))."""

def adjudicate(history: list[tuple[float, float]], new_day: float, new_value: float,
               cv_analytical: float, cv_within: float, lab_changed: bool = False, inter_lab_cv: float = 0.10,
               p_error_prior: float = 0.03, p_real_prior: float = 0.20) -> dict:
    """-> {"p_real", "p_error", "p_stable"  (sum to 1),
           "action": "explained" | "needs_repeat" | "escalate",
           "rationale_facts": [ {"fact_id": str, "type": str, "value": float|str, ...}, ... ]}"""
```
Stated generative model (the model the adjudicator must reason under; the tests simulate from it):
baseline level L; each measurement = L·exp(ε), ε ~ N(0, cva²+cvi²) (log scale, small-CV approximation); **real change** = persistent increase by factor f ~ logUniform(1.4, 3.0) on top of that noise; **gross error** = one of {value redrawn from the population `exp(N(ln 18, 0.6))`, ×10 decimal shift, ÷10 decimal shift} (equally likely); if `lab_changed`, the new value additionally carries a between-lab multiplicative offset exp(N(0, inter_lab_cv)). The baseline reported in facts is the **geometric mean of the history**.
Tests (all simulated inside the test): (1) `rcv` equals the closed forms; (2) outputs valid (probabilities in [0,1], sum to 1, allowed action); (3) **calibration** on 3,000 cases — ECE ≤ 0.06 for `p_real` and `p_error`, and Brier ≤ 0.85 × the constant-prior Brier; (4) **discrimination** — AUROC(p_real: real vs stable) ≥ 0.85, AUROC(p_error: error vs rest) ≥ 0.80; (5) **no dismissal policy** — `explained` only if `p_stable ≥ 0.90`; `escalate` only if `p_real ≥ 0.60`; if `p_error ≥ 0.30` the action is `needs_repeat` (never `explained`, never `escalate`); (6) **lab change** — for a 1.35× jump the same inputs give a lower `p_real` when `lab_changed=True`; (7) **facts** — `rationale_facts` contains a fact of type `rcv` (value equals `rcv(...)`) and a fact of type `observed_change` (value = new / geometric-mean(history), within 1%).

## M5 — `vigil_ml.m5`
```python
def render_clinician_note(facts: list[dict]) -> str            # templates only; may use any of the M3 facts / probabilities
def verify_narrative(text: str, facts: list[dict]) -> dict      # {"ok": bool, "violations": [str, ...]}
```
Tests: (1) round trip — for 200 random fact tables the rendered note verifies `ok`; (2) mutation tests on a rendered note with ≥ 2 distinct percentages: replace a percentage by a different number → not ok; swap two different percentages → not ok; append "Expected delay is 14 days." (number absent from facts) → not ok; (3) **safety** — appending each of ["You have cancer.", "Metastasis is confirmed.", "There is no need to worry.", "Start chemotherapy now.", "This is definitely lab error."] makes `ok` False; (4) empty fact table renders a safe abstention note that verifies ok; (5) removing a sentence keeps `ok` True. The verifier must be wording-agnostic to the test (it works from the facts and the module's own templates, not from the test's strings).


## Contract v2 (added after review of PR #29)
`tests/acceptance_p4/test_m5_contract_v2.py`: the verifier must accept **only** content warranted by the fact table. 17 unwarranted sentences (paraphrased forbidden claims and numberless clinical claims) must be rejected when appended, when replacing a real sentence, and when standing alone; every genuine sentence is accepted alone but rejected when one word is changed. A blacklist cannot pass this; template-derivation can.
