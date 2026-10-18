#!/usr/bin/env python3
"""Download METABRIC and TCGA-BRCA (PanCancer Atlas) clinical tables from the public cBioPortal API.

Writes tab-separated patient and sample files into data/external/ (git-ignored; never committed) and a MANIFEST.json
with the source URL, retrieval time and SHA-256 of every file. Network required. Terms of use of each study apply to
the user who runs this; see data/dataset_cards/.

    uv run python scripts/fetch_public_clinical.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "external"
BASE = "https://www.cbioportal.org/api"
STUDIES = {"METABRIC": "brca_metabric", "TCGA-BRCA": "brca_tcga_pan_can_atlas_2018"}


def get(url: str) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": "vigil-fetch/1", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return resp.read()


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest: dict = {"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "files": []}
    for label, study in STUDIES.items():
        info = json.loads(get(f"{BASE}/studies/{study}"))
        manifest.setdefault("studies", {})[label] = {
            "study_id": study,
            "name": info["name"],
            "allSampleCount": info["allSampleCount"],
        }
        for kind, id_key in (("PATIENT", "patientId"), ("SAMPLE", "sampleId")):
            url = f"{BASE}/studies/{study}/clinical-data?clinicalDataType={kind}&projection=SUMMARY&pageSize=10000000"
            data = json.loads(get(url))
            attrs = sorted({d["clinicalAttributeId"] for d in data})
            rows: dict[str, dict[str, str]] = defaultdict(dict)
            for d in data:
                key = d["patientId"] if kind == "PATIENT" else d["sampleId"]
                rows[key]["PATIENT_ID"] = d["patientId"]
                if kind == "SAMPLE":
                    rows[key]["SAMPLE_ID"] = d["sampleId"]
                rows[key][d["clinicalAttributeId"]] = d["value"]
            cols = ["PATIENT_ID"] + (["SAMPLE_ID"] if kind == "SAMPLE" else []) + attrs
            path = OUT / f"{label}_{kind.lower()}.tsv"
            with path.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(
                    fh,
                    fieldnames=cols,
                    delimiter="\t",
                    lineterminator="\n",
                    quoting=csv.QUOTE_NONE,
                    escapechar="\\",
                )
                w.writeheader()
                for k in sorted(rows):
                    w.writerow({c: rows[k].get(c, "") for c in cols})
            manifest["files"].append(
                {
                    "file": path.name,
                    "source_url": url,
                    "rows": len(rows),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
            print(f"{path.name}: {len(rows)} rows")
    (OUT / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
