"""M4 test-ladder properties P1 to P11 (docs/ml/M4-CONTRACT.md), plus the maths the engine relies on.

P11 (over HTTP) lives in apps/api/tests/test_test_ladder_route.py.
Everything here is a property or a metamorphic relation; none of it is a clinical validation.
"""

from __future__ import annotations

import dataclasses
import itertools
import json
import random
import re
from datetime import date, timedelta
from pathlib import Path

import pytest
from vigil_ml import m4_ladder as m4
from vigil_ml.m4_ladder import (
    AccuracyRange,
    Estimate,
    EvidenceSource,
    FacilityCapability,
    Interval,
    ModalityCapability,
    Prior,
    TestEvidence,
)

ROOT = Path(__file__).resolve().parents[3]
AS_OF = date(2026, 10, 18)
EVIDENCE_MD = (ROOT / "docs" / "EVIDENCE.md").read_text(encoding="utf-8")
EXCERPTS = ROOT / "docs" / "evidence" / "excerpts"

BANNED = re.compile(
    r"\b(ruled out|rule out|excluded|safe|normal|no cancer|negative means)\b", re.IGNORECASE
)


@pytest.fixture(scope="module")
def evidence():
    return m4.load_evidence()


@pytest.fixture(scope="module")
def templates():
    return m4.load_facility_templates()


def prior(v=0.2, lo=None, hi=None):
    return Prior(value=v, lo=v if lo is None else lo, hi=v if hi is None else hi, provenance="test")


def cap(modality, price=1, days=1, dist=1, verified=None, available=True):
    return ModalityCapability(
        modality=modality,
        available=available,
        turnaround_days=days if available else None,
        price_band=price,
        distance_band=dist,
        source="test fixture",
        verified_on=verified,
    )


def facility(rows, fid="F", illustrative=False):
    return FacilityCapability(fid, fid, "test", illustrative, tuple(rows))


def sourced(organ, modality, se, sp, interval=True):
    def est(v):
        if interval:
            return Estimate(value=v, lo=max(0.0, v - 0.05), hi=min(1.0, v + 0.05), basis="ci")
        return Estimate(value=v, lo=None, hi=None, basis="point")

    src = EvidenceSource("E20", "x.md", "test", False, "test", (est(se),), (est(sp),))
    return TestEvidence(organ, modality, "sourced", (src,))


# ------------------------------------------------------------------------------------------
# P1: evidence first
# ------------------------------------------------------------------------------------------
def _pct_forms(x: float):
    return {f"{x * 100:.1f}", f"{x * 100:g}", f"{x * 100:.0f}"}


def test_p1_every_registry_number_appears_in_its_excerpt(evidence):
    for (organ, modality), row in evidence.items():
        for src in row.sources:
            text = (EXCERPTS / src.excerpt).read_text(encoding="utf-8")
            for est in itertools.chain(src.sensitivity, src.specificity):
                if est.basis == "stratum":
                    # the stratum bound 1.0 is a logical bound, stated as such in the registry
                    nums = [est.lo]
                else:
                    nums = [x for x in (est.value, est.lo, est.hi) if x is not None]
                for x in nums:
                    assert any(f in text for f in _pct_forms(x)), (
                        f"{organ}/{modality}: {x} not found in {src.excerpt}"
                    )


def test_p1_registry_evidence_ids_exist_and_are_not_blocked(evidence):
    for (organ, modality), row in evidence.items():
        for src in row.sources:
            header = re.search(rf"^### {src.evidence_id} — .*$", EVIDENCE_MD, re.MULTILINE)
            assert header, f"{src.evidence_id} not in docs/EVIDENCE.md"
            assert "BLOCKED" not in header.group(0)
            assert (EXCERPTS / src.excerpt).is_file()


def test_p1_every_rung_carries_evidence_ids(evidence, templates):
    for organ in m4.ORGANS:
        for fac in templates.values():
            res = m4.recommend(organ, prior(), fac, AS_OF, evidence=evidence)
            for rung in res.rungs:
                assert rung.evidence_ids


def test_registry_status_values_and_unsourced_rows(evidence):
    assert {r.status for r in evidence.values()} <= {"sourced", "unsourced"}
    for key in [
        ("bone", "plain_radiograph"),
        ("bone", "alp_calcium_trend"),
        ("brain", "mri_brain"),
        ("brain", "ct_brain"),
    ]:
        assert evidence[key].status == "unsourced" and not evidence[key].sources
    for r in evidence.values():
        if r.status == "sourced":
            assert r.sources
        else:
            assert r.reason


# ------------------------------------------------------------------------------------------
# P2: unsourced pairs are never ranked
# ------------------------------------------------------------------------------------------
def test_p2_unsourced_never_in_ladder_even_when_cheapest_and_fresh(evidence):
    fac = facility(
        [
            cap("plain_radiograph", price=1, days=1, verified=AS_OF),
            cap("alp_calcium_trend", price=1, days=1, verified=AS_OF),
            cap("ct", price=3, days=3, verified=AS_OF),
        ]
    )
    res = m4.recommend("bone", prior(), fac, AS_OF, evidence=evidence)
    assert [r.modality for r in res.rungs] == ["ct"]
    assert {s.modality for s in res.skipped if s.reason_code == "unsourced"} == {
        "plain_radiograph",
        "alp_calcium_trend",
    }


def test_p2_adding_an_unsourced_row_changes_no_rung(evidence):
    fac = facility([cap("ct", price=3, days=3, verified=AS_OF), cap("mri", 4, 5, 1, AS_OF)])
    base = m4.recommend("liver", prior(), fac, AS_OF, evidence=evidence)
    ev2 = dict(evidence)
    ev2[("liver", "mystery_scan")] = TestEvidence("liver", "mystery_scan", "unsourced", (), "none")
    fac2 = facility([*fac.modalities, cap("mystery_scan", 1, 1, 1, AS_OF)])
    more = m4.recommend("liver", prior(), fac2, AS_OF, evidence=ev2)
    assert base.to_dict()["rungs"] == more.to_dict()["rungs"]
    assert base.outcome == more.outcome == "ladder"


def test_brain_has_no_sourced_option_anywhere(evidence, templates):
    res = m4.recommend(
        "brain",
        prior(0.1),
        templates["TEMPLATE-TERTIARY"],
        AS_OF,
        evidence=evidence,
        other_facilities=list(templates.values()),
    )
    assert res.outcome == "no_sourced_option" and not res.rungs and not res.referrals


# ------------------------------------------------------------------------------------------
# Maths: concavity, monotonicity, interval containment (relied on by the bounds)
# ------------------------------------------------------------------------------------------
def test_information_gain_is_zero_at_chance_and_for_extreme_priors():
    assert m4.information_gain(0.3, 0.7, 0.3) == pytest.approx(0.0, abs=1e-12)
    assert m4.information_gain(1e-12, 0.9, 0.9) == pytest.approx(0.0, abs=1e-9)


def test_information_gain_is_concave_in_the_prior():
    rng = random.Random(4001)
    for _ in range(500):
        se, sp = rng.uniform(0.3, 1), rng.uniform(0.3, 1)
        if se + sp < 1:
            continue
        a, b = sorted(rng.uniform(0.01, 0.99) for _ in range(2))
        t = rng.random()
        mid = t * a + (1 - t) * b
        lhs = m4.information_gain(mid, se, sp)
        rhs = t * m4.information_gain(a, se, sp) + (1 - t) * m4.information_gain(b, se, sp)
        assert lhs >= rhs - 1e-12


def test_p3_raising_sensitivity_or_specificity_never_lowers_gain_bounds():
    rng = random.Random(4002)
    for _ in range(800):
        se_lo = rng.uniform(0.2, 0.95)
        sp_lo = rng.uniform(max(0.0, 1.0 - se_lo), 0.97)
        se_hi = rng.uniform(se_lo, 1.0)
        sp_hi = rng.uniform(sp_lo, 1.0)
        pl = rng.uniform(0.02, 0.5)
        ph = rng.uniform(pl, 0.6)
        base = AccuracyRange(Interval(se_lo, se_hi), Interval(sp_lo, sp_hi), False)
        d_se = rng.uniform(0, 1 - se_hi)
        d_sp = rng.uniform(0, 1 - sp_hi)
        up = AccuracyRange(
            Interval(se_lo + d_se, se_hi + d_se), Interval(sp_lo + d_sp, sp_hi + d_sp), False
        )
        g0 = m4.gain_interval(Interval(pl, ph), base)
        g1 = m4.gain_interval(Interval(pl, ph), up)
        assert g1.lo >= g0.lo - 1e-12
        assert g1.hi >= g0.hi - 1e-12


def test_gain_interval_contains_every_point_inside_the_boxes():
    rng = random.Random(4003)
    for _ in range(300):
        se_lo = rng.uniform(0.3, 0.9)
        sp_lo = rng.uniform(max(0.0, 1.0 - se_lo), 0.95)
        acc = AccuracyRange(
            Interval(se_lo, min(1.0, se_lo + rng.uniform(0, 0.2))),
            Interval(sp_lo, min(1.0, sp_lo + rng.uniform(0, 0.2))),
            False,
        )
        pl = rng.uniform(0.02, 0.5)
        pr = Interval(pl, min(0.9, pl + rng.uniform(0, 0.3)))
        g = m4.gain_interval(pr, acc)
        for _ in range(20):
            p = rng.uniform(pr.lo, pr.hi)
            se = rng.uniform(acc.se.lo, acc.se.hi)
            sp = rng.uniform(acc.sp.lo, acc.sp.hi)
            v = m4.information_gain(p, se, sp)
            assert g.lo - 1e-9 <= v <= g.hi + 1e-9


def test_residual_and_positive_intervals_contain_every_point():
    rng = random.Random(4004)
    for _ in range(300):
        se_lo = rng.uniform(0.2, 0.95)
        sp_lo = rng.uniform(0.2, 0.95)
        acc = AccuracyRange(
            Interval(se_lo, min(1.0, se_lo + rng.uniform(0, 0.2))),
            Interval(sp_lo, min(1.0, sp_lo + rng.uniform(0, 0.2))),
            False,
        )
        pl = rng.uniform(0.01, 0.5)
        pr = Interval(pl, min(0.95, pl + rng.uniform(0, 0.3)))
        neg = m4.residual_after_negative(pr, acc)
        pos = m4.probability_after_positive(pr, acc)
        for _ in range(20):
            p = rng.uniform(pr.lo, pr.hi)
            se = rng.uniform(acc.se.lo, acc.se.hi)
            sp = rng.uniform(acc.sp.lo, acc.sp.hi)
            assert neg.lo - 1e-12 <= m4.posterior_negative(p, se, sp) <= neg.hi + 1e-12
            assert pos.lo - 1e-12 <= m4.posterior_positive(p, se, sp) <= pos.hi + 1e-12


def test_accuracy_range_is_a_computed_hull_with_assumed_widening_flag():
    liver_ct = sourced("liver", "ct", 0.72, 0.9, interval=True)
    acc = m4.accuracy_range(liver_ct)
    assert acc.se.lo == pytest.approx(0.67) and acc.se.hi == pytest.approx(0.77)
    assert not acc.assumed_widening
    point_only = sourced("liver", "ct", 0.72, 0.9, interval=False)
    acc2 = m4.accuracy_range(point_only)
    assert acc2.se.lo == pytest.approx(0.62) and acc2.se.hi == pytest.approx(0.82)
    assert acc2.assumed_widening
    # clipping
    top = m4.accuracy_range(sourced("liver", "ct", 0.97, 0.99, interval=False))
    assert top.se.hi == 1.0 and top.sp.hi == 1.0
    with pytest.raises(ValueError):
        m4.accuracy_range(TestEvidence("liver", "x", "unsourced", (), "no source"))


def test_hull_over_sources_takes_the_widest_extent():
    s1 = EvidenceSource(
        "E21",
        "a.md",
        "all",
        False,
        "d",
        (Estimate(0.86, None, None, "point"),),
        (Estimate(0.814, None, None, "point"),),
    )
    s2 = EvidenceSource(
        "E21",
        "b.md",
        "breast",
        True,
        "d",
        (Estimate(0.97, None, None, "point"),),
        (Estimate(0.97, None, None, "point"),),
    )
    acc = m4.accuracy_range(TestEvidence("bone", "mri", "sourced", (s1, s2)))
    assert acc.se.lo == pytest.approx(0.76) and acc.se.hi == 1.0
    assert acc.sp.lo == pytest.approx(0.714) and acc.sp.hi == 1.0


# ------------------------------------------------------------------------------------------
# Ladder construction
# ------------------------------------------------------------------------------------------
def test_dominated_test_is_dropped_and_ladder_is_ordered(evidence):
    # liver, tertiary-like: MRI costs more and takes longer than CT, with a lower IG lower bound.
    fac = facility(
        [
            cap("ultrasound", 1, 1, 1, AS_OF),
            cap("ct", 3, 2, 1, AS_OF),
            cap("mri", 4, 5, 1, AS_OF),
        ]
    )
    res = m4.recommend("liver", prior(0.2), fac, AS_OF, evidence=evidence)
    mods = [r.modality for r in res.rungs]
    assert "mri" not in mods
    assert {s.modality for s in res.skipped if s.reason_code == "dominated"} == {"mri"}
    keys = [(r.price_band, r.turnaround_days, -r.information_gain_bits.lo) for r in res.rungs]
    assert keys == sorted(keys)
    assert mods[0] == "ultrasound"


def test_p6_stale_row_cannot_remove_a_fresh_row(evidence):
    # Liver CT has a higher information-gain lower bound than liver MRI (E20 intervals), so a CT
    # that is cheaper and faster would dominate the MRI if its staleness were ignored.
    fresh_mri = cap("mri", 4, 5, 1, AS_OF - timedelta(days=10))
    stale_ct = cap("ct", 1, 1, 1, AS_OF - timedelta(days=800))
    res = m4.recommend(
        "liver", prior(0.2), facility([fresh_mri, stale_ct]), AS_OF, evidence=evidence
    )
    mods = {r.modality for r in res.rungs}
    assert mods == {"mri", "ct"}
    stale = [r for r in res.rungs if r.modality == "ct"]
    assert all(r.availability_confidence == "stale" and r.confirm_availability for r in stale)
    # the same rows, both fresh: the CT dominates and the MRI leaves the ladder
    both_fresh = facility([fresh_mri, cap("ct", 1, 1, 1, AS_OF)])
    res2 = m4.recommend("liver", prior(0.2), both_fresh, AS_OF, evidence=evidence)
    assert [r.modality for r in res2.rungs] == ["ct"]


def test_availability_confidence_classes():
    base = cap("ct")
    assert m4.availability_confidence(base, AS_OF) == "unverified"
    fresh = dataclasses.replace(base, verified_on=AS_OF - timedelta(days=365))
    assert m4.availability_confidence(fresh, AS_OF) == "fresh"
    stale = dataclasses.replace(base, verified_on=AS_OF - timedelta(days=366))
    assert m4.availability_confidence(stale, AS_OF) == "stale"
    future = dataclasses.replace(base, verified_on=AS_OF + timedelta(days=1))
    assert m4.availability_confidence(future, AS_OF) == "unverified"


def test_fresh_dominates_stale_when_it_is_better_everywhere(evidence):
    fresh_ct = cap("ct", 1, 1, 1, AS_OF)
    stale_mri = cap("mri", 4, 5, 1, AS_OF - timedelta(days=900))
    res = m4.recommend(
        "liver", prior(0.2), facility([fresh_ct, stale_mri]), AS_OF, evidence=evidence
    )
    assert [r.modality for r in res.rungs] == ["ct"]


def test_non_informative_row_is_not_ranked_and_says_why():
    ev = {
        ("lung", "chest_radiograph"): sourced("lung", "chest_radiograph", 0.30, 0.65),
    }
    fac = facility([cap("chest_radiograph", 1, 1, 1, AS_OF)])
    res = m4.recommend("lung", prior(0.2), fac, AS_OF, evidence=ev)
    assert not res.rungs
    assert [s.reason_code for s in res.skipped] == ["not_shown_informative"]


def test_affordability_band_filters_with_reason(evidence, templates):
    sec = templates["TEMPLATE-SECONDARY"]
    res = m4.recommend("lung", prior(0.1), sec, AS_OF, evidence=evidence, max_price_band=1)
    assert not res.rungs
    assert any(s.reason_code == "above_price_band" for s in res.skipped)
    assert res.outcome == "no_sourced_option"


def test_unavailable_and_not_offered_are_reported(evidence, templates):
    res = m4.recommend(
        "bone", prior(0.3), templates["TEMPLATE-SECONDARY"], AS_OF, evidence=evidence
    )
    codes = {s.modality: s.reason_code for s in res.skipped}
    assert codes["bone_scintigraphy"] == "unavailable"
    assert codes["mri"] == "not_offered"


def test_refer_orders_other_facilities_by_distance_then_price(evidence, templates):
    prim = templates["TEMPLATE-PRIMARY"]
    far = facility([cap("ct", 2, 1, 4, AS_OF)], fid="FAR")
    near_dear = facility([cap("ct", 4, 1, 2, AS_OF)], fid="NEAR_DEAR")
    near_cheap = facility([cap("ct", 2, 1, 2, AS_OF)], fid="NEAR_CHEAP")
    res = m4.recommend(
        "bone",
        prior(0.3),
        prim,
        AS_OF,
        evidence=evidence,
        other_facilities=[far, near_dear, near_cheap, prim],
    )
    assert res.outcome == "refer"
    assert [r.facility_id for r in res.referrals] == ["NEAR_CHEAP", "NEAR_DEAR", "FAR"]
    assert all(r.facility_id != prim.facility_id for r in res.referrals)


def test_lung_chest_radiograph_alone_is_not_shown_informative_in_the_registry(evidence, templates):
    """A consequence of the registry, recorded as a test so it cannot change silently.

    The sources for chest radiography (E22) give sensitivity down to 0.20 (literature range
    quoted in the paper) and specificity down to 0.78 (point 0.88 widened by 0.10), so the lower
    corner has sensitivity + specificity of 0.98, below 1.
    """
    acc = m4.accuracy_range(evidence[("lung", "chest_radiograph")])
    assert acc.se.lo == pytest.approx(0.20) and acc.sp.lo == pytest.approx(0.78)
    assert not acc.informative
    res = m4.recommend(
        "lung",
        prior(0.1),
        templates["TEMPLATE-PRIMARY"],
        AS_OF,
        evidence=evidence,
        other_facilities=list(templates.values()),
    )
    assert res.outcome == "refer"
    assert res.referrals[0].facility_id == "TEMPLATE-SECONDARY"


def test_the_widening_assumption_decides_the_chest_radiograph_result(evidence):
    """Sensitivity analysis recorded in the open: with a narrower assumed widening the
    chest radiograph passes the informativeness rule. The rule is not tuned to either result."""
    row = evidence[("lung", "chest_radiograph")]
    assert not m4.accuracy_range(row, 0.10).informative
    assert m4.accuracy_range(row, 0.05).informative


# ------------------------------------------------------------------------------------------
# P4: order invariance; P5: stability
# ------------------------------------------------------------------------------------------
def test_p4_input_row_order_does_not_change_the_output(evidence, templates):
    rng = random.Random(4005)
    for organ in m4.ORGANS:
        for fac in templates.values():
            base = m4.recommend(
                organ,
                prior(0.2, 0.1, 0.3),
                fac,
                AS_OF,
                evidence=evidence,
                other_facilities=list(templates.values()),
            ).to_dict()
            for _ in range(5):
                rows = list(fac.modalities)
                rng.shuffle(rows)
                ev_items = list(evidence.items())
                rng.shuffle(ev_items)
                others = list(templates.values())
                rng.shuffle(others)
                out = m4.recommend(
                    organ,
                    prior(0.2, 0.1, 0.3),
                    dataclasses.replace(fac, modalities=tuple(rows)),
                    AS_OF,
                    evidence=dict(ev_items),
                    other_facilities=others,
                ).to_dict()
                assert out == base


def _signature(res):
    return (
        res.outcome,
        tuple(r.modality for r in res.rungs),
        tuple(r.facility_id for r in res.referrals),
    )


def test_p5_prior_perturbation_leaves_seeded_worked_examples_unchanged(evidence, templates):
    for organ in m4.ORGANS:
        for fac in templates.values():
            for p in (0.05, 0.1, 0.2, 0.35):
                a = m4.recommend(
                    organ,
                    prior(p),
                    fac,
                    AS_OF,
                    evidence=evidence,
                    other_facilities=list(templates.values()),
                )
                b = m4.recommend(
                    organ,
                    prior(p + 0.01),
                    fac,
                    AS_OF,
                    evidence=evidence,
                    other_facilities=list(templates.values()),
                )
                assert _signature(a) == _signature(b), (organ, fac.facility_id, p)


def test_p5_random_registries_change_only_when_gain_bounds_are_close():
    rng = random.Random(4006)
    mods = ["ultrasound", "ct", "mri", "fdg_pet"]
    for trial in range(200):
        ev = {}
        rows = []
        for m in mods:
            se = rng.uniform(0.5, 0.95)
            sp = rng.uniform(0.6, 0.98)
            ev[("liver", m)] = sourced("liver", m, se, sp)
            rows.append(cap(m, rng.randint(1, 4), rng.randint(1, 5), 1, AS_OF))
        fac = facility(rows)
        p = rng.uniform(0.05, 0.4)
        a = m4.recommend("liver", prior(p), fac, AS_OF, evidence=ev)
        b = m4.recommend("liver", prior(p + 1e-6), fac, AS_OF, evidence=ev)
        if _signature(a) != _signature(b):
            los = sorted(r.information_gain_bits.lo for r in (*a.rungs, *b.rungs))
            gaps = [y - x for x, y in zip(los, los[1:])]
            # some pair of compared IG lower bounds lies within 1e-4
            assert min(gaps) < 1e-4, trial


# ------------------------------------------------------------------------------------------
# P7, P8, P9, P10
# ------------------------------------------------------------------------------------------
def _all_results(evidence, templates):
    for organ in m4.ORGANS:
        for fac in templates.values():
            for pr in (prior(0.05), prior(0.2, 0.1, 0.4), prior(0.6, 0.5, 0.7)):
                yield m4.recommend(
                    organ,
                    pr,
                    fac,
                    AS_OF,
                    evidence=evidence,
                    other_facilities=list(templates.values()),
                )


def test_p7_negative_result_residual_is_present_bounded_and_positive(evidence, templates):
    n = 0
    for res in _all_results(evidence, templates):
        for r in res.rungs:
            n += 1
            lo, hi = r.residual_after_negative.lo, r.residual_after_negative.hi
            assert 0.0 <= lo <= hi <= 1.0
            if r.sensitivity.hi < 1.0 and res.prior.hi > 0:
                assert hi > 0.0
            assert hi > 0.0 or r.sensitivity.lo == 1.0
            d = r.to_dict()
            assert "probability_remaining_after_negative" in d
    assert n > 20


def _strings(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def test_p8_no_forbidden_wording_and_negative_never_excludes(evidence, templates):
    n = 0
    for res in _all_results(evidence, templates):
        d = res.to_dict()
        assert d["negative_result_excludes_involvement"] is False
        for s in _strings(d):
            n += 1
            assert not BANNED.search(s), s
    assert n > 100


def test_p8_registry_json_has_no_forbidden_wording():
    for name in ("m4_test_evidence.json", "m4_facility_templates.json"):
        text = (m4.REGISTRY_DIR / name).read_text(encoding="utf-8")
        for s in _strings(json.loads(text)):
            assert not BANNED.search(s), (name, s)


def test_p9_assumed_widening_is_flagged_on_every_output_that_depends_on_it(evidence, templates):
    flagged = 0
    for res in _all_results(evidence, templates):
        d = res.to_dict()
        if any(r["assumed_widening"] for r in d["rungs"]):
            flagged += 1
            assert any("assumed widening" in n for n in d["notes"])
        else:
            assert not any("assumed widening" in n for n in d["notes"])
    assert flagged > 0
    # liver rows come with intervals: no widening is assumed or flagged
    res = m4.recommend("liver", prior(), templates["TEMPLATE-TERTIARY"], AS_OF, evidence=evidence)
    assert not any(r.assumed_widening for r in res.rungs)


def test_other_population_is_printed_with_the_recommendation(evidence, templates):
    res = m4.recommend("liver", prior(), templates["TEMPLATE-TERTIARY"], AS_OF, evidence=evidence)
    assert any("other cancers" in n for n in res.to_dict()["notes"])
    assert all(r.populations and not r.includes_breast_population for r in res.rungs)


def test_p10_deterministic_and_clock_and_random_free(evidence, templates):
    a = [r.to_dict() for r in _all_results(evidence, templates)]
    b = [r.to_dict() for r in _all_results(evidence, templates)]
    assert a == b
    src = Path(m4.__file__).read_text(encoding="utf-8")
    for needle in (
        "datetime.now",
        "date.today",
        "import random",
        "time.time",
        "numpy.random",
        "np.random",
        "uuid",
    ):
        assert needle not in src, needle


# ------------------------------------------------------------------------------------------
# Priors and templates
# ------------------------------------------------------------------------------------------
def test_prior_validation():
    for bad in [(0.0, 0.0, 0.0), (0.5, 0.6, 0.7), (0.5, 0.4, 0.45), (1.0, 1.0, 1.0)]:
        with pytest.raises(ValueError):
            Prior(*bad, provenance="x")
    with pytest.raises(ValueError):
        Prior(0.2, 0.1, 0.3, provenance=" ")
    with pytest.raises(ValueError):
        m4.recommend("ovary", prior(), facility([]), AS_OF)


def test_m1_and_m4_prior_conversion_fail_closed_while_m1_is_quarantined():
    from vigil_ml.organ_susceptibility import BaselineOrganSusceptibilityModelM1

    with pytest.raises(RuntimeError, match="quarantined"):
        BaselineOrganSusceptibilityModelM1().predict_susceptibility("TNBC", "Stage II", 50.0)
    with pytest.raises(RuntimeError, match="quarantined"):
        m4.prior_from_m1(object(), "liver", (0.05, 0.15))


def test_facility_templates_are_illustrative_and_unverified(templates):
    assert set(templates) == {"TEMPLATE-PRIMARY", "TEMPLATE-SECONDARY", "TEMPLATE-TERTIARY"}
    for fac in templates.values():
        assert fac.illustrative
        for m in fac.modalities:
            assert m.verified_on is None and m.source == "ILLUSTRATIVE-TEMPLATE"
    res = m4.recommend("liver", prior(), templates["TEMPLATE-TERTIARY"], AS_OF)
    assert res.illustrative_facility
    assert any("illustrative tier template" in n for n in res.notes)
    assert all(
        r.availability_confidence == "unverified" and r.confirm_availability for r in res.rungs
    )


def test_worked_examples_file_is_exactly_what_the_script_writes():
    """docs/ml/M4-WORKED-EXAMPLES.md carries no hand-typed number: regenerate and compare."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "m4_worked_examples", ROOT / "scripts" / "m4_worked_examples.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert (ROOT / "docs" / "ml" / "M4-WORKED-EXAMPLES.md").read_text(
        encoding="utf-8"
    ) == mod.render()
