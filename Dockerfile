FROM python:3.11-slim

# Install system packages for Pillow, Ghostscript, and build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ghostscript \
        libjpeg-dev \
        libfreetype6-dev \
        libwebp-dev \
        build-essential \
        libz-dev \
        zlib1g-dev \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy and install Python dependencies (make sure google-cloud-storage is in requirements.txt)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Expose Flask port
EXPOSE 8080

# Run Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "0", "app:app"]

