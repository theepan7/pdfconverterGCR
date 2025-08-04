FROM python:3.11-slim

# Install only essential system packages for Pillow, ReportLab, and Ghostscript
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ghostscript \
    libjpeg-dev \
    libfreetype6-dev \
    libwebp-dev \
    build-essential \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*
    
# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Ensure folders exist
RUN mkdir -p uploads processed

# Expose Flask default port
EXPOSE 8080

# Start the Flask app
CMD ["python", "app.py"]
