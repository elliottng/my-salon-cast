# MySalonCast MCP Server - Production Dockerfile
# Modernized with uv for fast, reliable dependency management

FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and GCP services
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Enable bytecode compilation for faster startup
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install dependencies first (better Docker layer caching)
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-editable

# Copy the project into the image
COPY . /app

# Install the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Production stage
FROM python:3.11-slim AS production

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and GCP services
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy the virtual environment from builder stage
COPY --from=builder --chown=app:app /app/.venv /app/.venv

# Create necessary directories
RUN mkdir -p /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files

# Set environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PATH="/app/.venv/bin:$PATH"

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Create a non-root user for security
RUN groupadd -r app && useradd -r -g app app
RUN chown -R app:app /app /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files
USER app

# Start the MCP server directly (not through uv)
CMD ["python", "-m", "app.mcp_server"]