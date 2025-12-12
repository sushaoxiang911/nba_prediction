#!/usr/bin/env bash
set -euo pipefail

# Script to test the Discord bot locally before deploying to Cloud Run

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo ">>> Testing Discord Bot Locally"
echo ""
echo "Prerequisites:"
echo "  1. Discord bot token (get from https://discord.com/developers/applications)"
echo "  2. Google Cloud credentials configured:"
echo "     Option A (for local testing): gcloud auth application-default login"
echo "     Option B (recommended for production): Use service account key file"
echo "  3. Access to the GCS bucket: nba-cover-assets"
echo ""
echo "Note: Application-default credentials work for uploads but won't generate signed URLs."
echo "      For signed URLs, use a service account key file (see Option B below)."
echo ""
echo ">>> Option 1: Run directly with Python (fastest for testing)"
echo ""
echo "First, install dependencies:"
echo "  pip install -r requirements.txt"
echo ""
echo "Then set environment variables and run:"
echo "  export DISCORD_TOKEN='your-discord-bot-token'"
echo "  export ASSETS_BUCKET='nba-cover-assets'  # optional, this is the default"
echo "  python bot.py"
echo ""
echo ">>> Option 2: Run with Docker (closer to Cloud Run environment)"
echo ""
echo "Building Docker image..."
# Detect platform - use native platform for local testing (faster on ARM Macs)
docker build -t discord-bot-local .

echo ""
echo "Running container locally..."
echo ""
echo "Option A: Using service account key file (supports signed URLs):"
echo "  docker run -p 8080:8080 \\"
echo "    -e DISCORD_TOKEN='your-discord-bot-token' \\"
echo "    -e ASSETS_BUCKET='nba-cover-assets' \\"
echo "    -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/credentials.json \\"
echo "    -v /path/to/service-account-key.json:/tmp/credentials.json:ro \\"
echo "    discord-bot-local"
echo ""
echo "Option B: Using gcloud application-default credentials (no signed URLs):"

# Check if DISCORD_TOKEN is set
if [ -z "${DISCORD_TOKEN:-}" ]; then
    echo ""
    echo "⚠️  DISCORD_TOKEN environment variable is not set!"
    echo "   Please set it first:"
    echo "   export DISCORD_TOKEN='your-discord-bot-token'"
    echo ""
    echo "   Then run this script again, or run the docker command manually:"
    echo "   docker run -p 8080:8080 \\"
    echo "     -e DISCORD_TOKEN=\"\$DISCORD_TOKEN\" \\"
    echo "     -e ASSETS_BUCKET=\"\${ASSETS_BUCKET:-nba-cover-assets}\" \\"
    echo "     -v ~/.config/gcloud:/root/.config/gcloud \\"
    echo "     discord-bot-local"
    exit 1
fi

# Set default ASSETS_BUCKET if not provided
ASSETS_BUCKET="${ASSETS_BUCKET:-nba-cover-assets}"

# Check for application-default credentials
ADC_PATH="$HOME/.config/gcloud/application_default_credentials.json"
if [ ! -f "$ADC_PATH" ]; then
    echo ""
    echo "⚠️  Application Default Credentials not found!"
    echo "   Please run: gcloud auth application-default login"
    echo ""
    exit 1
fi

# Get GCP project ID (optional, but helpful)
GCP_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")

echo "Running Docker container with application-default credentials..."
echo "Using credentials from: $ADC_PATH"
echo ""

# Build docker run command
DOCKER_ARGS=(
  -p 8080:8080
  -e "DISCORD_TOKEN=$DISCORD_TOKEN"
  -e "ASSETS_BUCKET=$ASSETS_BUCKET"
  -e "GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json"
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro"
)

# Add GCP project if available
if [ -n "$GCP_PROJECT" ]; then
  DOCKER_ARGS+=(-e "GOOGLE_CLOUD_PROJECT=$GCP_PROJECT")
fi

DOCKER_ARGS+=(discord-bot-local)

docker run "${DOCKER_ARGS[@]}"
echo ""
echo ">>> Testing the Bot Commands"
echo ""
echo "Once the bot is running and online in Discord:"
echo ""
echo "1. Test upload_qimen command:"
echo "   - Attach an image to a Discord message"
echo "   - Type: !upload_qimen 2025-12-07.jpg"
echo "   - Bot should reply with confirmation and GCS path"
echo ""
echo "2. Test upload_player command:"
echo "   - Attach an image to a Discord message"
echo "   - Type: !upload_player LAL_Doncic.png"
echo "   - Bot should reply with confirmation and GCS path"
echo ""
echo "3. Test error handling:"
echo "   - Try !upload_qimen without an attachment (should show error)"
echo "   - Try !upload_qimen with a non-image file (should show error)"
echo ""
echo ">>> Health Check"
echo ""
echo "The bot also runs a health check server on port 8080:"
echo "  curl http://localhost:8080"
echo "  Should return: OK"
echo ""

