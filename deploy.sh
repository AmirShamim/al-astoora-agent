#!/bin/bash
# deploy.sh — Al Astoora Agent: Pull latest code and redeploy to Cloud Run
# Usage: bash deploy.sh
# Run this from Cloud Shell after pushing changes from your local machine.

set -e

echo "=============================================="
echo "  Al Astoora Agent — Deploy to Cloud Run"
echo "=============================================="

# 1. Pull latest changes from GitHub
echo ""
echo "📥 Pulling latest changes from GitHub..."
git pull origin main

# 2. Deploy to Cloud Run (only backend files — frontend/ is excluded via .gcloudignore)
echo ""
echo "🚀 Deploying backend to Cloud Run..."
echo "   (frontend/ is excluded via .gcloudignore — only backend code is uploaded)"
echo ""

gcloud run deploy al-astoora-agent \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 3 \
  --set-env-vars "APP_ENV=production,GCP_PROJECT_ID=project-080b5971-eb4b-4d2b-a4c,GCP_LOCATION=asia-south1,GCS_BUCKET_NAME=al-astoora-documents,GEMINI_MODEL=gemini-3.7-flash,GEMINI_LOCATION=global,WHATSAPP_TOKEN=EAAStEGDoJOYBR6eSp1ZAu8IxU86MbIQX6SkHOY5SDQtNvUaph2yUFtCZAgiz0ZBZCn2r7japgrLSMEps2QcU1S2lNerokp1RZBzpFXxP3zA2b34jJz7lwVezhE60TZCEZAsWmXdtguJKwo4e5j6kyqr1kjTgRZCvWZC05IdHm8EqYhxSHMcsktK8wFJuNvi0bgBa34wZDZD,WHATSAPP_PHONE_NUMBER_ID=1113443245192571,BOT_PHONE_NUMBER=919289581053,WEBHOOK_VERIFY_TOKEN=al_astoora_secure_verify_token_2026" \
  --quiet

echo ""
echo "=============================================="
echo "  ✅ Deployment complete!"
echo "=============================================="
echo ""
echo "Your backend is now live with the latest changes."
echo "Frontend (Vercel) deploys separately from the frontend/ directory."
echo ""
