# Real Estate CRM - Cloud Deployment
# ====================================
# This Dockerfile packages the app for deployment on any cloud platform.
# Supports both SQLite (default) and PostgreSQL (cloud) databases.

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set work directory
WORKDIR /app

# Install system dependencies for PostgreSQL and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for Docker layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire application
COPY backend/ ./backend/
COPY frontend/ ./frontend/
COPY crm_core/ ./crm_core/
COPY CRM/ ./CRM/
COPY migrations/ ./migrations/
COPY company_logo/ ./company_logo/

# Copy top-level Python files that are imported
COPY professional_crm.py ./
COPY config.py ./
COPY qt_crm_premium_style.py ./

# Create necessary directories for data persistence
RUN mkdir -p data/backups data/outputs logs

# Set default database path for SQLite (can be overridden by DATABASE_URL)
ENV CRM_DB_PATH=/app/data/real_estate_crm.db

# Expose the port the app runs on
EXPOSE 6090

# Health check - works for both SQLite and PostgreSQL
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:6090/api/health')" || exit 1

# Run the application
# DATABASE_URL env var (set by Render/Railway/etc.) takes precedence over SQLite
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "6090"]
