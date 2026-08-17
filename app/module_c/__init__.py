"""
Module C: Firestore State Manager.
Handles all state persistence, client records, document intake tracking, and appointments.
"""

from app.module_c.firestore_client import (
    get_firestore_client,
    set_firestore_client,
    close_firestore_client,
)
from app.module_c.leads import (
    capture_lead,
    get_lead_by_phone,
)
from app.module_c.clients import (
    get_or_create_client,
    check_intake_status,
    get_client,
    DEFAULT_INTAKE_TEMPLATES,
)
from app.module_c.documents import (
    update_document_status,
    get_document,
    list_documents,
)
from app.module_c.bookings import (
    check_available_slots,
    book_appointment,
    cancel_appointment,
    get_client_bookings,
    DEFAULT_SLOTS,
)
from app.module_c.sessions import (
    get_session_history,
    append_session_message,
    clear_session,
)

__all__ = [
    "get_firestore_client",
    "set_firestore_client",
    "close_firestore_client",
    "capture_lead",
    "get_lead_by_phone",
    "get_or_create_client",
    "check_intake_status",
    "get_client",
    "DEFAULT_INTAKE_TEMPLATES",
    "update_document_status",
    "get_document",
    "list_documents",
    "check_available_slots",
    "book_appointment",
    "cancel_appointment",
    "get_client_bookings",
    "DEFAULT_SLOTS",
    "get_session_history",
    "append_session_message",
    "clear_session",
]
