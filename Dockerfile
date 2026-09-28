# Football Betting Assistant - FastAPI Backend
# Supports Docker deployment on Render, CloudBase, and other platforms

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Expose port (default 8080, override with PORT env var)
EXPOSE 8080

# Health check
# HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    # CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')" || exit 1

# Run with uvicorn (production config)
# Render sets PORT env var automatically; default to 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
