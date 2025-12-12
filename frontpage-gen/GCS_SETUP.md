# Google Cloud Storage Setup Guide

This guide explains how to set up and use Google Cloud Storage (GCS) for storing cover generator assets.

## Benefits of Using GCS

- **Dynamic asset management**: Add/update backgrounds, players, logos, and qimen images without rebuilding Docker images
- **Smaller Docker images**: Assets are not bundled in the container
- **Easy updates**: Upload new assets via `gsutil` or the GCS console
- **Scalability**: Multiple Cloud Run instances can access the same assets

## Setup Steps

### 1. Create a GCS Bucket

```bash
# Set your project and bucket name
export PROJECT_ID="nba-prediction-n8n"
export GCS_BUCKET="nba-cover-assets"

# Create the bucket
gsutil mb -p "${PROJECT_ID}" -l us-central1 "gs://${GCS_BUCKET}"
```

### 2. Upload Assets to GCS

Use the provided script to upload all assets:

```bash
cd frontpage-gen
export GCS_BUCKET="nba-cover-assets"  # Your bucket name
./upload_assets_to_gcs.sh
```

Or manually upload specific directories:

```bash
# Upload backgrounds
gsutil -m cp -r backgrounds/* "gs://${GCS_BUCKET}/backgrounds/"

# Upload players
gsutil -m cp -r players/* "gs://${GCS_BUCKET}/players/"

# Upload qimen images
gsutil -m cp -r qimen/* "gs://${GCS_BUCKET}/qimen/"

# Upload assets (fonts, logos, etc.)
gsutil -m cp -r assets/* "gs://${GCS_BUCKET}/assets/"

# Upload logos (if exists)
gsutil -m cp -r logos/* "gs://${GCS_BUCKET}/logos/"
```

### 3. Grant Cloud Run Access to GCS

Cloud Run services need permission to read from GCS. The service account used by Cloud Run needs the "Storage Object Viewer" role:

```bash
# Set your project and service details
PROJECT_ID="nba-prediction-n8n"
SERVICE_NAME="cover-generator"
REGION="us-central1"

# Get the service account used by your Cloud Run service
SERVICE_ACCOUNT=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --project="${PROJECT_ID}" \
  --format="value(spec.template.spec.serviceAccountName)")

# If no custom service account is set, Cloud Run uses the compute service account
if [ -z "${SERVICE_ACCOUNT}" ] || [ "${SERVICE_ACCOUNT}" = "default" ]; then
  # Get the project number to construct the compute service account
  PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
  SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
fi

echo "Using service account: ${SERVICE_ACCOUNT}"

# Grant access to GCS
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/storage.objectViewer"
```

Alternatively, you can use a custom service account with the necessary permissions. If you're using a custom service account, specify it when deploying:

```bash
# Deploy with a custom service account
gcloud run deploy "${SERVICE_NAME}" \
  --service-account="your-custom-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  # ... other flags
```

### 4. Deploy with GCS Configuration

Update `deploy_cloudrun.sh` to set your bucket name:

```bash
# Edit deploy_cloudrun.sh and set:
GCS_BUCKET="nba-cover-assets"  # Your bucket name
```

Then deploy:

```bash
./deploy_cloudrun.sh
```

The deployment script will automatically set the `GCS_BUCKET` environment variable.

### 5. Adding New Assets

To add new assets without redeploying:

```bash
# Add a new background
gsutil cp new_background.png "gs://${GCS_BUCKET}/backgrounds/"

# Add a new player image
gsutil cp HOU_NewPlayer.png "gs://${GCS_BUCKET}/players/"

# Add a new qimen image for a date
gsutil cp 2025-11-27.jpg "gs://${GCS_BUCKET}/qimen/"
```

The service will automatically use the new assets on the next request (they're cached locally in the container).

## Bucket Structure

Your GCS bucket should have the following structure:

```
gs://your-bucket/
├── backgrounds/
│   ├── bg_001.png
│   ├── bg_002.png
│   └── ...
├── players/
│   ├── HOU_Sengun.png
│   ├── GSW_Curry.png
│   └── ...
├── qimen/
│   ├── 2025-11-24.jpg
│   ├── 2025-11-25.jpg
│   └── ...
├── assets/
│   ├── taiji.png
│   ├── fog.png
│   ├── circle-red.png
│   ├── footer.png
│   └── STXINGKA.TTF
└── logos/
    ├── DEN.png
    ├── LAC.png
    └── ...
```

## Local Development

For local testing, you can either:

1. **Use local paths** (default): Don't set `GCS_BUCKET` environment variable
2. **Use GCS**: Set `GCS_BUCKET` environment variable:
   ```bash
   export GCS_BUCKET="nba-cover-assets"
   python app.py
   ```

Make sure you're authenticated with GCS:
```bash
gcloud auth application-default login
```

## Troubleshooting

### "Permission denied" errors
- Ensure the Cloud Run service account has `roles/storage.objectViewer` permission
- Check that the bucket name is correct

### "File not found" errors
- Verify the file exists in GCS: `gsutil ls gs://your-bucket/path/to/file`
- Check the bucket structure matches the expected format
- Ensure file names match exactly (case-sensitive)

### Slow performance
- Files are cached locally after first download
- Consider using Cloud CDN for frequently accessed assets

