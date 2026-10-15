"""
contracts.loaders

Standard data ingestion loaders and validation contracts for Vigil oncology platform.
"""

from contracts.loaders.metabric_loader import METABRICRecord, load_metabric_dataset
from contracts.loaders.mimic_loader import (
    MIMICAdmissionRecord,
    MIMICLabRecord,
    build_mimic_cancer_cohort,
)
from contracts.loaders.pds_loader import (
    PDSDemographicRecord,
    PDSLabRecord,
    load_pds_dataset,
)
from contracts.loaders.seer_loader import SEERRecord, load_seer_dataset
from contracts.loaders.tcga_loader import TCGARecord, load_tcga_dataset

__all__ = [
    "SEERRecord",
    "load_seer_dataset",
    "METABRICRecord",
    "load_metabric_dataset",
    "TCGARecord",
    "load_tcga_dataset",
    "PDSDemographicRecord",
    "PDSLabRecord",
    "load_pds_dataset",
    "MIMICAdmissionRecord",
    "MIMICLabRecord",
    "build_mimic_cancer_cohort",
]
