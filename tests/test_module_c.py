"""
Unit Tests for Module C (Firestore State Manager).
Tests leads, clients, document intake state tracking, and booking management using AsyncClient mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.module_c.firestore_client import (
    get_firestore_client,
    set_firestore_client,
    close_firestore_client,
)
from app.module_c.leads import capture_lead, get_lead_by_phone
from app.module_c.clients import (
    get_or_create_client,
    check_intake_status,
    get_client,
    _get_required_documents_for_service,
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


# ==============================================================================
# Helper Mock Classes for Async Firestore
# ==============================================================================

class AsyncIter:
    """Helper to mock async generator streams in Firestore."""
    def __init__(self, items):
        self.items = items

    def __aiter__(self):
        self.iter = iter(self.items)
        return self

    async def __anext__(self):
        try:
            return next(self.iter)
        except StopIteration:
            raise StopAsyncIteration


# ==============================================================================
# 1. Firestore Client Initialization Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_firestore_client_singleton_and_override():
    """Verify singleton getter and custom client override."""
    mock_db = MagicMock()
    set_firestore_client(mock_db)
    assert get_firestore_client() is mock_db

    await close_firestore_client()
    # After close, client reference is reset
    assert get_firestore_client() is not mock_db


# ==============================================================================
# 2. Leads Management Tests (app/module_c/leads.py)
# ==============================================================================

@pytest.mark.asyncio
async def test_capture_lead_new_success():
    """Capturing a new lead creates a Firestore document and returns success."""
    mock_db = MagicMock()
    mock_leads_col = MagicMock()
    mock_query = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "lead_doc_123"
    mock_doc_ref.set = AsyncMock()

    # Empty stream -> lead does not exist
    mock_query.stream.return_value = AsyncIter([])
    mock_leads_col.where.return_value.limit.return_value = mock_query
    mock_leads_col.document.return_value = mock_doc_ref
    mock_db.collection.return_value = mock_leads_col

    set_firestore_client(mock_db)

    result = await capture_lead(
        name="Ahmed Al-Rashid",
        phone="6591234567",
        interest="Singapore company registration",
    )

    assert result["success"] is True
    assert result["already_captured"] is False
    assert result["lead_id"] == "lead_doc_123"
    mock_doc_ref.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_capture_lead_duplicate_detected():
    """Duplicate lead with existing phone number returns already_captured=True."""
    mock_db = MagicMock()
    mock_leads_col = MagicMock()
    mock_query = MagicMock()

    mock_existing_doc = MagicMock()
    mock_existing_doc.id = "existing_lead_456"

    # Stream returns an existing document
    mock_query.stream.return_value = AsyncIter([mock_existing_doc])
    mock_leads_col.where.return_value.limit.return_value = mock_query
    mock_db.collection.return_value = mock_leads_col

    set_firestore_client(mock_db)

    result = await capture_lead(
        name="Ahmed Al-Rashid",
        phone="6591234567",
        interest="Singapore company registration",
    )

    assert result["success"] is True
    assert result["already_captured"] is True
    assert result["lead_id"] == "existing_lead_456"


@pytest.mark.asyncio
async def test_capture_lead_handles_exception():
    """Catches exceptions and returns success=False with database unavailable error."""
    mock_db = MagicMock()
    mock_db.collection.side_effect = RuntimeError("Firestore connection timed out")

    set_firestore_client(mock_db)

    result = await capture_lead("Ahmed", "6591234567", "Consulting")
    assert result["success"] is False
    assert "Database unavailable" in result["error"]


@pytest.mark.asyncio
async def test_get_lead_by_phone():
    """Retrieves an existing lead record by phone number."""
    mock_db = MagicMock()
    mock_leads_col = MagicMock()
    mock_query = MagicMock()

    mock_doc = MagicMock()
    mock_doc.id = "lead_789"
    mock_doc.to_dict.return_value = {
        "name": "Sarah Lee",
        "phone": "6598765432",
        "interest": "Accounting",
    }

    mock_query.stream.return_value = AsyncIter([mock_doc])
    mock_leads_col.where.return_value.limit.return_value = mock_query
    mock_db.collection.return_value = mock_leads_col

    set_firestore_client(mock_db)

    result = await get_lead_by_phone("6598765432")
    assert result["success"] is True
    assert result["lead"]["name"] == "Sarah Lee"
    assert result["lead"]["id"] == "lead_789"


# ==============================================================================
# 3. Client & Intake Tracking Tests (app/module_c/clients.py)
# ==============================================================================

@pytest.mark.asyncio
async def test_get_or_create_client_new():
    """Creates a new client record and initializes subcollection documents."""
    mock_db = MagicMock()
    mock_clients_col = MagicMock()
    mock_client_ref = MagicMock()
    mock_client_snap = MagicMock()
    mock_client_snap.exists = False
    mock_client_ref.get = AsyncMock(return_value=mock_client_snap)
    mock_client_ref.set = AsyncMock()

    mock_docs_subcol = MagicMock()
    mock_doc_entry_ref = MagicMock()
    mock_doc_entry_ref.set = AsyncMock()
    mock_docs_subcol.document.return_value = mock_doc_entry_ref
    mock_client_ref.collection.return_value = mock_docs_subcol

    mock_clients_col.document.return_value = mock_client_ref

    # Template mock
    mock_templates_col = MagicMock()
    mock_template_ref = MagicMock()
    mock_template_snap = MagicMock()
    mock_template_snap.exists = True
    mock_template_snap.to_dict.return_value = {
        "service_name": "SG Registration",
        "required_documents": ["passport", "proof_of_address"],
    }
    mock_template_ref.get = AsyncMock(return_value=mock_template_snap)
    mock_templates_col.document.return_value = mock_template_ref

    def collection_side_effect(col_name):
        if col_name == "clients":
            return mock_clients_col
        if col_name == "intake_templates":
            return mock_templates_col
        return MagicMock()

    mock_db.collection.side_effect = collection_side_effect
    set_firestore_client(mock_db)

    result = await get_or_create_client(
        phone="6591234567",
        name="Ahmed Al-Rashid",
        service_type="sg_company_registration",
    )

    assert result["success"] is True
    assert result["is_new"] is True
    assert len(result["documents"]) == 2
    assert result["documents"][0]["doc_type"] == "passport"
    assert result["documents"][0]["status"] == "pending"
    mock_client_ref.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_client_existing():
    """Retrieves an existing client and their document subcollection."""
    mock_db = MagicMock()
    mock_clients_col = MagicMock()
    mock_client_ref = MagicMock()
    mock_client_snap = MagicMock()
    mock_client_snap.exists = True
    mock_client_snap.to_dict.return_value = {
        "name": "Ahmed Al-Rashid",
        "phone": "6591234567",
        "service_type": "sg_company_registration",
        "onboarding_status": "in_progress",
    }
    mock_client_ref.get = AsyncMock(return_value=mock_client_snap)

    mock_doc_snap = MagicMock()
    mock_doc_snap.to_dict.return_value = {
        "doc_type": "passport",
        "status": "validated",
    }

    mock_docs_subcol = MagicMock()
    mock_docs_subcol.stream.return_value = AsyncIter([mock_doc_snap])
    mock_client_ref.collection.return_value = mock_docs_subcol
    mock_clients_col.document.return_value = mock_client_ref
    mock_db.collection.return_value = mock_clients_col

    set_firestore_client(mock_db)

    result = await get_or_create_client(
        phone="6591234567",
        name="Ahmed Al-Rashid",
        service_type="sg_company_registration",
    )

    assert result["success"] is True
    assert result["is_new"] is False
    assert result["client"]["name"] == "Ahmed Al-Rashid"
    assert len(result["documents"]) == 1
    assert result["documents"][0]["status"] == "validated"


@pytest.mark.asyncio
async def test_check_intake_status():
    """Checks completion calculation with validated, pending, submitted, and rejected documents."""
    mock_db = MagicMock()
    mock_clients_col = MagicMock()
    mock_client_ref = MagicMock()
    mock_client_snap = MagicMock()
    mock_client_snap.exists = True
    mock_client_snap.to_dict.return_value = {
        "name": "Ahmed Al-Rashid",
        "phone": "6591234567",
        "service_type": "sg_company_registration",
        "documents_required": 3,
        "onboarding_status": "in_progress",
    }
    mock_client_ref.get = AsyncMock(return_value=mock_client_snap)

    doc1 = MagicMock()
    doc1.to_dict.return_value = {"doc_type": "passport", "status": "validated"}
    doc2 = MagicMock()
    doc2.to_dict.return_value = {"doc_type": "proof_of_address", "status": "rejected", "rejection_reason": "Expired"}
    doc3 = MagicMock()
    doc3.to_dict.return_value = {"doc_type": "director_resolution", "status": "pending"}

    mock_docs_subcol = MagicMock()
    mock_docs_subcol.stream.return_value = AsyncIter([doc1, doc2, doc3])
    mock_client_ref.collection.return_value = mock_docs_subcol
    mock_clients_col.document.return_value = mock_client_ref
    mock_db.collection.return_value = mock_clients_col

    set_firestore_client(mock_db)

    result = await check_intake_status("6591234567")

    assert result["success"] is True
    assert result["total_required"] == 3
    assert result["received"] == 1
    assert result["validated"] == ["passport"]
    assert result["pending"] == ["director_resolution"]
    assert len(result["rejected"]) == 1
    assert result["rejected"][0]["rejection_reason"] == "Expired"
    assert result["complete"] is False


# ==============================================================================
# 4. Document State Management Tests (app/module_c/documents.py)
# ==============================================================================

@pytest.mark.asyncio
async def test_update_document_status_to_validated_completes_intake():
    """When all required documents become validated, onboarding_status updates to complete."""
    mock_db = MagicMock()
    mock_clients_col = MagicMock()
    mock_client_ref = MagicMock()
    mock_client_snap = MagicMock()
    mock_client_snap.exists = True
    mock_client_snap.to_dict.return_value = {
        "name": "Ahmed",
        "documents_required": 2,
        "onboarding_status": "in_progress",
    }
    mock_client_ref.get = AsyncMock(return_value=mock_client_snap)
    mock_client_ref.update = AsyncMock()

    mock_doc_ref = MagicMock()
    mock_doc_snap = MagicMock()
    mock_doc_snap.exists = True
    mock_doc_snap.to_dict.return_value = {"attempts": 1}
    mock_doc_ref.get = AsyncMock(return_value=mock_doc_snap)
    mock_doc_ref.set = AsyncMock()

    mock_docs_subcol = MagicMock()
    mock_docs_subcol.document.return_value = mock_doc_ref

    # Subcollection after update: 2 validated docs
    doc1 = MagicMock()
    doc1.to_dict.return_value = {"doc_type": "passport", "status": "validated"}
    doc2 = MagicMock()
    doc2.to_dict.return_value = {"doc_type": "proof_of_address", "status": "validated"}
    mock_docs_subcol.stream.return_value = AsyncIter([doc1, doc2])

    mock_client_ref.collection.return_value = mock_docs_subcol
    mock_clients_col.document.return_value = mock_client_ref
    mock_db.collection.return_value = mock_clients_col

    set_firestore_client(mock_db)

    result = await update_document_status(
        phone="6591234567",
        doc_type="proof_of_address",
        status="validated",
        file_url="gs://al-astoora-documents/clients/6591234567/proof_of_address/sample.pdf",
    )

    assert result["success"] is True
    assert result["status"] == "validated"
    assert result["documents_received"] == 2
    assert result["documents_required"] == 2
    assert result["is_complete"] is True
    assert result["onboarding_status"] == "complete"
    assert result["remaining_docs"] == []

    mock_doc_ref.set.assert_awaited_once()
    mock_client_ref.update.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_document_status_client_not_found():
    """Updating a document for a nonexistent client returns success=False."""
    mock_db = MagicMock()
    mock_clients_col = MagicMock()
    mock_client_ref = MagicMock()
    mock_client_snap = MagicMock()
    mock_client_snap.exists = False
    mock_client_ref.get = AsyncMock(return_value=mock_client_snap)
    mock_clients_col.document.return_value = mock_client_ref
    mock_db.collection.return_value = mock_clients_col

    set_firestore_client(mock_db)

    result = await update_document_status("9999999999", "passport", "validated")
    assert result["success"] is False
    assert "Client not found" in result["error"]


# ==============================================================================
# 5. Booking Management Tests (app/module_c/bookings.py)
# ==============================================================================

@pytest.mark.asyncio
async def test_check_available_slots_filters_booked():
    """Available slots are computed by subtracting confirmed bookings from default slots."""
    mock_db = MagicMock()
    mock_bookings_col = MagicMock()
    mock_query = MagicMock()

    booked_doc = MagicMock()
    booked_doc.to_dict.return_value = {"time": "10:00", "status": "confirmed"}

    mock_query.stream.return_value = AsyncIter([booked_doc])
    mock_bookings_col.where.return_value.where.return_value = mock_query
    mock_db.collection.return_value = mock_bookings_col

    set_firestore_client(mock_db)

    result = await check_available_slots("2026-08-20")

    assert result["success"] is True
    assert result["date"] == "2026-08-20"
    assert "10:00" not in result["available_slots"]
    assert "10:00" in result["booked_slots"]
    assert "09:00" in result["available_slots"]
    assert len(result["available_slots"]) == len(DEFAULT_SLOTS) - 1


@pytest.mark.asyncio
async def test_book_appointment_success():
    """Booking an available slot creates a confirmed booking document."""
    mock_db = MagicMock()
    mock_bookings_col = MagicMock()
    mock_collision_query = MagicMock()

    # Slot is open
    mock_collision_query.stream.return_value = AsyncIter([])
    (
        mock_bookings_col
        .where.return_value
        .where.return_value
        .where.return_value
        .limit.return_value
    ) = mock_collision_query

    mock_doc_ref = MagicMock()
    mock_doc_ref.id = "booking_abc_123"
    mock_doc_ref.set = AsyncMock()
    mock_bookings_col.document.return_value = mock_doc_ref
    mock_db.collection.return_value = mock_bookings_col

    set_firestore_client(mock_db)

    result = await book_appointment(
        date="2026-08-20",
        time="14:00",
        name="Ahmed Al-Rashid",
        phone="6591234567",
    )

    assert result["success"] is True
    assert result["booking_id"] == "booking_abc_123"
    assert result["status"] == "confirmed"
    assert "Ahmed Al-Rashid" in result["confirmation"]
    mock_doc_ref.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_book_appointment_collision():
    """Attempting to book an already booked slot returns slot_taken=True."""
    mock_db = MagicMock()
    mock_bookings_col = MagicMock()
    mock_collision_query = MagicMock()

    existing_booking = MagicMock()
    existing_booking.id = "existing_booking_123"

    mock_collision_query.stream.return_value = AsyncIter([existing_booking])
    (
        mock_bookings_col
        .where.return_value
        .where.return_value
        .where.return_value
        .limit.return_value
    ) = mock_collision_query

    mock_db.collection.return_value = mock_bookings_col
    set_firestore_client(mock_db)

    result = await book_appointment(
        date="2026-08-20",
        time="14:00",
        name="Ahmed Al-Rashid",
        phone="6591234567",
    )

    assert result["success"] is False
    assert result["slot_taken"] is True
    assert "already booked" in result["error"]


@pytest.mark.asyncio
async def test_cancel_appointment():
    """Cancelling a booking updates status to cancelled."""
    mock_db = MagicMock()
    mock_bookings_col = MagicMock()
    mock_doc_ref = MagicMock()
    mock_doc_snap = MagicMock()
    mock_doc_snap.exists = True
    mock_doc_ref.get = AsyncMock(return_value=mock_doc_snap)
    mock_doc_ref.update = AsyncMock()
    mock_bookings_col.document.return_value = mock_doc_ref
    mock_db.collection.return_value = mock_bookings_col

    set_firestore_client(mock_db)

    result = await cancel_appointment("booking_abc_123")
    assert result["success"] is True
    assert result["status"] == "cancelled"
    mock_doc_ref.update.assert_awaited_once()
