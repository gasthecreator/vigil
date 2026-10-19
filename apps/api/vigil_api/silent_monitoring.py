"""Silent-mode monitoring (PREREGISTRATION.md section 6).

Reads **only** the shadow store (predictions, imported outcomes, rejection counts) and computes the four
monitors the pre-registration names: alarm-rate audit, calibration drift, conformal coverage and data shift.
Every threshold comes from a ``Parameters`` object whose provenance is recorded in the report; this module has
no default for the alert budget (PR-04), because the pre-registration deliberately has none.

Operational definitions (each is a choice the pre-registration leaves open; each is printed in the report):
- A *landmark* is one patient-day (UTC date of the specimen). Its score is the maximum score of that day's
  predictions; it alerts if any prediction of that day would alert. This mirrors the evaluation's "an alert is
  counted at every landmark" (``docs/clinical/ANALYSIS-SPEC.md`` section 4).
- Patient-months of exposure: for each patient, the time between the first and the last specimen, in months of
  30.4375 days. A patient with one specimen contributes nothing, which overstates the alert rate slightly.
- A landmark's outcome is *determinable* when a recurrence is confirmed within ``horizon_days`` of it (y = 1), or
  when follow-up (the later of the last imported follow-up date and any recurrence date) reaches the horizon with
  no earlier recurrence (y = 0). Others are excluded and counted. A death from another cause before the horizon
  excludes the landmark (a competing risk, not modelled here).
- Calibration windows are consecutive, non-overlapping blocks of determinable landmarks, each closed when it holds
  at least PR-08 events. "The slope interval excludes [PR-01, PR-02]" is read literally: the 95 % Wald interval
  lies wholly outside that range. A interval that straddles a bound is reported as inconclusive, not as a breach.
- Data-shift windows are consecutive blocks of PR-08 landmark-days (missingness) or PR-08 ingestion attempts
  (rejection rate). "More than doubles" is evaluated against the first window; if the first window's rate is
  zero the ratio is undefined and the report says so instead of declaring a breach.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.stats import chi2, norm
from sqlalchemy import select

from vigil_api.governance_attestation import attest_monitor_report
from vigil_api.shadow_store import (
    OUTCOME_TYPES,
    ShadowIngestRejection,
    ShadowOutcome,
    ShadowPrediction,
    ShadowStore,
)

MONTH_DAYS = 30.4375
STATUSES = ("OK", "BREACH", "INSUFFICIENT", "NOT_EVALUABLE", "NOT_MEASURABLE")


@dataclass(frozen=True)
class Parameters:
    slope_low: float  # PR-01
    slope_high: float  # PR-02
    alert_budget: Optional[float]  # PR-04, alerts per 100 patient-months; no default
    min_window: int  # PR-08
    coverage_shortfall: float  # PR-09
    provenance: str
    horizon_days: int = 365
    confidence: float = 0.95


# ---------------------------------------------------------------------------------------------- statistics


def poisson_exact_interval(k: int, level: float = 0.95) -> Tuple[float, float]:
    """Exact (Garwood) interval for a Poisson mean given k events."""
    a = 1.0 - level
    lo = 0.0 if k == 0 else float(chi2.ppf(a / 2.0, 2 * k) / 2.0)
    hi = float(chi2.ppf(1.0 - a / 2.0, 2 * k + 2) / 2.0)
    return lo, hi


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def logistic_slope(score: Sequence[float], y: Sequence[int], level: float = 0.95) -> Dict[str, Any]:
    """Calibration slope (coefficient of logit(score)) with a Wald interval, by Newton-Raphson.

    Returns ``{"status": "OK", slope, intercept, ci_low, ci_high}`` or ``{"status": "UNSTABLE"|"INSUFFICIENT"}``.
    """
    yv = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(score, dtype=float), 1e-6, 1 - 1e-6)
    x = np.log(p / (1 - p))
    if len(yv) < 3 or yv.sum() < 2 or (len(yv) - yv.sum()) < 2 or np.ptp(x) < 1e-9:
        return {"status": "INSUFFICIENT"}
    design = np.column_stack([np.ones_like(x), x])
    beta = np.zeros(2)
    for _ in range(100):
        mu = _sigmoid(design @ beta)
        w = mu * (1 - mu)
        grad = design.T @ (yv - mu)
        hess = design.T @ (design * w[:, None])
        try:
            step = np.linalg.solve(hess + 1e-12 * np.eye(2), grad)
        except np.linalg.LinAlgError:
            return {"status": "UNSTABLE"}
        beta_new = beta + step
        if not np.all(np.isfinite(beta_new)) or np.max(np.abs(beta_new)) > 50:
            return {"status": "UNSTABLE"}
        converged = np.max(np.abs(step)) < 1e-10
        beta = beta_new
        if converged:
            break
    else:
        return {"status": "UNSTABLE"}
    mu = _sigmoid(design @ beta)
    w = mu * (1 - mu)
    cov = np.linalg.inv(design.T @ (design * w[:, None]))
    se = math.sqrt(cov[1, 1])
    z = float(norm.ppf(1 - (1 - level) / 2))
    return {
        "status": "OK",
        "slope": float(beta[1]),
        "intercept": float(beta[0]),
        "ci_low": float(beta[1] - z * se),
        "ci_high": float(beta[1] + z * se),
    }


# ---------------------------------------------------------------------------------------------- data loading


@dataclass
class Landmark:
    patient_id: str
    day: Any  # datetime.date
    time: datetime
    score: float
    alert: bool
    analytes: Tuple[str, ...]


def _utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def load(store: ShadowStore) -> Dict[str, Any]:
    with store.session() as session:
        preds = session.execute(select(ShadowPrediction).order_by(ShadowPrediction.specimen_collected_at)).scalars().all()
        outcomes = session.execute(select(ShadowOutcome)).scalars().all()
        rejections = session.execute(select(ShadowIngestRejection).order_by(ShadowIngestRejection.recorded_at)).scalars().all()
        return {
            "predictions": [
                {
                    "patient_id": r.patient_id, "time": _utc(r.specimen_collected_at), "recorded_at": _utc(r.recorded_at),
                    "analyte": r.analyte_code, "score": r.score, "score_kind": r.score_kind,
                    "would_alert": bool(r.would_alert), "conformal_set": r.conformal_set,
                    "conformal_nominal": r.conformal_nominal,
                }
                for r in preds
            ],
            "outcomes": [
                {"patient_id": o.patient_id, "event_type": o.event_type, "time": _utc(o.event_time)} for o in outcomes
            ],
            "rejections": [
                {"analyte": r.analyte_code, "reason": r.reason, "recorded_at": _utc(r.recorded_at)} for r in rejections
            ],
        }


def landmarks_from(preds: List[Dict[str, Any]]) -> List[Landmark]:
    by_key: Dict[Tuple[str, Any], List[Dict[str, Any]]] = {}
    for p in preds:
        by_key.setdefault((p["patient_id"], p["time"].date()), []).append(p)
    out = [
        Landmark(
            patient_id=pid, day=day, time=min(x["time"] for x in rows),
            score=max(x["score"] for x in rows), alert=any(x["would_alert"] for x in rows),
            analytes=tuple(sorted({x["analyte"] for x in rows})),
        )
        for (pid, day), rows in by_key.items()
    ]
    out.sort(key=lambda lm: (lm.time, lm.patient_id))
    return out


def patient_outcomes(outcomes: List[Dict[str, Any]]) -> Dict[str, Dict[str, Optional[datetime]]]:
    info: Dict[str, Dict[str, Optional[datetime]]] = {}
    for o in outcomes:
        d = info.setdefault(o["patient_id"], {"recurrence": None, "followup_end": None, "death_other": None})
        if o["event_type"] == "recurrence_confirmed":
            if d["recurrence"] is None or o["time"] < d["recurrence"]:
                d["recurrence"] = o["time"]
        elif o["event_type"] == "last_followup":
            if d["followup_end"] is None or o["time"] > d["followup_end"]:
                d["followup_end"] = o["time"]
        elif o["event_type"] == "death_other":
            d["death_other"] = o["time"]
            if d["followup_end"] is None or o["time"] > d["followup_end"]:
                d["followup_end"] = o["time"]
    return info


def label(lm: Landmark, info: Dict[str, Dict[str, Optional[datetime]]], horizon_days: int) -> Optional[int]:
    """1 / 0 when determinable, None when not (see the module docstring)."""
    d = info.get(lm.patient_id)
    if d is None:
        return None
    horizon_end = lm.time + timedelta(days=horizon_days)
    rec = d["recurrence"]
    if rec is not None and rec <= lm.time:
        return None  # at or after the recurrence: not a surveillance landmark
    if rec is not None and rec <= horizon_end:
        return 1
    end = d["followup_end"]
    if rec is not None and (end is None or rec > end):
        end = rec
    if end is not None and end >= horizon_end:
        return 0
    return None


# ---------------------------------------------------------------------------------------------- monitors


def alarm_rate_audit(landmarks: List[Landmark], params: Parameters) -> Dict[str, Any]:
    alerts = sum(1 for lm in landmarks if lm.alert)
    by_patient: Dict[str, List[datetime]] = {}
    for lm in landmarks:
        by_patient.setdefault(lm.patient_id, []).append(lm.time)
    months = sum((max(t) - min(t)).total_seconds() / 86400.0 / MONTH_DAYS for t in by_patient.values())
    out: Dict[str, Any] = {
        "alerts": alerts, "landmarks": len(landmarks), "patients": len(by_patient),
        "patient_months": round(months, 4), "budget_per_100_patient_months": params.alert_budget,
    }
    if months > 0:
        lo, hi = poisson_exact_interval(alerts, params.confidence)
        out.update(
            rate_per_100_patient_months=100.0 * alerts / months,
            ci_low=100.0 * lo / months, ci_high=100.0 * hi / months,
        )
    if params.alert_budget is None:
        out["status"] = "NOT_EVALUABLE"
        out["reason"] = "PR-04 (alert budget) has no ratified value; there is no default."
    elif months <= 0 or len(landmarks) < params.min_window:
        out["status"] = "INSUFFICIENT"
        out["reason"] = f"fewer than PR-08 = {params.min_window} landmarks or no exposure yet"
    elif out["ci_low"] > params.alert_budget:
        out["status"] = "BREACH"
        out["reason"] = "lower bound of the exact interval exceeds the budget"
    else:
        out["status"] = "OK"
    return out


def _determinable(landmarks: List[Landmark], info, horizon_days: int):
    kept, excluded = [], 0
    for lm in landmarks:
        y = label(lm, info, horizon_days)
        if y is None:
            excluded += 1
        else:
            kept.append((lm, y))
    return kept, excluded


def calibration_drift(landmarks: List[Landmark], info, params: Parameters) -> Dict[str, Any]:
    kept, excluded = _determinable(landmarks, info, params.horizon_days)
    out: Dict[str, Any] = {
        "determinable_landmarks": len(kept), "excluded_landmarks": excluded,
        "acceptable_slope_range": [params.slope_low, params.slope_high], "windows": [],
    }
    windows: List[List[Tuple[Landmark, int]]] = []
    cur: List[Tuple[Landmark, int]] = []
    events = 0
    for item in kept:
        cur.append(item)
        events += item[1]
        if events >= params.min_window:
            windows.append(cur)
            cur, events = [], 0
    statuses = []
    for i, block in enumerate(windows):
        s = np.array([lm.score for lm, _ in block])
        y = np.array([yy for _, yy in block])
        fit = logistic_slope(s, y, params.confidence)
        entry: Dict[str, Any] = {
            "window": i + 1, "landmarks": len(block), "events": int(y.sum()),
            "expected": float(s.sum()), "observed_over_expected": float(y.sum() / s.sum()) if s.sum() > 0 else None,
            "first": min(lm.time for lm, _ in block).isoformat(), "last": max(lm.time for lm, _ in block).isoformat(),
        }
        if fit["status"] == "OK":
            entry.update({k: fit[k] for k in ("slope", "intercept", "ci_low", "ci_high")})
            if fit["ci_high"] < params.slope_low or fit["ci_low"] > params.slope_high:
                entry["status"] = "BREACH"
            elif fit["ci_low"] >= params.slope_low and fit["ci_high"] <= params.slope_high:
                entry["status"] = "OK"
            else:
                entry["status"] = "OK"
                entry["inconclusive"] = True  # straddles a bound: not a breach by the literal reading
        else:
            entry["status"] = "INSUFFICIENT" if fit["status"] == "INSUFFICIENT" else "NOT_EVALUABLE"
            entry["reason"] = fit["status"]
        statuses.append(entry["status"])
        out["windows"].append(entry)
    out["open_block"] = {"landmarks": len(cur), "events": int(sum(yy for _, yy in cur)), "needed_events": params.min_window}
    if "BREACH" in statuses:
        out["status"] = "BREACH"
    elif not windows:
        out["status"] = "INSUFFICIENT"
        out["reason"] = f"no window has reached PR-08 = {params.min_window} events yet"
    elif "NOT_EVALUABLE" in statuses:
        out["status"] = "NOT_EVALUABLE"
    else:
        out["status"] = "OK"
    return out


def conformal_coverage(preds: List[Dict[str, Any]], info, params: Parameters) -> Dict[str, Any]:
    with_sets = [p for p in preds if p["conformal_set"] is not None and p["conformal_nominal"] is not None]
    if not with_sets:
        return {
            "status": "NOT_MEASURABLE", "predictions_with_sets": 0,
            "reason": "the producing model records no conformal sets (the M3/K2 pipeline has none); "
            "coverage is not invented",
        }
    rows = []
    for p in with_sets:
        lm = Landmark(p["patient_id"], p["time"].date(), p["time"], p["score"], p["would_alert"], (p["analyte"],))
        y = label(lm, info, params.horizon_days)
        if y is not None:
            rows.append((y in p["conformal_set"], p["conformal_nominal"]))
    out: Dict[str, Any] = {"predictions_with_sets": len(with_sets), "determinable": len(rows), "windows": []}
    breached = False
    for i in range(0, len(rows) - params.min_window + 1, params.min_window):
        block = rows[i : i + params.min_window]
        cov = float(np.mean([c for c, _ in block]))
        nominal = float(np.mean([n for _, n in block]))
        w = {"window": i // params.min_window + 1, "n": len(block), "coverage": cov, "nominal": nominal}
        w["status"] = "BREACH" if cov < nominal - params.coverage_shortfall else "OK"
        breached |= w["status"] == "BREACH"
        out["windows"].append(w)
    out["status"] = "BREACH" if breached else ("OK" if out["windows"] else "INSUFFICIENT")
    return out


def data_shift(landmarks: List[Landmark], preds: List[Dict[str, Any]], rejections: List[Dict[str, Any]], params: Parameters) -> Dict[str, Any]:
    w = params.min_window
    analytes = sorted({p["analyte"] for p in preds} | {r["analyte"] for r in rejections})
    out: Dict[str, Any] = {"missingness": {}, "rejection_rate": {}}
    statuses: List[str] = []

    def judge(rates: List[float]) -> Dict[str, Any]:
        if len(rates) < 2:
            return {"status": "INSUFFICIENT", "rates": rates}
        base = rates[0]
        flagged = []
        undefined = False
        for k, r in enumerate(rates[1:], start=2):
            if base == 0.0:
                undefined |= r > 0.0
            elif r > 2.0 * base:
                flagged.append(k)
        res: Dict[str, Any] = {"rates": rates, "first_window_rate": base}
        if flagged:
            res.update(status="BREACH", windows_more_than_double=flagged)
        else:
            res["status"] = "OK"
            if undefined:
                res["note"] = "first-window rate is zero, so 'more than doubles' is undefined; not declared a breach"
        return res

    for a in analytes:
        # missingness over blocks of W landmark-days
        blocks = [landmarks[i : i + w] for i in range(0, len(landmarks) - w + 1, w)]
        miss = [1.0 - sum(1 for lm in b if a in lm.analytes) / len(b) for b in blocks]
        res = judge(miss)
        out["missingness"][a] = res
        statuses.append(res["status"])
        # rejection rate over blocks of W attempts
        attempts = [(p["recorded_at"], 0) for p in preds if p["analyte"] == a] + [
            (r["recorded_at"], 1) for r in rejections if r["analyte"] == a
        ]
        attempts.sort()
        blocks2 = [attempts[i : i + w] for i in range(0, len(attempts) - w + 1, w)]
        rej = [sum(f for _, f in b) / len(b) for b in blocks2]
        res2 = judge(rej)
        out["rejection_rate"][a] = res2
        statuses.append(res2["status"])
    out["status"] = "BREACH" if "BREACH" in statuses else ("OK" if "OK" in statuses else "INSUFFICIENT")
    return out


def build_report(store: ShadowStore, params: Parameters, generated_at: Optional[datetime] = None) -> Dict[str, Any]:
    data = load(store)
    preds, outcomes, rejections = data["predictions"], data["outcomes"], data["rejections"]
    landmarks = landmarks_from(preds)
    info = patient_outcomes(outcomes)
    pred_patients = {p["patient_id"] for p in preds}
    sections = {
        "alarm_rate": alarm_rate_audit(landmarks, params),
        "calibration_drift": calibration_drift(landmarks, info, params),
        "conformal_coverage": conformal_coverage(preds, info, params),
        "data_shift": data_shift(landmarks, preds, rejections, params),
    }
    statuses = [s["status"] for s in sections.values()]
    report = {
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(),
        "source": "shadow store only",
        "parameters": {
            "PR-01_slope_low": params.slope_low, "PR-02_slope_high": params.slope_high,
            "PR-04_alert_budget_per_100_patient_months": params.alert_budget, "PR-08_min_window": params.min_window,
            "PR-09_coverage_shortfall": params.coverage_shortfall, "horizon_days": params.horizon_days,
            "confidence": params.confidence, "provenance": params.provenance,
        },
        "data": {
            "predictions": len(preds), "landmarks": len(landmarks), "patients": len(pred_patients),
            "outcome_rows": len(outcomes), "patients_with_outcomes": len(info),
            "outcome_patients_without_predictions": len(set(info) - pred_patients),
            "rejections": len(rejections), "score_kinds": sorted({p["score_kind"] for p in preds}),
            "first_specimen": min((p["time"] for p in preds), default=None) and min(p["time"] for p in preds).isoformat(),
            "last_specimen": max((p["time"] for p in preds), default=None) and max(p["time"] for p in preds).isoformat(),
        },
        "sections": sections,
        "breach": "BREACH" in statuses,
        "incomplete": "NOT_EVALUABLE" in statuses,
        "caveats": [
            "The score monitored is whatever the pipeline records as `score` (score_kind). For the M3/K2 pipeline it "
            "is M3's probability that a change is real, not a recurrence-risk probability, so calibration against "
            "the recurrence outcome measures how well that quantity tracks recurrence, nothing more.",
            "Outcomes are imported by the data steward from the chart; a missing import makes landmarks "
            "non-determinable, it never makes them negative.",
            "A breach pauses further evaluation and starts the review in docs/clinical/PILOT/STOP-RULES.md; it is not "
            "resolved by editing a parameter.",
        ],
    }
    return attest_monitor_report(report)


def render_markdown(report: Dict[str, Any]) -> str:
    p = report["parameters"]
    d = report["data"]
    lines = [
        "# Silent-mode monitoring report",
        "",
        f"Generated {report['generated_at']} from the shadow store only. Parameters: {p['provenance']}.",
        "",
        f"**Overall: {'BREACH' if report['breach'] else 'incomplete' if report['incomplete'] else 'no breach'}**"
        + (" (some monitors could not be evaluated)" if report["incomplete"] and not report["breach"] else ""),
        "",
        f"Data: {d['predictions']} predictions, {d['landmarks']} landmarks, {d['patients']} patients, "
        f"{d['outcome_rows']} outcome rows ({d['patients_with_outcomes']} patients), {d['rejections']} refused ingestions. "
        f"Score kind: {', '.join(d['score_kinds']) or 'none'}.",
        "",
        "| Monitor | Status | Detail |",
        "|---|---|---|",
    ]
    s = report["sections"]
    a = s["alarm_rate"]
    rate = f"{a['rate_per_100_patient_months']:.2f} per 100 patient-months (exact 95 % interval {a['ci_low']:.2f} to {a['ci_high']:.2f})" if "rate_per_100_patient_months" in a else "no exposure yet"
    lines.append(f"| Alarm rate | {a['status']} | {a['alerts']} alerts in {a['landmarks']} landmarks; {rate}; budget {a['budget_per_100_patient_months']} |")
    c = s["calibration_drift"]
    lines.append(f"| Calibration drift | {c['status']} | {len(c['windows'])} completed windows; {c['determinable_landmarks']} determinable and {c['excluded_landmarks']} excluded landmarks |")
    k = s["conformal_coverage"]
    lines.append(f"| Conformal coverage | {k['status']} | {k.get('reason', str(len(k.get('windows', []))) + ' windows')} |")
    sh = s["data_shift"]
    lines.append(f"| Data shift | {sh['status']} | per-analyte missingness and refused-ingestion rates, see JSON |")
    lines += ["", "## Calibration windows", ""]
    if c["windows"]:
        lines += ["| Window | Landmarks | Events | Slope (95 % CI) | O/E | Status |", "|---|---|---|---|---|---|"]
        for w in c["windows"]:
            slope = f"{w['slope']:.2f} ({w['ci_low']:.2f} to {w['ci_high']:.2f})" if "slope" in w else w.get("reason", "n/a")
            oe = f"{w['observed_over_expected']:.2f}" if w.get("observed_over_expected") is not None else "n/a"
            lines.append(f"| {w['window']} | {w['landmarks']} | {w['events']} | {slope} | {oe} | {w['status']}{' (inconclusive)' if w.get('inconclusive') else ''} |")
    else:
        lines.append(f"No window has reached the minimum of {p['PR-08_min_window']} events (open block: {c['open_block']['events']}).")
    lines += ["", "## Caveats", ""] + [f"- {t}" for t in report["caveats"]]
    return "\n".join(lines) + "\n"


def import_outcomes(store: ShadowStore, rows: List[Dict[str, str]], source: str) -> Dict[str, Any]:
    """Import steward-supplied outcomes. Rows with a problem are rejected with a code; no cell value is echoed.

    Required columns: ``patient_id``, ``event_type`` (one of OUTCOME_TYPES), ``event_time`` (ISO 8601).
    Codes: MISSING_REQUIRED, BAD_ENUM, BAD_TIMESTAMP, UNKNOWN_PATIENT (no prediction exists for the patient),
    DUPLICATE (an identical outcome is already stored).
    """
    counts: Dict[str, int] = {"accepted": 0}
    codes: Dict[str, int] = {}

    def reject(code: str) -> None:
        codes[code] = codes.get(code, 0) + 1

    with store.session() as session:
        known = set(session.execute(select(ShadowPrediction.patient_id).distinct()).scalars())
        existing = {
            (o.patient_id, o.event_type, _utc(o.event_time))
            for o in session.execute(select(ShadowOutcome)).scalars()
        }
        for row in rows:
            pid = (row.get("patient_id") or "").strip()
            etype = (row.get("event_type") or "").strip()
            when = (row.get("event_time") or "").strip()
            if not pid or not etype or not when:
                reject("MISSING_REQUIRED")
                continue
            if etype not in OUTCOME_TYPES:
                reject("BAD_ENUM")
                continue
            try:
                ts = _utc(datetime.fromisoformat(when.replace("Z", "+00:00")))
            except ValueError:
                reject("BAD_TIMESTAMP")
                continue
            if pid not in known:
                reject("UNKNOWN_PATIENT")
                continue
            if (pid, etype, ts) in existing:
                reject("DUPLICATE")
                continue
            existing.add((pid, etype, ts))
            session.add(ShadowOutcome(patient_id=pid, event_type=etype, event_time=ts, source=source[:100]))
            counts["accepted"] += 1
        session.commit()
    return {"rows": len(rows), "accepted": counts["accepted"], "rejected": sum(codes.values()), "rejection_codes": dict(sorted(codes.items()))}
