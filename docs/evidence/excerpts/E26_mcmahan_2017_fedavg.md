# Excerpt: Federated Averaging (McMahan et al. 2017)

**Source:** McMahan HB, Moore E, Ramage D, Hampson S, Agüera y Arcas B. "Communication-Efficient Learning of Deep Networks from Decentralized Data." *Proceedings of the 20th International Conference on Artificial Intelligence and Statistics (AISTATS)*. PMLR 54:1273-1282, 2017.  
**DOI:** none in Crossref (PMLR 54; arXiv identifier 10.48550/arXiv.1602.05629 is not a Crossref work)  
**URL:** https://arxiv.org/abs/1602.05629  
**License:** arXiv abstract (public).  

---

## Verbatim Excerpt: Abstract

> "We advocate an alternative that leaves the training data distributed on the mobile devices, and learns a shared model by aggregating locally-computed updates. We term this decentralized approach Federated Learning."

> "We present a practical method for the federated learning of deep networks based on iterative model averaging, and conduct an extensive empirical evaluation, considering five different model architectures and four datasets."

---

## Limits (not quoted)
- The paper is about mobile-device language and image models, not hospital laboratory surveillance and not breast-cancer follow-up.
- "Robust to unbalanced and non-IID data" is an empirical claim on their datasets, not a guarantee for Vigil's simulator.
- Used only to name the algorithm (FederatedAveraging / iterative model averaging) that EXP-M12-001 implements. No numeric result from this paper is copied into Vigil's study.
