# Phase 5 & 6: End-to-End Testing & Submission Execution Plan

**Hackathon Category:** The Taskmaster  
**Live Service URL:** `https://al-astoora-agent-1019975245319.asia-south1.run.app`  
**Current Status:** Phases 0–4 Built & Live | 72 Automated Tests Passing | E2E Testing & Final Submission Packaging  

---

## Current System State & Bug Resolutions

- **Cloud Run Service:** Live and healthy (`/health` returns `{"status": "healthy", "service": "al-astoora-agent", "version": "1.0.0"}`).
- **Meta WhatsApp Cloud API Webhook:** Verified and operational (`POST /webhook` acknowledges in <50ms).
- **Tool Calling Multi-Turn Loop:** ✅ **RESOLVED & VERIFIED.** `app/module_b/agent.py` implements an 8-turn tool calling loop in `_execute_agent_turn` that passes function responses back to Gemini 3.7 Flash until a final text response is produced.
- **`GEMINI_LOCATION` Configuration:** ✅ **VERIFIED.** Configured to `global` for direct Vertex AI access to Gemini 3.7 Flash, with `GCP_LOCATION=asia-south1` for low-latency Firestore operations.

---

## Phase 5: End-to-End WhatsApp Test Scenarios

The following 7 test scenarios validate the entire autonomous workflow over real WhatsApp:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      7 END-TO-END VALIDATION SCENARIOS                      │
│                                                                             │
│  1. Lead Capture       → User expresses interest; lead captured in DB       │
│  2. Start Onboarding   → Service selected; required checklist dispatched    │
│  3. Valid Document     → Valid passport uploaded; instant '✅' confirmation │
│  4. Defective Document → Blurry/expired file uploaded; '⚠️' fix guidance    │
│  5. Status Check       → User asks progress; remaining checklist returned   │
│  6. Intake Completion  → Final document submitted; '🎉' completion flagged │
│  7. Interactive Booking→ Discovery call slot selected via buttons/lists     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Scenario 1: New Prospect Exploration & Lead Capture
- **User Action:** Sends *"Hi! I need help setting up a business in Singapore."*
- **Agent Execution:**
  1. Module A parses message, applies deduplication, and hands off to Module B.
  2. Module B fires instant WhatsApp typing indicator and read receipt.
  3. Gemini 3.7 Flash calls `capture_lead(name="User", phone="...", interest="Singapore Company Registration")`.
  4. Module C records lead in `leads` collection with `status="new"`.
  5. Agent replies with a warm, 1-2 sentence consultative greeting outlining the Singapore Company Registration process.
- **Verification:** Query Firestore `leads` collection to confirm new entry.

### Scenario 2: Onboarding Track Initialization
- **User Action:** Sends *"Let's proceed with Singapore Company Registration."*
- **Agent Execution:**
  1. Agent calls `get_or_create_client(phone="...", name="...", service_type="sg_company_registration")`.
  2. Module C loads `intake_templates/sg_company_registration`, initializes `clients/{phone}`, and creates 3 subcollection document records (`passport`, `proof_of_address`, `director_resolution`) with status `"pending"`.
  3. Agent prompts client to upload the first required document (Passport).
- **Verification:** Check `clients/{phone}` document and `documents` subcollection in Firestore.

### Scenario 3: Valid Document Upload & Instant Verification
- **User Action:** Uploads a clear, unexpired passport photo.
- **Agent Execution:**
  1. Module A extracts `media_id`.
  2. Module B calls `validate_document(media_id="...", expected_doc_type="auto_detect", client_phone="...")`.
  3. Module D executes `asyncio.gather`:
     - Streams file to `gs://al-astoora-documents/clients/{phone}/passport/...`.
     - Analyzes image with Gemini 3.7 Flash Multimodal Vision on Vertex AI.
  4. Gemini extracts name, document number, and confirms expiry > current UTC date.
  5. Module C updates `clients/{phone}/documents/passport` to `"validated"` and logs entry in `document_submissions`.
  6. Agent replies: *"✅ Thank you! Your Passport has been successfully verified. Next, please upload your Proof of Address (utility bill or bank statement)."*
- **Verification:** Check GCS bucket file existence and `document_submissions` record.

### Scenario 4: Defective / Blurry / Expired Document Rejection
- **User Action:** Uploads a blurry document or expired ID.
- **Agent Execution:**
  1. Module D runs validation pipeline.
  2. Gemini 3.7 Flash flags defects: `is_valid = false`, `issues = ["Image blurry", "Expiry date obscured"]`.
  3. Module C updates document status to `"rejected"` with `rejection_reason`.
  4. Agent replies: *"⚠️ We noticed an issue with your document: The image is blurry and the expiry date is covered. Please send a clearer, unobstructed photo for us to proceed."*
- **Verification:** Subcollection document reflects `status="rejected"`.

### Scenario 5: Mid-Conversation Status Inquiry
- **User Action:** Sends *"What documents do you still need from me?"*
- **Agent Execution:**
  1. Agent calls `check_intake_status(phone="...")`.
  2. Module C calculates received (1/3), pending (`proof_of_address`, `director_resolution`), and rejected files.
  3. Agent replies with a clear, concise status breakdown.

### Scenario 6: Full Onboarding Completion
- **User Action:** Uploads remaining valid documents (`proof_of_address` and signed `director_resolution`).
- **Agent Execution:**
  1. Module D validates each upload.
  2. `update_document_status` detects that `documents_received == documents_required` (3/3).
  3. Sets `onboarding_status = "complete"` on `clients/{phone}`.
  4. Agent replies: *"🎉 Congratulations! All required onboarding documents have been received and verified. Our corporate team will now prepare your incorporation filing."*

### Scenario 7: Interactive Consultation Discovery Call Booking
- **User Action:** Sends *"Can we schedule a call for tomorrow?"*
- **Agent Execution:**
  1. Agent calls `send_booking_buttons(recipient_phone="...", date="tomorrow")` or `send_interactive_booking_slots`.
  2. Module C checks `bookings` for tomorrow and computes open 30-minute slots (e.g. 09:00 AM, 12:00 PM, 03:00 PM).
  3. Dispatches interactive WhatsApp buttons directly to the user's phone.
  4. Client taps `"10:00 AM"`.
  5. Webhook receives button reply `book_2026-08-25_10:00`.
  6. Agent calls `book_appointment` to atomically confirm booking in Firestore.
  7. Agent sends confirmation: *"📅 Your discovery consultation is confirmed for Tuesday, August 25, 2026 at 10:00 - 10:30 AM."*

---

## Phase 6: Submission Deliverables Roadmap

| # | Deliverable | Format / Platform | Action Checklist |
|---|---|---|---|
| 1 | **Category Selection** | Devpost | Select **The Taskmaster** |
| 2 | **Hosted Project URL** | Cloud Run | `https://al-astoora-agent-1019975245319.asia-south1.run.app` |
| 3 | **Text Description** | Devpost Markdown | Features, Tech Stack, Data Sources, Findings & Learnings |
| 4 | **Code Repository** | GitHub | Public repo with commit history (or share with `testing@devpost.com` & `cloudhackathons@google.com`) |
| 5 | **README.md** | GitHub Markdown | Step-by-step setup, environment variables, local testing, Cloud Run deployment |
| 6 | **Architecture Diagram** | PNG / SVG / Mermaid | Visual flow: WhatsApp ↔ Cloud Run ↔ Gemini 3.7 Flash ↔ Firestore / GCS |
| 7 | **Demo Video (≤ 4 Min)** | YouTube (Public) | Screen recording of WhatsApp live demo + Cloud Console metrics + Vertex AI logs |
| 8 | **Technical Blog Post** | Medium / dev.to | Optional bonus (+0.2 points) |
| 9 | **LinkedIn Post** | LinkedIn | Optional bonus (+0.2 points) with `#AllThingsAgenticHackathon` |

---

## Advantages of the E2E Testing Architecture

1. **Deterministic Verification:** 72 unit tests validate every failure mode offline, while the 7 live WhatsApp scenarios verify production transport and multimodal reasoning.
2. **Automated Audit Telemetry:** Every test upload creates a permanent record in Firestore `document_submissions`, providing real-time verification proof for hackathon judging.

---

## Operational Limitations

1. **Single Testing Device:** Testing must be conducted via the single production WhatsApp Business Number ID (`BOT_PHONE_NUMBER=919289581053`).
2. **Video Time Constraint:** The 4-minute maximum video limit requires crisp demonstration pacing across lead capture, validation, and booking.
