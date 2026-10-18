"""vigil_ml.k5: laboratory harmonisation by hierarchical partial pooling, and a laboratory-stream changepoint
detector. Specification and evaluation design: `experiments/EXP-K5-001/PREREG.md` (committed before this file).

Model (one analyte, log scale): for result j of patient i measured at laboratory l(i, j),

    z_ij = a_i + b_i t_ij + beta_l(i,j) + eps_ij,   eps ~ N(0, sigma^2),   beta_l ~ N(0, tau^2) independent.

Patient intercepts a_i and slopes b_i are fixed effects and are eliminated by projecting each patient's results
onto the orthogonal complement of span{1, t}. The laboratory offsets are therefore identified **only through
patients who are tested at more than one laboratory**. A laboratory with no such connection keeps its prior
(offset 0, posterior sd tau). sigma^2 and rho = tau^2 / sigma^2 are estimated by restricted maximum likelihood on
the projected model; with A = Z~'Z~ and b = Z~'r~ (Z~, r~ the projected design and response):

    profile log-lik(rho) = -1/2 [ df log sigma_hat^2(rho) + log det(I + rho A) ],
    sigma_hat^2(rho)     = (r~'r~ - rho b'(I + rho A)^-1 b) / df,
    beta_hat             = (A + I/rho)^-1 b,    cov = sigma_hat^2 (A + I/rho)^-1.

This module imports no simulator and takes only arrays (patient, time, laboratory, value): it can never see a true
offset or a latent column (checked by `tests/test_k5.py`). Research module: synthetic-data evidence only.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.optimize import minimize_scalar

RHO_GRID = np.logspace(-4.0, 2.0, 400)
LEGACY_SHRINKAGE = 15.0


# --------------------------------------------------------------------------------------------
# Within-patient projection
# --------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class ProjectedSystem:
    A: np.ndarray  # Z~'Z~   (L, L)
    b: np.ndarray  # Z~'r~   (L,)
    rtr: float  # r~'r~
    df: int  # sum_i (n_i - rank_i)
    lab_ids: Tuple[str, ...]
    n_obs: int
    n_patients_informative: int


def _residual_maker(t: np.ndarray) -> np.ndarray:
    """I - Q Q' for the design [1, centred scaled t]; the zero matrix when n <= rank."""
    n = len(t)
    cols = [np.ones(n)]
    tc = t - t.mean()
    sd = float(np.sqrt(np.mean(tc**2)))
    if sd > 1e-12:
        cols.append(tc / sd)
    X = np.column_stack(cols)
    q, rr = np.linalg.qr(X)
    rank = int(np.sum(np.abs(np.diag(rr)) > 1e-10))
    q = q[:, :rank]
    return np.eye(n) - q @ q.T


def build_projected_system(
    patient: Sequence[object],
    t_days: Sequence[float],
    lab: Sequence[object],
    value: Sequence[float],
) -> ProjectedSystem:
    """Eliminate patient intercepts and slopes from log values; return the L x L normal-equation pieces."""
    patient = np.asarray(patient)
    t = np.asarray(t_days, dtype=float)
    lab_arr = np.asarray([str(x) for x in lab])
    y = np.asarray(value, dtype=float)
    if np.any(~np.isfinite(y)) or np.any(y <= 0):
        raise ValueError("values must be finite and strictly positive (log scale)")
    z = np.log(y)
    lab_ids = tuple(sorted(set(lab_arr.tolist())))
    index = {lab_id: k for k, lab_id in enumerate(lab_ids)}
    L = len(lab_ids)
    A = np.zeros((L, L))
    b = np.zeros(L)
    rtr = 0.0
    df = 0
    informative = 0
    order = np.argsort(patient, kind="stable")
    patient, t, lab_arr, z = patient[order], t[order], lab_arr[order], z[order]
    boundaries = np.flatnonzero(np.r_[True, patient[1:] != patient[:-1], True])
    for lo, hi in zip(boundaries[:-1], boundaries[1:]):
        n = hi - lo
        if n < 3:
            # a line fits two points exactly: no residual degrees of freedom, no information on offsets
            continue
        M = _residual_maker(t[lo:hi])
        Z = np.zeros((n, L))
        for r, lab_id in enumerate(lab_arr[lo:hi]):
            Z[r, index[lab_id]] = 1.0
        Zt = M @ Z
        rt = M @ z[lo:hi]
        A += Zt.T @ Zt
        b += Zt.T @ rt
        rtr += float(rt @ rt)
        df += int(round(np.trace(M)))
        informative += 1
    return ProjectedSystem(A, b, rtr, df, lab_ids, int(len(y)), informative)


# --------------------------------------------------------------------------------------------
# Estimators
# --------------------------------------------------------------------------------------------
def _profile(rho: float, sys_: ProjectedSystem) -> Tuple[float, float]:
    """(negative profile REML log-likelihood up to a constant, sigma_hat^2) at rho."""
    L = len(sys_.lab_ids)
    S = np.eye(L) + rho * sys_.A
    sign, logdet = np.linalg.slogdet(S)
    if sign <= 0:
        return math.inf, math.nan
    quad = sys_.rtr - rho * float(sys_.b @ np.linalg.solve(S, sys_.b))
    sigma2 = max(quad, 1e-300) / sys_.df
    nll = 0.5 * (sys_.df * math.log(sigma2) + logdet)
    return nll, sigma2


@dataclass(frozen=True)
class K5Fit:
    lab_ids: Tuple[str, ...]
    beta: np.ndarray
    cov: np.ndarray
    sigma2: float
    rho: float
    method: str  # "k5" | "fixed"
    n_obs: int
    n_patients_informative: int

    @property
    def tau(self) -> float:
        return math.sqrt(self.rho * self.sigma2) if math.isfinite(self.rho) else math.nan

    def index(self, lab_id: object) -> Optional[int]:
        try:
            return self.lab_ids.index(str(lab_id))
        except ValueError:
            return None

    def contrast(self, a: object, b: object) -> Tuple[float, float]:
        """Estimate and standard deviation of beta_a - beta_b. An unseen laboratory has mean 0 and sd tau."""
        ia, ib = self.index(a), self.index(b)
        w = np.zeros(len(self.lab_ids))
        extra_var = 0.0
        if ia is None:
            extra_var += self.sigma2 * self.rho if self.method == "k5" else math.inf
        else:
            w[ia] += 1.0
        if ib is None:
            extra_var += self.sigma2 * self.rho if self.method == "k5" else math.inf
        else:
            w[ib] -= 1.0
        est = float(w @ self.beta)
        var = float(w @ self.cov @ w) + extra_var
        return est, math.sqrt(max(var, 0.0))


def posterior_at_rho(system: ProjectedSystem, rho: float) -> K5Fit:
    """Posterior of the offsets for a given rho (sigma^2 profiled out). rho -> 0 gives 0; rho -> inf gives fixed."""
    _, sigma2 = _profile(rho, system)
    L = len(system.lab_ids)
    P = np.linalg.inv(system.A + np.eye(L) / rho)
    return K5Fit(
        lab_ids=system.lab_ids,
        beta=P @ system.b,
        cov=sigma2 * P,
        sigma2=sigma2,
        rho=rho,
        method="k5",
        n_obs=system.n_obs,
        n_patients_informative=system.n_patients_informative,
    )


def fit_k5(system: ProjectedSystem) -> K5Fit:
    """Partial pooling: REML for (sigma^2, rho), then the posterior mean and covariance of the offsets."""
    if system.df <= 0:
        raise ValueError("no patient has three or more results: nothing to estimate")
    nlls = np.array([_profile(r, system)[0] for r in RHO_GRID])
    k = int(np.argmin(nlls))
    lo, hi = RHO_GRID[max(k - 1, 0)], RHO_GRID[min(k + 1, len(RHO_GRID) - 1)]
    if lo < hi:
        res = minimize_scalar(
            lambda lr: _profile(math.exp(lr), system)[0],
            bounds=(math.log(lo), math.log(hi)),
            method="bounded",
            options={"xatol": 1e-8},
        )
        rho = math.exp(res.x) if res.fun <= nlls[k] else float(RHO_GRID[k])
    else:
        rho = float(RHO_GRID[k])
    return posterior_at_rho(system, rho)


def fit_fixed(system: ProjectedSystem) -> K5Fit:
    """Per-laboratory fixed offsets, minimum-norm gauge: components not connected by switching patients are 0."""
    if system.df <= 0:
        raise ValueError("no patient has three or more results: nothing to estimate")
    pinv = np.linalg.pinv(system.A, rcond=1e-10)
    beta = pinv @ system.b
    rank = int(np.linalg.matrix_rank(system.A, tol=1e-9))
    resid_df = max(system.df - rank, 1)
    rss = max(system.rtr - float(system.b @ beta), 1e-300)
    sigma2 = rss / resid_df
    return K5Fit(
        lab_ids=system.lab_ids,
        beta=beta,
        cov=sigma2 * pinv,
        sigma2=sigma2,
        rho=math.inf,
        method="fixed",
        n_obs=system.n_obs,
        n_patients_informative=system.n_patients_informative,
    )


def fit_legacy_mean_shrinkage(
    lab: Sequence[object], value: Sequence[float], shrinkage: float = LEGACY_SHRINKAGE
) -> Dict[str, float]:
    """The earlier K5 rule on the log scale: shrink a laboratory's mean toward the global mean.

    Kept only as a comparator. It cannot separate a laboratory that reads high from a laboratory that sees
    sicker patients, because it never compares the same patient across laboratories.
    """
    z = np.log(np.asarray(value, dtype=float))
    labs = np.asarray([str(x) for x in lab])
    g = float(z.mean())
    out: Dict[str, float] = {}
    for lab_id in sorted(set(labs.tolist())):
        zl = z[labs == lab_id]
        w = len(zl) / (len(zl) + shrinkage)
        out[lab_id] = float(w * (zl.mean() - g))
    return out


# --------------------------------------------------------------------------------------------
# Harmoniser (the shippable object)
# --------------------------------------------------------------------------------------------
class LabHarmoniserK5:
    """Fits offsets for one analyte and divides each result by exp(offset of its laboratory)."""

    def __init__(self, analyte: str = "ca_15_3"):
        self.analyte = analyte
        self.fit_: Optional[K5Fit] = None

    def fit(
        self,
        patient: Sequence[object],
        t_days: Sequence[float],
        lab: Sequence[object],
        value: Sequence[float],
    ) -> "LabHarmoniserK5":
        self.fit_ = fit_k5(build_projected_system(patient, t_days, lab, value))
        return self

    def _need(self) -> K5Fit:
        if self.fit_ is None:
            raise RuntimeError("fit() first")
        return self.fit_

    def offsets(self) -> Dict[str, float]:
        f = self._need()
        return {lab_id: float(b) for lab_id, b in zip(f.lab_ids, f.beta)}

    def harmonise(self, lab: Sequence[object], value: Sequence[float]) -> np.ndarray:
        """value / exp(offset). A laboratory not seen in fitting is left unchanged (offset 0)."""
        f = self._need()
        table = {lab_id: float(b) for lab_id, b in zip(f.lab_ids, f.beta)}
        beta = np.array([table.get(str(x), 0.0) for x in lab], dtype=float)
        return np.asarray(value, dtype=float) / np.exp(beta)

    # ---- export (no pickle) ----------------------------------------------------------------
    def to_arrays_and_meta(self) -> Tuple[Dict[str, np.ndarray], Dict[str, str]]:
        f = self._need()
        meta = {
            "format": "vigil-k5-v1",
            "analyte": self.analyte,
            "lab_ids": json.dumps(list(f.lab_ids)),
            "sigma2": repr(float(f.sigma2)),
            "rho": repr(float(f.rho)),
            "method": f.method,
            "n_obs": str(f.n_obs),
            "n_patients_informative": str(f.n_patients_informative),
        }
        return {"beta": np.asarray(f.beta, dtype=np.float64), "cov": np.asarray(f.cov, dtype=np.float64)}, meta

    def save_safetensors(self, path: Path) -> None:
        from safetensors.numpy import save_file

        arrays, meta = self.to_arrays_and_meta()
        save_file(arrays, str(path), metadata=meta)

    @classmethod
    def load_safetensors(cls, path: Path) -> "LabHarmoniserK5":
        from safetensors import safe_open

        with safe_open(str(path), framework="numpy") as fh:
            meta = fh.metadata()
            beta = fh.get_tensor("beta")
            cov = fh.get_tensor("cov")
        if meta.get("format") != "vigil-k5-v1":
            raise ValueError("not a vigil K5 file")
        obj = cls(analyte=meta["analyte"])
        obj.fit_ = K5Fit(
            lab_ids=tuple(json.loads(meta["lab_ids"])),
            beta=beta,
            cov=cov,
            sigma2=float(meta["sigma2"]),
            rho=float(meta["rho"]),
            method=meta["method"],
            n_obs=int(meta["n_obs"]),
            n_patients_informative=int(meta["n_patients_informative"]),
        )
        return obj

    def export_onnx(self, path: Path) -> List[str]:
        """ONNX graph: inputs `value` (double, [N]) and `lab_index` (int64, [N]); output `harmonised`.

        `lab_index` indexes `lab_ids`; the value `len(lab_ids)` means "laboratory not seen in fitting" and maps
        to offset 0. Returns the lab-id order the caller must use to build `lab_index`.
        """
        import onnx
        from onnx import TensorProto, helper, numpy_helper

        f = self._need()
        table = np.r_[np.asarray(f.beta, dtype=np.float64), 0.0]
        nodes = [
            helper.make_node("Gather", ["beta_table", "lab_index"], ["beta_n"], axis=0),
            helper.make_node("Exp", ["beta_n"], ["scale"]),
            helper.make_node("Div", ["value", "scale"], ["harmonised"]),
        ]
        graph = helper.make_graph(
            nodes,
            "vigil_k5_harmonise",
            [
                helper.make_tensor_value_info("value", TensorProto.DOUBLE, ["N"]),
                helper.make_tensor_value_info("lab_index", TensorProto.INT64, ["N"]),
            ],
            [helper.make_tensor_value_info("harmonised", TensorProto.DOUBLE, ["N"])],
            initializer=[numpy_helper.from_array(table, name="beta_table")],
        )
        model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)])
        model.ir_version = 9
        onnx.checker.check_model(model)
        onnx.save(model, str(path))
        return list(f.lab_ids)


# --------------------------------------------------------------------------------------------
# Laboratory-stream changepoint detection
# --------------------------------------------------------------------------------------------
def one_step_residuals(
    patient: Sequence[object], calendar_day: Sequence[float], h: Sequence[float]
) -> np.ndarray:
    """For each result: h minus the mean of the same patient's earlier results (NaN for a first result).

    "Earlier" is by calendar day, across laboratories. Uses nothing from the future of the patient.
    """
    patient = np.asarray(patient)
    cal = np.asarray(calendar_day, dtype=float)
    h = np.asarray(h, dtype=float)
    out = np.full(len(h), np.nan)
    order = np.lexsort((cal, patient))
    run_sum, run_n, prev_patient = 0.0, 0, None
    for idx in order:
        if patient[idx] != prev_patient:
            run_sum, run_n, prev_patient = 0.0, 0, patient[idx]
        if run_n > 0:
            out[idx] = h[idx] - run_sum / run_n
        run_sum += h[idx]
        run_n += 1
    return out


def mad_sd(x: Sequence[float]) -> float:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    return float(1.4826 * np.median(np.abs(x - np.median(x))))


def cusum_first_alarm(standardised: Sequence[float], slack: float, threshold: float) -> Optional[int]:
    """Index of the first alarm of S_n = max(0, S_{n-1} + x_n - slack) >= threshold, else None."""
    s = 0.0
    for n, x in enumerate(standardised):
        s = max(0.0, s + float(x) - slack)
        if s >= threshold:
            return n
    return None


def cusum_alarm_count(streams: Sequence[Sequence[float]], slack: float, threshold: float) -> int:
    """Number of alarms over the streams; an alarm restarts the chart."""
    alarms = 0
    for stream in streams:
        c = 0.0
        for x in stream:
            c = max(0.0, c + float(x) - slack)
            if c >= threshold:
                alarms += 1
                c = 0.0
    return alarms


def calibrate_cusum_threshold(
    null_streams: Sequence[Sequence[float]],
    slack: float = 0.5,
    max_alarms_per_obs: float = 1.0 / 1500.0,
    grid: Optional[Sequence[float]] = None,
) -> float:
    """Smallest threshold on the grid whose alarm count on the null streams is <= max_alarms_per_obs * n.

    An alarm restarts the chart (S set to 0), so the count is the number of alarms in the whole stream.
    """
    grid = list(np.arange(2.0, 15.0001, 0.25)) if grid is None else list(grid)
    total = sum(len(s) for s in null_streams)
    for h in grid:
        if cusum_alarm_count(null_streams, slack, h) <= max_alarms_per_obs * total:
            return float(h)
    return float(grid[-1])  # target not attainable on the grid: the caller must check (see the study runner)


__all__ = [
    "K5Fit",
    "LabHarmoniserK5",
    "ProjectedSystem",
    "build_projected_system",
    "calibrate_cusum_threshold",
    "cusum_alarm_count",
    "cusum_first_alarm",
    "fit_fixed",
    "fit_k5",
    "fit_legacy_mean_shrinkage",
    "posterior_at_rho",
    "mad_sd",
    "one_step_residuals",
]
