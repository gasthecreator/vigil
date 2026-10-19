"""Vigil FastAPI Application Entrypoint."""

import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

# Ensure single threaded OpenMP on macOS to prevent fork segfaults
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from fastapi.responses import Response

from vigil_api.api.router import api_router
from vigil_api.config import settings
from vigil_api.database import Base, engine
from vigil_api.ml.inference import VigilEngine
from vigil_api.observability import (
    liveness_body,
    maybe_start_otel,
    metrics_payload,
    readiness_body,
    record_request,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database schemas and warm up Vigil engine."""
    Base.metadata.create_all(bind=engine)
    if settings.OTEL_ENABLED:
        maybe_start_otel()

    engine_instance = VigilEngine.get_instance()
    print(
        f"VigilEngine initialized. Status: {engine_instance.status}, Loaded: {engine_instance.is_loaded}"
    )

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
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

logger = logging.getLogger("vigil.api.access")


@app.middleware("http")
async def request_id_and_logging_middleware(request: Request, call_next):
    """Generates/propagates X-Request-ID and emits structured JSON access logs."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id

    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    response.headers["X-Request-ID"] = request_id

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": duration_ms,
        "client_ip": request.client.host if request.client else "unknown",
    }
    logger.info(json.dumps(log_entry))
    record_request(request.method, request.url.path, response.status_code, duration_ms / 1000.0)
    return response


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


# G-09 probes/metrics. /live and /ready are public and minimal (no dependency detail beyond ok/unavailable).
# /metrics is bearer-token gated (VIGIL_METRICS_TOKEN) in every profile; with no token it is disabled (403).
@app.get("/live")
def live():
    return liveness_body()


@app.get("/ready")
def ready():
    body, status_code = readiness_body()
    return Response(
        content=json.dumps(body),
        status_code=status_code,
        media_type="application/json",
    )


@app.get("/metrics")
def metrics(request: Request):
    token = settings.METRICS_TOKEN
    if not token:
        return Response(status_code=403)  # disabled until the operator sets VIGIL_METRICS_TOKEN
    supplied = request.headers.get("authorization", "")
    if not hmac.compare_digest(supplied.encode(), f"Bearer {token}".encode()):
        return Response(status_code=401, headers={"WWW-Authenticate": "Bearer"})
    body, content_type = metrics_payload()
    return Response(content=body, media_type=content_type)


if __name__ == "__main__":
    import uvicorn

    # Local reload helper only; container entrypoints bind explicitly in Dockerfiles.
    uvicorn.run("vigil_api.main:app", host="127.0.0.1", port=8000, reload=True)
