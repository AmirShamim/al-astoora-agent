# Al Astoora — WhatsApp Document Collector Agent

**Hackathon:** Google All Things Agentic Hackathon 2026  
**Category:** The Taskmaster  
**Live Service URL:** `https://al-astoora-agent-1019975245319.asia-south1.run.app`  
**Tech Stack:** Python 3.11, FastAPI, Google ADK >=2.6.0, google-genai SDK >=1.0.0, Gemini 3.7 Flash, Google Cloud Run, Google Cloud Firestore (Native Mode), Google Cloud Storage, Meta WhatsApp Cloud API v26.0.

---

## Executive Overview

Al Astoora Document Collector Agent is a production-grade, serverless AI agent built for professional services agencies (corporate secretarial, accounting, tax, and immigration firms) in Singapore and the GCC / UAE.

It autonomously executes the entire client document intake and onboarding workflow over WhatsApp:
- **Collects required documents** (Passports, Trade Licenses, ACRA BizFiles, Bank Statements, Director Resolutions).
- **Inspects documents using Gemini 3.7 Flash Multimodal Vision** — verifying clarity, detecting blur/glare/thumb obstructions, evaluating expiry dates relative to real-time UTC dates, and confirming signatures.
- **Maintains persistent state in Firestore** — tracks checklist progress (`pending`, `submitted`, `validated`, `rejected`) and automatically calculates onboarding completion.
- **Communicates naturally with consultative precision** — explains specific defects on rejected uploads with emoji highlighting (`✅`, `⚠️`) and guides the client to completion.
- **Captures qualified leads** and **schedules discovery calls** with collision prevention using interactive WhatsApp buttons (3 slots) and sectioned lists (10 rows).
- **Delivers a responsive WhatsApp UX** — dispatches instant typing indicators and read receipts, aggregates rapid multi-part messages via a 1.5s debounce queue, and enforces clean plain text output.

---

## System Architecture

```
Meta WhatsApp Cloud API v26.0
          │
          │ HTTPS Webhook POST
          ▼
   ┌────────────────────────────────────────────────────────────────────────────────┐
   │                    GOOGLE CLOUD RUN (FastAPI Serverless)                       │
   │                                                                                │
   │  ┌──────────────────────────────────────────────────────────────────────────┐  │
   │  │ MODULE A: Webhook & Message Router (13 Tests)                            │  │
   │  │ - GET /webhook: Meta verification challenge                              │  │
   │  │ - POST /webhook: Noise filtering, self-reply guard, message dedup cache  │  │
   │  │ - Transforms incoming payload into standardized ParsedMessage dataclass  │  │
   │  └─────────────────────────────────────┬────────────────────────────────────┘  │
   │                                        │ BackgroundTask handoff                │
   │                                        ▼                                       │
   │  ┌──────────────────────────────────────────────────────────────────────────┐  │
   │  │ MODULE B: Gemini 3.7 Flash Agent Orchestrator (17 Tests)                 │  │
   │  │ - 1.5s Debounce Queue merges rapid multi-messages                        │  │
   │  │ - Instant WhatsApp typing indicators & blue tick read receipts           │  │
   │  │ - Injects live Firestore state summary & multi-turn session history      │  │
   │  │ - Google ADK Agent + Direct google-genai SDK 8-turn tool calling loop    │  │
   │  │ - 12 ADK Scoped Tools bridging to Modules C, D, and WhatsApp UI         │  │
   │  │ - Plain text enforcement (markdown stripping) & emoji status indicators  │  │
   │  └───────────────────┬──────────────────────────────────┬───────────────────┘  │
   │                      │                                  │                      │
   │                      ▼                                  ▼                      │
   │  ┌─────────────────────────────────────┐  ┌─────────────────────────────────┐  │
   │  │ MODULE C: Firestore State (19 Tests)│  │ MODULE D: Validation (16 Tests) │  │
   │  │ - AsyncClient Singleton             │  │ - Media Downloader (Graph API)  │  │
   │  │ - leads, clients, documents         │  │ - GCS Cloud Storage Uploader    │  │
   │  │ - intake_templates, bookings        │  │ - Gemini 3.7 Multimodal Vision  │  │
   │  │ - sessions (Multi-turn Memory)      │  │ - Parallel asyncio.gather I/O   │  │
   │  │ - document_submissions (Audit Log)  │  │ - Canonical Enum Normalizers    │  │
   │  └─────────────────────────────────────┘  └─────────────────────────────────┘  │
   └────────────────────────────────────────────────────────────────────────────────┘
```

---

## Project Directory Structure

```
Al Astoora Agent/
├── Dockerfile                      # python:3.11-slim container specification
├── Procfile                        # Cloud Run execution command
├── requirements.txt                # Pinned Python dependencies
├── .env.example                    # Environment variable configuration template
├── .gitignore / .gcloudignore      # VCS and deployment exclusion rules
├── README.md                       # Master repository documentation (This file)
├── implementation_plan.md          # Architectural plan & technical contracts
├── e2e-testing-and-submission-plan.md  # Testing scenarios & submission checklist
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application entry point, /health, router mount
│   ├── config.py                   # Pydantic Settings configuration loader
│   │
│   ├── module_a/                   # Webhook & Message Router Layer
│   │   ├── __init__.py
│   │   ├── router.py              # GET/POST /webhook endpoints & deduplication cache
│   │   ├── parser.py              # ParsedMessage dataclass & payload extraction
│   │   └── filters.py             # Event noise filtering & self-reply guard
│   │
│   ├── module_b/                   # Gemini 3.7 Flash Agent Orchestrator
│   │   ├── __init__.py
│   │   ├── agent.py               # ADK root agent & direct GenAI 8-turn tool loop
│   │   ├── system_prompt.py       # Modular 5-section prompt & corporate service rules
│   │   ├── whatsapp_sender.py     # Graph API sender (Text, Buttons, Lists, Typing)
│   │   └── tools.py               # 12 typed ADK tool definitions
│   │
│   ├── module_c/                   # Firestore State Management Layer
│   │   ├── __init__.py
│   │   ├── firestore_client.py    # AsyncClient singleton & connection management
│   │   ├── leads.py               # Lead capture with duplicate phone filtering
│   │   ├── clients.py             # Client onboarding profiles & intake templates
│   │   ├── documents.py           # Document state updates & submissions audit log
│   │   ├── bookings.py            # Appointment scheduling & collision prevention
│   │   └── sessions.py            # Multi-turn conversation persistence & LRU cache
│   │
│   └── module_d/                   # Multimodal Document Validation Engine
│       ├── __init__.py
│       ├── media_downloader.py    # Binary media download via Graph API v26.0
│       ├── storage.py             # Asynchronous Google Cloud Storage uploader
│       └── validator.py           # Gemini 3.7 Vision pipeline & canonical normalizers
│
└── tests/                          # 72 Automated Unit & Integration Tests
    ├── __init__.py
    ├── sample_payloads/            # Mock WhatsApp webhook JSON events
    ├── test_module_a.py            # 13 tests for Webhook & Parser
    ├── test_module_b.py            # 17 tests for Agent, Tools & Debouncer
    ├── test_module_c.py            # 19 tests for Firestore CRUD, Bookings & Sessions
    └── test_module_d.py            # 16 tests for Multimodal Validation & Storage
```

---

## 12 Active Agent Tools

| Tool Name | Key Parameters | Functionality |
|---|---|---|
| `capture_lead` | `name`, `phone`, `interest` | Records prospective client with duplicate phone filtering |
| `get_or_create_client` | `phone`, `name`, `service_type` | Retrieves or initializes client profile & document checklist |
| `check_intake_status` | `phone` | Returns breakdown of required, received, pending, and rejected files |
| `update_document_status` | `phone`, `doc_type`, `status`, `file_url`, `rejection_reason` | Updates verification status and recalculates onboarding completion |
| `validate_document` | `media_id`, `expected_doc_type`, `client_phone`, `original_filename` | Parallel download, storage, and Gemini 3.7 Flash vision validation |
| `check_available_slots` | `recipient_phone`, `phone`, `date` | Checks available times and dispatches interactive slot picker |
| `send_booking_buttons` | `recipient_phone`, `phone`, `date` | Sends 3 quick-tap interactive WhatsApp booking buttons |
| `send_interactive_booking_slots`| `recipient_phone`, `phone`, `date` | Sends 10-slot selectable interactive list dropdown |
| `book_appointment` | `date`, `time`, `name`, `phone` | Confirms consultation slot with collision prevention |
| `send_whatsapp_text` | `recipient_phone`, `text` | Sends direct plain text message |
| `send_whatsapp_buttons` | `recipient_phone`, `body_text`, `buttons`, `header_text`, `footer_text` | Dispatches custom 3-button interactive message |
| `send_whatsapp_list` | `recipient_phone`, `body_text`, `button_text`, `sections`, `title`, `footer`| Dispatches custom 10-row sectioned list message |

---

## Local Development Quickstart

### 1. Clone & Set Up Environment
```bash
git clone <repository-url>
cd "Al Astoora Agent"
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
```
Fill in your Meta WhatsApp token, phone number IDs, and GCP credentials in `.env`.

### 3. Run Test Suite (72 Tests)
```bash
pytest tests/ -v
```

### 4. Start Local Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Environment Variables Configuration

| Variable | Description | Default / Example |
|---|---|---|
| `WHATSAPP_TOKEN` | Permanent Meta System User Token | `EAAStEGDo...` |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta WhatsApp Business Phone Number ID | `1113443245192571` |
| `BOT_PHONE_NUMBER` | Bot Phone Number (Self-reply filter) | `919289581053` |
| `WEBHOOK_VERIFY_TOKEN` | Meta Webhook Verification Token | `al_astoora_secure_verify_token_2026` |
| `GRAPH_API_VERSION` | Meta Graph API Version | `v26.0` |
| `GCP_PROJECT_ID` | Google Cloud Project ID | `project-080b5971-eb4b-4d2b-a4c` |
| `GCP_LOCATION` | Regional location for Firestore / Compute | `asia-south1` |
| `GEMINI_LOCATION` | Vertex AI regional endpoint for Gemini 3.7 | `global` |
| `GCS_BUCKET_NAME` | Cloud Storage Bucket Name | `al-astoora-documents` |
| `GEMINI_MODEL` | Gemini Model Identifier | `gemini-3.7-flash` |
| `GEMINI_THINKING_LEVEL` | Thinking level for perception latency | `low` |
| `GEMINI_THINKING_BUDGET`| Thinking token budget (0 = minimal latency)| `0` |
| `APP_ENV` | Environment Identifier | `production` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `PORT` | Server listening port | `8080` |

> **Note on Regional Architecture:** `GEMINI_LOCATION=global` and `GCP_LOCATION=asia-south1` is an intentional configuration. Gemini 3.7 Flash models are available via the global Vertex AI endpoint, while Firestore is regionally hosted in `asia-south1` (Mumbai) for low-latency operations in Asia and the Middle East.

---

## Google Cloud Run Deployment

Deploy directly using the Google Cloud CLI from the `Al Astoora Agent/` directory:

```bash
gcloud run deploy al-astoora-agent \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --service-account ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com \
  --set-env-vars "WHATSAPP_TOKEN=<token>,WHATSAPP_PHONE_NUMBER_ID=1113443245192571,BOT_PHONE_NUMBER=919289581053,WEBHOOK_VERIFY_TOKEN=al_astoora_secure_verify_token_2026,GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GEMINI_MODEL=gemini-3.7-flash,GEMINI_LOCATION=global"
```

---

## Meta Webhook Setup

1. Open the [Meta Developer Portal](https://developers.facebook.com/).
2. Select your WhatsApp Business App → **WhatsApp > Configuration**.
3. Set **Callback URL** to: `https://al-astoora-agent-1019975245319.asia-south1.run.app/webhook`
4. Set **Verify Token** to: `al_astoora_secure_verify_token_2026`
5. Click **Verify and Save**.
6. Under **Webhook fields**, subscribe to **`messages`**.

---

## Advantages of the Coded Solution

1. **Zero OCR Brittleness:** Direct Gemini 3.7 Flash Multimodal Vision evaluates layout, text, stamps, signatures, and dates without fragile coordinate regexes.
2. **Sub-50ms Webhook Acknowledgment:** Asynchronous background handoff eliminates 504 gateway timeouts.
3. **Instant Visual Perception:** Instant typing indicators and read receipts eliminate conversational dead air.
4. **Resilient Session Memory:** Firestore-backed persistent sessions with in-memory caching ensure multi-turn continuity across container cold starts.
5. **Strict Data Integrity:** Canonical enum normalizers prevent database contamination in downstream CRM collections.

---

## Limitations & Constraints

1. **Single-Tenant WhatsApp Identifier:** Configured for a single production business phone number; multi-tenant white-labeling requires adding tenant routing headers.
2. **Container-Local Caches:** In-memory deduplication and debounce queues run per Cloud Run instance.
3. **24-Hour Messaging Window:** Free-form interactive responses operate within Meta's standard 24-hour service window.
