"""
vigil_core.analytes

Clinical Analyte Registry for Vigil Oncology Decision-Support Platform.
Contains >= 24 clinical laboratory analytes with LOINC codes, canonical UCUM units,
EFLM biological variation parameters (CVi, CVg), analytical specifications (CVa),
Reference Change Value (RCV) computations, and plausibility boundary validation.
"""

from __future__ import annotations

import math
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from vigil_core.units import convert_units


class TargetOrgan(str, Enum):
    BREAST = "breast"
    LIVER = "liver"
    BONE = "bone"
    LUNG = "lung"
    BRAIN = "brain"
    RENAL = "renal"
    BONE_MARROW = "bone_marrow"
    SYSTEMIC = "systemic"


class PlausibilityStatus(str, Enum):
    VALID_NORMAL = "valid_normal"
    VALID_ELEVATED = "valid_elevated"
    VALID_DEPRESSED = "valid_depressed"
    CRITICAL_HIGH = "critical_high"
    CRITICAL_LOW = "critical_low"
    UNPHYSIOLOGICAL_HIGH = "unphysiological_high"
    UNPHYSIOLOGICAL_LOW = "unphysiological_low"


class BiologicalVariation(BaseModel):
    """Within-subject (CVi) and between-subject (CVg) biological variation from EFLM."""

    cv_i: float = Field(..., description="Within-subject biological coefficient of variation (%)")
    cv_g: float = Field(..., description="Between-subject biological coefficient of variation (%)")
    index_of_individuality: float = Field(..., description="II = CVi / CVg")
    citation: str = Field(..., description="Literature source / EFLM database DOI")
    evidence_status: str = Field(
        default="SECONDARY",
        description="Evidence status: PRIMARY-VERIFIED (backed by saved public excerpt) or SECONDARY",
    )


class AnalyticalSpecification(BaseModel):
    """Desirable analytical precision and maximum bias goals."""

    cv_a_desirable: float = Field(..., description="Desirable analytical CV (%) = 0.5 * CVi")
    bias_max_desirable: float = Field(..., description="Desirable maximum bias (%)")


class PlausibilityBounds(BaseModel):
    """Physiological, reference, and critical safety thresholds."""

    physiological_min: float = Field(..., description="Absolute biological minimum limit")
    physiological_max: float = Field(..., description="Absolute biological maximum limit")
    reference_low: float = Field(..., description="Healthy population reference low")
    reference_high: float = Field(..., description="Healthy population reference high")
    critical_low: Optional[float] = Field(None, description="Critical action low threshold")
    critical_high: Optional[float] = Field(None, description="Critical action high threshold")


class AnalyteDefinition(BaseModel):
    """Full clinical definition of an analyte in the Vigil registry."""

    code: str = Field(..., description="Unique internal identifier (e.g. 'ca_15_3')")
    name: str = Field(..., description="Standard clinical display name")
    description: str = Field(..., description="Brief clinical role and diagnostic utility")
    loinc_code: str = Field(..., description="Official Regenstrief LOINC code")
    canonical_unit: str = Field(..., description="Canonical UCUM unit string")
    supported_units: List[str] = Field(
        default_factory=list, description="Supported alternate UCUM units"
    )
    biological_variation: BiologicalVariation
    analytical_spec: AnalyticalSpecification
    plausibility: PlausibilityBounds
    target_organs: List[TargetOrgan] = Field(default_factory=list)


class PlausibilityResult(BaseModel):
    """Result of validating an analyte measurement against clinical boundaries."""

    analyte_code: str
    original_value: float
    original_unit: str
    canonical_value: float
    canonical_unit: str
    status: PlausibilityStatus
    is_valid: bool
    is_critical: bool
    message: str


# ==============================================================================
# Master Analyte Registry (EFLM 2024 Biological Variation & Clinical Guidelines)
# ==============================================================================

ANALYTE_REGISTRY: Dict[str, AnalyteDefinition] = {
    "ca_15_3": AnalyteDefinition(
        code="ca_15_3",
        name="Cancer Antigen 15-3",
        description="MUC1 mucin-derived serum tumour marker for metastatic breast cancer recurrence monitoring.",
        loinc_code="83082-8",
        canonical_unit="[iU]/mL",
        supported_units=["[iU]/mL", "U/mL", "kU/L"],
        biological_variation=BiologicalVariation(
            cv_i=6.1,
            cv_g=62.9,
            index_of_individuality=0.10,  # High individuality (II < 0.6)
            citation="Ricós C et al. Scand J Clin Lab Invest 1999; Westgard Biodatabase (docs/evidence/excerpts/E9_westgard_ricos_biodatabase.md)",
            evidence_status="PRIMARY-VERIFIED",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=3.05,  # 0.5 * CVi
            bias_max_desirable=15.8,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=5000.0,
            reference_low=0.0,
            reference_high=30.0,
            critical_high=100.0,
        ),
        target_organs=[TargetOrgan.BREAST, TargetOrgan.LIVER, TargetOrgan.BONE, TargetOrgan.LUNG],
    ),
    "ca_27_29": AnalyteDefinition(
        code="ca_27_29",
        name="Cancer Antigen 27-29",
        description="Alternate MUC1 epitope tumour marker used in breast cancer surveillance.",
        loinc_code="17842-6",
        canonical_unit="[iU]/mL",
        supported_units=["[iU]/mL", "U/mL"],
        biological_variation=BiologicalVariation(
            cv_i=6.2,
            cv_g=24.5,
            index_of_individuality=0.25,
            citation="EFLM Biological Variation Database 2024",
            evidence_status="SECONDARY",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=3.1,
            bias_max_desirable=6.3,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=6000.0,
            reference_low=0.0,
            reference_high=38.0,
            critical_high=120.0,
        ),
        target_organs=[TargetOrgan.BREAST, TargetOrgan.LIVER, TargetOrgan.BONE],
    ),
    "cea": AnalyteDefinition(
        code="cea",
        name="Carcinoembryonic Antigen",
        description="Oncofetal glycoprotein elevated in metastatic breast, colorectal, and lung adenocarcinomas.",
        loinc_code="2039-6",
        canonical_unit="ug/L",
        supported_units=["ug/L", "ng/mL"],
        biological_variation=BiologicalVariation(
            cv_i=12.7,
            cv_g=55.6,
            index_of_individuality=0.23,
            citation="Ricós C et al. Scand J Clin Lab Invest 1999; Westgard Biodatabase (docs/evidence/excerpts/E9_westgard_ricos_biodatabase.md)",
            evidence_status="PRIMARY-VERIFIED",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=6.35,
            bias_max_desirable=14.9,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=10000.0,
            reference_low=0.0,
            reference_high=5.0,
            critical_high=20.0,
        ),
        target_organs=[TargetOrgan.BREAST, TargetOrgan.LIVER, TargetOrgan.LUNG],
    ),
    "alt": AnalyteDefinition(
        code="alt",
        name="Alanine Aminotransferase",
        description="Hepatocellular enzyme sensitive to hepatic metastasis, drug injury, and viral hepatitis.",
        loinc_code="1742-6",
        canonical_unit="U/L",
        supported_units=["U/L", "ukat/L"],
        biological_variation=BiologicalVariation(
            cv_i=19.4,
            cv_g=41.6,
            index_of_individuality=0.47,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=9.7,
            bias_max_desirable=11.5,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=1.0,
            physiological_max=5000.0,
            reference_low=7.0,
            reference_high=56.0,
            critical_high=500.0,
        ),
        target_organs=[TargetOrgan.LIVER],
    ),
    "ast": AnalyteDefinition(
        code="ast",
        name="Aspartate Aminotransferase",
        description="Transaminase present in hepatocytes, cardiac myocytes, and skeletal muscle.",
        loinc_code="1920-8",
        canonical_unit="U/L",
        supported_units=["U/L", "ukat/L"],
        biological_variation=BiologicalVariation(
            cv_i=12.3,
            cv_g=23.1,
            index_of_individuality=0.53,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=6.15,
            bias_max_desirable=6.5,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=1.0,
            physiological_max=6000.0,
            reference_low=10.0,
            reference_high=40.0,
            critical_high=400.0,
        ),
        target_organs=[TargetOrgan.LIVER, TargetOrgan.SYSTEMIC],
    ),
    "alp": AnalyteDefinition(
        code="alp",
        name="Alkaline Phosphatase",
        description="Enzyme concentrated in biliary canaliculi and osteoblasts; marker of bone and liver metastasis.",
        loinc_code="6768-6",
        canonical_unit="U/L",
        supported_units=["U/L", "ukat/L"],
        biological_variation=BiologicalVariation(
            cv_i=6.4,
            cv_g=26.1,
            index_of_individuality=0.25,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=3.2,
            bias_max_desirable=6.7,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=5.0,
            physiological_max=3000.0,
            reference_low=44.0,
            reference_high=147.0,
            critical_high=500.0,
        ),
        target_organs=[TargetOrgan.BONE, TargetOrgan.LIVER],
    ),
    "ggt": AnalyteDefinition(
        code="ggt",
        name="Gamma-Glutamyl Transferase",
        description="Biliary canalicular enzyme used to adjudicate hepatic vs bone origin of elevated ALP.",
        loinc_code="2324-2",
        canonical_unit="U/L",
        supported_units=["U/L", "ukat/L"],
        biological_variation=BiologicalVariation(
            cv_i=13.8,
            cv_g=42.4,
            index_of_individuality=0.33,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=6.9,
            bias_max_desirable=11.1,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=1.0,
            physiological_max=2500.0,
            reference_low=9.0,
            reference_high=48.0,
            critical_high=300.0,
        ),
        target_organs=[TargetOrgan.LIVER],
    ),
    "total_bilirubin": AnalyteDefinition(
        code="total_bilirubin",
        name="Total Bilirubin",
        description="Haem breakdown metabolite; reflects hepatic clearance capacity and biliary patency.",
        loinc_code="1975-2",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "umol/L"],
        biological_variation=BiologicalVariation(
            cv_i=21.8,
            cv_g=31.5,
            index_of_individuality=0.69,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=10.9,
            bias_max_desirable=9.6,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.05,
            physiological_max=50.0,
            reference_low=0.2,
            reference_high=1.2,
            critical_high=15.0,
        ),
        target_organs=[TargetOrgan.LIVER],
    ),
    "direct_bilirubin": AnalyteDefinition(
        code="direct_bilirubin",
        name="Direct Bilirubin",
        description="Conjugated fraction reflecting post-hepatic or obstructive biliary pathology.",
        loinc_code="1968-7",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "umol/L"],
        biological_variation=BiologicalVariation(
            cv_i=36.8,
            cv_g=43.2,
            index_of_individuality=0.85,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=18.4,
            bias_max_desirable=14.2,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=35.0,
            reference_low=0.0,
            reference_high=0.3,
            critical_high=10.0,
        ),
        target_organs=[TargetOrgan.LIVER],
    ),
    "albumin": AnalyteDefinition(
        code="albumin",
        name="Serum Albumin",
        description="Hepatic synthetic protein and systemic negative acute-phase reactant.",
        loinc_code="1751-7",
        canonical_unit="g/dL",
        supported_units=["g/dL", "g/L"],
        biological_variation=BiologicalVariation(
            cv_i=3.2,
            cv_g=4.8,
            index_of_individuality=0.67,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=1.6,
            bias_max_desirable=1.4,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.5,
            physiological_max=7.0,
            reference_low=3.5,
            reference_high=5.0,
            critical_low=1.5,
        ),
        target_organs=[TargetOrgan.LIVER, TargetOrgan.SYSTEMIC],
    ),
    "total_protein": AnalyteDefinition(
        code="total_protein",
        name="Total Protein",
        description="Serum protein concentration including albumin and globulin fractions.",
        loinc_code="2885-2",
        canonical_unit="g/dL",
        supported_units=["g/dL", "g/L"],
        biological_variation=BiologicalVariation(
            cv_i=2.7,
            cv_g=4.7,
            index_of_individuality=0.57,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=1.35,
            bias_max_desirable=1.35,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=2.0,
            physiological_max=15.0,
            reference_low=6.0,
            reference_high=8.3,
            critical_low=3.5,
            critical_high=11.0,
        ),
        target_organs=[TargetOrgan.LIVER, TargetOrgan.SYSTEMIC],
    ),
    "ldh": AnalyteDefinition(
        code="ldh",
        name="Lactate Dehydrogenase",
        description="Intracellular glycolytic enzyme indicative of high cellular turnover and tumour burden.",
        loinc_code="2532-0",
        canonical_unit="U/L",
        supported_units=["U/L", "ukat/L"],
        biological_variation=BiologicalVariation(
            cv_i=8.6,
            cv_g=15.0,
            index_of_individuality=0.57,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=4.3,
            bias_max_desirable=4.3,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=20.0,
            physiological_max=10000.0,
            reference_low=140.0,
            reference_high=280.0,
            critical_high=800.0,
        ),
        target_organs=[TargetOrgan.LIVER, TargetOrgan.BONE_MARROW, TargetOrgan.SYSTEMIC],
    ),
    "calcium": AnalyteDefinition(
        code="calcium",
        name="Serum Total Calcium",
        description="Serum cation essential for neuromuscular signaling; elevated in osteolytic bone metastasis.",
        loinc_code="17861-6",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "mmol/L"],
        biological_variation=BiologicalVariation(
            cv_i=1.9,
            cv_g=2.8,
            index_of_individuality=0.68,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=0.95,
            bias_max_desirable=0.85,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=3.0,
            physiological_max=20.0,
            reference_low=8.5,
            reference_high=10.5,
            critical_low=6.5,
            critical_high=13.0,
        ),
        target_organs=[TargetOrgan.BONE, TargetOrgan.RENAL],
    ),
    "corrected_calcium": AnalyteDefinition(
        code="corrected_calcium",
        name="Albumin-Corrected Calcium",
        description="Calcium adjusted for hypoalbuminaemia: Total Ca + 0.8 * (4.0 - Albumin).",
        loinc_code="47553-3",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "mmol/L"],
        biological_variation=BiologicalVariation(
            cv_i=2.1,
            cv_g=3.0,
            index_of_individuality=0.70,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=1.05,
            bias_max_desirable=0.9,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=3.0,
            physiological_max=20.0,
            reference_low=8.5,
            reference_high=10.5,
            critical_low=6.5,
            critical_high=13.0,
        ),
        target_organs=[TargetOrgan.BONE],
    ),
    "phosphate": AnalyteDefinition(
        code="phosphate",
        name="Serum Phosphate",
        description="Inorganic phosphorus critical for bone mineralization and acid-base balance.",
        loinc_code="2777-1",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "mmol/L"],
        biological_variation=BiologicalVariation(
            cv_i=8.5,
            cv_g=10.4,
            index_of_individuality=0.82,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=4.25,
            bias_max_desirable=3.4,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.5,
            physiological_max=15.0,
            reference_low=2.5,
            reference_high=4.5,
            critical_low=1.0,
            critical_high=8.0,
        ),
        target_organs=[TargetOrgan.BONE, TargetOrgan.RENAL],
    ),
    "creatinine": AnalyteDefinition(
        code="creatinine",
        name="Serum Creatinine",
        description="Muscle catabolism product cleared by glomerular filtration; key marker of renal function.",
        loinc_code="2160-0",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "umol/L"],
        biological_variation=BiologicalVariation(
            cv_i=4.5,
            cv_g=14.1,
            index_of_individuality=0.32,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=2.25,
            bias_max_desirable=3.7,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.1,
            physiological_max=25.0,
            reference_low=0.5,
            reference_high=1.1,
            critical_high=5.0,
        ),
        target_organs=[TargetOrgan.RENAL],
    ),
    "egfr": AnalyteDefinition(
        code="egfr",
        name="Estimated GFR (CKD-EPI)",
        description="Glomerular filtration rate estimated from creatinine, age, and sex.",
        loinc_code="33914-3",
        canonical_unit="mL/min/1.73m2",
        supported_units=["mL/min/1.73m2"],
        biological_variation=BiologicalVariation(
            cv_i=5.4,
            cv_g=12.0,
            index_of_individuality=0.45,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=2.7,
            bias_max_desirable=3.3,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=2.0,
            physiological_max=180.0,
            reference_low=90.0,
            reference_high=140.0,
            critical_low=15.0,
        ),
        target_organs=[TargetOrgan.RENAL],
    ),
    "urea": AnalyteDefinition(
        code="urea",
        name="Blood Urea Nitrogen / Urea",
        description="Nitrogenous waste product reflecting protein turnover, renal perfusion, and filtration.",
        loinc_code="3094-0",
        canonical_unit="mg/dL",
        supported_units=["mg/dL", "mmol/L"],
        biological_variation=BiologicalVariation(
            cv_i=12.3,
            cv_g=18.2,
            index_of_individuality=0.68,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=6.15,
            bias_max_desirable=5.5,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=1.0,
            physiological_max=200.0,
            reference_low=7.0,
            reference_high=20.0,
            critical_high=80.0,
        ),
        target_organs=[TargetOrgan.RENAL],
    ),
    "haemoglobin": AnalyteDefinition(
        code="haemoglobin",
        name="Haemoglobin",
        description="Erythrocyte oxygen carrier; decreased in bone marrow infiltration, chemotherapy toxicity, chronic disease.",
        loinc_code="718-7",
        canonical_unit="g/dL",
        supported_units=["g/dL", "g/L"],
        biological_variation=BiologicalVariation(
            cv_i=2.8,
            cv_g=6.6,
            index_of_individuality=0.42,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=1.4,
            bias_max_desirable=1.8,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=2.0,
            physiological_max=25.0,
            reference_low=12.0,
            reference_high=16.0,
            critical_low=6.5,
            critical_high=20.0,
        ),
        target_organs=[TargetOrgan.BONE_MARROW, TargetOrgan.SYSTEMIC],
    ),
    "platelets": AnalyteDefinition(
        code="platelets",
        name="Platelet Count",
        description="Thrombocytes responsible for haemostasis; suppressed by marrow replacement or chemotherapy.",
        loinc_code="777-3",
        canonical_unit="10*9/L",
        supported_units=["10*9/L", "10*3/uL", "/uL"],
        biological_variation=BiologicalVariation(
            cv_i=9.1,
            cv_g=21.5,
            index_of_individuality=0.42,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=4.55,
            bias_max_desirable=5.8,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=5.0,
            physiological_max=2000.0,
            reference_low=150.0,
            reference_high=450.0,
            critical_low=20.0,
            critical_high=1000.0,
        ),
        target_organs=[TargetOrgan.BONE_MARROW],
    ),
    "wbc": AnalyteDefinition(
        code="wbc",
        name="White Blood Cell Count",
        description="Total leukocyte count; reflects marrow function, systemic inflammatory response, or infection.",
        loinc_code="6690-2",
        canonical_unit="10*9/L",
        supported_units=["10*9/L", "10*3/uL", "/uL"],
        biological_variation=BiologicalVariation(
            cv_i=11.3,
            cv_g=20.4,
            index_of_individuality=0.55,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=5.65,
            bias_max_desirable=5.8,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.2,
            physiological_max=200.0,
            reference_low=4.0,
            reference_high=11.0,
            critical_low=1.5,
            critical_high=30.0,
        ),
        target_organs=[TargetOrgan.BONE_MARROW, TargetOrgan.SYSTEMIC],
    ),
    "anc": AnalyteDefinition(
        code="anc",
        name="Absolute Neutrophil Count",
        description="Granulocyte count essential for monitoring post-chemotherapy neutropenia.",
        loinc_code="751-8",
        canonical_unit="10*9/L",
        supported_units=["10*9/L", "10*3/uL", "/uL"],
        biological_variation=BiologicalVariation(
            cv_i=18.2,
            cv_g=31.0,
            index_of_individuality=0.59,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=9.1,
            bias_max_desirable=9.0,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=100.0,
            reference_low=1.8,
            reference_high=7.5,
            critical_low=0.5,
        ),
        target_organs=[TargetOrgan.BONE_MARROW],
    ),
    "nlr": AnalyteDefinition(
        code="nlr",
        name="Neutrophil-to-Lymphocyte Ratio",
        description="Prognostic systemic inflammatory index calculated as ANC divided by ALC.",
        loinc_code="96552-5",
        canonical_unit="1",
        supported_units=["1", "ratio", ""],
        biological_variation=BiologicalVariation(
            cv_i=16.5,
            cv_g=28.0,
            index_of_individuality=0.59,
            citation="Literature pooled meta-analysis",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=8.25,
            bias_max_desirable=8.1,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.1,
            physiological_max=50.0,
            reference_low=1.0,
            reference_high=3.0,
            critical_high=10.0,
        ),
        target_organs=[TargetOrgan.SYSTEMIC],
    ),
    "esr": AnalyteDefinition(
        code="esr",
        name="Erythrocyte Sedimentation Rate",
        description="Indirect non-specific measure of circulating acute-phase reactants (fibrinogen, immunoglobulins).",
        loinc_code="4537-7",
        canonical_unit="mm/h",
        supported_units=["mm/h", "mm/hr"],
        biological_variation=BiologicalVariation(
            cv_i=19.0,
            cv_g=45.0,
            index_of_individuality=0.42,
            citation="Ricós C et al. 1999",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=9.5,
            bias_max_desirable=12.2,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.0,
            physiological_max=150.0,
            reference_low=0.0,
            reference_high=20.0,
            critical_high=80.0,
        ),
        target_organs=[TargetOrgan.SYSTEMIC, TargetOrgan.BONE],
    ),
    "crp": AnalyteDefinition(
        code="crp",
        name="C-Reactive Protein",
        description="Pentameric acute-phase reactant synthesized by hepatocytes in response to IL-6.",
        loinc_code="1988-5",
        canonical_unit="mg/L",
        supported_units=["mg/L", "mg/dL"],
        biological_variation=BiologicalVariation(
            cv_i=42.2,
            cv_g=76.3,
            index_of_individuality=0.55,
            citation="Aarsand AK et al. CCLM 2020 (EFLM)",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=21.1,
            bias_max_desirable=21.8,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.05,
            physiological_max=500.0,
            reference_low=0.0,
            reference_high=5.0,
            critical_high=50.0,
        ),
        target_organs=[TargetOrgan.SYSTEMIC, TargetOrgan.LIVER],
    ),
    "inr": AnalyteDefinition(
        code="inr",
        name="International Normalized Ratio",
        description="Standardized prothrombin time measuring extrinsic coagulation pathway.",
        loinc_code="6301-6",
        canonical_unit="1",
        supported_units=["1", "ratio", ""],
        biological_variation=BiologicalVariation(
            cv_i=4.0,
            cv_g=6.5,
            index_of_individuality=0.62,
            citation="EFLM Biological Variation Database 2024",
        ),
        analytical_spec=AnalyticalSpecification(
            cv_a_desirable=2.0,
            bias_max_desirable=1.9,
        ),
        plausibility=PlausibilityBounds(
            physiological_min=0.6,
            physiological_max=15.0,
            reference_low=0.8,
            reference_high=1.2,
            critical_high=4.5,
        ),
        target_organs=[TargetOrgan.LIVER],
    ),
}


# ==============================================================================
# Helper Functions & Reference Change Value (RCV)
# ==============================================================================


def get_analyte(code: str) -> AnalyteDefinition:
    """Retrieves an analyte definition by code. Case-insensitive."""
    clean_code = code.strip().lower()
    if clean_code not in ANALYTE_REGISTRY:
        raise KeyError(f"Analyte '{code}' not found in Vigil Analyte Registry.")
    return ANALYTE_REGISTRY[clean_code]


def list_analytes() -> List[AnalyteDefinition]:
    """Returns all registered analyte definitions."""
    return list(ANALYTE_REGISTRY.values())


def calculate_rcv(
    analyte_code: str,
    cv_a: Optional[float] = None,
    confidence: float = 0.95,
    two_sided: bool = True,
    log_normal: bool = False,
) -> float:
    """
    Computes the Reference Change Value (RCV, %) per Fraser (2001).

    Normal model:
        RCV = sqrt(2) * Z * sqrt(CV_a^2 + CV_i^2)

    Log-normal model (recommended for right-skewed analytes with CVi > 20%):
        s_i = sqrt(ln(1 + (CV_i / 100)^2))
        s_a = sqrt(ln(1 + (CV_a / 100)^2))
        RCV_up = (exp(Z * sqrt(2 * (s_a^2 + s_i^2))) - 1) * 100

    Parameters:
        analyte_code: Registered analyte code.
        cv_a: Analytical CV (%). Defaults to desirable CVa from registry.
        confidence: Desired statistical confidence (typically 0.95 or 0.99).
        two_sided: Whether the critical difference is two-sided.
        log_normal: Use log-normal formula for skewed distributions.

    Returns:
        Critical difference threshold in percentage (%).
    """
    analyte = get_analyte(analyte_code)
    cv_i = analyte.biological_variation.cv_i
    effective_cv_a = cv_a if cv_a is not None else analyte.analytical_spec.cv_a_desirable

    # Standard Z-scores
    if confidence == 0.95:
        z = 1.96 if two_sided else 1.645
    elif confidence == 0.99:
        z = 2.576 if two_sided else 2.326
    elif confidence == 0.90:
        z = 1.645 if two_sided else 1.282
    else:
        # Fallback approximation using probit
        z = 1.96

    if not log_normal:
        return math.sqrt(2.0) * z * math.sqrt(effective_cv_a**2 + cv_i**2)
    else:
        s_i = math.sqrt(math.log(1.0 + (cv_i / 100.0) ** 2))
        s_a = math.sqrt(math.log(1.0 + (effective_cv_a / 100.0) ** 2))
        s_total = math.sqrt(2.0 * (s_a**2 + s_i**2))
        return (math.exp(z * s_total) - 1.0) * 100.0


def check_plausibility(
    analyte_code: str,
    value: float,
    unit: str,
) -> PlausibilityResult:
    """
    Validates a laboratory result against physiological, reference, and critical bounds.
    Converts input value to canonical unit before validation.
    """
    analyte = get_analyte(analyte_code)
    canonical_val = convert_units(
        value, from_unit=unit, to_unit=analyte.canonical_unit, analyte_code=analyte.code
    )
    p = analyte.plausibility

    # Check unphysiological bounds
    if canonical_val < p.physiological_min:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.UNPHYSIOLOGICAL_LOW,
            is_valid=False,
            is_critical=True,
            message=f"Value {canonical_val:.2f} {analyte.canonical_unit} is below the physiological minimum ({p.physiological_min}). Probable dilution or instrument error.",
        )
    if canonical_val > p.physiological_max:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.UNPHYSIOLOGICAL_HIGH,
            is_valid=False,
            is_critical=True,
            message=f"Value {canonical_val:.2f} {analyte.canonical_unit} exceeds the physiological maximum ({p.physiological_max}). Probable carryover or unit error.",
        )

    # Check critical panic thresholds
    if p.critical_low is not None and canonical_val <= p.critical_low:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.CRITICAL_LOW,
            is_valid=True,
            is_critical=True,
            message=f"CRITICAL PANIC LOW: {canonical_val:.2f} {analyte.canonical_unit} <= {p.critical_low}. Immediate clinical notification required.",
        )
    if p.critical_high is not None and canonical_val >= p.critical_high:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.CRITICAL_HIGH,
            is_valid=True,
            is_critical=True,
            message=f"CRITICAL PANIC HIGH: {canonical_val:.2f} {analyte.canonical_unit} >= {p.critical_high}. Immediate clinical notification required.",
        )

    # Check population reference range
    if canonical_val < p.reference_low:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.VALID_DEPRESSED,
            is_valid=True,
            is_critical=False,
            message=f"Below healthy reference interval ({p.reference_low} - {p.reference_high} {analyte.canonical_unit}).",
        )
    if canonical_val > p.reference_high:
        return PlausibilityResult(
            analyte_code=analyte.code,
            original_value=value,
            original_unit=unit,
            canonical_value=canonical_val,
            canonical_unit=analyte.canonical_unit,
            status=PlausibilityStatus.VALID_ELEVATED,
            is_valid=True,
            is_critical=False,
            message=f"Elevated above healthy reference interval ({p.reference_low} - {p.reference_high} {analyte.canonical_unit}).",
        )

    return PlausibilityResult(
        analyte_code=analyte.code,
        original_value=value,
        original_unit=unit,
        canonical_value=canonical_val,
        canonical_unit=analyte.canonical_unit,
        status=PlausibilityStatus.VALID_NORMAL,
        is_valid=True,
        is_critical=False,
        message=f"Within healthy reference interval ({p.reference_low} - {p.reference_high} {analyte.canonical_unit}).",
    )
