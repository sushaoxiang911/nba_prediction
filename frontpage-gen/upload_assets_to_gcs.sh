#!/usr/bin/env bash
set -euo pipefail

#############################################
# Script to upload assets to Google Cloud Storage
#############################################

# GCP project & bucket name
PROJECT_ID="${PROJECT_ID:-nba-prediction-n8n}"
BUCKET_NAME="${GCS_BUCKET:-nba-cover-assets}"

echo ">>> Setting gcloud project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">>> Creating GCS bucket if it doesn't exist..."
gsutil mb -p "${PROJECT_ID}" -l us-central1 "gs://${BUCKET_NAME}" 2>/dev/null || echo "Bucket already exists or creation failed"

echo ""
echo ">>> Uploading assets to gs://${BUCKET_NAME}..."
echo ""

# Upload backgrounds
if [ -d "${SCRIPT_DIR}/backgrounds" ]; then
    echo "Uploading backgrounds..."
    gsutil -m cp -r "${SCRIPT_DIR}/backgrounds"/* "gs://${BUCKET_NAME}/backgrounds/"
fi

# Upload players
if [ -d "${SCRIPT_DIR}/players" ]; then
    echo "Uploading players..."
    gsutil -m cp -r "${SCRIPT_DIR}/players"/* "gs://${BUCKET_NAME}/players/"
fi

# Upload qimen
if [ -d "${SCRIPT_DIR}/qimen" ]; then
    echo "Uploading qimen..."
    gsutil -m cp -r "${SCRIPT_DIR}/qimen"/* "gs://${BUCKET_NAME}/qimen/"
fi

# Upload logos (if exists)
if [ -d "${SCRIPT_DIR}/logos" ]; then
    echo "Uploading logos..."
    gsutil -m cp -r "${SCRIPT_DIR}/logos"/* "gs://${BUCKET_NAME}/logos/"
fi

echo ""
echo ">>> Upload complete!"
echo ""
echo ">>> To use GCS in your Cloud Run service, set the environment variable:"
echo "    GCS_BUCKET=${BUCKET_NAME}"
echo ""
echo ">>> You can add this to your deploy_cloudrun.sh script:"
echo "    --set-env-vars=\"GCS_BUCKET=${BUCKET_NAME}\""
echo ""

