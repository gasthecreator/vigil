from __future__ import annotations

from vigil_sim.e1_comparison import evaluate_e1_source_comparison
from vigil_sim.generators import (
    BreastCancerSubtype,
    CohortDataset,
    GeneratorType,
    LongitudinalObservation,
    PatientBaseline,
    PresentationStage,
)


def _patient(
    patient_id: str,
    *,
    true_event: bool = False,
    true_day: float | None = None,
    true_site: str | None = None,
    observed_event: bool = False,
    observed_day: float | None = None,
    observed_site: str | None = None,
    competing_event: str | None = None,
    competing_day: float | None = None,
    admin_day: float = 100.0,
) -> PatientBaseline:
    return PatientBaseline(
        patient_id=patient_id,
        age=50.0,
        stage=PresentationStage.STAGE_II,
        subtype=BreastCancerSubtype.HR_POS_HER2_NEG,
        er_status=True,
        pr_status=True,
        her2_status=False,
        true_recurrence_event=true_event,
        true_recurrence_day=true_day,
        true_recurrence_site=true_site,
        is_indolent=False,
        observed_recurrence_event=observed_event,
        observed_recurrence_day=observed_day,
        observed_recurrence_site=observed_site,
        competing_event=competing_event,
        competing_event_day=competing_day,
        generator_id=GeneratorType.G1_SMOOTH.value,
        facility_id="FACILITY-TEST",
        out_of_pocket_delay_factor=1.0,
        administrative_censor_day=admin_day,
    )


def _observation(
    observation_id: str,
    patient_id: str,
    day: float,
    value: object,
    *,
    observed: bool = True,
) -> LongitudinalObservation:
    return LongitudinalObservation(
        observation_id=observation_id,
        patient_id=patient_id,
        day=day,
        date_drawn="2026-01-01",
        analytes={"ca_15_3": value},  # type: ignore[dict-item]
        observed_mask={"ca_15_3": observed},
        symptoms={},
        imaging_performed=False,
    )


def _cohort(patients, observations) -> CohortDataset:
    return CohortDataset(
        patients=patients,
        observations=observations,
        latent_states=[],
        generator_type=GeneratorType.G1_SMOOTH,
        seed=91,
    )


def test_source_aligned_e1_metrics_use_strict_prediagnosis_measured_values():
    patients = [
        _patient(
            "case",
            true_event=True,
            true_day=60.0,
            true_site="bone",
            observed_event=True,
            observed_day=80.0,
            observed_site="bone",
        ),
        _patient("ned-negative"),
        _patient("occult", true_event=True, true_day=70.0, true_site="liver"),
        _patient("false-positive"),
        _patient("ned-unmeasured"),
        _patient("lost", competing_event="lost_to_follow_up", competing_day=70.0),
        _patient("incomplete", admin_day=80.0),
    ]
    observations = [
        _observation("case-hidden", "case", 40.0, 1000.0, observed=False),
        _observation("case-at-cutoff", "case", 70.0, 60.0),
        _observation("case-elevated", "case", 79.0, 60.0001),
        _observation("case-same-day", "case", 80.0, 1000.0),
        _observation("case-after", "case", 81.0, 1000.0),
        _observation("ned-marker", "ned-negative", 90.0, 60.0),
        _observation("occult-marker", "occult", 90.0, 61.0),
        _observation("false-marker", "false-positive", 90.0, 61.0),
        _observation("lost-marker", "lost", 50.0, 60.0),
        _observation("incomplete-marker", "incomplete", 50.0, 60.0),
    ]

    report = evaluate_e1_source_comparison(
        _cohort(patients, observations), administrative_followup_days=100.0
    )

    assert report["ca_15_3_cutoff"]["value"] == 60.0
    assert report["ca_15_3_cutoff"]["comparison"] == ">"
    assert report["case_detection"] == {
        "diagnosed_cases": 1,
        "monitored_cases": 1,
        "not_monitored_cases": 0,
        "detected_cases": 1,
        "fraction_monitored_detected": 1.0,
        "fraction_all_diagnosed_detected": 1.0,
    }
    assert report["conditional_lead_time"]["mean_days"] == 1.0
    assert report["observed_ned_specificity"] == {
        "eligible_ned_patients": 4,
        "measured_ned_patients": 3,
        "unmeasured_ned_patients": 1,
        "negative_measured_ned_patients": 1,
        "specificity": 1.0 / 3.0,
        "latent_undiagnosed_cases_may_be_included": True,
    }
    assert report["oracle_recurrence_free_specificity"]["specificity"] == 0.5
    assert report["e1_distant_recurrence_sensitivity"]["status"] == "not_estimable"
    assert report["synthetic_only"] is True


def test_e1_empty_cohort_keeps_undefined_metrics_null():
    report = evaluate_e1_source_comparison(_cohort([], []), administrative_followup_days=100.0)

    assert report["case_detection"]["fraction_monitored_detected"] is None
    assert report["conditional_lead_time"]["mean_days"] is None
    assert report["observed_ned_specificity"]["specificity"] is None


def test_e1_rejects_contradictory_observed_event_fields():
    patient = _patient("bad", observed_event=True, observed_day=50.0, observed_site="bone")

    try:
        evaluate_e1_source_comparison(_cohort([patient], []), administrative_followup_days=100.0)
    except ValueError as exc:
        assert "contradicts latent recurrence" in str(exc)
    else:
        raise AssertionError("contradictory observed event was accepted")


def test_e1_rejects_observed_diagnosis_after_patient_censoring():
    patient = _patient(
        "censored-before-diagnosis",
        true_event=True,
        true_day=30.0,
        true_site="bone",
        observed_event=True,
        observed_day=50.0,
        observed_site="bone",
        admin_day=40.0,
    )

    try:
        evaluate_e1_source_comparison(_cohort([patient], []), administrative_followup_days=100.0)
    except ValueError as exc:
        assert "after patient administrative censoring" in str(exc)
    else:
        raise AssertionError("diagnosis after patient censoring was accepted")


def test_e1_rejects_unregistered_locoregional_site_instead_of_scoring_it():
    patient = _patient(
        "locoregional",
        true_event=True,
        true_day=40.0,
        true_site="breast",
        observed_event=True,
        observed_day=50.0,
        observed_site="breast",
    )

    try:
        evaluate_e1_source_comparison(_cohort([patient], []), administrative_followup_days=100.0)
    except ValueError as exc:
        assert "unregistered" in str(exc)
    else:
        raise AssertionError("unregistered site was treated as a valid E1 comparison")


def test_e1_rejects_unknown_patients_and_boolean_observed_values():
    unknown = _observation("unknown", "missing-patient", 10.0, 5.0)
    try:
        evaluate_e1_source_comparison(
            _cohort([_patient("known")], [unknown]), administrative_followup_days=100.0
        )
    except ValueError as exc:
        assert "unknown patient_id" in str(exc)
    else:
        raise AssertionError("observation with an unknown patient was accepted")

    boolean_value = _observation("bool", "known", 10.0, True)
    try:
        evaluate_e1_source_comparison(
            _cohort([_patient("known")], [boolean_value]), administrative_followup_days=100.0
        )
    except ValueError as exc:
        assert "finite numeric values" in str(exc)
    else:
        raise AssertionError("boolean measurement was accepted")
