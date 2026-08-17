"""
Module C: Document Intake State Management.
Handles updates to client document submission, validation, rejection, and intake progression.
"""

import logging
from typing import Dict, Any, Optional, List
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

CLIENTS_COLLECTION = "clients"
DOCUMENTS_SUBCOLLECTION = "documents"


async def update_document_status(
    phone: str,
    doc_type: str,
    status: str,
    file_url: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Updates the status and metadata of a specific document for a client.
    Automatically recalculates client progress counters and completion status.

    Args:
        phone: Client phone number.
        doc_type: Document type key (e.g. 'passport', 'proof_of_address').
        status: New status ('pending', 'submitted', 'validated', 'rejected').
        file_url: Optional Cloud Storage or media URL.
        rejection_reason: Optional explanation if document was rejected.

    Returns:
        Dictionary with updated document state, progress counters, and remaining required documents.
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

        client_data = client_snap.to_dict() or {}
        doc_ref = client_ref.collection(DOCUMENTS_SUBCOLLECTION).document(doc_type)
        doc_snap = await doc_ref.get()

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
