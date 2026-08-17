"""
Module C: Firestore Client Initialization.
Provides a singleton AsyncClient for interacting with Google Cloud Firestore.
"""

import logging
from typing import Optional
from google.cloud import firestore

from app.config import get_settings

logger = logging.getLogger(__name__)

_async_db: Optional[firestore.AsyncClient] = None


def get_firestore_client() -> firestore.AsyncClient:
    """
    Returns the singleton AsyncClient for Google Cloud Firestore.
    Automatically uses credentials from the environment or service account.
    """
    global _async_db
    if _async_db is None:
        settings = get_settings()
        logger.info("Initializing Firestore AsyncClient for project: %s", settings.GCP_PROJECT_ID)
        _async_db = firestore.AsyncClient(project=settings.GCP_PROJECT_ID)
    return _async_db


def set_firestore_client(client: Optional[firestore.AsyncClient]) -> None:
    """
    Sets or overrides the Firestore AsyncClient instance (useful for unit testing/mocking).
    """
    global _async_db
    _async_db = client


async def close_firestore_client() -> None:
    """
    Closes the active Firestore client session if open.
    """
    global _async_db
    if _async_db is not None:
        try:
            if hasattr(_async_db, "close"):
                res = _async_db.close()
                if hasattr(res, "__await__"):
                    await res
        except Exception as e:
            logger.warning("Error closing Firestore client: %s", e)
        finally:
            _async_db = None
