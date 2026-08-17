"""
Configuration management for Al Astoora Document Collector Agent.
Loads settings from environment variables or .env file.
"""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable bindings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Meta WhatsApp Cloud API
    WHATSAPP_TOKEN: str = "EAAStEGDoJOYBR6eSp1ZAu8IxU86MbIQX6SkHOY5SDQtNvUaph2yUFtCZAgiz0ZBZCn2r7japgrLSMEps2QcU1S2lNerokp1RZBzpFXxP3zA2b34jJz7lwVezhE60TZCEZAsWmXdtguJKwo4e5j6kyqr1kjTgRZCvWZC05IdHm8EqYhxSHMcsktK8wFJuNvi0bgBa34wZDZD"
    WHATSAPP_PHONE_NUMBER_ID: str = "1113443245192571"
    BOT_PHONE_NUMBER: str = "919289581053"
    WEBHOOK_VERIFY_TOKEN: str = "al_astoora_secure_verify_token_2026"

    # Google Cloud Platform
    GCP_PROJECT_ID: str = "project-080b5971-eb4b-4d2b-a4c"
    GCP_LOCATION: str = "asia-south1"
    GCS_BUCKET_NAME: str = "al-astoora-documents"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # Model & AI Configuration
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_LOCATION: str = "us-central1"

    # App Environment
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8080


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
