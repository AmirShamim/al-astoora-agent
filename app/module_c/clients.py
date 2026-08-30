"""
Module C: Client Profile and Intake Management.
Handles client creation, retrieval, and document intake tracking in Firestore.
"""

import logging
from typing import Dict, Any, List, Optional
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

CLIENTS_COLLECTION = "clients"
DOCUMENTS_SUBCOLLECTION = "documents"
INTAKE_TEMPLATES_COLLECTION = "intake_templates"

# Default fallback templates if intake_templates collection is not yet seeded in Firestore
# Includes both new automation-focused track names and legacy aliases for backward compatibility
DEFAULT_INTAKE_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "client_onboarding": {
        "service_name": "Client Onboarding Automation",
        "required_documents": [
            "passport",
            "proof_of_address",
            "director_resolution",
        ],
        "description": "Document validation workflow for client onboarding automation.",
    },
    "financial_compliance": {
        "service_name": "Financial Compliance Automation",
        "required_documents": [
            "trade_license",
            "bank_statement",
            "tax_assessment",
        ],
        "description": "Document validation workflow for financial compliance automation.",
    },
    "employment_processing": {
        "service_name": "Employment Processing Automation",
        "required_documents": [
            "passport",
            "resume",
            "employment_contract",
        ],
        "description": "Document validation workflow for employment processing automation.",
    },
    "general_verification": {
        "service_name": "General Document Verification",
        "required_documents": [
            "trade_license",
            "bank_statement",
            "company_constitution",
        ],
        "description": "General document verification automation workflow.",
    },
    # Legacy aliases for backward compatibility with existing Firestore data
    "sg_company_registration": {
        "service_name": "Client Onboarding Automation",
        "required_documents": [
            "passport",
            "proof_of_address",
            "director_resolution",
        ],
        "description": "Document validation workflow for client onboarding automation.",
    },
    "accounting_services": {
        "service_name": "Financial Compliance Automation",
        "required_documents": [
            "trade_license",
            "bank_statement",
            "tax_assessment",
        ],
        "description": "Document validation workflow for financial compliance automation.",
    },
    "immigration_consulting": {
        "service_name": "Employment Processing Automation",
        "required_documents": [
            "passport",
            "resume",
            "employment_contract",
        ],
        "description": "Document validation workflow for employment processing automation.",
    },
}

FALLBACK_DOCUMENTS = ["passport", "proof_of_address"]


async def _get_required_documents_for_service(service_type: str) -> List[str]:
    """
    Fetches required document types from Firestore intake_templates or fallback defaults.
    """
    try:
        db = get_firestore_client()
        template_ref = db.collection(INTAKE_TEMPLATES_COLLECTION).document(service_type)
        template_snap = await template_ref.get()

        if template_snap.exists:
            template_data = template_snap.to_dict() or {}
            required = template_data.get("required_documents")
            if isinstance(required, list) and required:
                return required
    except Exception as e:
        logger.warning("Could not load template '%s' from Firestore, using default: %s", service_type, e)

    # Use predefined default if available, otherwise fallback
    if service_type in DEFAULT_INTAKE_TEMPLATES:
        return DEFAULT_INTAKE_TEMPLATES[service_type]["required_documents"]
    return FALLBACK_DOCUMENTS


async def get_or_create_client(
    phone: str,
    name: str,
    service_type: str,
    company: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieves existing client profile or creates a new client and initializes their document checklist.

    Args:
        phone: Primary phone number (identifier).
        name: Client full name.
        service_type: Service type key (e.g. 'sg_company_registration').
        company: Optional company name.

    Returns:
        Dictionary with client data, list of required documents and statuses.
    """
    try:
        db = get_firestore_client()
        client_ref = db.collection(CLIENTS_COLLECTION).document(phone)
        client_snap = await client_ref.get()

        if client_snap.exists:
            client_data = client_snap.to_dict() or {}
            # Fetch existing documents subcollection
            docs_stream = client_ref.collection(DOCUMENTS_SUBCOLLECTION).stream()
            documents = [doc.to_dict() async for doc in docs_stream]

            logger.info("Existing client found for phone %s", phone)
            return {
                "success": True,
                "is_new": False,
                "client": client_data,
                "documents": documents,
            }

        # Client does not exist: create profile and initialize document checklist
        required_docs = await _get_required_documents_for_service(service_type)

        client_data = {
            "name": name,
            "phone": phone,
            "company": company,
            "service_type": service_type,
            "onboarding_started": firestore.SERVER_TIMESTAMP,
            "onboarding_status": "in_progress",
            "documents_required": len(required_docs),
            "documents_received": 0,
            "last_activity": firestore.SERVER_TIMESTAMP,
        }
        await client_ref.set(client_data)

        # Initialize document entries under subcollection in a single batched write
        created_documents = []
        batch = db.batch()
        for doc_type in required_docs:
            doc_entry = {
                "doc_type": doc_type,
                "status": "pending",
                "rejection_reason": None,
                "file_url": None,
                "submitted_at": None,
                "validated_at": None,
                "attempts": 0,
            }
            doc_ref = client_ref.collection(DOCUMENTS_SUBCOLLECTION).document(doc_type)
            batch.set(doc_ref, doc_entry)
            created_documents.append(doc_entry)

        await batch.commit()

        logger.info("New client created for phone %s with %d required documents (batched write)", phone, len(required_docs))
        return {
            "success": True,
            "is_new": True,
            "client": client_data,
            "documents": created_documents,
        }

    except Exception as e:
        logger.exception("Failed to get_or_create_client for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def check_intake_status(phone: str) -> Dict[str, Any]:
    """
    Checks the document intake progress for a client.

    Args:
        phone: Client phone number.

    Returns:
        Structured breakdown of required, received, pending, and rejected documents.
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
        docs_stream = client_ref.collection(DOCUMENTS_SUBCOLLECTION).stream()
        all_docs = [doc.to_dict() async for doc in docs_stream]

        pending = []
        submitted = []
        validated = []
        rejected = []

        for d in all_docs:
            doc_type = d.get("doc_type", "")
            status = d.get("status", "pending")
            if status == "validated":
                validated.append(doc_type)
            elif status == "rejected":
                rejected.append({
                    "doc_type": doc_type,
                    "rejection_reason": d.get("rejection_reason") or "Validation failed",
                })
            elif status == "submitted":
                submitted.append(doc_type)
            else:
                pending.append(doc_type)

        total_required = client_data.get("documents_required", len(all_docs))
        received = len(validated)
        complete = (received >= total_required) and (total_required > 0)

        return {
            "success": True,
            "phone": phone,
            "name": client_data.get("name", ""),
            "service_type": client_data.get("service_type", ""),
            "onboarding_status": client_data.get("onboarding_status", "in_progress"),
            "total_required": total_required,
            "received": received,
            "pending": pending,
            "submitted": submitted,
            "validated": validated,
            "rejected": rejected,
            "complete": complete,
        }

    except Exception as e:
        logger.exception("Failed to check intake status for %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_client(phone: str) -> Dict[str, Any]:
    """
    Fetches the profile details of an existing client.

    Args:
        phone: Client phone number.

    Returns:
        Dictionary with client data or error.
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

        return {
            "success": True,
            "client": client_snap.to_dict(),
        }

    except Exception as e:
        logger.exception("Failed to get client %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_all_clients(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieves all client onboarding profiles with their document checklists for the dashboard.
    """
    try:
        db = get_firestore_client()
        clients_stream = db.collection(CLIENTS_COLLECTION).limit(limit).stream()
        results = []
        async for doc in clients_stream:
            client_data = doc.to_dict() or {}
            phone = doc.id
            client_data["phone"] = phone

            # Fetch subcollection documents
            docs_stream = doc.reference.collection(DOCUMENTS_SUBCOLLECTION).stream()
            docs_list = [d.to_dict() async for d in docs_stream]
            client_data["documents"] = docs_list
            results.append(client_data)

        return results
    except Exception as e:
        logger.warning("Failed to fetch all clients: %s", e)
        return []
