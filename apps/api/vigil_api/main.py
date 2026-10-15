"""Vigil FastAPI Application Entrypoint."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure single threaded OpenMP on macOS to prevent fork segfaults
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from vigil_api.config import settings
from vigil_api.database import engine, Base
from vigil_api.api.router import api_router
from vigil_api.ml.inference import VigilEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schemas and warm up Vigil engine."""
    Base.metadata.create_all(bind=engine)

    engine_instance = VigilEngine.get_instance()
    print(f"VigilEngine initialized. Status: {engine_instance.status}, Loaded: {engine_instance.is_loaded}")

    yield

    print("Shutting down Vigil surveillance services.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Vigil: Continuous Multimodal Oncology Surveillance & Decision-Support Aid. "
        "Research prototype — not a medical device."
    ),
    lifespan=lifespan,
)

# CORS Middleware with strict origin list (Defect A5)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "system": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "is_synthetic": settings.IS_SYNTHETIC_DATA,
        "disclaimer": settings.DISCLAIMER,
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    engine_inst = VigilEngine.get_instance()
    return {
        "status": "healthy",
        "ml_engine_loaded": engine_inst.is_loaded,
        "ml_model_status": engine_inst.status,
        "database": "connected",
        "is_synthetic": settings.IS_SYNTHETIC_DATA,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("vigil_api.main:app", host="0.0.0.0", port=8000, reload=True)
