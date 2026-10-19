"""Configuration settings for Vigil Clinical Decision Support API.

Adheres to MASTER_PLAN.md §9.2, §9.3, and §11.
Remediates Defect A4 (personal machine paths), Defect A5 (wildcard CORS),
and Defect A7 (hardcoded alert thresholds).
"""

import os

from pydantic_settings import BaseSettings

DEFAULT_INSECURE_SECRET: str = "vigil-precision-oncology-secret-key-32bytes-min"


class Settings(BaseSettings):
    PROJECT_NAME: str = "Vigil"
    VERSION: str = "0.1.0-alpha"
    API_V1_STR: str = "/api/v1"

    # Environment profile: 'local', 'staging', or 'production'
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

    # Database: Default to local SQLite relative path; no personal absolute paths (Defect A4)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vigil_dev.db")

    # Clinical Alert Threshold (Defect A7)
    CLINICAL_ALERT_THRESHOLD: float = float(os.getenv("CLINICAL_ALERT_THRESHOLD", "0.75"))

    # CORS configuration: strict whitelist, NO wildcard '*' permitted (Defect A5)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # Synthetic data labeling: all current data and mock profiles are synthetic (Principle 1)
    IS_SYNTHETIC_DATA: bool = True

    # JWT & Auth Security (Master Plan §9.2, Condition S5-1)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")

    # Silent mode (PREREGISTRATION section 6, T-Q): model outputs go to a shadow store that no clinician-facing
    # route can read. Server-side only: no request field, header or query parameter can change it.
    SILENT_MODE: bool = os.getenv("VIGIL_SILENT_MODE", "false").lower() in ("true", "1", "yes")
    SILENT_SHADOW_DATABASE_URL: str = os.getenv("VIGIL_SILENT_SHADOW_DATABASE_URL", "")

    # G-09: OpenTelemetry is off by default; set VIGIL_OTEL_ENABLED=true to install tracing hooks.
    # G-09: /metrics needs this bearer token; with no token it is disabled (403) in every profile.
    METRICS_TOKEN: str = os.getenv("VIGIL_METRICS_TOKEN", "")
    OTEL_ENABLED: bool = os.getenv("VIGIL_OTEL_ENABLED", "false").lower() in ("true", "1", "yes")

    # Disclaimer text required on API root
    DISCLAIMER: str = (
        "Vigil is a research prototype and decision-support aid. It is not a medical device, "
        "does not diagnose or treat any condition, and must not replace the judgement of a qualified clinician."
    )

    def model_post_init(self, __context) -> None:
        if self.SILENT_MODE:
            if not self.SILENT_SHADOW_DATABASE_URL:
                raise ValueError(
                    "VIGIL_SILENT_MODE is on but VIGIL_SILENT_SHADOW_DATABASE_URL is not set; "
                    "silent mode fails closed instead of writing model outputs to the main database."
                )
            if self.SILENT_SHADOW_DATABASE_URL == self.DATABASE_URL:
                raise ValueError(
                    "VIGIL_SILENT_SHADOW_DATABASE_URL must differ from DATABASE_URL: the shadow store "
                    "must be a separate database."
                )
        if self.ENVIRONMENT != "local":
            self.REQUIRE_AUTH = True
            if (
                not self.JWT_SECRET_KEY
                or self.JWT_SECRET_KEY == DEFAULT_INSECURE_SECRET
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    f"In environment '{self.ENVIRONMENT}', JWT_SECRET_KEY must be explicitly set to a "
                    f"secure secret (>= 32 chars) and cannot match the known default development secret."
                )
        else:
            if not self.JWT_SECRET_KEY:
                self.JWT_SECRET_KEY = DEFAULT_INSECURE_SECRET


settings = Settings()
