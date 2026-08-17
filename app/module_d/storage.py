"""
Module D: Google Cloud Storage Client & Upload Handler.
Handles uploading validated and incoming client documents to GCS bucket for record-keeping.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
import re
from typing import Dict, Any, Optional
from google.cloud import storage

from app.config import get_settings

logger = logging.getLogger(__name__)

_storage_client: Optional[storage.Client] = None

# Extension mapping by MIME type
MIME_EXTENSION_MAP = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


def get_storage_client() -> storage.Client:
    """
    Returns the singleton Storage Client for Google Cloud Storage.
    Automatically uses project ID from configuration.
    """
    global _storage_client
    if _storage_client is None:
        settings = get_settings()
        logger.info("Initializing Google Cloud Storage Client for project: %s", settings.GCP_PROJECT_ID)
        _storage_client = storage.Client(project=settings.GCP_PROJECT_ID)
    return _storage_client


def set_storage_client(client: Optional[storage.Client]) -> None:
    """
    Sets or overrides the Storage Client instance (useful for unit testing / mocking).
    """
    global _storage_client
    _storage_client = client


def close_storage_client() -> None:
    """
    Resets the storage client instance reference.
    """
    global _storage_client
    if _storage_client is not None:
        try:
            if hasattr(_storage_client, "close"):
                _storage_client.close()
        except Exception as e:
            logger.warning("Error closing Storage client: %s", e)
        finally:
            _storage_client = None


def _sanitize_string(val: str, fallback: str = "unknown") -> str:
    """Sanitizes a string to contain only safe alphanumeric and underscore characters."""
    if not val:
        return fallback
    cleaned = re.sub(r"[^\w\-.]", "_", str(val).strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or fallback


def _generate_blob_name(
    client_phone: str,
    doc_type: str,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> str:
    """
    Constructs the standard GCS blob path:
    clients/{client_phone}/{doc_type}/{timestamp}_{filename}
    """
    # Clean phone (remove non-digits, e.g. +65 9123-4567 -> 6591234567)
    clean_phone = re.sub(r"\D", "", client_phone) or _sanitize_string(client_phone, "unknown_phone")
    clean_doc_type = _sanitize_string(doc_type, "misc_document")

    # Generate timestamp prefix
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    # Clean or infer filename
    if filename and filename.strip():
        base_name = os.path.basename(filename.strip())
        clean_filename = _sanitize_string(base_name, "document")
    else:
        ext = MIME_EXTENSION_MAP.get((mime_type or "").lower(), ".bin")
        clean_filename = f"document{ext}"

    return f"clients/{clean_phone}/{clean_doc_type}/{timestamp}_{clean_filename}"


def _sync_upload(
    client: storage.Client,
    bucket_name: str,
    blob_name: str,
    file_bytes: bytes,
    mime_type: Optional[str] = None,
) -> str:
    """Synchronous upload execution to be run in a worker thread."""
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(
        file_bytes,
        content_type=mime_type or "application/octet-stream",
    )
    return f"gs://{bucket_name}/{blob_name}"


async def upload_to_storage(
    file_bytes: bytes,
    client_phone: str,
    doc_type: str,
    filename: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Uploads document binary bytes to Google Cloud Storage.

    Destination format:
    gs://{GCS_BUCKET_NAME}/clients/{client_phone}/{doc_type}/{timestamp}_{filename}

    Args:
        file_bytes: Raw binary bytes of the file.
        client_phone: Target client's phone number for path isolation.
        doc_type: Document category/type (e.g., 'passport', 'proof_of_address').
        filename: Optional original filename.
        mime_type: Optional MIME type for Content-Type header.

    Returns:
        Dict with:
            - success (bool): True if upload succeeded, False otherwise.
            - file_url (str, optional): GCS URI (gs://bucket/path).
            - blob_name (str, optional): Relative blob path within the bucket.
            - bucket (str, optional): GCS bucket name.
            - size_bytes (int, optional): Size of the uploaded file.
            - error (str, optional): Error message if upload failed.
    """
    if not file_bytes:
        return {
            "success": False,
            "error": "Cannot upload empty or null file bytes",
            "file_url": None,
        }

    settings = get_settings()
    bucket_name = settings.GCS_BUCKET_NAME

    try:
        client = get_storage_client()
        blob_name = _generate_blob_name(
            client_phone=client_phone,
            doc_type=doc_type,
            filename=filename,
            mime_type=mime_type,
        )

        logger.info("Uploading %d bytes to gs://%s/%s", len(file_bytes), bucket_name, blob_name)

        # Offload sync GCS SDK call to thread pool so it does not block the async event loop
        file_url = await asyncio.to_thread(
            _sync_upload,
            client,
            bucket_name,
            blob_name,
            file_bytes,
            mime_type,
        )

        return {
            "success": True,
            "file_url": file_url,
            "blob_name": blob_name,
            "bucket": bucket_name,
            "size_bytes": len(file_bytes),
        }

    except Exception as e:
        logger.exception("Failed to upload document to Cloud Storage: %s", e)
        return {
            "success": False,
            "error": str(e),
            "file_url": None,
        }
