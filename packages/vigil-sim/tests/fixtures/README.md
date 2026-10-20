# Historical cohort compatibility fixture

`historical_generator_cohorts.json.gz` contains seeded synthetic cohorts generated
from source commit `4772dc6dda9c28dc86503c45903c7a9e2fcf3ee2`, immediately before
the profile assumptions became required in the generator configuration. It covers
the legacy, v1, and K3 v2 profiles for G1, G2, and G3, with seed `654321`, 80
patients, and 730 days of follow-up.

The snapshot was generated on macOS arm64 with Python 3.12.15, NumPy 2.5.4,
pandas 3.0.6, and SciPy 1.18.1. The generator implementation and profiles are
available at the source commit in Git history. The compressed fixture SHA-256 is
`6ea8ee5b4edd4d56b1e9b0e0b1d0aa9f2a5af65bd2251ebf714db47b892279ff`; the
uncompressed JSON SHA-256 is
`98f8b52e56e2fc7acf3b8e5b12886e609e11ab50b37de0210e7de1a727463935`.

The test compares schema, row order, null masks, categorical values, and integer
values exactly. Floating point values use absolute tolerance `1e-6` and zero
relative tolerance to account for host math-library differences. This fixture
tests synthetic implementation compatibility only; it is not an experiment
result or evidence of simulator calibration or clinical validity.
