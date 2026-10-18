#!/usr/bin/env python3
"""Generate the SYNTHETIC messy partner dataset used to rehearse the retrospective-partner ingestion.

Everything here is invented (fixed seed). The generator does NOT import the ingestion code: it writes an extraction in
the DATA-DICTIONARY format, damages specific rows in ways real hospital extracts are damaged, and records what it did
in ``INJECTED_FAULTS.json`` (table, 1-based data row, expected rejection code). The ingestion code is then tested
against that manifest, so the injected defects and the detector do not share a definition.

Output: data/fixtures/partner_messy/{*.csv, partner_messy.xlsx, hl7/, INJECTED_FAULTS.json, README.md}
"""

from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "fixtures" / "partner_messy"
SEED = 20261018
N = 60

PCOLS = [
    "patient_id",
    "age_at_diagnosis",
    "menopausal_status",
    "vital_status",
    "days_to_last_followup",
    "index_day",
]
BCOLS = [
    "patient_id",
    "histological_type",
    "tumor_grade",
    "stage_ajcc",
    "er_status",
    "pr_status",
    "her2_status",
    "has_hypertension",
    "renal_history",
    "surgery_type",
    "chemotherapy_given",
    "endocrine_therapy",
    "radiotherapy_given",
]
LCOLS = [
    "patient_id",
    "observation_day",
    "analyte_code",
    "analyte_name",
    "value_numeric",
    "unit_ucum",
    "ref_low",
    "ref_high",
]
OCOLS = [
    "patient_id",
    "recurrence_confirmed",
    "recurrence_day",
    "site_bone",
    "site_liver",
    "site_lung",
    "site_brain",
    "site_locoregional",
    "confirmatory_modality",
    "dismissed_prior_signal",
    "restaging_imaging_done",
]

LOINC = {
    "ca_15_3": "83082-8",
    "alt": "1742-6",
    "ast": "1920-8",
    "creatinine": "2160-0",
    "wbc": "6690-2",
}


def build(rng: random.Random):
    pts, base, labs, outs = [], [], [], []
    for i in range(N):
        pid = f"PTR-{i + 1:03d}"
        follow = rng.randint(400, 3000)
        pts.append(
            {
                "patient_id": pid,
                "age_at_diagnosis": rng.randint(28, 78),
                "menopausal_status": rng.choice(["PRE", "PERI", "POST", "UNKNOWN"]),
                "vital_status": rng.choice(
                    ["ALIVE", "ALIVE", "ALIVE", "DEAD_DISEASE", "DEAD_OTHER", "LOST_TO_FOLLOWUP"]
                ),
                "days_to_last_followup": follow,
                "index_day": rng.randint(60, 300),
            }
        )
        base.append(
            {
                "patient_id": pid,
                "histological_type": rng.choice(["IDC", "IDC", "ILC", "OTHER"]),
                "tumor_grade": rng.randint(1, 3),
                "stage_ajcc": rng.choice(["I", "IIA", "IIB", "IIIA", "IIIB"]),
                "er_status": rng.choice(["POSITIVE", "NEGATIVE", "UNKNOWN"]),
                "pr_status": rng.choice(["POSITIVE", "NEGATIVE", "UNKNOWN"]),
                "her2_status": rng.choice(["POSITIVE", "NEGATIVE", "EQUIVOCAL", "UNKNOWN"]),
                "has_hypertension": rng.choice(["true", "false"]),
                "renal_history": rng.choice(["true", "false"]),
                "surgery_type": rng.choice(["MRM", "BCS", "TOTAL_MASTECTOMY"]),
                "chemotherapy_given": rng.choice(["true", "false"]),
                "endocrine_therapy": rng.choice(["true", "false"]),
                "radiotherapy_given": rng.choice(["true", "false"]),
            }
        )
        days = sorted(rng.sample(range(0, min(follow, 1500)), 8))
        umol = i % 3 == 0
        for d in days:
            for a in LOINC:
                if a == "ca_15_3":
                    v, u = round(rng.lognormvariate(3.0, 0.25), 1), rng.choice(["[iU]/mL", "U/mL"])
                elif a in ("alt", "ast"):
                    v, u = round(rng.lognormvariate(3.2, 0.25), 1), "U/L"
                elif a == "creatinine":
                    mgdl = round(rng.uniform(0.6, 1.1), 2)
                    v, u = (round(mgdl * 88.4, 1), "umol/L") if umol else (mgdl, "mg/dL")
                else:
                    v, u = round(rng.uniform(4.0, 9.0), 1), rng.choice(["10*3/uL", "10*9/L"])
                labs.append(
                    {
                        "patient_id": pid,
                        "observation_day": d,
                        "analyte_code": LOINC[a],
                        "analyte_name": a,
                        "value_numeric": v,
                        "unit_ucum": u,
                        "ref_low": "",
                        "ref_high": "",
                    }
                )
        rec = rng.random() < 0.3
        rday = rng.randint(200, min(follow, 1400)) if rec else ""
        outs.append(
            {
                "patient_id": pid,
                "recurrence_confirmed": "true" if rec else "false",
                "recurrence_day": rday,
                "site_bone": "true" if rec and rng.random() < 0.5 else "false",
                "site_liver": "false",
                "site_lung": "false",
                "site_brain": "false",
                "site_locoregional": "false",
                "confirmatory_modality": rng.choice(["CT_SCAN", "BIOPSY", "BONE_SCAN"])
                if rec
                else "",
                "dismissed_prior_signal": "false",
                "restaging_imaging_done": "true" if rec or rng.random() < 0.6 else "false",
            }
        )
    return pts, base, labs, outs


def main() -> int:
    rng = random.Random(SEED)
    pts, base, labs, outs = build(rng)
    faults: list[dict] = []
    flagged: list[dict] = []
    dropped_dups = 0

    def fault(table: str, row: int, code: str, field: str = "") -> None:
        faults.append({"table": table, "row": row, "code": code, "field": field})

    def children_rejected(pid: str) -> None:
        for r, row in enumerate(base, 1):
            if row["patient_id"] == pid:
                fault("baseline_profile", r, "PARENT_REJECTED", "patient_id")
        for r, row in enumerate(outs, 1):
            if row["patient_id"] == pid:
                fault("clinical_outcomes", r, "PARENT_REJECTED", "patient_id")
        for r, row in enumerate(labs, 1):
            if row["patient_id"] == pid:
                fault("lab_observations", r, "PARENT_REJECTED", "patient_id")

    # ---- patients (indices chosen so no two faults share a patient)
    pts[2]["age_at_diagnosis"] = ""
    fault("patients", 3, "MISSING_REQUIRED", "age_at_diagnosis")
    children_rejected(pts[2]["patient_id"])
    pts[5]["age_at_diagnosis"] = 17
    fault("patients", 6, "OUT_OF_RANGE", "age_at_diagnosis")
    children_rejected(pts[5]["patient_id"])
    pts[8]["vital_status"] = "Mrs Okafor"
    fault("patients", 9, "BAD_ENUM", "vital_status")
    children_rejected(pts[8]["patient_id"])
    pts[14]["days_to_last_followup"] = "ten"
    fault("patients", 15, "BAD_TYPE", "days_to_last_followup")
    children_rejected(pts[14]["patient_id"])
    pts[17]["index_day"] = int(pts[17]["days_to_last_followup"]) + 50
    fault("patients", 18, "INCONSISTENT", "index_day")
    children_rejected(pts[17]["patient_id"])
    dup = dict(pts[11])
    dup["age_at_diagnosis"] = int(dup["age_at_diagnosis"]) + 1
    pts.append(dup)
    fault("patients", 12, "CONFLICTING_DUPLICATE", "patient_id")
    fault("patients", len(pts), "CONFLICTING_DUPLICATE", "patient_id")
    children_rejected(pts[11]["patient_id"])

    # ---- baseline
    base[20]["stage_ajcc"] = "IV"
    fault("baseline_profile", 21, "BAD_ENUM", "stage_ajcc")
    base[24]["tumor_grade"] = 4
    fault("baseline_profile", 25, "OUT_OF_RANGE", "tumor_grade")
    orphan = dict(base[22])
    orphan["patient_id"] = "PTR-999"
    base.append(orphan)
    fault("baseline_profile", len(base), "ORPHAN_FK", "patient_id")
    base.append(dict(base[26]))
    dropped_dups += 1  # exact duplicate: dropped, not rejected

    # ---- laboratory (patients 30+ so no cascade from the patient faults)
    def lab_rows_of(idx: int):
        pid = f"PTR-{idx + 1:03d}"
        return [(n, r) for n, r in enumerate(labs, 1) if r["patient_id"] == pid]

    rows30 = lab_rows_of(30)
    n, r = rows30[0]
    r["analyte_code"] = "99999-9"
    fault("lab_observations", n, "UNKNOWN_ANALYTE", "analyte_code")
    n, r = rows30[6]
    r["unit_ucum"] = "furlongs"
    fault("lab_observations", n, "UNKNOWN_UNIT", "unit_ucum")
    rows31 = lab_rows_of(31)
    n, r = rows31[0]
    r["value_numeric"] = -3
    fault("lab_observations", n, "OUT_OF_RANGE", "value_numeric")
    n, r = rows31[5]
    r["observation_day"] = -5
    fault("lab_observations", n, "OUT_OF_RANGE", "observation_day")
    n, r = rows31[10]
    r["observation_day"] = "ten"
    fault("lab_observations", n, "BAD_TYPE", "observation_day")
    rows32 = lab_rows_of(32)
    n, r = next((n, r) for n, r in rows32 if r["analyte_name"] == "alt")
    r["unit_ucum"] = "mg/dL"
    fault("lab_observations", n, "INCOMPATIBLE_UNIT", "unit_ucum")
    n, r = next((n, r) for n, r in rows32 if r["analyte_name"] == "ast")
    r["analyte_name"] = "alt"
    fault("lab_observations", n, "NAME_CODE_MISMATCH", "analyte_name")
    rows33 = lab_rows_of(33)
    n0, r0 = rows33[3]
    twin = dict(r0)
    twin["value_numeric"] = round(float(r0["value_numeric"]) * 1.5, 1)
    labs.append(twin)
    fault(
        "lab_observations", n0, "CONFLICTING_DUPLICATE", "patient_id,observation_day,analyte_code"
    )
    fault(
        "lab_observations",
        len(labs),
        "CONFLICTING_DUPLICATE",
        "patient_id,observation_day,analyte_code",
    )
    n1, r1 = rows33[9]
    labs.append(dict(r1))
    dropped_dups += 1
    rows34 = lab_rows_of(34)
    n, r = next((n, r) for n, r in rows34 if r["analyte_name"] == "alt")
    r["value_numeric"] = 90000
    flagged.append({"row": n, "analyte": "alt"})

    # ---- outcomes
    rec = [i for i, o in enumerate(outs) if o["recurrence_confirmed"] == "true" and i >= 36]
    non = [i for i, o in enumerate(outs) if o["recurrence_confirmed"] == "false" and i >= 36]
    i = rec[0]
    outs[i]["recurrence_day"] = ""
    fault("clinical_outcomes", i + 1, "MISSING_REQUIRED", "recurrence_day")
    i = non[0]
    outs[i]["recurrence_day"] = 300
    fault("clinical_outcomes", i + 1, "INCONSISTENT", "recurrence_confirmed")
    i = rec[1]
    outs[i]["recurrence_day"] = int(pts[i]["days_to_last_followup"]) + 100
    fault("clinical_outcomes", i + 1, "INCONSISTENT", "recurrence_day")
    orphan_o = dict(outs[rec[2]])
    orphan_o["patient_id"] = "PTR-998"
    outs.append(orphan_o)
    fault("clinical_outcomes", len(outs), "ORPHAN_FK", "patient_id")

    # ---- messy presentation of otherwise valid cells (normalised, never rejected)
    normalised = 0
    for k, row in enumerate(pts):
        if k % 7 == 0 and row["menopausal_status"] in ("PRE", "PERI", "POST"):
            row["menopausal_status"] = " " + row["menopausal_status"].lower() + " "
            normalised += 1
    for k, row in enumerate(base):
        if k % 5 == 0 and row["has_hypertension"] in ("true", "false"):
            row["has_hypertension"] = "Yes" if row["has_hypertension"] == "true" else "N"
            normalised += 1
        if k % 9 == 0 and row["er_status"] == "POSITIVE":
            row["er_status"] = "Positive"
            normalised += 1

    OUT.mkdir(parents=True, exist_ok=True)
    tables = {
        "patients": (PCOLS, pts),
        "baseline_profile": (BCOLS, base),
        "lab_observations": (LCOLS, labs),
        "clinical_outcomes": (OCOLS, outs),
    }
    for name, (cols, rows) in tables.items():
        with (OUT / f"{name}.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, lineterminator="\n")
            w.writeheader()
            w.writerows(rows)
    from openpyxl import Workbook

    def cell(v):
        if isinstance(v, str):
            for cast in (int, float):
                try:
                    return cast(v) if v.strip() == v else v
                except ValueError:
                    pass
        return v

    wb = Workbook()
    wb.remove(wb.active)
    for name, (cols, rows) in tables.items():
        ws = wb.create_sheet(name)
        ws.append(cols)
        for row in rows:
            ws.append([cell(row[c]) if row[c] != "" else None for c in cols])
    wb.save(OUT / "partner_messy.xlsx")

    hl7_dir = OUT / "hl7"
    hl7_dir.mkdir(exist_ok=True)
    H = "MSH|^~\\&|LIS|SYNTHETIC-SITE|VIGIL|CLINIC|{ts}||ORU^R01|{cid}|P|2.5\rPID|1||{lid}^^^SITE^MR||TESTSURNAME^TESTFIRST\rOBR|1|||LAB|||{ts}\r"
    msgs = [
        H.format(ts="20250310093000", cid="M1", lid="LOCAL-1")
        + "OBX|1|NM|83082-8^CA 15-3^LN||41.0|U/mL||N|||F|||20250310093000|LAB1\r"
        + "OBX|2|NM|1742-6^ALT^LN||32|U/L||N|||F|||20250310093000|LAB1\r",
        H.format(ts="20250410093000", cid="M2", lid="LOCAL-1")
        + "OBX|1|NM|99999-9^MYSTERY^LN||5|U/L||N|||F|||20250410093000|LAB1\r"
        + "OBX|2|NM|1920-8^AST^LN||pending|U/L||N|||F|||20250410093000|LAB1\r"
        + "OBX|3|NM|1920-8^AST^LN||28|||N|||F|||20250410093000|LAB1\r"
        + "OBX|4|NM|1920-8^AST^LN||29|U/L||N|||F|||20250410093000|LAB1\r",
        H.format(ts="20240101093000", cid="M3", lid="LOCAL-1")
        + "OBX|1|NM|1742-6^ALT^LN||30|U/L||N|||F|||20240101093000|LAB1\r",
        H.format(ts="20250310093000", cid="M4", lid="LOCAL-UNKNOWN")
        + "OBX|1|NM|1742-6^ALT^LN||30|U/L||N|||F|||20250310093000|LAB1\r",
    ]
    (hl7_dir / "oru_messages.hl7").write_text(
        "\n\n".join(m.replace("\r", "\n").rstrip("\n") for m in msgs) + "\n", encoding="utf-8"
    )
    (hl7_dir / "index_dates.json").write_text(
        json.dumps({"LOCAL-1": "2025-01-15"}, indent=2) + "\n", encoding="utf-8"
    )
    hl7_expected = {
        "accepted_rows": 3,  # M1 x2, M2 OBX4
        "rejections": [
            {"message": 2, "obx": 1, "code": "UNKNOWN_ANALYTE"},
            {"message": 2, "obx": 2, "code": "NON_NUMERIC_VALUE"},
            {"message": 2, "obx": 3, "code": "MISSING_UNIT"},
            {"message": 3, "obx": 1, "code": "BEFORE_DIAGNOSIS"},
            {"message": 4, "obx": 1, "code": "NO_INDEX_DATE"},
        ],
    }
    manifest = {
        "synthetic": True,
        "seed": SEED,
        "generator": "scripts/make_messy_partner_dataset.py",
        "rows": {k: len(v[1]) for k, v in tables.items()},
        "expected_rejections": sorted(
            faults, key=lambda f: (f["table"], f["row"], f["code"], f["field"])
        ),
        "expected_flagged_labs": flagged,
        "expected_duplicates_dropped": dropped_dups,
        "expected_normalised_cells_at_least": normalised,
        "hl7": hl7_expected,
    }
    (OUT / "INJECTED_FAULTS.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (OUT / "README.md").write_text(
        "# SYNTHETIC messy partner dataset\n\nInvented data, fixed seed, written by `scripts/make_messy_partner_dataset.py`. "
        "Nothing here describes a real patient. `INJECTED_FAULTS.json` lists every defect that was injected and the rejection code it must produce.\n"
        "The `hl7/` files contain a made-up patient name on purpose: they rehearse the on-site converter, which is the only place a name may exist.\n",
        encoding="utf-8",
    )
    (OUT / "SYNTHETIC").write_text(
        "All data in this folder are invented (scripts/make_messy_partner_dataset.py).\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT} ({len(faults)} expected rejections)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
