"""
Tests for vigil_eval evaluation components:
- Clustered patient-level bootstrap
- Subgroup analysis with Empirical Bayes shrinkage
- Verification bias estimators (Complete-case, IPW; retired pseudo-label routine)
- Preclinical lead-time and overdetection analysis
- Frozen test set access audit logger
- Model regression gate
"""

import numpy as np
import pandas as pd
import pytest
from vigil_eval.audit import FrozenTestAccessLogger
from vigil_eval.bootstrap import patient_cluster_bootstrap
from vigil_eval.lead_time import evaluate_lead_time_and_overdetection
from vigil_eval.regression_gate import ModelRegressionGate, render_benchmark_table_markdown
from vigil_eval.subgroups import empirical_bayes_shrinkage, evaluate_subgroups_with_shrinkage
from vigil_eval.verification_bias import (
    evaluate_complete_case,
    evaluate_ipw_verification,
    evaluate_latent_class_em,
)


def test_patient_cluster_bootstrap():
    """Verifies that patient cluster bootstrap resamples by patient and produces valid CIs."""
    rng = np.random.default_rng(42)
    # 50 patients, 4 observations each
    rows = []
    for i in range(50):
        pt_id = f"PT-{i:03d}"
        y_val = int(rng.random() < 0.3)
        for d in [0, 90, 180, 270]:
            rows.append(
                {
                    "patient_id": pt_id,
                    "day": d,
                    "score": rng.uniform(0.1, 0.9),
                    "label": y_val,
                }
            )
    df = pd.DataFrame(rows)

    def dummy_metric(data: pd.DataFrame):
        return {
            "mean_score": float(data["score"].mean()),
            "prevalence": float(data["label"].mean()),
        }

    res = patient_cluster_bootstrap(df, "patient_id", dummy_metric, n_bootstraps=50, seed=42)

    assert "mean_score" in res
    assert "prevalence" in res
    m_score = res["mean_score"]
    assert m_score.ci_lower <= m_score.point_estimate <= m_score.ci_upper
    assert m_score.standard_error > 0.0


def test_empirical_bayes_shrinkage_analytical():
    """
    Verifies that Empirical Bayes pulls noisy small-sample estimates toward grand mean.
    """
    # 3 subgroups:
    # Subgroup 1: huge sample, precise estimate 0.80, s=0.01
    # Subgroup 2: tiny sample, noisy outlier 0.40, s=0.25
    # Subgroup 3: moderate sample, estimate 0.75, s=0.05
    estimates = np.array([0.80, 0.40, 0.75])
    ses = np.array([0.01, 0.25, 0.05])

    shrunk, b_factors, grand_mean, tau2 = empirical_bayes_shrinkage(estimates, ses)

    # Subgroup 1 should have minimal shrinkage (B_1 near 0)
    assert b_factors[0] < b_factors[1]
    # Subgroup 2 should be pulled significantly toward grand mean
    assert abs(shrunk[1] - grand_mean) < abs(estimates[1] - grand_mean)


def test_subgroup_analysis_keeps_undefined_metrics_undefined():
    data = pd.DataFrame({"patient_id": ["p1", "p2"], "site": ["A", "B"]})
    result = evaluate_subgroups_with_shrinkage(
        data,
        patient_col="patient_id",
        subgroup_col="site",
        metric_fn=lambda _: {"other_metric": 0.8},
        target_metric="roc_auc",
        n_bootstraps=10,
    )
    assert len(result) == 2
    assert all(np.isnan(item.raw_estimate) and np.isnan(item.shrunk_estimate) for item in result)
    assert all(np.isnan(item.raw_ci_lower) and np.isnan(item.shrunk_ci_upper) for item in result)


def test_verification_bias_corrections():
    """
    Verifies verification bias correction:
    Selective imaging creates inflated apparent sensitivity in complete-case analysis,
    which IPW and Latent-Class EM adjust.
    """
    rng = np.random.default_rng(42)
    n = 500

    # True disease state
    true_y = rng.binomial(1, 0.20, n)
    marker = rng.normal(true_y * 2.0, 1.0)
    scores = 1.0 / (1.0 + np.exp(-marker))

    # Verification mechanism: imaging performed predominantly if marker is high
    p_verify = 1.0 / (1.0 + np.exp(-(marker - 0.5)))
    v_mask = rng.binomial(1, p_verify) == 1

    obs_y = np.where(v_mask, true_y, 0)
    features = marker.reshape(-1, 1)

    cc_rep = evaluate_complete_case(scores, obs_y, v_mask, cutoff=0.5)
    ipw_rep = evaluate_ipw_verification(scores, obs_y, v_mask, features, cutoff=0.5)

    assert cc_rep.empirical_sensitivity > 0.0
    assert ipw_rep.empirical_sensitivity > 0.0
    # Complete case evaluates fewer patients
    assert cc_rep.details["n_verified"] < n
    assert ipw_rep.details["n_total"] == n
    with pytest.raises(NotImplementedError, match="not latent-class EM"):
        evaluate_latent_class_em(
            scores, obs_y, v_mask, features, max_iter=50, tol=1e-4, cutoff=0.5
        )


def test_verification_metrics_are_undefined_when_no_outcomes_are_verified():
    scores = np.array([0.2, 0.8])
    labels = np.array([np.nan, np.nan])
    verified = np.array([False, False])
    report = evaluate_complete_case(scores, labels, verified, cutoff=0.5)
    assert not report.details["metrics_defined"]
    assert np.isnan(report.empirical_sensitivity)
    assert np.isnan(report.empirical_specificity)
    assert np.isnan(report.apparent_prevalence)
    assert np.isnan(report.brier_score)
    assert np.isnan(report.roc_auc)


def test_single_outcome_class_does_not_receive_plausible_sensitivity_or_auc():
    report = evaluate_complete_case(
        risk_scores=np.array([0.2, 0.8]),
        observed_verified_labels=np.array([1, 1]),
        verification_mask=np.array([True, True]),
        cutoff=0.5,
    )
    assert not report.details["metrics_defined"]
    assert np.isnan(report.empirical_specificity)
    assert np.isnan(report.roc_auc)


def test_verification_ipw_requires_finite_declared_features():
    with pytest.raises(ValueError, match="verification_features must be finite"):
        evaluate_ipw_verification(
            risk_scores=np.array([0.2, 0.8]),
            observed_verified_labels=np.array([0, 1]),
            verification_mask=np.array([True, False]),
            verification_features=np.array([[0.0], [np.nan]]),
            cutoff=0.5,
        )


def test_verification_ipw_accepts_propensities_fitted_on_an_independent_split():
    scores = np.array([0.1, 0.3, 0.7, 0.9])
    labels = np.array([0.0, np.nan, 1.0, 1.0])
    verified = np.array([True, False, True, True])
    propensities = np.array([0.4, 0.5, 0.6, 0.8])
    report = evaluate_ipw_verification(
        scores,
        labels,
        verified,
        verification_features=None,
        cutoff=0.5,
        verification_propensities=propensities,
    )
    assert report.details["metrics_defined"]
    assert report.details["minimum_verified_propensity"] == pytest.approx(0.4)
    assert report.details["maximum_verified_inverse_weight"] == pytest.approx(2.5)


def test_verification_ipw_rejects_misaligned_or_invalid_supplied_propensities():
    scores = np.array([0.1, 0.9])
    labels = np.array([0.0, 1.0])
    verified = np.array([True, False])
    with pytest.raises(ValueError, match="aligned with rows"):
        evaluate_ipw_verification(
            scores, labels, verified, None, 0.5, verification_propensities=np.array([0.5])
        )
    with pytest.raises(ValueError, match="finite probabilities"):
        evaluate_ipw_verification(
            scores,
            labels,
            verified,
            None,
            0.5,
            verification_propensities=np.array([np.nan, 0.5]),
        )


def test_verification_mask_rejects_unknown_values_instead_of_treating_them_as_verified():
    with pytest.raises(ValueError, match="verification_mask must contain only known 0/1"):
        evaluate_complete_case(
            risk_scores=np.array([0.2, 0.8]),
            observed_verified_labels=np.array([0, 1]),
            verification_mask=np.array([0.0, np.nan]),
            cutoff=0.5,
        )


def test_lead_time_and_overdetection():
    """Verifies preclinical lead-time and overdetection calculation."""
    # 20 patients: 10 recurrent, 10 non-recurrent
    pt_rows = []
    obs_rows = []

    for i in range(20):
        pt_id = f"PT-{i:02d}"
        is_rec = i < 10
        rec_day = 360.0 if is_rec else None
        is_indolent = i == 9  # 1 indolent patient

        pt_rows.append(
            {
                "patient_id": pt_id,
                "true_recurrence_event": is_rec,
                "true_recurrence_day": rec_day,
                "is_indolent": is_indolent,
            }
        )

        # Observations at 0, 90, 180, 270, 360
        for d in [0.0, 90.0, 180.0, 270.0, 360.0]:
            # Alert triggered at day 270 for recurrent patients (lead time = 90 days)
            # Alert falsely triggered on patient 15 (non-recurrent)
            alert = 1 if ((is_rec and d >= 270.0) or (i == 15 and d >= 180.0)) else 0
            obs_rows.append(
                {
                    "patient_id": pt_id,
                    "day": d,
                    "alert_triggered": alert,
                }
            )

    pt_df = pd.DataFrame(pt_rows)
    obs_df = pd.DataFrame(obs_rows)

    rep = evaluate_lead_time_and_overdetection(pt_df, obs_df)

    assert rep.conditional_mean_days == pytest.approx(90.0)
    assert rep.recurrence_detection_rate == 1.0
    # Overdetection accounts for indolent pt 9 + false alarm pt 15
    assert rep.overdetection_rate > 0.0


def test_lead_time_reports_undefined_denominators_and_uses_observed_person_time():
    patients = pd.DataFrame(
        [{"patient_id": "p1", "true_recurrence_event": False, "is_indolent": False}]
    )
    observations = pd.DataFrame(
        [
            {"patient_id": "p1", "day": 5.0, "alert_triggered": 0},
            {"patient_id": "p1", "day": 15.0, "alert_triggered": 0},
        ]
    )
    report = evaluate_lead_time_and_overdetection(patients, observations)
    assert np.isnan(report.conditional_mean_days)
    assert np.isnan(report.unconditional_mean_days)
    assert np.isnan(report.recurrence_detection_rate)
    assert np.isnan(report.overdetection_rate)
    assert report.alert_burden_per_100_pt_years == 0.0
    assert report.details["total_surveillance_patient_years"] == round(10.0 / 365.25, 2)
    assert not report.details["metrics_defined"]


@pytest.mark.parametrize("event", [None, np.nan, pd.NA, "unknown"])
def test_lead_time_rejects_unknown_recurrence_status(event):
    patients = pd.DataFrame(
        [{"patient_id": "p1", "true_recurrence_event": event, "is_indolent": False}]
    )
    observations = pd.DataFrame(
        [{"patient_id": "p1", "day": 5.0, "alert_triggered": 0}]
    )
    with pytest.raises(ValueError, match="true_recurrence_event"):
        evaluate_lead_time_and_overdetection(patients, observations)


def test_lead_time_rejects_recurrence_without_event_day():
    patients = pd.DataFrame(
        [{
            "patient_id": "p1",
            "true_recurrence_event": True,
            "true_recurrence_day": np.nan,
            "is_indolent": False,
        }]
    )
    observations = pd.DataFrame(
        [{"patient_id": "p1", "day": 5.0, "alert_triggered": 0}]
    )
    with pytest.raises(ValueError, match="recurrence day"):
        evaluate_lead_time_and_overdetection(patients, observations)


def test_lead_time_rejects_recurrence_day_for_non_recurrent_patient():
    patients = pd.DataFrame(
        [{
            "patient_id": "p1",
            "true_recurrence_event": False,
            "true_recurrence_day": 30.0,
            "is_indolent": False,
        }]
    )
    observations = pd.DataFrame(
        [{"patient_id": "p1", "day": 5.0, "alert_triggered": 0}]
    )
    with pytest.raises(ValueError, match="marked as non-recurrent"):
        evaluate_lead_time_and_overdetection(patients, observations)


def test_lead_time_rejects_observations_for_unmatched_patients():
    patients = pd.DataFrame(
        [{"patient_id": "p1", "true_recurrence_event": False, "is_indolent": False}]
    )
    observations = pd.DataFrame(
        [{"patient_id": "unknown", "day": 5.0, "alert_triggered": 0}]
    )
    with pytest.raises(ValueError, match="unknown patients"):
        evaluate_lead_time_and_overdetection(patients, observations)


def test_frozen_test_access_logger(tmp_path):
    """Verifies append-only frozen test set audit log."""
    log_file = tmp_path / "test_access.jsonl"
    logger = FrozenTestAccessLogger(log_file)

    logger.log_access(
        dataset_name="synthetic_g1_test",
        access_type="final_evaluation",
        caller="gemini_executor",
        purpose="phase_2_benchmark",
        num_samples=100,
    )

    history = logger.get_access_history("synthetic_g1_test")
    assert len(history) == 1
    assert history[0]["dataset_name"] == "synthetic_g1_test"
    assert history[0]["caller"] == "gemini_executor"


def test_model_regression_gate():
    """Verifies regression gate thresholds and leak detection trigger."""
    gate = ModelRegressionGate(min_auc=0.65, max_brier=0.20, max_ece=0.15)

    # 1. Healthy model
    res_pass = gate.evaluate({"roc_auc": 0.78, "brier_score": 0.14, "ece": 0.08})
    assert res_pass.passed

    # 2. Deficient model
    res_fail = gate.evaluate({"roc_auc": 0.58, "brier_score": 0.25, "ece": 0.20})
    assert res_pass.passed is not False
    assert not res_fail.passed

    # 3. Stop-and-think trigger: AUROC > 0.97 indicates leakage
    res_leaked = gate.evaluate({"roc_auc": 0.99, "brier_score": 0.02, "ece": 0.01})
    assert not res_leaked.passed
    assert any("STOP-AND-THINK TRIGGER" in f for f in res_leaked.failures)


def test_regression_gate_rejects_missing_candidate_and_baseline_metrics():
    gate = ModelRegressionGate()
    result = gate.evaluate({"roc_auc": 0.8}, baseline_metrics={"roc_auc": 0.7})
    assert not result.passed
    assert any("Candidate brier_score is missing" in failure for failure in result.failures)
    assert any("Baseline brier_score is missing" in failure for failure in result.failures)


def test_benchmark_table_marks_missing_metrics_as_unavailable():
    table = render_benchmark_table_markdown([{"model_id": "partial"}])
    assert "N/A" in table
    assert "0.0000" not in table
