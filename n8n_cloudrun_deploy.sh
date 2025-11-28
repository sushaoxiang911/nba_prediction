#!/usr/bin/env bash
set -euo pipefail

#############################################
# CONFIG – EDIT THESE VALUES
#############################################

# GCP project & region
PROJECT_ID="nba-prediction-n8n"
REGION="us-central1"

# Cloud Run service name
SERVICE_NAME="n8n"

# Cloud SQL Postgres instance name (NOT connection name)
SQL_INSTANCE_NAME="n8n-postgres"

# Postgres DB + user
DB_NAME="n8n"
DB_USER="n8n_user"
DB_PASSWORD="CHANGE_ME_DB_PASSWORD"          # <-- set this to the password you used / will use for n8n_user

# n8n basic auth (for the editor UI)
N8N_BASIC_AUTH_USER="admin"                  # <-- choose your admin username
N8N_BASIC_AUTH_PASSWORD="CHANGE_ME_ADMIN"    # <-- choose a strong password

# n8n encryption key (MUST stay stable across deploys, do NOT change once in use)
# You can generate one with:  openssl rand -base64 32
N8N_ENCRYPTION_KEY="CHANGE_ME_ENCRYPTION_KEY"

#############################################
# END CONFIG
#############################################

echo ">>> Setting gcloud project to: ${PROJECT_ID}"
gcloud config set project "${PROJECT_ID}" >/dev/null

#############################################
# 1) Ensure Cloud SQL DB exists
#############################################

echo ">>> Ensuring Cloud SQL database '${DB_NAME}' exists on instance '${SQL_INSTANCE_NAME}'..."

# Check if DB exists
if gcloud sql databases list --instance="${SQL_INSTANCE_NAME}" \
  --format="value(name)" | grep -q "^${DB_NAME}\$"; then
  echo ">>> Database '${DB_NAME}' already exists. Skipping creation."
else
  echo ">>> Creating database '${DB_NAME}'..."
  gcloud sql databases create "${DB_NAME}" --instance="${SQL_INSTANCE_NAME}"
fi

#############################################
# 2) Ensure user exists & set password
#############################################

echo ">>> Ensuring Postgres user '${DB_USER}' exists on instance '${SQL_INSTANCE_NAME}'..."

if gcloud sql users list --instance="${SQL_INSTANCE_NAME}" \
  --format="value(name)" | grep -q "^${DB_USER}\$"; then
  echo ">>> User '${DB_USER}' already exists. Updating password..."
  gcloud sql users set-password "${DB_USER}" \
    --instance="${SQL_INSTANCE_NAME}" \
    --password="${DB_PASSWORD}"
else
  echo ">>> Creating user '${DB_USER}'..."
  gcloud sql users create "${DB_USER}" \
    --instance="${SQL_INSTANCE_NAME}" \
    --password="${DB_PASSWORD}"
fi

#############################################
# 3) Get Cloud SQL connection name
#############################################

echo ">>> Fetching Cloud SQL connection name..."
SQL_CONNECTION_NAME=$(gcloud sql instances describe "${SQL_INSTANCE_NAME}" \
  --format="value(connectionName)")

if [[ -z "${SQL_CONNECTION_NAME}" ]]; then
  echo "!!! ERROR: Could not get Cloud SQL connection name for instance '${SQL_INSTANCE_NAME}'"
  exit 1
fi

echo ">>> Cloud SQL connection name: ${SQL_CONNECTION_NAME}"

#############################################
# 4) Deploy n8n to Cloud Run
#############################################

echo ">>> Deploying n8n to Cloud Run service '${SERVICE_NAME}' in region '${REGION}'..."

# NOTE:
# - Uses official n8n image from Docker Hub
# - Listens on port 5678 (n8n default)
# - Connects to Cloud SQL via Unix socket /cloudsql/CONNECTION_NAME
# - Basic auth enabled
# - Encryption key set (must remain constant over time)

gcloud run deploy "${SERVICE_NAME}" \
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
  --command="/bin/sh" \
  --args="-c,sleep 5; n8n start" \
  --add-cloudsql-instances="${SQL_CONNECTION_NAME}" \
  --set-env-vars="N8N_PORT=5678" \
  --set-env-vars="N8N_PROTOCOL=https" \
  --set-env-vars="N8N_USER_FOLDER=/home/node/.n8n" \
  --set-env-vars="GENERIC_TIMEZONE=UTC" \
  --set-env-vars="QUEUE_HEALTH_CHECK_ACTIVE=true" \
  --set-env-vars="DB_TYPE=postgresdb" \
  --set-env-vars="DB_POSTGRESDB_DATABASE=${DB_NAME}" \
  --set-env-vars="DB_POSTGRESDB_USER=${DB_USER}" \
  --set-env-vars="DB_POSTGRESDB_PASSWORD=${DB_PASSWORD}" \
  --set-env-vars="DB_POSTGRESDB_HOST=/cloudsql/${SQL_CONNECTION_NAME}" \
  --set-env-vars="DB_POSTGRESDB_PORT=5432" \
  --set-env-vars="DB_POSTGRESDB_SCHEMA=public" \
  --set-env-vars="N8N_BASIC_AUTH_ACTIVE=true" \
  --set-env-vars="N8N_BASIC_AUTH_USER=${N8N_BASIC_AUTH_USER}" \
  --set-env-vars="N8N_BASIC_AUTH_PASSWORD=${N8N_BASIC_AUTH_PASSWORD}" \
  --set-env-vars="N8N_ENCRYPTION_KEY=${N8N_ENCRYPTION_KEY}" \
  --set-env-vars="N8N_LOG_LEVEL=info"

echo ">>> Deployment command finished."

#############################################
# 5) Show service URL
#############################################

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --region="${REGION}" \
  --format="value(status.url)")

echo ">>> n8n is deployed at: ${SERVICE_URL}"
echo ">>> Log in with basic auth:"
echo "    Username: ${N8N_BASIC_AUTH_USER}"
echo "    Password: ${N8N_BASIC_AUTH_PASSWORD}"

echo ">>> IMPORTANT:"
echo "    - Do NOT change N8N_ENCRYPTION_KEY after you start using n8n, or existing credentials will break."
echo "    - You can set N8N_HOST to the host part of the URL later if you want correct webhook URLs."

