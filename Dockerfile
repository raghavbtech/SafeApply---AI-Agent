# ==============================================================================
# SafeApply Production Backend Dockerfile
# Optimized for Azure Container Apps / Azure App Service (Cost-Conscious)
# ==============================================================================

FROM python:3.11-slim-bookworm AS runner

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000 \
    SAFEAPPLY_ENV=production \
    SAFEAPPLY_UPLOADS_DIR=/app/uploads

WORKDIR /app

# Install minimal OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Create non-root user and group
RUN groupadd -g 1001 safeapply && \
    useradd -u 1001 -g safeapply -s /bin/bash -m safeapply

# Create uploads directory and set permissions
RUN mkdir -p /app/uploads && \
    chown -R safeapply:safeapply /app

# Copy application source code and ML models
COPY --chown=safeapply:safeapply backend/ /app/backend/
COPY --chown=safeapply:safeapply models/ /app/models/
COPY --chown=safeapply:safeapply *.py /app/
COPY --chown=safeapply:safeapply scam_patterns.json /app/

# Switch to non-root user
USER safeapply

# Health check against liveness endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/health/live || exit 1

EXPOSE 8000

# Start production server without --reload
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2 --timeout-keep-alive 65"]
