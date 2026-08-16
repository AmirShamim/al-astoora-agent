# Al Astoora — Hackathon Agent Master Implementation Plan

**Hackathon:** All Things Agentic Hackathon 2026 (Google LLC / Devpost)  
**Category:** The Taskmaster  
**App Name:** Al Astoora Document Collector Agent  
**Stack:** Python 3.11, FastAPI, Google ADK 2.7.0, Gemini 3.7 Flash, Google Cloud Run (Docker container), Firestore Native Mode, Cloud Storage  
**GCP Project ID:** `project-080b5971-eb4b-4d2b-a4c`  
**Location:** `us-central1`  
**Gemini Region:** `global`  

---

## System Architecture & Flow

```
Meta WhatsApp Cloud API
         │
         ▼
  ┌──────────────────┐
  │  MODULE A         │  Webhook + Message Router (receives, filters noise, parses)
  └────────┬─────────┘
           │ ParsedMessage
           ▼
  ┌──────────────────┐
  │  MODULE B         │  Gemini 3.7 Flash Agent Orchestrator (Google ADK)
  └──┬────────────┬──┘
     │            │
     ▼            ▼
  ┌──────────┐ ┌──────────┐
  │ MODULE C  │ │ MODULE D  │
  │ Firestore │ │ Document  │
  │ State     │ │ Validation│
  └──────────┘ └──────────┘
```

---

## Module Boundaries & Responsibilities

| Module | Purpose | Responsibilities | Does NOT |
|---|---|---|---|
| **Module A** (`app/module_a`) | Webhook + Router | Handshake with Meta (`GET /webhook`), filter status receipts & self-replies, parse into `ParsedMessage`, dispatch async | Does NOT call Gemini or Firestore |
| **Module B** (`app/module_b`) | Agent Orchestrator | Google ADK Agent (`gemini-3.7-flash`), system prompt, tool routing, conversation context, WhatsApp message sender | Does NOT execute raw Firestore CRUD directly (calls Module C) |
| **Module C** (`app/module_c`) | Firestore State | `clients`, `documents`, `leads`, `bookings`, `intake_templates` collections. Pure CRUD | Does NOT call WhatsApp or Gemini |
| **Module D** (`app/module_d`) | Document Validation | Download WhatsApp media, upload to GCS, multimodal vision analysis via Gemini 3.7 Flash | Does NOT send WhatsApp replies directly |

---

## Project Structure

```
Al Astoora Agent/
├── Dockerfile                    # Python 3.11-slim production container for Cloud Run
├── Procfile                      # Web process definition
├── requirements.txt              # Pinned compatible dependencies (FastAPI, ADK, GenAI, Firestore, GCS)
├── .env.example                  # Environment configuration template
├── .env                          # Local environment variables
├── .gitignore                    # Git hygiene
├── .gcloudignore                 # Cloud Build optimization
├── README.md                     # Setup, testing, and deployment instructions
├── implementation_plan.md        # This master architecture and build plan
│
├── app/
│   ├── __init__.py
│   ├── main.py                   # FastAPI app entry point & /health probe
│   ├── config.py                 # Pydantic BaseSettings environment loader
│   │
│   ├── module_a/                 # Module A: Webhook + Message Router [COMPLETED]
│   │   ├── __init__.py
│   │   ├── router.py             # GET/POST /webhook endpoints with background dispatch
│   │   ├── parser.py             # ParsedMessage dataclass & payload parser
│   │   └── filters.py            # Status receipt filters & self-reply guard
│   │
│   ├── module_b/                 # Module B: Gemini Agent (Orchestrator)
│   │   ├── __init__.py
│   │   ├── agent.py              # ADK Agent definition & model configuration
│   │   ├── system_prompt.py      # System prompt with domain rules & WhatsApp constraints
│   │   ├── whatsapp_sender.py    # Async sender for text, buttons, and list replies [COMPLETED]
│   │   └── tools.py              # ADK-registered tool definitions bridging to Modules C & D
│   │
│   ├── module_c/                 # Module C: Firestore State Manager
│   │   ├── __init__.py
│   │   ├── firestore_client.py   # AsyncClient singleton
│   │   ├── leads.py              # capture_lead()
│   │   ├── clients.py            # get_or_create_client(), check_intake_status()
│   │   ├── documents.py          # update_document_status()
│   │   └── bookings.py           # check_available_slots(), book_appointment()
│   │
│   └── module_d/                 # Module D: Document Validation Engine
│       ├── __init__.py
│       ├── media_downloader.py   # 2-step WhatsApp Graph API media downloader
│       ├── storage.py            # GCS file uploader for records
│       └── validator.py          # Gemini 3.7 Flash multimodal document reasoning
│
└── tests/
    ├── __init__.py
    ├── sample_payloads/          # Standard Meta WhatsApp Webhook payloads
    │   ├── text_message.json
    │   ├── button_reply.json
    │   ├── list_reply.json
    │   ├── image_message.json
    │   ├── document_message.json
    │   └── status_update.json
    ├── test_module_a.py          # Module A unit & integration test suite [COMPLETED]
    ├── test_module_c.py          # Module C Firestore tests
    └── test_module_d.py          # Module D document validation tests
```

---

## Containerization & Cloud Run Deployment

Deployment is containerized using `Dockerfile` (Python 3.11-slim) which guarantees 100% reproducible builds across any environment.

### Deployment Command
```bash
gcloud run deploy al-astoora-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account ai-agent-n8n@project-080b5971-eb4b-4d2b-a4c.iam.gserviceaccount.com \
  --set-env-vars "WHATSAPP_TOKEN=EAAStEGDoJOYBR6eSp1ZAu8IxU86MbIQX6SkHOY5SDQtNvUaph2yUFtCZAgiz0ZBZCn2r7japgrLSMEps2QcU1S2lNerokp1RZBzpFXxP3zA2b34jJz7lwVezhE60TZCEZAsWmXdtguJKwo4e5j6kyqr1kjTgRZCvWZC05IdHm8EqYhxSHMcsktK8wFJuNvi0bgBa34wZDZD,WHATSAPP_PHONE_NUMBER_ID=1113443245192571,BOT_PHONE_NUMBER=919289581053,WEBHOOK_VERIFY_TOKEN=al_astoora_secure_verify_token_2026,GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GEMINI_MODEL=gemini-3.7-flash"
```

---

## Build Phases & Status

- [x] **Phase 0: Project Scaffolding & Config** — Dependencies, settings, logging, Dockerfile, Git setup.
- [x] **Phase 1: Module A (Webhook Router)** — Verification handshake, filters, parsers, WhatsApp sender, sample payloads, pytest suite.
- [ ] **Phase 2: Module C (Firestore State Manager)** — Client profiles, document status tracking, lead capture, appointment booking CRUD.
- [ ] **Phase 3: Module D (Document Validation Engine)** — Media download, Cloud Storage upload, Gemini 3.7 Flash multimodal vision analysis.
- [ ] **Phase 4: Module B (Gemini 3.7 Agent with ADK)** — System prompt, tool calling integration, multi-turn conversation memory.
- [ ] **Phase 5: End-to-End Testing & Edge Cases** — Full lifecycle tests, error fallbacks, unreadable/expired doc handling.
- [ ] **Phase 6: Submission Deliverables** — Architecture diagram, README polish, 4-minute demo video showing GCP deployment, Devpost submission.
