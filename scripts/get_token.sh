#!/bin/bash
# Quick script to get a fresh Bearer token for MCP Inspector

echo "🎫 Generating fresh Bearer token for MCP Inspector..."
echo "Server: https://mcp-server-staging-644248751086.us-west1.run.app"
echo "------------------------------------------------------------"

# Activate venv and run the OAuth test, extract just the token
source venv/bin/activate && python test_staging_oauth.py 2>/dev/null | grep "Access Token:" | cut -d' ' -f3

echo ""
echo "💡 Use this token in MCP Inspector:"
echo "   Header: Authorization"
echo "   Value:  Bearer <token_above>"
echo "   URL:    https://mcp-server-staging-644248751086.us-west1.run.app"
