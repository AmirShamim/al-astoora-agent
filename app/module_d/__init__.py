"""
Module D: Document Validation Engine.
Handles downloading WhatsApp media, storing documents in Google Cloud Storage,
and inspecting documents with Gemini 3.7 Flash multimodal vision.
"""

from app.module_d.media_downloader import (
    download_media,
)
from app.module_d.storage import (
    upload_to_storage,
    get_storage_client,
    set_storage_client,
    close_storage_client,
)
from app.module_d.validator import (
    validate_document,
    analyze_document_with_gemini,
    get_genai_client,
    set_genai_client,
    close_genai_client,
)

__all__ = [
    "download_media",
    "upload_to_storage",
    "get_storage_client",
    "set_storage_client",
    "close_storage_client",
    "validate_document",
    "analyze_document_with_gemini",
    "get_genai_client",
    "set_genai_client",
    "close_genai_client",
]
