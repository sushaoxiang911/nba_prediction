#!/usr/bin/env bash
set -euo pipefail

#############################################
# CONFIG – EDIT THESE VALUES
#############################################

# GCP project & region
PROJECT_ID="nba-prediction-n8n"
REGION="us-central1"

# Cloud Run service name
SERVICE_NAME="cover-generator"

# GCS bucket name for assets (set to empty string to use local paths)
GCS_BUCKET="${GCS_BUCKET:-nba-cover-assets}"

# Docker image name (will be pushed to GCR)
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

#############################################
# END CONFIG
#############################################

echo ">>> Setting gcloud project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> Building Docker image for linux/amd64 (Cloud Run requirement)..."
cd "${SCRIPT_DIR}"

# Build the Docker image for linux/amd64 platform (required for Cloud Run)
docker build --platform linux/amd64 -t "${IMAGE_NAME}" .

echo ">>> Pushing Docker image to Google Container Registry..."
docker push "${IMAGE_NAME}"

echo ">>> Deploying to Cloud Run..."
DEPLOY_CMD="gcloud run deploy ${SERVICE_NAME} \
  --image=${IMAGE_NAME} \
  --platform=managed \
  --region=${REGION} \
  --allow-unauthenticated \
  --port=8080 \
  --cpu=2 \
  --memory=4Gi \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=10 \
  --no-cpu-throttling"

# Add GCS_BUCKET env var if specified
if [ -n "${GCS_BUCKET}" ]; then
  DEPLOY_CMD="${DEPLOY_CMD} --set-env-vars=GCS_BUCKET=${GCS_BUCKET}"
fi

eval ${DEPLOY_CMD}

echo ">>> Deployment complete!"

#############################################
# Show service URL
#############################################

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ""
echo ">>> Cover Generator is deployed at: ${SERVICE_URL}"
echo ""
echo ">>> Test the service:"
echo "    curl ${SERVICE_URL}/health"
echo ""
echo ">>> Generate a cover:"
echo "    curl -X POST ${SERVICE_URL}/generate \\"
echo "      -H 'Content-Type: application/json' \\"
echo "      -d '{\"date\":\"2025-11-26\",\"away_team\":\"HOU\",\"home_team\":\"GSW\",\"title\":[\"火旺克金形势显\",\"刺锋遇曜力难前\"]}' \\"
echo "      --output cover.jpg"
echo ""

