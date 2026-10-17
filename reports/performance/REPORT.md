# Vigil Performance & Latency Benchmark Report

**Generated:** 2026-10-17T07:58:25.890204+00:00  
**Sample Size:** N=1,000 iterations per component (Condition P7-C)  
**Governing Requirements:** `docs/MASTER_PLAN.md` §9.5 Performance Budgets  

## Latency Summary Table

| Operation | p50 (ms) | p95 (ms) | p99 (ms) | Section 9.5 Budget (p95) | Status |
|---|---|---|---|---|---|
| `k3_inference` | 0.108 ms | 0.122 ms | 0.131 ms | < 300.0 ms | **PASS** |
| `b4_inference` | 0.554 ms | 0.604 ms | 0.648 ms | < 300.0 ms | **PASS** |
| `m3_adjudication` | 0.003 ms | 0.003 ms | 0.003 ms | < 100.0 ms | **PASS** |
| `triage_queue` | 1.845 ms | 2.162 ms | 3.274 ms | < 400.0 ms | **PASS** |
| `patient_timeline` | 9.8 ms | 38.069 ms | 81.662 ms | < 600.0 ms | **PASS** |

## Conclusion
All inference and endpoint operations strictly satisfy Section 9.5 latency budgets under full N=1,000 sampling.
