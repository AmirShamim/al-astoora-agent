"""
Webhook Filters for Noise Reduction and Infinite Loop Prevention.
"""

import re
from typing import Dict, Any, Optional


def normalize_phone_number(phone: Optional[str]) -> str:
    """Strips all non-digit characters from a phone number string."""
    if not phone:
        return ""
    return re.sub(r"\D", "", phone)


def is_valid_message_event(payload: Dict[str, Any]) -> bool:
    """
    Checks if the webhook payload represents an actual incoming user message,
    as opposed to status updates (sent, delivered, read) or system notifications.
    """
    if not isinstance(payload, dict):
        return False

    entries = payload.get("entry", [])
    if not entries or not isinstance(entries, list):
        return False

    changes = entries[0].get("changes", [])
    if not changes or not isinstance(changes, list):
        return False

    value = changes[0].get("value", {})
    if not isinstance(value, dict):
        return False

    # Status updates contain a 'statuses' key instead of 'messages'
    if "statuses" in value and "messages" not in value:
        return False

    messages = value.get("messages", [])
    if not messages or not isinstance(messages, list) or len(messages) == 0:
        return False

    return True


def is_self_reply(sender_phone: str, bot_phone_number: str) -> bool:
    """
    Prevents self-reply infinite loops by checking if the incoming message
    originated from the bot's own configured WhatsApp phone number.
    """
    normalized_sender = normalize_phone_number(sender_phone)
    normalized_bot = normalize_phone_number(bot_phone_number)

    if not normalized_sender or not normalized_bot:
        return False

    return normalized_sender == normalized_bot
