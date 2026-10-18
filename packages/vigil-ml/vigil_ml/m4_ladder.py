"""
vigil_ml.m4_ladder

M4 test-escalation ladder. The specification is docs/ml/M4-CONTRACT.md, committed before this
file. This module is a deterministic, stateless function of its arguments: it reads no clock, no
random numbers, no database and no network. ``as_of`` is a caller-supplied date.

What it does: for one organ it takes a prior probability of involvement (always an interval),
the accuracy sources in ``registry/m4_test_evidence.json`` and one facility's capability rows,
and returns the Pareto-non-dominated set of tests on (price band, turnaround days, information
gain lower bound), together with the residual probability after either result, as intervals.

What it never does (contract section 2): it does not output a diagnosis, a stage, a "negative
means clear" statement, or a single number for the weight of cost against information. There is
no numeric cost weight. A test whose accuracy has no source is not recommended, and a test whose
lower accuracy corner is not better than chance is not recommended.

The information gain used is the expected reduction in binary entropy of the involvement
indicator, in bits. It is concave in the prior and, while sensitivity + specificity >= 1,
monotone non-decreasing in sensitivity and in specificity (the lower operating point can be
reached by garbling the output of the higher one). Both facts are exercised as properties in
packages/vigil-ml/tests/test_m4_ladder.py.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

REGISTRY_DIR = Path(__file__).resolve().parent / "registry"
EVIDENCE_PATH = REGISTRY_DIR / "m4_test_evidence.json"
FACILITY_TEMPLATES_PATH = REGISTRY_DIR / "m4_facility_templates.json"

ORGANS = ("bone", "liver", "lung", "brain")

#: Half-width applied to a point estimate that has no published interval. This is an assumption
#: of M4, not a finding of any paper; every output that depends on it says so.
ASSUMED_HALFWIDTH = 0.10

#: A facility row verified more than this many days before ``as_of`` is "stale".
STALE_AFTER_DAYS = 365

NEGATIVE_RESULT_STATEMENT = (
    "A negative result lowers the probability of involvement but leaves the remaining "
    "probability shown. It does not establish that the organ is free of metastasis."
)
SCOPE_STATEMENT = (
    "Decision support for a clinician. Not a diagnosis. Accuracy figures come from published "
    "studies of the populations named on each row, which may differ from this patient."
)

Number = Union[int, float]


# --------------------------------------------------------------------------------------------
# Value types
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Interval:
    lo: float
    hi: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.lo <= self.hi <= 1.0):
            raise ValueError(f"invalid interval [{self.lo}, {self.hi}]")

    def to_dict(self) -> Dict[str, float]:
        return {"lo": self.lo, "hi": self.hi}


@dataclass(frozen=True)
class Prior:
    """Probability that the organ is involved, as an interval with a stated provenance."""

    value: float
    lo: float
    hi: float
    provenance: str

    def __post_init__(self) -> None:
        if not (0.0 < self.lo <= self.value <= self.hi < 1.0):
            raise ValueError(
                "prior must satisfy 0 < lo <= value <= hi < 1; got "
                f"lo={self.lo} value={self.value} hi={self.hi}"
            )
        if not self.provenance.strip():
            raise ValueError("a prior must state its provenance")

    @property
    def interval(self) -> Interval:
        return Interval(self.lo, self.hi)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "lo": self.lo,
            "hi": self.hi,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class Estimate:
    value: Optional[float]
    lo: Optional[float]
    hi: Optional[float]
    basis: str
    note: str = ""


@dataclass(frozen=True)
class EvidenceSource:
    evidence_id: str
    excerpt: str
    population: str
    breast_population: bool
    design: str
    sensitivity: Tuple[Estimate, ...]
    specificity: Tuple[Estimate, ...]


@dataclass(frozen=True)
class TestEvidence:
    __test__ = False  # not a pytest class

    organ: str
    modality: str
    status: str  # "sourced" | "unsourced"
    sources: Tuple[EvidenceSource, ...] = ()
    reason: str = ""


@dataclass(frozen=True)
class AccuracyRange:
    se: Interval
    sp: Interval
    assumed_widening: bool

    @property
    def informative(self) -> bool:
        """True when even the lower corner is not worse than chance (se_lo + sp_lo >= 1)."""
        return self.se.lo + self.sp.lo >= 1.0


@dataclass(frozen=True)
class ModalityCapability:
    modality: str
    available: bool
    turnaround_days: Optional[int]
    price_band: int
    distance_band: int
    source: str
    verified_on: Optional[date]


@dataclass(frozen=True)
class FacilityCapability:
    facility_id: str
    name: str
    tier: str
    illustrative: bool
    modalities: Tuple[ModalityCapability, ...]

    def row(self, modality: str) -> Optional[ModalityCapability]:
        for m in self.modalities:
            if m.modality == modality:
                return m
        return None


# --------------------------------------------------------------------------------------------
# Registry loading
# --------------------------------------------------------------------------------------------
def _estimate(d: Mapping[str, Any]) -> Estimate:
    return Estimate(
        value=d.get("value"),
        lo=d.get("lo"),
        hi=d.get("hi"),
        basis=d["basis"],
        note=d.get("note", ""),
    )


def load_evidence(path: Path = EVIDENCE_PATH) -> Dict[Tuple[str, str], TestEvidence]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[Tuple[str, str], TestEvidence] = {}
    for r in data["rows"]:
        sources = tuple(
            EvidenceSource(
                evidence_id=s["evidence_id"],
                excerpt=s["excerpt"],
                population=s["population"],
                breast_population=bool(s["breast_population"]),
                design=s["design"],
                sensitivity=tuple(_estimate(e) for e in s["sensitivity"]),
                specificity=tuple(_estimate(e) for e in s["specificity"]),
            )
            for s in r.get("sources", [])
        )
        key = (r["organ"], r["modality"])
        if key in out:
            raise ValueError(f"duplicate evidence row {key}")
        out[key] = TestEvidence(
            organ=r["organ"],
            modality=r["modality"],
            status=r["status"],
            sources=sources,
            reason=r.get("reason", ""),
        )
    return out


def facility_from_dict(d: Mapping[str, Any]) -> FacilityCapability:
    mods = []
    for m in d["modalities"]:
        v = m.get("verified_on")
        mods.append(
            ModalityCapability(
                modality=m["modality"],
                available=bool(m["available"]),
                turnaround_days=m.get("turnaround_days"),
                price_band=int(m["price_band"]),
                distance_band=int(m["distance_band"]),
                source=m["source"],
                verified_on=date.fromisoformat(v) if isinstance(v, str) else v,
            )
        )
    return FacilityCapability(
        facility_id=d["facility_id"],
        name=d["name"],
        tier=d["tier"],
        illustrative=bool(d.get("illustrative", False)),
        modalities=tuple(mods),
    )


def load_facility_templates(path: Path = FACILITY_TEMPLATES_PATH) -> Dict[str, FacilityCapability]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {f["facility_id"]: facility_from_dict(f) for f in data["facilities"]}


# --------------------------------------------------------------------------------------------
# Probability and information quantities
# --------------------------------------------------------------------------------------------
def _entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * math.log2(p) + (1.0 - p) * math.log2(1.0 - p))


def information_gain(prior: float, se: float, sp: float) -> float:
    """Expected reduction in binary entropy, in bits, from one test with (se, sp)."""
    p_pos = prior * se + (1.0 - prior) * (1.0 - sp)
    p_neg = 1.0 - p_pos
    h_after = 0.0
    if p_pos > 0.0:
        h_after += p_pos * _entropy(prior * se / p_pos)
    if p_neg > 0.0:
        h_after += p_neg * _entropy(prior * (1.0 - se) / p_neg)
    return max(0.0, _entropy(prior) - h_after)


def posterior_negative(prior: float, se: float, sp: float) -> float:
    """P(involved | negative result)."""
    num = prior * (1.0 - se)
    den = num + (1.0 - prior) * sp
    return num / den if den > 0.0 else 0.0


def posterior_positive(prior: float, se: float, sp: float) -> float:
    """P(involved | positive result)."""
    num = prior * se
    den = num + (1.0 - prior) * (1.0 - sp)
    return num / den if den > 0.0 else 0.0


def _max_gain_over_prior(prior: Interval, se: float, sp: float) -> float:
    """Maximum of the concave gain over a prior interval, by ternary search (deterministic)."""
    lo, hi = prior.lo, prior.hi
    for _ in range(200):
        a = lo + (hi - lo) / 3.0
        b = hi - (hi - lo) / 3.0
        if information_gain(a, se, sp) < information_gain(b, se, sp):
            lo = a
        else:
            hi = b
    return information_gain((lo + hi) / 2.0, se, sp)


def gain_interval(prior: Interval, acc: AccuracyRange) -> Interval:
    """Lower and upper bound of the information gain over the prior and accuracy intervals.

    Lower bound: concave in the prior, so its minimum is at a prior endpoint; monotone in the
    accuracy while se + sp >= 1, so use the lower accuracy corner. Upper bound: the upper corner,
    maximised over the prior interval. Requires ``acc.informative``.
    """
    lo = min(
        information_gain(prior.lo, acc.se.lo, acc.sp.lo),
        information_gain(prior.hi, acc.se.lo, acc.sp.lo),
    )
    hi = _max_gain_over_prior(prior, acc.se.hi, acc.sp.hi)
    return Interval(lo, max(lo, hi))


def residual_after_negative(prior: Interval, acc: AccuracyRange) -> Interval:
    """Interval for P(involved | negative). Increasing in prior, decreasing in se and sp."""
    return Interval(
        posterior_negative(prior.lo, acc.se.hi, acc.sp.hi),
        posterior_negative(prior.hi, acc.se.lo, acc.sp.lo),
    )


def probability_after_positive(prior: Interval, acc: AccuracyRange) -> Interval:
    """Interval for P(involved | positive). Increasing in prior, se and sp."""
    return Interval(
        posterior_positive(prior.lo, acc.se.lo, acc.sp.lo),
        posterior_positive(prior.hi, acc.se.hi, acc.sp.hi),
    )


def accuracy_range(row: TestEvidence, halfwidth: float = ASSUMED_HALFWIDTH) -> AccuracyRange:
    """Hull of every source estimate for one sourced row (contract section 4)."""
    if row.status != "sourced" or not row.sources:
        raise ValueError(f"{row.organ}/{row.modality} has no accuracy source")

    def hull(estimates: Sequence[Estimate]) -> Tuple[Interval, bool]:
        spans: List[Tuple[float, float, bool]] = []
        for e in estimates:
            if e.lo is not None and e.hi is not None:
                spans.append((float(e.lo), float(e.hi), False))
            elif e.value is not None:
                spans.append((max(0.0, e.value - halfwidth), min(1.0, e.value + halfwidth), True))
            else:
                raise ValueError("estimate with neither a value nor an interval")
        lo = min(s[0] for s in spans)
        hi = max(s[1] for s in spans)
        widened = any((s[2] and (s[0] == lo or s[1] == hi)) for s in spans)
        return Interval(lo, hi), widened

    all_se = [e for s in row.sources for e in s.sensitivity]
    all_sp = [e for s in row.sources for e in s.specificity]
    se, w1 = hull(all_se)
    sp, w2 = hull(all_sp)
    return AccuracyRange(se=se, sp=sp, assumed_widening=w1 or w2)


# --------------------------------------------------------------------------------------------
# Priors
# --------------------------------------------------------------------------------------------
def prior_from_m1(
    m1_prediction: Any,
    organ: str,
    p_any_metastasis: Union[Number, Tuple[Number, Number]],
) -> Prior:
    """Build an organ prior from an M1 prediction and a probability of any metastasis.

    M1 gives the *share* of metastases that go to each organ (a distribution over sites). The
    probability that an organ is involved is therefore approximated as share x P(any
    metastasis). This is an approximation: it ignores multi-site disease, and the share is
    defined among patients who do have a metastasis. The caller owns ``p_any_metastasis``
    (for example from M2); M4 does not invent it.
    """
    if organ not in ORGANS:
        raise ValueError(f"unknown organ {organ!r}")
    if isinstance(p_any_metastasis, tuple):
        p_lo, p_hi = float(p_any_metastasis[0]), float(p_any_metastasis[1])
        p_mid = (p_lo + p_hi) / 2.0
    else:
        p_lo = p_hi = p_mid = float(p_any_metastasis)
    share = float(m1_prediction.probabilities[organ])
    s_lo, s_hi = (float(x) for x in m1_prediction.credible_intervals_95[organ])
    return Prior(
        value=share * p_mid,
        lo=s_lo * p_lo,
        hi=s_hi * p_hi,
        provenance=(
            f"M1 organ share ({share:.3f}, 95% interval {s_lo:.3f} to {s_hi:.3f}) multiplied by a "
            f"caller-supplied probability of any metastasis ({p_lo:.3f} to {p_hi:.3f}); "
            "approximation, see prior_from_m1 docstring"
        ),
    )


# --------------------------------------------------------------------------------------------
# Ladder
# --------------------------------------------------------------------------------------------
def availability_confidence(
    row: ModalityCapability, as_of: date, stale_after_days: int = STALE_AFTER_DAYS
) -> str:
    if row.verified_on is None:
        return "unverified"
    age = (as_of - row.verified_on).days
    if age < 0:
        return "unverified"  # a verification date in the future is not evidence
    return "fresh" if age <= stale_after_days else "stale"


@dataclass(frozen=True)
class Rung:
    modality: str
    evidence_ids: Tuple[str, ...]
    populations: Tuple[str, ...]
    includes_breast_population: bool
    sensitivity: Interval
    specificity: Interval
    assumed_widening: bool
    information_gain_bits: Interval
    residual_after_negative: Interval
    probability_after_positive: Interval
    price_band: int
    turnaround_days: int
    distance_band: int
    availability_confidence: str
    confirm_availability: bool
    facility_id: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "modality": self.modality,
            "facility_id": self.facility_id,
            "evidence_ids": list(self.evidence_ids),
            "populations": list(self.populations),
            "includes_breast_population": self.includes_breast_population,
            "sensitivity": self.sensitivity.to_dict(),
            "specificity": self.specificity.to_dict(),
            "assumed_widening": self.assumed_widening,
            "information_gain_bits": self.information_gain_bits.to_dict(),
            "probability_remaining_after_negative": self.residual_after_negative.to_dict(),
            "probability_after_positive": self.probability_after_positive.to_dict(),
            "price_band": self.price_band,
            "turnaround_days": self.turnaround_days,
            "distance_band": self.distance_band,
            "availability_confidence": self.availability_confidence,
            "confirm_availability": self.confirm_availability,
        }


@dataclass(frozen=True)
class Referral:
    facility_id: str
    name: str
    tier: str
    illustrative: bool
    distance_band: int
    price_band: int
    first_modality: str
    availability_confidence: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "facility_id": self.facility_id,
            "name": self.name,
            "tier": self.tier,
            "illustrative": self.illustrative,
            "distance_band": self.distance_band,
            "price_band": self.price_band,
            "first_modality": self.first_modality,
            "availability_confidence": self.availability_confidence,
        }


@dataclass(frozen=True)
class Skipped:
    modality: str
    reason_code: str
    reason: str

    def to_dict(self) -> Dict[str, str]:
        return {"modality": self.modality, "reason_code": self.reason_code, "reason": self.reason}


@dataclass(frozen=True)
class LadderResult:
    organ: str
    outcome: str  # "ladder" | "refer" | "no_sourced_option"
    prior: Prior
    as_of: date
    facility_id: str
    illustrative_facility: bool
    rungs: Tuple[Rung, ...]
    referrals: Tuple[Referral, ...]
    skipped: Tuple[Skipped, ...]
    notes: Tuple[str, ...] = field(default_factory=tuple)
    negative_result_excludes_involvement: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "organ": self.organ,
            "outcome": self.outcome,
            "prior": self.prior.to_dict(),
            "as_of": self.as_of.isoformat(),
            "facility_id": self.facility_id,
            "illustrative_facility": self.illustrative_facility,
            "rungs": [r.to_dict() for r in self.rungs],
            "referrals": [r.to_dict() for r in self.referrals],
            "skipped": [s.to_dict() for s in self.skipped],
            "notes": list(self.notes),
            "negative_result_excludes_involvement": self.negative_result_excludes_involvement,
            "negative_result_statement": NEGATIVE_RESULT_STATEMENT,
            "scope_statement": SCOPE_STATEMENT,
        }


def _dominates(a: Rung, b: Rung) -> bool:
    """True when ``a`` is at least as good as ``b`` on every axis and better on one.

    Axes: lower price band, lower turnaround, higher information-gain lower bound. A row whose
    availability is not fresh can never dominate a fresh row.
    """
    if a.availability_confidence != "fresh" and b.availability_confidence == "fresh":
        return False
    no_worse = (
        a.price_band <= b.price_band
        and a.turnaround_days <= b.turnaround_days
        and a.information_gain_bits.lo >= b.information_gain_bits.lo
    )
    better = (
        a.price_band < b.price_band
        or a.turnaround_days < b.turnaround_days
        or a.information_gain_bits.lo > b.information_gain_bits.lo
    )
    return no_worse and better


def _rung_order(r: Rung) -> Tuple[Any, ...]:
    return (r.price_band, r.turnaround_days, -r.information_gain_bits.lo, r.modality)


def _evaluate_facility(
    organ: str,
    prior: Prior,
    facility: FacilityCapability,
    evidence: Mapping[Tuple[str, str], TestEvidence],
    as_of: date,
    max_price_band: Optional[int],
    halfwidth: float,
) -> Tuple[List[Rung], List[Skipped]]:
    rungs: List[Rung] = []
    skipped: List[Skipped] = []
    organ_rows = sorted((k[1] for k in evidence if k[0] == organ))
    for modality in organ_rows:
        ev = evidence[(organ, modality)]
        cap = facility.row(modality)
        if cap is None:
            skipped.append(
                Skipped(
                    modality, "not_offered", "No capability row for this test at this facility."
                )
            )
            continue
        if not cap.available or cap.turnaround_days is None:
            skipped.append(Skipped(modality, "unavailable", "Recorded as not available here."))
            continue
        if ev.status != "sourced":
            skipped.append(
                Skipped(
                    modality,
                    "unsourced",
                    "No accuracy source is registered for this test, so M4 does not rank it. "
                    + ev.reason,
                )
            )
            continue
        if max_price_band is not None and cap.price_band > max_price_band:
            skipped.append(
                Skipped(
                    modality,
                    "above_price_band",
                    f"Price band {cap.price_band} is above the stated limit {max_price_band}.",
                )
            )
            continue
        acc = accuracy_range(ev, halfwidth)
        if not acc.informative:
            skipped.append(
                Skipped(
                    modality,
                    "not_shown_informative",
                    "At the lower end of the registered accuracy range the test is no better "
                    f"than chance (sensitivity {acc.se.lo:.3f} + specificity {acc.sp.lo:.3f} < 1), "
                    "so the sources do not show that it is informative.",
                )
            )
            continue
        conf = availability_confidence(cap, as_of)
        prior_iv = prior.interval
        rungs.append(
            Rung(
                modality=modality,
                evidence_ids=tuple(sorted({s.evidence_id for s in ev.sources})),
                populations=tuple(s.population for s in ev.sources),
                includes_breast_population=any(s.breast_population for s in ev.sources),
                sensitivity=acc.se,
                specificity=acc.sp,
                assumed_widening=acc.assumed_widening,
                information_gain_bits=gain_interval(prior_iv, acc),
                residual_after_negative=residual_after_negative(prior_iv, acc),
                probability_after_positive=probability_after_positive(prior_iv, acc),
                price_band=cap.price_band,
                turnaround_days=cap.turnaround_days,
                distance_band=cap.distance_band,
                availability_confidence=conf,
                confirm_availability=conf != "fresh",
                facility_id=facility.facility_id,
            )
        )
    return rungs, skipped


def _pareto(rungs: Sequence[Rung]) -> List[Rung]:
    front = [r for r in rungs if not any(_dominates(o, r) for o in rungs if o is not r)]
    return sorted(front, key=_rung_order)


def recommend(
    organ: str,
    prior: Prior,
    facility: FacilityCapability,
    as_of: date,
    *,
    evidence: Optional[Mapping[Tuple[str, str], TestEvidence]] = None,
    other_facilities: Sequence[FacilityCapability] = (),
    max_price_band: Optional[int] = None,
    halfwidth: float = ASSUMED_HALFWIDTH,
) -> LadderResult:
    """Return the test ladder for one organ at one facility. Pure and deterministic."""
    if organ not in ORGANS:
        raise ValueError(f"unknown organ {organ!r}; expected one of {ORGANS}")
    ev = evidence if evidence is not None else load_evidence()

    rungs, skipped = _evaluate_facility(
        organ, prior, facility, ev, as_of, max_price_band, halfwidth
    )
    ladder = _pareto(rungs)
    dominated = [r for r in rungs if r not in ladder]
    for r in dominated:
        skipped.append(
            Skipped(
                r.modality,
                "dominated",
                "Another available test is no worse on price band, turnaround and information "
                "gain lower bound, and better on at least one.",
            )
        )

    notes: List[str] = []
    if facility.illustrative:
        notes.append(
            "This facility is an illustrative tier template, not a real facility; availability, "
            "price bands and turnaround are placeholders."
        )
    if any(r.assumed_widening for r in ladder):
        notes.append(
            f"Some accuracy ranges include an assumed widening of plus or minus {halfwidth:.2f} "
            "applied to estimates that have no published interval."
        )
    if any(not r.includes_breast_population for r in ladder):
        notes.append(
            "Some accuracy figures come from studies of other cancers or of other populations "
            "than breast cancer; see the populations listed on each row."
        )

    if ladder:
        return LadderResult(
            organ=organ,
            outcome="ladder",
            prior=prior,
            as_of=as_of,
            facility_id=facility.facility_id,
            illustrative_facility=facility.illustrative,
            rungs=tuple(ladder),
            referrals=(),
            skipped=tuple(sorted(skipped, key=lambda s: (s.reason_code, s.modality))),
            notes=tuple(notes),
        )

    referrals: List[Referral] = []
    for other in other_facilities:
        if other.facility_id == facility.facility_id:
            continue
        o_rungs, _ = _evaluate_facility(organ, prior, other, ev, as_of, max_price_band, halfwidth)
        o_ladder = _pareto(o_rungs)
        if not o_ladder:
            continue
        first = o_ladder[0]
        referrals.append(
            Referral(
                facility_id=other.facility_id,
                name=other.name,
                tier=other.tier,
                illustrative=other.illustrative,
                distance_band=first.distance_band,
                price_band=first.price_band,
                first_modality=first.modality,
                availability_confidence=first.availability_confidence,
            )
        )
    referrals.sort(key=lambda r: (r.distance_band, r.price_band, r.facility_id))
    if referrals:
        notes.append(
            "No sourced, informative test is available at this facility; the registry lists other "
            "facilities that offer one. Confirm availability before sending the patient."
        )
        outcome = "refer"
    else:
        notes.append(
            "No sourced, informative test is available at this facility or at any other facility "
            "in the registry. This is a statement about the registry, not about the patient."
        )
        outcome = "no_sourced_option"
    return LadderResult(
        organ=organ,
        outcome=outcome,
        prior=prior,
        as_of=as_of,
        facility_id=facility.facility_id,
        illustrative_facility=facility.illustrative,
        rungs=(),
        referrals=tuple(referrals),
        skipped=tuple(sorted(skipped, key=lambda s: (s.reason_code, s.modality))),
        notes=tuple(notes),
    )


__all__ = [
    "ASSUMED_HALFWIDTH",
    "AccuracyRange",
    "Estimate",
    "EvidenceSource",
    "FacilityCapability",
    "Interval",
    "LadderResult",
    "ModalityCapability",
    "NEGATIVE_RESULT_STATEMENT",
    "ORGANS",
    "Prior",
    "Referral",
    "Rung",
    "SCOPE_STATEMENT",
    "Skipped",
    "STALE_AFTER_DAYS",
    "TestEvidence",
    "accuracy_range",
    "availability_confidence",
    "facility_from_dict",
    "gain_interval",
    "information_gain",
    "load_evidence",
    "load_facility_templates",
    "posterior_negative",
    "posterior_positive",
    "prior_from_m1",
    "probability_after_positive",
    "recommend",
    "residual_after_negative",
]
