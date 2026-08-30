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
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "APP_ENV=production" \
  --memory 512Mi \
  --timeout 300 \
  --min-instances 0 \
  --max-instances 3 \
  --quiet

echo ""
echo "=============================================="
echo "  ✅ Deployment complete!"
echo "=============================================="
echo ""
echo "Your backend is now live with the latest changes."
echo "Frontend (Vercel) deploys separately from the frontend/ directory."
echo ""
