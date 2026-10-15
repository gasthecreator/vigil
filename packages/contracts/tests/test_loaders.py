"""
Tests for contracts.loaders: Validation of SEER, METABRIC, TCGA, PDS, and MIMIC fixtures.
"""

from pathlib import Path
import pytest

from contracts.loaders import (
    build_mimic_cancer_cohort,
    load_metabric_dataset,
    load_pds_dataset,
    load_seer_dataset,
    load_tcga_dataset,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "fixtures"


def test_load_seer_dataset():
    f = FIXTURES_DIR / "seer_fixture.csv"
    assert f.exists()
    df = load_seer_dataset(f)
    assert len(df) == 5
    assert "SEER_ID" in df.columns
    assert "SUBTYPE" in df.columns
    assert df["AGE_DX"].mean() > 40


def test_load_metabric_dataset():
    f = FIXTURES_DIR / "metabric_fixture.csv"
    assert f.exists()
    df = load_metabric_dataset(f)
    assert len(df) == 5
    assert "PATIENT_ID" in df.columns
    assert "NOTTINGHAM_PROGNOSTIC_INDEX" in df.columns
    assert set(df["ER_STATUS"].unique()).issubset({"Positive", "Negative"})


def test_load_tcga_dataset():
    f = FIXTURES_DIR / "tcga_brca_fixture.csv"
    assert f.exists()
    df = load_tcga_dataset(f)
    assert len(df) == 5
    assert "bcr_patient_barcode" in df.columns
    assert "ajcc_pathologic_tumor_stage" in df.columns


def test_load_pds_dataset():
    dm_f = FIXTURES_DIR / "pds_dm_fixture.csv"
    lb_f = FIXTURES_DIR / "pds_lb_fixture.csv"
    assert dm_f.exists() and lb_f.exists()
    dm_df, lb_df = load_pds_dataset(dm_f, lb_f)
    assert len(dm_df) == 3
    assert len(lb_df) == 6
    assert "USUBJID" in dm_df.columns
    assert "LBTESTCD" in lb_df.columns


def test_build_mimic_cancer_cohort():
    adm_f = FIXTURES_DIR / "mimic_admissions_fixture.csv"
    diag_f = FIXTURES_DIR / "mimic_diagnoses_fixture.csv"
    lab_f = FIXTURES_DIR / "mimic_labevents_fixture.csv"
    assert adm_f.exists() and diag_f.exists() and lab_f.exists()

    cohort_df = build_mimic_cancer_cohort(adm_f, diag_f, lab_f)
    assert not cohort_df.empty
    # Subject 10001 (C50911) and 10002 (1749) are cancer patients; 10003 is hypertension only (4019)
    assert set(cohort_df["subject_id"].unique()) == {10001, 10002}
    assert "charttime" in cohort_df.columns
    assert "valuenum" in cohort_df.columns
