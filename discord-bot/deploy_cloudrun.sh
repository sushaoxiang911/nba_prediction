PROJECT_ID="nba-prediction-n8n"
REGION="us-central1"
SERVICE_NAME="discord-gcs-bot"
ASSETS_BUCKET="nba-cover-assets"
DISCORD_TOKEN=

# Submit container to Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --set-env-vars DISCORD_TOKEN="$DISCORD_TOKEN",ASSETS_BUCKET="$ASSETS_BUCKET",GOOGLE_CLOUD_PROJECT="$PROJECT_ID" \
  --memory 256Mi \
  --cpu 0.08 \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 1 \
  --allow-unauthenticated
