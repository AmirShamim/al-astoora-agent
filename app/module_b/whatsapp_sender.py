"""
Module B: WhatsApp Cloud API Message Sender.
Provides asynchronous functions to send text, interactive buttons, and interactive list messages.
"""

import logging
from typing import Dict, Any, List, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

GRAPH_API_VERSION = "v20.0"


def _get_api_url() -> str:
    settings = get_settings()
    return f"https://graph.facebook.com/{GRAPH_API_VERSION}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"


def _get_headers() -> Dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
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

    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                _get_api_url(),
                headers=_get_headers(),
                json=payload,
            )
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _get_api_url(),
                headers=_get_headers(),
                json=payload,
            )
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
    
    Args:
        recipient_phone: Target phone number.
        body_text: Main message text.
        buttons: List of dicts with keys 'id' and 'title' (e.g. [{'id': 'opt_1', 'title': 'Yes'}])
        header_text: Optional header text.
        footer_text: Optional footer text.
    """
    settings = get_settings()
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("WhatsApp credentials not configured; skipping real API call.")
        return {"success": False, "error": "Credentials missing", "mock": True}

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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _get_api_url(),
                headers=_get_headers(),
                json=payload,
            )
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

    interactive_obj: Dict[str, Any] = {
        "type": "list",
        "body": {"text": body_text[:1024]},
        "action": {
            "button": button_text[:20],
            "sections": sections,
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
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                _get_api_url(),
                headers=_get_headers(),
                json=payload,
            )
            response_json = response.json()
            if response.status_code in (200, 201):
                return {"success": True, "data": response_json}
            else:
                logger.error(f"WhatsApp List API Error [{response.status_code}]: {response_json}")
                return {"success": False, "status_code": response.status_code, "error": response_json}
    except Exception as e:
        logger.exception(f"Failed to send list message: {e}")
        return {"success": False, "error": str(e)}
