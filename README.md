# Al Astoora — WhatsApp Document Collection Agent

**Hackathon:** Google All Things Agentic Hackathon 2026
**Category:** The Taskmaster
**Stack:** Python 3.11, FastAPI, Google ADK 2.6+, google-genai SDK, Gemini 3.7 Flash, Cloud Run, Firestore, Cloud Storage

---

## What It Does

An autonomous WhatsApp agent that handles multi-step client document intake for professional services firms (corporate secretarial, accounting, immigration) in Singapore and GCC. It:

- **Collects documents** via WhatsApp (passports, visas, trade licenses, etc.)
- **Validates documents** using Gemini 3.7 Flash multimodal vision — checks readability, expiry, signatures, document type
- **Tracks onboarding state** in Firestore — knows which docs are submitted, pending, rejected
- **Communicates with clients** naturally — explains what's wrong with rejected docs, shows remaining checklist
- **Captures leads** and **books appointments** via interactive WhatsApp buttons and lists
- **Sends read receipts and typing indicators** for a native WhatsApp UX

All without human intervention.

---

## System Architecture

```
Meta WhatsApp Cloud API
         │
         ▼
  ┌──────────────────┐
  │  MODULE A         │  Webhook + Message Router (receives, filters noise, parses)
  │  (13 tests)       │
  └────────┬─────────┘
           │ ParsedMessage
           ▼
  ┌──────────────────┐
  │  MODULE B         │  Gemini 3.7 Flash Agent Orchestrator (ADK + GenAI SDK)
  │  (17 tests)       │  Decides → Calls Tools → Sends WhatsApp Replies
  └──┬────────────┬──┘
     │            │
     ▼            ▼
  ┌──────────┐ ┌──────────┐
  │ MODULE C  │ │ MODULE D  │
  │ Firestore │ │ Document  │
  │ State     │ │ Validation│
  │ (19 tests)│ │ (16 tests)│
  └──────────┘ └──────────┘
```

---

## Project Structure

```
Al Astoora Agent/
├── Dockerfile                      # python:3.11-slim container
├── Procfile                        # Cloud Run execution command
├── requirements.txt                # Pinned Python dependencies
├── .env.example                    # Environment variable reference
├── .gitignore / .gcloudignore
├── README.md                       # This file
├── implementation_plan.md          # Code contracts & deployment config
├── e2e-testing-and-submission-plan.md  # Phase 5 & 6 plan
│
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI app, /health, /webhook mount
│   ├── config.py                   # Pydantic Settings (env vars)
│   │
│   ├── module_a/                   # Webhook + Message Router
│   │   ├── router.py              # GET/POST /webhook endpoints
│   │   ├── parser.py              # ParsedMessage dataclass
│   │   └── filters.py             # Status filters & self-reply guard
│   │
│   ├── module_b/                   # Gemini 3.7 Flash Agent
│   │   ├── agent.py               # Google ADK Agent + GenAI fallback
│   │   ├── system_prompt.py       # Modular 5-section system prompt
│   │   ├── whatsapp_sender.py     # Async WhatsApp Cloud API sender
│   │   └── tools.py               # 10+ ADK tool functions
│   │
│   ├── module_c/                   # Firestore State Manager
│   │   ├── firestore_client.py    # Async Firestore singleton
│   │   ├── leads.py               # Lead capture with duplicate check
│   │   ├── clients.py             # Client profiles & intake templates
│   │   ├── documents.py           # Document status & submissions audit log
│   │   ├── bookings.py            # Appointment slot management
│   │   └── sessions.py            # Conversation session persistence
│   │
│   └── module_d/                   # Document Validation Engine
│       ├── media_downloader.py    # WhatsApp media download
│       ├── storage.py             # Cloud Storage upload
│       └── validator.py           # Gemini 3.7 Flash multimodal analysis
│
└── tests/                          # 72 total tests
    ├── sample_payloads/            # 6 JSON test payloads
    ├── test_module_a.py            # 13 tests
    ├── test_module_b.py            # 17 tests
    ├── test_module_c.py            # 19 tests
    └── test_module_d.py            # 16 tests
```

---

## Prerequisites

- Python 3.11+
- Google Cloud Platform account with billing enabled
- Meta WhatsApp Business API access (system user token)
- GCP services enabled: Cloud Run, Firestore (Native mode), Cloud Storage, Vertex AI

---

## Quickstart

### 1. Clone & Setup Environment
```bash
git clone <repo-url>
cd "Al Astoora Agent"
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Fill in your WhatsApp token, GCP project ID, etc.
```

### 3. Run Tests
```bash
pytest tests/ -v
```

### 4. Start Local Development Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `WHATSAPP_TOKEN` | Meta permanent system user token | (required) |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp Business phone number ID | `1113443245192571` |
| `BOT_PHONE_NUMBER` | Bot's own phone number (for self-reply prevention) | `919289581053` |
| `WEBHOOK_VERIFY_TOKEN` | Meta webhook verification token | `al_astoora_secure_verify_token_2026` |
| `GRAPH_API_VERSION` | Meta Graph API version | `v26.0` |
| `GCP_PROJECT_ID` | Google Cloud project ID | `project-080b5971-eb4b-4d2b-a4c` |
| `GCP_LOCATION` | GCP region for Firestore/Cloud Run | `asia-south1` |
| `GCS_BUCKET_NAME` | Cloud Storage bucket for documents | `al-astoora-documents` |
| `GEMINI_MODEL` | Gemini model ID | `gemini-3.7-flash` |
| `GEMINI_LOCATION` | Gemini model region (intentionally different from GCP_LOCATION) | `global` |
| `GEMINI_THINKING_LEVEL` | Gemini thinking mode | `low` |
| `GEMINI_THINKING_BUDGET` | Thinking token budget (0 = no thinking for fast responses) | `0` |
| `APP_ENV` | Environment identifier | `production` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `PORT` | Server port | `8080` |

> **Note:** `GEMINI_LOCATION=global` and `GCP_LOCATION=asia-south1` is an intentional split. Gemini 3.7 Flash is available in the global region, while Firestore and Cloud Run use the Indian region for lower latency.

---

## Google Cloud Run Deployment

```bash
gcloud run deploy al-astoora-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com \
  --set-env-vars "WHATSAPP_TOKEN=<token>,WHATSAPP_PHONE_NUMBER_ID=1113443245192571,BOT_PHONE_NUMBER=919289581053,WEBHOOK_VERIFY_TOKEN=al_astoora_secure_verify_token_2026,GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GEMINI_MODEL=gemini-3.7-flash"
```

---

## Meta Webhook Configuration

1. Go to [Meta Developer Portal](https://developers.facebook.com/)
2. Select your WhatsApp Business app
3. Navigate to **WhatsApp > Configuration**
4. Set **Callback URL** to: `https://al-astoora-agent-1019975245319.us-central1.run.app/webhook`
5. Set **Verify Token** to: your `WEBHOOK_VERIFY_TOKEN` value
6. Subscribe to: `messages` webhook field

---

## Tech Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| Web Framework | FastAPI >= 0.115.0 |
| AI Agent Framework | Google ADK >= 2.6.0 + google-genai SDK >= 1.0.0 |
| AI Model | Gemini 3.7 Flash (multimodal) |
| Database | Firestore Native Mode |
| File Storage | Cloud Storage |
| Hosting | Google Cloud Run |
| WhatsApp API | Meta Cloud API v26.0 (via httpx async) |
| Config | Pydantic Settings |
