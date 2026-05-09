FROM python:3.11-slim

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

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--worker-class", "sync", \
     "--timeout", "300", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50", \
     "app:app"]
