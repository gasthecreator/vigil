"""cBioPortal-format loaders for METABRIC and TCGA-BRCA, on INVENTED rows written in the real file layout."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
from contracts.loaders.cbioportal import ROW_CODES, load_study

META = "#Patient Identifier\tAge\n#Identifier\tAge at diagnosis\n#STRING\tNUMBER\n#1\t1\n"


def _write(path: Path, header: list[str], rows: list[list[str]], meta: bool = True) -> Path:
    body = "\t".join(header) + "\n" + "\n".join("\t".join(r) for r in rows) + "\n"
    path.write_text((META if meta else "") + body, encoding="utf-8")
    return path


MB_PAT = [
    "PATIENT_ID",
    "AGE_AT_DIAGNOSIS",
    "SEX",
    "CLAUDIN_SUBTYPE",
    "OS_MONTHS",
    "OS_STATUS",
    "INFERRED_MENOPAUSAL_STATE",
    "NPI",
    "RFS_MONTHS",
    "RFS_STATUS",
]
MB_SMP = [
    "PATIENT_ID",
    "SAMPLE_ID",
    "ER_STATUS",
    "PR_STATUS",
    "HER2_STATUS",
    "GRADE",
    "TUMOR_STAGE",
]


def _metabric(tmp_path):
    pat = _write(
        tmp_path / "p.txt",
        MB_PAT,
        [
            [
                "MB-1",
                "48.2",
                "Female",
                "LumA",
                "140.5",
                "0:LIVING",
                "Post",
                "4.04",
                "140.5",
                "0:Not Recurred",
            ],  # fine
            [
                "MB-2",
                "56.7",
                "Female",
                "Basal",
                "42.1",
                "1:DECEASED",
                "Pre",
                "5.2",
                "31.4",
                "1:Recurred",
            ],  # fine
            ["MB-3", "", "Female", "LumB", "10", "0:LIVING", "Post", "", "", ""],  # missing age
            ["MB-4", "forty", "Female", "LumB", "10", "0:LIVING", "Post", "", "", ""],  # bad type
            [
                "MB-5",
                "12",
                "Female",
                "LumB",
                "10",
                "0:LIVING",
                "Post",
                "",
                "",
                "",
            ],  # age out of range
            [
                "MB-6",
                "50",
                "Female",
                "LumB",
                "-3",
                "0:LIVING",
                "Post",
                "",
                "",
                "",
            ],  # negative months
            ["MB-7", "50", "Female", "LumB", "30", "ALIVE?", "Post", "", "", ""],  # bad status
            ["MB-1", "49", "Female", "LumA", "20", "0:LIVING", "Post", "", "", ""],  # duplicate id
            [
                "MB-8",
                "61",
                "Female",
                "Her2",
                "88",
                "1:DECEASED",
                "Post",
                "3.1",
                "NA",
                "NA",
            ],  # fine; relapse unknown
            [
                "MB-9",
                "61",
                "Female",
                "Her2",
                "88",
                "1:DECEASED",
                "Post",
                "3.1",
                "5",
                "maybe",
            ],  # bad relapse status
            [
                "MB-10",
                "70",
                "Female",
                "Her2",
                "88",
                "1:DECEASED",
                "Post",
                "3.1",
                "5",
                "0:Not Recurred",
            ],  # no sample row
        ],
    )
    smp = _write(
        tmp_path / "s.txt",
        MB_SMP,
        [[f"MB-{i}", f"MB-{i}-S", "Positive", "Negative", "NA", "2", "2"] for i in range(1, 10)],
    )
    return pat, smp


def test_metabric_rows_are_loaded_or_rejected_with_the_expected_code(tmp_path):
    pat, smp = _metabric(tmp_path)
    df, rep = load_study("METABRIC", pat, smp)
    assert list(df["patient_id"]) == ["MB-1", "MB-2", "MB-8"]
    got = sorted((r["row"], r["code"], r["field"]) for r in rep["rejections"])
    assert got == sorted(
        [
            (3, "MISSING_REQUIRED", "age"),
            (4, "BAD_TYPE", "age"),
            (5, "OUT_OF_RANGE", "age"),
            (6, "OUT_OF_RANGE", "os_months"),
            (7, "BAD_ENUM", "os_status"),
            (8, "DUPLICATE_PATIENT", "PATIENT_ID"),
            (10, "BAD_ENUM", "relapse_status"),
            (11, "NO_SAMPLE_ROW", "sample"),
        ]
    )
    assert (
        rep["patients_in_file"] == 11 and rep["patients_loaded"] == 3 and rep["rows_rejected"] == 8
    )
    assert set(rep["rejection_codes"]) <= set(ROW_CODES)


def test_values_are_mapped_not_guessed(tmp_path):
    pat, smp = _metabric(tmp_path)
    df, _ = load_study("METABRIC", pat, smp)
    r = df.set_index("patient_id")
    assert r.loc["MB-1", "os_event"] == 0 and r.loc["MB-2", "os_event"] == 1
    assert r.loc["MB-2", "relapse_event"] == 1 and r.loc["MB-1", "relapse_event"] == 0
    assert (
        r.loc["MB-8", "relapse_event"] is None
        or r.loc["MB-8", "relapse_event"] != r.loc["MB-8", "relapse_event"]
    )  # unknown stays unknown
    assert (
        r.loc["MB-1", "er"] == "POSITIVE"
        and r.loc["MB-1", "pr"] == "NEGATIVE"
        and r.loc["MB-1", "her2"] is None
    )
    assert r.loc["MB-1", "stage"] == "II" and r.loc["MB-1", "npi"] == pytest.approx(4.04)


def test_report_never_contains_a_cell_value(tmp_path):
    pat, smp = _metabric(tmp_path)
    _, rep = load_study("METABRIC", pat, smp)
    blob = json.dumps(rep)
    for leaked in ("forty", "ALIVE?", "maybe"):
        assert leaked not in blob


def test_missing_required_attribute_column_is_an_error_not_a_silent_empty_load(tmp_path):
    pat = _write(tmp_path / "p.txt", ["PATIENT_ID", "AGE_AT_DIAGNOSIS"], [["MB-1", "50"]])
    with pytest.raises(ValueError, match="lacks required attribute"):
        load_study("METABRIC", pat)


def test_tcga_pancancer_layout(tmp_path):
    header = [
        "PATIENT_ID",
        "AGE",
        "SEX",
        "SUBTYPE",
        "OS_MONTHS",
        "OS_STATUS",
        "AJCC_PATHOLOGIC_TUMOR_STAGE",
        "DFS_MONTHS",
        "DFS_STATUS",
    ]
    pat = _write(
        tmp_path / "p.txt",
        header,
        [
            [
                "TCGA-A1",
                "54",
                "Female",
                "BRCA_LumA",
                "40.2",
                "0:LIVING",
                "STAGE IIA",
                "40.2",
                "0:DiseaseFree",
            ],
            [
                "TCGA-A2",
                "61",
                "Female",
                "BRCA_Basal",
                "12.0",
                "1:DECEASED",
                "STAGE IIIC",
                "8.0",
                "1:Recurred/Progressed",
            ],
            [
                "TCGA-A3",
                "47",
                "Male",
                "BRCA_Her2",
                "5",
                "0:LIVING",
                "STAGE X",
                "[Not Available]",
                "[Not Available]",
            ],
            ["TCGA-A4", "30", "Female", "BRCA_Her2", "5", "0:LIVING", "STAGE IV", "", ""],
        ],
        meta=False,
    )
    df, rep = load_study("TCGA-BRCA", pat)
    r = df.set_index("patient_id")
    assert rep["patients_loaded"] == 4 and rep["rejection_codes"] == {}
    assert (
        r.loc["TCGA-A1", "stage"] == "II"
        and r.loc["TCGA-A2", "stage"] == "III"
        and r.loc["TCGA-A4", "stage"] == "IV"
    )
    assert pd.isna(r.loc["TCGA-A3", "stage"])  # "STAGE X" is unknown, not guessed
    assert r.loc["TCGA-A2", "relapse_event"] == 1 and r.loc["TCGA-A3", "sex"] == "MALE"


def test_every_declared_code_is_exercised_by_these_tests_or_documented():
    card = (
        Path(__file__).resolve().parents[3] / "data" / "dataset_cards" / "DATASET-CARD-METABRIC.md"
    ).read_text(encoding="utf-8")
    for code in ROW_CODES:
        assert code in card, f"{code} not documented in the METABRIC dataset card"
