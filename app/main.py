"""
Al Astoora Document Collector Agent — FastAPI Application Entry Point.
Production-ready serverless backend for Meta WhatsApp Cloud API and Google Cloud Run.
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.module_a.router import router as webhook_router, register_message_handler
from app.module_b.agent import process_message

# Configure structured logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("al_astoora_agent")

# Register Module B Agent message handler with Module A webhook router
register_message_handler(process_message)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle management."""
    logger.info("=" * 60)
    logger.info("🚀 Al Astoora Document Collector Agent starting up...")
    logger.info(f"   Environment: {settings.APP_ENV}")
    logger.info(f"   GCP Project: {settings.GCP_PROJECT_ID}")
    logger.info(f"   Gemini Model: {settings.GEMINI_MODEL}")
    logger.info("=" * 60)
    # Ensure message handler registration is affirmed on startup
    register_message_handler(process_message)
    yield
    logger.info("🛑 Al Astoora Agent shutting down.")


app = FastAPI(
    title="Al Astoora Document Collector Agent",
    description="Autonomous WhatsApp agent for client document intake and onboarding.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Webhook Router (Module A)
app.include_router(webhook_router)


@app.get("/health", tags=["Health"], summary="Service Health Check")
async def health_check():
    """Health check endpoint for Google Cloud Run container liveness probes."""
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "healthy",
            "service": "al-astoora-agent",
            "version": "1.0.0",
            "environment": settings.APP_ENV,
        },
    )


@app.get("/", tags=["Root"], summary="Root status")
async def root():
    """Root landing endpoint."""
    return {
        "agency": "Al Astoora",
        "agent": "Document Collector Agent",
        "status": "online",
        "hackathon": "All Things Agentic 2026",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
