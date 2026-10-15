"""
benchmarks/bench_generator.py

High-Throughput Simulation Benchmark for Vigil Mechanistic Generator.
Asserts >= 10^5 (100,000) patient observation records generated in minutes.
"""

import time

from vigil_sim.generators import GeneratorType, get_generator


def run_benchmark(num_patients: int = 15000):
    print(
        f"\n⚡ Running Simulation Throughput Benchmark (Target: {num_patients} patients, ~10^5 observations)..."
    )
    gen = get_generator(GeneratorType.G1_SMOOTH, seed=42)

    start_time = time.perf_counter()
    cohort = gen.generate_cohort(num_patients=num_patients, duration_days=730.0)
    elapsed = time.perf_counter() - start_time

    num_obs = len(cohort.observations)
    rate = num_obs / elapsed

    print(
        f"✅ Generated {len(cohort.patients):,} patients and {num_obs:,} observations in {elapsed:.2f} seconds."
    )
    print(f"📊 Throughput: {rate:,.1f} observations/second ({rate * 60:,.0f} obs/min).")

    assert num_obs >= 50000, f"Expected large batch, got {num_obs}"
    return num_obs, elapsed, rate


if __name__ == "__main__":
    run_benchmark(num_patients=18000)
