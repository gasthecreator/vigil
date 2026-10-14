"""FastAPI Router aggregator."""

from fastapi import APIRouter
from sentinel.api.endpoints import patients, analytics

api_router = APIRouter()

api_router.include_router(patients.router, prefix="/patients", tags=["Patients & Surveillance"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["Analytics & Cohort"])
