# MySalonCast MCP Server Authentication Guide

This document explains the authentication methods supported by MySalonCast MCP Server and how to configure them for different use cases.

## Overview

MySalonCast MCP Server supports **hybrid authentication** with two methods:
- **OAuth 2.0**: For interactive clients (Claude.ai, web apps, mobile apps)
- **Bearer Token (API Key)**: For server-to-server integrations and development tools

## Authentication Methods

### 1. OAuth 2.0 (Recommended for Interactive Clients)

OAuth 2.0 provides secure, user-consented access with proper scope limitations.

#### Supported Flows
- **Authorization Code Flow**: For web applications and mobile apps
- **Client Credentials Flow**: For server-to-server applications

#### Pre-configured Clients
- **Claude.ai**: Auto-approved for seamless integration
- **MySalonCast Web App**: Requires user consent

#### OAuth Endpoints
```
Discovery: /.well-known/oauth-authorization-server
Authorize: /auth/authorize
Token: /auth/token
Introspection: /auth/introspect
Registration: /auth/register (dynamic client registration)
```

#### Example OAuth Flow (Claude.ai)
1. Client redirects to authorization endpoint
2. Server auto-approves Claude.ai clients
3. Client exchanges code for access token
4. Client uses access token in Bearer header

### 2. Bearer Token (API Key)

Simple API key authentication for direct server-to-server access.

#### Use Cases
- CI/CD pipelines
- Internal services
- Development tools
- MCP Inspector and debugging tools

#### Configuration

Set API keys via environment variables:

```bash
# Production API key
MYSALONCAST_API_KEY=your-secure-api-key-here

# Development API key (auto-set in local env)
MYSALONCAST_DEV_API_KEY=dev-key-12345

# CI/CD API key
MYSALONCAST_CI_API_KEY=ci-pipeline-key
```

#### Usage

Include the API key in the Authorization header:

```http
Authorization: Bearer your-api-key-here
```

## Environment-Based Configuration

### Local Development
```bash
ENVIRONMENT=local
```
- **Authentication**: Disabled (for easy development)
- **CORS**: Allows all origins
- **API Key**: Auto-generated dev key available

### Staging/Production
```bash
ENVIRONMENT=staging  # or production
PROJECT_ID=your-gcp-project
```
- **Authentication**: Required (OAuth or API key)
- **CORS**: Restricted to configured origins
- **API Keys**: Must be explicitly configured

## Client Configuration Examples

### MCP Inspector / Debugging Tools
For local testing with MCP Inspector:

1. **Local Development** (easiest):
   ```bash
   ENVIRONMENT=local
   ```
   Connect to: `http://localhost:8000/sse` (no auth required)

2. **With API Key**:
   ```bash
   MYSALONCAST_DEV_API_KEY=your-dev-key
   ```
   Header: `Authorization: Bearer your-dev-key`

### Claude.ai Integration
Claude.ai uses OAuth 2.0 with auto-approval:

```json
{
  "client_id": "claude-ai",
  "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
  "auto_approve": true
}
```

### Web Application
MySalonCast web app requires user consent:

```json
{
  "client_id": "mysaloncast-webapp", 
  "redirect_uri": "https://mysaloncast.com/oauth/callback",
  "auto_approve": false
}
```

### CI/CD Pipeline
Use API key for automated testing:

```yaml
# GitHub Actions example
env:
  MYSALONCAST_CI_API_KEY: ${{ secrets.MYSALONCAST_API_KEY }}

steps:
  - name: Test MCP Integration
    run: |
      curl -H "Authorization: Bearer $MYSALONCAST_CI_API_KEY" \
           http://mysaloncast-server/tools
```

## Security Best Practices

### API Key Management
- ✅ Use different keys for different environments
- ✅ Rotate keys regularly
- ✅ Store keys in secure environment variables
- ❌ Never commit keys to version control
- ❌ Don't share production keys

### OAuth 2.0 Security
- ✅ Use PKCE for public clients
- ✅ Validate redirect URIs strictly
- ✅ Use short-lived tokens (1 hour default)
- ✅ Implement proper scope validation
- ❌ Don't store client secrets in frontend code

### Production Deployment
- ✅ Set `ENVIRONMENT=production`
- ✅ Configure proper CORS origins
- ✅ Use HTTPS for all endpoints
- ✅ Monitor authentication failures
- ❌ Don't disable authentication in production

## Troubleshooting

### Common Issues

**"401 Unauthorized" in MCP Inspector**
- Check `ENVIRONMENT` is set to `local` for development
- Or provide valid API key in Authorization header

**"invalid_client" in OAuth flow**
- Verify client is registered (check OAuth configuration)
- For Claude.ai, ensure redirect URI contains "claude.ai"

**"invalid_scope" error**
- Check requested scopes are supported: `mcp.read`, `mcp.write`, `admin`
- API keys automatically get all scopes

**Connection timeout in production**
- Verify HTTPS is used for all OAuth endpoints
- Check firewall allows HTTPS traffic on port 443

### Debug Commands

Check server health:
```bash
curl http://localhost:8000/health
```

View OAuth discovery:
```bash
curl http://localhost:8000/.well-known/oauth-authorization-server
```

Test API key authentication:
```bash
curl -H "Authorization: Bearer dev-key-12345" \
     http://localhost:8000/sse
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `ENVIRONMENT` | Deployment environment | `local` | No |
| `MYSALONCAST_API_KEY` | Production API key | None | Production |
| `MYSALONCAST_DEV_API_KEY` | Development API key | `dev-key-12345` | Local |
| `MYSALONCAST_CI_API_KEY` | CI/CD API key | None | CI/CD |
| `CLAUDE_CLIENT_SECRET` | Claude.ai OAuth secret | Auto-generated | Production |
| `WEBAPP_CLIENT_SECRET` | Web app OAuth secret | Auto-generated | Production |

## Integration Examples

### Python Client
```python
import httpx

# Using API key
headers = {"Authorization": "Bearer your-api-key"}
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/tools",
        headers=headers
    )
```

### JavaScript/Node.js
```javascript
// Using OAuth token
const headers = {
    'Authorization': `Bearer ${oauthToken}`,
    'Content-Type': 'application/json'
};

const response = await fetch('http://localhost:8000/sse', {
    headers: headers
});
```

### cURL Examples
```bash
# Get available tools
curl -H "Authorization: Bearer dev-key-12345" \
     http://localhost:8000/tools

# Start podcast generation
curl -X POST \
     -H "Authorization: Bearer dev-key-12345" \
     -H "Content-Type: application/json" \
     -d '{"source_urls": ["https://example.com"], "prominent_persons": ["Einstein"]}' \
     http://localhost:8000/tools/generate_podcast_async
```

## Support

For authentication issues:
1. Check this documentation
2. Verify environment variables
3. Test with provided debug commands
4. Check server logs for authentication errors

The hybrid authentication system ensures compatibility with both interactive OAuth clients (like Claude.ai) and direct API integrations while maintaining security best practices for each use case.