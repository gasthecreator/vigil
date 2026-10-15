"""
scripts/generate_synthetic_cohorts.py

Generates versioned cross-generator synthetic cohort datasets for Vigil:
- cohort_g1_smooth (Continuous secretion kinetics)
- cohort_g2_burst (Step-change & necrotic bursts)
- cohort_g3_noise (Heavy-tailed noise & lab offsets)

Saves both patient registries, observations, and latent ground truth states.
"""

import hashlib
import json
from pathlib import Path

from vigil_sim.generators import GeneratorType, get_generator

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"


def generate_and_save_cohorts(num_patients: int = 500, seed: int = 42):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}

    for gen_type in [GeneratorType.G1_SMOOTH, GeneratorType.G2_BURST, GeneratorType.G3_NOISE]:
        name = gen_type.value
        print(f"Generating cohort for {name} ({num_patients} patients)...")
        gen = get_generator(gen_type, seed=seed)
        cohort = gen.generate_cohort(num_patients=num_patients, duration_days=730.0)

        obs_df = cohort.to_observations_dataframe()
        pts_df = cohort.to_patients_dataframe()
        latent_df = cohort.to_latent_states_dataframe()

        obs_path = DATA_DIR / f"{name}_observations.csv.gz"
        pts_path = DATA_DIR / f"{name}_patients.csv.gz"
        latent_path = DATA_DIR / f"{name}_latent_states.csv.gz"

        obs_df.to_csv(obs_path, index=False, compression="gzip")
        pts_df.to_csv(pts_path, index=False, compression="gzip")
        latent_df.to_csv(latent_path, index=False, compression="gzip")

        # Compute checksum
        hasher = hashlib.sha256()
        hasher.update(obs_path.read_bytes())
        obs_hash = hasher.hexdigest()

        manifest[name] = {
            "num_patients": len(pts_df),
            "num_observations": len(obs_df),
            "sha256_observations": obs_hash,
            "observations_file": str(obs_path.name),
            "patients_file": str(pts_path.name),
            "latent_states_file": str(latent_path.name),
            "generator_type": gen_type.value,
            "seed": seed,
        }

    manifest_path = DATA_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"✅ Generated and versioned all 3 synthetic cohorts in {DATA_DIR}")
    print(f"📄 Manifest written to {manifest_path}")


if __name__ == "__main__":
    generate_and_save_cohorts()
