#!/usr/bin/env bash
set -euo pipefail

# Script to test the cover generator locally before deploying to Cloud Run

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

echo ">>> Testing locally - Option 1: Run Flask app directly (fastest)"
echo ""
echo "First, install dependencies:"
echo "  pip install -r requirements.txt"
echo ""
echo "Then run:"
echo "  python app.py"
echo ""
echo "Or with custom port:"
echo "  export PORT=8080 && python app.py"
echo ""
echo "To use GCS (optional):"
echo "  export GCS_BUCKET=your-bucket-name && python app.py"
echo ""
echo "Then test with:"
echo "  curl http://localhost:8080/health"
echo ""
echo "  curl -X POST http://localhost:8080/generate \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"date\":\"2025-11-26\",\"away_team\":\"HOU\",\"home_team\":\"GSW\",\"title\":[\"火旺克金形势显\",\"刺锋遇曜力难前\"],\"circle_cells\":[2,4]}' \\"
echo "    --output test_cover.jpg"
echo ""
echo ">>> Testing locally - Option 2: Run with Docker (closer to Cloud Run)"
echo ""
echo "Building Docker image..."
docker build --platform linux/amd64 -t cover-generator-local .

echo ""
echo "Running container locally..."
echo "Container will be available at http://localhost:8080"
echo ""
echo "To use GCS (optional):"
echo "  docker run -p 8080:8080 -e PORT=8080 -e GCS_BUCKET=your-bucket-name cover-generator-local"
echo ""
docker run -p 8080:8080 \
  -e PORT=8080 \
  cover-generator-local

