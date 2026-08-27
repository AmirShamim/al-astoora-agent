"""
Module C: Session and Conversation History Manager.
Provides persistent multi-turn conversation memory backed by Firestore and an in-memory cache,
along with an immutable audit log (message_audit) for permanent accountability and dispute prevention.
"""

from collections import OrderedDict
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional

from google.cloud import firestore
from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

SESSIONS_COLLECTION = "sessions"
MESSAGE_AUDIT_COLLECTION = "message_audit"
MAX_HISTORY_MESSAGES = 16  # Keep last 16 messages (8 back-and-forth turns for active prompt context)
_SESSION_CACHE_MAX_SIZE = 500

# In-memory LRU cache for ultra-fast turns
_SESSION_CACHE: OrderedDict[str, List[Dict[str, Any]]] = OrderedDict()


async def get_session_history(phone: str, max_messages: int = MAX_HISTORY_MESSAGES) -> List[Dict[str, Any]]:
    """
    Retrieves recent conversation history for a given phone number.
    Returns list of dicts: [{"role": "user" | "model", "text": str, "timestamp": str}]
    """
    clean_phone = str(phone).strip()
    if not clean_phone:
        return []

    # 1. Check in-memory cache
    if clean_phone in _SESSION_CACHE and _SESSION_CACHE[clean_phone]:
        _SESSION_CACHE.move_to_end(clean_phone)
        return _SESSION_CACHE[clean_phone][-max_messages:]

    # 2. Query Firestore if not in cache
    try:
        db = get_firestore_client()
        session_ref = db.collection(SESSIONS_COLLECTION).document(clean_phone)
        session_snap = await session_ref.get()

        if session_snap.exists:
            data = session_snap.to_dict() or {}
            messages = data.get("messages", [])
            if isinstance(messages, list):
                _SESSION_CACHE[clean_phone] = messages
                if len(_SESSION_CACHE) > _SESSION_CACHE_MAX_SIZE:
                    _SESSION_CACHE.popitem(last=False)
                return messages[-max_messages:]
    except Exception as e:
        logger.warning("Could not fetch session history from Firestore for %s: %s", clean_phone, e)

    return []


async def append_session_message(phone: str, role: str, text: str) -> None:
    """
    Appends a message (user or model) to the active session history in both memory and Firestore,
    and writes an immutable permanent record to message_audit/{phone}/messages for full auditability.
    """
    clean_phone = str(phone).strip()
    if not clean_phone or not text or not str(text).strip():
        return

    iso_now = datetime.now(timezone.utc).isoformat()
    entry = {
        "role": "user" if role == "user" else "model",
        "text": str(text).strip(),
        "timestamp": iso_now,
    }

    # Ensure in-memory cache is populated from Firestore if not present
    if clean_phone not in _SESSION_CACHE:
        try:
            db = get_firestore_client()
            session_ref = db.collection(SESSIONS_COLLECTION).document(clean_phone)
            session_snap = await session_ref.get()
            if session_snap.exists:
                data = session_snap.to_dict() or {}
                existing_msgs = data.get("messages", [])
                if isinstance(existing_msgs, list):
                    _SESSION_CACHE[clean_phone] = list(existing_msgs)
                else:
                    _SESSION_CACHE[clean_phone] = []
            else:
                _SESSION_CACHE[clean_phone] = []
        except Exception as e:
            logger.warning("Could not pre-fetch session from Firestore for %s: %s", clean_phone, e)
            _SESSION_CACHE[clean_phone] = []

    _SESSION_CACHE[clean_phone].append(entry)
    _SESSION_CACHE.move_to_end(clean_phone)

    # Trim in-memory cache to last 20 messages for prompt efficiency
    if len(_SESSION_CACHE[clean_phone]) > 20:
        _SESSION_CACHE[clean_phone] = _SESSION_CACHE[clean_phone][-20:]

    if len(_SESSION_CACHE) > _SESSION_CACHE_MAX_SIZE:
        _SESSION_CACHE.popitem(last=False)

    # Persist to Firestore:
    # 1. Update fast working session document
    # 2. Append permanent immutable audit log entry in subcollection
    try:
        db = get_firestore_client()
        session_ref = db.collection(SESSIONS_COLLECTION).document(clean_phone)
        await session_ref.set(
            {
                "phone": clean_phone,
                "messages": _SESSION_CACHE[clean_phone],
                "updated_at": entry["timestamp"],
            },
            merge=True,
        )

        # Permanent Immutable Audit Log
        audit_msg_ref = db.collection(MESSAGE_AUDIT_COLLECTION).document(clean_phone).collection("messages").document()
        await audit_msg_ref.set(
            {
                "phone": clean_phone,
                "role": entry["role"],
                "text": entry["text"],
                "timestamp": entry["timestamp"],
                "created_at": firestore.SERVER_TIMESTAMP,
            }
        )
    except Exception as e:
        logger.warning("Could not persist session/audit message to Firestore for %s: %s", clean_phone, e)


async def get_audit_history(phone: str, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves the complete, untrimmed immutable message audit log for a given phone number.
    Used by the client dashboard to inspect full conversation history for accountability.
    """
    clean_phone = str(phone).strip()
    if not clean_phone:
        return []

    try:
        db = get_firestore_client()
        audit_col = (
            db.collection(MESSAGE_AUDIT_COLLECTION)
            .document(clean_phone)
            .collection("messages")
            .order_by("timestamp")
            .limit(limit)
        )
        stream = audit_col.stream()
        messages = [doc.to_dict() async for doc in stream]
        if messages:
            return messages

        # Fallback to session collection if audit log is empty (for legacy sessions)
        return await get_session_history(clean_phone, max_messages=limit)
    except Exception as e:
        logger.warning("Could not fetch audit history for %s: %s", clean_phone, e)
        return await get_session_history(clean_phone, max_messages=limit)


async def get_all_sessions(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Returns recent active session metadata for all clients.
    """
    try:
        db = get_firestore_client()
        sessions_stream = db.collection(SESSIONS_COLLECTION).limit(limit).stream()
        results = []
        async for doc in sessions_stream:
            data = doc.to_dict() or {}
            data["id"] = doc.id
            results.append(data)
        return results
    except Exception as e:
        logger.warning("Failed to list sessions from Firestore: %s", e)
        return []


async def clear_session(phone: str) -> None:
    """Clears conversation history for a given phone number from memory and Firestore working session."""
    clean_phone = str(phone).strip()
    if clean_phone in _SESSION_CACHE:
        _SESSION_CACHE.pop(clean_phone, None)
    try:
        db = get_firestore_client()
        session_ref = db.collection(SESSIONS_COLLECTION).document(clean_phone)
        await session_ref.delete()
    except Exception as e:
        logger.warning("Could not delete session from Firestore for %s: %s", clean_phone, e)


def clear_session_cache() -> None:
    """Clears local in-memory session cache (primarily for unit testing)."""
    _SESSION_CACHE.clear()


