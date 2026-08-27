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

    # Meta WhatsApp Cloud API (Loaded from .env)
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    BOT_PHONE_NUMBER: str = ""
    WEBHOOK_VERIFY_TOKEN: str = ""
    GRAPH_API_VERSION: str = "v26.0"

    # Google Cloud Platform (Loaded from .env)
    GCP_PROJECT_ID: str = ""
    GCP_LOCATION: str = "asia-south1"
    GCS_BUCKET_NAME: str = "al-astoora-documents"
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = None

    # Model & AI Configuration
    GEMINI_MODEL: str = "gemini-3.7-flash"
    GEMINI_LOCATION: str = "global"     # "global" required for Gemini 3.6 / 3.x models on Vertex AI
    GEMINI_THINKING_LEVEL: str = "low"  # "low" or "off" for fast WhatsApp perception
    GEMINI_THINKING_BUDGET: int = 0     # 0 tokens for no-thinking / minimal latency

    # Google Calendar Integration (Optional Sync)
    GOOGLE_CALENDAR_ID: Optional[str] = None
    DEFAULT_TIMEZONE: str = "Asia/Singapore"

    # App Environment
    APP_ENV: str = "production"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8080


@lru_cache()
def get_settings() -> Settings:
    """Singleton getter for application settings."""
    return Settings()
