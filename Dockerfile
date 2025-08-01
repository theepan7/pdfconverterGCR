FROM python:3.11-slim

# Install Ghostscript for PDF compression
RUN apt-get update && \
    apt-get install -y --no-install-recommends ghostscript && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure upload and processed folders exist
RUN mkdir -p uploads processed

# Expose the port your app runs on (8080 by default)
EXPOSE 8080

# Start the Flask app
CMD ["python", "app.py"]
