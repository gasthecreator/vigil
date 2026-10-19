# EXP-OCR-001 report (synthetic lab reports)

Script-written from `results.json`. Not clinical documents. Not a claim about real laboratories.

- Seed: `20261019` (frozen seed is `20261019`)
- N: 40 generated reports
- Tesseract available: yes

## Exact-match rates

- PDF text layer (T): 1.0
- Clean PNG (I-clean): 1.0
- JPEG quality 40: 1.0
- Rotation 2°: 0.975
- Speckle 0.5%: 0.825

## Hypotheses

- H1 (PDF ≥ 0.95): observed 1.0; met=True; kill=False
- H2 (clean image ≥ 0.8): observed 1.0; met=True; does not kill
- H3 (each noisy arm ≥ 0.5): observed {'jpeg': 1.0, 'rotate': 0.975, 'speckle': 0.825}; met=True; does not kill

Kill fired: False

## What this is not

Accuracy on real photographs, handwriting, stamps, thermal paper, or non-English reports is not measured.
A human catching an OCR error at confirmation is not measured (handover H-117).
