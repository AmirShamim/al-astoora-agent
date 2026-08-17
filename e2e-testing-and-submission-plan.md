# Phase 5 & 6: End-to-End Testing + Submission Deliverables

## Current Status

Your Cloud Run service at `https://al-astoora-agent-1019975245319.us-central1.run.app` is **live and healthy** — the `/health` endpoint returns `200 OK`. All 4 phases of code are deployed. However, the code review found **one critical bug** and several items that need attention before end-to-end testing will actually work.

---

## 🔴 CRITICAL BUG: GenAI Fallback Loop in agent.py (Lines 131–182)

> [!CAUTION]
> The `_execute_agent_turn` function's **fallback path** (path #4, used when ADK `run_async`/`run` methods aren't available) has a broken multi-step tool calling loop. When Gemini requests a tool call (e.g., `validate_document`), the code:
> 1. ✅ Correctly parses the `function_call` from the response
> 2. ✅ Correctly executes the tool function
> 3. ❌ **Never sends the tool result back to the model** — it immediately returns `getattr(response, "text", None)`, which is `None` during a tool call
>
> **Impact**: If the deployed container is using the fallback path (because `google.adk.Agent` doesn't have a `run_async` or `run` method that works as expected), then every message requiring tool calls — lead capture, document validation, intake status — **will silently fail**. The agent calls the tool but doesn't know the result, so the user gets either no reply or the fallback error message.

### Fix Required

Replace the fallback loop (lines 131–182 in `agent.py`) with a proper multi-turn conversation loop that:
1. Calls `generate_content` with the user prompt
2. If the model returns `function_call` parts → execute each tool
3. Build a `FunctionResponse` with the tool results
4. Append to conversation history and call `generate_content` again
5. Repeat until the model produces a text response (no more tool calls)
6. Return that text response

---

## 🟡 Issue: ADK Agent Import & Compatibility

> [!WARNING]
> The code tries `from google.adk import Agent`, then `from google.adk.agents import Agent`, and finally falls back to a dummy class. On Cloud Run, the actual `google-adk>=2.6.0` package is installed, but the `Agent` class may not expose `run_async()` or `run()` methods that match the code's expectations (paths #1–#3 in `_execute_agent_turn`). If none of those paths match, it falls to the broken fallback loop.
>
> **You need to verify** which path your deployed container actually takes by checking Cloud Run logs.

---

## 🟡 Issue: `GEMINI_LOCATION` Mismatch

> [!IMPORTANT]
> In `config.py`, `GEMINI_LOCATION` defaults to `"global"`. In `.env`, only `GCP_LOCATION=us-central1` is set. The `get_genai_client()` in `validator.py` uses `settings.GEMINI_LOCATION` (which resolves to `"global"`) for Vertex AI initialization. This may cause `400 Bad Request` errors from the Gemini API.
>
> **Fix**: Either add `GEMINI_LOCATION=us-central1` to the Cloud Run env vars, or change the default in `config.py` to `us-central1`.

---

## 🟢 Things That Look Correct

| Component | Status | Notes |
|-----------|--------|-------|
| Module A (Webhook Router) | ✅ Solid | GET/POST `/webhook`, filters, parser, self-reply guard all well-structured |
| Module A → Module B wiring | ✅ Correct | `register_message_handler(process_message)` in `main.py` |
| Module B Tools (tools.py) | ✅ Correct | All 10 tools have clear docstrings, simple types, error handling |
| Module B System Prompt | ✅ Good | Complete identity, services, tool instructions, WhatsApp constraints |
| Module C (Firestore CRUD) | ✅ Correct | All functions return `{success: bool}` dicts, proper error handling |
| Module D (Validation) | ✅ Correct | Download → Store → Gemini analysis pipeline, proper boundaries |
| Dockerfile | ✅ Correct | `python:3.11-slim`, proper build, `PORT=8080` |
| Cloud Run health | ✅ Verified | Returns `{"status": "healthy"}` |
| Test suite | ✅ 72 tests | Comprehensive unit/integration coverage |

---

## Proposed Changes

### 1. Fix the Critical Bug in agent.py

#### [MODIFY] [agent.py](file:///g:/My%20Drive/Business%20Work/al-astoora-agency/hackathon-2026/Al%20Astoora%20Agent/app/module_b/agent.py)

Replace the fallback `generate_content` block (lines 131–182) with a proper multi-turn tool-calling loop:

```python
# 4. Direct GenAI model invocation fallback with multi-turn tool loop
try:
    from google import genai
    from google.genai import types
    from app.module_d.validator import get_genai_client

    client = get_genai_client()
    settings = get_settings()
    model_name = settings.GEMINI_MODEL or "gemini-3.7-flash"

    # Build tool declarations for GenAI
    tool_map = {t.__name__: t for t in ALL_TOOLS}

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        temperature=0.2,
        tools=ALL_TOOLS,
    )

    # Multi-turn conversation history
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    MAX_TURNS = 8  # Safety limit to prevent infinite loops
    for turn in range(MAX_TURNS):
        if hasattr(client, "aio") and hasattr(client.aio, "models"):
            response = await client.aio.models.generate_content(
                model=model_name, contents=contents, config=config,
            )
        else:
            res = client.models.generate_content(
                model=model_name, contents=contents, config=config,
            )
            response = await res if inspect.isawaitable(res) else res

        # Check for function calls
        candidates = getattr(response, "candidates", [])
        has_function_calls = False
        function_responses = []

        if candidates and hasattr(candidates[0], "content") and hasattr(candidates[0].content, "parts"):
            # Append the model's response to conversation history
            contents.append(candidates[0].content)

            for part in candidates[0].content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call:
                    has_function_calls = True
                    fn_name = getattr(fn_call, "name", "")
                    fn_args = dict(getattr(fn_call, "args", {}) or {})
                    logger.info("Agent tool call [turn %d]: %s(%s)", turn, fn_name, fn_args)

                    # Execute the tool
                    tool_result = "Tool not found"
                    if fn_name in tool_map:
                        target_tool = tool_map[fn_name]
                        tool_result = target_tool(**fn_args)
                        if inspect.isawaitable(tool_result):
                            tool_result = await tool_result
                        logger.info("Tool %s result: %s", fn_name, str(tool_result)[:200])

                    # Build FunctionResponse
                    function_responses.append(
                        types.Part.from_function_response(
                            name=fn_name,
                            response={"result": str(tool_result)},
                        )
                    )

        if has_function_calls and function_responses:
            # Append tool results and loop for next model turn
            contents.append(types.Content(role="user", parts=function_responses))
            continue

        # No more tool calls — return the text response
        return getattr(response, "text", None)

    logger.warning("Agent exceeded max %d turns", MAX_TURNS)
    return None
except Exception as e:
    logger.warning("Direct GenAI client turn encountered: %s", e)
    return None
```

### 2. Fix GEMINI_LOCATION Default

#### [MODIFY] [config.py](file:///g:/My%20Drive/Business%20Work/al-astoora-agency/hackathon-2026/Al%20Astoora%20Agent/app/config.py)

Change `GEMINI_LOCATION` default from `"global"` to `"us-central1"` to match the GCP project region.

### 3. Upgrade README.md for Submission

#### [MODIFY] [README.md](file:///g:/My%20Drive/Business%20Work/al-astoora-agency/hackathon-2026/Al%20Astoora%20Agent/README.md)

Rewrite to include:
- Full architecture diagram (polished)
- All prerequisites listed
- Step-by-step local setup and Cloud Run deployment
- Environment variable table
- Meta webhook configuration steps
- Tech stack table
- How to run tests

### 4. Verify with Cloud Run Logs

Before deploying fixes, check the current Cloud Run logs to understand:
- Which path in `_execute_agent_turn` is actually being taken
- Whether there are `google.adk` import errors
- Whether Gemini API calls are failing (GEMINI_LOCATION issue)
- Whether WhatsApp messages are being received

---

## Verification Plan

### Phase 5: End-to-End Testing Sequence

After deploying the bug fix, test these 7 scenarios via real WhatsApp:

| # | Test | Expected Outcome |
|---|------|-----------------|
| 1 | Send "Hi" to bot | Bot greets, introduces Al Astoora, asks about services |
| 2 | Say "I'm interested in SG company registration" | Bot captures lead in Firestore, asks if ready to start |
| 3 | Confirm to start intake | Bot creates client record, lists 3 required docs (passport, proof_of_address, director_resolution) |
| 4 | Send a clear passport photo | Gemini validates → bot confirms receipt, shows remaining docs |
| 5 | Send a blurry/bad photo | Gemini rejects → bot explains what's wrong, asks to resend |
| 6 | Ask "What do I still need?" | Bot shows intake status with pending/validated/rejected docs |
| 7 | Ask for appointment | Bot checks slots, presents options, confirms booking |

### Automated Tests
```bash
pytest tests/ -v --tb=short
```

### Manual Cloud Run Log Inspection
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=al-astoora-agent" --limit=50 --format=json
```

---

## Phase 6: Submission Deliverables Checklist

| # | Deliverable | Status | Action Needed |
|---|-------------|--------|---------------|
| 1 | Category: The Taskmaster | ❌ | Select on Devpost |
| 2 | Cloud Run URL | ✅ | `https://al-astoora-agent-1019975245319.us-central1.run.app` |
| 3 | Text Description | ❌ | Write 4-section description (features, tech, data sources, learnings) |
| 4 | GitHub Repository | ❌ | Push final code, share with `testing@devpost.com` + `cloudhackathons@google.com` |
| 5 | README with setup instructions | 🟡 | Current README is outdated/minimal — needs major rewrite |
| 6 | Architecture Diagram | 🟡 | ASCII diagram exists — need polished visual version |
| 7 | Demo Video (≤4 min, YouTube) | ❌ | Record after E2E testing passes |
| 8 | Blog Post (+0.2 bonus) | ❌ | Optional — Medium or dev.to post |
| 9 | Social Media Post (+0.2 bonus) | ❌ | LinkedIn post with #AllThingsAgenticHackathon |

---

## Recommended Execution Order

1. **Fix the critical agent.py bug** (multi-turn tool loop)
2. **Fix GEMINI_LOCATION** default
3. **Run unit tests** locally to confirm nothing breaks
4. **Deploy to Cloud Run** with fixes
5. **Check Cloud Run logs** to verify correct execution path
6. **Run E2E WhatsApp tests** (7 scenarios above)
7. **Rewrite README.md** for submission quality
8. **Generate architecture diagram** (visual, polished)
9. **Write Devpost text description**
10. **Record demo video** (≤4 min)
11. **Submit on Devpost**
12. *(Optional)* Blog post + LinkedIn post for bonus points
