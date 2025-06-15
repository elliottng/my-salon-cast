# MySalonCast

Convert PDF documents and web content into conversational audio podcasts using AI. Features OAuth 2.0 authentication, cloud deployment, and seamless integration with Claude.ai.

## 🚀 Quick Start

### Quick API Test
**Test the deployed service:**
```bash
# Check if service is running
curl https://YOUR_SERVICE_URL/health

# Generate a simple podcast (example)
curl -X POST https://YOUR_SERVICE_URL/generate-podcast \
  -H "Content-Type: application/json" \
  -d '{"content": "Your content here", "personas": ["Host", "Expert"]}'
```

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

MySalonCast provides a **FastAPI REST API server** for podcast generation:

### Core Components
- **FastAPI Server** (`app/main.py`): HTTP API for podcast generation
- **Podcast Generation Pipeline**: Multi-step AI-powered audio creation
- **Google Cloud Integration**: Gemini LLM for content generation
- **Local SQLite Database**: Simple data persistence

```
Web/Mobile/CLI ─── HTTP/REST ─── FastAPI Server ─── Podcast Pipeline
                                        │
                                   Core Services:
                                   ├── Google Gemini LLM
                                   ├── Audio Processing (ffmpeg)
                                   └── Local SQLite Database
```

### Local Development

**REST API Server:**
```bash
uv run python -m uvicorn app.main:app --reload
# Available at: http://localhost:8000
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

## 🚀 Google Cloud Deployment

### Prerequisites
1. **Google Cloud Project** with billing enabled
2. **APIs enabled**: Cloud Run, Cloud Build, Container Registry
3. **Environment Variables**: Configured in `.env` file

### Step 1: Configure Environment Variables
```bash
# Copy the template and configure your API keys
cp .env.template .env

# Edit .env with your actual values
# Required:
#   GEMINI_API_KEY=your-actual-gemini-api-key
# Optional:
#   FIRECRAWL_API_KEY=your-firecrawl-key
#   FIRECRAWL_ENABLED=true
```

### Step 2: Deploy Using Helper Script (Recommended)
```bash
# Deploy (automatically loads .env file)
./scripts/deploy.sh
```

### Step 3: Manual Deployment (Alternative)
```bash
# Load environment variables manually
source .env

# Deploy with Cloud Build
gcloud builds submit --config cloudbuild.yaml \
  --machine-type=e2-highcpu-8 \
  --substitutions=_GEMINI_API_KEY="$GEMINI_API_KEY",_FIRECRAWL_API_KEY="$FIRECRAWL_API_KEY",_FIRECRAWL_ENABLED="$FIRECRAWL_ENABLED"
```

### Step 4: Verify Deployment
```bash
# Get service URL
gcloud run services describe mysaloncast-api --region=us-west1 --format='value(status.url)'

# Test health endpoint
curl https://YOUR_SERVICE_URL/health
```

**📖 Deployment Files:** 
- `Dockerfile` - Unified container for REST API
- `cloudbuild.yaml` - Streamlined build pipeline with environment variable support
- `scripts/deploy.sh` - Automated deployment helper script
- `.env.template` - Environment variable template
- `terraform/simple.tf` - Minimal infrastructure setup

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

## 🌐 API Endpoints

After deployment, your REST API will be available at:
- **Service URL**: `https://mysaloncast-api-[hash].us-west1.run.app`

### Key Endpoints
- `GET /health` - Health check
- `POST /generate-podcast` - Generate podcast from content
- `GET /status/{task_id}` - Check generation status
- `GET /audio/{task_id}` - Stream generated audio

## 🔐 Security Features

- Container security with non-root user
- Environment variable based configuration
- Google Cloud IAM integration
- Public API access (suitable for prototype)
- Secure API key management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Follow the local development setup instructions above
4. Add tests and ensure they pass: `uv run pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.