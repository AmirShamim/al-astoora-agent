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


def get_genai_client(location: Optional[str] = None) -> genai.Client:
    """
    Returns the singleton Google GenAI Client for Gemini 3.7 Flash multimodal vision and agent orchestration.
    Uses location="global" by default for Gemini 3.7 / 3.x series models on Vertex AI.
    """
    global _genai_client
    settings = get_settings()
    target_loc = location or getattr(settings, "GEMINI_LOCATION", "global") or "global"

    if _genai_client is None or getattr(_genai_client, "_location", None) != target_loc:
        logger.info(
            "Initializing Google GenAI Client (Project: %s, Location: %s)",
            settings.GCP_PROJECT_ID,
            target_loc,
        )
        try:
            # Initialize for Vertex AI backend on GCP
            _genai_client = genai.Client(
                vertexai=True,
                project=settings.GCP_PROJECT_ID,
                location=target_loc,
            )
            setattr(_genai_client, "_location", target_loc)
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


# Rigid canonical enum constants for corporate data integrity
VALID_DOC_TYPES = {
    "passport",
    "proof_of_address",
    "trade_license",
    "bank_statement",
    "tax_assessment",
    "director_resolution",
    "company_constitution",
    "acra_bizfile",
    "invoice",
    "resume",
    "employment_contract",
    "general_document",
}

VALID_SERVICE_TRACKS = {
    "sg_company_registration",
    "accounting_services",
    "immigration_consulting",
    "general_corporate_services",
}

VALID_ELIGIBILITY_STATUSES = {
    "eligible",
    "ineligible",
    "pending_review",
}


def _normalize_doc_type(raw_type: Any, fallback: str = "general_document") -> str:
    """Deterministically normalizes any arbitrary document type string into a rigid canonical enum."""
    if not raw_type:
        return fallback
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", str(raw_type).strip().lower()).strip("_")

    alias_map = {
        "trade_license": "trade_license",
        "tradelicense": "trade_license",
        "commercial_license": "trade_license",
        "business_license": "trade_license",
        "tl": "trade_license",
        "passport": "passport",
        "passport_scan": "passport",
        "passport_photo": "passport",
        "passport_copy": "passport",
        "proof_of_address": "proof_of_address",
        "address_proof": "proof_of_address",
        "utility_bill": "proof_of_address",
        "bank_statement": "bank_statement",
        "bank_stmt": "bank_statement",
        "bank_statements": "bank_statement",
        "tax_assessment": "tax_assessment",
        "tax_return": "tax_assessment",
        "corporate_tax": "tax_assessment",
        "director_resolution": "director_resolution",
        "directors_resolution": "director_resolution",
        "board_resolution": "director_resolution",
        "company_constitution": "company_constitution",
        "constitution": "company_constitution",
        "memorandum": "company_constitution",
        "articles_of_association": "company_constitution",
        "acra_bizfile": "acra_bizfile",
        "bizfile": "acra_bizfile",
        "acra": "acra_bizfile",
        "acra_profile": "acra_bizfile",
        "invoice": "invoice",
        "invoices_receipts": "invoice",
        "receipt": "invoice",
        "resume": "resume",
        "resume_cv": "resume",
        "cv": "resume",
        "employment_contract": "employment_contract",
        "contract": "employment_contract",
        "employment_offer_letter": "employment_contract",
        "general_document": "general_document",
    }

    if clean in alias_map:
        return alias_map[clean]
    if clean in VALID_DOC_TYPES:
        return clean
    return fallback if fallback in VALID_DOC_TYPES else "general_document"


def _normalize_eligibility_status(raw_status: Any, is_valid: bool) -> str:
    """Deterministically normalizes eligibility status to strictly 'eligible', 'ineligible', or 'pending_review'."""
    clean = str(raw_status or "").strip().lower().replace("-", "_").replace(" ", "_")
    if clean in ("eligible", "qualified", "approved", "valid", "pass", "true"):
        return "eligible"
    if clean in ("ineligible", "not_eligible", "disqualified", "rejected", "failed", "false", "no"):
        return "ineligible"
    if clean in ("pending", "pending_review", "needs_review", "review", "partial", "under_review"):
        return "pending_review"
    return "eligible" if is_valid else "ineligible"


def _normalize_service_track(raw_track: Any, doc_type: str) -> str:
    """Deterministically normalizes service track to one of the 4 rigid system tracks."""
    clean = str(raw_track or "").strip().lower().replace("-", "_").replace(" ", "_")
    if clean in (
        "sg_company_registration",
        "sg_reg",
        "company_registration",
        "incorporation",
        "secretarial",
        "corporate_secretarial",
        "corporate_secretarial_compliance",
    ):
        return "sg_company_registration"
    if clean in ("accounting_services", "accounting", "tax", "bookkeeping", "tax_compliance"):
        return "accounting_services"
    if clean in ("immigration_consulting", "immigration", "visa", "employment_pass"):
        return "immigration_consulting"
    if clean in VALID_SERVICE_TRACKS:
        return clean

    # Infer standard track from document type
    if doc_type in ("passport", "proof_of_address", "director_resolution", "acra_bizfile", "company_constitution"):
        return "sg_company_registration"
    if doc_type in ("bank_statement", "tax_assessment", "invoice"):
        return "accounting_services"
    if doc_type in ("resume", "employment_contract"):
        return "immigration_consulting"
    return "general_corporate_services"


def _build_validation_prompt(expected_doc_type: str, current_date_str: str) -> str:
    """Constructs the prompt for Gemini 3.7 Flash multimodal document validation with strict enum constraints."""
    is_auto = expected_doc_type.lower() in ("auto_detect", "auto", "general_document", "general", "")
    target_clause = (
        "Classify the document into one of the allowed document types (passport, trade_license, bank_statement, "
        "tax_assessment, director_resolution, company_constitution, acra_bizfile, invoice, resume, employment_contract)."
        if is_auto
        else f"Examine the attached file which is expected to be a '{expected_doc_type}'."
    )

    return f"""You are a strict, expert document validation specialist & corporate workflow consultant for Al Astoora (alastoora.tech).
Al Astoora is a digital infrastructure & SaaS agency assisting corporate secretarial, accounting, tax, and immigration clients in Singapore and GCC (UAE).

Today's date is: {current_date_str}

Task:
{target_clause}

Validate the document according to these strict professional criteria:
1. Document Identification: Accurately identify and classify the document. If it is an irrelevant photo (selfie, landscape, meme), flag as invalid.
2. Readability & Quality: Text, registration numbers, dates, and official seals must be crisp and legible. Flag if there are severe blurs, glare, reflections, or if fingers/objects cover vital details or dates.
3. Expiry & Validity: Extract expiry or validity dates. Check if the document has expired relative to today ({current_date_str}). Flag expired documents as invalid.
4. Signature & Authentication: If the document is a director resolution, contract, or legal agreement, verify if it is signed/executed.
5. Corporate Eligibility & Business Insights:
   - Extract business insights (Company Name, Registration/UEN/Tax ID, Registered Capital, Directors/Officers, Financial figures).
   - Evaluate corporate service eligibility with a specific reason.

CRITICAL SCHEMA REQUIREMENTS (STRICT ENUMS ONLY - NO EXCEPTIONS):
- 'document_type' MUST be strictly one of: ["passport", "proof_of_address", "trade_license", "bank_statement", "tax_assessment", "director_resolution", "company_constitution", "acra_bizfile", "invoice", "resume", "employment_contract", "general_document"]
- 'is_valid' MUST be boolean: true or false
- 'eligibility_assessment.eligibility_status' MUST be strictly one of: ["eligible", "ineligible", "pending_review"]
- 'eligibility_assessment.service_track' MUST be strictly one of: ["sg_company_registration", "accounting_services", "immigration_consulting", "general_corporate_services"]
- 'eligibility_assessment.eligibility_reason': Specific explanation of corporate qualification or disqualification.
- 'eligibility_assessment.recommended_next_step': Specific actionable next step.

Client Message Guidelines:
Write a friendly, polite 1-2 sentence message to the client on WhatsApp with prominent emoji highlighting:
- If valid (is_valid = true): Start with '✅' (e.g., "✅ Thank you! Your Trade License has been verified. Next, please upload your company bank statement.")
- If invalid (is_valid = false): Start with '⚠️' or '❌' (e.g., "⚠️ The document you sent appears to be a handwritten note, not a trade license. Could you please send the official trade license document for us to proceed?")

Respond strictly in valid JSON matching this exact schema:
{{
  "document_type": "{_normalize_doc_type(expected_doc_type, fallback='trade_license' if is_auto else 'general_document')}",
  "extracted_fields": {{
    "key": "value"
  }},
  "is_valid": true,
  "issues": [],
  "client_message": "✅ Thank you! Your document has been successfully verified.",
  "eligibility_assessment": {{
    "eligibility_status": "eligible",
    "service_track": "sg_company_registration",
    "eligibility_reason": "Specific reason explaining business qualification or disqualification",
    "recommended_next_step": "Next document or consultation step"
  }}
}}
"""


def _parse_gemini_json_response(raw_text: str, expected_doc_type: str) -> Dict[str, Any]:
    """Parses, sanitizes, and deterministically normalizes Gemini JSON output with strict enum guarantees."""
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

    fallback_doc = _normalize_doc_type(expected_doc_type, fallback="general_document")

    if not isinstance(data, dict):
        logger.error("Gemini response did not produce a valid dictionary: %s", raw_text)
        return {
            "document_type": fallback_doc,
            "extracted_fields": {},
            "is_valid": False,
            "issues": ["AI validation response could not be parsed"],
            "client_message": "⚠️ We received your document, but could not process it automatically. Our team will review it shortly.",
            "eligibility_assessment": {
                "eligibility_status": "ineligible",
                "service_track": "general_corporate_services",
                "eligibility_reason": "Document could not be parsed automatically.",
                "recommended_next_step": "Please submit a clear image or document file.",
                "status": "ineligible",
                "summary": "Document could not be parsed automatically.",
            },
        }

    # 1. Rigidly normalize is_valid
    is_valid = bool(data.get("is_valid", False))

    # 2. Rigidly normalize document_type
    raw_doc_type = data.get("document_type") or fallback_doc
    norm_doc_type = _normalize_doc_type(raw_doc_type, fallback=fallback_doc)

    # 3. Rigidly normalize extracted_fields
    extracted_fields = data.get("extracted_fields")
    if not isinstance(extracted_fields, dict):
        extracted_fields = {}

    # 4. Rigidly normalize issues
    issues = data.get("issues")
    if not isinstance(issues, list):
        issues = [str(issues)] if issues else []

    # 5. Rigidly normalize eligibility_assessment
    raw_eligibility = data.get("eligibility_assessment")
    if not isinstance(raw_eligibility, dict):
        raw_eligibility = {}

    raw_el_status = raw_eligibility.get("eligibility_status") or raw_eligibility.get("status")
    norm_status = _normalize_eligibility_status(raw_el_status, is_valid=is_valid)
    norm_track = _normalize_service_track(raw_eligibility.get("service_track"), doc_type=norm_doc_type)

    reason_text = str(
        raw_eligibility.get("eligibility_reason")
        or raw_eligibility.get("summary")
        or ""
    ).strip()
    if not reason_text:
        reason_text = (
            f"Document successfully verified for {norm_track}."
            if is_valid
            else f"Document validation failed for {norm_track} due to issues detected."
        )

    next_step_text = str(raw_eligibility.get("recommended_next_step") or "").strip()
    if not next_step_text:
        next_step_text = (
            "Proceed with remaining required onboarding documents."
            if is_valid
            else "Please provide a valid, unexpired, and legible document to continue."
        )

    eligibility_assessment = {
        "eligibility_status": norm_status,
        "service_track": norm_track,
        "eligibility_reason": reason_text,
        "recommended_next_step": next_step_text,
        # Backward-compatible aliases:
        "status": norm_status,
        "summary": reason_text,
    }

    # 6. Rigidly normalize client_message with emoji highlighting
    client_msg = str(data.get("client_message") or "").strip()
    friendly_name = norm_doc_type.replace("_", " ").title()
    if not client_msg:
        if is_valid:
            client_msg = f"✅ Thank you! Your {friendly_name} has been successfully verified."
        else:
            issues_str = ", ".join(issues) if issues else "the document could not be validated"
            client_msg = f"⚠️ We noticed an issue with your {friendly_name}: {issues_str}. Please send a clearer, official document."
    else:
        # Guarantee visible emoji prefix
        if is_valid:
            if not any(client_msg.startswith(e) for e in ("✅", "🎉", "👍", "📋")):
                client_msg = f"✅ {client_msg}"
        else:
            if not any(client_msg.startswith(e) for e in ("⚠️", "❌", "🚫", "❗")):
                client_msg = f"⚠️ {client_msg}"

    return {
        "document_type": norm_doc_type,
        "extracted_fields": extracted_fields,
        "is_valid": is_valid,
        "issues": issues,
        "client_message": client_msg,
        "eligibility_assessment": eligibility_assessment,
    }



def _build_thinking_config(model_name: str, settings: Any) -> Optional[Any]:
    """
    Builds ThinkingConfig optimized for fast document validation,
    setting thinking_level to 'low' for Gemini 3.7 Flash / 3.x series,
    or thinking_budget=0 for legacy/fallback models to prevent default medium thinking latency.
    """
    try:
        if not hasattr(types, "ThinkingConfig"):
            return None

        level = getattr(settings, "GEMINI_THINKING_LEVEL", "low") or "low"
        budget = getattr(settings, "GEMINI_THINKING_BUDGET", 0)

        # Gemini 3.x / 3.7 Flash uses thinking_level ("low", "medium", "high")
        if "3." in model_name or "gemini-3" in model_name:
            try:
                return types.ThinkingConfig(thinking_level=level.lower())
            except Exception:
                try:
                    return types.ThinkingConfig(thinking_budget=budget)
                except Exception:
                    return None
        else:
            try:
                return types.ThinkingConfig(thinking_budget=budget)
            except Exception:
                try:
                    return types.ThinkingConfig(thinking_level=level.lower())
                except Exception:
                    return None
    except Exception as e:
        logger.debug("Could not build thinking_config for validator model %s: %s", model_name, e)
        return None


async def analyze_document_with_gemini(
    file_bytes: bytes,
    mime_type: str,
    expected_doc_type: str = "auto_detect",
) -> Dict[str, Any]:
    """
    Sends document image or PDF to Gemini 3.7 Flash multimodal vision for analysis.

    Args:
        file_bytes: Raw binary bytes of the document.
        mime_type: MIME type (e.g. 'image/jpeg', 'application/pdf').
        expected_doc_type: Expected document type or 'auto_detect'.

    Returns:
        Dict containing document_type, extracted_fields, is_valid, issues, client_message, eligibility_assessment.
    """
    fallback_doc_type = "general_document" if expected_doc_type.lower() in ("auto_detect", "auto", "") else expected_doc_type

    if not file_bytes:
        return {
            "document_type": fallback_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": ["No document bytes provided for validation"],
            "client_message": "No document file was received. Please try sending your document again.",
            "eligibility_assessment": {},
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

        configured_model = settings.GEMINI_MODEL or "gemini-3.6-flash"
        candidate_models = [configured_model]
        for fallback in [
            "gemini-3.6-flash",
            "gemini-3.7-flash",
            "gemini-3-flash-preview",
            "gemini-3.5-flash",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        config_kwargs: Dict[str, Any] = {
            "response_mime_type": "application/json",
            "temperature": 0.1,
        }
        thinking_cfg = _build_thinking_config(configured_model, settings)
        if thinking_cfg is not None:
            config_kwargs["thinking_config"] = thinking_cfg

        try:
            config = types.GenerateContentConfig(**config_kwargs)
        except Exception as cfg_err:
            logger.warning("Vision GenerateContentConfig with thinking_config failed (%s), falling back", cfg_err)
            config = types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            )

        response = None
        for model_name in candidate_models:
            try:
                # Dynamically adjust thinking config for the target candidate model
                if hasattr(config, "thinking_config"):
                    config.thinking_config = _build_thinking_config(model_name, settings)

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
            "document_type": fallback_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": [f"Document analysis error: {str(e)}"],
            "client_message": "We received your document, but encountered an error analyzing it. Our team will review it manually.",
            "eligibility_assessment": {},
        }


async def validate_document(
    media_id: str,
    expected_doc_type: str = "auto_detect",
    client_phone: str = "",
    original_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Main entry point for Module D: Document Validation Pipeline.

    Executes non-blocking parallelized workflow:
    1. Download media bytes from WhatsApp Graph API
    2. Concurrently execute Cloud Storage upload and Gemini 3.7 Flash multimodal vision analysis via asyncio.gather
    3. Return structured validation & eligibility outcome

    Args:
        media_id: WhatsApp media ID from the incoming message.
        expected_doc_type: Expected document type or 'auto_detect'.
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
            - eligibility_assessment (dict): Corporate eligibility and workflow recommendation
            - file_url (str | None): GCS URL if uploaded
            - media_id (str): WhatsApp media ID
            - mime_type (str): Detected media MIME type
    """
    fallback_doc_type = "general_document" if expected_doc_type.lower() in ("auto_detect", "auto", "") else expected_doc_type

    logger.info(
        "Starting parallel document validation pipeline: media_id=%s, doc_type=%s, phone=%s",
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
            "document_type": fallback_doc_type,
            "extracted_fields": {},
            "is_valid": False,
            "issues": [error_msg],
            "client_message": "Could not download your document from WhatsApp. Please try sending it again.",
            "eligibility_assessment": {},
            "file_url": None,
            "media_id": media_id,
            "mime_type": "unknown",
        }

    file_bytes: bytes = download_res["file_bytes"]
    mime_type: str = download_res.get("mime_type", "image/jpeg")

    # Step 2 & 3: Run Cloud Storage upload and Gemini Vision analysis concurrently
    storage_task = asyncio.create_task(
        upload_to_storage(
            file_bytes=file_bytes,
            client_phone=client_phone or "unknown_client",
            doc_type=expected_doc_type if expected_doc_type not in ("auto_detect", "auto", "") else "documents",
            filename=original_filename,
            mime_type=mime_type,
        )
    )
    analysis_task = asyncio.create_task(
        analyze_document_with_gemini(
            file_bytes=file_bytes,
            mime_type=mime_type,
            expected_doc_type=expected_doc_type,
        )
    )

    storage_res, analysis_res = await asyncio.gather(storage_task, analysis_task, return_exceptions=False)

    file_url = storage_res.get("file_url") if isinstance(storage_res, dict) and storage_res.get("success") else None
    if isinstance(storage_res, dict) and not storage_res.get("success"):
        logger.warning(
            "Storage upload failed for media %s, but proceeding with validation: %s",
            media_id,
            storage_res.get("error"),
        )

    detected_doc_type = analysis_res.get("document_type") or fallback_doc_type

    return {
        "success": True,
        "document_type": detected_doc_type,
        "extracted_fields": analysis_res.get("extracted_fields", {}),
        "is_valid": bool(analysis_res.get("is_valid", False)),
        "issues": analysis_res.get("issues", []),
        "client_message": analysis_res.get("client_message", ""),
        "eligibility_assessment": analysis_res.get("eligibility_assessment", {}),
        "file_url": file_url,
        "media_id": media_id,
        "mime_type": mime_type,
    }

