"""
Module B: Google ADK Agent Orchestrator for Al Astoora.
Orchestrates Gemini 3.7 Flash with Google ADK tool calling, handling incoming
ParsedMessage events from Module A, executing tools, and delivering WhatsApp responses.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Dict, List, Optional

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
except ImportError:
    try:
        from google.adk.agents import Agent
    except ImportError:
        # Fallback dummy class if ADK is mocked or running in minimal test environment
        class Agent:  # type: ignore
            def __init__(self, name: str, model: str, instruction: str, tools: Optional[List[Any]] = None):
                self.name = name
                self.model = model
                self.instruction = instruction
                self.tools = tools or []


_agent_instance: Optional[Any] = None


def create_adk_agent() -> Any:
    """
    Creates and configures the Google ADK root agent instance for Al Astoora.
    Configured with Gemini 3.7 Flash, system prompt, and all Module C/D tools.
    """
    settings = get_settings()
    model_name = settings.GEMINI_MODEL or "gemini-3.7-flash"
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
Review the client's message and history. If this is a document/image upload (Media ID provided), call the 'validate_document' tool. If the user inquires about services or appointments, call the relevant tool. Respond to the client on WhatsApp concisely in English without any markdown syntax.
"""


async def _execute_agent_turn(agent: Any, prompt: str, message: ParsedMessage) -> Optional[str]:
    """
    Executes an agent reasoning and tool invocation turn with Google ADK or fallback runner.
    Returns the agent's textual response if produced.
    """
    # 1. If agent has async run method
    if hasattr(agent, "run_async") and callable(agent.run_async):
        res = await agent.run_async(prompt)
        return str(res) if res is not None else None

    # 2. If agent has synchronous or callable run method
    if hasattr(agent, "run") and callable(agent.run):
        res = agent.run(prompt)
        if inspect.isawaitable(res):
            res = await res
        return str(res) if res is not None else None

    # 3. If agent is a custom callable / mock
    if callable(agent):
        res = agent(prompt)
        if inspect.isawaitable(res):
            res = await res
        return str(res) if res is not None else None

    # 4. Direct GenAI model invocation fallback with tools
    try:
        from google import genai
        from google.genai import types
        from app.module_d.validator import get_genai_client

        client = get_genai_client()
        settings = get_settings()

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            tools=ALL_TOOLS,
        )

        model_name = settings.GEMINI_MODEL or "gemini-3.7-flash"
        if hasattr(client, "aio") and hasattr(client.aio, "models"):
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
        else:
            res = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            response = await res if inspect.isawaitable(res) else res

        # Check for function calls / tool calls
        candidates = getattr(response, "candidates", [])
        if candidates and hasattr(candidates[0], "content") and hasattr(candidates[0].content, "parts"):
            for part in candidates[0].content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    fn_name = getattr(fn_call, "name", "")
                    fn_args = getattr(fn_call, "args", {}) or {}
                    logger.info("Agent requested tool call: %s with args: %s", fn_name, fn_args)
                    # Find tool in ALL_TOOLS
                    tool_map = {t.__name__: t for t in ALL_TOOLS}
                    if fn_name in tool_map:
                        target_tool = tool_map[fn_name]
                        tool_res = target_tool(**fn_args)
                        if inspect.isawaitable(tool_res):
                            tool_res = await tool_res
                        logger.info("Tool %s completed: %s", fn_name, str(tool_res)[:200])

        return getattr(response, "text", None)
    except Exception as e:
        logger.warning("Direct GenAI client turn encountered: %s", e)
        return None


async def process_message(message: ParsedMessage) -> None:
    """
    Main asynchronous message processing hook registered with Module A router.
    Orchestrates the entire agent response lifecycle:
    1. Formats incoming WhatsApp context.
    2. Runs the Google ADK Gemini agent with tools.
    3. Sends response to client via WhatsApp if not already dispatched.
    4. Catches all errors and ensures a graceful fallback message is delivered.
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
        response_text = await _execute_agent_turn(agent, prompt, message)

        # If agent produced text that hasn't been sent via WhatsApp tools, deliver it
        if response_text and isinstance(response_text, str) and response_text.strip():
            clean_text = response_text.strip()
            # Remove any accidental markdown syntax
            clean_text = clean_text.replace("**", "").replace("*", "")
            logger.info("Sending agent response to %s: %s", sender_phone, clean_text[:120])
            await send_text_message(recipient_phone=sender_phone, text=clean_text)

    except Exception as e:
        logger.exception("Critical failure during agent processing for %s: %s", sender_phone, e)
        # Resilient Fallback: Never leave the user hanging
        fallback_msg = (
            f"Hello {profile_name}, we are experiencing a brief technical delay processing your message. "
            "Please try again in a few moments, or let us know how we can assist you."
        )
        try:
            await send_text_message(recipient_phone=sender_phone, text=fallback_msg)
        except Exception as send_err:
            logger.error("Failed to send emergency fallback message to %s: %s", sender_phone, send_err)


root_agent = get_agent()
