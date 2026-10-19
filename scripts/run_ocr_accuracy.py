#!/usr/bin/env python3
"""EXP-OCR-001 frozen accuracy run. Writes results.json and REPORT.md. Synthetic reports only.

Usage:
  uv run python scripts/run_ocr_accuracy.py            # frozen seed, PDF + images
  uv run python scripts/run_ocr_accuracy.py --pdf-only # PDF text-layer arm (CI)
  uv run python scripts/run_ocr_accuracy.py --dev      # development seed 7; does not overwrite frozen files
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from vigil_api.ocr import (  # noqa: E402
    extract_from_bytes,
    jpeg_noise,
    render_synthetic_report,
    rotate_noise,
    speckle_noise,
    suggestion_triple,
    tesseract_available,
)

EXP = ROOT / "experiments" / "EXP-OCR-001"
FROZEN_SEED = 20261019
DEV_SEED = 7
N = 40
H1_MIN = 0.95
H2_MIN = 0.80
H3_MIN = 0.50


def _reports(seed: int) -> List[Dict[str, Any]]:
    import numpy as np

    rng = np.random.default_rng(seed)
    rows = []
    for i in range(N):
        analyte = "ca_15_3" if i % 2 == 0 else "cea"
        value = round(float(rng.uniform(8.0, 80.0)), 1)
        unit = "U/mL" if analyte == "ca_15_3" else "ng/mL"
        collected = (date(2026, 1, 1) + timedelta(days=i)).isoformat()
        report = render_synthetic_report(
            analyte_code=analyte, value=value, unit=unit, collected_on=collected
        )
        truth = (analyte, report.value, unit)
        rows.append({"i": i, "truth": truth, "report": report})
    return rows


def _score(extracted, truth: Tuple[str, float, str]) -> Dict[str, Any]:
    pred = suggestion_triple(extracted.suggestion)
    return {
        "engine": extracted.engine,
        "predicted": list(pred) if pred else None,
        "truth": list(truth),
        "exact": pred == truth,
    }


def evaluate(seed: int, images: bool) -> Dict[str, Any]:
    tess = tesseract_available()
    rows = _reports(seed)
    pdf_scores: List[Dict[str, Any]] = []
    arms: Dict[str, List[Dict[str, Any]]] = {
        "pdf": pdf_scores,
        "clean": [],
        "jpeg": [],
        "rotate": [],
        "speckle": [],
    }
    for row in rows:
        report = row["report"]
        truth = row["truth"]
        pdf_scores.append(_score(extract_from_bytes(report.pdf_bytes, "application/pdf"), truth))
        if not images:
            continue
        if not tess:
            miss = {
                "engine": "tesseract_missing",
                "predicted": None,
                "truth": list(truth),
                "exact": False,
            }
            for key in ("clean", "jpeg", "rotate", "speckle"):
                arms[key].append(dict(miss))
            continue
        arms["clean"].append(_score(extract_from_bytes(report.png_bytes, "image/png"), truth))
        arms["jpeg"].append(
            _score(extract_from_bytes(jpeg_noise(report.png_bytes, 40), "image/jpeg"), truth)
        )
        arms["rotate"].append(
            _score(extract_from_bytes(rotate_noise(report.png_bytes, 2.0), "image/png"), truth)
        )
        arms["speckle"].append(
            _score(
                extract_from_bytes(speckle_noise(report.png_bytes, 0.005, seed + row["i"]), "image/png"),
                truth,
            )
        )

    def rate(scores: List[Dict[str, Any]]) -> Optional[float]:
        if not scores:
            return None
        return round(sum(1 for s in scores if s["exact"]) / len(scores), 4)

    pdf_rate = rate(pdf_scores)
    clean_rate = rate(arms["clean"]) if images else None
    jpeg_rate = rate(arms["jpeg"]) if images else None
    rotate_rate = rate(arms["rotate"]) if images else None
    speckle_rate = rate(arms["speckle"]) if images else None
    h1 = bool(pdf_rate is not None and pdf_rate >= H1_MIN)
    h2 = bool(images and tess and clean_rate is not None and clean_rate >= H2_MIN)
    h3 = bool(
        images
        and tess
        and jpeg_rate is not None
        and rotate_rate is not None
        and speckle_rate is not None
        and jpeg_rate >= H3_MIN
        and rotate_rate >= H3_MIN
        and speckle_rate >= H3_MIN
    )
    return {
        "study": "EXP-OCR-001",
        "data": "synthetic_lab_reports",
        "seed": seed,
        "n": N,
        "tesseract_available": tess,
        "images_evaluated": bool(images and tess),
        "rates": {
            "pdf": pdf_rate,
            "clean_png": clean_rate,
            "jpeg": jpeg_rate,
            "rotate": rotate_rate,
            "speckle": speckle_rate,
        },
        "hypotheses": {
            "H1_pdf_exact_ge_0.95": {"min": H1_MIN, "observed": pdf_rate, "met": h1, "kill": not h1},
            "H2_clean_image_ge_0.80": {
                "min": H2_MIN,
                "observed": clean_rate,
                "met": h2,
                "kill": False,
                "note": "H2 does not kill the importer; confirm gate still holds.",
            },
            "H3_noisy_image_ge_0.50": {
                "min": H3_MIN,
                "observed": {"jpeg": jpeg_rate, "rotate": rotate_rate, "speckle": speckle_rate},
                "met": h3,
                "kill": False,
                "note": "H3 does not kill the importer; confirm gate still holds.",
            },
        },
        "kill_fired": not h1,
        "records": {k: v for k, v in arms.items() if v},
    }


def render_report(result: Dict[str, Any]) -> str:
    rates = result["rates"]
    h = result["hypotheses"]
    tess = "yes" if result["tesseract_available"] else "no (image arm recorded as engine_missing)"
    lines = [
        "# EXP-OCR-001 report (synthetic lab reports)",
        "",
        "Script-written from `results.json`. Not clinical documents. Not a claim about real laboratories.",
        "",
        f"- Seed: `{result['seed']}` (frozen seed is `{FROZEN_SEED}`)",
        f"- N: {result['n']} generated reports",
        f"- Tesseract available: {tess}",
        "",
        "## Exact-match rates",
        "",
        f"- PDF text layer (T): {rates['pdf']}",
        f"- Clean PNG (I-clean): {rates['clean_png']}",
        f"- JPEG quality 40: {rates['jpeg']}",
        f"- Rotation 2°: {rates['rotate']}",
        f"- Speckle 0.5%: {rates['speckle']}",
        "",
        "## Hypotheses",
        "",
        f"- H1 (PDF ≥ {H1_MIN}): observed {h['H1_pdf_exact_ge_0.95']['observed']}; "
        f"met={h['H1_pdf_exact_ge_0.95']['met']}; kill={h['H1_pdf_exact_ge_0.95']['kill']}",
        f"- H2 (clean image ≥ {H2_MIN}): observed {h['H2_clean_image_ge_0.80']['observed']}; "
        f"met={h['H2_clean_image_ge_0.80']['met']}; does not kill",
        f"- H3 (each noisy arm ≥ {H3_MIN}): observed {h['H3_noisy_image_ge_0.50']['observed']}; "
        f"met={h['H3_noisy_image_ge_0.50']['met']}; does not kill",
        "",
        f"Kill fired: {result['kill_fired']}",
        "",
        "## What this is not",
        "",
        "Accuracy on real photographs, handwriting, stamps, thermal paper, or non-English reports is not measured.",
        "A human catching an OCR error at confirmation is not measured (handover H-117).",
        "",
    ]
    return "\n".join(lines)


def render_conclusion(result: Dict[str, Any]) -> str:
    h1 = result["hypotheses"]["H1_pdf_exact_ge_0.95"]
    h2 = result["hypotheses"]["H2_clean_image_ge_0.80"]
    h3 = result["hypotheses"]["H3_noisy_image_ge_0.50"]
    verdict = (
        "The PDF text-layer extractor met H1 on these generated documents."
        if h1["met"]
        else "The PDF text-layer extractor failed H1; that is a kill of the PDF arm."
    )
    image_note = (
        "The image arm met H2/H3 on this synthetic print-style set."
        if h2["met"] and h3["met"]
        else "The image arm did not meet H2 and/or H3 (or Tesseract was missing). Suggestions from photos are hints, not a record."
    )
    return "\n".join(
        [
            "# EXP-OCR-001 conclusion",
            "",
            "Synthetic generated reports only. Not a clinical validation.",
            "",
            f"{verdict} {image_note} The confirm gate is independent of these rates: an unconfirmed draft is not an observation.",
            "",
            f"- H1 met: {h1['met']} (observed {h1['observed']})",
            f"- H2 met: {h2['met']} (observed {h2['observed']})",
            f"- H3 met: {h3['met']} (observed {h3['observed']})",
            f"- Kill fired: {result['kill_fired']}",
            "",
            "## What would change the decision",
            "",
            "A consented set of real laboratory photographs and PDFs, scored the same way, with a native-speaker / clinician review of the confirm UI (H-117).",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--pdf-only", action="store_true")
    args = parser.parse_args()
    seed = DEV_SEED if args.dev else FROZEN_SEED
    images = not args.pdf_only
    result = evaluate(seed, images=images)
    if args.dev:
        out = EXP / "dev_results.json"
        out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {out}")
        return 0
    if args.pdf_only:
        print(json.dumps({"rates": result["rates"], "hypotheses": result["hypotheses"]}, indent=2))
        return 0
    EXP.mkdir(parents=True, exist_ok=True)
    # Drop bulky per-record predicted text for the committed file; keep exact flags.
    slim = dict(result)
    slim["records"] = {
        arm: [{"exact": r["exact"], "engine": r["engine"], "predicted": r["predicted"], "truth": r["truth"]}
              for r in rows]
        for arm, rows in result.get("records", {}).items()
    }
    (EXP / "results.json").write_text(json.dumps(slim, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (EXP / "REPORT.md").write_text(render_report(slim), encoding="utf-8")
    (EXP / "CONCLUSION.md").write_text(render_conclusion(slim), encoding="utf-8")
    print(f"wrote {EXP / 'results.json'}")
    print(json.dumps(slim["rates"], indent=2))
    print("kill_fired", slim["kill_fired"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
