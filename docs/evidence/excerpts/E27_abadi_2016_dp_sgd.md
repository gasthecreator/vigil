# Excerpt: Differentially private SGD (Abadi et al. 2016)

**Source:** Abadi M, Chu A, Goodfellow I, McMahan HB, Mironov I, Talwar K, Zhang L. "Deep Learning with Differential Privacy." *Proceedings of the 2016 ACM SIGSAC Conference on Computer and Communications Security (CCS '16)*. 2016:308-318.  
**DOI:** 10.1145/2976749.2978318  
**URL:** https://arxiv.org/abs/1607.00133  
**License:** arXiv abstract (public).  

---

## Verbatim Excerpt: Abstract

> "Addressing this goal, we develop new algorithmic techniques for learning and a refined analysis of privacy costs within the framework of differential privacy."

> "Our implementation and experiments demonstrate that we can train deep neural networks with non-convex objectives, under a modest privacy budget, and at a manageable cost in software complexity, training efficiency, and model quality."

---

## Limits (not quoted)
- Experiments are MNIST and CIFAR, not clinical laboratory series.
- The paper's numerical privacy-loss examples (full text) are used only as a unit-test target for Vigil's accountant, not as a clinical privacy guarantee.
- (ε, δ)-DP is a mathematical bound on a mechanism; it is not a legal determination under NDPA/GDPR, and it does not by itself prevent every attack.
- Used to name DP-SGD (clip per-example gradients, average, add Gaussian noise, account the privacy loss) as implemented in EXP-M12-001.
