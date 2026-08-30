"""
Module B: ADK Tool Definitions for Al Astoora Document Collector Agent.
Provides typed, docstring-annotated tool functions bridging the Gemini agent
to Module C (Firestore state), Module D (multimodal validation), and WhatsApp messaging.
"""

import json
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


async def capture_lead(name: str, phone: str, interest: str) -> str:
    """
    Captures a prospective client lead with contact information and service interest.
    Call this when a user expresses interest in Al Astoora services or inquiries.

    Args:
        name: The client's full name.
        phone: The client's phone number with country code (e.g. "6591234567").
        interest: Service interest description (e.g. "AI automation for client onboarding").

    Returns:
        String summary of the lead capture outcome.
    """
    try:
        from app.module_c.leads import capture_lead as _capture
        result = await _capture(name=name, phone=phone, interest=interest)
        if result.get("success"):
            return f"Success: {result.get('message', 'Lead captured successfully.')}"
        return f"Notice: {result.get('message', 'Lead already recorded or processing error.')}"
    except Exception as e:
        logger.exception("Error in capture_lead tool: %s", e)
        return "Could not capture lead due to a temporary database issue."


async def get_or_create_client(phone: str, name: str, service_type: str) -> str:
    """
    Retrieves an existing client profile or creates a new client onboarding record
    with the required document checklist for the specified service.

    Args:
        phone: The client's phone number with country code (e.g. "6591234567").
        name: The client's full name.
        service_type: Service identifier ('client_onboarding', 'financial_compliance', 'employment_processing', or 'general_verification').

    Returns:
        String summary of client record and required document checklist.
    """
    try:
        from app.module_c.clients import get_or_create_client as _get_or_create
        result = await _get_or_create(phone=phone, name=name, service_type=service_type)
        if not result.get("success"):
            return f"Notice: {result.get('error', 'Unable to retrieve or create client record.')}"

        client_data = result.get("client", {})
        docs_list = result.get("required_documents", [])
        status_lines = [f"- {d.get('doc_type')}: {d.get('status')}" for d in docs_list]
        docs_str = "\n".join(status_lines) if status_lines else "None pending"

        return (
            f"Client profile ready for {client_data.get('name')} ({phone}).\n"
            f"Service: {client_data.get('service_type')}\n"
            f"Status: {client_data.get('onboarding_status')}\n"
            f"Required Documents:\n{docs_str}"
        )
    except Exception as e:
        logger.exception("Error in get_or_create_client tool: %s", e)
        return "Could not load or create client record due to a temporary issue."


async def check_intake_status(phone: str) -> str:
    """
    Checks the document intake and onboarding progress for a client.
    Call when a client asks what documents they still need to provide or their status.

    Args:
        phone: The client's phone number with country code.

    Returns:
        String summary detailing total required documents, received, pending, and rejected files.
    """
    try:
        from app.module_c.clients import check_intake_status as _check_status
        result = await _check_status(phone=phone)
        if not result.get("success"):
            return f"Notice: {result.get('error', 'Client record not found. Please start onboarding first.')}"

        total = result.get("total_required", 0)
        received = result.get("documents_received", 0)
        pending = result.get("pending_documents", [])
        rejected = result.get("rejected_documents", [])
        is_complete = result.get("is_complete", False)

        lines = [
            f"Onboarding Status: {'Complete' if is_complete else 'In Progress'}",
            f"Progress: {received}/{total} documents validated.",
        ]
        if pending:
            lines.append(f"Pending Documents: {', '.join(pending)}")
        if rejected:
            rej_details = [f"{r.get('doc_type')} ({r.get('rejection_reason', 'issues detected')})" for r in rejected]
            lines.append(f"Rejected Documents to Resubmit: {', '.join(rej_details)}")

        return "\n".join(lines)
    except Exception as e:
        logger.exception("Error in check_intake_status tool: %s", e)
        return "Could not check intake status due to a temporary issue."


async def update_document_status(
    phone: str,
    doc_type: str,
    status: str,
    file_url: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> str:
    """
    Updates the verification status of a specific document for a client in the database.

    Args:
        phone: The client's phone number with country code.
        doc_type: Document type name (e.g. 'passport', 'proof_of_address').
        status: New status ('pending', 'submitted', 'validated', or 'rejected').
        file_url: Optional Cloud Storage file URL.
        rejection_reason: Optional explanation if status is 'rejected'.

    Returns:
        String summary of the update and remaining documents.
    """
    try:
        from app.module_c.documents import update_document_status as _update_doc
        result = await _update_doc(
            phone=phone,
            doc_type=doc_type,
            status=status,
            file_url=file_url,
            rejection_reason=rejection_reason,
        )
        if result.get("success"):
            remaining = result.get("remaining_documents", [])
            complete = result.get("onboarding_complete", False)
            if complete:
                return f"Document '{doc_type}' marked as '{status}'. All onboarding documents are complete!"
            return f"Document '{doc_type}' marked as '{status}'. Remaining documents needed: {', '.join(remaining) if remaining else 'None'}."
        return f"Failed to update document: {result.get('error', 'Unknown error')}"
    except Exception as e:
        logger.exception("Error in update_document_status tool: %s", e)
        return "Could not update document status due to a temporary database issue."


async def validate_document(
    media_id: str,
    expected_doc_type: str = "auto_detect",
    client_phone: str = "",
    original_filename: Optional[str] = None,
) -> str:
    """
    Downloads, stores, and validates a client's document image or PDF using Gemini 3.7 Flash multimodal vision.
    Extracts structured business information, validates authenticity/readability, assesses eligibility,
    and automatically records the submission to both the client's onboarding profile and the top-level database.

    Args:
        media_id: WhatsApp media ID for the uploaded file.
        expected_doc_type: Expected document type (e.g. 'auto_detect', 'passport', 'proof_of_address', 'director_resolution', 'trade_license', 'bank_statement', 'tax_assessment', 'resume', 'employment_contract').
        client_phone: The client's phone number with country code.
        original_filename: Optional original filename from WhatsApp metadata.

    Returns:
        JSON string summary of validation results, extracted fields, issues, eligibility assessment, and client response.
    """
    try:
        from app.module_d.validator import validate_document as _validate
        from app.module_c.documents import (
            update_document_status as _update_doc,
            record_document_submission as _record_submission,
        )

        effective_phone = client_phone or "unknown"
        val_result = await _validate(
            media_id=media_id,
            expected_doc_type=expected_doc_type or "auto_detect",
            client_phone=effective_phone,
            original_filename=original_filename,
        )

        is_valid = val_result.get("is_valid", False)
        detected_doc_type = val_result.get("document_type") or expected_doc_type or "general_document"
        issues = val_result.get("issues", [])
        client_message = val_result.get("client_message", "")
        file_url = val_result.get("file_url")
        extracted = val_result.get("extracted_fields", {})
        eligibility = val_result.get("eligibility_assessment", {})

        # 1. Record to top-level document_submissions database collection
        await _record_submission(
            phone=effective_phone,
            doc_type=detected_doc_type,
            is_valid=is_valid,
            extracted_fields=extracted,
            issues=issues,
            file_url=file_url,
            client_message=client_message,
            eligibility_assessment=eligibility,
            media_id=media_id,
            metadata={"original_filename": original_filename},
        )

        # 2. Update client onboarding checklist in Firestore
        doc_status = "validated" if is_valid else "rejected"
        rejection_reason = ", ".join(issues) if (not is_valid and issues) else None

        if effective_phone and effective_phone != "unknown":
            await _update_doc(
                phone=effective_phone,
                doc_type=detected_doc_type,
                status=doc_status,
                file_url=file_url,
                rejection_reason=rejection_reason,
            )

        # Check rejection count for 3-strike escalation awareness
        rejection_count = 0
        if not is_valid and effective_phone and effective_phone != "unknown":
            try:
                from app.module_c.documents import get_rejection_count
                rejection_count = await get_rejection_count(effective_phone, detected_doc_type)
            except Exception:
                pass

        summary = {
            "is_valid": is_valid,
            "document_type": detected_doc_type,
            "client_message": client_message,
            "issues": issues,
            "extracted_fields": extracted,
            "eligibility_assessment": eligibility,
            "file_url": file_url,
            "rejection_count": rejection_count,
        }

        # Add escalation hint when 3+ rejections
        if rejection_count >= 3:
            summary["escalation_required"] = True
            summary["escalation_message"] = (
                "This document has been rejected 3 or more times. "
                "You MUST call escalate_to_human now and send the handoff message."
            )

        return json.dumps(summary)
    except Exception as e:
        logger.exception("Error in validate_document tool: %s", e)
        return json.dumps({
            "is_valid": False,
            "document_type": expected_doc_type or "general_document",
            "client_message": "We received your file but encountered a temporary issue inspecting it. Our team will review it manually.",
            "issues": [str(e)],
            "eligibility_assessment": {},
            "rejection_count": 0,
        })



async def check_available_slots(
    recipient_phone: Optional[str] = None,
    phone: Optional[str] = None,
    date: str = "tomorrow",
) -> str:
    """
    Checks and sends available appointment consultation slots directly to the user as interactive WhatsApp options.
    Automatically excludes already booked slots.
    Call this whenever the user asks for available times, booking slots, or wants to schedule a meeting.

    Args:
        recipient_phone: Client's phone number with country code.
        phone: Alternative parameter for client's phone number.
        date: Target appointment date (e.g. 'tomorrow', 'today', '2026-08-20', 'Wednesday').

    Returns:
        Status string confirming dispatch of interactive slot list.
    """
    return await send_interactive_booking_slots(recipient_phone=recipient_phone, phone=phone, date=date)


async def send_booking_buttons(
    recipient_phone: Optional[str] = None,
    phone: Optional[str] = None,
    date: str = "tomorrow",
) -> str:
    """
    Sends 3 quick-tap interactive WhatsApp buttons with popular discovery call slots
    (e.g. Morning 09:00 AM, Midday 12:00 PM, Afternoon 03:00 PM) for one-tap booking.
    Call this when the user agrees to schedule a meeting or asks for quick times.

    Args:
        recipient_phone: Client's phone number with country code.
        phone: Alternative parameter for client's phone number.
        date: Target appointment date (e.g. 'tomorrow', 'today', '2026-08-20', 'Friday').

    Returns:
        Status string confirming dispatch of interactive buttons.
    """
    target_phone = recipient_phone or phone
    if not target_phone:
        return "Error: Missing recipient phone number for sending interactive buttons."

    try:
        from app.module_c.bookings import check_available_slots as _check_slots
        from app.module_b.whatsapp_sender import send_button_message

        result = await _check_slots(date=date)
        date_iso = result.get("date", date)
        friendly_date = result.get("friendly_date", date)
        available_slots = result.get("available_slots", [])

        if not available_slots:
            return f"Notice: No open slots available on {friendly_date}. Please ask the client for another preferred date."

        # Pick up to 3 well-spaced slots (e.g. morning, midday, afternoon)
        selected_slots = []
        preferred_keys = ["09:00", "12:00", "15:00", "10:00", "14:00", "16:00", "11:00", "17:00", "13:00"]
        for p_key in preferred_keys:
            if p_key in available_slots and p_key not in selected_slots:
                selected_slots.append(p_key)
            if len(selected_slots) >= 3:
                break

        # Fallback to first 3 available if preferred keys not found
        if not selected_slots:
            selected_slots = available_slots[:3]

        buttons = []
        for slot_key in selected_slots:
            sh, sm = map(int, slot_key.split(":"))
            hour_12 = sh if 1 <= sh <= 12 else (sh - 12 if sh > 12 else 12)
            ampm = "AM" if sh < 12 else "PM"
            btn_title = f"{hour_12}:{sm:02d} {ampm}"
            buttons.append({
                "id": f"book_{date_iso}_{slot_key}",
                "title": btn_title[:20],
            })

        body_text = f"Please select a time slot for our 30-min discovery call on {friendly_date}:"

        res = await send_button_message(
            recipient_phone=target_phone,
            body_text=body_text,
            buttons=buttons,
            header_text="Discovery Call Booking",
            footer_text="Al Astoora B2B Consultations",
        )

        if res.get("success"):
            return f"Sent interactive booking buttons for {friendly_date} to {target_phone}."
        return f"Notice: Interactive button dispatch returned {res.get('error', 'error')}."

    except Exception as e:
        logger.exception("Error in send_booking_buttons tool: %s", e)
        return f"Failed to send interactive buttons: {str(e)}"


async def send_interactive_booking_slots(
    recipient_phone: Optional[str] = None,
    phone: Optional[str] = None,
    date: str = "tomorrow",
) -> str:
    """
    Sends an interactive WhatsApp list message displaying all available 30-minute discovery call slots
    directly to the user for one-tap selection. Automatically excludes already booked slots.
    Call this when the user wants to view all available meeting times or schedule a call.

    Args:
        recipient_phone: Client's phone number with country code.
        phone: Alternative parameter for client's phone number.
        date: Target appointment date (e.g. 'tomorrow', 'today', '2026-08-20', 'Friday').

    Returns:
        Status string confirming dispatch of interactive slot list.
    """
    target_phone = recipient_phone or phone
    if not target_phone:
        return "Error: Missing recipient phone number for sending interactive list."

    try:
        from app.module_c.bookings import check_available_slots as _check_slots
        from app.module_b.whatsapp_sender import send_list_message

        result = await _check_slots(date=date)
        date_iso = result.get("date", date)
        friendly_date = result.get("friendly_date", date)
        available_slots = result.get("available_slots", [])
        available_labels = result.get("available_slot_labels", [])

        if not available_slots:
            return f"Notice: No open slots available on {friendly_date}. Please ask the client for another preferred date."

        # Build list rows (max 10 rows for WhatsApp interactive list)
        rows = []
        for slot_key, slot_lbl in zip(available_slots[:10], available_labels[:10]):
            rows.append({
                "id": f"book_{date_iso}_{slot_key}",
                "title": slot_lbl[:24],
                "description": "30-min discovery call",
            })

        sections = [{"title": "Available Slots", "rows": rows}]

        body_text = (
            f"Please choose a convenient 30-minute slot for our discovery call on {friendly_date} "
            "(each session includes a 30-min buffer):"
        )

        res = await send_list_message(
            recipient_phone=target_phone,
            body_text=body_text,
            button_text="Select Time Slot",
            sections=sections,
            title="Discovery Call Booking",
            footer_text="Al Astoora B2B Consultations",
        )

        if res.get("success"):
            return f"Sent interactive slot picker for {friendly_date} ({len(rows)} slots available) to {target_phone}."
        return f"Notice: Interactive dispatch returned {res.get('error', 'error')}."

    except Exception as e:
        logger.exception("Error in send_interactive_booking_slots tool: %s", e)
        return f"Failed to send interactive slot picker: {str(e)}"


async def book_appointment(
    date: str,
    time: str,
    name: Optional[str] = None,
    phone: Optional[str] = None,
) -> str:
    """
    Books an appointment / consultation slot for a client with collision detection.
    Standard meeting duration is 30 minutes with a 30-minute buffer interval.

    Args:
        date: Appointment date (e.g. 'tomorrow', '2026-08-20', 'today', 'Wednesday').
        time: Appointment time slot (e.g. '12 pm', '12:00', '14:00', '10:00 AM').
        name: Client's full name (optional, defaults from profile).
        phone: Client's phone number with country code.

    Returns:
        String confirmation message or conflict notification.
    """
    try:
        from app.module_c.bookings import book_appointment as _book
        result = await _book(date=date, time=time, name=name, phone=phone)
        if result.get("success"):
            confirmation = result.get("confirmation", "Appointment confirmed.")
            return f"Success: {confirmation} Booking ID: {result.get('booking_id')}."
        
        # If slot was taken, provide open alternative slots
        error_msg = result.get("error", "Slot already booked.")
        open_labels = result.get("available_slot_labels", [])
        if open_labels:
            return f"Notice: {error_msg} Available open slots for that day are: {', '.join(open_labels)}."
        return f"Could not book appointment: {error_msg}"
    except Exception as e:
        logger.exception("Error in book_appointment tool: %s", e)
        return "Could not book appointment due to a temporary issue."


async def send_whatsapp_text(recipient_phone: str, text: str) -> str:
    """
    Sends a direct plain text message to a client over WhatsApp.

    Args:
        recipient_phone: Client's phone number with country code.
        text: Plain text content to send.

    Returns:
        Status string confirming if the message was sent.
    """
    try:
        from app.module_b.whatsapp_sender import send_text_message
        res = await send_text_message(recipient_phone=recipient_phone, text=text)
        if res.get("success"):
            return "Message sent successfully."
        return f"Notice: Message dispatch returned {res.get('error', 'unknown error')}."
    except Exception as e:
        logger.exception("Error in send_whatsapp_text tool: %s", e)
        return f"Failed to send text message: {str(e)}"


async def send_whatsapp_buttons(
    recipient_phone: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> str:
    """
    Sends an interactive button message (max 3 buttons) to a client over WhatsApp.

    Args:
        recipient_phone: Client's phone number with country code.
        body_text: Main message body.
        buttons: List of dicts with 'id' and 'title' (max 3 buttons, title max 20 chars).
                 Example: [{'id': 'sg_reg', 'title': 'SG Company Reg'}, {'id': 'acc_serv', 'title': 'Accounting'}]
        header_text: Optional header string.
        footer_text: Optional footer string.

    Returns:
        Status string confirming dispatch.
    """
    try:
        from app.module_b.whatsapp_sender import send_button_message
        res = await send_button_message(
            recipient_phone=recipient_phone,
            body_text=body_text,
            buttons=buttons,
            header_text=header_text,
            footer_text=footer_text,
        )
        if res.get("success"):
            return "Interactive button message sent successfully."
        return f"Notice: Button dispatch returned {res.get('error', 'unknown error')}."
    except Exception as e:
        logger.exception("Error in send_whatsapp_buttons tool: %s", e)
        return f"Failed to send button message: {str(e)}"


async def send_whatsapp_list(
    recipient_phone: str,
    body_text: str,
    button_text: str,
    sections: List[Dict[str, Any]],
    title: Optional[str] = None,
    footer_text: Optional[str] = None,
) -> str:
    """
    Sends an interactive list message (up to 10 rows) to a client over WhatsApp.

    Args:
        recipient_phone: Client's phone number with country code.
        body_text: Main message body.
        button_text: Text displayed on the list dropdown trigger button (max 20 chars).
        sections: List of section dicts containing title and rows.
                  Example: [{'title': 'Services', 'rows': [{'id': 'sg_reg', 'title': 'SG Company Registration'}]}]
        title: Optional list header title.
        footer_text: Optional footer text.

    Returns:
        Status string confirming dispatch.
    """
    try:
        from app.module_b.whatsapp_sender import send_list_message
        res = await send_list_message(
            recipient_phone=recipient_phone,
            body_text=body_text,
            button_text=button_text,
            sections=sections,
            title=title,
            footer_text=footer_text,
        )
        if res.get("success"):
            return "Interactive list message sent successfully."
        return f"Notice: List dispatch returned {res.get('error', 'unknown error')}."
    except Exception as e:
        logger.exception("Error in send_whatsapp_list tool: %s", e)
        return f"Failed to send list message: {str(e)}"


async def escalate_to_human(phone: str, reason: str, doc_type: str = "") -> str:
    """
    Escalates a client case to the human support team when automated handling
    has been exhausted (e.g., 3 failed document validation attempts).
    Records the escalation event in Firestore for dashboard visibility.

    Args:
        phone: Client's phone number with country code.
        reason: Why the case is being escalated (e.g., "3 failed passport validation attempts").
        doc_type: The document type that triggered escalation.

    Returns:
        Confirmation that the human team has been notified.
    """
    try:
        from app.module_c.documents import record_escalation
        result = await record_escalation(
            phone=phone,
            reason=reason,
            doc_type=doc_type,
            escalation_type="document_validation_failure",
        )
        if result.get("success"):
            return (
                f"Escalation recorded (ID: {result.get('escalation_id')}). "
                f"The human support team has been notified about {phone}'s case. "
                f"Send the handoff message to the client now."
            )
        return f"Warning: Could not record escalation — {result.get('error')}. Still send the handoff message to the client."
    except Exception as e:
        logger.exception("Error in escalate_to_human tool: %s", e)
        return "Could not record escalation due to a temporary issue. Still send the handoff message to the client."


ALL_TOOLS = [
    capture_lead,
    get_or_create_client,
    check_intake_status,
    update_document_status,
    validate_document,
    check_available_slots,
    send_booking_buttons,
    send_interactive_booking_slots,
    book_appointment,
    escalate_to_human,
    send_whatsapp_text,
    send_whatsapp_buttons,
    send_whatsapp_list,
]

