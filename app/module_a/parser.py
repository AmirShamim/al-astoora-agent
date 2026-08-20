"""
Payload Parser for WhatsApp Cloud API Webhooks.
Transforms raw JSON event payloads into standardized ParsedMessage dataclass instances.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass(frozen=True)
class ParsedMessage:
    """Standardized representation of an incoming WhatsApp message."""

    sender_phone: str
    profile_name: str
    message_type: str  # "text" | "image" | "document" | "interactive" | "unsupported"
    message_content: str
    media_id: Optional[str] = None
    media_filename: Optional[str] = None
    media_mime_type: Optional[str] = None
    media_sha256: Optional[str] = None
    raw_timestamp: str = ""
    raw_message_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def parse_webhook_payload(payload: Dict[str, Any]) -> Optional[ParsedMessage]:
    """
    Parses a raw WhatsApp Cloud API webhook JSON payload.
    
    Returns:
        ParsedMessage if a valid message is found, otherwise None.
    """
    try:
        entries = payload.get("entry", [])
        if not entries:
            return None

        changes = entries[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        sender_phone = msg.get("from", "").strip()
        raw_msg_id = msg.get("id")
        raw_timestamp = msg.get("timestamp", "")
        msg_type = msg.get("type", "unknown")

        # Extract profile name if available in contacts
        contacts = value.get("contacts", [])
        profile_name = ""
        if contacts and isinstance(contacts, list):
            profile_name = contacts[0].get("profile", {}).get("name", "")

        # Fallback profile name to sender phone if empty
        if not profile_name:
            profile_name = sender_phone

        # Handle different message types
        if msg_type == "text":
            text_body = msg.get("text", {}).get("body", "")
            return ParsedMessage(
                sender_phone=sender_phone,
                profile_name=profile_name,
                message_type="text",
                message_content=text_body,
                raw_timestamp=raw_timestamp,
                raw_message_id=raw_msg_id,
            )

        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            interactive_type = interactive.get("type", "")
            
            if interactive_type == "button_reply":
                button_reply = interactive.get("button_reply", {})
                reply_id = button_reply.get("id", "")
                reply_title = button_reply.get("title", "")
                return ParsedMessage(
                    sender_phone=sender_phone,
                    profile_name=profile_name,
                    message_type="interactive",
                    message_content=reply_id or reply_title,
                    raw_timestamp=raw_timestamp,
                    raw_message_id=raw_msg_id,
                    metadata={"interactive_type": "button_reply", "title": reply_title, "id": reply_id},
                )

            elif interactive_type == "list_reply":
                list_reply = interactive.get("list_reply", {})
                reply_id = list_reply.get("id", "")
                reply_title = list_reply.get("title", "")
                reply_description = list_reply.get("description", "")
                return ParsedMessage(
                    sender_phone=sender_phone,
                    profile_name=profile_name,
                    message_type="interactive",
                    message_content=reply_id or reply_title,
                    raw_timestamp=raw_timestamp,
                    raw_message_id=raw_msg_id,
                    metadata={
                        "interactive_type": "list_reply",
                        "title": reply_title,
                        "id": reply_id,
                        "description": reply_description,
                    },
                )
            
            else:
                return ParsedMessage(
                    sender_phone=sender_phone,
                    profile_name=profile_name,
                    message_type="interactive",
                    message_content=f"interactive_{interactive_type}",
                    raw_timestamp=raw_timestamp,
                    raw_message_id=raw_msg_id,
                )

        elif msg_type == "image":
            image_data = msg.get("image", {})
            media_id = image_data.get("id")
            caption = image_data.get("caption", "")
            mime_type = image_data.get("mime_type", "image/jpeg")
            return ParsedMessage(
                sender_phone=sender_phone,
                profile_name=profile_name,
                message_type="image",
                message_content=caption,
                media_id=media_id,
                media_mime_type=mime_type,
                media_sha256=image_data.get("sha256"),
                raw_timestamp=raw_timestamp,
                raw_message_id=raw_msg_id,
                metadata={"mime_type": mime_type},
            )

        elif msg_type == "document":
            doc_data = msg.get("document", {})
            media_id = doc_data.get("id")
            filename = doc_data.get("filename", "document.pdf")
            caption = doc_data.get("caption", "")
            mime_type = doc_data.get("mime_type", "application/pdf")
            return ParsedMessage(
                sender_phone=sender_phone,
                profile_name=profile_name,
                message_type="document",
                message_content=caption or filename,
                media_id=media_id,
                media_filename=filename,
                media_mime_type=mime_type,
                media_sha256=doc_data.get("sha256"),
                raw_timestamp=raw_timestamp,
                raw_message_id=raw_msg_id,
                metadata={"mime_type": mime_type},
            )

        else:
            # Other unsupported types (audio, video, sticker, location, contact, reaction, etc.)
            return ParsedMessage(
                sender_phone=sender_phone,
                profile_name=profile_name,
                message_type="unsupported",
                message_content=f"unsupported_type_{msg_type}",
                raw_timestamp=raw_timestamp,
                raw_message_id=raw_msg_id,
                metadata={"original_type": msg_type},
            )

    except Exception:
        # Never crash on malformed payloads
        return None
