from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import vigil_ml.causal_k7_grouped as k7


def test_grouped_crossfit_keeps_bootstrap_copies_in_one_fold():
    cohort = k7.generate_cohort(n_patients=1000, seed=71304, unmeasured_confounding=False)
    draws = np.random.default_rng(25).integers(0, len(cohort.patient_ids), size=1000)
    groups = draws.copy()
    _, _, _, _, digest = k7._crossfit_nuisance(
        cohort.covariates[draws],
        cohort.treatment[draws],
        cohort.outcome[draws],
        groups,
        fold_seed=515,
    )
    assert len(digest) == 64


def test_estimator_rejects_misaligned_or_noninteger_patient_groups():
    cohort = k7.generate_cohort(n_patients=500, seed=71305, unmeasured_confounding=False)
    with pytest.raises(ValueError, match="integer source-patient"):
        k7.estimate_effects(
            cohort.covariates,
            cohort.treatment,
            cohort.outcome,
            cohort.covariate_names,
            fold_seed=515,
            group_ids=np.array(["patient"] * 500),
        )


def test_k7_004_seed_namespaces_are_injective_and_disjoint():
    path = Path(__file__).resolve().parents[3] / "experiments" / "EXP-S8-K7-004" / "run.py"
    spec = importlib.util.spec_from_file_location("k7_004_runner", path)
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    runner.validate_seed_namespaces()
    namespaces = runner.purpose_seeds()
    sets = [set(values) for values in namespaces.values()]
    assert [len(values) for values in namespaces.values()] == [40, 40, 40000]
    assert all(not sets[i].intersection(sets[j]) for i in range(3) for j in range(i + 1, 3))
    assert not any(set(runner.SEEDS).intersection(values) for values in sets)
