#!/bin/bash
# deploy.sh — Build and deploy Trip Planning Agent to Cloud Run
#
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -e   # stop on any error

# ── Config — edit these ────────────────────────────────────────────────────────
PROJECT_ID="trip-agent-492405"
SERVICE_NAME="trip-planning-agent"
REGION="us-east1"
IMAGE="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo ""
echo "================================================"
echo "  Deploying Trip Planning Agent to Cloud Run"
echo "================================================"
echo ""

# ── Step 1: Set active GCP project ────────────────────────────────────────────
echo "1. Setting GCP project..."
gcloud config set project $PROJECT_ID

# ── Step 2: Enable required GCP APIs ──────────────────────────────────────────
echo "2. Enabling required APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  secretmanager.googleapis.com

# ── Step 3: Store secrets in Secret Manager ────────────────────────────────────
echo "3. Storing API keys in Secret Manager..."

# Only create secrets if they don't already exist
create_secret() {
  local name=$1
  local value=$2
  if ! gcloud secrets describe $name --project=$PROJECT_ID &>/dev/null; then
    echo "  Creating secret: $name"
    echo -n "$value" | gcloud secrets create $name \
      --data-file=- \
      --project=$PROJECT_ID
  else
    echo "  Secret $name already exists — skipping."
  fi
}

create_secret "ANTHROPIC_API_KEY"    "$ANTHROPIC_API_KEY"
create_secret "SERPAPI_API_KEY"      "$SERPAPI_API_KEY"
create_secret "OPENWEATHER_API_KEY"  "$OPENWEATHER_API_KEY"

# ── Step 4: Build and push Docker image ───────────────────────────────────────
echo "4. Building and pushing Docker image..."
gcloud builds submit --tag $IMAGE .

# ── Step 5: Deploy to Cloud Run ───────────────────────────────────────────────
echo "5. Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image $IMAGE \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 120 \
  --set-secrets="ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest,SERPAPI_API_KEY=SERPAPI_API_KEY:latest,OPENWEATHER_API_KEY=OPENWEATHER_API_KEY:latest"

# ── Done ───────────────────────────────────────────────────────────────────────
echo ""
echo "================================================"
echo "  Deployment complete!"
echo "================================================"
echo ""
echo "Your agent is live at:"
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format "value(status.url)"
echo ""
echo "Test it:"
echo "  curl -X POST <your-url>/chat \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"message\": \"Plan me a trip to Tokyo\"}'"
