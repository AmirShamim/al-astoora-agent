"""
FastAPI Router for Meta WhatsApp Cloud API Webhook Endpoints.
Handles GET verification handshake and POST incoming message dispatching.
"""

import logging
from typing import Dict, Any, Optional, Callable, Awaitable
from fastapi import APIRouter, Request, Response, Query, BackgroundTasks, status

from app.config import get_settings
from app.module_a.filters import is_valid_message_event, is_self_reply
from app.module_a.parser import parse_webhook_payload, ParsedMessage
from app.module_b.whatsapp_sender import send_text_message

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Webhook"])

# Message handler callback registry (allows Module B / main app to inject agent processing)
_message_handler: Optional[Callable[[ParsedMessage], Awaitable[None]]] = None


def register_message_handler(handler: Callable[[ParsedMessage], Awaitable[None]]) -> None:
    """Registers the async agent callback function to handle parsed WhatsApp messages."""
    global _message_handler
    _message_handler = handler


async def _default_fallback_processor(message: ParsedMessage) -> None:
    """
    Default handler used during Phase 1 testing before the full Gemini agent is attached.
    Confirms message receipt with a polite acknowledgment.
    """
    logger.info(
        f"[Phase 1 Hardcoded Handler] Received message from {message.profile_name} ({message.sender_phone}): "
        f"type={message.message_type}, content='{message.message_content}'"
    )
    # In Phase 1, send hardcoded reply if credentials configured
    settings = get_settings()
    if settings.WHATSAPP_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID:
        ack_text = f"Hello {message.profile_name}! Al Astoora Document Collector received your {message.message_type} message."
        await send_text_message(message.sender_phone, ack_text)


@router.get("/webhook", summary="WhatsApp Webhook Verification")
async def verify_webhook(
    mode: Optional[str] = Query(None, alias="hub.mode"),
    token: Optional[str] = Query(None, alias="hub.verify_token"),
    challenge: Optional[str] = Query(None, alias="hub.challenge"),
) -> Response:
    """
    Meta WhatsApp Cloud API Webhook verification handshake endpoint.
    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge.
    """
    settings = get_settings()

    if mode == "subscribe" and token == settings.WEBHOOK_VERIFY_TOKEN:
        logger.info("WhatsApp webhook challenge verification succeeded.")
        return Response(content=str(challenge or ""), media_type="text/plain", status_code=status.HTTP_200_OK)

    logger.warning(f"WhatsApp webhook verification failed. Received mode={mode}, token={token}")
    return Response(content="Verification failed", media_type="text/plain", status_code=status.HTTP_403_FORBIDDEN)


@router.post("/webhook", summary="WhatsApp Webhook Event Receiver")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Receives incoming WhatsApp webhook events (messages, status updates).
    Filters out noise, prevents self-reply loops, parses the message,
    and delegates processing asynchronously while returning 200 OK immediately.
    """
    settings = get_settings()

    try:
        payload = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse incoming webhook JSON: {e}")
        return {"status": "invalid_json"}

    # 1. Filter: Check if this is a genuine user message event
    if not is_valid_message_event(payload):
        logger.debug("Filtered out non-message webhook event (status update or receipt).")
        return {"status": "ignored_non_message"}

    # 2. Parse: Convert raw JSON into standard ParsedMessage dataclass
    parsed = parse_webhook_payload(payload)
    if not parsed:
        logger.warning("Failed to extract ParsedMessage from payload.")
        return {"status": "parse_failed"}

    # 3. Filter: Prevent infinite self-reply loops
    if is_self_reply(parsed.sender_phone, settings.BOT_PHONE_NUMBER):
        logger.info(f"Filtered out self-reply message from bot number ({parsed.sender_phone}).")
        return {"status": "ignored_self_reply"}

    logger.info(f"Incoming message from {parsed.profile_name} ({parsed.sender_phone}) [type: {parsed.message_type}]")

    # 4. Asynchronous Handoff: Process via registered agent or fallback in background
    handler = _message_handler or _default_fallback_processor
    background_tasks.add_task(handler, parsed)

    return {"status": "received"}
