"""
Module C: Document Intake State Management.
Handles updates to client document submission, validation, rejection, and intake progression.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

CLIENTS_COLLECTION = "clients"
DOCUMENTS_SUBCOLLECTION = "documents"
SUBMISSIONS_COLLECTION = "document_submissions"
ESCALATIONS_COLLECTION = "escalations"


async def record_document_submission(
    phone: str,
    doc_type: str,
    is_valid: bool,
    extracted_fields: Optional[Dict[str, Any]] = None,
    issues: Optional[List[str]] = None,
    file_url: Optional[str] = None,
    client_message: Optional[str] = None,
    eligibility_assessment: Optional[Dict[str, Any]] = None,
    media_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Records a document upload event into the top-level 'document_submissions' collection.
    Provides centralized audit logging, SaaS analytics, and dashboard queries across all clients.

    Args:
        phone: Client phone number.
        doc_type: Identified or expected document type.
        is_valid: Boolean indicating if validation passed.
        extracted_fields: Key fields extracted from the document.
        issues: List of issues or rejection reasons if any.
        file_url: Cloud Storage permanent URL.
        client_message: Message returned to client.
        eligibility_assessment: Corporate eligibility assessment data.
        media_id: WhatsApp media ID.
        metadata: Additional metadata (e.g. original filename, mime type).

    Returns:
        Dict with success status and submission_id.
    """
    try:
        db = get_firestore_client()
        submissions_ref = db.collection(SUBMISSIONS_COLLECTION)

        submission_data = {
            "phone": phone,
            "doc_type": doc_type,
            "is_valid": is_valid,
            "document_verification_status": "validated" if is_valid else "rejected",
            "status": "validated" if is_valid else "rejected",
            "extracted_fields": extracted_fields or {},
            "issues": issues or [],
            "file_url": file_url,
            "client_message": client_message or "",
            "eligibility_assessment": eligibility_assessment or {},
            "media_id": media_id,
            "metadata": metadata or {},
            "submitted_at": firestore.SERVER_TIMESTAMP,
        }

        doc_ref = submissions_ref.document()
        await doc_ref.set(submission_data)
        logger.info("Recorded document submission %s for %s (%s, valid=%s)", doc_ref.id, phone, doc_type, is_valid)

        return {
            "success": True,
            "submission_id": doc_ref.id,
            "phone": phone,
            "doc_type": doc_type,
            "is_valid": is_valid,
        }

    except Exception as e:
        logger.exception("Failed to record document submission for %s (%s): %s", phone, doc_type, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_recent_submissions(
    phone: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Retrieves recent document submissions across all clients or for a specific phone number.

    Args:
        phone: Optional client phone number to filter submissions.
        limit: Maximum number of records to return.

    Returns:
        Dict with list of recent submission records.
    """
    try:
        db = get_firestore_client()
        submissions_ref = db.collection(SUBMISSIONS_COLLECTION)

        if phone:
            query = (
                submissions_ref
                .where(filter=firestore.FieldFilter("phone", "==", phone))
                .limit(limit)
            )
        else:
            query = submissions_ref.limit(limit)

        submissions = []
        async for doc in query.stream():
            data = doc.to_dict() or {}
            data["id"] = doc.id
            submissions.append(data)

        return {
            "success": True,
            "submissions": submissions,
            "count": len(submissions),
        }

    except Exception as e:
        logger.exception("Failed to fetch recent submissions: %s", e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_document_submission(submission_id: str) -> Dict[str, Any]:
    """
    Retrieves a single document submission record by its Firestore document ID.

    Args:
        submission_id: Document submission ID.

    Returns:
        Dict with submission record or error.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(SUBMISSIONS_COLLECTION).document(submission_id)
        doc_snap = await doc_ref.get()

        if not doc_snap.exists:
            return {
                "success": False,
                "error": f"Submission '{submission_id}' not found",
            }

        data = doc_snap.to_dict() or {}
        data["id"] = doc_snap.id
        return {
            "success": True,
            "submission": data,
        }

    except Exception as e:
        logger.exception("Failed to get submission %s: %s", submission_id, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def update_document_status(
    phone: str,
    doc_type: str,
    status: str,
    file_url: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    auto_create_client: bool = True,
) -> Dict[str, Any]:
    """
    Updates the status and metadata of a specific document for a client.
    Automatically recalculates client progress counters and completion status.
    If client profile does not exist and auto_create_client is True, initializes profile automatically.

    Args:
        phone: Client phone number.
        doc_type: Document type key (e.g. 'passport', 'proof_of_address').
        status: New status ('pending', 'submitted', 'validated', 'rejected').
        file_url: Optional Cloud Storage or media URL.
        rejection_reason: Optional explanation if document was rejected.
        auto_create_client: If True, automatically creates client profile if missing.

    Returns:
        Dictionary with updated document state, progress counters, and remaining required documents.
    """
    try:
        db = get_firestore_client()
        client_ref = db.collection(CLIENTS_COLLECTION).document(phone)
        doc_ref = client_ref.collection(DOCUMENTS_SUBCOLLECTION).document(doc_type)

        # Parallelize client and document snapshot reads
        client_snap, doc_snap = await asyncio.gather(
            client_ref.get(),
            doc_ref.get(),
        )

        if not client_snap.exists:
            # Only create a client onboarding profile when a document is successfully validated
            if not auto_create_client or status != "validated":
                return {
                    "success": False,
                    "error": f"Client profile not created yet for phone {phone} (awaiting first validated document).",
                }
            # Fetch prospect name from leads if available
            client_name = phone
            try:
                from app.module_c.leads import get_lead_by_phone
                lead_res = await get_lead_by_phone(phone)
                if lead_res.get("success") and lead_res.get("lead"):
                    client_name = lead_res["lead"].get("name") or phone
            except Exception:
                pass

            init_client_data = {
                "name": client_name,
                "phone": phone,
                "service_type": "client_onboarding",
                "onboarding_started": firestore.SERVER_TIMESTAMP,
                "onboarding_status": "in_progress",
                "documents_required": 3,
                "documents_received": 0,
                "last_activity": firestore.SERVER_TIMESTAMP,
            }
            await client_ref.set(init_client_data)
            client_data = init_client_data
        else:
            client_data = client_snap.to_dict() or {}

        # Calculate attempts
        current_attempts = 0
        if doc_snap.exists:
            current_attempts = (doc_snap.to_dict() or {}).get("attempts", 0)

        # Prepare document updates
        doc_updates: Dict[str, Any] = {
            "doc_type": doc_type,
            "status": status,
            "attempts": current_attempts + (1 if status in ("submitted", "validated", "rejected") else 0),
        }

        if file_url is not None:
            doc_updates["file_url"] = file_url

        if rejection_reason is not None:
            doc_updates["rejection_reason"] = rejection_reason
        elif status == "validated":
            doc_updates["rejection_reason"] = None

        if status == "submitted":
            doc_updates["submitted_at"] = firestore.SERVER_TIMESTAMP
        elif status == "validated":
            doc_updates["validated_at"] = firestore.SERVER_TIMESTAMP

        # Save document update (merge to preserve existing fields like submitted_at)
        await doc_ref.set(doc_updates, merge=True)

        # Re-fetch all documents in subcollection to recalculate progress
        docs_stream = client_ref.collection(DOCUMENTS_SUBCOLLECTION).stream()
        all_docs = [doc.to_dict() async for doc in docs_stream]

        validated_count = sum(1 for d in all_docs if d.get("status") == "validated")
        total_required = client_data.get("documents_required", len(all_docs))
        remaining_docs = [d.get("doc_type") for d in all_docs if d.get("status") != "validated"]

        is_complete = (validated_count >= total_required) and (total_required > 0)
        new_onboarding_status = "complete" if is_complete else "in_progress"

        # Update client parent document
        client_updates = {
            "documents_received": validated_count,
            "onboarding_status": new_onboarding_status,
            "last_activity": firestore.SERVER_TIMESTAMP,
        }
        await client_ref.update(client_updates)

        logger.info(
            "Updated %s for %s -> status=%s, received=%d/%d, complete=%s",
            doc_type,
            phone,
            status,
            validated_count,
            total_required,
            is_complete,
        )

        return {
            "success": True,
            "phone": phone,
            "doc_type": doc_type,
            "status": status,
            "documents_received": validated_count,
            "documents_required": total_required,
            "onboarding_status": new_onboarding_status,
            "is_complete": is_complete,
            "remaining_docs": remaining_docs,
        }

    except Exception as e:
        logger.exception("Failed to update document status for %s (%s): %s", phone, doc_type, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_document(phone: str, doc_type: str) -> Dict[str, Any]:
    """
    Retrieves the status and metadata of a single client document.

    Args:
        phone: Client phone number.
        doc_type: Document type key.

    Returns:
        Dictionary with document details or error.
    """
    try:
        db = get_firestore_client()
        doc_ref = (
            db.collection(CLIENTS_COLLECTION)
            .document(phone)
            .collection(DOCUMENTS_SUBCOLLECTION)
            .document(doc_type)
        )
        doc_snap = await doc_ref.get()

        if not doc_snap.exists:
            return {
                "success": False,
                "error": f"Document '{doc_type}' not found for client {phone}",
            }

        return {
            "success": True,
            "document": doc_snap.to_dict(),
        }

    except Exception as e:
        logger.exception("Failed to get document %s for %s: %s", doc_type, phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def list_documents(phone: str) -> Dict[str, Any]:
    """
    Lists all documents and their statuses for a client.

    Args:
        phone: Client phone number.

    Returns:
        Dictionary with list of documents or error.
    """
    try:
        db = get_firestore_client()
        client_ref = db.collection(CLIENTS_COLLECTION).document(phone)
        client_snap = await client_ref.get()

        if not client_snap.exists:
            return {
                "success": False,
                "error": f"Client not found for phone {phone}",
            }

        docs_stream = client_ref.collection(DOCUMENTS_SUBCOLLECTION).stream()
        documents = [doc.to_dict() async for doc in docs_stream]

        return {
            "success": True,
            "phone": phone,
            "documents": documents,
        }

    except Exception as e:
        logger.exception("Failed to list documents for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_all_submissions(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves all document submissions across all clients for the dashboard audit trail.
    """
    try:
        db = get_firestore_client()
        submissions_stream = (
            db.collection(DOCUMENT_SUBMISSIONS_COLLECTION)
            .order_by("submitted_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        results = []
        async for doc in submissions_stream:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results
    except Exception as e:
        logger.warning("Failed to fetch all submissions: %s", e)
        return []


async def get_rejection_count(phone: str, doc_type: str) -> int:
    """
    Returns the number of consecutive rejections for a specific document type
    for a client. Used by the 3-strike escalation logic.

    Args:
        phone: Client phone number.
        doc_type: Document type key.

    Returns:
        Number of rejection attempts (0 if no rejections or client/doc not found).
    """
    try:
        db = get_firestore_client()
        doc_ref = (
            db.collection(CLIENTS_COLLECTION)
            .document(phone)
            .collection(DOCUMENTS_SUBCOLLECTION)
            .document(doc_type)
        )
        doc_snap = await doc_ref.get()

        if not doc_snap.exists:
            return 0

        doc_data = doc_snap.to_dict() or {}
        # Count attempts only if current status is 'rejected'
        if doc_data.get("status") == "rejected":
            return doc_data.get("attempts", 0)
        return 0

    except Exception as e:
        logger.warning("Could not check rejection count for %s/%s: %s", phone, doc_type, e)
        return 0


async def record_escalation(
    phone: str,
    reason: str,
    doc_type: str = "",
    escalation_type: str = "document_validation_failure",
) -> Dict[str, Any]:
    """
    Records a human escalation event in Firestore for dashboard visibility and audit.

    Args:
        phone: Client phone number.
        reason: Why the case is being escalated.
        doc_type: The document type that triggered escalation.
        escalation_type: Category of escalation.

    Returns:
        Dict with success status and escalation_id.
    """
    try:
        db = get_firestore_client()
        esc_ref = db.collection(ESCALATIONS_COLLECTION).document()

        escalation_data = {
            "phone": phone,
            "doc_type": doc_type,
            "reason": reason,
            "escalation_type": escalation_type,
            "status": "pending",
            "created_at": firestore.SERVER_TIMESTAMP,
            "resolved_at": None,
            "resolved_by": None,
        }
        await esc_ref.set(escalation_data)

        # Also update client profile to mark escalated status
        client_ref = db.collection(CLIENTS_COLLECTION).document(phone)
        client_snap = await client_ref.get()
        if client_snap.exists:
            await client_ref.update({
                "escalation_status": "escalated",
                "escalation_reason": reason,
                "escalation_doc_type": doc_type,
                "last_activity": firestore.SERVER_TIMESTAMP,
            })

        logger.info(
            "Escalation recorded for %s: %s (doc_type=%s, id=%s)",
            phone, reason, doc_type, esc_ref.id,
        )
        return {
            "success": True,
            "escalation_id": esc_ref.id,
            "phone": phone,
            "message": f"Escalation recorded. A human team member will review the case for {phone}.",
        }

    except Exception as e:
        logger.exception("Failed to record escalation for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Could not record escalation: {str(e)}",
        }
