"""
Unit Tests for Module A (Webhook Router, Filters, and Payload Parser).
Verifies that all WhatsApp Cloud API payloads are filtered and parsed correctly.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.module_a.parser import parse_webhook_payload, ParsedMessage
from app.module_a.filters import is_valid_message_event, is_self_reply, normalize_phone_number
from app.module_a.router import register_message_handler

PAYLOADS_DIR = Path(__file__).parent / "sample_payloads"


def load_payload(filename: str) -> dict:
    """Helper to load sample JSON payload files."""
    filepath = PAYLOADS_DIR / filename
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


client = TestClient(app)


# ==============================================================================
# 1. Verification Handshake Tests (GET /webhook)
# ==============================================================================

def test_webhook_verification_success():
    """Valid verification challenge should return challenge string with 200 OK."""
    settings = get_settings()
    challenge_token = "987654321_challenge_token"
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": settings.WEBHOOK_VERIFY_TOKEN,
            "hub.challenge": challenge_token,
        },
    )
    assert response.status_code == 200
    assert response.text == challenge_token


def test_webhook_verification_invalid_token():
    """Invalid verify token must be rejected with 403 Forbidden."""
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong_invalid_secret_token",
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403
    assert "failed" in response.text.lower()


def test_webhook_verification_invalid_mode():
    """Missing or incorrect mode must be rejected with 403."""
    settings = get_settings()
    response = client.get(
        "/webhook",
        params={
            "hub.mode": "unsubscribe",
            "hub.verify_token": settings.WEBHOOK_VERIFY_TOKEN,
            "hub.challenge": "12345",
        },
    )
    assert response.status_code == 403


# ==============================================================================
# 2. Filter Tests (is_valid_message_event, is_self_reply)
# ==============================================================================

def test_filter_validates_real_messages():
    """Valid messages return True for is_valid_message_event."""
    text_payload = load_payload("text_message.json")
    assert is_valid_message_event(text_payload) is True


def test_filter_rejects_status_updates():
    """Status updates (delivered/read/sent receipts) return False."""
    status_payload = load_payload("status_update.json")
    assert is_valid_message_event(status_payload) is False


def test_filter_rejects_empty_or_malformed_payloads():
    """Empty dictionaries, None, or garbage payloads are safely rejected."""
    assert is_valid_message_event({}) is False
    assert is_valid_message_event({"entry": []}) is False
    assert is_valid_message_event({"entry": [{"changes": []}]}) is False


def test_phone_normalization_and_self_reply():
    """Self-reply loop prevention normalizes phone numbers correctly."""
    assert normalize_phone_number("+65 9123-4567") == "6591234567"
    assert normalize_phone_number("6591234567") == "6591234567"
    assert normalize_phone_number("") == ""

    bot_number = "+65-9123-4567"
    # Matches normalized bot number
    assert is_self_reply("6591234567", bot_number) is True
    assert is_self_reply("+65 9123 4567", bot_number) is True
    # Different number
    assert is_self_reply("6598889999", bot_number) is False


# ==============================================================================
# 3. Payload Parsing Tests (parse_webhook_payload)
# ==============================================================================

def test_parse_text_message():
    """Parses text message payload into ParsedMessage with body content."""
    payload = load_payload("text_message.json")
    parsed = parse_webhook_payload(payload)

    assert isinstance(parsed, ParsedMessage)
    assert parsed.sender_phone == "6591234567"
    assert parsed.profile_name == "Ahmed Al-Rashid"
    assert parsed.message_type == "text"
    assert parsed.message_content == "Hi, I need to register a company in Singapore"
    assert parsed.media_id is None
    assert parsed.media_filename is None


def test_parse_button_reply():
    """Parses interactive button reply and extracts button ID."""
    payload = load_payload("button_reply.json")
    parsed = parse_webhook_payload(payload)

    assert isinstance(parsed, ParsedMessage)
    assert parsed.sender_phone == "6591234567"
    assert parsed.message_type == "interactive"
    assert parsed.message_content == "btn_sg_incorporation"
    assert parsed.metadata.get("interactive_type") == "button_reply"
    assert parsed.metadata.get("title") == "SG Incorporation"


def test_parse_list_reply():
    """Parses interactive list reply and extracts list item ID and title."""
    payload = load_payload("list_reply.json")
    parsed = parse_webhook_payload(payload)

    assert isinstance(parsed, ParsedMessage)
    assert parsed.sender_phone == "6591234567"
    assert parsed.message_type == "interactive"
    assert parsed.message_content == "service_accounting_annual"
    assert parsed.metadata.get("interactive_type") == "list_reply"
    assert parsed.metadata.get("title") == "Annual Accounting"


def test_parse_image_message():
    """Parses image message extracting media_id and optional caption."""
    payload = load_payload("image_message.json")
    parsed = parse_webhook_payload(payload)

    assert isinstance(parsed, ParsedMessage)
    assert parsed.sender_phone == "6591234567"
    assert parsed.message_type == "image"
    assert parsed.media_id == "media_img_9988776655"
    assert parsed.message_content == "Here is my passport photo"


def test_parse_document_message():
    """Parses document PDF upload extracting media_id and original filename."""
    payload = load_payload("document_message.json")
    parsed = parse_webhook_payload(payload)

    assert isinstance(parsed, ParsedMessage)
    assert parsed.sender_phone == "6591234567"
    assert parsed.message_type == "document"
    assert parsed.media_id == "media_doc_1122334455"
    assert parsed.media_filename == "Director_Resolution_Signed.pdf"


# ==============================================================================
# 4. End-to-End POST /webhook Flow & Handler Dispatching
# ==============================================================================

def test_post_webhook_status_update_ignored():
    """Status updates sent to POST /webhook are ignored immediately with 200 OK."""
    status_payload = load_payload("status_update.json")
    response = client.post("/webhook", json=status_payload)
    assert response.status_code == 200
    assert response.json() == {"status": "ignored_non_message"}


def test_post_webhook_dispatches_message_handler():
    """Valid incoming message is acknowledged with 200 OK and passed to message handler."""
    received_messages = []

    async def custom_test_handler(msg: ParsedMessage):
        received_messages.append(msg)

    # Register test handler
    register_message_handler(custom_test_handler)

    text_payload = load_payload("text_message.json")
    response = client.post("/webhook", json=text_payload)

    assert response.status_code == 200
    assert response.json() == {"status": "received"}
    assert len(received_messages) == 1
    assert received_messages[0].sender_phone == "6591234567"
    assert received_messages[0].message_content == "Hi, I need to register a company in Singapore"
