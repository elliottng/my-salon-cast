# MySalonCast

A sophisticated web application and **Model Context Protocol (MCP) server** that converts PDF documents and web links into engaging, conversational audio podcasts. Features OAuth 2.0 authentication, cloud deployment, and seamless integration with Claude.ai.

## 🚀 Quick Start

### For Claude.ai Users (Recommended)
**No setup required!** Connect directly to our production server:
1. Go to [Claude.ai Settings > Integrations](https://claude.ai/settings/integrations)
2. Click "Add custom integration" 
3. Enter: `https://mcp-server-production-644248751086.us-west1.run.app`
4. Start chatting: *"Create a podcast from this URL with Einstein and Marie Curie"*

### Available Through Claude
- **🎙️ Generate Podcasts**: "Create a podcast from this URL with Einstein and Marie Curie"
- **📊 Monitor Progress**: "What's the status of my podcast generation?"  
- **📁 Browse Episodes**: "Show me all my podcast episodes"
- **🔍 Access Content**: View outlines, research, and audio files
- **🏥 Health Monitoring**: "Check service health status"

## 🏗️ Developer Setup

### Prerequisites
- Python 3.11+
- Docker (for containerized development/deployment)
- Google Cloud SDK (for deployment)
- Git

### 1. Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd mysaloncast

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.staging.template .env
# Edit .env with your configuration (see Environment Variables section)

# Run the MCP server locally
python -m app.mcp_server
```

The server will be available at:
- **MCP Server**: `http://localhost:8000` (for Claude Desktop integration)
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)
- **Health Check**: `http://localhost:8000/health`

### 2. Docker Development

```bash
# Build the Docker image
docker build -t mysaloncast .

# Run with environment variables
docker run -p 8000:8000 \
  -e GEMINI_API_KEY=your_key_here \
  -e PROJECT_ID=your_project_id \
  -e ENVIRONMENT=local \
  mysaloncast
```

## 📦 Environment Variables

Create a `.env` file with the following variables:

### Required Variables
```env
# Core Configuration
ENVIRONMENT=local                    # local|staging|production
PROJECT_ID=my-salon-cast            # Your GCP project ID
GEMINI_API_KEY=your_gemini_api_key  # Required for podcast generation

# Server Configuration
PORT=8000
HOST=0.0.0.0
```

### Optional Variables
```env
# Cloud Storage (if using GCS)
AUDIO_BUCKET=your-audio-bucket
DATABASE_BUCKET=your-database-bucket

# OAuth Configuration (for production deployment)
CLAUDE_CLIENT_SECRET=your_claude_secret
WEBAPP_CLIENT_SECRET=your_webapp_secret

# Application Settings
MAX_CONCURRENT_GENERATIONS=2
AUDIO_CLEANUP_POLICY=auto_after_hours
AUDIO_CLEANUP_HOURS=24
```

## 🚀 Deployment

### Staging Deployment

```bash
# Set required environment variables
export GEMINI_API_KEY=your_gemini_api_key
export CLAUDE_CLIENT_SECRET=your_claude_secret  
export WEBAPP_CLIENT_SECRET=your_webapp_secret

# Deploy to staging
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_ENV=staging,_GEMINI_API_KEY="$GEMINI_API_KEY",_CLAUDE_CLIENT_SECRET="$CLAUDE_CLIENT_SECRET",_WEBAPP_CLIENT_SECRET="$WEBAPP_CLIENT_SECRET"
```

**Staging URL**: https://mcp-server-staging-644248751086.us-west1.run.app

### Production Deployment

```bash
# Deploy to production (same command with _ENV=production)
gcloud builds submit --config cloudbuild.yaml \
  --substitutions=_ENV=production,_GEMINI_API_KEY="$GEMINI_API_KEY",_CLAUDE_CLIENT_SECRET="$CLAUDE_CLIENT_SECRET",_WEBAPP_CLIENT_SECRET="$WEBAPP_CLIENT_SECRET"
```

**Production URL**: https://mcp-server-production-644248751086.us-west1.run.app

### Cloud Build Configuration

The deployment pipeline (`cloudbuild.yaml`) automatically:
1. **Builds** Docker image with all dependencies
2. **Pushes** to Google Container Registry
3. **Deploys** to Cloud Run with proper configuration
4. **Runs** health checks to verify deployment
5. **Configures** OAuth 2.0 authentication and CORS

### Deployment Requirements

Ensure you have:
- Google Cloud Project with Cloud Run API enabled
- Service account with Cloud Run Admin permissions
- Container Registry write access
- Environment variables properly set

## 🏗️ Project Architecture

```
mysaloncast/
├── app/                          # Main application code
│   ├── mcp_server.py            # MCP server entry point
│   ├── podcast_workflow.py     # Core podcast generation logic
│   ├── oauth_*.py              # OAuth 2.0 authentication
│   ├── tts_service.py          # Text-to-speech integration
│   ├── llm_service.py          # LLM integration (Gemini)
│   └── production_config.py    # Environment-aware configuration
├── tests/                       # Test suite
├── scripts/                     # Utility scripts
├── terraform/                   # Infrastructure as code
├── Dockerfile                   # Container configuration
├── cloudbuild.yaml             # CI/CD pipeline
├── requirements.txt            # Python dependencies
└── .env.*.template            # Environment templates
```

### Key Components

- **FastMCP Server**: Powers Claude integration with OAuth 2.0
- **Podcast Workflow**: Multi-step podcast generation pipeline
- **TTS Service**: Google Cloud Text-to-Speech with thread pool optimization
- **LLM Service**: Google Gemini integration with timeout handling
- **OAuth 2.0**: RFC-compliant authentication for Claude.ai integration
- **Cloud Storage**: GCS integration for audio and content storage

## 🧪 Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/test_llm_service.py
pytest tests/test_generate_text_async.py

# Run integration tests
python test_mcp_integration.py
```

## 📚 Documentation

- **[MCP Setup Guide](./MCP_SETUP_GUIDE.md)**: Complete Claude Desktop integration
- **[OAuth Deployment](./OAUTH_DEPLOYMENT_SUMMARY.md)**: Authentication setup
- **[CORS Configuration](./CORS_CONFIGURATION.md)**: Cross-origin setup
- **[API Documentation v1](./api_documentation_v1.md)**: REST API reference

## 🔧 Development Tools

### Health Monitoring
```bash
curl http://localhost:8000/health
```

### OAuth Testing
```bash
# Get OAuth discovery metadata
curl http://localhost:8000/.well-known/oauth-authorization-server

# Test authentication flow
bash scripts/get_token.sh
```

### MCP Testing
```bash
# Test MCP integration end-to-end
python test_mcp_integration.py
```

## 🌐 Production URLs

- **Production MCP Server**: https://mcp-server-production-644248751086.us-west1.run.app
- **Staging MCP Server**: https://mcp-server-staging-644248751086.us-west1.run.app

Both environments support:
- MCP connections from Claude.ai and Claude Desktop
- OAuth 2.0 authentication with auto-approval for Claude.ai
- Real-time health monitoring and status reporting
- Comprehensive CORS support for browser integration

## 🔐 Security Features

- **OAuth 2.0 Compliance**: RFC 8414/7591 with PKCE support
- **Domain-based Authentication**: Auto-approval for trusted Claude.ai domains
- **Container Security**: Non-root user, minimal attack surface
- **Environment Isolation**: Separate staging/production configurations
- **Token Management**: Secure access token generation with proper expiration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the local development setup above
4. Make your changes and add tests
5. Run the test suite: `pytest`
6. Submit a pull request

For major changes, please open an issue first to discuss the proposed changes.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
