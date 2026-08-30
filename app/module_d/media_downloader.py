"""
Module D: WhatsApp Media Downloader.
Handles fetching raw media bytes (images, PDFs) from Meta WhatsApp Cloud API.
"""

import logging
from typing import Dict, Any, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v26.0"

_MEDIA_HTTP_CLIENT: Optional[httpx.AsyncClient] = None


def get_media_http_client() -> httpx.AsyncClient:
    """
    Returns a shared, pooled AsyncClient with keep-alive connections.
    Reuses TCP/TLS connections to graph.facebook.com, reducing download latency by 200-300ms.
    """
    global _MEDIA_HTTP_CLIENT
    if _MEDIA_HTTP_CLIENT is None or _MEDIA_HTTP_CLIENT.is_closed:
        _MEDIA_HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=15,
                max_connections=30,
                keepalive_expiry=600.0,
            ),
            follow_redirects=True,
        )
    return _MEDIA_HTTP_CLIENT


def _get_media_meta_url(media_id: str) -> str:
    """Returns the WhatsApp Graph API URL for querying media metadata."""
    settings = get_settings()
    api_version = getattr(settings, "GRAPH_API_VERSION", GRAPH_API_VERSION) or GRAPH_API_VERSION
    return f"https://graph.facebook.com/{api_version}/{media_id}"


def _get_auth_headers() -> Dict[str, str]:
    """Returns standard authorization headers for WhatsApp Graph API."""
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "User-Agent": "AlAstooraAgent/1.0",
    }


async def download_media(media_id: str, timeout: float = 30.0) -> Dict[str, Any]:
    """
    Downloads media file (image, PDF document) from WhatsApp Cloud API.

    Step 1: Queries Graph API for media URL and metadata.
    Step 2: Downloads raw file bytes from the media URL using Bearer auth.

    Args:
        media_id: The WhatsApp media ID from the incoming webhook payload.
        timeout: HTTP request timeout in seconds.

    Returns:
        Dict with:
            - success (bool): True if download succeeded, False otherwise.
            - file_bytes (bytes, optional): Raw binary content.
            - mime_type (str, optional): Content MIME type (e.g., 'image/jpeg', 'application/pdf').
            - file_size (int, optional): Size of downloaded file in bytes.
            - media_id (str): The requested media ID.
            - error (str, optional): Human-readable error message on failure.
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN:
        logger.error("WHATSAPP_TOKEN is missing in configuration. Cannot download media.")
        return {
            "success": False,
            "error": "WhatsApp credentials not configured",
            "media_id": media_id,
        }

    if not media_id or not str(media_id).strip():
        return {
            "success": False,
            "error": "Invalid or empty media ID provided",
            "media_id": media_id,
        }

    headers = _get_auth_headers()

    try:
        client = get_media_http_client()
        # Step 1: Query media metadata to retrieve direct download URL
        meta_url = _get_media_meta_url(media_id)
        meta_response = await client.get(meta_url, headers=headers)

        if meta_response.status_code != 200:
            logger.error(
                "WhatsApp Media Meta API error [%d] for media_id %s: %s",
                meta_response.status_code,
                media_id,
                meta_response.text,
            )
            return {
                "success": False,
                "error": f"WhatsApp media metadata lookup failed [{meta_response.status_code}]",
                "media_id": media_id,
            }

        meta_data = meta_response.json()
        download_url = meta_data.get("url")
        mime_type = meta_data.get("mime_type", "application/octet-stream")

        if not download_url:
            logger.error("No download URL returned for media_id %s: %s", media_id, meta_data)
            return {
                "success": False,
                "error": "No download URL returned by WhatsApp",
                "media_id": media_id,
            }

        # Step 2: Download raw media bytes from direct URL
        media_response = await client.get(download_url, headers=headers)

        if media_response.status_code != 200:
            logger.error(
                "WhatsApp Media Download failed [%d] for media_id %s: %s",
                media_response.status_code,
                media_id,
                media_response.text,
            )
            return {
                "success": False,
                "error": f"WhatsApp media file download failed [{media_response.status_code}]",
                "media_id": media_id,
            }

        file_bytes = media_response.content
        # Use content-type from response if available and more specific
        content_type_header = media_response.headers.get("content-type")
        if content_type_header and "application/octet-stream" not in content_type_header:
            mime_type = content_type_header.split(";")[0].strip()

        logger.info(
            "Successfully downloaded media %s (%d bytes, %s)",
            media_id,
            len(file_bytes),
            mime_type,
        )

        return {
            "success": True,
            "file_bytes": file_bytes,
            "mime_type": mime_type,
            "file_size": len(file_bytes),
            "media_id": media_id,
        }

    except httpx.TimeoutException as e:
        logger.error("Timeout downloading WhatsApp media %s: %s", media_id, e)
        return {
            "success": False,
            "error": "Media download timed out",
            "media_id": media_id,
        }
    except Exception as e:
        logger.exception("Unexpected error downloading WhatsApp media %s: %s", media_id, e)
        return {
            "success": False,
            "error": f"Unexpected download error: {str(e)}",
            "media_id": media_id,
        }
