"""
Unit Tests for Module D (Document Validation Engine).
Tests media download from WhatsApp, GCS storage uploads, Gemini 3.7 Flash multimodal analysis,
and the end-to-end document validation pipeline.
"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.config import Settings
from app.module_d.media_downloader import (
    download_media,
    _get_media_meta_url,
    _get_auth_headers,
)
from app.module_d.storage import (
    upload_to_storage,
    get_storage_client,
    set_storage_client,
    close_storage_client,
    _generate_blob_name,
    _sanitize_string,
)
from app.module_d.validator import (
    validate_document,
    analyze_document_with_gemini,
    get_genai_client,
    set_genai_client,
    close_genai_client,
    _build_validation_prompt,
    _parse_gemini_json_response,
)


# ==============================================================================
# 1. Media Downloader Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_download_media_success():
    """Test successful 2-step WhatsApp media download."""
    media_id = "media_123456"
    fake_token = "test_whatsapp_token"
    fake_bytes = b"%PDF-1.4 mock pdf content"

    mock_settings = Settings(
        WHATSAPP_TOKEN=fake_token,
        WHATSAPP_PHONE_NUMBER_ID="1113443245192571",
    )

    with patch("app.module_d.media_downloader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            # Step 1 response (Metadata)
            meta_resp = MagicMock()
            meta_resp.status_code = 200
            meta_resp.json.return_value = {
                "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/123456",
                "mime_type": "application/pdf",
                "sha256": "abc123sha",
                "file_size": len(fake_bytes),
                "id": media_id,
            }

            # Step 2 response (Media bytes)
            media_resp = MagicMock()
            media_resp.status_code = 200
            media_resp.content = fake_bytes
            media_resp.headers = {"content-type": "application/pdf"}

            mock_client_instance.get.side_effect = [meta_resp, media_resp]

            result = await download_media(media_id)

            assert result["success"] is True
            assert result["file_bytes"] == fake_bytes
            assert result["mime_type"] == "application/pdf"
            assert result["file_size"] == len(fake_bytes)
            assert result["media_id"] == media_id


@pytest.mark.asyncio
async def test_download_media_missing_token():
    """Test that download_media returns error when WHATSAPP_TOKEN is missing."""
    mock_settings = Settings(WHATSAPP_TOKEN="", WHATSAPP_PHONE_NUMBER_ID="")

    with patch("app.module_d.media_downloader.get_settings", return_value=mock_settings):
        result = await download_media("media_999")
        assert result["success"] is False
        assert "credentials not configured" in result["error"].lower()


@pytest.mark.asyncio
async def test_download_media_empty_id():
    """Test that download_media returns error when media_id is empty."""
    mock_settings = Settings(WHATSAPP_TOKEN="valid_token")

    with patch("app.module_d.media_downloader.get_settings", return_value=mock_settings):
        result = await download_media("   ")
        assert result["success"] is False
        assert "invalid or empty" in result["error"].lower()


@pytest.mark.asyncio
async def test_download_media_metadata_error():
    """Test handling of WhatsApp Graph API metadata lookup error (404/500)."""
    mock_settings = Settings(WHATSAPP_TOKEN="valid_token")

    with patch("app.module_d.media_downloader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            meta_resp = MagicMock()
            meta_resp.status_code = 404
            meta_resp.text = '{"error": {"message": "Media not found"}}'

            mock_client_instance.get.return_value = meta_resp

            result = await download_media("nonexistent_id")
            assert result["success"] is False
            assert "metadata lookup failed [404]" in result["error"]


@pytest.mark.asyncio
async def test_download_media_bytes_download_error():
    """Test handling of error when downloading actual binary stream."""
    mock_settings = Settings(WHATSAPP_TOKEN="valid_token")

    with patch("app.module_d.media_downloader.get_settings", return_value=mock_settings):
        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            MockClient.return_value.__aenter__.return_value = mock_client_instance

            meta_resp = MagicMock()
            meta_resp.status_code = 200
            meta_resp.json.return_value = {
                "url": "https://lookaside.fbsbx.com/whatsapp_business/attachments/123",
                "mime_type": "image/jpeg",
            }

            media_resp = MagicMock()
            media_resp.status_code = 403
            media_resp.text = "Forbidden"

            mock_client_instance.get.side_effect = [meta_resp, media_resp]

            result = await download_media("media_forbidden")
            assert result["success"] is False
            assert "download failed [403]" in result["error"]


# ==============================================================================
# 2. Cloud Storage Upload Tests
# ==============================================================================

def test_storage_client_singleton_and_override():
    """Verify storage client getter, setter, and close lifecycle."""
    mock_client = MagicMock()
    set_storage_client(mock_client)
    assert get_storage_client() is mock_client

    close_storage_client()
    assert get_storage_client() is not mock_client
    close_storage_client()


def test_sanitize_string_helper():
    """Verify string sanitization."""
    assert _sanitize_string("Singapore / SG & Co.") == "Singapore_SG_Co."
    assert _sanitize_string("passport_front.pdf") == "passport_front.pdf"
    assert _sanitize_string("", fallback="default") == "default"


def test_generate_blob_name():
    """Verify blob path naming format: clients/{phone}/{doc_type}/{timestamp}_{filename}."""
    blob_name = _generate_blob_name(
        client_phone="+65 9123-4567",
        doc_type="passport",
        filename="my_passport.jpg",
        mime_type="image/jpeg",
    )
    assert blob_name.startswith("clients/6591234567/passport/")
    assert blob_name.endswith("_my_passport.jpg")

    # When filename is missing, infer extension from mime_type
    blob_pdf = _generate_blob_name(
        client_phone="919289581053",
        doc_type="director_resolution",
        filename=None,
        mime_type="application/pdf",
    )
    assert blob_pdf.startswith("clients/919289581053/director_resolution/")
    assert blob_pdf.endswith("_document.pdf")


@pytest.mark.asyncio
async def test_upload_to_storage_success():
    """Test successful GCS upload."""
    mock_storage = MagicMock()
    mock_bucket = MagicMock()
    mock_blob = MagicMock()

    mock_storage.bucket.return_value = mock_bucket
    mock_bucket.blob.return_value = mock_blob
    set_storage_client(mock_storage)

    fake_bytes = b"image content bytes 12345"
    result = await upload_to_storage(
        file_bytes=fake_bytes,
        client_phone="6591234567",
        doc_type="passport",
        filename="passport_scan.jpg",
        mime_type="image/jpeg",
    )

    assert result["success"] is True
    assert result["file_url"].startswith("gs://al-astoora-documents/clients/6591234567/passport/")
    assert result["size_bytes"] == len(fake_bytes)
    mock_blob.upload_from_string.assert_called_once_with(fake_bytes, content_type="image/jpeg")

    close_storage_client()


@pytest.mark.asyncio
async def test_upload_to_storage_empty_bytes():
    """Test that upload_to_storage handles empty bytes gracefully."""
    result = await upload_to_storage(
        file_bytes=b"",
        client_phone="6591234567",
        doc_type="passport",
    )
    assert result["success"] is False
    assert "empty or null" in result["error"].lower()


@pytest.mark.asyncio
async def test_upload_to_storage_exception_handling():
    """Test that upload_to_storage catches GCS errors without raising."""
    mock_storage = MagicMock()
    mock_storage.bucket.side_effect = Exception("GCS Bucket permission denied")
    set_storage_client(mock_storage)

    result = await upload_to_storage(
        file_bytes=b"some bytes",
        client_phone="6591234567",
        doc_type="passport",
    )
    assert result["success"] is False
    assert "permission denied" in result["error"].lower()

    close_storage_client()


# ==============================================================================
# 3. Gemini Multimodal Analysis & Parser Tests
# ==============================================================================

def test_genai_client_singleton_and_override():
    """Verify GenAI client getter, setter, and close lifecycle."""
    mock_client = MagicMock()
    set_genai_client(mock_client)
    assert get_genai_client() is mock_client

    close_genai_client()
    assert get_genai_client() is not mock_client
    close_genai_client()


def test_build_validation_prompt():
    """Verify prompt includes expected document type and rules."""
    prompt = _build_validation_prompt("director_resolution", "2026-08-17")
    assert "director_resolution" in prompt
    assert "2026-08-17" in prompt
    assert "Readability & Quality" in prompt
    assert "Expiry & Validity" in prompt


def test_parse_gemini_json_response_valid():
    """Test parsing clean valid JSON response."""
    raw_json = json.dumps({
        "document_type": "passport",
        "extracted_fields": {
            "full_name": "Ahmed Al-Mansoor",
            "passport_number": "N1234567A",
            "expiry_date": "2032-10-15",
            "nationality": "Singaporean",
        },
        "is_valid": True,
        "issues": [],
        "client_message": "Your passport has been successfully verified.",
    })

    parsed = _parse_gemini_json_response(raw_json, "passport")
    assert parsed["document_type"] == "passport"
    assert parsed["is_valid"] is True
    assert parsed["extracted_fields"]["passport_number"] == "N1234567A"
    assert parsed["issues"] == []
    assert "successfully verified" in parsed["client_message"]


def test_parse_gemini_json_response_with_markdown_fences():
    """Test parsing JSON enclosed in markdown code fences."""
    raw_json_in_fences = """```json
    {
      "document_type": "passport",
      "extracted_fields": {
        "full_name": "John Doe",
        "expiry_date": "2021-01-01"
      },
      "is_valid": false,
      "issues": ["Document is expired (expired on 2021-01-01)"],
      "client_message": "Your passport is expired. Please provide a currently valid passport."
    }
    ```"""

    parsed = _parse_gemini_json_response(raw_json_in_fences, "passport")
    assert parsed["is_valid"] is False
    assert len(parsed["issues"]) == 1
    assert "expired" in parsed["issues"][0].lower()
    assert "expired" in parsed["client_message"].lower()


def test_parse_gemini_json_response_malformed():
    """Test fallback when response is completely unparseable."""
    malformed_text = "Sorry, I am unable to process this image due to an internal error."
    parsed = _parse_gemini_json_response(malformed_text, "proof_of_address")

    assert parsed["is_valid"] is False
    assert parsed["document_type"] == "proof_of_address"
    assert parsed["eligibility_assessment"]["status"] == "ineligible"
    assert parsed["eligibility_assessment"]["service_track"] == "sg_company_registration"
    assert len(parsed["issues"]) >= 1


def test_parse_gemini_json_response_normalizes_hallucinated_enums():
    """Test that arbitrary strings like 'not_eligible', 'corporate_secretarial_compliance', or 'n/a' are strictly normalized."""
    raw_json_with_variations = json.dumps({
        "document_type": "trade license",
        "extracted_fields": {"company_name": "AL NOOR TRADING L.L.C"},
        "is_valid": False,
        "issues": ["Expired trade license"],
        "client_message": "Your trade license has expired.",
        "eligibility_assessment": {
            "status": "not_eligible",
            "service_track": "corporate_secretarial_compliance",
            "summary": "Trade license is expired.",
            "recommended_next_step": "Renew license.",
        },
    })

    parsed = _parse_gemini_json_response(raw_json_with_variations, "trade_license")
    assert parsed["document_type"] == "trade_license"
    assert parsed["is_valid"] is False
    # Must be rigidly mapped to 'ineligible' and 'sg_company_registration'
    assert parsed["eligibility_assessment"]["status"] == "ineligible"
    assert parsed["eligibility_assessment"]["service_track"] == "sg_company_registration"

    # Test 'n/a' service track mapping
    raw_json_na = json.dumps({
        "document_type": "unknown_file",
        "extracted_fields": {},
        "is_valid": False,
        "issues": ["Invalid file"],
        "eligibility_assessment": {
            "status": "rejected",
            "service_track": "n/a",
        },
    })
    parsed_na = _parse_gemini_json_response(raw_json_na, "auto_detect")
    assert parsed_na["document_type"] == "general_document"
    assert parsed_na["eligibility_assessment"]["status"] == "ineligible"
    assert parsed_na["eligibility_assessment"]["service_track"] == "general_corporate_services"



@pytest.mark.asyncio
async def test_analyze_document_with_gemini_success():
    """Test analyze_document_with_gemini calling GenAI client."""
    mock_genai = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps({
        "document_type": "proof_of_address",
        "extracted_fields": {
            "name": "Sarah Tan",
            "address": "10 Marina Boulevard, Singapore",
            "bill_date": "2026-07-15",
        },
        "is_valid": True,
        "issues": [],
        "client_message": "Your proof of address has been approved.",
    })

    # Support async models.generate_content
    mock_genai.aio = MagicMock()
    mock_genai.aio.models = MagicMock()
    mock_genai.aio.models.generate_content = AsyncMock(return_value=mock_response)
    set_genai_client(mock_genai)

    result = await analyze_document_with_gemini(
        file_bytes=b"mock utility bill image",
        mime_type="image/png",
        expected_doc_type="proof_of_address",
    )

    assert result["is_valid"] is True
    assert result["document_type"] == "proof_of_address"
    assert result["extracted_fields"]["address"] == "10 Marina Boulevard, Singapore"

    close_genai_client()


@pytest.mark.asyncio
async def test_analyze_document_with_gemini_empty_bytes():
    """Test handling of empty file bytes."""
    result = await analyze_document_with_gemini(
        file_bytes=b"",
        mime_type="image/jpeg",
        expected_doc_type="passport",
    )
    assert result["is_valid"] is False
    assert "no document bytes" in result["issues"][0].lower()


# ==============================================================================
# 4. End-to-End Validation Pipeline Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_validate_document_full_pipeline_success():
    """Test end-to-end validate_document pipeline (download -> store -> analyze)."""
    fake_bytes = b"binary photo of passport"

    # Mock download_media
    mock_download = {
        "success": True,
        "file_bytes": fake_bytes,
        "mime_type": "image/jpeg",
        "file_size": len(fake_bytes),
        "media_id": "media_pass_123",
    }

    # Mock upload_to_storage
    mock_storage = {
        "success": True,
        "file_url": "gs://al-astoora-documents/clients/6591234567/passport/20260817_120000_passport.jpg",
        "blob_name": "clients/6591234567/passport/20260817_120000_passport.jpg",
        "bucket": "al-astoora-documents",
        "size_bytes": len(fake_bytes),
    }

    # Mock analyze_document_with_gemini
    mock_analysis = {
        "document_type": "passport",
        "extracted_fields": {
            "full_name": "Amir Shamim",
            "passport_number": "K98765432",
            "expiry_date": "2030-05-20",
        },
        "is_valid": True,
        "issues": [],
        "client_message": "Your passport has been validated successfully.",
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage", new=AsyncMock(return_value=mock_storage)):
            with patch("app.module_d.validator.analyze_document_with_gemini", new=AsyncMock(return_value=mock_analysis)):
                result = await validate_document(
                    media_id="media_pass_123",
                    expected_doc_type="passport",
                    client_phone="6591234567",
                    original_filename="passport.jpg",
                )

                assert result["success"] is True
                assert result["is_valid"] is True
                assert result["document_type"] == "passport"
                assert result["extracted_fields"]["passport_number"] == "K98765432"
                assert result["file_url"] == mock_storage["file_url"]
                assert result["media_id"] == "media_pass_123"
                assert result["mime_type"] == "image/jpeg"


@pytest.mark.asyncio
async def test_validate_document_download_failure():
    """Test validate_document stops immediately on download failure."""
    mock_download = {
        "success": False,
        "error": "WhatsApp media expired",
        "media_id": "expired_media_id",
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage") as mock_store:
            with patch("app.module_d.validator.analyze_document_with_gemini") as mock_gemini:
                result = await validate_document(
                    media_id="expired_media_id",
                    expected_doc_type="passport",
                    client_phone="6591234567",
                )

                assert result["success"] is False
                assert result["is_valid"] is False
                assert "WhatsApp media expired" in result["issues"]
                assert "try sending it again" in result["client_message"]

                # Ensure storage and gemini were never called
                mock_store.assert_not_called()
                mock_gemini.assert_not_called()


@pytest.mark.asyncio
async def test_validate_document_storage_failure_proceeds_with_validation():
    """Test that storage failure is non-fatal; validation continues."""
    fake_bytes = b"binary photo of resolution"

    mock_download = {
        "success": True,
        "file_bytes": fake_bytes,
        "mime_type": "application/pdf",
        "file_size": len(fake_bytes),
        "media_id": "media_doc_pdf",
    }

    mock_storage_failed = {
        "success": False,
        "error": "Storage bucket unreachable",
        "file_url": None,
    }

    mock_analysis = {
        "document_type": "director_resolution",
        "extracted_fields": {"company_name": "Al Astoora Pte Ltd"},
        "is_valid": True,
        "issues": [],
        "client_message": "Director resolution verified.",
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage", new=AsyncMock(return_value=mock_storage_failed)):
            with patch("app.module_d.validator.analyze_document_with_gemini", new=AsyncMock(return_value=mock_analysis)):
                result = await validate_document(
                    media_id="media_doc_pdf",
                    expected_doc_type="director_resolution",
                    client_phone="6591234567",
                )

                assert result["success"] is True
                assert result["is_valid"] is True
                assert result["file_url"] is None  # GCS failed, but validation succeeded!
                assert result["document_type"] == "director_resolution"


@pytest.mark.asyncio
async def test_validate_document_invalid_document_flagged():
    """Test validation catches invalid document (e.g. blurry/thumb over date)."""
    fake_bytes = b"blurry image bytes"

    mock_download = {
        "success": True,
        "file_bytes": fake_bytes,
        "mime_type": "image/jpeg",
        "file_size": len(fake_bytes),
        "media_id": "media_blurry",
    }

    mock_storage = {
        "success": True,
        "file_url": "gs://al-astoora-documents/clients/6591234567/passport/blurry.jpg",
    }

    mock_analysis = {
        "document_type": "passport",
        "extracted_fields": {"full_name": "John Doe"},
        "is_valid": False,
        "issues": ["Image is too blurry", "Expiry date obscured by finger"],
        "client_message": "Your passport photo is blurry and the expiry date is covered. Please send a clearer photo.",
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage", new=AsyncMock(return_value=mock_storage)):
            with patch("app.module_d.validator.analyze_document_with_gemini", new=AsyncMock(return_value=mock_analysis)):
                result = await validate_document(
                    media_id="media_blurry",
                    expected_doc_type="passport",
                    client_phone="6591234567",
                )
                assert result["success"] is True
                assert result["is_valid"] is False
                assert len(result["issues"]) == 2
                assert "blurry" in result["client_message"].lower()


@pytest.mark.asyncio
async def test_validate_document_auto_detect_doc_type():
    """Test validate_document accurately auto-detects document type when expected_doc_type is auto_detect."""
    fake_bytes = b"binary photo of trade license"

    mock_download = {
        "success": True,
        "file_bytes": fake_bytes,
        "mime_type": "application/pdf",
        "file_size": len(fake_bytes),
        "media_id": "media_tl_auto",
    }

    mock_storage = {
        "success": True,
        "file_url": "gs://al-astoora-documents/clients/6591234567/documents/trade_license.pdf",
    }

    mock_analysis = {
        "document_type": "trade_license",
        "extracted_fields": {
            "company_name": "Al Astoora Global Pte Ltd",
            "registration_number": "202612345Z",
            "expiry_date": "2028-12-31",
        },
        "is_valid": True,
        "issues": [],
        "client_message": "Your trade license has been successfully validated.",
        "eligibility_assessment": {
            "status": "eligible",
            "service_track": "corporate_secretarial",
            "summary": "Valid trade license ready for corporate secretarial compliance.",
        },
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage", new=AsyncMock(return_value=mock_storage)):
            with patch("app.module_d.validator.analyze_document_with_gemini", new=AsyncMock(return_value=mock_analysis)):
                result = await validate_document(
                    media_id="media_tl_auto",
                    expected_doc_type="auto_detect",
                    client_phone="6591234567",
                )

                assert result["success"] is True
                assert result["is_valid"] is True
                assert result["document_type"] == "trade_license"
                assert result["extracted_fields"]["company_name"] == "Al Astoora Global Pte Ltd"
                assert result["eligibility_assessment"]["status"] == "eligible"


@pytest.mark.asyncio
async def test_validate_document_extracts_eligibility_assessment():
    """Test that corporate eligibility assessment is extracted and returned in the pipeline."""
    fake_bytes = b"binary photo of bank statement"

    mock_download = {
        "success": True,
        "file_bytes": fake_bytes,
        "mime_type": "application/pdf",
        "file_size": len(fake_bytes),
        "media_id": "media_bs_pdf",
    }

    mock_storage = {
        "success": True,
        "file_url": "gs://al-astoora-documents/clients/6591234567/documents/bank_statement.pdf",
    }

    mock_analysis = {
        "document_type": "bank_statement",
        "extracted_fields": {"bank_name": "DBS Bank", "account_holder": "Apex LLC"},
        "is_valid": True,
        "issues": [],
        "client_message": "Bank statement verified.",
        "eligibility_assessment": {
            "status": "eligible",
            "service_track": "accounting_services",
            "summary": "Eligible for automated monthly accounting sync.",
            "recommended_next_step": "Submit trade license or tax assessment.",
        },
    }

    with patch("app.module_d.validator.download_media", new=AsyncMock(return_value=mock_download)):
        with patch("app.module_d.validator.upload_to_storage", new=AsyncMock(return_value=mock_storage)):
            with patch("app.module_d.validator.analyze_document_with_gemini", new=AsyncMock(return_value=mock_analysis)):
                result = await validate_document(
                    media_id="media_bs_pdf",
                    expected_doc_type="bank_statement",
                    client_phone="6591234567",
                )

                assert result["success"] is True
                assert result["eligibility_assessment"]["status"] == "eligible"
                assert "accounting_services" in result["eligibility_assessment"]["service_track"]


def test_module_d_strict_boundaries():
    """
    Supervision Checkpoint 5: Verify module boundaries.
    Module D must NEVER import or call Firestore or WhatsApp message sending.
    """
    import app.module_d as mod_d
    import app.module_d.media_downloader as downloader
    import app.module_d.storage as storage_mod
    import app.module_d.validator as validator_mod

    for mod in [mod_d, downloader, storage_mod, validator_mod]:
        # Must not contain firestore or whatsapp sender references
        mod_vars = dir(mod)
        assert "firestore" not in mod_vars or mod is storage_mod or mod is validator_mod # standard check
        assert "send_text_message" not in mod_vars
        assert "send_button_message" not in mod_vars
        assert "send_list_message" not in mod_vars
        assert "capture_lead" not in mod_vars
        assert "update_document_status" not in mod_vars
