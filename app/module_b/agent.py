"""
Module B: Google ADK Agent Orchestrator for Al Astoora Agency.
Orchestrates Gemini with Google ADK tool calling, handling incoming
ParsedMessage events from Module A, executing tools, and delivering WhatsApp responses.
"""

import asyncio
import inspect
import json
import logging
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
    book_appointment,
    send_whatsapp_text,
    send_whatsapp_buttons,
    send_whatsapp_list,
)
from app.module_b.whatsapp_sender import send_text_message

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
MESSAGING_TOOL_NAMES = {"send_whatsapp_text", "send_whatsapp_buttons", "send_whatsapp_list"}


def create_adk_agent() -> Any:
    """
    Creates and configures the Google ADK root agent instance for Al Astoora.
    Configured with Gemini, system prompt, and all Module C/D tools.
    """
    settings = get_settings()
    model_name = settings.GEMINI_MODEL or "gemini-3.6-flash"
    logger.info("Initializing Google ADK Agent 'al_astoora_agent' with model: %s", model_name)

    agent = Agent(
        name="al_astoora_agent",
        model=model_name,
        instruction=SYSTEM_PROMPT,
        tools=ALL_TOOLS,
    )
    return agent


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


def _build_user_event_prompt(message: ParsedMessage) -> str:
    """
    Formats the incoming WhatsApp message event and metadata into a structured
    context prompt for the Gemini agent.
    """
    metadata_json = json.dumps(message.metadata or {})
    media_info = f"Media ID: {message.media_id}" if message.media_id else "No Media attached"
    if message.media_filename:
        media_info += f" (Filename: {message.media_filename})"

    return f"""[INCOMING WHATSAPP MESSAGE EVENT]
- Sender Phone: {message.sender_phone}
- Sender Profile Name: {message.profile_name}
- Message Type: {message.message_type}
- Message Content / User Text: {message.message_content}
- Media Details: {media_info}
- Metadata: {metadata_json}

Instruction:
Follow the consultative workflow for Al Astoora Agency:
1. If the user shares interest or is greeting, call 'capture_lead' to record them.
2. If this is a document/image upload (Media ID provided), check which document is pending and call 'validate_document'.
3. If they inquire about consultations, call 'check_available_slots' or 'book_appointment'.
4. If they confirm starting a service, call 'get_or_create_client'.
5. Respond concisely in English without any markdown syntax. If you use a WhatsApp messaging tool (e.g. send_whatsapp_buttons), you do not need to repeat the same text in your final response.
"""


async def _execute_agent_turn(agent: Any, prompt: str, message: ParsedMessage) -> Tuple[Optional[str], bool]:
    """
    Executes an agent reasoning and tool invocation turn with Google ADK or fallback runner.
    Returns:
        tuple (response_text: Optional[str], message_already_sent_via_tool: bool)
    """
    dispatched_via_tool = False

    # 1. If agent has async run method
    if hasattr(agent, "run_async") and callable(agent.run_async):
        logger.info("Using ADK Agent.run_async path")
        try:
            res_obj = agent.run_async(prompt)
            # Check if it returns an async generator
            if hasattr(res_obj, "__aiter__"):
                accumulated_text = []
                async for event in res_obj:
                    if isinstance(event, str):
                        accumulated_text.append(event)
                    elif hasattr(event, "text") and event.text:
                        accumulated_text.append(str(event.text))
                    elif hasattr(event, "content"):
                        accumulated_text.append(str(event.content))
                    else:
                        accumulated_text.append(str(event))
                final_text = "".join(accumulated_text).strip()
                return (final_text if final_text else None, False)
            elif inspect.isawaitable(res_obj):
                res = await res_obj
                return (str(res) if res is not None else None, False)
            else:
                return (str(res_obj) if res_obj is not None else None, False)
        except Exception as adk_err:
            logger.warning("ADK Agent.run_async error, will try next execution path: %s", adk_err)

    # 2. If agent has synchronous or callable run method
    if hasattr(agent, "run") and callable(agent.run):
        logger.info("Using ADK Agent.run path")
        try:
            res = agent.run(prompt)
            if inspect.isawaitable(res):
                res = await res
            return (str(res) if res is not None else None, False)
        except Exception as adk_run_err:
            logger.warning("ADK Agent.run error, will try next execution path: %s", adk_run_err)

    # 3. If agent is a custom callable / mock
    if callable(agent):
        logger.info("Using callable agent path")
        try:
            res = agent(prompt)
            if inspect.isawaitable(res):
                res = await res
            return (str(res) if res is not None else None, False)
        except Exception as call_err:
            logger.warning("Callable agent error, falling back to GenAI: %s", call_err)

    # 4. Direct GenAI model invocation fallback with multi-turn tool loop
    logger.info("Using direct GenAI fallback path")
    try:
        from google import genai
        from google.genai import types
        from app.module_d.validator import get_genai_client

        client = get_genai_client()
        settings = get_settings()
        model_name = settings.GEMINI_MODEL or "gemini-3.6-flash"

        tool_map = {t.__name__: t for t in ALL_TOOLS}

        func_declarations = []
        for tool_fn in ALL_TOOLS:
            try:
                func_declarations.append(tool_fn)
            except Exception as td_err:
                logger.warning("Could not add tool %s: %s", tool_fn.__name__, td_err)

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            tools=func_declarations,
        )

        contents = [prompt]

        MAX_TURNS = 8
        for turn in range(MAX_TURNS):
            logger.info("GenAI turn %d, contents length: %d", turn, len(contents))

            if hasattr(client, "aio") and hasattr(client.aio, "models"):
                response = await client.aio.models.generate_content(
                    model=model_name, contents=contents, config=config,
                )
            else:
                res = client.models.generate_content(
                    model=model_name, contents=contents, config=config,
                )
                response = await res if inspect.isawaitable(res) else res

            candidates = getattr(response, "candidates", [])
            has_function_calls = False
            function_response_parts = []

            if candidates and hasattr(candidates[0], "content") and hasattr(candidates[0].content, "parts"):
                if turn == 0 and isinstance(contents[0], str):
                    try:
                        contents = [
                            types.Content(role="user", parts=[types.Part(text=prompt)])
                        ]
                    except Exception:
                        contents = [
                            {"role": "user", "parts": [{"text": prompt}]}
                        ]

                contents.append(candidates[0].content)

                for part in candidates[0].content.parts:
                    fn_call = getattr(part, "function_call", None)
                    if fn_call:
                        has_function_calls = True
                        fn_name = getattr(fn_call, "name", "")
                        fn_args = dict(getattr(fn_call, "args", {}) or {})
                        logger.info("Agent tool call [turn %d]: %s(%s)", turn, fn_name, fn_args)

                        # Check if this tool already dispatches a message to WhatsApp
                        if fn_name in MESSAGING_TOOL_NAMES:
                            dispatched_via_tool = True

                        tool_result = "Tool not found"
                        if fn_name in tool_map:
                            try:
                                target_tool = tool_map[fn_name]
                                tool_result = target_tool(**fn_args)
                                if inspect.isawaitable(tool_result):
                                    tool_result = await tool_result
                                logger.info("Tool %s result: %s", fn_name, str(tool_result)[:200])
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
                try:
                    tool_content = types.Content(role="user", parts=function_response_parts)
                except Exception:
                    tool_content = {"role": "user", "parts": function_response_parts}
                contents.append(tool_content)
                continue

            # No more tool calls
            text_result = getattr(response, "text", None)
            logger.info(
                "GenAI finished (turn %d): text='%s', dispatched_via_tool=%s",
                turn,
                str(text_result)[:100] if text_result else "None",
                dispatched_via_tool,
            )
            return (text_result, dispatched_via_tool)

        logger.warning("Agent exceeded max %d turns", MAX_TURNS)
        return (None, dispatched_via_tool)
    except Exception as e:
        logger.exception("Direct GenAI fallback FAILED: %s", e)
        return (None, dispatched_via_tool)


async def process_message(message: ParsedMessage) -> None:
    """
    Main asynchronous message processing hook registered with Module A router.
    Orchestrates the entire agent response lifecycle.
    """
    sender_phone = message.sender_phone
    profile_name = message.profile_name or "Client"

    logger.info(
        "Module B processing message from %s (%s) [type=%s]",
        profile_name,
        sender_phone,
        message.message_type,
    )

    try:
        agent = get_agent()
        prompt = _build_user_event_prompt(message)

        # Execute agent reasoning & tool calling loop
        response_text, dispatched_via_tool = await _execute_agent_turn(agent, prompt, message)

        # If a messaging tool already dispatched a button/text message, don't send a duplicate!
        if dispatched_via_tool:
            logger.info("Message was already sent via tool for %s. Skipping extra text dispatch.", sender_phone)
            return

        # Deliver generated text response if available
        if response_text and isinstance(response_text, str) and response_text.strip():
            clean_text = response_text.strip()
            # Remove any accidental markdown syntax
            clean_text = clean_text.replace("**", "").replace("*", "")
            logger.info("Sending agent response to %s: %s", sender_phone, clean_text[:120])
            await send_text_message(recipient_phone=sender_phone, text=clean_text)
        else:
            # Fallback acknowledgment
            logger.warning("Sending fallback greeting to %s (%s)", profile_name, sender_phone)
            fallback_msg = (
                f"Hello {profile_name}! Welcome to Al Astoora Agency. "
                "How can we assist you today? We specialize in corporate secretarial, accounting, and immigration consulting."
            )
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


root_agent = get_agent()
