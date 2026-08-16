"""
Module A: Webhook + Message Router
Handles incoming Meta WhatsApp Cloud API webhooks, filters noise, parses payloads,
and converts raw webhook events into clean, strongly typed ParsedMessage objects.
"""

from app.module_a.parser import ParsedMessage, parse_webhook_payload
from app.module_a.filters import is_valid_message_event, is_self_reply
from app.module_a.router import router as webhook_router

__all__ = [
    "ParsedMessage",
    "parse_webhook_payload",
    "is_valid_message_event",
    "is_self_reply",
    "webhook_router",
]
