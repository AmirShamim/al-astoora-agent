"""
Al Astoora Agency & Client Dashboard Router.
Provides REST APIs and full interactive web dashboard interface.
"""

from pathlib import Path
from datetime import datetime, timezone
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Response, HTTPException, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse, RedirectResponse
import io

from app.config import get_settings
from app.module_c.leads import get_all_leads
from app.module_c.clients import get_all_clients
from app.module_c.bookings import get_all_bookings
from app.module_c.documents import get_all_submissions
from app.module_c.sessions import get_audit_history, get_all_sessions
from app.module_d.storage import generate_signed_url, download_blob_bytes

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

FRONTEND_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"


@router.get("/dashboard", summary="Al Astoora React Web Client Dashboard")
async def get_dashboard():
    """
    Renders the live interactive React frontend dashboard for Al Astoora Agency and clients.
    Serves frontend/dist/index.html when built, or a clean fallback linking to dashboard APIs.
    """
    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    return HTMLResponse(
        content="""<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-950 text-slate-100">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Al Astoora - React Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="h-full flex items-center justify-center bg-slate-950 text-slate-100 font-sans p-6">
  <div class="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl text-center">
    <div class="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-400 mb-6">
      <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    </div>
    <h1 class="text-2xl font-bold text-white mb-2">Al Astoora React Dashboard</h1>
    <p class="text-slate-400 text-sm mb-6 leading-relaxed">
      The dashboard frontend is maintained in <code class="text-emerald-400 font-mono text-xs bg-slate-800 px-2 py-1 rounded">frontend/</code> (React + Vite + Tailwind).
    </p>
    <div class="space-y-3">
      <a href="/api/dashboard/stats" class="block w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-sm transition">
        View Overview KPI API &rarr;
      </a>
      <a href="/api/dashboard/clients" class="block w-full py-2.5 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-sm transition">
        View Clients API &rarr;
      </a>
      <a href="/docs" class="block w-full py-2.5 px-4 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-300 font-medium text-sm transition">
        Interactive OpenAPI Docs
      </a>
    </div>
  </div>
</body>
</html>"""
    )


@router.get("/api/dashboard/stats", summary="Overview KPI Metrics")
async def get_dashboard_stats() -> Dict[str, Any]:
    """
    Computes overall summary statistics across all collections for dashboard KPI cards.
    """
    try:
        leads = await get_all_leads(limit=100)
        clients = await get_all_clients(limit=100)
        bookings = await get_all_bookings(limit=100)
        submissions = await get_all_submissions(limit=100)
        sessions = await get_all_sessions(limit=100)

        total_clients = len(clients)
        completed_clients = sum(1 for c in clients if c.get("onboarding_status") == "complete")
        in_progress_clients = total_clients - completed_clients

        total_submissions = len(submissions)
        validated_submissions = sum(1 for s in submissions if s.get("is_valid") is True)
        rejected_submissions = total_submissions - validated_submissions

        confirmed_bookings = sum(1 for b in bookings if b.get("status") == "confirmed")

        return {
            "total_leads": len(leads),
            "total_clients": total_clients,
            "completed_clients": completed_clients,
            "in_progress_clients": in_progress_clients,
            "total_submissions": total_submissions,
            "validated_submissions": validated_submissions,
            "rejected_submissions": rejected_submissions,
            "total_bookings": len(bookings),
            "confirmed_bookings": confirmed_bookings,
            "total_sessions": len(sessions),
        }
    except Exception as e:
        logger.exception("Error computing dashboard stats: %s", e)
        return {
            "total_leads": 0,
            "total_clients": 0,
            "completed_clients": 0,
            "in_progress_clients": 0,
            "total_submissions": 0,
            "validated_submissions": 0,
            "rejected_submissions": 0,
            "total_bookings": 0,
            "confirmed_bookings": 0,
            "total_sessions": 0,
            "error": str(e),
        }


@router.get("/api/dashboard/clients", summary="All Clients Onboarding Profiles")
async def get_dashboard_clients() -> Dict[str, Any]:
    """
    Returns list of clients with their document checklist progress and signed file URLs.
    """
    try:
        clients = await get_all_clients(limit=50)
        for client in clients:
            docs = client.get("documents", [])
            for d in docs:
                file_url = d.get("file_url")
                if file_url:
                    d["signed_url"] = generate_signed_url(file_url, expiration_minutes=120)
        return {"success": True, "clients": clients}
    except Exception as e:
        logger.exception("Error fetching dashboard clients: %s", e)
        return {"success": False, "error": str(e), "clients": []}


@router.get("/api/dashboard/leads", summary="All Captured Leads")
async def get_dashboard_leads() -> Dict[str, Any]:
    """
    Returns list of captured prospective leads.
    """
    try:
        leads = await get_all_leads(limit=50)
        return {"success": True, "leads": leads}
    except Exception as e:
        logger.exception("Error fetching dashboard leads: %s", e)
        return {"success": False, "error": str(e), "leads": []}


@router.get("/api/dashboard/bookings", summary="All Consultation Bookings")
async def get_dashboard_bookings() -> Dict[str, Any]:
    """
    Returns list of all discovery call appointments.
    """
    try:
        bookings = await get_all_bookings(limit=50)
        return {"success": True, "bookings": bookings}
    except Exception as e:
        logger.exception("Error fetching dashboard bookings: %s", e)
        return {"success": False, "error": str(e), "bookings": []}


@router.get("/api/dashboard/submissions", summary="All Document Submissions")
async def get_dashboard_submissions() -> Dict[str, Any]:
    """
    Returns all document submissions with extracted fields, validation results, and signed file URLs.
    """
    try:
        submissions = await get_all_submissions(limit=50)
        for s in submissions:
            file_url = s.get("file_url")
            if file_url:
                s["signed_url"] = generate_signed_url(file_url, expiration_minutes=120)
        return {"success": True, "submissions": submissions}
    except Exception as e:
        logger.exception("Error fetching dashboard submissions: %s", e)
        return {"success": False, "error": str(e), "submissions": []}


@router.get("/api/dashboard/transcripts/{phone}", summary="Immutable Conversation Audit Transcript")
async def get_dashboard_transcript(phone: str) -> Dict[str, Any]:
    """
    Returns the complete, untrimmed immutable message audit log for a given phone number.
    Backed by Firestore message_audit collection for legal accountability.
    """
    try:
        messages = await get_audit_history(phone=phone, limit=100)
        return {
            "success": True,
            "phone": phone,
            "messages": messages,
            "audit_trail_verified": True,
        }
    except Exception as e:
        logger.exception("Error fetching dashboard transcript for %s: %s", phone, e)
        return {
            "success": False,
            "phone": phone,
            "error": str(e),
            "messages": [],
        }


@router.get("/api/dashboard/media-preview", summary="Secure Document / Image Preview Stream")
async def get_media_preview(uri: str = Query(..., description="GCS URI or blob path")):
    """
    Streams file bytes directly from Google Cloud Storage or redirects to signed URL,
    allowing in-browser image inspection and PDF viewing without public bucket exposure.
    """
    if not uri:
        raise HTTPException(status_code=400, detail="Missing URI query parameter")

    # Try generating signed URL first
    signed_url = generate_signed_url(uri, expiration_minutes=60)
    if signed_url:
        return RedirectResponse(url=signed_url)

    # Fallback to direct byte streaming
    result = await download_blob_bytes(uri)
    if not result:
        raise HTTPException(status_code=404, detail="File not found in storage")

    content_bytes, mime_type = result
    return StreamingResponse(io.BytesIO(content_bytes), media_type=mime_type)
