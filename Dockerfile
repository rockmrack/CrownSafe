# Use official Python runtime as base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt || \
    pip install --no-cache-dir \
        fastapi \
        uvicorn \
        sqlalchemy \
        psycopg2-binary \
        pydantic \
        python-jose \
        passlib \
        python-multipart \
        httpx \
        redis \
        celery \
        requests \
        psutil \
        python-dotenv

# Copy application code
COPY . .

# Create startup script inline if it doesn't exist
RUN if [ ! -f startup.py ]; then \
    echo '#!/usr/bin/env python3' > startup.py && \
    echo 'import os' >> startup.py && \
    echo 'import uvicorn' >> startup.py && \
    echo 'os.environ.setdefault("API_HOST", "0.0.0.0")' >> startup.py && \
    echo 'os.environ.setdefault("API_PORT", "8001")' >> startup.py && \
    echo 'os.environ.setdefault("TEST_MODE", "false")' >> startup.py && \
    echo 'try:' >> startup.py && \
    echo '    from api.main_babyshield import app' >> startup.py && \
    echo '    print("Starting main_babyshield app")' >> startup.py && \
    echo 'except ImportError:' >> startup.py && \
    echo '    from api.main_babyshield_simplified import app' >> startup.py && \
    echo '    print("Starting simplified app")' >> startup.py && \
    echo 'uvicorn.run(app, host="0.0.0.0", port=8001)' >> startup.py; \
    fi

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    API_HOST=0.0.0.0 \
    API_PORT=8001

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1

# Run the application
CMD ["python", "startup.py"]