# Al Astoora — WhatsApp Document Collection Agent

**Hackathon:** Google All Things Agentic Hackathon 2026  
**Category:** The Taskmaster  
**Stack:** Python 3.11+, FastAPI, Google ADK 2.7.0, Gemini 3.7 Flash, Google Cloud Run, Firestore, Cloud Storage  

---

## 🏛️ System Architecture

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
  │  MODULE B         │  Gemini 3.7 Agent Orchestrator (ADK)
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

## 📂 Project Structure

```
Al Astoora Agent/
├── app/
│   ├── main.py                   # FastAPI entry point & health check
│   ├── config.py                 # Pydantic Settings & environment loader
│   ├── module_a/                 # Webhook & Message Router (Phase 1)
│   │   ├── router.py             # GET /webhook (Meta handshake) & POST /webhook
│   │   ├── parser.py             # ParsedMessage dataclass & payload parser
│   │   └── filters.py            # Status filters & self-reply guard
│   ├── module_b/                 # Gemini Agent & WhatsApp Sender
│   │   └── whatsapp_sender.py    # Async WhatsApp Cloud API sender
│   ├── module_c/                 # Firestore State Manager (Phase 3)
│   └── module_d/                 # Document Validation Engine (Phase 4)
├── tests/
│   ├── sample_payloads/          # Standard Meta WhatsApp Webhook payloads
│   └── test_module_a.py          # Module A unit & integration tests
├── requirements.txt              # Pinned Python dependencies
├── Procfile                      # Google Cloud Run execution command
├── .env.example                  # Environment variable reference
└── README.md
```

---

## ⚡ Quickstart

### 1. Environment Setup
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` and fill in your WhatsApp & Google Cloud credentials:
```bash
copy .env.example .env
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

## 🚀 Google Cloud Run Deployment

Deploy directly from source without Docker:
```bash
gcloud run deploy al-astoora-agent \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GEMINI_MODEL=gemini-3.7-flash,WEBHOOK_VERIFY_TOKEN=your_token"
```
