#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="nba-prediction-n8n"
REGION="us-central1"
SERVICE_NAME="ssx-workflow"

# n8n auth / crypto
N8N_BASIC_AUTH_USER="admin"
N8N_BASIC_AUTH_PASSWORD="\$uShaoxiang911"
N8N_ENCRYPTION_KEY="80mubAobFc+6khwoTqIJihLbhk1tOneHkw126izi5gY="

# GCS bucket to hold .n8n (SQLite DB etc.)
N8N_BUCKET="n8n-sqlite-nba"

echo ">>> Setting gcloud project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

echo ">>> Checking GCS bucket exists: ${N8N_BUCKET}"
if ! gsutil ls -b "gs://${N8N_BUCKET}" >/dev/null 2>&1; then
  echo ">>> Creating GCS bucket: ${N8N_BUCKET}"
  gsutil mb -p "${PROJECT_ID}" -l "${REGION}" "gs://${N8N_BUCKET}"
else
  echo ">>> Bucket ${N8N_BUCKET} already exists"
fi

echo ">>> Deploying n8n (SQLite) to Cloud Run..."
echo ">>> Using local /tmp for SQLite DB (avoids Cloud Storage journal issues) with periodic GCS sync"
echo ">>> PERSISTENCE: Database syncs every 30 seconds to GCS. Risk: up to 30s of data loss if container crashes."
echo ">>> For production, consider using PostgreSQL (see n8n/n8n_cloudrun_deploy.sh) for better durability."

# Read startup script and embed it in the command
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STARTUP_SCRIPT="${SCRIPT_DIR}/n8n_sqlite_startup.sh"

if [ ! -f "${STARTUP_SCRIPT}" ]; then
  echo "!!! ERROR: Startup script not found: ${STARTUP_SCRIPT}"
  exit 1
fi

# Upload startup script to GCS bucket (will be accessible via the mounted volume)
# This avoids shell quoting issues with base64 encoding
echo ">>> Uploading startup script to GCS bucket..."
gsutil cp "${STARTUP_SCRIPT}" "gs://${N8N_BUCKET}/startup.sh" 2>/dev/null || {
  echo "!!! ERROR: Failed to upload startup script to GCS"
  exit 1
}
echo ">>> Startup script uploaded successfully"

# Copy script from mounted GCS volume to /tmp and execute
# The GCS bucket is mounted at /mnt/n8n, so startup.sh will be at /mnt/n8n/startup.sh
STARTUP_CMD="cp /mnt/n8n/startup.sh /tmp/start.sh 2>/dev/null && chmod +x /tmp/start.sh && exec /tmp/start.sh || (echo '!!! Failed to copy startup script from GCS mount' && exit 1)"

gcloud beta run deploy "${SERVICE_NAME}" \
  --image=docker.io/n8nio/n8n:latest \
  --platform=managed \
  --region="${REGION}" \
  --allow-unauthenticated \
  --port=5678 \
  --cpu=1 \
  --memory=2Gi \
  --timeout=300 \
  --min-instances=0 \
  --max-instances=1 \
  --no-cpu-throttling \
  --execution-environment=gen2 \
  --command="/bin/sh" \
  --args="-c,${STARTUP_CMD}" \
  --add-volume="name=n8n-data,type=cloud-storage,bucket=${N8N_BUCKET}" \
  --add-volume-mount="volume=n8n-data,mount-path=/mnt/n8n" \
  --set-env-vars="N8N_PORT=5678" \
  --set-env-vars="N8N_PROTOCOL=https" \
  --set-env-vars="N8N_BASIC_AUTH_ACTIVE=true" \
  --set-env-vars="N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}" \
  --set-env-vars="N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}" \
  --set-env-vars="N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}" \
  --set-env-vars="GENERIC_TIMEZONE=UTC" \
  --set-env-vars="N8N_USER_FOLDER=/tmp/n8n-db" \
  --set-env-vars="DB_TYPE=sqlite" \
  --set-env-vars="DB_SQLITE_VACUUM_ON_STARTUP=false" \
  --set-env-vars="DB_SQLITE_DATABASE=/tmp/n8n-db/database.sqlite" \
  --set-env-vars="N8N_LOG_LEVEL=info"

echo ">>> Deployment finished."

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ">>> n8n (SQLite) is at: ${SERVICE_URL}"
echo "    Login:"
echo "      user: ${N8N_BASIC_AUTH_USER}"
echo "      pass: ${N8N_BASIC_AUTH_PASSWORD}"
