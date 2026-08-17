"""
Module C: Session and Conversation History Manager.
Provides persistent multi-turn conversation memory backed by Firestore and an in-memory cache.
"""

from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

SESSIONS_COLLECTION = "sessions"
MAX_HISTORY_MESSAGES = 16  # Keep last 16 messages (8 back-and-forth turns)

# In-memory LRU cache for ultra-fast turns
_SESSION_CACHE: Dict[str, List[Dict[str, Any]]] = {}


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
                return messages[-max_messages:]
    except Exception as e:
        logger.warning("Could not fetch session history from Firestore for %s: %s", clean_phone, e)

    return []


async def append_session_message(phone: str, role: str, text: str) -> None:
    """
    Appends a message (user or model) to the active session history in both memory and Firestore.
    """
    clean_phone = str(phone).strip()
    if not clean_phone or not text or not str(text).strip():
        return

    entry = {
        "role": "user" if role == "user" else "model",
        "text": str(text).strip(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Update in-memory cache
    if clean_phone not in _SESSION_CACHE:
        _SESSION_CACHE[clean_phone] = []
    _SESSION_CACHE[clean_phone].append(entry)

    # Trim in-memory cache to last 20 messages
    if len(_SESSION_CACHE[clean_phone]) > 20:
        _SESSION_CACHE[clean_phone] = _SESSION_CACHE[clean_phone][-20:]

    # Persist to Firestore asynchronously
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
    except Exception as e:
        logger.warning("Could not persist session message to Firestore for %s: %s", clean_phone, e)


async def clear_session(phone: str) -> None:
    """Clears conversation history for a given phone number."""
    clean_phone = str(phone).strip()
    if clean_phone in _SESSION_CACHE:
        _SESSION_CACHE.pop(clean_phone, None)
    try:
        db = get_firestore_client()
        session_ref = db.collection(SESSIONS_COLLECTION).document(clean_phone)
        await session_ref.delete()
    except Exception as e:
        logger.warning("Could not delete session from Firestore for %s: %s", clean_phone, e)
