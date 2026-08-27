"""
Module C: Lead Capture Management.
Handles recording and querying prospective client leads in Firestore.
"""

import logging
from typing import Dict, Any
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

LEADS_COLLECTION = "leads"


async def capture_lead(name: str, phone: str, interest: str) -> Dict[str, Any]:
    """
    Captures a prospective client lead.
    Checks for duplicate entries by phone number before writing.

    Args:
        name: Full name of the prospect.
        phone: Contact phone number.
        interest: Service or topic of interest.

    Returns:
        Dictionary with success status and outcome message.
    """
    try:
        db = get_firestore_client()
        leads_ref = db.collection(LEADS_COLLECTION)

        # Check for existing lead with the same phone number
        query = leads_ref.where(filter=firestore.FieldFilter("phone", "==", phone)).limit(1)
        existing_docs = [doc async for doc in query.stream()]

        if existing_docs:
            existing_doc = existing_docs[0]
            logger.info("Lead with phone %s already exists (ID: %s)", phone, existing_doc.id)
            return {
                "success": True,
                "message": "Lead already captured",
                "already_captured": True,
                "lead_id": existing_doc.id,
            }

        # Create new lead entry
        lead_data = {
            "name": name,
            "phone": phone,
            "interest": interest,
            "source": "whatsapp_bot",
            "captured_at": firestore.SERVER_TIMESTAMP,
            "status": "new",
        }

        doc_ref = leads_ref.document()
        await doc_ref.set(lead_data)
        logger.info("Lead captured successfully for %s (ID: %s)", phone, doc_ref.id)

        return {
            "success": True,
            "message": "Lead captured",
            "already_captured": False,
            "lead_id": doc_ref.id,
        }

    except Exception as e:
        logger.exception("Failed to capture lead for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_lead_by_phone(phone: str) -> Dict[str, Any]:
    """
    Retrieves a lead record by phone number.

    Args:
        phone: Contact phone number to query.

    Returns:
        Dictionary containing lead record or error status.
    """
    try:
        db = get_firestore_client()
        leads_ref = db.collection(LEADS_COLLECTION)

        query = leads_ref.where(filter=firestore.FieldFilter("phone", "==", phone)).limit(1)
        docs = [doc async for doc in query.stream()]

        if not docs:
            return {
                "success": False,
                "error": f"Lead not found for phone {phone}",
            }

        lead_doc = docs[0]
        data = lead_doc.to_dict()
        data["id"] = lead_doc.id
        return {
            "success": True,
            "lead": data,
        }

    except Exception as e:
        logger.exception("Failed to retrieve lead for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_all_leads(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves all captured prospective leads for the dashboard lead pipeline.
    """
    try:
        db = get_firestore_client()
        leads_stream = (
            db.collection(LEADS_COLLECTION)
            .order_by("captured_at", direction=firestore.Query.DESCENDING)
            .limit(limit)
            .stream()
        )
        results = []
        async for doc in leads_stream:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results
    except Exception as e:
        logger.warning("Failed to fetch all leads: %s", e)
        return []
