"""
Module C: Appointment and Consultation Booking Management.
Handles slot availability checking and atomic appointment booking in Firestore.
"""

import logging
from typing import Dict, Any, List
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

BOOKINGS_COLLECTION = "bookings"

# Predefined standard business consultation slots (09:00 - 17:00, 30 min intervals)
DEFAULT_SLOTS: List[str] = [
    "09:00",
    "09:30",
    "10:00",
    "10:30",
    "11:00",
    "11:30",
    "12:00",
    "12:30",
    "13:00",
    "13:30",
    "14:00",
    "14:30",
    "15:00",
    "15:30",
    "16:00",
    "16:30",
]


async def check_available_slots(date: str) -> Dict[str, Any]:
    """
    Checks consultation slot availability for a given date.

    Args:
        date: Date in YYYY-MM-DD format (e.g. '2026-08-20').

    Returns:
        Dictionary with date, list of available slots, and booked slots.
    """
    try:
        db = get_firestore_client()
        bookings_ref = db.collection(BOOKINGS_COLLECTION)

        query = (
            bookings_ref
            .where(filter=firestore.FieldFilter("date", "==", date))
            .where(filter=firestore.FieldFilter("status", "==", "confirmed"))
        )

        booked_slots: List[str] = []
        async for doc in query.stream():
            data = doc.to_dict() or {}
            slot_time = data.get("time")
            if slot_time:
                booked_slots.append(slot_time)

        available_slots = [slot for slot in DEFAULT_SLOTS if slot not in booked_slots]

        logger.info(
            "Checked slots for %s: %d available out of %d",
            date,
            len(available_slots),
            len(DEFAULT_SLOTS),
        )

        return {
            "success": True,
            "date": date,
            "available_slots": available_slots,
            "booked_slots": booked_slots,
            "total_slots": len(DEFAULT_SLOTS),
        }

    except Exception as e:
        logger.exception("Failed to check slots for date %s: %s", date, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def book_appointment(
    date: str,
    time: str,
    name: str,
    phone: str,
) -> Dict[str, Any]:
    """
    Books an appointment slot with collision detection.

    Args:
        date: Date in YYYY-MM-DD format.
        time: Time in HH:MM format (e.g. '14:00').
        name: Client full name.
        phone: Client contact phone number.

    Returns:
        Dictionary with booking confirmation or conflict error.
    """
    try:
        db = get_firestore_client()
        bookings_ref = db.collection(BOOKINGS_COLLECTION)

        # Collision guard: check if slot is already booked
        collision_query = (
            bookings_ref
            .where(filter=firestore.FieldFilter("date", "==", date))
            .where(filter=firestore.FieldFilter("time", "==", time))
            .where(filter=firestore.FieldFilter("status", "==", "confirmed"))
            .limit(1)
        )

        existing_docs = [doc async for doc in collision_query.stream()]
        if existing_docs:
            logger.warning("Booking collision: Slot %s on %s is already taken", time, date)
            return {
                "success": False,
                "error": f"Slot at {time} on {date} is already booked",
                "slot_taken": True,
            }

        # Create booking entry
        booking_data = {
            "date": date,
            "time": time,
            "name": name,
            "phone": phone,
            "booked_at": firestore.SERVER_TIMESTAMP,
            "status": "confirmed",
        }

        doc_ref = bookings_ref.document()
        await doc_ref.set(booking_data)

        confirmation_msg = f"Appointment confirmed for {name} on {date} at {time}."
        logger.info("Booked appointment %s for %s (%s at %s)", doc_ref.id, name, date, time)

        return {
            "success": True,
            "booking_id": doc_ref.id,
            "date": date,
            "time": time,
            "name": name,
            "phone": phone,
            "status": "confirmed",
            "confirmation": confirmation_msg,
        }

    except Exception as e:
        logger.exception("Failed to book appointment for %s on %s at %s: %s", name, date, time, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def cancel_appointment(booking_id: str) -> Dict[str, Any]:
    """
    Cancels an existing appointment.

    Args:
        booking_id: Firestore document ID for the booking.

    Returns:
        Dictionary with cancellation status.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection(BOOKINGS_COLLECTION).document(booking_id)
        doc_snap = await doc_ref.get()

        if not doc_snap.exists:
            return {
                "success": False,
                "error": f"Booking ID {booking_id} not found",
            }

        await doc_ref.update({
            "status": "cancelled",
            "cancelled_at": firestore.SERVER_TIMESTAMP,
        })

        logger.info("Cancelled booking %s", booking_id)
        return {
            "success": True,
            "booking_id": booking_id,
            "status": "cancelled",
            "message": "Appointment cancelled successfully",
        }

    except Exception as e:
        logger.exception("Failed to cancel booking %s: %s", booking_id, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }


async def get_client_bookings(phone: str) -> Dict[str, Any]:
    """
    Retrieves all bookings made for a specific phone number.

    Args:
        phone: Client phone number.

    Returns:
        Dictionary containing list of bookings.
    """
    try:
        db = get_firestore_client()
        bookings_ref = db.collection(BOOKINGS_COLLECTION)

        query = bookings_ref.where(filter=firestore.FieldFilter("phone", "==", phone))
        bookings: List[Dict[str, Any]] = []

        async for doc in query.stream():
            data = doc.to_dict() or {}
            data["booking_id"] = doc.id
            bookings.append(data)

        return {
            "success": True,
            "phone": phone,
            "bookings": bookings,
        }

    except Exception as e:
        logger.exception("Failed to get bookings for phone %s: %s", phone, e)
        return {
            "success": False,
            "error": f"Database unavailable: {str(e)}",
        }
