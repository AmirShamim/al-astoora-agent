# Al Astoora Agent — Master Implementation Plan (SELF-CONTAINED)

> **PURPOSE:** This is the ONLY file any AI model needs to build, modify, or debug this project. It contains ALL domain knowledge, technical specs, and code contracts. Do NOT reference the hackathon planning files (00-overview.md through 11-module-d.md) — everything relevant is consolidated here.

---

## PROJECT IDENTITY

- **App:** Al Astoora Document Collector Agent  
- **What it does:** WhatsApp bot that collects, validates, and tracks client documents for professional services firms (corporate secretarial, accounting, immigration). Uses Gemini 3.7 Flash multimodal vision to inspect documents automatically.  
- **Owner:** Amir Shamim  
- **Hackathon:** All Things Agentic 2026 (Google/Devpost), Category: The Taskmaster  
- **Deadline:** Aug 31, 2026 5:00 PM PT  

---

## TECH STACK (LOCKED — DO NOT CHANGE)

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11 |
| Web Framework | FastAPI | >=0.115.0 |
| AI Agent Framework | Google ADK | >=2.6.0 (hackathon mandatory) |
| AI Model | Gemini 3.7 Flash | Model ID: `gemini-3.7-flash` |
| State Database | Firestore Native Mode | `google-cloud-firestore` |
| File Storage | Cloud Storage | `google-cloud-storage` |
| Hosting | Google Cloud Run | Docker container (python:3.11-slim) |
| WhatsApp API | Meta Cloud API v20.0 | via `httpx` async |
| Config | Pydantic Settings | `pydantic-settings` |

---

## GCP CONFIGURATION (LOCKED)

```
GCP_PROJECT_ID    = project-080b5971-eb4b-4d2b-a4c
GCP_LOCATION      = us-central1
GCS_BUCKET_NAME   = al-astoora-documents
SERVICE_ACCOUNT   = ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com
GEMINI_MODEL      = gemini-3.7-flash
CLOUD_RUN_URL     = https://al-astoora-agent-1019975245319.us-central1.run.app
```

---

## WHATSAPP CONFIGURATION (LOCKED)

```
WHATSAPP_PHONE_NUMBER_ID  = 1113443245192571
BOT_PHONE_NUMBER          = 919289581053
WEBHOOK_VERIFY_TOKEN      = al_astoora_secure_verify_token_2026
GRAPH_API_VERSION         = v20.0
```

---

## DEPLOYMENT (LOCKED)

Uses `Dockerfile` (python:3.11-slim) NOT Buildpacks. Deploy via Google Cloud Shell:

```bash
cd al-astoora-agent
gcloud run deploy al-astoora-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com \
  --set-env-vars "WHATSAPP_TOKEN=<token>,WHATSAPP_PHONE_NUMBER_ID=1113443245192571,BOT_PHONE_NUMBER=919289581053,WEBHOOK_VERIFY_TOKEN=al_astoora_secure_verify_token_2026,GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GEMINI_MODEL=gemini-3.7-flash"
```

---

## ARCHITECTURE

```
Meta WhatsApp Cloud API
         │
         ▼
  ┌──────────────────┐
  │  MODULE A         │  Webhook + Message Router
  │  [COMPLETED]      │  Receives → Filters → Parses → Dispatches
  └────────┬─────────┘
           │ ParsedMessage dataclass
           ▼
  ┌──────────────────┐
  │  MODULE B         │  Gemini 3.7 Agent (Google ADK)
  │  [IN PROGRESS]    │  Decides → Calls Tools → Sends WhatsApp Replies
  └──┬────────────┬──┘
     │            │
     ▼            ▼
  ┌──────────┐ ┌──────────┐
  │ MODULE C  │ │ MODULE D  │
  │ Firestore │ │ Document  │
  │ State     │ │ Validation│
  │[COMPLETED]│ │[COMPLETED]│
  └──────────┘ └──────────┘
```

---

## BUILD PHASES & STATUS

- [x] **Phase 0:** Project scaffold, config, Dockerfile, requirements, .env, .gitignore
- [x] **Phase 1:** Module A complete (webhook router, parser, filters, WhatsApp sender, 13 tests)
- [x] **Phase 2:** Module C complete (Firestore State Manager: leads, clients, docs, bookings CRUD, 19 tests)
- [x] **Phase 3:** Module D complete (Document Validation Engine: WhatsApp download, GCS storage, Gemini 3.7 Flash multimodal vision, 16 tests)
- [x] **Phase 4:** Module B complete (Google ADK Agent Orchestrator, tools, system prompt, fallback recovery, 17 tests)
- [ ] **Phase 5:** End-to-end testing
- [ ] **Phase 6:** Submission (README, architecture diagram, 4-min demo video)

---

## PROJECT STRUCTURE

```
Al Astoora Agent/
├── Dockerfile
├── Procfile
├── requirements.txt
├── .env / .env.example
├── .gitignore / .gcloudignore
├── README.md
├── implementation_plan.md          ← THIS FILE
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, /health, /webhook mount, Module B wireup [DONE]
│   ├── config.py                   # Pydantic Settings loader [DONE]
│   │
│   ├── module_a/                   # [DONE] Webhook + Message Router
│   │   ├── __init__.py
│   │   ├── router.py              # GET/POST /webhook, register_message_handler()
│   │   ├── parser.py              # ParsedMessage dataclass
│   │   └── filters.py             # is_valid_message_event(), is_self_reply()
│   │
│   ├── module_b/                   # [DONE] Agent Orchestrator
│   │   ├── __init__.py
│   │   ├── agent.py               # Google ADK Agent + process_message hook [DONE]
│   │   ├── system_prompt.py       # Full system prompt definition [DONE]
│   │   ├── whatsapp_sender.py     # send_text/button/list_message() [DONE]
│   │   └── tools.py               # 10 ADK tool functions bridging to C & D [DONE]
│   │
│   ├── module_c/                   # [DONE] Firestore State Manager
│   │   ├── __init__.py
│   │   ├── firestore_client.py
│   │   ├── leads.py
│   │   ├── clients.py
│   │   ├── documents.py
│   │   └── bookings.py
│   │
│   └── module_d/                   # [DONE] Document Validation Engine
│       ├── __init__.py
│       ├── media_downloader.py
│       ├── storage.py
│       └── validator.py
│
└── tests/
    ├── __init__.py
    ├── sample_payloads/            # [DONE] 6 JSON test payloads
    ├── test_module_a.py            # [DONE] 13 tests
    ├── test_module_b.py            # [DONE] 17 tests
    ├── test_module_c.py            # [DONE] 19 tests
    └── test_module_d.py            # [DONE] 16 tests
```

---

## EXISTING CODE CONTRACTS (DO NOT BREAK THESE)

### ParsedMessage (app/module_a/parser.py) — The Universal Message Object

```python
@dataclass(frozen=True)
class ParsedMessage:
    sender_phone: str           # "6591234567"
    profile_name: str           # "Ahmed Al-Rashid"
    message_type: str           # "text" | "image" | "document" | "interactive" | "unsupported"
    message_content: str        # text body, button ID, or caption
    media_id: Optional[str]     # WhatsApp media ID (images/docs only)
    media_filename: Optional[str]  # original filename (docs only)
    raw_timestamp: str
    raw_message_id: Optional[str]
    metadata: Dict[str, Any]    # {"interactive_type": "button_reply", "title": "...", "id": "..."}
```

### Router Dispatch Hook (app/module_a/router.py)

Module B registers its agent processing function via:
```python
from app.module_a.router import register_message_handler

async def agent_process_message(message: ParsedMessage) -> None:
    # Module B's main entry point
    ...

register_message_handler(agent_process_message)
```

### WhatsApp Sender (app/module_b/whatsapp_sender.py) — Already Built

```python
await send_text_message(recipient_phone: str, text: str)
await send_button_message(recipient_phone: str, body_text: str, buttons: List[Dict])
    # buttons = [{"id": "btn_1", "title": "Yes"}]  (max 3, title max 20 chars)
await send_list_message(recipient_phone: str, body_text: str, button_text: str, sections: List)
```

### Config (app/config.py) — Already Built

```python
from app.config import get_settings
settings = get_settings()
# settings.WHATSAPP_TOKEN, settings.GCP_PROJECT_ID, settings.GEMINI_MODEL, etc.
```

---

## PHASE 2: MODULE C — FIRESTORE STATE MANAGER [COMPLETED]

### Firestore Schema

**Collection: `leads`**
```
leads/{auto-id}
├── name: string              # "Ahmed Al-Rashid"
├── phone: string             # "6591234567"
├── interest: string          # "Singapore company registration"
├── source: string            # "whatsapp_bot"
├── captured_at: timestamp    # Firestore SERVER_TIMESTAMP
└── status: string            # "new" | "contacted" | "converted"
```

**Collection: `clients`**
```
clients/{phone}
├── name: string
├── phone: string
├── company: string | null
├── service_type: string      # "sg_company_registration"
├── onboarding_started: timestamp
├── onboarding_status: string # "in_progress" | "complete" | "stalled"
├── documents_required: int
├── documents_received: int
└── last_activity: timestamp
```

**Subcollection: `clients/{phone}/documents`**
```
clients/{phone}/documents/{doc_type}
├── doc_type: string          # "passport" | "proof_of_address" | "director_resolution"
├── status: string            # "pending" | "submitted" | "validated" | "rejected"
├── rejection_reason: string | null
├── file_url: string | null   # Cloud Storage URL
├── submitted_at: timestamp | null
├── validated_at: timestamp | null
└── attempts: int
```

**Collection: `intake_templates`**
```
intake_templates/{service_type}
├── service_name: string      # "Singapore Company Registration"
├── required_documents: array  # ["passport", "proof_of_address", "director_resolution"]
└── description: string
```

**Collection: `bookings`** (production feature)
```
bookings/{auto-id}
├── date: string              # "2026-08-20" (YYYY-MM-DD)
├── time: string              # "14:00" (HH:MM 24hr)
├── name: string
├── phone: string
├── booked_at: timestamp
└── status: string            # "confirmed" | "cancelled"
```

### Module C Functions (Pure CRUD — No Gemini, No WhatsApp)

**File: `app/module_c/firestore_client.py`**
- Singleton `google.cloud.firestore.AsyncClient` using `get_settings().GCP_PROJECT_ID`
- Auto-detects credentials (service account on Cloud Run, key file locally)

**File: `app/module_c/leads.py`**
```python
async def capture_lead(name: str, phone: str, interest: str) -> dict:
    # Check duplicate by phone → if exists return "already_captured"
    # Write to leads collection with SERVER_TIMESTAMP
    # Return {"success": True, "message": "Lead captured"}
```

**File: `app/module_c/clients.py`**
```python
async def get_or_create_client(phone: str, name: str, service_type: str) -> dict:
    # If clients/{phone} exists → return existing data
    # If not → create client + load intake_templates/{service_type}
    #        → create documents subcollection entries (all "pending")
    # Return client data + list of required documents with statuses

async def check_intake_status(phone: str) -> dict:
    # Read clients/{phone} + all documents subcollection
    # Return {total_required, received, pending: [], rejected: [], complete: bool}
```

**File: `app/module_c/documents.py`**
```python
async def update_document_status(phone: str, doc_type: str, status: str, file_url: str = None, rejection_reason: str = None) -> dict:
    # Write to clients/{phone}/documents/{doc_type}
    # Update clients/{phone} counters (documents_received)
    # If ALL docs validated → set onboarding_status = "complete"
    # Return {success: True, remaining_docs: []}
```

**File: `app/module_c/bookings.py`**
```python
async def check_available_slots(date: str) -> dict:
    # Read bookings where date == date
    # Compute available from predefined slots (e.g. 09:00-17:00, 30min intervals)
    # Return {date, available_slots: ["09:00", "09:30", ...]}

async def book_appointment(date: str, time: str, name: str, phone: str) -> dict:
    # Re-read to guard race condition → write if slot open
    # Return {success: True, date, time, confirmation: "..."}
```

### Module C Rules
- ONLY imports: `google.cloud.firestore`, `app.config`
- Every function returns a dict with a `success` boolean — NEVER raises exceptions to caller
- If Firestore unreachable → return `{"success": False, "error": "Database unavailable"}`

---

## PHASE 3: MODULE D — DOCUMENT VALIDATION ENGINE

### Pipeline: Download → Store → Analyze

**File: `app/module_d/media_downloader.py`**
```python
async def download_media(media_id: str) -> dict:
    # Step 1: GET https://graph.facebook.com/v20.0/{media_id} with Bearer token → get URL
    # Step 2: GET {url} with Bearer token → get raw bytes
    # Return {"success": True, "file_bytes": bytes, "mime_type": str}
    # On failure: {"success": False, "error": "Could not download file"}
```

**File: `app/module_d/storage.py`**
```python
async def upload_to_storage(file_bytes: bytes, client_phone: str, doc_type: str, filename: str) -> dict:
    # Upload to: gs://al-astoora-documents/clients/{client_phone}/{doc_type}/{timestamp}_{filename}
    # Return {"success": True, "file_url": "gs://..."}
    # On failure: {"success": False, "error": "..."} — validation continues even if storage fails
```

**File: `app/module_d/validator.py`**
```python
async def validate_document(media_id: str, expected_doc_type: str, client_phone: str) -> dict:
    # 1. Download media
    # 2. (Optional) Upload to Cloud Storage
    # 3. Send to Gemini 3.7 Flash multimodal with validation prompt
    # Return:
    # {
    #   "document_type": "passport",
    #   "extracted_fields": {"name": "...", "expiry_date": "...", "number": "..."},
    #   "is_valid": true/false,
    #   "issues": ["expired", "blurry", "wrong document type"],
    #   "client_message": "Your passport appears to be expired. Please send a valid one."
    # }
```

### Gemini Validation Prompt (used in validator.py)
```
You are a strict document validation expert for Al Astoora, a professional services agency.

Examine the attached image which is expected to be a '{expected_doc_type}'.

Extract the core fields (name, number, expiry date, etc.) from the document.

Validate that:
1. It is indeed a {expected_doc_type} (not a different document type).
2. It is fully readable without obstruction (no fingers, shadows, or glare covering text).
3. It is not expired (check expiry/validity date against today's date).
4. If it requires a signature (e.g., director resolution), verify it is signed.
5. The image is clear enough to read all important fields.

Respond ONLY with this exact JSON (no markdown, no explanation outside the JSON):
{
  "document_type": "detected document type",
  "extracted_fields": {},
  "is_valid": true or false,
  "issues": ["list of specific problems found"],
  "client_message": "A friendly, 1-2 sentence message to the client. If valid, confirm receipt. If invalid, explain exactly what to fix and ask them to resend."
}
```

### Module D Rules
- Uses `google.genai` SDK (NOT ADK) for the Gemini vision call
- Uses `httpx` for WhatsApp media download
- Uses `google.cloud.storage` for GCS upload
- NEVER sends WhatsApp messages — returns data for Module B to act on
- NEVER writes to Firestore — returns data for Module B to pass to Module C

---

## PHASE 4: MODULE B — GEMINI 3.7 AGENT (GOOGLE ADK)

### File: `app/module_b/agent.py`

```python
from google.adk import Agent

root_agent = Agent(
    name="al_astoora_agent",
    model="gemini-3.7-flash",
    instruction=SYSTEM_PROMPT,  # from system_prompt.py
    tools=[
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
    ],
)
```

### File: `app/module_b/tools.py`

ADK tool functions that bridge Module B → Module C and Module D. Each function must:
1. Have a clear docstring (ADK uses these for tool descriptions to the model)
2. Accept only simple types (str, int, bool) — no complex objects
3. Return a string or dict that Gemini can reason about

Example pattern:
```python
async def capture_lead(name: str, phone: str, interest: str) -> str:
    """Captures a new sales lead with contact information.
    Call this when a potential client expresses interest in services.
    Args:
        name: The client's full name.
        phone: The client's phone number.
        interest: What service the client is interested in.
    Returns:
        Confirmation message or duplicate notice.
    """
    from app.module_c.leads import capture_lead as _capture
    result = await _capture(name, phone, interest)
    return result.get("message", "Lead processing failed")
```

### File: `app/module_b/system_prompt.py`

The system prompt must define:
1. **Identity:** "You are Al Astoora's document collection assistant on WhatsApp."
2. **Services:** Singapore company registration, accounting, immigration consulting
3. **Intake rules:** Which documents per service (loaded dynamically via `check_intake_status`)
4. **Communication style:** Professional, warm, concise. Max 2-3 sentences per message. Never use markdown. Never use emojis excessively. Always respond in English.
5. **WhatsApp constraints:** Use `send_whatsapp_buttons` for choices (max 3 buttons, title max 20 chars). Use `send_whatsapp_list` for menus (max 10 items).
6. **Tool instructions:** When to call each tool:
   - New user mentions interest → `capture_lead`
   - User wants to start document submission → `get_or_create_client` then tell them what's needed
   - User asks "what do I still need?" → `check_intake_status`
   - User sends image/document → `validate_document` then `update_document_status` based on result
   - User wants appointment → `check_available_slots` then `book_appointment`
7. **Error handling:** If a tool fails, tell the client you're having temporary issues and to try again shortly. Never expose technical errors.
8. **Conversation flow:** Always acknowledge → process → respond. Never leave the user without a reply.

### Wiring Module B to Module A

In `app/main.py`, during startup:
```python
from app.module_a.router import register_message_handler
from app.module_b.agent import process_message  # The main agent entry point

register_message_handler(process_message)
```

---

## PHASE 5: END-TO-END TESTING

Test these flows on real WhatsApp:
1. **New user greeting** → bot introduces itself, offers services
2. **Lead capture** → user says "I'm interested in SG incorporation" → lead saved in Firestore
3. **Start intake** → user selects service → bot creates client + lists required docs
4. **Document submission** → user sends passport photo → Gemini validates → bot confirms or rejects with reason
5. **Rejected document** → user sends blurry photo → bot explains what's wrong, asks to resend
6. **Intake completion** → user submits all docs → bot congratulates, marks onboarding complete
7. **Booking** → user asks for appointment → bot shows available slots → user picks one → confirmed

---

## PHASE 6: SUBMISSION DELIVERABLES

1. **Architecture diagram** — use the ASCII diagram above or generate a visual
2. **README.md** — setup instructions, deployment command, tech stack
3. **Demo video** — ≤4 minutes, public YouTube, must show:
   - WhatsApp conversation demonstrating full flow
   - Google Cloud Console showing Cloud Run service running
   - Firestore data being created/updated in real-time
4. **Devpost submission** — text description covering: features, tech used, data sources, learnings
5. **Bonus:** Blog post (+0.2), LinkedIn post with #AllThingsAgenticHackathon (+0.2)

---

## RULES FOR AI MODELS WORKING ON THIS PROJECT

1. **Never change Phase 0/1 code** unless fixing a bug. Module A and WhatsApp sender are complete and tested.
2. **Follow the module boundary rules strictly.** Module C only talks to Firestore. Module D only downloads/validates. Module B orchestrates.
3. **Every function returns a dict with `success: bool`** — never raise raw exceptions to callers.
4. **Use `async/await` everywhere** — FastAPI runs async, Firestore has async client, httpx is async.
5. **Test locally first** with `pytest tests/ -v`, then deploy with the gcloud command above.
6. **After any code change:** `git add . ; git commit -m "description" ; git push` then in Google Cloud Shell: `git pull ; gcloud run deploy ...`
7. **The .env file contains real credentials** — never commit it to a public repo. The `.gitignore` already excludes `.env`.
