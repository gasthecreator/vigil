"""
packages/vigil-ml/vigil_ml/k1.py

Model K1: synthetic kinetic parameter-inference research module.
Implements the K1 Acceptance Contract specified in docs/ml/K1-CONTRACT.md.

Inference routes:
- amortized: trained neural recognition network (no per-patient optimization at inference)
- ukf: contract compatibility key for a sequential particle filter
- nuts: NumPyro NUTS on the shared observation likelihood
- npe: conditional Gaussian-mixture density estimator trained on simulator pairs
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

import jax
import jax.numpy as jnp
import numpy as np
import numpyro
import numpyro.distributions as dist
import torch
import torch.nn as nn
from numpyro.diagnostics import summary as mcmc_summary
from numpyro.infer import MCMC, NUTS
from safetensors import safe_open
from safetensors.torch import load_file
from scipy.special import expit, logit

# Single-threaded configuration for numerical stability on macOS Apple Silicon
torch.set_num_threads(1)

MODELS_DIR = Path(__file__).resolve().parent / "models"
AMORTIZED_WEIGHTS_PATH = MODELS_DIR / "k1_amortized_weights.safetensors"
NPE_WEIGHTS_PATH = MODELS_DIR / "k1_npe_weights.safetensors"
ASSUMPTIONS_PATH = MODELS_DIR / "k1_assumptions.json"
ARTIFACT_MANIFEST_PATH = MODELS_DIR / "k1_artifact_manifest.json"
ASSUMPTIONS = json.loads(ASSUMPTIONS_PATH.read_text(encoding="utf-8"))
if ASSUMPTIONS.get("status") != "synthetic_research_assumptions":
    raise ValueError("K1 assumptions must explicitly remain research-only synthetic assumptions")
if ASSUMPTIONS.get("time_unit") != "day":
    raise ValueError("K1 assumptions must express time in days")

PARAM_CONFIG = ASSUMPTIONS["parameters"]
INFERENCE_CONFIG = ASSUMPTIONS["inference"]
TRAINING_CONFIG = ASSUMPTIONS["training"]
LO_BOUNDS = np.array([PARAM_CONFIG[name]["lower"] for name in (
    "doubling_time_days", "shedding_ca153", "clearance_ca153", "onset_day"
)])
HI_BOUNDS = np.array([PARAM_CONFIG[name]["upper"] for name in (
    "doubling_time_days", "shedding_ca153", "clearance_ca153", "onset_day"
)])
OBS_CONFIG = ASSUMPTIONS["analytes"]["ca153"]
BASELINE_CA153 = float(OBS_CONFIG["baseline"])
OBSERVATION_SD = float(OBS_CONFIG["measurement_noise"]["standard_deviation"])
BURDEN_AT_ONSET = float(ASSUMPTIONS["dynamics"]["burden_at_onset"])
SCHEDULE = np.asarray(ASSUMPTIONS["reference_schedule_days"], dtype=np.float64)
REFERENCE_PARAMS = np.asarray(ASSUMPTIONS["identifiability_reference_parameters"], dtype=np.float64)
MID_BOUNDS = 0.5 * (LO_BOUNDS + HI_BOUNDS)
SPAN_BOUNDS = 0.5 * (HI_BOUNDS - LO_BOUNDS)
AMORTIZED_LOG_SCALE_BOUNDS = tuple(INFERENCE_CONFIG["amortized_log_scale_bounds"])
NPE_LOG_SCALE_BOUNDS = tuple(INFERENCE_CONFIG["npe_log_scale_bounds"])
if (
    not np.all(np.isfinite(LO_BOUNDS))
    or not np.all(np.isfinite(HI_BOUNDS))
    or np.any(LO_BOUNDS >= HI_BOUNDS)
    or not np.all(np.isfinite(SCHEDULE))
    or np.any(np.diff(SCHEDULE) <= 0)
    or len(SCHEDULE) != TRAINING_CONFIG["time_bin_count"]
    or REFERENCE_PARAMS.shape != LO_BOUNDS.shape
    or np.any(REFERENCE_PARAMS < LO_BOUNDS)
    or np.any(REFERENCE_PARAMS > HI_BOUNDS)
    or not np.isfinite(BASELINE_CA153)
    or not np.isfinite(OBSERVATION_SD)
    or OBSERVATION_SD <= 0
    or not np.isfinite(BURDEN_AT_ONSET)
    or BURDEN_AT_ONSET <= 0
    or INFERENCE_CONFIG["default_posterior_draws"] <= 0
    or TRAINING_CONFIG["default_validation_seed_offset"] <= 0
    or any(
        TRAINING_CONFIG[name] <= 0
        for name in (
            "default_amortized_simulations",
            "default_amortized_epochs",
            "default_npe_simulations",
            "default_npe_epochs",
        )
    )
    or not 0 < INFERENCE_CONFIG["unconstrained_logit_clip_epsilon"] < 0.5
    or INFERENCE_CONFIG["identifiability_finite_difference_fraction_of_half_range"] <= 0
    or any(
        len(bounds) != 2
        or not np.all(np.isfinite(bounds))
        or bounds[0] >= bounds[1]
        for bounds in (AMORTIZED_LOG_SCALE_BOUNDS, NPE_LOG_SCALE_BOUNDS)
    )
    or any(PARAM_CONFIG[name].get("prior") != "uniform" for name in (
        "doubling_time_days", "shedding_ca153", "clearance_ca153", "onset_day"
    ))
    or OBS_CONFIG["measurement_noise"].get("distribution") != "normal"
):
    raise ValueError("K1 synthetic assumptions configuration is invalid or internally inconsistent")


@dataclass(frozen=True)
class K1Params:
    """Ground truth and posterior kinetic parameters for Model K1."""

    doubling_time_days: float  # tumour doubling time (days)
    shedding_ca153: float  # marker shedding rate per unit burden
    clearance_ca153: float  # marker clearance rate (1/day)
    onset_day: float  # recurrence seeding day (>0)


PARAM_NAMES: tuple[str, ...] = (
    "doubling_time_days",
    "shedding_ca153",
    "clearance_ca153",
    "onset_day",
)


def sample_prior(rng: np.random.Generator) -> K1Params:
    """Draw from the explicitly synthetic, versioned research prior."""
    return K1Params(
        **{
            name: float(rng.uniform(LO_BOUNDS[i], HI_BOUNDS[i]))
            for i, name in enumerate(PARAM_NAMES)
        }
    )


@dataclass
class K1Observations:
    """Patient longitudinal observation record over visit schedules."""

    days: np.ndarray
    values: dict[str, np.ndarray]

    def __post_init__(self) -> None:
        days = np.asarray(self.days, dtype=np.float64)
        if days.ndim != 1 or not np.all(np.isfinite(days)):
            raise ValueError("observation days must be a finite one-dimensional array")
        if np.any(np.diff(days) <= 0):
            raise ValueError("observation days must be strictly increasing")
        normalized: dict[str, np.ndarray] = {}
        for analyte, raw in self.values.items():
            values = np.asarray(raw, dtype=np.float64)
            if values.ndim != 1 or len(values) != len(days):
                raise ValueError(f"{analyte} values must be one-dimensional and align with days")
            if np.any(np.isinf(values)):
                raise ValueError(f"{analyte} values may be finite or NaN, never infinite")
            normalized[analyte] = values
        self.days = days
        self.values = normalized


def simulate_patient(
    params: K1Params,
    schedule_days: Sequence[float],
    rng: np.random.Generator,
    measurement_noise_sd: float | None = None,
) -> K1Observations:
    """
    Forward-simulate observed analytes with measurement noise using the SAME dynamics
    the inference routes assume (the model's continuous ODE + observation model).

    The numerical assumptions are loaded from `models/k1_assumptions.json`; they are
    synthetic research assumptions, not clinically calibrated values.
    """
    days = np.array(schedule_days, dtype=float)
    parameter_values = np.array([getattr(params, name) for name in PARAM_NAMES], dtype=float)
    if (
        not np.all(np.isfinite(parameter_values))
        or np.any(parameter_values < LO_BOUNDS)
        or np.any(parameter_values > HI_BOUNDS)
    ):
        raise ValueError("K1 parameters must be finite and within configured synthetic prior bounds")
    T_d = params.doubling_time_days
    s = params.shedding_ca153
    c = params.clearance_ca153
    t_onset = params.onset_day

    g = np.log(2.0) / T_d
    dt = np.maximum(0.0, days - t_onset)
    elev = np.where(
        days >= t_onset,
        s * BURDEN_AT_ONSET / (g + c) * (np.exp(g * dt) - np.exp(-c * dt)),
        0.0,
    )
    mu = BASELINE_CA153 + elev
    noise_sd = OBSERVATION_SD if measurement_noise_sd is None else float(measurement_noise_sd)
    if not np.isfinite(noise_sd) or noise_sd <= 0:
        raise ValueError("measurement_noise_sd must be finite and positive")
    ca153 = mu + rng.normal(0.0, noise_sd, size=len(days))
    return K1Observations(days=days, values={"ca153": ca153})


def _expected_ca153(params: K1Params, days: np.ndarray) -> np.ndarray:
    growth = np.log(2.0) / params.doubling_time_days
    elapsed = np.maximum(0.0, days - params.onset_day)
    excess = params.shedding_ca153 * BURDEN_AT_ONSET / (growth + params.clearance_ca153) * (
        np.exp(growth * elapsed) - np.exp(-params.clearance_ca153 * elapsed)
    )
    return BASELINE_CA153 + np.where(days >= params.onset_day, excess, 0.0)


def _expected_ca153_samples(samples: dict[str, np.ndarray], days: np.ndarray) -> np.ndarray:
    """Evaluate the shared mechanistic mean for posterior draws at arbitrary days."""
    matrix = np.column_stack([np.asarray(samples[name], dtype=np.float64) for name in PARAM_NAMES])
    days = np.asarray(days, dtype=np.float64)
    if matrix.ndim != 2 or len(matrix) == 0 or days.ndim != 1:
        raise ValueError("posterior parameters and prediction days must be non-empty vectors")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(days)):
        raise ValueError("posterior parameters and prediction days must be finite")
    growth = np.log(2.0) / matrix[:, 0, None]
    elapsed = np.maximum(0.0, days[None, :] - matrix[:, 3, None])
    excess = matrix[:, 1, None] * BURDEN_AT_ONSET / (growth + matrix[:, 2, None]) * (
        np.exp(growth * elapsed) - np.exp(-matrix[:, 2, None] * elapsed)
    )
    return BASELINE_CA153 + np.where(days[None, :] >= matrix[:, 3, None], excess, 0.0)


def _observed_ca153(obs: K1Observations) -> tuple[np.ndarray, np.ndarray]:
    if "ca153" not in obs.values:
        raise ValueError("K1 observations require the ca153 analyte key")
    values = np.asarray(obs.values["ca153"], dtype=np.float64)
    measured = np.isfinite(values)
    return obs.days[measured], values[measured]


def _log_likelihood(params: K1Params, obs: K1Observations) -> float:
    days, values = _observed_ca153(obs)
    if len(days) == 0:
        return 0.0
    residual = (values - _expected_ca153(params, days)) / OBSERVATION_SD
    return float(-0.5 * np.sum(residual**2 + np.log(2.0 * np.pi * OBSERVATION_SD**2)))


# ---------------------------------------------------------------------------
# Route: Sequential Particle Filter (UKF / Particle filter route)
# ---------------------------------------------------------------------------
class SequentialParticleFilter:
    """
    Sequential particle filter tracking tumor burden and marker trajectory
    across discrete visit days, performing sequential likelihood updates over the parameter prior.
    """

    def __init__(self, n_particles: int | None = None) -> None:
        self.n_particles = (
            INFERENCE_CONFIG["particle_count"] if n_particles is None else int(n_particles)
        )

    def filter(
        self,
        obs: K1Observations,
        rng: np.random.Generator,
        n_draws: int | None = None,
    ) -> dict[str, np.ndarray]:
        n_draws = INFERENCE_CONFIG["default_posterior_draws"] if n_draws is None else n_draws
        if n_draws <= 0 or self.n_particles <= 0:
            raise ValueError("particle and posterior draw counts must be positive")
        days, values = _observed_ca153(obs)
        particles = rng.uniform(LO_BOUNDS, HI_BOUNDS, size=(self.n_particles, len(PARAM_NAMES)))
        if len(days) == 0:
            idx = rng.integers(self.n_particles, size=n_draws)
            return {name: particles[idx, i] for i, name in enumerate(PARAM_NAMES)} | {
                "prior_only": True,
                "diagnostics": {
                    "ess_fraction_min": None,
                    "ess_fraction_median": None,
                    "resampling_count": 0,
                    "unique_particles_final": self.n_particles,
                },
            }

        log_weights = np.full(self.n_particles, -np.log(self.n_particles))
        ess_fractions: list[float] = []
        resampling_count = 0
        for day, value in zip(days, values, strict=True):
            theta = particles
            growth = np.log(2.0) / theta[:, 0]
            elapsed = np.maximum(0.0, day - theta[:, 3])
            excess = theta[:, 1] * BURDEN_AT_ONSET / (growth + theta[:, 2]) * (
                np.exp(growth * elapsed) - np.exp(-theta[:, 2] * elapsed)
            )
            mean = BASELINE_CA153 + np.where(day >= theta[:, 3], excess, 0.0)
            residual = (value - mean) / OBSERVATION_SD
            log_weights += -0.5 * (residual**2 + np.log(2.0 * np.pi * OBSERVATION_SD**2))
            log_weights -= np.max(log_weights)
            weights = np.exp(log_weights)
            total = weights.sum()
            if not np.isfinite(total) or total <= 0:
                raise FloatingPointError("particle likelihood collapsed to non-finite weights")
            weights /= total
            ess = 1.0 / np.sum(weights**2)
            ess_fractions.append(float(ess / self.n_particles))
            if ess < self.n_particles * INFERENCE_CONFIG["particle_resampling_ess_fraction"]:
                selected = rng.choice(self.n_particles, size=self.n_particles, p=weights)
                particles = particles[selected]
                log_weights.fill(-np.log(self.n_particles))
                resampling_count += 1

        weights = np.exp(log_weights - np.max(log_weights))
        weights /= weights.sum()
        idx = rng.choice(self.n_particles, size=n_draws, p=weights)
        return {name: particles[idx, i] for i, name in enumerate(PARAM_NAMES)} | {
            "diagnostics": {
                "ess_fraction_min": float(np.min(ess_fractions)),
                "ess_fraction_median": float(np.median(ess_fractions)),
                "resampling_count": resampling_count,
                "unique_particles_final": int(np.unique(particles, axis=0).shape[0]),
            },
        }


def _route_ukf(
    obs: K1Observations, rng: np.random.Generator, n_draws: int | None = None
) -> dict[str, np.ndarray]:
    n_draws = INFERENCE_CONFIG["default_posterior_draws"] if n_draws is None else n_draws
    pf = SequentialParticleFilter(n_particles=INFERENCE_CONFIG["particle_count"])
    return pf.filter(obs, rng, n_draws=n_draws)


# ---------------------------------------------------------------------------
# Route: Reference Gold-Standard NUTS (NumPyro NUTS)
# ---------------------------------------------------------------------------
def _numpyro_k1_model(days: jnp.ndarray, y_obs: jnp.ndarray | None = None) -> None:
    T_d = numpyro.sample("doubling_time_days", dist.Uniform(LO_BOUNDS[0], HI_BOUNDS[0]))
    s = numpyro.sample("shedding_ca153", dist.Uniform(LO_BOUNDS[1], HI_BOUNDS[1]))
    c = numpyro.sample("clearance_ca153", dist.Uniform(LO_BOUNDS[2], HI_BOUNDS[2]))
    t_onset = numpyro.sample("onset_day", dist.Uniform(LO_BOUNDS[3], HI_BOUNDS[3]))

    g = jnp.log(2.0) / T_d
    dt = jnp.maximum(0.0, days - t_onset)
    elev = jnp.where(
        days >= t_onset,
        (s * BURDEN_AT_ONSET) / (g + c) * (jnp.exp(g * dt) - jnp.exp(-c * dt)),
        0.0,
    )
    mu = BASELINE_CA153 + elev
    numpyro.sample("y", dist.Normal(mu, OBSERVATION_SD), obs=y_obs)


_NUTS_KERNEL = NUTS(
    _numpyro_k1_model,
    target_accept_prob=INFERENCE_CONFIG["nuts_target_accept_probability"],
)


def _route_nuts(
    obs: K1Observations, rng: np.random.Generator, n_draws: int | None = None
) -> dict[str, np.ndarray]:
    n_draws = INFERENCE_CONFIG["default_posterior_draws"] if n_draws is None else n_draws
    if n_draws <= 0:
        raise ValueError("n_draws must be positive")
    days_np, values_np = _observed_ca153(obs)
    if len(days_np) == 0:
        return {
            name: rng.uniform(LO_BOUNDS[i], HI_BOUNDS[i], size=n_draws)
            for i, name in enumerate(PARAM_NAMES)
        } | {
            "prior_only": True,
        }

    days = jnp.asarray(days_np)
    ca153 = jnp.asarray(values_np)
    seed = int(rng.integers(0, 2**31 - 1))
    samples_per_chain = int(np.ceil(n_draws / INFERENCE_CONFIG["nuts_chains"]))
    mcmc = MCMC(
        _NUTS_KERNEL,
        num_warmup=INFERENCE_CONFIG["nuts_warmup"],
        num_samples=samples_per_chain,
        num_chains=INFERENCE_CONFIG["nuts_chains"],
        progress_bar=False,
    )
    mcmc.run(jax.random.PRNGKey(seed), days=days, y_obs=ca153)
    raw = mcmc.get_samples()
    grouped = mcmc.get_samples(group_by_chain=True)
    diagnostics = mcmc_summary(grouped)
    extra = mcmc.get_extra_fields(group_by_chain=True)
    return {
        **{name: np.asarray(raw[name])[:n_draws] for name in PARAM_NAMES},
        "diagnostics": {
            "r_hat": {name: float(diagnostics[name]["r_hat"]) for name in PARAM_NAMES},
            "effective_sample_size": {
                name: float(diagnostics[name]["n_eff"]) for name in PARAM_NAMES
            },
            "divergences": int(np.sum(extra.get("diverging", 0))),
            "chains": INFERENCE_CONFIG["nuts_chains"],
            "warmup_per_chain": INFERENCE_CONFIG["nuts_warmup"],
            "samples_per_chain": samples_per_chain,
        },
    }


# ---------------------------------------------------------------------------
# Route: Amortized Neural Recognition Network
# ---------------------------------------------------------------------------
class AmortizedRecognitionNet(nn.Module):
    """
    Trained recognition network mapping longitudinal visit trajectories
    directly to parameter posterior distribution moments (mu).
    """

    def __init__(self) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(2 * len(SCHEDULE), INFERENCE_CONFIG["neural_hidden_dimensions"][0]),
            nn.Tanh(),
            nn.Linear(
                INFERENCE_CONFIG["neural_hidden_dimensions"][0],
                INFERENCE_CONFIG["neural_hidden_dimensions"][1],
            ),
            nn.Tanh(),
            nn.Linear(INFERENCE_CONFIG["neural_hidden_dimensions"][1], 2 * len(PARAM_NAMES)),
        )
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        out = self.net(x)
        mean, log_scale = out.chunk(2, dim=-1)
        return mean, torch.clamp(
            log_scale,
            min=AMORTIZED_LOG_SCALE_BOUNDS[0],
            max=AMORTIZED_LOG_SCALE_BOUNDS[1],
        )


_AMORTIZED_MODEL: AmortizedRecognitionNet | None = None


def _get_or_load_amortized_model() -> AmortizedRecognitionNet:
    global _AMORTIZED_MODEL
    if _AMORTIZED_MODEL is not None:
        return _AMORTIZED_MODEL

    if not AMORTIZED_WEIGHTS_PATH.exists():
        raise RuntimeError("K1 amortized weights are absent; run the registered training script first")
    model = AmortizedRecognitionNet()
    state_dict = _load_registered_state_dict(AMORTIZED_WEIGHTS_PATH, "amortized")
    model.load_state_dict(state_dict, strict=True)
    model.eval()
    _AMORTIZED_MODEL = model
    return _AMORTIZED_MODEL


AMORTIZED_CENTER = MID_BOUNDS.copy()
AMORTIZED_SCALE = SPAN_BOUNDS.copy()


def _to_unconstrained(parameters: np.ndarray) -> np.ndarray:
    unit = (parameters - LO_BOUNDS) / (HI_BOUNDS - LO_BOUNDS)
    epsilon = INFERENCE_CONFIG["unconstrained_logit_clip_epsilon"]
    return logit(np.clip(unit, epsilon, 1.0 - epsilon))


def _from_unconstrained(values: np.ndarray) -> np.ndarray:
    return LO_BOUNDS + (HI_BOUNDS - LO_BOUNDS) * expit(values)


def _summarize_observations(obs: K1Observations) -> np.ndarray:
    """Return one observed-value mean and an explicit count indicator per time bin."""
    days, values = _observed_ca153(obs)
    if len(days) == 0:
        return np.zeros(2 * len(SCHEDULE), dtype=np.float32)
    edges = np.concatenate(([-np.inf], (SCHEDULE[:-1] + SCHEDULE[1:]) / 2, [np.inf]))
    binned = np.zeros(len(SCHEDULE), dtype=np.float32)
    measured = np.zeros(len(SCHEDULE), dtype=np.float32)
    for index in range(len(SCHEDULE)):
        in_bin = (days >= edges[index]) & (days < edges[index + 1])
        if in_bin.any():
            binned[index] = float(np.mean(values[in_bin]) - BASELINE_CA153) / OBSERVATION_SD
            measured[index] = 1.0
    return np.concatenate((binned, measured))


def train_amortized(
    n_sims: int | None = None,
    seed: int | None = None,
    shuffle_pairs: bool = False,
    epochs: int | None = None,
    validation_seed: int | None = None,
) -> dict[str, Any]:
    """
    Train amortized recognition network on simulator draws via genuine gradient descent.
    Returns real posterior-mean MSE and optimized Gaussian NLL histories on independent
    validation simulations, plus the trained model.
    """
    n_sims = TRAINING_CONFIG["default_amortized_simulations"] if n_sims is None else n_sims
    seed = INFERENCE_CONFIG["default_random_seed"] if seed is None else seed
    epochs = TRAINING_CONFIG["default_amortized_epochs"] if epochs is None else epochs
    if n_sims < 10 or epochs < 1:
        raise ValueError("n_sims must be at least 10 and epochs must be positive")
    rng = np.random.default_rng(seed)
    val_rng = np.random.default_rng(
        seed + TRAINING_CONFIG["default_validation_seed_offset"]
        if validation_seed is None
        else validation_seed
    )
    torch.manual_seed(seed)
    def generate(rng_local: np.random.Generator, count: int) -> tuple[np.ndarray, np.ndarray]:
        theta_values = rng_local.uniform(LO_BOUNDS, HI_BOUNDS, size=(count, len(PARAM_NAMES)))
        features = np.zeros((count, 2 * len(SCHEDULE)), dtype=np.float32)
        for row_index, row in enumerate(theta_values):
            schedule = SCHEDULE + rng_local.uniform(
                -TRAINING_CONFIG["schedule_jitter_days"],
                TRAINING_CONFIG["schedule_jitter_days"],
                size=len(SCHEDULE),
            )
            schedule[0] = 0.0
            params = K1Params(**dict(zip(PARAM_NAMES, row, strict=True)))
            observation = simulate_patient(params, schedule, rng_local)
            keep = rng_local.random(len(schedule)) >= TRAINING_CONFIG["missing_visit_probability"]
            keep[0] = True
            features[row_index] = _summarize_observations(
                K1Observations(
                    days=schedule,
                    values={"ca153": np.where(keep, observation.values["ca153"], np.nan)},
                )
            )
        return features, _to_unconstrained(theta_values).astype(np.float32)

    X, theta = generate(rng, n_sims)
    X_val_raw, theta_val_raw = generate(val_rng, max(1, n_sims // 4))
    if shuffle_pairs:
        # Break the simulator's feature/parameter correspondence. Applying the
        # same permutation to both arrays only reorders intact pairs and leaves
        # the negative control equivalent to the real training run.
        perm = rng.permutation(n_sims)
        theta = theta[perm]
    X_train = torch.tensor(X, dtype=torch.float32)
    y_train = torch.tensor(theta, dtype=torch.float32)
    X_val = torch.tensor(X_val_raw, dtype=torch.float32)
    y_val = torch.tensor(theta_val_raw, dtype=torch.float32)

    model = AmortizedRecognitionNet()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=TRAINING_CONFIG["amortized_learning_rate"],
        weight_decay=TRAINING_CONFIG["weight_decay"],
    )
    criterion = nn.GaussianNLLLoss()
    batch_size = min(TRAINING_CONFIG["batch_size"], len(X_train))

    train_losses: list[float] = []
    val_losses: list[float] = []
    train_nll: list[float] = []
    val_nll: list[float] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_val_nll = float("inf")
    best_epoch = 0

    for _ in range(epochs):
        model.train()
        order = rng.permutation(len(X_train))
        for start in range(0, len(order), batch_size):
            batch = torch.as_tensor(order[start : start + batch_size], dtype=torch.long)
            optimizer.zero_grad()
            pred, log_scale = model(X_train[batch])
            loss = criterion(pred, y_train[batch], torch.exp(2.0 * log_scale))
            loss.backward()
            optimizer.step()

        model.eval()
        with torch.no_grad():
            train_pred, train_log_scale = model(X_train)
            vpred, vlog_scale = model(X_val)
            train_losses.append(float(torch.mean((train_pred - y_train) ** 2)))
            val_losses.append(float(torch.mean((vpred - y_val) ** 2)))
            train_nll.append(
                float(criterion(train_pred, y_train, torch.exp(2.0 * train_log_scale)))
            )
            current_val_nll = float(criterion(vpred, y_val, torch.exp(2.0 * vlog_scale)))
            val_nll.append(current_val_nll)
            if current_val_nll < best_val_nll:
                best_val_nll = current_val_nll
                best_epoch = len(val_nll)
                best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}

    if best_state is None:
        raise RuntimeError("amortized training produced no validation checkpoint")
    model.load_state_dict(best_state)

    return {
        "train_loss": train_losses,
        "val_loss": val_losses,
        "train_nll": train_nll,
        "val_nll": val_nll,
        "selected_epoch": best_epoch,
        "model": model,
    }


def _route_amortized(
    obs: K1Observations, rng: np.random.Generator, n_draws: int | None = None
) -> dict[str, np.ndarray]:
    """
    Amortized recognition route evaluating posterior draws in O(1) time.
    Distinct from other routes; does not alias other estimators.
    """
    n_draws = INFERENCE_CONFIG["default_posterior_draws"] if n_draws is None else n_draws
    if n_draws <= 0:
        raise ValueError("n_draws must be positive")
    days_arr, vals_arr = _observed_ca153(obs)
    if len(vals_arr) == 0:
        # With no measurements, preserve the prior instead of inventing observations.
        draws = rng.uniform(LO_BOUNDS, HI_BOUNDS, size=(n_draws, len(PARAM_NAMES)))
        return {name: draws[:, i] for i, name in enumerate(PARAM_NAMES)} | {"prior_only": True}

    net = _get_or_load_amortized_model()
    x_in = torch.tensor(_summarize_observations(obs), dtype=torch.float32).unsqueeze(0)
    with torch.no_grad():
        mean, log_scale = net(x_in)
        means = mean.numpy()[0]
        scales = np.exp(log_scale.numpy()[0])
    unconstrained = rng.normal(means, scales, size=(n_draws, len(PARAM_NAMES)))
    draws = _from_unconstrained(unconstrained)
    return {name: draws[:, i] for i, name in enumerate(PARAM_NAMES)}


# ---------------------------------------------------------------------------
# Route: Neural Posterior Estimation (conditional Gaussian mixture)
# ---------------------------------------------------------------------------
class NeuralPosteriorEstimator(nn.Module):
    """Conditional density estimator q(theta | summary), trained by simulation pairs."""

    def __init__(self, components: int | None = None) -> None:
        super().__init__()
        self.components = (
            INFERENCE_CONFIG["npe_mixture_components"] if components is None else components
        )
        hidden = INFERENCE_CONFIG["neural_hidden_dimensions"]
        self.encoder = nn.Sequential(
            nn.Linear(2 * len(SCHEDULE), hidden[0]), nn.Tanh(), nn.Linear(hidden[0], hidden[1]), nn.Tanh()
        )
        self.mixture = nn.Linear(
            hidden[1], self.components * (1 + 2 * len(PARAM_NAMES))
        )

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        raw = self.mixture(self.encoder(x)).view(-1, self.components, 1 + 2 * len(PARAM_NAMES))
        logits = raw[:, :, 0]
        means = raw[:, :, 1 : 1 + len(PARAM_NAMES)]
        log_scales = torch.clamp(
            raw[:, :, 1 + len(PARAM_NAMES) :],
            min=NPE_LOG_SCALE_BOUNDS[0],
            max=NPE_LOG_SCALE_BOUNDS[1],
        )
        return logits, means, log_scales


_NPE_MODEL: NeuralPosteriorEstimator | None = None


def _get_or_load_npe_model() -> NeuralPosteriorEstimator:
    global _NPE_MODEL
    if _NPE_MODEL is not None:
        return _NPE_MODEL
    if not NPE_WEIGHTS_PATH.exists():
        raise RuntimeError("K1 NPE weights are absent; run the registered training script first")
    model = NeuralPosteriorEstimator()
    model.load_state_dict(_load_registered_state_dict(NPE_WEIGHTS_PATH, "npe"), strict=True)
    model.eval()
    _NPE_MODEL = model
    return model


def _load_registered_state_dict(path: Path, estimator: str) -> dict[str, torch.Tensor]:
    """Load only finite weights matching the committed K1 artifact manifest."""
    manifest = json.loads(ARTIFACT_MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = manifest.get("artifacts", {}).get(path.name)
    if not isinstance(entry, dict) or entry.get("estimator") != estimator:
        raise ValueError(f"K1 {estimator} artifact is absent from its committed manifest")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != entry.get("sha256"):
        raise ValueError(f"K1 {estimator} artifact does not match its committed manifest digest")
    with safe_open(str(path), framework="pt", device="cpu") as artifact:
        metadata = artifact.metadata() or {}
    if metadata != entry.get("metadata"):
        raise ValueError(f"K1 {estimator} artifact metadata does not match its committed manifest")
    if manifest.get("assumptions_sha256") != hashlib.sha256(ASSUMPTIONS_PATH.read_bytes()).hexdigest():
        raise ValueError("K1 artifact manifest does not match the active synthetic assumptions")
    state_dict = load_file(str(path), device="cpu")
    if not state_dict or any(not torch.isfinite(tensor).all() for tensor in state_dict.values()):
        raise ValueError(f"K1 {estimator} artifact must contain finite model weights")
    return state_dict


def train_npe(
    n_sims: int | None = None,
    seed: int | None = None,
    epochs: int | None = None,
    validation_seed: int | None = None,
) -> dict[str, Any]:
    """Train a conditional mixture density on independent prior-predictive pairs."""
    n_sims = TRAINING_CONFIG["default_npe_simulations"] if n_sims is None else n_sims
    seed = INFERENCE_CONFIG["default_random_seed"] if seed is None else seed
    epochs = TRAINING_CONFIG["default_npe_epochs"] if epochs is None else epochs
    if n_sims < 10 or epochs < 1:
        raise ValueError("n_sims must be at least 10 and epochs must be positive")
    rng = np.random.default_rng(seed)
    val_rng = np.random.default_rng(
        seed + TRAINING_CONFIG["default_validation_seed_offset"]
        if validation_seed is None
        else validation_seed
    )
    torch.manual_seed(seed)
    def generate(rng_local: np.random.Generator, count: int) -> tuple[np.ndarray, np.ndarray]:
        theta_values = rng_local.uniform(LO_BOUNDS, HI_BOUNDS, size=(count, len(PARAM_NAMES)))
        features = np.empty((count, 2 * len(SCHEDULE)), dtype=np.float32)
        for i, row in enumerate(theta_values):
            schedule = SCHEDULE + rng_local.uniform(
                -TRAINING_CONFIG["schedule_jitter_days"],
                TRAINING_CONFIG["schedule_jitter_days"],
                size=len(SCHEDULE),
            )
            schedule[0] = 0.0
            params = K1Params(**dict(zip(PARAM_NAMES, row, strict=True)))
            simulated = simulate_patient(params, schedule, rng_local)
            mask = rng_local.random(len(schedule)) >= TRAINING_CONFIG["missing_visit_probability"]
            mask[0] = True
            features[i] = _summarize_observations(
                K1Observations(
                    days=schedule,
                    values={"ca153": np.where(mask, simulated.values["ca153"], np.nan)},
                )
            )
        return features, _to_unconstrained(theta_values).astype(np.float32)
    x, theta = generate(rng, n_sims)
    xv, yv = generate(val_rng, max(1, n_sims // 4))
    xt, yt = torch.as_tensor(x), torch.as_tensor(theta)
    xv, yv = torch.as_tensor(xv), torch.as_tensor(yv)
    model = NeuralPosteriorEstimator()
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=TRAINING_CONFIG["npe_learning_rate"],
        weight_decay=TRAINING_CONFIG["weight_decay"],
    )
    train_loss: list[float] = []
    val_loss: list[float] = []
    best_state: dict[str, torch.Tensor] | None = None
    best_val_nll = float("inf")
    best_epoch = 0
    batch_size = min(TRAINING_CONFIG["batch_size"], len(xt))
    for _ in range(epochs):
        model.train()
        order = rng.permutation(len(xt))
        epoch_loss = 0.0
        for start in range(0, len(order), batch_size):
            batch = torch.as_tensor(order[start : start + batch_size], dtype=torch.long)
            logits, means, log_scales = model(xt[batch])
            standardized = -0.5 * ((yt[batch, None, :] - means) / log_scales.exp()) ** 2
            component_log_prob = (
                torch.log_softmax(logits, dim=-1)
                + (-log_scales - 0.5 * np.log(2.0 * np.pi) + standardized).sum(dim=-1)
            )
            loss = -torch.logsumexp(component_log_prob, dim=-1).mean()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            epoch_loss += float(loss.detach()) * len(batch) / len(order)
        train_loss.append(epoch_loss)
        model.eval()
        with torch.no_grad():
            logits, means, log_scales = model(xv)
            component_log_prob = torch.log_softmax(logits, dim=-1) + (
                -log_scales
                - 0.5 * np.log(2.0 * np.pi)
                - 0.5 * ((yv[:, None, :] - means) / log_scales.exp()) ** 2
            ).sum(dim=-1)
            current_val_nll = float(-torch.logsumexp(component_log_prob, dim=-1).mean())
            val_loss.append(current_val_nll)
            if current_val_nll < best_val_nll:
                best_val_nll = current_val_nll
                best_epoch = len(val_loss)
                best_state = {name: value.detach().clone() for name, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("NPE training produced no validation checkpoint")
    model.load_state_dict(best_state)
    return {
        "train_loss": train_loss,
        "val_loss": val_loss,
        "val_nll": val_loss,
        "selected_epoch": best_epoch,
        "model": model,
    }


def _route_npe(
    obs: K1Observations, rng: np.random.Generator, n_draws: int | None = None
) -> dict[str, np.ndarray]:
    """Sample from the separately trained conditional Gaussian-mixture posterior."""
    n_draws = INFERENCE_CONFIG["default_posterior_draws"] if n_draws is None else n_draws
    if n_draws <= 0:
        raise ValueError("n_draws must be positive")
    if len(_observed_ca153(obs)[0]) == 0:
        draws = rng.uniform(LO_BOUNDS, HI_BOUNDS, size=(n_draws, len(PARAM_NAMES)))
        return {name: draws[:, i] for i, name in enumerate(PARAM_NAMES)} | {"prior_only": True}
    model = _get_or_load_npe_model()
    summary = torch.as_tensor(_summarize_observations(obs)).unsqueeze(0)
    with torch.no_grad():
        logits, means, log_scales = model(summary)
    logits_np = logits.numpy()[0]
    means_np = means.numpy()[0]
    scales_np = np.exp(log_scales.numpy()[0])
    component = rng.choice(len(logits_np), size=n_draws, p=np.exp(logits_np - logits_np.max()) / np.exp(logits_np - logits_np.max()).sum())
    unconstrained = rng.normal(means_np[component], scales_np[component])
    draws = _from_unconstrained(unconstrained)
    return {name: draws[:, i] for i, name in enumerate(PARAM_NAMES)}


ROUTES: dict[str, Callable[[K1Observations, np.random.Generator, int], dict[str, np.ndarray]]] = {
    "amortized": _route_amortized,
    "ukf": _route_ukf,
    "nuts": _route_nuts,
    "npe": _route_npe,
}


def risk_from_posterior(
    samples: dict[str, np.ndarray],
    horizon_days: float,
) -> float:
    """
    Posterior probability of one modeled burden doubling by an absolute study day.

    This is a synthetic model event, not a clinical recurrence probability. The
    event time is the configured seed day plus one tumor doubling time. The
    simulator does not share this event definition; see the K1 event-semantics
    proposal. Product-facing prediction is therefore disabled.
    """
    if not np.isfinite(horizon_days) or horizon_days < 0:
        raise ValueError("horizon_days must be finite and non-negative")
    doubling = np.asarray(samples["doubling_time_days"], dtype=np.float64)
    onset = np.asarray(samples["onset_day"], dtype=np.float64)
    if doubling.ndim != 1 or onset.shape != doubling.shape or len(doubling) == 0:
        raise ValueError("posterior doubling-time and onset samples must be non-empty aligned vectors")
    if not np.all(np.isfinite(doubling)) or not np.all(np.isfinite(onset)) or np.any(doubling <= 0):
        raise ValueError("posterior event-time parameters must be finite and doubling times positive")
    return float(np.mean(onset + doubling <= horizon_days))


# ---------------------------------------------------------------------------
# HybridKineticModelK1 Interface
# ---------------------------------------------------------------------------
class HybridKineticModelK1:
    """Research-only parameter inference facade; recurrence-risk prediction is disabled."""

    def __init__(
        self,
        horizon_days: float | None = None,
        seed: int | None = None,
    ) -> None:
        # Retained as an optional constructor compatibility field; recurrence risk is disabled.
        self.horizon_days = horizon_days
        self.seed = int(INFERENCE_CONFIG["default_random_seed"] if seed is None else seed)
        self.reference_schedule = SCHEDULE.copy()
        self.reference_parameters = REFERENCE_PARAMS.copy()
        self.measurement_sd = OBSERVATION_SD
        self.is_fitted = False

    def predict_parameters(
        self,
        observations: K1Observations | Sequence[K1Observations],
        *,
        route: str = "amortized",
        n_draws: int | None = None,
    ) -> list[dict[str, np.ndarray]]:
        """Return research posterior draws for observed longitudinal records."""
        if route not in ROUTES:
            raise ValueError(f"unknown K1 inference route: {route}")
        items = [observations] if isinstance(observations, K1Observations) else list(observations)
        if not all(isinstance(item, K1Observations) for item in items):
            raise TypeError("K1 inputs must be K1Observations")
        rng = np.random.default_rng(self.seed)
        return [ROUTES[route](item, rng, n_draws) for item in items]

    def predict_risk(
        self,
        X: Any,
        return_ci: bool = False,
    ) -> np.ndarray | tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Fail closed: current synthetic event does not estimate clinical recurrence."""
        del X, return_ci
        raise RuntimeError(
            "K1 recurrence-risk prediction is disabled: its synthetic one-doubling event "
            "is not the project's recurrence estimand. See PROP-K1-EVENT-SEMANTICS.md."
        )

    def identifiability_analysis(self) -> dict[str, Any]:
        """Compute a finite-difference Fisher spectrum at the registered reference point."""
        jac = np.empty((len(self.reference_schedule), len(PARAM_NAMES)), dtype=np.float64)
        for index in range(len(PARAM_NAMES)):
            step = (
                SPAN_BOUNDS[index]
                * INFERENCE_CONFIG["identifiability_finite_difference_fraction_of_half_range"]
            )
            plus, minus = self.reference_parameters.copy(), self.reference_parameters.copy()
            plus[index] += step
            minus[index] -= step
            p_plus = K1Params(**dict(zip(PARAM_NAMES, plus, strict=True)))
            p_minus = K1Params(**dict(zip(PARAM_NAMES, minus, strict=True)))
            jac[:, index] = (
                _expected_ca153(p_plus, self.reference_schedule)
                - _expected_ca153(p_minus, self.reference_schedule)
            ) / (2.0 * step) * SPAN_BOUNDS[index]
        fisher = jac.T @ jac / self.measurement_sd**2
        eigenvalues, eigenvectors = np.linalg.eigh(fisher)
        order = np.argsort(np.abs(eigenvalues))[::-1]
        eigenvalues = np.abs(eigenvalues[order])
        eigenvectors = eigenvectors[:, order]
        ratio = eigenvalues / max(float(eigenvalues[0]), np.finfo(float).tiny)
        weak = np.flatnonzero(
            ratio < INFERENCE_CONFIG["identifiability_eigenvalue_ratio_threshold"]
        )
        null_influence = np.sum(eigenvectors[:, weak] ** 2, axis=1) if len(weak) else np.zeros(len(PARAM_NAMES))
        implicated = [PARAM_NAMES[i] for i in np.argsort(null_influence)[::-1][: len(weak)]]
        return {
            "eigenvalues": eigenvalues.tolist(),
            "ratio": ratio.tolist(),
            "identifiable": [name for name in PARAM_NAMES if name not in implicated],
            "non_identifiable": implicated,
            "expected_non_identifiable_count": len(weak),
            "identifiability_status": "FINITE_DIFFERENCE_FISHER_AT_REGISTERED_SYNTHETIC_REFERENCE",
        }
