# MySalonCast API - Unified Dockerfile
# Optimized for Cloud Run deployment with FastAPI

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and health checks
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Environment variables for build optimization
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency files first for better Docker layer caching
COPY uv.lock pyproject.toml ./

# Install dependencies (no cache mounts for Cloud Build compatibility)
RUN uv sync --locked --no-install-project --no-editable

# Copy application code
COPY . .

# Install the project
RUN uv sync --locked --no-editable

# Create necessary directories for temporary files
RUN mkdir -p /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files

# Runtime environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PATH="/app/.venv/bin:$PATH"

# Create non-root user for security
RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /app /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files
USER app

# Health check for Cloud Run monitoring
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Start FastAPI server by default
# Can be overridden at runtime: docker run ... python -m app.mcp_server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
