# MySalonCast MCP Server - Production Dockerfile
# Optimized for Cloud Run deployment with health checks and graceful shutdown

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and GCP services
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY secrets/ ./secrets/

# Create necessary directories
RUN mkdir -p /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files

# Set environment variables for production
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Health check for Cloud Run
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Expose port
EXPOSE 8000

# Create a non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser
RUN chown -R appuser:appuser /app /tmp/mysaloncast_audio_files /tmp/mysaloncast_text_files
USER appuser

# Start the MCP server with proper signal handling
CMD ["python", "-m", "app.mcp_server"]
