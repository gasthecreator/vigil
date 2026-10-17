"""FastAPI Router aggregator for Vigil Precision Oncology Platform."""

from fastapi import APIRouter

from vigil_api.api.endpoints import alerts, analytics, audit, follow_up, patients

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["Patients & Surveillance"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts & Acknowledgement"])
api_router.include_router(follow_up.router, prefix="/follow-up", tags=["Follow-Up Guardian (M6)"])
api_router.include_router(audit.router, prefix="/audit", tags=["Cryptographic Audit Trail"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Cohort"])
