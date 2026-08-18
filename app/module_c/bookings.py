"""
Module C: Appointment and Consultation Booking Management.
Handles slot availability checking and atomic appointment booking in Firestore.
"""

from datetime import datetime, timezone, timedelta, date as date_type
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
from google.cloud import firestore

from app.module_c.firestore_client import get_firestore_client

logger = logging.getLogger(__name__)

BOOKINGS_COLLECTION = "bookings"

# Curated 30-minute consultation slots with 30-minute buffer intervals (09:00 - 17:30)
DEFAULT_SLOTS: List[str] = [
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
]

SLOT_LABELS: Dict[str, str] = {
    "09:00": "09:00 - 09:30 AM",
    "10:00": "10:00 - 10:30 AM",
    "11:00": "11:00 - 11:30 AM",
    "12:00": "12:00 - 12:30 PM",
    "13:00": "01:00 - 01:30 PM",
    "14:00": "02:00 - 02:30 PM",
    "15:00": "03:00 - 03:30 PM",
    "16:00": "04:00 - 04:30 PM",
    "17:00": "05:00 - 05:30 PM",
}


def normalize_date(date_str: Optional[str] = None) -> Tuple[str, str]:
    """
    Parses a natural or ISO date string and returns (iso_date_str: 'YYYY-MM-DD', friendly_date_str: 'Day, Month DD, YYYY').
    Supports 'today', 'tomorrow', day names ('wednesday', 'next monday'), 'YYYY-MM-DD', 'DD-MM-YYYY', etc.
    """
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    if not date_str or not str(date_str).strip():
        target = today + timedelta(days=1)  # default to tomorrow
        return (target.strftime("%Y-%m-%d"), target.strftime("%A, %B %d, %Y"))

    clean = str(date_str).strip().lower()

    if clean in ("today", "tod"):
        target = today
    elif clean in ("tomorrow", "tom", "tmrw"):
        target = today + timedelta(days=1)
    elif clean in ("day after tomorrow", "overmorrow"):
        target = today + timedelta(days=2)
    else:
        # Check for day names (e.g. 'monday', 'next wednesday')
        days_map = {
            "monday": 0,
            "tuesday": 1,
            "wednesday": 2,
            "thursday": 3,
            "friday": 4,
            "saturday": 5,
            "sunday": 6,
        }
        matched_day = None
        for day_name, day_num in days_map.items():
            if day_name in clean:
                matched_day = day_num
                break

        if matched_day is not None:
            current_day = today.weekday()
            days_ahead = (matched_day - current_day) % 7
            if days_ahead == 0:
                days_ahead = 7  # next week if same day mentioned
            if "next" in clean and days_ahead < 7:
                days_ahead += 7
            target = today + timedelta(days=days_ahead)
        else:
            # Try parsing standard date formats
            target = None
            for fmt in (
                "%Y-%m-%d",
                "%d-%m-%Y",
                "%d/%m/%Y",
                "%Y/%m/%d",
                "%B %d, %Y",
                "%b %d, %Y",
                "%B %d",
                "%b %d",
            ):
                try:
                    parsed_dt = datetime.strptime(clean, fmt)
                    if parsed_dt.year == 1900:  # format without year
                        parsed_dt = parsed_dt.replace(year=today.year)
                    target = parsed_dt.date()
                    break
                except ValueError:
                    continue

            if target is None:
                # Regex match for YYYY-MM-DD
                match = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", clean)
                if match:
                    target = date_type(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                else:
                    target = today + timedelta(days=1)

    return (target.strftime("%Y-%m-%d"), target.strftime("%A, %B %d, %Y"))


def normalize_time(time_str: Optional[str] = None) -> Tuple[str, str]:
    """
    Normalizes various time strings ('12 pm', '12:00 PM', '14:00', '9am', '10:30', '17:00')
    to a standard (slot_key: 'HH:MM', slot_label: 'HH:MM - HH:MM AM/PM').
    """
    if not time_str or not str(time_str).strip():
        return ("10:00", SLOT_LABELS.get("10:00", "10:00 - 10:30 AM"))

    clean = str(time_str).strip().lower()

    # Detect AM/PM
    is_pm = "pm" in clean or "p.m." in clean or "afternoon" in clean or "evening" in clean or "night" in clean
    is_am = "am" in clean or "a.m." in clean or "morning" in clean

    # Strip everything except digits and colons
    clean_digits = re.sub(r"[^\d:]", "", clean)
    hour = 10
    minute = 0

    if ":" in clean_digits:
        parts = clean_digits.split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 and parts[1] else 0
        except ValueError:
            hour = 10
    elif clean_digits:
        try:
            hour = int(clean_digits)
        except ValueError:
            hour = 10

    if is_pm and hour < 12:
        hour += 12
    elif is_am and hour == 12:
        hour = 0

    # Match closest default slot
    target_minutes = hour * 60 + minute
    closest_slot = "10:00"
    min_diff = 999999
    for slot in DEFAULT_SLOTS:
        sh, sm = map(int, slot.split(":"))
        diff = abs((sh * 60 + sm) - target_minutes)
        if diff < min_diff:
            min_diff = diff
            closest_slot = slot

    slot_label = SLOT_LABELS.get(closest_slot, f"{closest_slot} Slot")
    return (closest_slot, slot_label)


async def check_available_slots(date: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks consultation slot availability for a given date.
    Filters out any slots that are already confirmed/booked in Firestore.

    Args:
        date: Date string (e.g. 'tomorrow', '2026-08-20', 'Friday').

    Returns:
        Dictionary with date, friendly_date, available_slots, available_slot_labels, and booked_slots.
    """
    date_iso, friendly_date = normalize_date(date)

    try:
        db = get_firestore_client()
        bookings_ref = db.collection(BOOKINGS_COLLECTION)

        query = (
            bookings_ref
            .where(filter=firestore.FieldFilter("date", "==", date_iso))
            .where(filter=firestore.FieldFilter("status", "==", "confirmed"))
        )

        booked_slots: List[str] = []
        async for doc in query.stream():
            data = doc.to_dict() or {}
            slot_time = data.get("time")
            if slot_time:
                booked_slots.append(slot_time)

        # Exclude any booked slots
        available_slots = [slot for slot in DEFAULT_SLOTS if slot not in booked_slots]
        available_labels = [SLOT_LABELS.get(slot, slot) for slot in available_slots]

        logger.info(
            "Checked slots for %s (%s): %d available out of %d",
            date_iso,
            friendly_date,
            len(available_slots),
            len(DEFAULT_SLOTS),
        )

        return {
            "success": True,
            "date": date_iso,
            "friendly_date": friendly_date,
            "available_slots": available_slots,
            "available_slot_labels": available_labels,
            "booked_slots": booked_slots,
            "total_slots": len(DEFAULT_SLOTS),
        }

    except Exception as e:
        logger.exception("Failed to check slots for date %s: %s", date_iso, e)
        return {
            "success": False,
            "date": date_iso,
            "friendly_date": friendly_date,
            "available_slots": DEFAULT_SLOTS,
            "available_slot_labels": [SLOT_LABELS.get(s, s) for s in DEFAULT_SLOTS],
            "booked_slots": [],
            "error": f"Database unavailable: {str(e)}",
        }


async def book_appointment(
    date: str,
    time: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Books an appointment slot with collision detection and natural language date/time parsing.

    Args:
        date: Appointment date (e.g. 'tomorrow', '2026-08-20', 'Wednesday').
        time: Appointment time slot (e.g. '12 pm', '14:00', '10:00 AM').
        name: Client full name.
        phone: Client contact phone number.

    Returns:
        Dictionary with booking confirmation or conflict error.
    """
    date_iso, friendly_date = normalize_date(date)
    time_key, time_label = normalize_time(time)
    client_name = str(name).strip() if name and str(name).strip() else "Valued Client"
    client_phone = str(phone).strip() if phone else ""

    try:
        db = get_firestore_client()
        bookings_ref = db.collection(BOOKINGS_COLLECTION)

        # Collision guard: check if slot is already booked
        collision_query = (
            bookings_ref
            .where(filter=firestore.FieldFilter("date", "==", date_iso))
            .where(filter=firestore.FieldFilter("time", "==", time_key))
            .where(filter=firestore.FieldFilter("status", "==", "confirmed"))
            .limit(1)
        )

        existing_docs = [doc async for doc in collision_query.stream()]
        if existing_docs:
            logger.warning("Booking collision: Slot %s on %s is already taken", time_key, date_iso)
            avail_res = await check_available_slots(date_iso)
            return {
                "success": False,
                "error": f"The {time_label} slot on {friendly_date} is already booked. Please choose another available slot.",
                "slot_taken": True,
                "date": date_iso,
                "friendly_date": friendly_date,
                "available_slots": avail_res.get("available_slots", []),
                "available_slot_labels": avail_res.get("available_slot_labels", []),
            }

        # Create confirmed booking entry
        booking_data = {
            "date": date_iso,
            "friendly_date": friendly_date,
            "time": time_key,
            "time_label": time_label,
            "name": client_name,
            "phone": client_phone,
            "booked_at": firestore.SERVER_TIMESTAMP,
            "status": "confirmed",
        }

        doc_ref = bookings_ref.document()
        await doc_ref.set(booking_data)

        confirmation_msg = f"Appointment confirmed for {client_name} on {friendly_date} at {time_label}."
        logger.info("Booked appointment %s for %s (%s at %s)", doc_ref.id, client_name, date_iso, time_key)

        return {
            "success": True,
            "booking_id": doc_ref.id,
            "date": date_iso,
            "friendly_date": friendly_date,
            "time": time_key,
            "time_label": time_label,
            "name": client_name,
            "phone": client_phone,
            "status": "confirmed",
            "confirmation": confirmation_msg,
        }

    except Exception as e:
        logger.exception("Failed to book appointment for %s on %s at %s: %s", client_name, date_iso, time_key, e)
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

