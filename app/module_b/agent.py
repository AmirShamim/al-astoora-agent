"""
Module B: Google ADK Agent Orchestrator for Al Astoora Agency.
Orchestrates Gemini with Google ADK tool calling, handling incoming
ParsedMessage events from Module A, executing tools, and delivering WhatsApp responses.
"""

import asyncio
import inspect
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.module_a.parser import ParsedMessage
from app.module_b.system_prompt import SYSTEM_PROMPT
from app.module_b.tools import (
    ALL_TOOLS,
    capture_lead,
    get_or_create_client,
    check_intake_status,
    update_document_status,
    validate_document,
    check_available_slots,
    send_booking_buttons,
    send_interactive_booking_slots,
    book_appointment,
    send_whatsapp_text,
    send_whatsapp_buttons,
    send_whatsapp_list,
)
from app.module_b.whatsapp_sender import (
    send_text_message,
    send_typing_indicator,
    mark_message_as_read,
)

logger = logging.getLogger(__name__)

# Attempt importing Agent from Google ADK
try:
    from google.adk import Agent
    logger.info("Loaded Agent from google.adk")
except ImportError:
    try:
        from google.adk.agents import Agent
        logger.info("Loaded Agent from google.adk.agents")
    except ImportError:
        logger.warning("Google ADK Agent not available — will use direct GenAI fallback")
        # Fallback dummy class if ADK is mocked or running in minimal test environment
        class Agent:  # type: ignore
            def __init__(self, name: str, model: str, instruction: str, tools: Optional[List[Any]] = None):
                self.name = name
                self.model = model
                self.instruction = instruction
                self.tools = tools or []


_agent_instance: Optional[Any] = None

# Messaging tools that directly dispatch WhatsApp messages to the user
MESSAGING_TOOL_NAMES = {
    "send_whatsapp_text",
    "send_whatsapp_buttons",
    "send_whatsapp_list",
    "send_booking_buttons",
    "send_interactive_booking_slots",
    "check_available_slots",
}


def create_adk_agent() -> Any:
    """
    Creates and configures the Google ADK root agent instance for Al Astoora.
    Configured with Gemini, system prompt, and all Module C/D tools.
    """
    settings = get_settings()
    model_name = settings.GEMINI_MODEL or "gemini-3.7-flash"
    logger.info("Initializing Google ADK Agent 'al_astoora_agent' with model: %s", model_name)

    try:
        agent = Agent(
            name="al_astoora_agent",
            model=model_name,
            instruction=SYSTEM_PROMPT,
            tools=ALL_TOOLS,
        )
        return agent
    except Exception as e:
        logger.warning("Could not initialize ADK Agent: %s. Will use direct GenAI backend.", e)
        return None


def get_agent() -> Any:
    """Singleton accessor for the Google ADK Agent."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = create_adk_agent()
    return _agent_instance


def set_agent(agent: Optional[Any]) -> None:
    """Overrides or resets the ADK Agent instance (for unit testing and mocking)."""
    global _agent_instance
    _agent_instance = agent


async def _get_client_state_summary(sender_phone: str) -> str:
    """
    Fetches the live business state for this sender from Module C (Firestore)
    including lead capture status, onboarding checklist progress, recent document submissions, and bookings.
    """
    summary_parts = []
    try:
        from app.module_c.clients import check_intake_status
        from app.module_c.leads import get_lead_by_phone
        from app.module_c.bookings import get_client_bookings
        from app.module_c.documents import get_recent_submissions

        # 1. Check if client has active onboarding profile
        intake_res = await check_intake_status(sender_phone)
        if intake_res.get("success"):
            service_type = intake_res.get("service_type", "General")
            received = intake_res.get("received", 0)
            total = intake_res.get("total_required", 0)
            pending = intake_res.get("pending", [])
            rejected = intake_res.get("rejected", [])
            is_complete = intake_res.get("complete", False)

            status_str = f"Client Onboarding Active for '{service_type}'. Progress: {received}/{total} documents validated."
            if is_complete:
                status_str += " All required documents have been validated!"
            else:
                if pending:
                    status_str += f" Pending next: {', '.join(pending)}."
                if rejected:
                    rej_strs = [f"{r.get('doc_type')} ({r.get('rejection_reason')})" for r in rejected]
                    status_str += f" Rejected to resubmit: {', '.join(rej_strs)}."
            summary_parts.append(status_str)
        else:
            # 2. Check if prospect lead was captured
            lead_res = await get_lead_by_phone(sender_phone)
            if lead_res.get("success"):
                lead_data = lead_res.get("lead", {})
                lead_name = lead_data.get("name", "Prospect")
                lead_interest = lead_data.get("interest", "Consulting")
                summary_parts.append(f"Lead record captured for {lead_name} (Interest: '{lead_interest}').")

        # 3. Check recent document submissions
        recent_sub_res = await get_recent_submissions(phone=sender_phone, limit=3)
        if recent_sub_res.get("success") and recent_sub_res.get("submissions"):
            sub_strs = [f"{s.get('doc_type')} ({s.get('status')})" for s in recent_sub_res.get("submissions", [])]
            summary_parts.append(f"Recent Uploads: {', '.join(sub_strs)}.")

        # 4. Check for existing confirmed bookings
        booking_res = await get_client_bookings(sender_phone)
        if booking_res.get("success") and booking_res.get("bookings"):
            confirmed_bookings = [b for b in booking_res.get("bookings", []) if b.get("status") == "confirmed"]
            if confirmed_bookings:
                latest_b = confirmed_bookings[-1]
                summary_parts.append(f"Confirmed Discovery Appointment: {latest_b.get('date')} at {latest_b.get('time')}.")

    except Exception as e:
        logger.warning("Could not build client state summary for %s: %s", sender_phone, e)

    return "\n".join(summary_parts) if summary_parts else ""


def _build_user_event_prompt(
    message: ParsedMessage,
    state_summary: str = "",
    is_continuing_convo: bool = False,
) -> str:
    """
    Formats the incoming WhatsApp message event, real-time date/time, and metadata into a clean
    context prompt for the Gemini agent, including live Firestore state and interactive click hints.
    """
    now_utc = datetime.now(timezone.utc)
    today_iso = now_utc.strftime("%Y-%m-%d")
    tomorrow_dt = now_utc + timedelta(days=1)
    tomorrow_iso = tomorrow_dt.strftime("%Y-%m-%d")
    today_friendly = now_utc.strftime("%A, %B %d, %Y")
    tomorrow_friendly = tomorrow_dt.strftime("%A, %B %d, %Y")
    current_time_str = now_utc.strftime("%H:%M UTC")

    metadata_json = json.dumps(message.metadata or {})
    media_info = f"Media ID: {message.media_id}" if message.media_id else "No Media attached"
    if message.media_filename:
        media_info += f" (Filename: {message.media_filename})"

    convo_status = (
        "Continuing multi-turn conversation. DO NOT re-introduce the agency or restart greetings. Continue seamlessly from previous context."
        if is_continuing_convo
        else "New incoming inquiry."
    )

    state_section = f"\n- Live Business Context (Module C): {state_summary}" if state_summary else ""
    doc_action = (
        f"\n- Document Intake Action: User uploaded a file (Media ID: {message.media_id}). "
        f"Call 'validate_document' with media_id='{message.media_id}', expected_doc_type='auto_detect', "
        f"client_phone='{message.sender_phone}' to inspect, validate, assess eligibility, and record to database. "
        f"When replying, use the tool client_message directly or include the status emoji ('✅' for valid, '⚠️' for errors/rejected)."
        if message.media_id
        else ""
    )

    # Detect interactive slot selection clicks (e.g. book_2026-08-19_12:00)
    booking_action = ""
    content_str = str(message.message_content or "").strip()
    if content_str.startswith("book_"):
        parts = content_str.split("_")
        if len(parts) >= 3:
            slot_date = parts[1]
            slot_time = parts[2]
            booking_action = (
                f"\n- Booking Action: User selected appointment slot Date='{slot_date}', Time='{slot_time}'. "
                f"Call 'book_appointment' immediately with date='{slot_date}', time='{slot_time}', "
                f"name='{message.profile_name}', phone='{message.sender_phone}' to confirm."
            )

    return f"""[INCOMING WHATSAPP MESSAGE EVENT]
- Sender Phone: {message.sender_phone}
- Sender Profile Name: {message.profile_name}
- Message Type: {message.message_type}
- Message Content / User Text: {message.message_content}
- Current System Date & Time: {today_friendly}, {current_time_str} (Today: {today_iso})
- Tomorrow's Date: {tomorrow_friendly} (Tomorrow: {tomorrow_iso})
- Media Details: {media_info}
- Metadata: {metadata_json}
- Conversation Status: {convo_status}{state_section}{doc_action}{booking_action}"""



def _build_thinking_config(model_name: str, settings: Any) -> Optional[Any]:
    """
    Builds ThinkingConfig optimized for low latency WhatsApp messaging,
    setting thinking_level to 'low' for Gemini 3.7 Flash / 3.x series,
    or thinking_budget=0 for legacy/fallback models to prevent default medium thinking latency.
    """
    try:
        from google.genai import types
        if not hasattr(types, "ThinkingConfig"):
            return None

        level = getattr(settings, "GEMINI_THINKING_LEVEL", "low") or "low"
        budget = getattr(settings, "GEMINI_THINKING_BUDGET", 0)

        # Gemini 3.x / 3.7 Flash uses thinking_level ("low", "medium", "high")
        if "3." in model_name or "gemini-3" in model_name:
            try:
                return types.ThinkingConfig(thinking_level=level.lower())
            except Exception:
                try:
                    return types.ThinkingConfig(thinking_budget=budget)
                except Exception:
                    return None
        else:
            try:
                return types.ThinkingConfig(thinking_budget=budget)
            except Exception:
                try:
                    return types.ThinkingConfig(thinking_level=level.lower())
                except Exception:
                    return None
    except Exception as e:
        logger.debug("Could not build thinking_config for model %s: %s", model_name, e)
        return None


async def _execute_agent_turn(
    agent: Any,
    prompt: str,
    message: ParsedMessage,
) -> Tuple[Optional[str], bool, Optional[str]]:
    """
    Executes an agent reasoning and tool invocation turn using Google GenAI SDK with multi-turn tool loop.
    Returns:
        tuple (response_text: Optional[str], message_already_sent_via_tool: bool, dispatched_message_text: Optional[str])
    """
    dispatched_via_tool = False
    dispatched_message_text: Optional[str] = None
    last_validation_is_valid = None

    # Direct GenAI model invocation with multi-turn tool loop
    try:
        from google import genai
        from google.genai import types
        from app.module_d.validator import get_genai_client
        from app.module_c.sessions import get_session_history

        client = get_genai_client()
        settings = get_settings()
        configured_model = settings.GEMINI_MODEL or "gemini-3.7-flash"
        # Prioritize Gemini 3.5+ generation models
        candidate_models = [configured_model]
        for fallback in [
            "gemini-3.7-flash",
            "gemini-3-flash-preview",
            "gemini-3.5-flash",
            "gemini-3.5-pro",
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
        ]:
            if fallback not in candidate_models:
                candidate_models.append(fallback)

        tool_map = {t.__name__: t for t in ALL_TOOLS}

        func_declarations = []
        for tool_fn in ALL_TOOLS:
            try:
                func_declarations.append(tool_fn)
            except Exception as td_err:
                logger.warning("Could not add tool %s: %s", tool_fn.__name__, td_err)

        config_kwargs: Dict[str, Any] = {
            "system_instruction": SYSTEM_PROMPT,
            "temperature": 0.2,
            "tools": func_declarations,
        }
        thinking_cfg = _build_thinking_config(configured_model, settings)
        if thinking_cfg is not None:
            config_kwargs["thinking_config"] = thinking_cfg

        try:
            config = types.GenerateContentConfig(**config_kwargs)
        except Exception as cfg_err:
            logger.warning("GenerateContentConfig with thinking_config failed (%s), falling back to standard config", cfg_err)
            config = types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.2,
                tools=func_declarations,
            )

        # 1. Load multi-turn session history for this sender
        past_history = await get_session_history(message.sender_phone, max_messages=10)
        contents = []
        last_role = None

        for past_msg in past_history:
            role = past_msg.get("role", "user")
            text = past_msg.get("text", "")
            if not text:
                continue

            # Ensure valid alternating roles (user -> model -> user -> model)
            if role == last_role:
                continue

            try:
                contents.append(types.Content(role=role, parts=[types.Part(text=text)]))
                last_role = role
            except Exception:
                contents.append({"role": role, "parts": [{"text": text}]})
                last_role = role

        # If history ended with a user turn, wrap prompt into a single user turn
        if last_role == "user" and contents:
            try:
                contents[-1] = types.Content(role="user", parts=[types.Part(text=prompt)])
            except Exception:
                contents[-1] = {"role": "user", "parts": [{"text": prompt}]}
        else:
            # 2. Append current user event prompt
            try:
                contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
            except Exception:
                contents.append({"role": "user", "parts": [{"text": prompt}]})

        MAX_TURNS = 8
        for turn in range(MAX_TURNS):
            logger.info("GenAI turn %d, contents length: %d (session history: %d)", turn, len(contents), len(past_history))

            response = None
            for model_name in candidate_models:
                try:
                    # Dynamically adjust thinking config for the target model
                    if hasattr(config, "thinking_config"):
                        config.thinking_config = _build_thinking_config(model_name, settings)

                    if hasattr(client, "aio") and hasattr(client.aio, "models"):
                        response = await client.aio.models.generate_content(
                            model=model_name, contents=contents, config=config,
                        )
                    else:
                        res = client.models.generate_content(
                            model=model_name, contents=contents, config=config,
                        )
                        response = await res if inspect.isawaitable(res) else res
                    if response is not None:
                        break
                except Exception as model_err:
                    logger.warning("GenAI model '%s' failed: %s. Trying next candidate...", model_name, model_err)

            if response is None:
                logger.error("All candidate GenAI models failed.")
                break

            candidates = getattr(response, "candidates", [])
            has_function_calls = False
            function_response_parts = []

            if candidates and hasattr(candidates[0], "content") and hasattr(candidates[0].content, "parts"):
                contents.append(candidates[0].content)

                for part in candidates[0].content.parts:
                    fn_call = getattr(part, "function_call", None)
                    if fn_call:
                        has_function_calls = True
                        fn_name = getattr(fn_call, "name", "")
                        fn_args = dict(getattr(fn_call, "args", {}) or {})
                        logger.info("Agent tool call [turn %d]: %s(%s)", turn, fn_name, fn_args)

                        # Check if this tool dispatches a message to WhatsApp
                        if fn_name in MESSAGING_TOOL_NAMES:
                            dispatched_via_tool = True
                            if fn_name == "send_whatsapp_text":
                                dispatched_message_text = fn_args.get("text", "")
                            elif fn_name in ("send_whatsapp_buttons", "send_whatsapp_list"):
                                dispatched_message_text = fn_args.get("body_text", "")
                            elif fn_name in ("send_interactive_booking_slots", "send_booking_buttons", "check_available_slots"):
                                dispatched_message_text = "Please choose a convenient 30-minute slot for our discovery call from the interactive options above:"

                        tool_result = "Tool not found"
                        if fn_name in tool_map:
                            try:
                                target_tool = tool_map[fn_name]
                                # Auto-fill sender phone and name into tool arguments if omitted by model
                                try:
                                    tool_sig = inspect.signature(target_tool)
                                    if "recipient_phone" in tool_sig.parameters and not fn_args.get("recipient_phone"):
                                        fn_args["recipient_phone"] = message.sender_phone
                                    if "phone" in tool_sig.parameters and not fn_args.get("phone"):
                                        fn_args["phone"] = message.sender_phone
                                    if "name" in tool_sig.parameters and not fn_args.get("name"):
                                        fn_args["name"] = message.profile_name or "Valued Client"
                                    if "client_phone" in tool_sig.parameters and not fn_args.get("client_phone"):
                                        fn_args["client_phone"] = message.sender_phone
                                except Exception as sig_err:
                                    logger.debug("Signature inspect: %s", sig_err)

                                tool_result = target_tool(**fn_args)
                                if inspect.isawaitable(tool_result):
                                    tool_result = await tool_result
                                logger.info("Tool %s result: %s", fn_name, str(tool_result)[:200])

                                # Track document validation outcome to ensure emoji highlight in final message
                                if fn_name == "validate_document":
                                    try:
                                        val_obj = json.loads(str(tool_result)) if isinstance(tool_result, str) else tool_result
                                        if isinstance(val_obj, dict):
                                            last_validation_is_valid = val_obj.get("is_valid")
                                    except Exception:
                                        pass
                            except Exception as tool_err:
                                logger.exception("Tool %s execution failed: %s", fn_name, tool_err)
                                tool_result = f"Tool execution error: {str(tool_err)}"

                        try:
                            fr_part = types.Part.from_function_response(
                                name=fn_name,
                                response={"result": str(tool_result)},
                            )
                        except (AttributeError, TypeError):
                            try:
                                fr_part = types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fn_name,
                                        response={"result": str(tool_result)},
                                    )
                                )
                            except Exception:
                                fr_part = {"function_response": {"name": fn_name, "response": {"result": str(tool_result)}}}

                        function_response_parts.append(fr_part)

            if has_function_calls and function_response_parts:
                # If an interactive UI message was already sent to WhatsApp, finish immediately without duplicate text
                if dispatched_via_tool:
                    logger.info("Interactive WhatsApp message dispatched via tool. Ending agent turn cleanly.")
                    return (None, True, dispatched_message_text)

                try:
                    tool_content = types.Content(role="user", parts=function_response_parts)
                except Exception:
                    tool_content = {"role": "user", "parts": function_response_parts}
                contents.append(tool_content)
                continue

            # No more tool calls
            text_result = getattr(response, "text", None)
            if text_result and isinstance(text_result, str):
                text_result = text_result.strip()
                # Enforce emoji status prefix if document validation just occurred
                if last_validation_is_valid is False and not any(text_result.startswith(e) for e in ("⚠️", "❌", "🚫", "❗")):
                    text_result = f"⚠️ {text_result}"
                elif last_validation_is_valid is True and not any(text_result.startswith(e) for e in ("✅", "🎉", "👍", "📋")):
                    text_result = f"✅ {text_result}"

            logger.info(
                "GenAI finished (turn %d): text='%s', dispatched_via_tool=%s",
                turn,
                str(text_result)[:100] if text_result else "None",
                dispatched_via_tool,
            )
            return (text_result, dispatched_via_tool, dispatched_message_text)

        logger.warning("Agent exceeded max %d turns", MAX_TURNS)
        return (None, dispatched_via_tool, dispatched_message_text)
    except Exception as e:
        logger.exception("Direct GenAI fallback FAILED: %s", e)
        return (None, dispatched_via_tool, dispatched_message_text)


async def process_message(message: ParsedMessage) -> None:
    """
    Main asynchronous message processing hook registered with Module A router.
    Orchestrates the entire agent response lifecycle with blue tick read receipts,
    multi-turn Firestore state persistence, and human typing pacing.
    """
    sender_phone = message.sender_phone
    profile_name = message.profile_name or "Client"

    logger.info(
        "Module B processing message from %s (%s) [type=%s]",
        profile_name,
        sender_phone,
        message.message_type,
    )

    # 1. Trigger blue tick read receipt and dispatch typing indicator immediately on WhatsApp
    if message.raw_message_id:
        try:
            await send_typing_indicator(message.raw_message_id)
        except Exception as read_err:
            logger.warning("Could not send typing indicator for message %s: %s", message.raw_message_id, read_err)

    try:
        agent = get_agent()

        # 2. Check live conversation history & Firestore business state
        from app.module_c.sessions import get_session_history, append_session_message
        past_history = await get_session_history(sender_phone, max_messages=10)
        is_continuing = len(past_history) > 0
        state_summary = await _get_client_state_summary(sender_phone)

        # 3. Build enriched context prompt
        prompt = _build_user_event_prompt(
            message,
            state_summary=state_summary,
            is_continuing_convo=is_continuing,
        )

        # 4. Execute agent reasoning & tool calling loop
        response_text, dispatched_via_tool, dispatched_message_text = await _execute_agent_turn(agent, prompt, message)

        # 5. Format incoming user text for persistent session recording
        user_text = message.message_content
        if not user_text or not str(user_text).strip():
            if message.media_filename:
                user_text = f"[{message.message_type}: {message.media_filename}]"
            elif message.media_id:
                user_text = f"[{message.message_type} upload]"
            else:
                user_text = f"[{message.message_type}]"

        # Record incoming user turn to persistent session history
        await append_session_message(sender_phone, "user", user_text)

        # If a messaging tool already dispatched a button/text message:
        if dispatched_via_tool:
            model_sent_text = dispatched_message_text or response_text or "[Interactive WhatsApp Message Sent]"
            await append_session_message(sender_phone, "model", model_sent_text)
            logger.info("Message was already sent via tool for %s. Recorded in session history.", sender_phone)
            return

        # Deliver generated text response if available
        if response_text and isinstance(response_text, str) and response_text.strip():
            clean_text = response_text.strip()
            # Cleanly strip any accidental markdown formatting (asterisks, hashes, backticks)
            for char in ["**", "*", "###", "##", "#", "`"]:
                clean_text = clean_text.replace(char, "")
            clean_text = clean_text.strip()

            # Record model turn into session history
            await append_session_message(sender_phone, "model", clean_text)

            # Human-like typing simulation pacing
            typing_delay = min(1.5, max(0.5, len(clean_text) * 0.008))
            await asyncio.sleep(typing_delay)

            logger.info("Sending agent response to %s: %s", sender_phone, clean_text[:120])
            await send_text_message(recipient_phone=sender_phone, text=clean_text)
        else:
            # Context-aware fallback response (maintains continuity if returning client)
            if is_continuing:
                fallback_msg = f"Thank you, {profile_name}. I have noted that. How would you like to proceed?"
            else:
                fallback_msg = f"Hi {profile_name}! Welcome to Al Astoora. How can we help automate or streamline your corporate services today?"

            await append_session_message(sender_phone, "model", fallback_msg)

            # Brief human pause
            await asyncio.sleep(0.5)
            await send_text_message(recipient_phone=sender_phone, text=fallback_msg)

    except Exception as e:
        logger.exception("Critical failure during agent processing for %s: %s", sender_phone, e)
        fallback_msg = (
            f"Hello {profile_name}, we are experiencing a brief technical delay processing your message. "
            "Please try again in a few moments, or let us know how we can assist you."
        )
        try:
            await send_text_message(recipient_phone=sender_phone, text=fallback_msg)
        except Exception as send_err:
            logger.error("Failed to send fallback message to %s: %s", sender_phone, send_err)


root_agent = None  # Lazy initialization via get_agent()


