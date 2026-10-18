"""FastAPI Router aggregator for Vigil Precision Oncology Platform."""

from fastapi import APIRouter

from vigil_api.api.endpoints import (
    alerts,
    analytics,
    audit,
    batch_import,
    companion,
    continuity,
    fhir,
    follow_up,
    hl7,
    patients,
    quality,
    sync,
)

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["Patients & Surveillance"])
api_router.include_router(
    companion.router, prefix="/companion", tags=["Family & Patient Companion (M8)"]
)
api_router.include_router(
    continuity.router, prefix="/continuity", tags=["Treatment Continuity & Radiotherapy (M7)"]
)
api_router.include_router(
    batch_import.router, prefix="/observations", tags=["Batch Observation Ingestion"]
)
api_router.include_router(fhir.router, prefix="/fhir", tags=["HL7 FHIR R4 Interoperability"])
api_router.include_router(hl7.router, prefix="/hl7", tags=["HL7 v2 ORU^R01 Interoperability"])
api_router.include_router(sync.router, prefix="/sync", tags=["Offline Batch Sync"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Acknowledgement"])
api_router.include_router(follow_up.router, prefix="/follow-up", tags=["Follow-Up Guardian (M6)"])
api_router.include_router(audit.router, prefix="/audit", tags=["Cryptographic Audit Trail"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Cohort"])
api_router.include_router(
    quality.router, prefix="/quality", tags=["Quality & Missed-Signal Audit (M10)"]
)
