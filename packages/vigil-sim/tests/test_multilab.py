"""vigil_sim.multilab: the laboratory layer used by EXP-K5-001."""

from __future__ import annotations

import numpy as np
import pytest
from vigil_sim.generators import GeneratorType, get_generator
from vigil_sim.multilab import LabShift, MultiLabConfig, apply_multilab, draw_true_beta


@pytest.fixture(scope="module")
def base():
    c = get_generator(GeneratorType.G1_SMOOTH, seed=11).generate_cohort(num_patients=250, duration_days=730.0)
    return c.to_observations_dataframe(), c.to_patients_dataframe()


def build(base, **kw):
    cfg = MultiLabConfig(**{"tau": 0.15, "switch_fraction": 0.3, "seed": 5, **kw})
    n = 8 if cfg.mode != "network" else 6
    return apply_multilab(base[0], base[1], cfg, draw_true_beta(9, cfg.tau, n))


def test_observation_columns_hide_the_truth(base):
    c = build(base)
    assert list(c.observations.columns) == ["patient_id", "visit_idx", "day", "calendar_day", "lab", "y"]
    assert not any(col.startswith("latent_") for col in c.observations.columns)


def test_value_is_clean_value_times_lab_bias(base):
    c = build(base)
    bias = c.observations["lab"].map(c.true_beta).to_numpy()
    assert np.allclose(c.observations["y"].to_numpy(), c.y_clean * np.exp(bias))


def test_deterministic_and_seed_sensitive(base):
    a, b, other = build(base), build(base), build(base, seed=6)
    assert a.observations.equals(b.observations)
    assert not a.observations["lab"].equals(other.observations["lab"])


def test_beta_draw_is_shared_across_tau_scale():
    a, b = draw_true_beta(3, 0.07, 6), draw_true_beta(3, 0.30, 6)
    assert all(b[k] == pytest.approx(a[k] * 0.30 / 0.07) for k in a)


def test_switch_fraction_and_one_switch_per_patient(base):
    c = build(base, switch_fraction=0.5)
    labs_per_pat = c.observations.groupby("patient_id")["lab"].nunique()
    assert labs_per_pat.max() <= 2
    share = (labs_per_pat == 2).mean()
    assert 0.3 < share < 0.6
    # a switcher moves once, and never back
    for _, g in c.observations.sort_values(["patient_id", "visit_idx"]).groupby("patient_id"):
        lab = g["lab"].to_numpy()
        assert (np.diff(lab) != 0).sum() <= 1


def test_no_switching_means_one_laboratory_per_patient(base):
    c = build(base, switch_fraction=0.0)
    assert c.observations.groupby("patient_id")["lab"].nunique().max() == 1


def test_case_mix_loads_advanced_stage_on_labs_0_and_1(base):
    c = build(base, case_mix=True, switch_fraction=0.0)
    p = c.patients
    adv = p["stage"].astype(str).str.upper().str.contains("III|IV")
    if adv.sum() >= 10 and (~adv).sum() >= 10:
        assert p.loc[adv, "home_lab"].isin([0, 1]).mean() > p.loc[~adv, "home_lab"].isin([0, 1]).mean() + 0.3


def test_shift_applies_only_to_the_lab_after_the_date(base):
    plain = build(base)
    shifted = build(base, shift=LabShift(lab=2, delta=0.2, calendar_day=365.0))
    o1, o2 = plain.observations, shifted.observations
    assert o1["lab"].equals(o2["lab"])
    ratio = (o2["y"] / o1["y"]).to_numpy()
    hit = ((o1["lab"] == 2) & (o1["calendar_day"] >= 365.0)).to_numpy()
    assert np.allclose(ratio[hit], np.exp(0.2))
    assert np.allclose(ratio[~hit], 1.0)


def test_new_site_training_adds_k_switchers_per_new_lab(base):
    c = build(base, mode="new_site_training", new_site_switchers=5)
    for new_lab in (6, 7):
        assert c.observations.loc[c.observations["lab"] == new_lab, "patient_id"].nunique() == 5


def test_new_site_eval_sends_switchers_to_new_labs_only(base):
    c = build(base, mode="new_site_eval", switch_fraction=0.4)
    switched = c.observations[c.observations["lab"] >= 6]
    assert len(switched) > 0
    first = c.observations.sort_values(["patient_id", "visit_idx"]).groupby("patient_id").first()
    assert first["lab"].max() <= 5  # nobody starts at a new laboratory


def test_missing_offsets_are_refused(base):
    with pytest.raises(ValueError):
        apply_multilab(base[0], base[1], MultiLabConfig(0.1, 0.1, 1, mode="new_site_eval"), draw_true_beta(1, 0.1, 6))
