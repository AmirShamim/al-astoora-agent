"""
Module B: WhatsApp Cloud API Message Sender.
Provides asynchronous functions to send text, interactive buttons, interactive list messages,
and mark incoming messages as read (blue tick) using persistent Keep-Alive connection pooling.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v26.0"

_HTTP_CLIENT: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """
    Returns a shared, pooled AsyncClient with keep-alive connections.
    Reuses TCP/TLS connections to graph.facebook.com, reducing latency by 200-300ms per call.
    """
    global _HTTP_CLIENT
    if _HTTP_CLIENT is None or _HTTP_CLIENT.is_closed:
        _HTTP_CLIENT = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=50,
                keepalive_expiry=600.0,
            ),
        )
    return _HTTP_CLIENT


def _build_messages_url(phone_number_id: str) -> str:
    settings = get_settings()
    api_version = getattr(settings, "GRAPH_API_VERSION", GRAPH_API_VERSION) or GRAPH_API_VERSION
    return f"https://graph.facebook.com/{api_version}/{phone_number_id}/messages"


def _build_auth_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


async def mark_message_as_read(message_id: str) -> Dict[str, Any]:
    """
    Marks an incoming WhatsApp message as read (triggers blue tick on client's WhatsApp).
    
    Args:
        message_id: The unique WhatsApp message ID (e.g. wamid.HBgL...).

    Returns:
        Dict with success status and API response or error.
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured; skipping mark_message_as_read.")
        return {"success": False, "error": "Credentials missing", "mock": True}

    if not message_id:
        return {"success": False, "error": "Missing message_id"}

    url = _build_messages_url(settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = _build_auth_headers(settings.WHATSAPP_TOKEN)
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        client = get_http_client()
        response = await client.post(url, headers=headers, json=payload)
        response_json = response.json()
        if response.status_code in (200, 201):
            logger.info(f"Successfully marked message {message_id} as read (blue tick).")
            return {"success": True, "data": response_json}
        else:
            logger.warning(f"WhatsApp Read Receipt Error [{response.status_code}]: {response_json}")
            return {"success": False, "status_code": response.status_code, "error": response_json}
    except Exception as e:
        logger.exception(f"Failed to mark message {message_id} as read: {e}")
        return {"success": False, "error": str(e)}


async def send_text_message(
    recipient_phone: str,
    text: str,
    preview_url: bool = False,
) -> Dict[str, Any]:
    """
    Sends a plain text message to a WhatsApp user.
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured; skipping real API call.")
        return {"success": False, "error": "Credentials missing", "mock": True}

    url = _build_messages_url(settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = _build_auth_headers(settings.WHATSAPP_TOKEN)
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "text",
        "text": {
            "preview_url": preview_url,
            "body": text,
        },
    }

    try:
        client = get_http_client()
        response = await client.post(url, headers=headers, json=payload)
        response_json = response.json()
        if response.status_code in (200, 201):
            return {"success": True, "data": response_json}
        else:
            logger.error(f"WhatsApp API Error [{response.status_code}]: {response_json}")
            return {"success": False, "status_code": response.status_code, "error": response_json}
    except Exception as e:
        logger.exception(f"Failed to send WhatsApp text message to {recipient_phone}: {e}")
        return {"success": False, "error": str(e)}


async def send_button_message(
    recipient_phone: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends an interactive button message (max 3 buttons).
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured; skipping real API call.")
        return {"success": False, "error": "Credentials missing", "mock": True}

    url = _build_messages_url(settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = _build_auth_headers(settings.WHATSAPP_TOKEN)

    formatted_buttons = []
    for btn in buttons[:3]:  # WhatsApp maximum 3 buttons limit
        btn_id = btn.get("id", "")[:256]
        btn_title = btn.get("title", "")[:20]  # WhatsApp max button title length 20 chars
        formatted_buttons.append({
            "type": "reply",
            "reply": {
                "id": btn_id,
                "title": btn_title,
            },
        })

    interactive_obj: Dict[str, Any] = {
        "type": "button",
        "body": {"text": body_text[:1024]},
        "action": {"buttons": formatted_buttons},
    }

    if header_text:
        interactive_obj["header"] = {"type": "text", "text": header_text[:60]}
    if footer_text:
        interactive_obj["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "interactive",
        "interactive": interactive_obj,
    }

    try:
        client = get_http_client()
        response = await client.post(url, headers=headers, json=payload)
        response_json = response.json()
        if response.status_code in (200, 201):
            return {"success": True, "data": response_json}
        else:
            logger.error(f"WhatsApp Button API Error [{response.status_code}]: {response_json}")
            return {"success": False, "status_code": response.status_code, "error": response_json}
    except Exception as e:
        logger.exception(f"Failed to send button message: {e}")
        return {"success": False, "error": str(e)}


async def send_list_message(
    recipient_phone: str,
    body_text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    title: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends an interactive list message (up to 10 rows).
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured; skipping real API call.")
        return {"success": False, "error": "Credentials missing", "mock": True}

    url = _build_messages_url(settings.WHATSAPP_PHONE_NUMBER_ID)
    headers = _build_auth_headers(settings.WHATSAPP_TOKEN)

    # Sanitize and truncate sections to meet strict WhatsApp Graph API limits
    sanitized_sections = []
    total_rows = 0
    for sec in sections:
        sec_title = str(sec.get("title", "Options"))[:24]
        sec_rows = []
        for r in sec.get("rows", []):
            if total_rows >= 10:
                break
            row_dict = {
                "id": str(r.get("id", ""))[:200],
                "title": str(r.get("title", ""))[:24],
            }
            if r.get("description"):
                row_dict["description"] = str(r.get("description"))[:72]
            sec_rows.append(row_dict)
            total_rows += 1

        if sec_rows:
            sanitized_sections.append({
                "title": sec_title,
                "rows": sec_rows,
            })

    interactive_obj: Dict[str, Any] = {
        "type": "list",
        "body": {"text": body_text[:1024]},
        "action": {
            "button": button_text[:20],
            "sections": sanitized_sections,
        },
    }

    if title:
        interactive_obj["header"] = {"type": "text", "text": title[:60]}
    if footer_text:
        interactive_obj["footer"] = {"text": footer_text[:60]}

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_phone,
        "type": "interactive",
        "interactive": interactive_obj,
    }

    try:
        client = get_http_client()
        response = await client.post(url, headers=headers, json=payload)
        response_json = response.json()
        if response.status_code in (200, 201):
            return {"success": True, "data": response_json}
        else:
            logger.error(f"WhatsApp List API Error [{response.status_code}]: {response_json}")
            return {"success": False, "status_code": response.status_code, "error": response_json}
    except Exception as e:
        logger.exception(f"Failed to send list message: {e}")
        return {"success": False, "error": str(e)}
