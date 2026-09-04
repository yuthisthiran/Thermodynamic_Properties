# ChemEng Thermodynamic API — Dockerfile
# ============================================================
# Multi-stage build for a minimal production image
# ============================================================

# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies (needed for CoolProp compilation if wheel unavailable)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --prefix=/install -r requirements.txt


# ---- Production stage ----
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed packages from build stage
COPY --from=builder /install /usr/local

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd --create-home --no-log-init appuser && chown -R appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Production command: 4 uvicorn workers via gunicorn
CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
