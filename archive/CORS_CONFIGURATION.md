# CORS Configuration for MySalonCast MCP Server

This document explains the CORS (Cross-Origin Resource Sharing) configuration for the MySalonCast MCP server and how it enables integration with Claude.ai and the MCP Inspector.

## Background

CORS is a security mechanism that restricts web pages from making requests to a different domain than the one that served the original page. For our MCP server to work with web-based clients like Claude.ai or the MCP Inspector, we need to explicitly allow these domains in our CORS configuration.

## Issue Identified

The OAuth authentication flow was working correctly, but the actual MCP connections from Claude.ai and the MCP Inspector were failing due to CORS restrictions. This is because:

1. OAuth token exchanges are server-to-server communications (not subject to CORS)
2. MCP connections are browser-to-server communications (subject to CORS)

Our default CORS configuration only allowed Google domains, which blocked Claude.ai and the MCP Inspector.

## Solution

We've updated the CORS configuration to explicitly allow requests from:
- `https://claude.ai` - For Claude.ai integration
- `https://inspect.mcp.garden` - For the hosted MCP Inspector

This is done by setting the `ALLOWED_ORIGINS` environment variable in our deployment environments.

## Implementation

The CORS configuration is managed through:

1. The `Config.cors_origins()` method in `app/config.py`, which checks for an `ALLOWED_ORIGINS` environment variable
2. The `CORSMiddleware` in `app/main.py`, which applies the CORS policy to all HTTP requests

## Testing

You can test the CORS configuration locally using the `test_cors_locally.sh` script, which:
1. Sets the `ALLOWED_ORIGINS` environment variable
2. Starts the MCP server with the updated CORS settings

## Deployment

The `deploy_cors_update.sh` script handles deploying the CORS configuration to:
1. Staging environment
2. Production environment

This script updates the `ALLOWED_ORIGINS` environment variable in the Cloud Run service configuration.

## Verification

After deployment, you can verify the CORS configuration by:
1. Using the hosted MCP Inspector at https://inspect.mcp.garden/
2. Testing the Claude.ai integration with your MCP server

## Troubleshooting

If you encounter CORS errors after deployment:
1. Check the Cloud Run logs for any CORS-related errors
2. Verify that the `ALLOWED_ORIGINS` environment variable is set correctly
3. Test with the browser developer tools to see the specific CORS error messages

## Future Considerations

If additional domains need to be allowed in the future, update the `ALLOWED_ORIGINS` environment variable with a comma-separated list of domains.
