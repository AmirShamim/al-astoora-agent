"""
Unit Tests for Module B (ADK Agent Orchestrator & WhatsApp Communicator).
Tests system prompt contents, ADK tool functions, agent orchestration,
message dispatching, and fallback error handling.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.module_a.parser import ParsedMessage
from app.module_b.system_prompt import SYSTEM_PROMPT
from app.module_b.tools import (
    ALL_TOOLS,
    capture_lead,
    get_or_create_client,
    check_intake_status,
    update_document_status,
    validate_document,
    check_available_slots,
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
    _build_user_event_prompt,
    _execute_agent_turn,
)


# ==============================================================================
# 1. System Prompt Compliance Tests
# ==============================================================================

def test_system_prompt_identity_and_services():
    """System prompt must define Al Astoora identity, services, and document rules."""
    assert "Al Astoora" in SYSTEM_PROMPT
    assert "sg_company_registration" in SYSTEM_PROMPT
    assert "accounting_services" in SYSTEM_PROMPT
    assert "immigration_consulting" in SYSTEM_PROMPT
    assert "passport" in SYSTEM_PROMPT
    assert "proof_of_address" in SYSTEM_PROMPT
    assert "director_resolution" in SYSTEM_PROMPT
    assert "trade_license" in SYSTEM_PROMPT
    assert "bank_statement" in SYSTEM_PROMPT
    assert "tax_assessment" in SYSTEM_PROMPT
    assert "resume" in SYSTEM_PROMPT
    assert "employment_contract" in SYSTEM_PROMPT


def test_system_prompt_whatsapp_constraints():
    """System prompt must enforce WhatsApp constraints: no markdown, English, brevity."""
    assert "NO MARKDOWN" in SYSTEM_PROMPT or "Never use markdown" in SYSTEM_PROMPT
    assert "English" in SYSTEM_PROMPT
    assert "concise" in SYSTEM_PROMPT.lower() or "2 to 3 sentences" in SYSTEM_PROMPT


def test_system_prompt_tool_instructions():
    """System prompt must reference all tool functions."""
    for tool_fn in ALL_TOOLS:
        assert tool_fn.__name__ in SYSTEM_PROMPT


# ==============================================================================
# 2. ADK Tool Functions Tests (Module C & D Bridges)
# ==============================================================================

@pytest.mark.asyncio
async def test_tool_capture_lead_success():
    """Test capture_lead tool forwards correctly and returns success string."""
    with patch("app.module_c.leads.capture_lead", new_callable=AsyncMock) as mock_capture:
        mock_capture.return_value = {"success": True, "message": "Lead captured successfully", "lead_id": "lead_123"}

        res = await capture_lead(name="Fatima Zahra", phone="6591234567", interest="Singapore company registration")
        assert "Success: Lead captured successfully" in res
        mock_capture.assert_called_once_with(name="Fatima Zahra", phone="6591234567", interest="Singapore company registration")


@pytest.mark.asyncio
async def test_tool_capture_lead_duplicate_or_notice():
    """Test capture_lead tool handles already existing leads cleanly."""
    with patch("app.module_c.leads.capture_lead", new_callable=AsyncMock) as mock_capture:
        mock_capture.return_value = {"success": False, "message": "Lead already captured for this phone number"}

        res = await capture_lead(name="Fatima Zahra", phone="6591234567", interest="Singapore company registration")
        assert "Notice: Lead already captured" in res


@pytest.mark.asyncio
async def test_tool_get_or_create_client():
    """Test get_or_create_client tool formats client record and checklist."""
    mock_data = {
        "success": True,
        "client": {
            "name": "Ahmed Al-Rashid",
            "phone": "6591234567",
            "service_type": "sg_company_registration",
            "onboarding_status": "in_progress",
        },
        "required_documents": [
            {"doc_type": "passport", "status": "pending"},
            {"doc_type": "proof_of_address", "status": "validated"},
        ],
    }
    with patch("app.module_c.clients.get_or_create_client", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = mock_data

        res = await get_or_create_client(phone="6591234567", name="Ahmed Al-Rashid", service_type="sg_company_registration")
        assert "Ahmed Al-Rashid" in res
        assert "sg_company_registration" in res
        assert "passport: pending" in res
        assert "proof_of_address: validated" in res


@pytest.mark.asyncio
async def test_tool_check_intake_status():
    """Test check_intake_status tool formats progress and remaining files."""
    mock_status = {
        "success": True,
        "total_required": 3,
        "documents_received": 1,
        "pending_documents": ["director_resolution"],
        "rejected_documents": [{"doc_type": "passport", "rejection_reason": "blurry photo"}],
        "is_complete": False,
    }
    with patch("app.module_c.clients.check_intake_status", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = mock_status

        res = await check_intake_status(phone="6591234567")
        assert "1/3 documents validated" in res
        assert "director_resolution" in res
        assert "blurry photo" in res


@pytest.mark.asyncio
async def test_tool_update_document_status():
    """Test update_document_status tool updates document and returns remaining status."""
    mock_res = {
        "success": True,
        "remaining_documents": ["director_resolution"],
        "onboarding_complete": False,
    }
    with patch("app.module_c.documents.update_document_status", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = mock_res

        res = await update_document_status(
            phone="6591234567",
            doc_type="passport",
            status="validated",
            file_url="gs://bucket/passport.jpg",
        )
        assert "marked as 'validated'" in res
        assert "director_resolution" in res


@pytest.mark.asyncio
async def test_tool_validate_document_success():
    """Test validate_document tool executes validation and persists validated state in Firestore."""
    mock_val = {
        "success": True,
        "document_type": "passport",
        "extracted_fields": {"name": "Ahmed Al-Rashid", "passport_number": "E1234567"},
        "is_valid": True,
        "issues": [],
        "client_message": "Thank you! Your passport has been successfully verified.",
        "file_url": "gs://al-astoora-documents/passport.jpg",
    }
    with patch("app.module_d.validator.validate_document", new_callable=AsyncMock) as mock_val_fn:
        with patch("app.module_c.documents.update_document_status", new_callable=AsyncMock) as mock_update_fn:
            mock_val_fn.return_value = mock_val
            mock_update_fn.return_value = {"success": True}

            res = await validate_document(
                media_id="media_123",
                expected_doc_type="passport",
                client_phone="6591234567",
                original_filename="passport.jpg",
            )
            parsed = json.loads(res)
            assert parsed["is_valid"] is True
            assert "passport" in parsed["document_type"]
            mock_update_fn.assert_called_once_with(
                phone="6591234567",
                doc_type="passport",
                status="validated",
                file_url="gs://al-astoora-documents/passport.jpg",
                rejection_reason=None,
            )


@pytest.mark.asyncio
async def test_tool_validate_document_rejected():
    """Test validate_document tool saves rejection reason if document is invalid."""
    mock_val = {
        "success": True,
        "document_type": "passport",
        "extracted_fields": {},
        "is_valid": False,
        "issues": ["expired passport date 2024-01-01"],
        "client_message": "Your passport appears to be expired. Please send a valid passport.",
        "file_url": "gs://al-astoora-documents/passport_expired.jpg",
    }
    with patch("app.module_d.validator.validate_document", new_callable=AsyncMock) as mock_val_fn:
        with patch("app.module_c.documents.update_document_status", new_callable=AsyncMock) as mock_update_fn:
            mock_val_fn.return_value = mock_val
            mock_update_fn.return_value = {"success": True}

            res = await validate_document(
                media_id="media_999",
                expected_doc_type="passport",
                client_phone="6591234567",
            )
            parsed = json.loads(res)
            assert parsed["is_valid"] is False
            mock_update_fn.assert_called_once_with(
                phone="6591234567",
                doc_type="passport",
                status="rejected",
                file_url="gs://al-astoora-documents/passport_expired.jpg",
                rejection_reason="expired passport date 2024-01-01",
            )


@pytest.mark.asyncio
async def test_tool_check_available_slots():
    """Test check_available_slots tool returns formatted slots."""
    with patch("app.module_c.bookings.check_available_slots", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {"success": True, "date": "2026-08-20", "available_slots": ["10:00", "11:00", "14:00"]}

        res = await check_available_slots("2026-08-20")
        assert "Available slots for 2026-08-20" in res
        assert "10:00, 11:00, 14:00" in res


@pytest.mark.asyncio
async def test_tool_book_appointment():
    """Test book_appointment tool confirms booking details."""
    with patch("app.module_c.bookings.book_appointment", new_callable=AsyncMock) as mock_fn:
        mock_fn.return_value = {"success": True, "booking_id": "bk_999"}

        res = await book_appointment(date="2026-08-20", time="14:00", name="Ahmed", phone="6591234567")
        assert "Appointment confirmed for Ahmed on 2026-08-20 at 14:00" in res
        assert "bk_999" in res


@pytest.mark.asyncio
async def test_tool_send_whatsapp_text():
    """Test send_whatsapp_text tool forwards to whatsapp_sender."""
    with patch("app.module_b.whatsapp_sender.send_text_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}

        res = await send_whatsapp_text("6591234567", "Hello from Al Astoora")
        assert "Message sent successfully" in res
        mock_send.assert_called_once_with(recipient_phone="6591234567", text="Hello from Al Astoora")


@pytest.mark.asyncio
async def test_tool_send_whatsapp_buttons():
    """Test send_whatsapp_buttons tool forwards buttons payload."""
    with patch("app.module_b.whatsapp_sender.send_button_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}

        buttons = [{"id": "btn_sg", "title": "SG Company"}]
        res = await send_whatsapp_buttons("6591234567", "Choose service:", buttons)
        assert "Interactive button message sent successfully" in res
        mock_send.assert_called_once_with(
            recipient_phone="6591234567",
            body_text="Choose service:",
            buttons=buttons,
            header_text=None,
            footer_text=None,
        )


@pytest.mark.asyncio
async def test_tool_send_whatsapp_list():
    """Test send_whatsapp_list tool forwards list payload."""
    with patch("app.module_b.whatsapp_sender.send_list_message", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"success": True}

        sections = [{"title": "Options", "rows": [{"id": "opt_1", "title": "Service 1"}]}]
        res = await send_whatsapp_list("6591234567", "Select:", "View Menu", sections)
        assert "Interactive list message sent successfully" in res
        mock_send.assert_called_once_with(
            recipient_phone="6591234567",
            body_text="Select:",
            button_text="View Menu",
            sections=sections,
            title=None,
            footer_text=None,
        )


# ==============================================================================
# 3. Agent Lifecycle & Prompt Construction Tests
# ==============================================================================

def test_agent_initialization_and_singleton():
    """Test create_adk_agent, get_agent, and set_agent lifecycle."""
    agent = create_adk_agent()
    assert agent is not None
    assert getattr(agent, "name", "") == "al_astoora_agent"
    assert getattr(agent, "instruction", "") == SYSTEM_PROMPT
    assert len(getattr(agent, "tools", [])) == 10

    set_agent(agent)
    assert get_agent() is agent
    set_agent(None)


def test_build_user_event_prompt():
    """Test format of the context prompt passed to the agent."""
    msg = ParsedMessage(
        sender_phone="6591234567",
        profile_name="Tariq Mansoor",
        message_type="image",
        message_content="",
        media_id="media_img_999",
        media_filename="passport_scan.jpg",
        raw_timestamp="1723852800",
        raw_message_id="wamid.123",
        metadata={"caption": "Here is my passport photo"},
    )
    prompt = _build_user_event_prompt(msg)
    assert "Sender Phone: 6591234567" in prompt
    assert "Sender Profile Name: Tariq Mansoor" in prompt
    assert "Media ID: media_img_999" in prompt
    assert "passport_scan.jpg" in prompt
    assert "validate_document" in prompt


# ==============================================================================
# 4. Agent Orchestrator & Message Processing (`process_message`) Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_process_message_text_reply_delivery():
    """When agent returns text response, process_message sends it via WhatsApp sender."""
    msg = ParsedMessage(
        sender_phone="6591234567",
        profile_name="Zayd",
        message_type="text",
        message_content="Hello, I want to incorporate a company in Singapore.",
        media_id=None,
        media_filename=None,
        raw_timestamp="1723852800",
        raw_message_id="wamid.text1",
        metadata={},
    )

    # Mock agent that returns a string response
    mock_agent = MagicMock()
    mock_agent.run = MagicMock(return_value="Hello Zayd! We would be delighted to help you incorporate in Singapore.")

    with patch("app.module_b.agent.get_agent", return_value=mock_agent):
        with patch("app.module_b.agent.send_text_message", new_callable=AsyncMock) as mock_send:
            await process_message(msg)
            mock_send.assert_called_once_with(
                recipient_phone="6591234567",
                text="Hello Zayd! We would be delighted to help you incorporate in Singapore.",
            )


@pytest.mark.asyncio
async def test_process_message_strips_markdown():
    """Agent response should have markdown asterisks removed before sending."""
    msg = ParsedMessage(
        sender_phone="6591234567",
        profile_name="Zayd",
        message_type="text",
        message_content="What do I need?",
        media_id=None,
        media_filename=None,
        raw_timestamp="1723852800",
        raw_message_id="wamid.text2",
        metadata={},
    )

    mock_agent = MagicMock()
    mock_agent.run = MagicMock(return_value="Please provide your **passport** and *proof of address*.")

    with patch("app.module_b.agent.get_agent", return_value=mock_agent):
        with patch("app.module_b.agent.send_text_message", new_callable=AsyncMock) as mock_send:
            await process_message(msg)
            mock_send.assert_called_once_with(
                recipient_phone="6591234567",
                text="Please provide your passport and proof of address.",
            )


@pytest.mark.asyncio
async def test_process_message_error_fallback():
    """If agent execution crashes, a polite fallback message is sent and no exception raised."""
    msg = ParsedMessage(
        sender_phone="6591234567",
        profile_name="Amina",
        message_type="text",
        message_content="Hi",
        media_id=None,
        media_filename=None,
        raw_timestamp="1723852800",
        raw_message_id="wamid.err1",
        metadata={},
    )

    mock_agent = MagicMock()
    mock_agent.run = MagicMock(side_effect=RuntimeError("AI backend connection timed out"))

    with patch("app.module_b.agent.get_agent", return_value=mock_agent):
        with patch("app.module_b.agent.send_text_message", new_callable=AsyncMock) as mock_send:
            # Should not raise exception
            await process_message(msg)
            mock_send.assert_called_once()
            called_text = mock_send.call_args[1]["text"]
            assert "Amina" in called_text
            assert "technical delay" in called_text or "experiencing" in called_text


# ==============================================================================
# 5. Module A Router Hook Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_router_dispatches_to_registered_handler():
    """Verify that posting to /webhook dispatches to the registered agent message handler."""
    from fastapi.testclient import TestClient
    from app.main import app
    from app.module_a.router import register_message_handler

    client = TestClient(app)

    # Valid incoming WhatsApp text message payload
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "1113443245192571",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "919289581053",
                                "phone_number_id": "1113443245192571",
                            },
                            "contacts": [{"profile": {"name": "Test Client"}, "wa_id": "6591234567"}],
                            "messages": [
                                {
                                    "from": "6591234567",
                                    "id": "wamid.test_dispatch",
                                    "timestamp": "1723852800",
                                    "text": {"body": "Hello agent!"},
                                    "type": "text",
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }

    mock_handler = AsyncMock()
    register_message_handler(mock_handler)

    response = client.post("/webhook", json=payload)
    assert response.status_code == 200
    assert response.json() == {"status": "received"}

    # Verify our handler was invoked
    mock_handler.assert_called_once()
    called_msg: ParsedMessage = mock_handler.call_args[0][0]
    assert called_msg.sender_phone == "6591234567"
    assert called_msg.message_content == "Hello agent!"
    assert called_msg.profile_name == "Test Client"
