"""Configuration settings for Vigil Clinical Decision Support API.

Adheres to MASTER_PLAN.md §9.2, §9.3, and §11.
Remediates Defect A4 (personal machine paths), Defect A5 (wildcard CORS),
and Defect A7 (hardcoded alert thresholds).
"""

import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Vigil"
    VERSION: str = "0.1.0-alpha"
    API_V1_STR: str = "/api/v1"

    # Environment profile: 'local', 'staging', or 'production'
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "local")

    # Database: Default to local SQLite relative path; no personal absolute paths (Defect A4)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./vigil_dev.db")

    # Clinical Alert Threshold (Defect A7)
    # Default demonstration threshold; replaced by conformal risk control operating point
    # in validated profiles per MASTER_PLAN §8.6.
    CLINICAL_ALERT_THRESHOLD: float = float(os.getenv("CLINICAL_ALERT_THRESHOLD", "0.75"))

    # CORS configuration: strict whitelist, NO wildcard '*' permitted (Defect A5)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    # Synthetic data labeling: all current data and mock profiles are synthetic (Principle 1)
    IS_SYNTHETIC_DATA: bool = True

    # JWT & Auth Security (Master Plan §9.2)
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "vigil-precision-oncology-secret-key-32bytes-min")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REQUIRE_AUTH: bool = os.getenv("REQUIRE_AUTH", "false").lower() in ("true", "1", "yes")

    # Disclaimer text required on API root
    DISCLAIMER: str = (
        "Vigil is a research prototype and decision-support aid. It is not a medical device, "
        "does not diagnose or treat any condition, and must not replace the judgement of a qualified clinician."
    )


settings = Settings()
