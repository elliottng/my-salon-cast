#!/bin/bash
# Quick script to get a fresh Bearer token for MCP Inspector

echo "🎫 Generating fresh Bearer token for MCP Inspector..."
echo "Server: https://mcp-server-staging-ttvealhkuq-uw.a.run.app"
echo "------------------------------------------------------------"

# Run the OAuth test and extract just the token
python test_staging_oauth.py 2>/dev/null | grep "Access Token:" | cut -d' ' -f3

echo ""
echo "💡 Use this token in MCP Inspector:"
echo "   Header: Authorization"
echo "   Value:  Bearer <token_above>"
echo "   URL:    https://mcp-server-staging-ttvealhkuq-uw.a.run.app"
