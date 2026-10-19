#!/usr/bin/env python3
"""Write a few generated lab-report PNG/PDF files for inspection. Synthetic. Not the frozen study."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from vigil_api.ocr import jpeg_noise, render_synthetic_report, rotate_noise, speckle_noise


def main() -> int:
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "experiments" / "EXP-OCR-001" / "_samples"
    out.mkdir(parents=True, exist_ok=True)
    report = render_synthetic_report(
        analyte_code="ca_15_3", value=24.6, unit="U/mL", collected_on="2026-03-15"
    )
    (out / "ca15_3_clean.png").write_bytes(report.png_bytes)
    (out / "ca15_3.pdf").write_bytes(report.pdf_bytes)
    (out / "ca15_3_jpeg.jpg").write_bytes(jpeg_noise(report.png_bytes, 40))
    (out / "ca15_3_rotate.png").write_bytes(rotate_noise(report.png_bytes, 2.0))
    (out / "ca15_3_speckle.png").write_bytes(speckle_noise(report.png_bytes, 0.005, 1))
    (out / "plaintext.txt").write_text(report.plaintext, encoding="utf-8")
    print(f"wrote samples under {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
