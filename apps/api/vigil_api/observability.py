"""Prometheus metrics, readiness/liveness helpers, and optional OpenTelemetry (G-09).

OpenTelemetry is off by default (``VIGIL_OTEL_ENABLED``). Enabling it without an
exporter endpoint is a no-op beyond installing instrumentation hooks.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from sqlalchemy import text

from vigil_api.database import engine

logger = logging.getLogger("vigil.api.observability")

REQUEST_COUNT = Counter(
    "vigil_http_requests_total",
    "HTTP requests handled by the API",
    ["method", "path", "status"],
)
REQUEST_LATENCY = Histogram(
    "vigil_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

_otel_started = False


def metrics_payload() -> tuple[bytes, str]:
    """Return (body, content_type) for a Prometheus scrape."""
    return generate_latest(), CONTENT_TYPE_LATEST


def check_database() -> dict[str, Any]:
    """Probe the configured database. Returns status dict; never raises."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"database": "ok"}
    except Exception as exc:  # noqa: BLE001 — readiness must not raise
        logger.warning("readiness database check failed: %s", exc)
        return {"database": "unavailable"}


def readiness_body() -> tuple[dict[str, Any], int]:
    """Return (JSON body, HTTP status). 503 when dependencies are down."""
    db = check_database()
    ok = db.get("database") == "ok"
    body = {"status": "ready" if ok else "not_ready", **db}
    return body, 200 if ok else 503


def liveness_body() -> dict[str, str]:
    """Process is up; does not check dependencies."""
    return {"status": "alive"}


def maybe_start_otel() -> None:
    """Install OpenTelemetry instrumentation when ``VIGIL_OTEL_ENABLED`` is truthy."""
    global _otel_started
    if _otel_started:
        return
    enabled = os.getenv("VIGIL_OTEL_ENABLED", "false").lower() in ("true", "1", "yes")
    if not enabled:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    except ImportError:
        logger.warning("VIGIL_OTEL_ENABLED set but opentelemetry packages are not installed")
        return

    resource = Resource.create({"service.name": os.getenv("OTEL_SERVICE_NAME", "vigil-api")})
    provider = TracerProvider(resource=resource)
    # Default: console exporter so enabling without a collector still produces spans locally.
    # Operators override via OTEL_EXPORTER_OTLP_ENDPOINT + otlp exporter in their image.
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        except ImportError:
            logger.warning("OTLP exporter unavailable; falling back to console exporter")
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    else:
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    _otel_started = True
    logger.info("OpenTelemetry tracing enabled (endpoint=%s)", endpoint or "console")


def record_request(method: str, path: str, status_code: int, duration_s: float) -> None:
    """Record one HTTP request on the Prometheus counters/histograms."""
    # Cardinality guard: drop path params by keeping only the first two segments for /api/v1/...
    label_path = _label_path(path)
    REQUEST_COUNT.labels(method=method, path=label_path, status=str(status_code)).inc()
    REQUEST_LATENCY.labels(method=method, path=label_path).observe(duration_s)


def _label_path(path: str) -> str:
    if path in ("/", "/health", "/live", "/ready", "/metrics"):
        return path
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] == "api":
        return "/" + "/".join(parts[:3]) + ("/…" if len(parts) > 3 else "")
    return "/" + (parts[0] if parts else "")
