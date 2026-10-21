"""Source-aligned, synthetic-only CA 15-3 comparison for E1.

This module is separate from ``calibration.evaluate_cohort_calibration`` so its
new observed-diagnosis estimand cannot silently rewrite historical reports.
The result is conditional on simulator assumptions and is not clinical
calibration or a diagnostic recommendation.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

import numpy as np
from vigil_core.analytes import ANALYTE_REGISTRY
from vigil_core.units import convert_units

from vigil_sim.generators import SUPPORTED_COMPETING_EVENTS, CohortDataset

E1_CA153_CUTOFF_U_PER_ML = 60.0
E1_CA153_CUTOFF_SOURCE = "docs/evidence/E1.md: Molina et al. 1995 excerpt"
MONTH_DAYS = 365.2425 / 12.0
SUPPORTED_RECURRENCE_SITES = frozenset({"bone", "lung", "liver", "brain"})


def _finite_nonnegative(value: object, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ValueError(f"{name} must be a finite non-negative number")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise ValueError(f"{name} must be a finite non-negative number")
    return number


def _positive_finite(value: object, name: str) -> float:
    number = _finite_nonnegative(value, name)
    if number == 0.0:
        raise ValueError(f"{name} must be positive")
    return number


def _observed_event(patient: Any, followup_days: float) -> tuple[bool, float | None]:
    event = patient.observed_recurrence_event
    if not isinstance(event, (bool, np.bool_)):
        raise ValueError("observed_recurrence_event must be boolean")
    day = patient.observed_recurrence_day
    site = patient.observed_recurrence_site
    if event:
        diagnosis_day = _finite_nonnegative(day, "observed_recurrence_day")
        if diagnosis_day > followup_days:
            raise ValueError("observed diagnosis occurs after administrative follow-up")
        if not isinstance(site, str) or not site.strip():
            raise ValueError("observed recurrence requires a non-empty site")
        if site not in SUPPORTED_RECURRENCE_SITES:
            raise ValueError(
                f"unregistered recurrence site {site!r}; E1 site-stratified comparison is unavailable"
            )
        if not patient.true_recurrence_event:
            raise ValueError("observed diagnosis contradicts latent recurrence status")
        if patient.true_recurrence_site != site:
            raise ValueError("observed recurrence site contradicts simulator site")
        # The source-aligned endpoint is observed diagnosis. In configured G1,
        # burden seeding precedes true_recurrence_day, so this nominal event
        # field is not a lower bound on when verification can occur.
        _finite_nonnegative(patient.true_recurrence_day, "true_recurrence_day")
        return True, diagnosis_day
    if day is not None or site is not None:
        raise ValueError("non-event patient has contradictory observed recurrence fields")
    return False, None


def evaluate_e1_source_comparison(
    cohort: CohortDataset, *, administrative_followup_days: float
) -> dict[str, Any]:
    """Evaluate preregistered E1 quantities on a single synthetic cohort.

    An elevated marker means strictly greater than the source's 60 U/mL cutoff.
    Only finite values with a true observation mask count. Cases use observed
    diagnosis time and only observations strictly before it.
    """
    followup_days = _positive_finite(administrative_followup_days, "administrative_followup_days")
    analyte = ANALYTE_REGISTRY["ca_15_3"]
    cutoff = convert_units(
        E1_CA153_CUTOFF_U_PER_ML,
        from_unit="U/mL",
        to_unit=analyte.canonical_unit,
        analyte_code=analyte.code,
    )
    if not math.isfinite(cutoff) or cutoff <= 0:
        raise ValueError("converted E1 cutoff must be finite and positive")

    patients: dict[str, Any] = {}
    diagnosis_days: dict[str, float | None] = {}
    observed_events: dict[str, bool] = {}
    complete_followup: dict[str, bool] = {}
    competing_days: dict[str, float | None] = {}
    for patient in cohort.patients:
        patient_id = patient.patient_id
        if not isinstance(patient_id, str) or not patient_id.strip():
            raise ValueError("patient_id must be a non-empty string")
        if patient_id in patients:
            raise ValueError(f"duplicate patient_id {patient_id!r}")
        if not isinstance(patient.true_recurrence_event, (bool, np.bool_)):
            raise ValueError("true_recurrence_event must be boolean")
        admin_censor = _finite_nonnegative(
            patient.administrative_censor_day, "administrative_censor_day"
        )
        if (patient.competing_event is None) != (patient.competing_event_day is None):
            raise ValueError(
                "competing_event and competing_event_day must be jointly present or absent"
            )
        if patient.competing_event_day is None:
            competing_days[patient_id] = None
        else:
            event_day = _finite_nonnegative(patient.competing_event_day, "competing_event_day")
            if not isinstance(patient.competing_event, str) or not patient.competing_event.strip():
                raise ValueError("competing event requires a non-empty event name")
            if patient.competing_event not in SUPPORTED_COMPETING_EVENTS:
                raise ValueError(f"unsupported competing event {patient.competing_event!r}")
            competing_days[patient_id] = event_day
        complete_followup[patient_id] = admin_censor >= followup_days
        if patient.true_recurrence_event:
            _finite_nonnegative(patient.true_recurrence_day, "true_recurrence_day")
            if (
                not isinstance(patient.true_recurrence_site, str)
                or not patient.true_recurrence_site.strip()
            ):
                raise ValueError("latent recurrence requires a non-empty site")
            if patient.true_recurrence_site not in SUPPORTED_RECURRENCE_SITES:
                raise ValueError(
                    f"unregistered latent recurrence site {patient.true_recurrence_site!r}"
                )
        elif patient.true_recurrence_day is not None or patient.true_recurrence_site is not None:
            raise ValueError("non-recurrent patient has contradictory latent recurrence fields")
        observed, diagnosis_day = _observed_event(patient, followup_days)
        if observed and diagnosis_day > admin_censor:
            raise ValueError("observed diagnosis occurs after patient administrative censoring")
        observed_events[patient_id] = observed
        diagnosis_days[patient_id] = diagnosis_day
        if (
            observed
            and competing_days[patient_id] is not None
            and competing_days[patient_id] <= diagnosis_day
        ):
            raise ValueError("observed diagnosis follows a terminal competing or censoring event")
        patients[patient_id] = patient

    by_patient: dict[str, list[tuple[float, float]]] = defaultdict(list)
    observation_ids: set[str] = set()
    for observation in cohort.observations:
        if observation.patient_id not in patients:
            raise ValueError(
                f"observation references unknown patient_id {observation.patient_id!r}"
            )
        if (
            not isinstance(observation.observation_id, str)
            or not observation.observation_id.strip()
        ):
            raise ValueError("observation_id must be a non-empty string")
        if observation.observation_id in observation_ids:
            raise ValueError(f"duplicate observation_id {observation.observation_id!r}")
        observation_ids.add(observation.observation_id)
        day = _finite_nonnegative(observation.day, "observation day")
        if day > followup_days:
            raise ValueError("observation occurs after administrative follow-up")
        patient = patients[observation.patient_id]
        patient_admin = float(patient.administrative_censor_day)
        if day > patient_admin:
            raise ValueError("observation occurs after patient administrative censoring")
        competing_day = competing_days[observation.patient_id]
        if competing_day is not None and competing_day < day:
            raise ValueError("observation occurs after a competing or censoring event")
        mask = observation.observed_mask.get("ca_15_3", False)
        if not isinstance(mask, (bool, np.bool_)):
            raise ValueError("CA 15-3 observed_mask must be boolean")
        if not mask:
            # Do not inspect hidden values behind an unobserved mask.
            continue
        value = observation.analytes.get("ca_15_3")
        if (
            isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))
            or not math.isfinite(float(value))
        ):
            raise ValueError("observed CA 15-3 values must be finite numeric values")
        by_patient[observation.patient_id].append((day, float(value)))

    diagnosed_cases = 0
    monitored_cases = 0
    detected_cases = 0
    lead_times_days: list[float] = []
    observed_ned_total = 0
    observed_ned_measured = 0
    observed_ned_negative = 0
    oracle_ned_total = 0
    oracle_ned_measured = 0
    oracle_ned_negative = 0

    for patient_id, patient in patients.items():
        values = sorted(by_patient.get(patient_id, []), key=lambda item: item[0])
        diagnosis_day = diagnosis_days[patient_id]
        if observed_events[patient_id]:
            diagnosed_cases += 1
            prediagnosis = [(day, value) for day, value in values if day < diagnosis_day]
            if prediagnosis:
                monitored_cases += 1
                elevations = [(day, value) for day, value in prediagnosis if value > cutoff]
                if elevations:
                    detected_cases += 1
                    lead_times_days.append(diagnosis_day - elevations[0][0])
            continue

        has_interruption = False
        competing_day = competing_days[patient_id]
        if competing_day is not None:
            has_interruption = competing_day <= followup_days
        if not complete_followup[patient_id] or has_interruption:
            continue

        observed_ned_total += 1
        if not patient.true_recurrence_event:
            oracle_ned_total += 1
        if values:
            observed_ned_measured += 1
            is_negative = all(value <= cutoff for _, value in values)
            observed_ned_negative += int(is_negative)
            if not patient.true_recurrence_event:
                oracle_ned_measured += 1
                oracle_ned_negative += int(is_negative)

    def ratio(numerator: int, denominator: int) -> float | None:
        return numerator / denominator if denominator else None

    lead_mean_days = float(np.mean(lead_times_days)) if lead_times_days else None
    lead_sd_days = float(np.std(lead_times_days, ddof=1)) if len(lead_times_days) > 1 else None
    return {
        "schema_version": 1,
        "synthetic_only": True,
        "estimand": "source_aligned_observed_diagnosis",
        "generator": cohort.generator_type.value,
        "seed": int(cohort.seed),
        "num_patients": len(patients),
        "num_observations": len(observation_ids),
        "administrative_followup_days": followup_days,
        "ca_15_3_cutoff": {
            "value": float(cutoff),
            "source_value": E1_CA153_CUTOFF_U_PER_ML,
            "source_unit": "U/mL",
            "canonical_unit": analyte.canonical_unit,
            "source": E1_CA153_CUTOFF_SOURCE,
            "comparison": ">",
        },
        "case_detection": {
            "diagnosed_cases": diagnosed_cases,
            "monitored_cases": monitored_cases,
            "not_monitored_cases": diagnosed_cases - monitored_cases,
            "detected_cases": detected_cases,
            "fraction_monitored_detected": ratio(detected_cases, monitored_cases),
            "fraction_all_diagnosed_detected": ratio(detected_cases, diagnosed_cases),
        },
        "conditional_lead_time": {
            "n_detected_monitored_cases": len(lead_times_days),
            "mean_days": lead_mean_days,
            "sample_sd_days": lead_sd_days,
            "mean_months": lead_mean_days / MONTH_DAYS if lead_mean_days is not None else None,
            "sample_sd_months": lead_sd_days / MONTH_DAYS if lead_sd_days is not None else None,
            "published_dispersion_comparable": False,
            "published_dispersion_note": "E1 abstract reports ± 2.3 months without defining the dispersion statistic.",
        },
        "observed_ned_specificity": {
            "eligible_ned_patients": observed_ned_total,
            "measured_ned_patients": observed_ned_measured,
            "unmeasured_ned_patients": observed_ned_total - observed_ned_measured,
            "negative_measured_ned_patients": observed_ned_negative,
            "specificity": ratio(observed_ned_negative, observed_ned_measured),
            "latent_undiagnosed_cases_may_be_included": True,
        },
        "oracle_recurrence_free_specificity": {
            "eligible_recurrence_free_patients": oracle_ned_total,
            "measured_recurrence_free_patients": oracle_ned_measured,
            "negative_measured_patients": oracle_ned_negative,
            "specificity": ratio(oracle_ned_negative, oracle_ned_measured),
            "synthetic_oracle_only": True,
        },
        "e1_distant_recurrence_sensitivity": {
            "status": "not_estimable",
            "reason": "The configured G1/G2/G3 recurrence-site mechanism has no locoregional recurrence class, so the source's locoregional-excluded denominator cannot be reconstructed.",
        },
        "limits": [
            "Synthetic mechanism-conditional result; not clinical calibration.",
            "Observed-NED controls may include latent recurrence without observed diagnosis.",
            "Marker elevation is not a diagnosis or evidence of clinical benefit.",
        ],
    }
