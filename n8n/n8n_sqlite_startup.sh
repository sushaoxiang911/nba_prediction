#!/bin/sh
# Don't use set -e, we want to handle errors gracefully
set +e

LOCAL_DB_DIR="/tmp/n8n-db"
GCS_MOUNT="/mnt/n8n"
DB_FILE="database.sqlite"
SYNC_INTERVAL=30  # Sync every 30 seconds for better persistence

# Create directories
mkdir -p "${LOCAL_DB_DIR}" "${GCS_MOUNT}"
chmod 777 "${LOCAL_DB_DIR}" "${GCS_MOUNT}" 2>/dev/null || true

# Restore database from GCS if it exists
echo ">>> Checking for existing database in GCS..."
if [ -f "${GCS_MOUNT}/${DB_FILE}" ]; then
  echo ">>> Found database in GCS, restoring to local storage..."
  cp "${GCS_MOUNT}/${DB_FILE}" "${LOCAL_DB_DIR}/${DB_FILE}" 2>/dev/null || {
    echo ">>> WARNING: Failed to restore database file, starting fresh"
  }
  # Copy other .n8n files (credentials, workflows, etc.)
  echo ">>> Restoring other n8n files from GCS..."
  cp -r "${GCS_MOUNT}/"* "${LOCAL_DB_DIR}/" 2>/dev/null || true
  echo ">>> Database restore completed"
else
  echo ">>> No existing database found in GCS, starting fresh"
fi

# Function to sync DB to GCS with error handling
sync_to_gcs() {
  echo ">>> Syncing database to GCS..."
  # Use atomic copy: copy to temp file first, then move
  if [ -f "${LOCAL_DB_DIR}/${DB_FILE}" ]; then
    # Create a temporary file on GCS mount
    cp "${LOCAL_DB_DIR}/${DB_FILE}" "${GCS_MOUNT}/${DB_FILE}.tmp" 2>/dev/null || true
    # Atomic move (if supported) or regular move
    mv "${GCS_MOUNT}/${DB_FILE}.tmp" "${GCS_MOUNT}/${DB_FILE}" 2>/dev/null || \
      cp "${LOCAL_DB_DIR}/${DB_FILE}" "${GCS_MOUNT}/${DB_FILE}" 2>/dev/null || true
  fi
  # Sync other files
  cp -r "${LOCAL_DB_DIR}/"* "${GCS_MOUNT}/" 2>/dev/null || true
  echo ">>> Sync completed at $(date)"
}

# Enhanced sync function that also checkpoints SQLite WAL
sync_with_checkpoint() {
  # If sqlite3 is available, checkpoint WAL before syncing
  if command -v sqlite3 >/dev/null 2>&1 && [ -f "${LOCAL_DB_DIR}/${DB_FILE}" ]; then
    sqlite3 "${LOCAL_DB_DIR}/${DB_FILE}" "PRAGMA wal_checkpoint(TRUNCATE);" 2>/dev/null || true
  fi
  sync_to_gcs
}

# Function to cleanup on exit
cleanup() {
  echo ">>> Shutting down, performing final sync..."
  kill $SYNC_PID 2>/dev/null || true
  wait $SYNC_PID 2>/dev/null || true
  sync_with_checkpoint
}

# Set up trap for cleanup (must be before starting background processes)
trap cleanup EXIT INT TERM

# Start background sync process (more frequent for better persistence)
(
  while true; do
    sleep "${SYNC_INTERVAL}"
    sync_with_checkpoint
  done
) &
SYNC_PID=$!

# Start n8n in foreground (Cloud Run needs the main process to stay running)
echo ">>> Starting n8n..."
echo ">>> Environment: N8N_PORT=${N8N_PORT:-5678}, N8N_USER_FOLDER=${N8N_USER_FOLDER:-/home/node/.n8n}"
echo ">>> Database location: ${DB_SQLITE_DATABASE:-${LOCAL_DB_DIR}/${DB_FILE}}"
echo ">>> Background sync process PID: $SYNC_PID"

# Verify n8n command exists
if ! command -v n8n >/dev/null 2>&1; then
  echo "!!! ERROR: n8n command not found!"
  exit 1
fi

# Start n8n in foreground - this is the main process Cloud Run monitors
# The sync process runs in background and will continue running
# When n8n exits, the trap will cleanup the sync process
echo ">>> Executing: n8n start"
n8n start
EXIT_CODE=$?

echo ">>> n8n exited with code: $EXIT_CODE"
exit $EXIT_CODE

