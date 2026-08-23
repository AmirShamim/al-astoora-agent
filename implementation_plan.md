# Al Astoora Agent — Master Implementation Plan & Code Contracts

> **PURPOSE:** Self-contained engineering reference containing all code contracts, API signatures, database schemas, and architectural boundaries for the Al Astoora Document Collector Agent.

---

## Project Identity & Hackathon Metadata

- **Application Name:** Al Astoora Document Collector Agent
- **Description:** Autonomous WhatsApp agent for client document collection, multimodal validation, and onboarding tracking.
- **Hackathon:** Google All Things Agentic Hackathon 2026
- **Category:** The Taskmaster
- **Entrant:** Amir Shamim (Individual Entry)
- **Production URL:** `https://al-astoora-agent-1019975245319.asia-south1.run.app`

---

## Locked Tech Stack & Cloud Infrastructure

| Layer | Component | Version / Specification |
|---|---|---|
| **Runtime & Language** | Python | 3.11 |
| **Web Server Framework** | FastAPI | >= 0.115.0 (ASGI via Uvicorn) |
| **AI Agent Framework** | Google ADK + google-genai SDK | `google-adk>=2.6.0`, `google-genai>=1.0.0` |
| **AI Vision & Reasoning** | Gemini 3.7 Flash | Model ID: `gemini-3.7-flash` (`GEMINI_LOCATION=global`) |
| **Database** | Google Cloud Firestore | Native Mode (`google-cloud-firestore>=2.16.0`) |
| **File Store** | Google Cloud Storage | Regional Bucket: `al-astoora-documents` |
| **Compute & Hosting** | Google Cloud Run | Containerized (`python:3.11-slim`), region: `asia-south1` |
| **External Messaging** | Meta WhatsApp Cloud API | Direct Integration, v26.0 (Async via `httpx`) |
| **Config Management** | Pydantic Settings | `pydantic-settings>=2.2.0` |

---

## Locked System Configuration

```python
GCP_PROJECT_ID           = "project-080b5971-eb4b-4d2b-a4c"
GCP_LOCATION             = "asia-south1"
GEMINI_LOCATION          = "global"
GEMINI_MODEL             = "gemini-3.7-flash"
GEMINI_THINKING_LEVEL    = "low"
GEMINI_THINKING_BUDGET   = 0
GCS_BUCKET_NAME          = "al-astoora-documents"
SERVICE_ACCOUNT          = "ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com"
WHATSAPP_PHONE_NUMBER_ID = "1113443245192571"
BOT_PHONE_NUMBER         = "919289581053"
WEBHOOK_VERIFY_TOKEN     = "al_astoora_secure_verify_token_2026"
GRAPH_API_VERSION        = "v26.0"
CLOUD_RUN_URL            = "https://al-astoora-agent-1019975245319.asia-south1.run.app"
```

---

## Build Status (All 4 Core Phases Complete ✅)

- [x] **Phase 0: Scaffold & Infrastructure** — Dockerfile, config, dependencies, env loader.
- [x] **Phase 1: Module A (Webhook Router & Parser)** — 13 tests (`test_module_a.py`).
- [x] **Phase 2: Module C (Firestore State Manager)** — 19 tests (`test_module_c.py`).
- [x] **Phase 3: Module D (Multimodal Validation Engine)** — 16 tests (`test_module_d.py`).
- [x] **Phase 4: Module B (Gemini 3.7 Agent Orchestrator)** — 17 tests (`test_module_b.py`).
  - *Resolved: Multi-turn tool calling loop and GenAI fallback are fully implemented and verified.*
- [ ] **Phase 5: End-to-End Testing** — 7 real-world WhatsApp conversational scenarios.
- [ ] **Phase 6: Submission Deliverables** — Demo video, visual diagram, README, Devpost text.

**Total Test Coverage:** **72 automated tests** passing across all 4 modules.

---

## Code Contracts & Module Interfaces

### 1. Module A: Universal Data Object (`app/module_a/parser.py`)

```python
@dataclass(frozen=True)
class ParsedMessage:
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
```

### 2. Module A: Message Handler Registry (`app/module_a/router.py`)

```python
def register_message_handler(handler: Callable[[ParsedMessage], Awaitable[None]]) -> None:
    """Registers the async agent callback function to handle parsed WhatsApp messages."""
```

### 3. Module B: WhatsApp Messaging Interface (`app/module_b/whatsapp_sender.py`)

```python
async def send_text_message(recipient_phone: str, text: str) -> Dict[str, Any]: ...
async def send_button_message(recipient_phone: str, body_text: str, buttons: List[Dict[str, str]], header_text: Optional[str] = None, footer_text: Optional[str] = None) -> Dict[str, Any]: ...
async def send_list_message(recipient_phone: str, body_text: str, button_text: str, sections: List[Dict[str, Any]], title: Optional[str] = None, footer_text: Optional[str] = None) -> Dict[str, Any]: ...
async def send_typing_indicator(message_id: str) -> Dict[str, Any]: ...
async def mark_message_as_read(message_id: str) -> Dict[str, Any]: ...
```

---

## 12 Active Agent Tools (`app/module_b/tools.py`)

1. **`capture_lead(name: str, phone: str, interest: str) -> str`**
2. **`get_or_create_client(phone: str, name: str, service_type: str) -> str`**
3. **`check_intake_status(phone: str) -> str`**
4. **`update_document_status(phone: str, doc_type: str, status: str, file_url: Optional[str], rejection_reason: Optional[str]) -> str`**
5. **`validate_document(media_id: str, expected_doc_type: str, client_phone: str, original_filename: Optional[str]) -> str`**
6. **`check_available_slots(recipient_phone: Optional[str], phone: Optional[str], date: str) -> str`**
7. **`send_booking_buttons(recipient_phone: Optional[str], phone: Optional[str], date: str) -> str`**
8. **`send_interactive_booking_slots(recipient_phone: Optional[str], phone: Optional[str], date: str) -> str`**
9. **`book_appointment(date: str, time: str, name: Optional[str], phone: Optional[str]) -> str`**
10. **`send_whatsapp_text(recipient_phone: str, text: str) -> str`**
11. **`send_whatsapp_buttons(recipient_phone: str, body_text: str, buttons: List[Dict[str, str]], header_text: Optional[str], footer_text: Optional[str]) -> str`**
12. **`send_whatsapp_list(recipient_phone: str, body_text: str, button_text: str, sections: List[Dict[str, Any]], title: Optional[str], footer_text: Optional[str]) -> str`**

---

## Complete Firestore Database Schema (`app/module_c/`)

### 1. `leads/{auto-id}`
`name` (str), `phone` (str), `interest` (str), `source` ("whatsapp_bot"), `captured_at` (SERVER_TIMESTAMP), `status` ("new").

### 2. `clients/{phone}` & `clients/{phone}/documents/{doc_type}`
- **Parent:** `name`, `phone`, `company`, `service_type`, `onboarding_started`, `onboarding_status` ("in_progress" | "complete"), `documents_required` (int), `documents_received` (int), `last_activity`.
- **Subcollection:** `doc_type`, `status` ("pending" | "submitted" | "validated" | "rejected"), `rejection_reason` (str | null), `file_url` (str | null), `submitted_at`, `validated_at`, `attempts` (int).

### 3. `intake_templates/{service_type}`
`service_name` (str), `required_documents` (list of str), `description` (str).  
*Templates:* `sg_company_registration`, `accounting_services`, `immigration_consulting`, `general_corporate_services`.

### 4. `bookings/{auto-id}`
`date` (YYYY-MM-DD), `friendly_date`, `time` (HH:MM), `time_label`, `name`, `phone`, `booked_at`, `status` ("confirmed" | "cancelled").

### 5. `sessions/{phone}`
`phone` (str), `messages` (list of maps `[{"role": "user"|"model", "text": "...", "timestamp": "..."}]`), `updated_at` (timestamp).

### 6. `document_submissions/{auto-id}` (SaaS Audit Log)
`phone`, `doc_type`, `is_valid` (bool), `status`, `extracted_fields` (map), `issues` (list of str), `file_url`, `client_message`, `eligibility_assessment` (map), `media_id`, `metadata`, `submitted_at`.

---

## Multimodal Validation Pipeline (`app/module_d/`)

1. **`media_downloader.py`:** Two-step Meta Graph API v26.0 authenticated download.
2. **`storage.py`:** Streams bytes to `gs://al-astoora-documents/clients/{phone}/{doc_type}/{timestamp}_{filename}`.
3. **`validator.py`:** Non-blocking parallel pipeline (`asyncio.gather` for GCS upload + Gemini Vision).
4. **Canonical Normalizers:**
   - `document_type`: `passport`, `proof_of_address`, `trade_license`, `bank_statement`, `tax_assessment`, `director_resolution`, `company_constitution`, `acra_bizfile`, `invoice`, `resume`, `employment_contract`, `general_document`.
   - `eligibility_status`: `eligible`, `ineligible`, `pending_review`.
   - `service_track`: `sg_company_registration`, `accounting_services`, `immigration_consulting`, `general_corporate_services`.
5. **Emoji Highlights:** Valid outputs start with `✅`; invalid outputs start with `⚠️` or `❌`.

---

## Advantages of the Coded Solution

1. **Zero OCR Fragility:** Native multimodal intelligence reasons over layouts, blur, glare, and signatures without coordinate scrapers.
2. **Sub-50ms Webhook Responses:** Background task handoff prevents webhook delivery timeouts.
3. **Debounced Multi-Turn Reasoning:** 1.5-second buffer merges fragmented user texts, preventing multi-reply race conditions.
4. **Persistent Conversation Continuity:** Firestore sessions survive serverless restarts, maintaining seamless multi-turn dialogue.
5. **Deterministic Schema Safety:** Canonical enum normalizers guarantee strict schema compliance.

---

## Limitations & Constraints

1. **Single-Tenant Identification:** Configured for a single Meta WhatsApp phone number ID. Multi-tenant agency SaaS requires adding tenant identification headers.
2. **Container-Local Buffers:** In-memory debounce queues operate per container instance.
3. **Meta 24-Hour Service Window:** Free-form interactive responses must occur within 24 hours of the client's last message.
