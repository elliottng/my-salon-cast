#!/bin/bash
# Script to test CORS configuration locally before deployment

set -e  # Exit on any error

# Kill any existing MCP server processes
echo "Stopping any existing MCP server processes..."
pkill -f "python.*mcp_server.py" || echo "No existing MCP server processes found"

# Set environment variables for CORS testing
export ALLOWED_ORIGINS="https://claude.ai,https://inspect.mcp.garden"
export ENVIRONMENT="local"

echo "Starting MCP server with updated CORS settings..."
echo "ALLOWED_ORIGINS=$ALLOWED_ORIGINS"

# Activate virtual environment and start server
source venv/bin/activate
python -m app.mcp_server

# Note: This script will keep running until you press Ctrl+C to stop the server
