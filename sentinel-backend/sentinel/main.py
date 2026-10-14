"""Sentinel FastAPI Application Entrypoint."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure single threaded OpenMP on macOS to prevent fork segfaults
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from sentinel.config import settings
from sentinel.database import engine, Base
from sentinel.api.router import api_router
from sentinel.ml.inference import SentinelEngine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schemas and warm up ML inference engine."""
    # Create DB tables
    Base.metadata.create_all(bind=engine)

    # Initialize SentinelEngine singleton
    engine_instance = SentinelEngine.get_instance(artifacts_dir=settings.ARTIFACTS_DIR)
    print(f"SentinelEngine initialized. Artifacts loaded: {engine_instance.is_loaded}")

    yield

    print("Shutting down Sentinel surveillance services.")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Continuous Multimodal Oncology Surveillance & Early Metastatic Recurrence Detection Platform",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
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
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    engine_loaded = SentinelEngine.get_instance().is_loaded
    return {
        "status": "healthy",
        "ml_engine_loaded": engine_loaded,
        "database": "connected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sentinel.main:app", host="0.0.0.0", port=8000, reload=True)
