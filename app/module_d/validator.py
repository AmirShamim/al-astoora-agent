"""
Module D: Document Validation Engine.
Performs multimodal inspection of client documents using Gemini 3.7 Flash on Google Cloud.
Extracts structured metadata, verifies document validity, detects issues, and produces client messages.
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import re
from typing import Dict, Any, Optional, List

from google import genai
from google.genai import types

from app.config import get_settings
from app.module_d.media_downloader import download_media
from app.module_d.storage import upload_to_storage

logger = logging.getLogger(__name__)

_genai_client: Optional[genai.Client] = None


def get_genai_client() -> genai.Client:
    """
    Returns the singleton Google GenAI Client for Gemini 3.7 Flash multimodal vision.
    Configured for Vertex AI or Google AI studio depending on configuration.
    """
    global _genai_client
    if _genai_client is None:
        settings = get_settings()
        logger.info(
            "Initializing Google GenAI Client (Project: %s, Location: %s)",
            settings.GCP_PROJECT_ID,
            settings.GEMINI_LOCATION,
        )
        try:
            # Initialize for Vertex AI backend on GCP
            _genai_client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=settings.GEMINI_LOCATION,
            )
        except Exception as e:
            logger.warning("Vertex AI initialization fallback to standard GenAI Client: %s", e)
            _genai_client = genai.Client()
    return _genai_client


def set_genai_client(client: Optional[genai.Client]) -> None:
    """
    Sets or overrides the GenAI Client instance (useful for unit testing / mocking).
    """
    global _genai_client
    _genai_client = client


def close_genai_client() -> None:
    """
    Resets the GenAI client instance reference.
    """
    global _genai_client
    _genai_client = None


def _build_validation_prompt(expected_doc_type: str, current_date_str: str) -> str:
    """Constructs the prompt for Gemini 3.7 Flash multimodal document validation."""
    return f"""You are a strict, expert document validation specialist for Al Astoora, a professional services agency assisting corporate clients with company incorporation, accounting, and immigration in Singapore and GCC (UAE).

Today's date is: {current_date_str}

Task:
Examine the attached image or document file which is expected to be a '{expected_doc_type}'.

Validate the document according to these strict rules:
1. Document Type Match: Verify that the document is indeed a '{expected_doc_type}' (e.g. passport, proof of address, director resolution, trade license). If it is a completely different document type, a selfie, or an irrelevant photo, flag it as invalid.
2. Readability & Quality: Verify that text, numbers, photo, and details are crisp and legible. Flag if there are severe blurs, glare, reflections, dark shadows, or if fingers/objects obstruct any vital information or dates.
3. Expiry & Validity: Extract the expiry date or validity period. Check if the document has expired relative to today's date ({current_date_str}). Flag expired documents as invalid.
4. Signature & Execution: If the document type is a resolution, contract, or legal agreement (e.g. director resolution), verify that it is signed.
5. Completeness: Ensure all crucial corners and key identifying fields are visible.

Field Extraction:
Extract core fields into 'extracted_fields' (e.g., full_name, document_number, nationality, date_of_birth, issue_date, expiry_date, address, company_name, etc. depending on document type).

Client Message Guidelines:
Write a friendly, polite 1-2 sentence message to the client on WhatsApp:
- If valid (is_valid = true): Warmly confirm that the document has been successfully validated.
- If invalid (is_valid = false): Concisely explain the exact issue in clear, non-technical language (e.g., "Your passport photo is blurry and the expiry date cannot be read. Please send a clearer, well-lit photo.") and ask them to resend.

Respond strictly in valid JSON matching this exact schema:
{{
  "document_type": "{expected_doc_type}",
  "extracted_fields": {{
    "key": "value"
  }},
  "is_valid": true,
  "issues": [],
  "client_message": "Friendly 1-2 sentence WhatsApp response."
}}
"""


def _parse_gemini_json_response(raw_text: str, expected_doc_type: str) -> Dict[str, Any]:
    """Parses and sanitizes Gemini JSON output with robust fallbacks."""
    cleaned = raw_text.strip()
    # Strip markdown fences if present
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        data = json.loads(cleaned)
    except Exception:
        # Attempt regex extraction if extra text surrounds JSON
        match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(1))
            except Exception as e:
                logger.error("Failed to parse regex extracted JSON from Gemini: %s", e)
                data = None
        else:
            data = None

    if not isinstance(data, dict):
        logger.error("Gemini response did not produce a valid dictionary: %s", raw_text)
        return {
            "document_type": expected_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": ["AI validation response could not be parsed"],
            "client_message": "We received your document, but could not process it automatically. Our team will review it shortly.",
        }

    # Ensure required keys exist with proper types
    doc_type = str(data.get("document_type") or expected_doc_type)
    extracted_fields = data.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}

    is_valid = bool(data.get("is_valid", False))
    issues = data.get("issues")
    if not isinstance(issues, list):
        issues = [str(issues)] if issues else []

    client_msg = str(data.get("client_message") or "")
    if not client_msg:
        if is_valid:
            client_msg = f"Thank you! Your {doc_type} has been successfully verified."
        else:
            issues_str = ", ".join(issues) if issues else "the document could not be validated"
            client_msg = f"We noticed an issue with your {doc_type}: {issues_str}. Please send a clearer document."

    return {
        "document_type": doc_type,
        "extracted_fields": extracted_fields,
        "is_valid": is_valid,
        "issues": issues,
        "client_message": client_msg,
    }


async def analyze_document_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    expected_doc_type: str,
) -> Dict[str, Any]:
    """
    Sends document image or PDF to Gemini 3.7 Flash multimodal vision for analysis.

    Args:
        file_bytes: Raw binary bytes of the document.
        mime_type: MIME type (e.g. 'image/jpeg', 'application/pdf').
        expected_doc_type: Expected document type (e.g. 'passport', 'proof_of_address').

    Returns:
        Dict containing document_type, extracted_fields, is_valid, issues, and client_message.
    """
    if not file_bytes:
        return {
            "document_type": expected_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": ["No document bytes provided for validation"],
            "client_message": "No document file was received. Please try sending your document again.",
        }

    settings = get_settings()
    current_date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = _build_validation_prompt(expected_doc_type, current_date_str)

    try:
        client = get_genai_client()
        # Build Part using google.genai types
        file_part = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type or "image/jpeg",
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1,
        )

        configured_model = settings.GEMINI_MODEL or "gemini-3.7-flash"
        candidate_models = [configured_model]
        for fallback in ["gemini-3.7-flash", "gemini-2.5-flash", "gemini-2.0-flash"]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        response = None
        for model_name in candidate_models:
            try:
                if hasattr(client, "aio") and hasattr(client.aio, "models") and hasattr(client.aio.models, "generate_content"):
                    response = await client.aio.models.generate_content(
                        model=model_name,
                        contents=[file_part, prompt],
                        config=config,
                    )
                elif hasattr(client, "models") and hasattr(client.models, "generate_content"):
                    res = client.models.generate_content(
                        model=model_name,
                        contents=[file_part, prompt],
                        config=config,
                    )
                    if hasattr(res, "__await__"):
                        response = await res
                    else:
                        response = res
                if response is not None:
                    break
            except Exception as model_err:
                logger.warning("Vision GenAI model '%s' failed: %s. Trying next...", model_name, model_err)

        if response is None:
            raise RuntimeError("All candidate multimodal models failed.")

        raw_text = getattr(response, "text", "") or ""
        logger.info("Gemini multimodal response for doc_type '%s': %s", expected_doc_type, raw_text[:200])

        return _parse_gemini_json_response(raw_text, expected_doc_type)

    except Exception as e:
        logger.exception("Gemini document analysis failed for '%s': %s", expected_doc_type, e)
        return {
            "document_type": expected_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": [f"Document analysis error: {str(e)}"],
            "client_message": "We received your document, but encountered an error analyzing it. Our team will review it manually.",
        }


async def validate_document(
    media_id: str,
    expected_doc_type: str,
    client_phone: str,
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entry point for Module D: Document Validation Pipeline.

    Executes:
    1. Download media bytes from WhatsApp Graph API
    2. Upload file to Google Cloud Storage (best-effort record-keeping)
    3. Analyze document with Gemini 3.7 Flash multimodal vision
    4. Return structured validation outcome

    Args:
        media_id: WhatsApp media ID from the incoming message.
        expected_doc_type: Expected document type (e.g. 'passport', 'proof_of_address').
        client_phone: Client phone number for storage path isolation.
        original_filename: Optional original filename if provided in document metadata.

    Returns:
        Dict with:
            - success (bool): True if pipeline completed
            - document_type (str): Detected or expected document type
            - extracted_fields (dict): Key fields extracted from the document
            - is_valid (bool): Whether the document passed all validation checks
            - issues (list[str]): List of identified issues or rejections reasons
            - client_message (str): Ready-to-send WhatsApp explanation message
            - file_url (str | None): GCS URL if uploaded
            - media_id (str): WhatsApp media ID
            - mime_type (str): Detected media MIME type
    """
    logger.info(
        "Starting document validation pipeline: media_id=%s, doc_type=%s, phone=%s",
        media_id,
        expected_doc_type,
        client_phone,
    )

    # Step 1: Download media from WhatsApp
    download_res = await download_media(media_id)
    if not download_res.get("success"):
        error_msg = download_res.get("error", "Could not download file from WhatsApp")
        logger.error("Validation aborted: media download failed: %s", error_msg)
        return {
            "success": False,
            "document_type": expected_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": [error_msg],
            "client_message": "Could not download your document from WhatsApp. Please try sending it again.",
            "file_url": None,
            "media_id": media_id,
            "mime_type": "unknown",
        }

    file_bytes: bytes = download_res["file_bytes"]
    mime_type: str = download_res.get("mime_type", "image/jpeg")

    # Step 2: Upload to Cloud Storage (best effort for record-keeping)
    storage_res = await upload_to_storage(
        file_bytes=file_bytes,
        client_phone=client_phone,
        doc_type=expected_doc_type,
        filename=original_filename,
        mime_type=mime_type,
    )

    file_url = storage_res.get("file_url") if storage_res.get("success") else None
    if not storage_res.get("success"):
        logger.warning(
            "Storage upload failed for media %s, but proceeding with validation: %s",
            media_id,
            storage_res.get("error"),
        )

    # Step 3: Analyze with Gemini 3.7 Flash Multimodal Vision
    analysis_res = await analyze_document_with_gemini(
        file_bytes=file_bytes,
        mime_type=mime_type,
        expected_doc_type=expected_doc_type,
    )

    return {
        "success": True,
        "document_type": analysis_res.get("document_type", expected_doc_type),
        "extracted_fields": analysis_res.get("extracted_fields", {}),
        "is_valid": bool(analysis_res.get("is_valid", False)),
        "issues": analysis_res.get("issues", []),
        "client_message": analysis_res.get("client_message", ""),
        "file_url": file_url,
        "media_id": media_id,
        "mime_type": mime_type,
    }
