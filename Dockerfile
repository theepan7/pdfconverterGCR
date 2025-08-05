FROM python:3.11-slim

# Install essential system packages for Pillow, Ghostscript, and build tools
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

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app source code
COPY . .

# Make sure upload/processed folders exist (optional, since your app does this too)
RUN mkdir -p uploads processed

# Expose Flask port
EXPOSE 8080

# Run Flask app
CMD ["python", "app.py"]
