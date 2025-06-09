# MySalonCast

Convert PDF documents and web content into conversational audio podcasts using AI. Features OAuth 2.0 authentication, cloud deployment, and seamless integration with Claude.ai.

## 🚀 Quick Start

### For Claude.ai Users (Recommended)
**No setup required!** Connect directly to our production server:
1. Go to [Claude.ai Settings > Integrations](https://claude.ai/settings/integrations)
2. Click "Add custom integration"
3. Enter: `https://mcp-server-production-644248751086.us-west1.run.app`
4. Start chatting: *"Create a podcast from this URL with Einstein and Marie Curie"*

### Local Development

Choose your preferred method:

**Option 1: uv (Recommended)**
```bash
git clone <repo-url>
cd my-salon-cast
uv sync
# Configure your .env file with required values
uv run python app/mcp_server.py
```

**Option 2: Docker**
```bash
git clone <repo-url>
cd my-salon-cast
# Configure your .env file with required values
docker build -t my-salon-cast .
docker run -p 8000:8000 --env-file .env my-salon-cast
```

The server will be available at `http://localhost:8000`

## 📋 Requirements

- Python 3.11+
- uv or Docker
- Google Cloud SDK (for deployment)
- **Environment Variables**: Configure your environment variables:
  - `GEMINI_API_KEY` (required for podcast generation)
  - `PROJECT_ID` (your GCP project ID)
  - See `.env` file for current configuration

## 🏗️ Architecture

MySalonCast uses a **dual-server architecture** to provide flexible integration options:

### Server Architecture
- **MCP Server** (`app/mcp_server.py`): Primary interface for Claude/AI clients via Model Context Protocol
- **REST API** (`app/main.py`): Minimal HTTP API (4 endpoints) for web/mobile integrations
- **Shared Services**: Both servers share the same podcast generation pipeline and configuration

### Core Components
- **FastMCP Server**: Powers Claude integration with OAuth 2.0
- **Podcast Generation Pipeline**: Multi-step AI-powered audio creation
- **Google Cloud Integration**: TTS, Gemini LLM, and Cloud Storage
- **Unified Configuration**: Single config system for both servers

```
Claude.ai ──── MCP Protocol ──── MCP Server ──── Podcast Pipeline
                                      │               │
Web/Mobile ─── HTTP/REST ────── REST API ─────────────┘
                                      │
                                 Shared Services:
                                 ├── Google Cloud TTS
                                 ├── Google Gemini LLM
                                 ├── Cloud Storage (GCS)
                                 └── Local SQLite Database
```

### Local Development

**MCP Server (Primary - for Claude integration):**
```bash
uv run python app/mcp_server.py
# Available at: http://localhost:8000
```

**REST API (Secondary - for other integrations):**
```bash
uv run python -m uvicorn app.main:app --reload
# Available at: http://localhost:8000
```

**Both servers simultaneously (different ports):**
```bash
# Terminal 1: MCP Server
PORT=8001 uv run python app/mcp_server.py

# Terminal 2: REST API  
PORT=8002 uv run python -m uvicorn app.main:app --reload --port 8002
```

## 🚀 Deployment

### Staging
```bash
export GEMINI_API_KEY=your_key
export CLAUDE_CLIENT_SECRET=your_secret
export WEBAPP_CLIENT_SECRET=your_secret

gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_ENV=staging,_GEMINI_API_KEY="$GEMINI_API_KEY",_CLAUDE_CLIENT_SECRET="$CLAUDE_CLIENT_SECRET",_WEBAPP_CLIENT_SECRET="$WEBAPP_CLIENT_SECRET"
```

### Production
```bash
# Same command with _ENV=production
```

**📖 Detailed Deployment**: See [OAUTH_DEPLOYMENT_SUMMARY.md](./archive/OAUTH_DEPLOYMENT_SUMMARY.md) for complete deployment guide.

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/test_llm_service.py
uv run pytest tests/test_generate_text_async.py
```

**📖 Testing Guide**: See [TESTING.md](./TESTING.md) for comprehensive testing information.

## 📚 Documentation

- **[Architecture](./ARCHITECTURE.md)** - Technical architecture and system design
- **[Authentication](./AUTHENTICATION.md)** - Authentication setup and configuration
- **[Testing](./TESTING.md)** - Test suite documentation

### Archived Documentation
- **[API Documentation](./archive/api_documentation_v1.md)** - REST API reference
- **[MCP Setup Guide](./archive/MCP_SETUP_GUIDE.md)** - Claude Desktop integration
- **[OAuth Deployment](./archive/OAUTH_DEPLOYMENT_SUMMARY.md)** - Authentication and deployment
- **[CORS Configuration](./archive/CORS_CONFIGURATION.md)** - Cross-origin setup
- **[Production Readiness](./archive/production_readiness_checklist.md)** - Production deployment checklist

## 🌐 Production URLs

- **Production**: https://mcp-server-production-644248751086.us-west1.run.app
- **Staging**: https://mcp-server-staging-644248751086.us-west1.run.app

Both environments support MCP connections from Claude.ai, OAuth 2.0 authentication, and comprehensive health monitoring.

## 🔐 Security Features

- OAuth 2.0 compliance with PKCE support
- Domain-based authentication with auto-approval for Claude.ai
- Container security with non-root user
- Environment isolation for staging/production
- Secure token management with proper expiration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the local development setup instructions above
4. Add tests and ensure they pass: `uv run pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.