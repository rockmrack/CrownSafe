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
    tesseract-ocr \
    tesseract-ocr-eng \
    libglib2.0-0 \
    build-essential \
    cmake \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install DataMatrix and OCR dependencies with comprehensive diagnostics
RUN apt-get update && \
    echo "🔍 Checking available DataMatrix packages..." && \
    apt-cache search libdmtx && \
    echo "📦 Installing DataMatrix dependencies..." && \
    (apt-get install -y --no-install-recommends libdmtx0a libdmtx-dev && \
     echo "✅ DataMatrix system libraries (libdmtx0a) installed successfully") || \
    (apt-get install -y --no-install-recommends libdmtx0b libdmtx-dev && \
     echo "✅ DataMatrix system libraries (libdmtx0b) installed successfully") || \
    (apt-get install -y --no-install-recommends libdmtx-dev && \
     echo "✅ DataMatrix development libraries installed (without specific version)") || \
    (echo "❌ WARNING: All DataMatrix installation attempts failed" && \
     echo "Available packages containing 'dmtx':" && apt-cache search dmtx) && \
    echo "📝 Installing additional OCR dependencies..." && \
    apt-get install -y --no-install-recommends \
        libtesseract-dev \
        libleptonica-dev \
        pkg-config && \
    echo "✅ OCR development libraries installed" && \
    echo "🔍 Final DataMatrix library check..." && \
    ldconfig -p | grep dmtx || echo "No DataMatrix libraries found in ldconfig" && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies - MUST succeed for all critical packages
RUN echo "📦 Installing Python packages..." && \
    pip install --no-cache-dir --upgrade pip setuptools wheel && \
    echo "Installing critical packages first..." && \
    pip install --no-cache-dir \
        fastapi==0.104.1 \
        uvicorn==0.24.0 \
        sqlalchemy==2.0.23 \
        psycopg2-binary==2.9.9 \
        pydantic==2.5.2 \
        python-jose==3.3.0 \
        passlib==1.7.4 \
        python-multipart==0.0.6 \
        httpx==0.25.2 \
        redis==5.0.1 \
        celery==5.3.4 \
        requests==2.31.0 \
        psutil==5.9.6 \
        python-dotenv==1.0.0 \
        openai==1.5.0 \
        email-validator==2.1.0 \
        prometheus-client==0.19.0 \
        alembic==1.12.1 \
        slowapi==0.1.9 \
        boto3==1.34.2 \
        PyJWT==2.8.0 \
        markdown==3.5.1 \
        aiosmtplib==3.0.1 \
        jinja2==3.1.2 \
        firebase-admin==6.3.0 \
        Pillow==10.1.0 \
        pyzbar==0.1.9 \
        opencv-python==4.8.1.78 \
        reportlab==4.0.7 \
        qrcode==7.4.2 \
        pytesseract==0.3.10 \
        easyocr==1.7.0 && \
    echo "✅ Critical packages installed" && \
    echo "Installing remaining packages (may fail)..." && \
    (pip install --no-cache-dir -r requirements.txt || echo "⚠️ Some optional packages failed") && \
    echo "🔧 Installing optional DataMatrix and OCR support..." && \
    echo "🔍 Checking system libraries for pylibdmtx..." && \
    ldconfig -p | grep dmtx && \
    echo "📦 Attempting pylibdmtx installation..." && \
    (pip install --no-cache-dir pylibdmtx==0.1.10 && \
     echo "✅ DataMatrix support (pylibdmtx) installed successfully" && \
     python -c "import pylibdmtx; print('✅ pylibdmtx import successful')") || \
    (echo "⚠️  pylibdmtx 0.1.10 failed, trying without version..." && \
     pip install --no-cache-dir pylibdmtx && \
     echo "✅ DataMatrix support (pylibdmtx latest) installed successfully" && \
     python -c "import pylibdmtx; print('✅ pylibdmtx import successful')") || \
    echo "❌ DataMatrix support not available - will run without it" && \
    echo "📝 Verifying OCR packages..." && \
    python -c "import pytesseract, easyocr; print('✅ OCR packages verified')" || \
    echo "⚠️  OCR packages not available"

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
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    API_HOST=0.0.0.0 \
    API_PORT=8001

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8001/healthz || exit 1

# Run the application
CMD ["python", "startup.py"]
