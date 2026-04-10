# Multi-stage build for smaller image size
FROM python:3.11-slim AS builder

# Install system dependencies for building
# Retry logic for network issues (Debian repos can be temporarily unavailable)
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends build-essential && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 5); \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies (globally, not --user)
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Final image
FROM python:3.11-slim

# Install runtime dependencies (for PDF processing)
# Retry logic for network issues
RUN set -eux; \
    for i in 1 2 3; do \
        apt-get update && \
        apt-get install -y --no-install-recommends poppler-utils && \
        break || \
        (echo "Attempt $i failed, retrying..." && sleep 5); \
    done && \
    rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder (global installs)
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data /app/uploads /app/qdrant_db && \
    chown -R appuser:appuser /app

# Set working directory
WORKDIR /app

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Expose Flask port
EXPOSE 5000

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    FLASK_APP=app.py \
    FLASK_ENV=production

# Health check (uses urllib instead of requests to avoid extra dependency)
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health', timeout=5)" || exit 1

# Run application
# For MVP: single container (web + email monitor in threads)
# For production: use Dockerfile.web + Dockerfile.worker with docker-compose.prod.yml
CMD ["python", "app.py"]
