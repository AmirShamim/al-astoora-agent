"""
Module B: Gemini Agent (Orchestrator) & WhatsApp Communicator.
Provides the Google ADK Agent, system prompt, tool definitions, and message processing pipeline.
"""

from app.module_b.whatsapp_sender import (
    send_text_message,
    send_button_message,
    send_list_message,
    mark_message_as_read,
)
from app.module_b.system_prompt import (
    SYSTEM_PROMPT,
)
from app.module_b.tools import (
    ALL_TOOLS,
    capture_lead,
    get_or_create_client,
    check_intake_status,
    update_document_status,
    validate_document,
    check_available_slots,
    send_interactive_booking_slots,
    book_appointment,
    send_whatsapp_text,
    send_whatsapp_buttons,
    send_whatsapp_list,
)
from app.module_b.agent import (
    create_adk_agent,
    get_agent,
    set_agent,
    process_message,
    root_agent,
)

__all__ = [
    "send_text_message",
    "send_button_message",
    "send_list_message",
    "mark_message_as_read",
    "SYSTEM_PROMPT",
    "ALL_TOOLS",
    "capture_lead",
    "get_or_create_client",
    "check_intake_status",
    "update_document_status",
    "validate_document",
    "check_available_slots",
    "send_interactive_booking_slots",
    "book_appointment",
    "send_whatsapp_text",
    "send_whatsapp_buttons",
    "send_whatsapp_list",
    "create_adk_agent",
    "get_agent",
    "set_agent",
    "process_message",
    "root_agent",
]
