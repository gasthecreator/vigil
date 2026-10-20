from __future__ import annotations

import numpy as np
import pytest
import vigil_ml.causal_k7_replacement as k7


def test_generator_is_reproducible_and_delay_matches_registered_treatment():
    first = k7.generate_cohort(n_patients=500, seed=71301, unmeasured_confounding=False)
    second = k7.generate_cohort(n_patients=500, seed=71301, unmeasured_confounding=False)
    np.testing.assert_array_equal(first.covariates, second.covariates)
    np.testing.assert_array_equal(first.treatment, second.treatment)
    np.testing.assert_array_equal(first.outcome, second.outcome)
    np.testing.assert_array_equal(first.treatment, first.delay_days > 56)
    assert np.all((first.delay_days >= 14) & (first.delay_days <= 180))
    assert first.unmeasured_confounder is None


def test_measured_inputs_exclude_u_and_paired_conditions_share_baseline():
    measured = k7.generate_cohort(n_patients=500, seed=71302, unmeasured_confounding=False)
    hidden = k7.generate_cohort(n_patients=500, seed=71302, unmeasured_confounding=True)
    np.testing.assert_array_equal(measured.covariates, hidden.covariates)
    assert measured.covariates.shape[1] == len(measured.covariate_names) == 6
    assert hidden.unmeasured_confounder is not None
    assert hidden.unmeasured_confounder.shape == (500,)
    assert not np.array_equal(hidden.unmeasured_confounder, hidden.covariates[:, 0])


def test_estimator_refits_nuisance_models_without_held_out_rows(monkeypatch):
    n = 100
    x = np.column_stack((np.arange(n, dtype=float), np.ones(n)))
    a = np.tile(np.array([0, 1], dtype=np.int64), n // 2)
    y = (np.arange(n) // 2 % 2).astype(np.int64)
    fitted_rows: list[set[int]] = []

    class SpyModel:
        def fit(self, features, labels):
            fitted_rows.append(set(features[:, 0].astype(int)))
            self.classes_ = np.array([0, 1])
            return self

        def predict_proba(self, features):
            return np.column_stack((np.full(len(features), 0.5), np.full(len(features), 0.5)))

    monkeypatch.setattr(k7, "_model", SpyModel)
    k7.estimate_effects(x, a, y, ("row_id", "constant"), fold_seed=5)
    assert len(fitted_rows) == 15  # propensity and two outcome models in each of five folds
    splitter = k7.StratifiedKFold(n_splits=5, shuffle=True, random_state=5)
    expected_heldouts = [set(test.tolist()) for _, test in splitter.split(x, a)]
    for fold in range(5):
        for fitted in fitted_rows[fold * 3 : (fold + 1) * 3]:
            assert fitted.isdisjoint(expected_heldouts[fold])


def test_cross_fitted_estimators_run_with_finite_diagnostics():
    cohort = k7.generate_cohort(n_patients=1000, seed=71303, unmeasured_confounding=False)
    estimate = k7.estimate_effects(
        cohort.covariates,
        cohort.treatment,
        cohort.outcome,
        cohort.covariate_names,
        fold_seed=1_071_303,
    )
    assert estimate["n_patients"] == 1000
    assert estimate["weight_diagnostics"]["maximum_stabilized_weight"] <= 10.0
    assert set(estimate["estimates"]) == {"naive", "iptw", "gcomp", "aipw"}
    assert estimate["estimates"]["aipw"]["risk_ratio"] is not None
    assert estimate["covariate_balance"]["maximum_weighted_smd"] is not None


def test_zero_variance_smd_and_undefined_risk_ratio_are_not_substituted():
    assert k7.compute_smd(np.ones(4), np.array([0, 0, 1, 1])) == 0.0
    assert k7.compute_smd(np.array([0.0, 0.0, 1.0, 1.0]), np.array([0, 0, 1, 1])) is None
    assert k7._contrast(0.2, 0.0)["risk_ratio"] is None
    assert k7._contrast(0.2, 0.0)["undefined_reason"] is not None


def test_e_value_uses_ci_limit_nearest_null_for_both_directions():
    harmful = k7.compute_e_value(1.5, (1.2, 1.8))
    assert harmful["confidence_limit_nearest_null"] == pytest.approx(1.2 + np.sqrt(1.2 * 0.2))
    protective = k7.compute_e_value(0.5, (0.4, 0.8))
    inverse = 1 / 0.8
    assert protective["confidence_limit_nearest_null"] == pytest.approx(
        inverse + np.sqrt(inverse * (inverse - 1))
    )
    crosses_null = k7.compute_e_value(1.2, (0.9, 1.5))
    assert crosses_null["confidence_limit_nearest_null"] == 1.0


def test_bootstrap_count_cannot_be_changed_from_preregistered_value():
    with pytest.raises(ValueError, match="exactly 1000"):
        k7.bootstrap_inference(
            np.empty((0, 6)),
            np.empty(0, dtype=int),
            np.empty(0, dtype=int),
            ("a", "b", "c", "d", "e", "f"),
            fold_seed=1,
            bootstrap_seed=2,
            n_bootstrap=10,
        )


def test_bootstrap_refits_all_estimators_with_registered_replicate_seeds(monkeypatch):
    calls: list[int] = []

    def fake_estimate(covariates, treatment, outcome, names, *, fold_seed):
        calls.append(fold_seed)
        return {
            "estimates": {name: {"risk_ratio": 1.2} for name in ("naive", "iptw", "gcomp", "aipw")}
        }

    monkeypatch.setattr(k7, "estimate_effects", fake_estimate)
    x = np.zeros((100, 1), dtype=float)
    a = np.tile(np.array([0, 1], dtype=np.int64), 50)
    y = a.copy()
    result = k7.bootstrap_inference(x, a, y, ("x",), fold_seed=10_000, bootstrap_seed=20_000)
    assert len(calls) == 1000
    assert calls[0] == 10_001
    assert calls[-1] == 11_000
    for interval in result["confidence_intervals"].values():
        assert interval["ci_95"] == [pytest.approx(1.2), pytest.approx(1.2)]
