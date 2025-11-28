# Use Python 3.11 slim image
FROM python:3.11-slim

# Install system dependencies for image processing
# rembg requires libgomp1 for ONNX runtime (OpenMP support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire frontpage_gen directory
# Note: assets/ is bundled in the image (static files)
# backgrounds/, logos/, players/, and qimen/ are excluded via .dockerignore
# These are stored in GCS and downloaded at runtime
COPY . .

# Expose port (Cloud Run will set PORT env var)
ENV PORT=8080

# Run the Flask app with gunicorn (using JSON format for CMD)
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 300 app:app"]

