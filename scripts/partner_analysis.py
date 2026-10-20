"""Retrospective-partner analysis (docs/clinical/PREREGISTRATION.md; operational definitions in ANALYSIS-SPEC.md).

Pure functions on the clean tables produced by ``contracts.partner.ingest``. Nothing here reads files, and nothing
here knows whether the data are real or synthetic; ``run_partner_evaluation.py`` decides that (and the freeze gate).

It calls the repository's own components rather than re-implementing them: ``WindowedFeatureExtractor`` for
landmark features, the B1-B4 baselines of ``vigil_ml.baselines``, and ``vigil_eval`` for IPCW weights, IPCW AUC,
calibration curves, decision curves, lead time and the verification-bias estimators.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from vigil_eval.lead_time import evaluate_lead_time_and_overdetection
from vigil_eval.metrics import (
    compute_ipcw_calibration_curve,
    compute_ipcw_weights,
    ipcw_time_dependent_roc_auc,
    survival_decision_curve_analysis,
)
from vigil_eval.verification_bias import evaluate_complete_case, evaluate_ipw_verification
from vigil_ml.baselines import (
    GradientBoostingBaseline,
    RegularizedCoxHazardBaseline,
    SingleThresholdBaseline,
    VelocityBaseline,
)
from vigil_ml.features import TRACKED_ANALYTES, WindowedFeatureExtractor

HORIZON = 365.0
DAYS_PER_MONTH = 30.4375
NON_FEATURES = ("patient_id", "eval_day")  # eval_day is bookkeeping, never a model input


class InsufficientData(Exception):
    """A step cannot be done honestly with the data at hand; the message says why."""


# ----------------------------------------------------------------------------------------------- partition
def assign_split(patient_id: str, key: bytes) -> str:
    """50/50 patient-level split by a keyed hash. The key is held by the data steward and never committed."""
    if not key or len(key) < 16:
        raise ValueError("partition key must be at least 16 bytes")
    return (
        "dev"
        if hmac.new(key, patient_id.encode("utf-8"), hashlib.sha256).digest()[0] % 2 == 0
        else "test"
    )


# ----------------------------------------------------------------------------------------------- landmarks
@dataclass
class Landmarks:
    X: pd.DataFrame  # one row per landmark; includes patient_id and eval_day
    y: np.ndarray  # recurrence before competing death within HORIZON; NaN if censored before HORIZON
    T: np.ndarray  # time from landmark to recurrence, competing death, or censoring
    E: np.ndarray  # 0=censoring, 1=recurrence, 2=competing death
    first: np.ndarray  # True for the first landmark of each patient (used for C1 and C2)
    end_day: Dict[
        str, float
    ]  # per patient: end of surveillance at risk (min(recurrence, death, follow-up))
    patients: pd.DataFrame
    counts: Dict[str, int] = field(default_factory=dict)

    def subset(self, patient_ids: Sequence[str]) -> "Landmarks":
        keep = self.X["patient_id"].isin(set(patient_ids)).to_numpy()
        return Landmarks(
            self.X[keep].reset_index(drop=True),
            self.y[keep],
            self.T[keep],
            self.E[keep],
            self.first[keep],
            {p: d for p, d in self.end_day.items() if p in set(patient_ids)},
            self.patients[self.patients["patient_id"].isin(set(patient_ids))].reset_index(
                drop=True
            ),
            dict(self.counts),
        )


def _stage(s: str) -> str:
    s = str(s)
    return "STAGE III" if s.startswith("III") else ("STAGE II" if s.startswith("II") else "STAGE I")


def _subtype(er: str, pr: str, her2: str) -> str:
    if her2 == "POSITIVE":
        return "HER2+"
    if er == "POSITIVE" or pr == "POSITIVE":
        return "HR+"
    if er == "NEGATIVE" and pr == "NEGATIVE" and her2 == "NEGATIVE":
        return "TNBC"
    return "UNCLASSIFIED"


def to_vigil_frames(
    tables: Dict[str, List[Dict[str, Any]]], cohort_ids: Sequence[str]
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Clean partner tables -> the ``patients_df`` / ``observations_df`` shapes of WindowedFeatureExtractor."""
    ids = set(cohort_ids)
    pat = {r["patient_id"]: r for r in tables["patients"] if r["patient_id"] in ids}
    base = {r["patient_id"]: r for r in tables["baseline_profile"] if r["patient_id"] in ids}
    out = {r["patient_id"]: r for r in tables["clinical_outcomes"] if r["patient_id"] in ids}
    rows = []
    for pid in sorted(pat):
        p, b, o = pat[pid], base[pid], out[pid]
        deceased = p["vital_status"] in {"DEAD_DISEASE", "DEAD_OTHER"}
        death_day = p.get("days_to_death")
        if deceased:
            if death_day is None or pd.isna(death_day):
                raise ValueError(f"explicit days_to_death is required for deceased patient {pid}")
            death_day = float(death_day)
            if not float(p["index_day"]) <= death_day <= float(p["days_to_last_followup"]):
                raise ValueError(f"days_to_death is outside follow-up for patient {pid}")
        elif death_day is not None and not pd.isna(death_day):
            raise ValueError(f"days_to_death supplied for non-deceased patient {pid}")
        death_day_value = float(death_day) if deceased and death_day is not None else np.nan
        rec = (
            bool(o["recurrence_confirmed"])
            and o["recurrence_day"] is not None
            and o["recurrence_day"] <= p["days_to_last_followup"]
        )
        rows.append(
            {
                "patient_id": pid,
                "age": float(p["age_at_diagnosis"]),
                "er_status": b["er_status"] == "POSITIVE",
                "pr_status": b["pr_status"] == "POSITIVE",
                "her2_status": b["her2_status"] == "POSITIVE",
                "stage": _stage(b["stage_ajcc"]),
                "subtype": _subtype(b["er_status"], b["pr_status"], b["her2_status"]),
                "observed_recurrence_event": rec,
                "observed_recurrence_day": float(o["recurrence_day"]) if rec else np.nan,
                "competing_event": "death" if deceased else None,
                "competing_event_day": death_day_value,
                "administrative_censor_day": float(p["days_to_last_followup"]),
                "days_to_last_followup": float(p["days_to_last_followup"]),
                "index_day": float(p["index_day"]),
                "restaging_imaging_done": o.get("restaging_imaging_done"),
                "dismissed_prior_signal": bool(o.get("dismissed_prior_signal")),
            }
        )
    patients_df = pd.DataFrame(rows)
    index_day = dict(zip(patients_df["patient_id"], patients_df["index_day"]))
    obs: Dict[Tuple[str, int], Dict[str, Any]] = {}
    for r in tables["lab_observations"]:
        pid = r["patient_id"]
        if pid not in pat or r["observation_day"] < index_day[pid]:
            continue  # features may use only post-index surveillance draws
        cell = obs.setdefault(
            (pid, r["observation_day"]), {"patient_id": pid, "day": float(r["observation_day"])}
        )
        if r["analyte"] in TRACKED_ANALYTES:
            cell[r["analyte"]] = float(r["value_canonical"])
    observation_rows: List[Dict[str, Any]] = list(obs.values())
    observation_rows.sort(key=lambda row: (row["patient_id"], row["day"]))
    observations_df = pd.DataFrame(observation_rows)
    return patients_df, observations_df


def build_landmarks(
    tables: Dict[str, List[Dict[str, Any]]], cohort_ids: Sequence[str], horizon: float = HORIZON
) -> Landmarks:
    patients_df, obs_df = to_vigil_frames(tables, cohort_ids)
    counts = {"cohort_complete_case": len(patients_df)}
    if obs_df.empty:
        raise InsufficientData("no post-index laboratory draws in the complete-case cohort")
    X, _y, _T, _E = WindowedFeatureExtractor().transform_cohort(
        patients_df, obs_df, horizon_days=horizon
    )
    p = patients_df.set_index("patient_id")
    # The extractor censors at the last laboratory day; partner follow-up and
    # vital status define the event/censor time for this fixed-horizon estimand.
    follow = X["patient_id"].map(p["days_to_last_followup"]).to_numpy()
    rec_day = X["patient_id"].map(p["observed_recurrence_day"]).to_numpy()
    rec = X["patient_id"].map(p["observed_recurrence_event"]).to_numpy().astype(bool)
    comp_type = X["patient_id"].map(p["competing_event"]).to_numpy()
    comp_day = X["patient_id"].map(p["competing_event_day"]).to_numpy(dtype=float)
    eval_day = X["eval_day"].to_numpy()
    competing = np.array(
        [kind is not None and not pd.isna(kind) and kind != "lost_to_follow_up" for kind in comp_type],
        dtype=bool,
    ) & np.isfinite(comp_day) & (comp_day <= follow)
    # Recurrence is observed only if it occurs before death. Equal-day events
    # are rejected by WindowedFeatureExtractor as order-ambiguous.
    recurrence = rec & (~competing | (rec_day < comp_day))
    death = competing & (~recurrence)
    keep = (
        (X["history_length"].to_numpy() >= 2)
        & ~(recurrence & (eval_day >= rec_day))
        & ~(death & (eval_day >= comp_day))
        & (eval_day < follow)
    )
    X, follow, rec_day, recurrence, death, comp_day, eval_day = (
        X[keep].reset_index(drop=True),
        follow[keep],
        rec_day[keep],
        recurrence[keep],
        death[keep],
        comp_day[keep],
        eval_day[keep],
    )
    E = np.where(recurrence, 1, np.where(death, 2, 0)).astype(int)
    end = np.where(recurrence, rec_day, np.where(death, comp_day, follow))
    T = np.maximum(1.0, end - eval_day)
    # By the horizon, recurrence and competing death are known non-censored
    # outcomes; recurrence is the positive class, death the competing control.
    # A patient censored before the horizon has unknown status (NaN).
    y = np.full(len(E), np.nan, dtype=float)
    known = (T <= horizon) & np.isin(E, [1, 2]) | (T >= horizon)
    y[known] = ((E[known] == 1) & (T[known] <= horizon)).astype(float)
    first = ~X["patient_id"].duplicated().to_numpy()
    end_day = {pid: float(e) for pid, e in zip(X["patient_id"], end)}
    counts.update(
        patients_with_a_landmark=int(first.sum()),
        patients_excluded_fewer_than_two_post_index_draws_or_terminal_event_before_second_draw=len(patients_df)
        - int(first.sum()),
        landmarks=len(X),
    )
    return Landmarks(X, y, T, E, first, end_day, patients_df, counts)


# ----------------------------------------------------------------------------------------------- metrics
def ipcw_auc(score: np.ndarray, T: np.ndarray, E: np.ndarray, horizon: float = HORIZON) -> float:
    return float(ipcw_time_dependent_roc_auc(np.asarray(score, float), T, E, horizon))


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.asarray(np.log(p / (1 - p)), dtype=float)


def weighted_calibration_fit(
    p: np.ndarray, T: np.ndarray, E: np.ndarray, horizon: float = HORIZON
) -> Tuple[float, float]:
    """IPCW-weighted logistic regression of the horizon outcome on logit(p): returns (intercept, slope)."""
    w = compute_ipcw_weights(T, E, horizon)
    ok = w > 0
    y = ((E == 1) & (T <= horizon)).astype(int)
    if ok.sum() < 5 or len(np.unique(y[ok])) < 2:
        raise InsufficientData(
            "calibration needs at least five determinable outcomes with both classes present"
        )
    m = LogisticRegression(C=np.inf, max_iter=1000)
    m.fit(_logit(p[ok]).reshape(-1, 1), y[ok], sample_weight=w[ok])
    return float(m.intercept_[0]), float(m.coef_[0, 0])


def calibration_slope(
    p: np.ndarray, T: np.ndarray, E: np.ndarray, horizon: float = HORIZON
) -> float:
    return weighted_calibration_fit(p, T, E, horizon)[1]


def alert_burden(
    p: np.ndarray,
    threshold: float,
    patient_ids: np.ndarray,
    eval_day: np.ndarray,
    end_day: Dict[str, float],
) -> Tuple[Dict[str, int], Dict[str, float]]:
    """Per patient: alerts issued (every landmark at or above the threshold) and months at risk.

    An alert is counted at every landmark that crosses the threshold, because each one is a review for the clinic.
    Counting only the onset of an episode would make "alert always on" cost one alert per patient and so reward it.
    """
    alerts: Dict[str, int] = {}
    months: Dict[str, float] = {}
    df = pd.DataFrame(
        {"pid": patient_ids, "day": eval_day, "a": np.asarray(p) >= threshold}
    ).sort_values(["pid", "day"])
    for raw_pid, g in df.groupby("pid", sort=True):
        if not isinstance(raw_pid, str):
            raise ValueError("patient_ids must contain strings")
        pid = raw_pid
        alerts[pid] = int(g["a"].sum())
        months[pid] = max(0.0, (end_day[pid] - float(g["day"].iloc[0])) / DAYS_PER_MONTH)
    return alerts, months


def rate_per_100_months(
    alerts: Dict[str, int], months: Dict[str, float], ids: Optional[Sequence[str]] = None
) -> float:
    ids = list(alerts) if ids is None else list(ids)
    m = sum(months[i] for i in ids)
    return 100.0 * sum(alerts[i] for i in ids) / m if m > 0 else float("nan")


# ----------------------------------------------------------------------------------------------- development split
COMPARATORS = {
    "B1_SINGLE_THRESHOLD": lambda: SingleThresholdBaseline(),
    "B2_VELOCITY_RULE": lambda: VelocityBaseline(),
    "B3_REGULARIZED_LOGISTIC_HORIZON": lambda: RegularizedCoxHazardBaseline(),
}


@dataclass
class FittedPlan:
    comparator_name: str
    comparator: Any
    candidate: Any
    recal_intercept: float
    recal_slope: float
    threshold: float
    dev_auc: Dict[str, float]
    dev_alert_rate: float
    notes: List[str] = field(default_factory=list)
    verification_propensity_model: Optional[LogisticRegression] = None
    verification_propensity_medians: Optional[np.ndarray] = None

    def candidate_risk(self, X: pd.DataFrame) -> np.ndarray:
        raw = self.candidate.predict_risk(_model_view(X))
        return 1.0 / (1.0 + np.exp(-(self.recal_intercept + self.recal_slope * _logit(raw))))

    def comparator_risk(self, X: pd.DataFrame) -> np.ndarray:
        return np.asarray(self.comparator.predict_risk(_model_view(X)), dtype=float)


VERIFICATION_FEATURE_COLUMNS = ("age", "ca_15_3_curr", "history_length")


def _verification_feature_matrix(
    X: pd.DataFrame, medians: Optional[np.ndarray] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """Impute verification covariates from development medians and preserve missingness indicators."""
    raw = np.column_stack(
        [
            pd.to_numeric(X[column], errors="coerce").to_numpy(dtype=float)
            if column in X
            else np.full(len(X), np.nan, dtype=float)
            for column in VERIFICATION_FEATURE_COLUMNS
        ]
    )
    missing = ~np.isfinite(raw)
    if medians is None:
        fitted_medians = np.nanmedian(np.where(np.isfinite(raw), raw, np.nan), axis=0)
        if not np.isfinite(fitted_medians).all():
            raise InsufficientData(
                "verification propensity cannot be fit: a development covariate is entirely missing"
            )
    else:
        fitted_medians = np.asarray(medians, dtype=float)
        if (
            fitted_medians.shape != (len(VERIFICATION_FEATURE_COLUMNS),)
            or not np.isfinite(fitted_medians).all()
        ):
            raise ValueError("verification propensity medians are malformed")
    imputed = np.where(missing, fitted_medians, raw)
    return np.column_stack((imputed, missing.astype(float))), fitted_medians


def _fit_verification_propensity(
    dev: Landmarks,
) -> Tuple[Optional[LogisticRegression], Optional[np.ndarray], Optional[str]]:
    """Fit the verification mechanism only on development patients, never the test cohort."""
    if "restaging_imaging_done" not in dev.patients:
        return None, None, "development cohort lacks restaging_imaging_done"
    first = dev.X.loc[dev.first].reset_index(drop=True)
    patients = dev.patients.set_index("patient_id")
    verified = first["patient_id"].map(patients["restaging_imaging_done"])
    numeric = pd.to_numeric(verified, errors="coerce").to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or np.any((numeric != 0.0) & (numeric != 1.0)):
        return None, None, "development verification status is incomplete or non-binary"
    if np.unique(numeric).size < 2:
        return None, None, "development verification status has no variation"
    try:
        features, medians = _verification_feature_matrix(first)
    except InsufficientData as exc:
        return None, None, str(exc)
    model = LogisticRegression(max_iter=500)
    model.fit(features, numeric.astype(int))
    return model, medians, None


def _predict_verification_propensity(plan: FittedPlan, X: pd.DataFrame) -> Optional[np.ndarray]:
    if plan.verification_propensity_model is None or plan.verification_propensity_medians is None:
        return None
    features, _ = _verification_feature_matrix(X, plan.verification_propensity_medians)
    return np.asarray(plan.verification_propensity_model.predict_proba(features)[:, 1], dtype=float)


def _model_view(X: pd.DataFrame) -> pd.DataFrame:
    return X.drop(columns=[c for c in ("eval_day",) if c in X.columns])


def _out_of_fold(dev: Landmarks, horizon: float, folds: int = 5) -> Tuple[np.ndarray, np.ndarray]:
    """Out-of-fold raw predictions (candidate, B3) for every development landmark, cross-fitted by patient."""
    from sklearn.model_selection import GroupKFold

    w = compute_ipcw_weights(dev.T, dev.E, horizon)
    det = w > 0
    n = len(dev.X)
    cand, cox = np.full(n, np.nan), np.full(n, np.nan)
    groups = dev.X["patient_id"].to_numpy()
    for tr, te in GroupKFold(n_splits=folds).split(dev.X, groups=groups):
        trd = tr[det[tr]]
        ytr = pd.Series(dev.y[trd])
        if ytr.nunique() < 2:
            raise InsufficientData(
                "a cross-fitting fold has a single outcome class in its training part"
            )
        Xtr = _model_view(dev.X.iloc[trd])
        Xte = _model_view(dev.X.iloc[te])
        train_weights = w[trd]
        cand[te] = (
            GradientBoostingBaseline().fit(Xtr, ytr, sample_weight=train_weights).predict_risk(Xte)
        )
        cox[te] = (
            RegularizedCoxHazardBaseline()
            .fit(Xtr, ytr, sample_weight=train_weights)
            .predict_risk(Xte)
        )
    return cand, cox


def fit_on_development(
    dev: Landmarks, alert_budget: float, horizon: float = HORIZON, min_events: int = 10
) -> FittedPlan:
    """Fit the candidate, recalibrate it, pick the comparator and the operating point, all on the development split.

    Selection, recalibration and the threshold use out-of-fold predictions (cross-fitted by patient), so none of
    them is tuned on predictions the model made for its own training rows.
    """
    n_events = int(((dev.E == 1) & (dev.T <= horizon) & dev.first).sum())
    if n_events < min_events:
        raise InsufficientData(
            f"{n_events} development-split events at the first landmark; at least {min_events} are needed to fit and select"
        )
    oof_cand, oof_cox = _out_of_fold(dev, horizon)
    first = dev.first
    Xf, Tf, Ef = dev.X[first], dev.T[first], dev.E[first]
    det = compute_ipcw_weights(dev.T, dev.E, horizon) > 0
    Xtr, ytr = _model_view(dev.X[det]), pd.Series(dev.y[det])
    train_weights = compute_ipcw_weights(dev.T, dev.E, horizon)[det]
    b1 = SingleThresholdBaseline().fit(Xtr, ytr, sample_weight=train_weights)
    b2 = VelocityBaseline().fit(Xtr, ytr, sample_weight=train_weights)
    rule_scores = {
        "B1_SINGLE_THRESHOLD": b1.predict_risk(_model_view(Xf)),
        "B2_VELOCITY_RULE": b2.predict_risk(_model_view(Xf)),
        "B3_REGULARIZED_LOGISTIC_HORIZON": oof_cox[first],
    }
    auc = {k: ipcw_auc(v, Tf, Ef, horizon) for k, v in rule_scores.items()}
    best = max(auc, key=lambda k: (auc[k], -list(auc).index(k)))
    a, b = weighted_calibration_fit(oof_cand[first], Tf, Ef, horizon)
    candidate = GradientBoostingBaseline().fit(Xtr, ytr, sample_weight=train_weights)
    comparator = {
        "B1_SINGLE_THRESHOLD": b1,
        "B2_VELOCITY_RULE": b2,
    }.get(best) or RegularizedCoxHazardBaseline().fit(Xtr, ytr, sample_weight=train_weights)
    verification_model, verification_medians, verification_issue = _fit_verification_propensity(dev)
    plan = FittedPlan(
        best,
        comparator,
        candidate,
        a,
        b,
        1.0,
        auc,
        float("nan"),
        verification_propensity_model=verification_model,
        verification_propensity_medians=verification_medians,
    )
    if verification_issue:
        plan.notes.append(f"verification-bias analysis unavailable: {verification_issue}")
    p_all = 1.0 / (1.0 + np.exp(-(a + b * _logit(oof_cand))))
    grid = np.unique(np.quantile(p_all, np.linspace(0.0, 1.0, 201)))
    pids, days = dev.X["patient_id"].to_numpy(), dev.X["eval_day"].to_numpy()
    chosen, rate = float(grid[-1]) + 1e-9, 0.0
    for thr in grid:
        al, mo = alert_burden(p_all, float(thr), pids, days, dev.end_day)
        r = rate_per_100_months(al, mo)
        if r <= alert_budget:
            chosen, rate = float(thr), r
            break
    plan.threshold, plan.dev_alert_rate = chosen, rate
    plan.notes.append(
        "candidate = GradientBoostingBaseline (B4) fitted from scratch on the development split; see ANALYSIS-SPEC.md section 3"
    )
    return plan


# ----------------------------------------------------------------------------------------------- frozen test split
def _boot_indices(n: int, rng: np.random.Generator) -> np.ndarray:
    return rng.integers(0, n, size=n)


def holm(pvals: Dict[str, float], alpha: float = 0.05) -> Dict[str, Dict[str, Any]]:
    order = sorted(pvals, key=lambda k: pvals[k])
    m = len(order)
    out: Dict[str, Dict[str, Any]] = {}
    running = 0.0
    for rank, k in enumerate(order):
        adj = min(1.0, (m - rank) * pvals[k])
        running = max(running, adj)
        out[k] = {"p": pvals[k], "p_holm": running, "reject": running < alpha}
    return out


def confirmatory(
    test: Landmarks,
    plan: FittedPlan,
    params: Dict[str, float],
    n_boot: int,
    seed: int,
    horizon: float = HORIZON,
) -> Dict[str, Any]:
    """C1, C2 and C3 of the pre-registration. ``params`` holds PR-01..PR-04 as floats."""
    f = test.first
    Xf, Tf, Ef = test.X[f], test.T[f], test.E[f]
    p_cand = plan.candidate_risk(Xf)
    s_comp = plan.comparator_risk(Xf)
    pids_f = Xf["patient_id"].to_numpy()
    pid_list = list(pids_f)
    n = len(pid_list)
    if n < 20:
        raise InsufficientData(
            f"{n} patients in the test split; too few for any confirmatory statement"
        )
    p_all = plan.candidate_risk(test.X)
    al, mo = alert_burden(
        p_all,
        plan.threshold,
        test.X["patient_id"].to_numpy(),
        test.X["eval_day"].to_numpy(),
        test.end_day,
    )
    a_vec = np.array([al.get(pid, 0) for pid in pid_list], float)
    m_vec = np.array([mo.get(pid, 0.0) for pid in pid_list], float)
    slope = calibration_slope(p_cand, Tf, Ef, horizon)
    d_auc = ipcw_auc(p_cand, Tf, Ef, horizon) - ipcw_auc(s_comp, Tf, Ef, horizon)
    rate = 100.0 * a_vec.sum() / m_vec.sum() if m_vec.sum() > 0 else float("nan")
    rng = np.random.default_rng(seed)
    slopes: list[float] = []
    diffs: list[float] = []
    rates: list[float] = []
    for _ in range(n_boot):
        i = _boot_indices(n, rng)
        mm = m_vec[i].sum()
        if mm > 0:
            rates.append(100.0 * a_vec[i].sum() / mm)
        try:
            slopes.append(calibration_slope(p_cand[i], Tf[i], Ef[i], horizon))
            diffs.append(
                ipcw_auc(p_cand[i], Tf[i], Ef[i], horizon)
                - ipcw_auc(s_comp[i], Tf[i], Ef[i], horizon)
            )
        except InsufficientData:
            continue

    def ci(values: Sequence[float]) -> Tuple[float, float]:
        return float(np.percentile(values, 2.5)), float(np.percentile(values, 97.5))

    sl, dl, rl = ci(slopes), ci(diffs), ci(rates)
    lo, hi, margin, budget = params["PR-01"], params["PR-02"], params["PR-03"], params["PR-04"]
    floor = 1.0 / (len(slopes) + 1)
    p1 = max(float(np.mean(np.array(slopes) < lo)), float(np.mean(np.array(slopes) > hi)), floor)
    p2 = max(float(np.mean(np.array(diffs) <= margin)), floor)
    p3 = max(float(np.mean(np.array(rates) > budget)), floor)
    hm = holm({"C1": p1, "C2": p2, "C3": p3})
    c1_ci = lo <= sl[0] and sl[1] <= hi
    c2_ci = dl[0] > margin
    c3_ci = rl[1] <= budget
    return {
        "n_test_patients": n,
        "n_boot": len(slopes),
        "seed": seed,
        "comparator": plan.comparator_name,
        "operating_threshold": plan.threshold,
        "C1": {
            "estimate": slope,
            "ci95": sl,
            "criterion": f"CI within [{lo}, {hi}]",
            "ci_criterion_met": c1_ci,
            **hm["C1"],
            "met": bool(c1_ci and hm["C1"]["reject"]),
        },
        "C2": {
            "estimate": d_auc,
            "ci95": dl,
            "criterion": f"lower CI bound > {margin}",
            "ci_criterion_met": c2_ci,
            **hm["C2"],
            "met": bool(c2_ci and hm["C2"]["reject"]),
        },
        "C3": {
            "estimate": rate,
            "ci95": rl,
            "criterion": f"upper CI bound <= {budget}",
            "ci_criterion_met": c3_ci,
            **hm["C3"],
            "met": bool(c3_ci and hm["C3"]["reject"]),
        },
        "decision_rule": "met only if the 95% CI criterion holds AND the Holm-adjusted one-sided bootstrap p-value is below 0.05",
    }


def begg_greenes_sensitivity(
    p: np.ndarray,
    y: np.ndarray,
    verified: np.ndarray,
    threshold: float,
    assumed_unverified_event_rates: Sequence[float],
) -> List[Dict[str, float]]:
    """Bounds on sensitivity and specificity if unverified patients had an assumed horizon-event rate ``q``.

    Verified patients contribute their observed outcomes; unverified patients contribute expected counts
    (``q`` of them are events). It is a sensitivity analysis over an assumption, not an estimate.
    """
    pos = np.asarray(p) >= threshold
    v = np.asarray(verified, bool)
    y = np.asarray(y)
    tp0, fn0 = float(((pos & (y == 1)) & v).sum()), float(((~pos & (y == 1)) & v).sum())
    fp0, tn0 = float(((pos & (y == 0)) & v).sum()), float(((~pos & (y == 0)) & v).sum())
    up, un = float((pos & ~v).sum()), float((~pos & ~v).sum())
    rows = []
    for q in assumed_unverified_event_rates:
        tp, fn, fp, tn = tp0 + q * up, fn0 + q * un, fp0 + (1 - q) * up, tn0 + (1 - q) * un
        rows.append(
            {
                "assumed_unverified_event_rate": float(q),
                "sensitivity": tp / (tp + fn) if tp + fn > 0 else float("nan"),
                "specificity": tn / (tn + fp) if tn + fp > 0 else float("nan"),
            }
        )
    return rows


# ----------------------------------------------------------------------------------------------- secondary analyses
def small_cell(n: int, threshold: int) -> Any:
    return n if n >= threshold else f"<{threshold}"


def secondary(
    test: Landmarks,
    plan: FittedPlan,
    params: Dict[str, float],
    n_boot: int,
    seed: int,
    horizon: float = HORIZON,
    dca_thresholds: Optional[Sequence[float]] = None,
) -> Dict[str, Any]:
    f = test.first
    Xf, Tf, Ef, yf = test.X[f].reset_index(drop=True), test.T[f], test.E[f], test.y[f]
    p = plan.candidate_risk(Xf)
    out: Dict[str, Any] = {}
    w = compute_ipcw_weights(Tf, Ef, horizon)
    ok = w > 0
    if ok.sum() and len(np.unique(yf[ok])) > 1:
        cal = compute_ipcw_calibration_curve(
            plan.candidate.predict_risk(_model_view(Xf)),
            Tf,
            Ef,
            horizon_time=horizon,
            n_bins=5,
            weights=w,
        )
        out["calibration_before_recalibration"] = {
            "ece": float(cal.expected_calibration_error),
            "mean_predicted": float(
                np.average(plan.candidate.predict_risk(_model_view(Xf)), weights=np.where(ok, w, 0))
            ),
            "observed_ipcw": float(np.average((Tf <= horizon) & (Ef == 1), weights=w)),
            "note": "ECE and calibration-in-the-large means use IPCW weights on determinable outcomes",
        }
    if dca_thresholds is None:
        out["decision_curve"] = {
            "not_run": "no clinically ratified PR-10 threshold grid is present in the frozen protocol"
        }
    else:
        threshold_array = np.asarray(dca_thresholds, dtype=float)
        dca = survival_decision_curve_analysis(p, Tf, Ef, horizon, thresholds=threshold_array)
        out["decision_curve"] = {
            "thresholds": [float(x) for x in dca.thresholds],
            "net_benefit_model": [float(x) for x in dca.net_benefit_model],
            "net_benefit_all": [float(x) for x in dca.net_benefit_all],
        }
    # Subgroups
    pt = test.patients.set_index("patient_id")
    ids = Xf["patient_id"]
    groups = {
        "age<50": ids.map(pt["age"]) < 50,
        "age50-64": (ids.map(pt["age"]) >= 50) & (ids.map(pt["age"]) < 65),
        "age>=65": ids.map(pt["age"]) >= 65,
        "stage I-II": ids.map(pt["stage"]).isin(["STAGE I", "STAGE II"]),
        "stage III": ids.map(pt["stage"]) == "STAGE III",
    }
    for st in sorted(set(pt["subtype"])):
        groups[f"subtype {st}"] = ids.map(pt["subtype"]) == st
    sub = {}
    rng = np.random.default_rng(seed)
    for name, mask in groups.items():
        m = mask.to_numpy()
        events = int(((Ef[m] == 1) & (Tf[m] <= horizon)).sum())
        if events < params["PR-05"]:
            sub[name] = {
                "patients": small_cell(int(m.sum()), int(params["PR-06"])),
                "events": small_cell(events, int(params["PR-06"])),
                "result": "insufficient data",
            }
            continue
        idx = np.where(m)[0]
        point = ipcw_auc(p[m], Tf[m], Ef[m], horizon)
        boots = []
        for _ in range(min(n_boot, 500)):
            i = idx[rng.integers(0, len(idx), len(idx))]
            boots.append(ipcw_auc(p[i], Tf[i], Ef[i], horizon))
        sub[name] = {
            "patients": int(m.sum()),
            "events": events,
            "ipcw_auc": point,
            "ci95": [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))],
        }
    scored = [(k, v["ipcw_auc"]) for k, v in sub.items() if "ipcw_auc" in v]
    out["subgroups"] = {
        "groups": sub,
        "worst_group": min(scored, key=lambda kv: kv[1]) if scored else None,
        "facility": "single-site extraction: not applicable",
    }
    # Lead time and overdetection at the operating point (all landmarks)
    p_all = plan.candidate_risk(test.X)
    pdf = test.patients
    patient_df = pd.DataFrame(
        {
            "patient_id": pdf["patient_id"],
            "true_recurrence_event": pdf["observed_recurrence_event"],
            "true_recurrence_day": pdf["observed_recurrence_day"],
            "is_indolent": False,
        }
    )
    obs_df = pd.DataFrame(
        {
            "patient_id": test.X["patient_id"],
            "day": test.X["eval_day"],
            "alert_triggered": (p_all >= plan.threshold).astype(int),
        }
    )
    try:
        out["lead_time"] = evaluate_lead_time_and_overdetection(patient_df, obs_df).to_dict() | {
            "caveat": "relative to the confirming test date; length bias and overdetection apply (ML_PROGRAM 4.5); no survival benefit is implied"
        }
    except Exception as exc:  # reported, never hidden
        out["lead_time"] = {"not_computed": f"{type(exc).__name__}"}
    # Missed-signal audit, aggregate only
    dismissed = int(pt.loc[ids, "dismissed_prior_signal"].sum())
    out["m10_aggregate"] = {
        "patients_with_dismissed_prior_signal": small_cell(dismissed, int(params["PR-06"])),
        "small_cell_threshold": int(params["PR-06"]),
    }
    # Verification bias
    vr = test.patients.set_index("patient_id")["restaging_imaging_done"].reindex(ids)
    if vr.isna().any():
        out["verification_bias"] = {
            "not_run": "restaging_imaging_done is missing for at least one test patient (optional column of the data dictionary)"
        }
    else:
        verification_numeric = pd.to_numeric(vr, errors="coerce").to_numpy(dtype=float)
        if not np.isfinite(verification_numeric).all() or np.any(
            (verification_numeric != 0.0) & (verification_numeric != 1.0)
        ):
            out["verification_bias"] = {
                "not_run": "restaging_imaging_done must contain known binary values for every test patient"
            }
        elif plan.verification_propensity_model is None:
            out["verification_bias"] = {
                "not_run": "no valid verification propensity model was fit on development patients"
            }
        else:
            v = verification_numeric.astype(bool) & ok
            props = _predict_verification_propensity(plan, Xf)
            if props is None:
                out["verification_bias"] = {
                    "not_run": "development verification propensity model or imputation state is unavailable"
                }
                return out
            if v.sum() < 10 or len(np.unique(yf[v])) < 2:
                out["verification_bias"] = {
                    "not_run": "fewer than ten verified determinable patients or only one outcome class among them"
                }
                return out
            cc = evaluate_complete_case(p, yf, v, plan.threshold)
            ipw = evaluate_ipw_verification(
                p,
                yf,
                v,
                verification_features=None,
                cutoff=plan.threshold,
                verification_propensities=props,
            )
            if not ipw.details.get("metrics_defined", False):
                out["verification_bias"] = {
                    "not_run": f"development-fit propensity unsupported on test patients: {ipw.details.get('reason', 'undefined metrics')}"
                }
                return out
            out["verification_bias"] = {
                "complete_case": {
                    "sensitivity": cc.empirical_sensitivity,
                    "specificity": cc.empirical_specificity,
                },
                "ipw": {
                    "sensitivity": ipw.empirical_sensitivity,
                    "specificity": ipw.empirical_specificity,
                    "minimum_verified_propensity": ipw.details["minimum_verified_propensity"],
                    "maximum_inverse_weight": ipw.details["maximum_verified_inverse_weight"],
                    "effective_sample_size": ipw.details["effective_sample_size"],
                },
                "sensitivity_analysis": begg_greenes_sensitivity(
                    p, yf, v, plan.threshold, (0.0, 0.05, 0.10, 0.20)
                ),
                "note": "the propensity model is fitted on development patients only and applied to test patients; verified-outcome metrics still require conditional exchangeability and positivity. The complete-case estimate is descriptive, and the assumed-rate sensitivity analysis is not an estimate",
            }
    return out
