"""Configuration settings for Sentinel Backend."""

import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sentinel"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////Users/gsanni/.gemini/antigravity/scratch/sentinel/sentinel-backend/sentinel.db",
    )

    # ML Artifacts directory
    ARTIFACTS_DIR: str = os.getenv(
        "ARTIFACTS_DIR",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "ml", "artifacts"),
    )

    # Clinical Alert Threshold
    CLINICAL_ALERT_THRESHOLD: float = 0.75

    # CORS configuration
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "*",
    ]


settings = Settings()
