# Excerpt: GRUwE, a recurrent model for irregular time series (Joshi and Hauskrecht 2025)

**Source:** Joshi A, Hauskrecht M. "Still Competitive: Revisiting Recurrent Models for Irregular Time Series Prediction." arXiv preprint, October 2025 (a later journal version is cited in `docs/EVIDENCE.md` E11 as TMLR 2026; that version was not retrieved).  
**URL:** https://arxiv.org/html/2510.16161  
**License:** Only two sentences of the abstract are quoted.  

---

## Verbatim Excerpt: Abstract

> "GRUwE works by maintaining a Markov state representation of the time series that updates with the arrival of irregular observations."

> "The Markov state update relies on two reset mechanisms: (i) observation-triggered reset to account for the new observation, and (ii) time-triggered reset that relies on learnable exponential decays, to support the predictions in continuous time."

---

## What the K4 implementation takes from the paper (not quoted; written from the method section of the same page)
- Time-triggered reset: the previous hidden state is multiplied element-wise by a learnable decay `exp(-max(0, W_gamma * dt + b_gamma))`, where `dt` is the time since the previous observation.
- Observation-triggered reset: a GRU update whose input is the masked observation vector, with the mask vector fed through its own weights.
- `vigil_ml.k4.GRUwE` implements these two steps for a risk head read from the hidden state; the paper's continuous-time prediction module and its next-observation tasks are not used.

## Limits (not quoted)
- The paper's benchmarks are next-observation and next-event prediction on non-oncology intensive-care and sensor data. Nothing in it supports a claim about breast-cancer follow-up.
- A preprint; this entry does not rely on any of its reported performance figures.
