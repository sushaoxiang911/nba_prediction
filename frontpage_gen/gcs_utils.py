"""
Utilities for downloading assets from Google Cloud Storage.
Supports both GCS bucket paths and local file paths for backward compatibility.
"""
import os
import tempfile
from google.cloud import storage
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Cache directory for downloaded files
_cache_dir = None

def get_cache_dir():
    """Get or create the cache directory for downloaded files"""
    global _cache_dir
    if _cache_dir is None:
        _cache_dir = tempfile.mkdtemp(prefix="cover_gen_cache_")
        logger.info(f"Created cache directory: {_cache_dir}")
    return _cache_dir

def is_gcs_path(path: str) -> bool:
    """Check if a path is a GCS path (gs://bucket/path)"""
    return path.startswith("gs://")

def download_from_gcs(gcs_path: str, local_filename: Optional[str] = None) -> str:
    """
    Download a file from GCS to local cache.
    
    Args:
        gcs_path: GCS path in format gs://bucket/path/to/file
        local_filename: Optional local filename (defaults to basename of GCS path)
    
    Returns:
        Local file path
    """
    if not is_gcs_path(gcs_path):
        # Already a local path, return as-is
        return gcs_path
    
    # Parse GCS path: gs://bucket/path/to/file
    parts = gcs_path.replace("gs://", "").split("/", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid GCS path format: {gcs_path}")
    
    bucket_name = parts[0]
    blob_path = parts[1]
    
    # Determine local filename
    if local_filename is None:
        local_filename = os.path.basename(blob_path)
    
    # Check cache first
    cache_dir = get_cache_dir()
    local_path = os.path.join(cache_dir, local_filename)
    
    if os.path.exists(local_path):
        logger.info(f"Using cached file: {local_path}")
        return local_path
    
    # Download from GCS
    logger.info(f"Downloading {gcs_path} to {local_path}")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    
    blob.download_to_filename(local_path)
    logger.info(f"Downloaded to {local_path}")
    
    return local_path

def list_gcs_files(gcs_dir: str, prefix: str = "") -> list:
    """
    List files in a GCS directory.
    
    Args:
        gcs_dir: GCS path in format gs://bucket/path/to/dir
        prefix: Optional prefix to filter files
    
    Returns:
        List of file names (not full paths)
    """
    if not is_gcs_path(gcs_dir):
        # Local directory
        local_dir = os.path.join(gcs_dir, prefix) if prefix else gcs_dir
        if not os.path.exists(local_dir):
            return []
        return [f for f in os.listdir(local_dir) if os.path.isfile(os.path.join(local_dir, f))]
    
    # Parse GCS path
    parts = gcs_dir.replace("gs://", "").split("/", 1)
    bucket_name = parts[0]
    dir_path = parts[1] if len(parts) > 1 else ""
    
    # Build full prefix
    full_prefix = f"{dir_path}/{prefix}" if dir_path and prefix else (dir_path or prefix)
    if full_prefix and not full_prefix.endswith("/"):
        full_prefix += "/"
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blobs = bucket.list_blobs(prefix=full_prefix)
    
    # Extract just the filenames
    files = []
    for blob in blobs:
        if blob.name.endswith("/"):  # Skip directories
            continue
        filename = os.path.basename(blob.name)
        if filename:
            files.append(filename)
    
    return files

def get_gcs_path(bucket: str, *path_parts: str) -> str:
    """Construct a GCS path from bucket and path parts"""
    path = "/".join(path_parts)
    return f"gs://{bucket}/{path}"

