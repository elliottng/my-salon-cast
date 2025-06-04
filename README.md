# MySalonCast

A web application for converting PDF documents and web links into engaging, conversational audio podcasts.

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the development server:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## Project Structure

- `app/` - Main application code
- `services/` - Business logic and external service integrations
- `utils/` - Helper functions and utilities
- `temp_files/` - Temporary storage for uploaded files and generated content
- `tests/` - Test files

## 🎙️ MCP Server Integration

MySalonCast includes a **Model Context Protocol (MCP) server** that allows Claude Desktop to generate podcasts directly through natural conversation.

### 🌐 Use with Claude.ai (Recommended)
**No setup required!** Connect directly to our deployed server:
1. Go to [Claude.ai Settings > Integrations](https://claude.ai/settings/integrations)
2. Click "Add custom integration" 
3. Enter: `https://mcp-server-production-644248751086.us-west1.run.app`
4. Start chatting: *"Create a podcast from this URL with Einstein and Marie Curie"*

### 💻 Use with Claude Desktop (Development)
For local development and customization:
1. Start the MCP server: `python -m app.mcp_server`
2. Configure Claude Desktop with the MCP connection
3. Generate podcasts by chatting with Claude!

**📖 Full Setup Guide**: See [MCP_SETUP_GUIDE.md](./MCP_SETUP_GUIDE.md) for complete instructions.

### Available Through Claude
- **🎙️ Generate Podcasts**: "Create a podcast from this URL with Einstein and Marie Curie"
- **📊 Monitor Progress**: "What's the status of my podcast generation?"  
- **📁 Browse Episodes**: "Show me all my podcast episodes"
- **🔍 Access Content**: View outlines, research, and audio files

## Environment Variables

Create a `.env` file with the following variables:
```
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-file.json
# Required for podcast generation
GEMINI_API_KEY=your-gemini-api-key
PROJECT_ID=your-gcp-project-id
ENVIRONMENT=local

# Optional for cloud storage
GOOGLE_CLOUD_STORAGE_BUCKET=your-bucket-name
```

## Development

The project uses FastAPI for the backend API and follows RESTful conventions.

## API Documentation

API documentation is automatically generated and available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- **MCP Server**: `http://localhost:8000` (for Claude Desktop integration)

## 🚀 Deployment

The application is deployed on Google Cloud Run:
- **Staging**: https://mcp-server-staging-644248751086.us-west1.run.app
- **Production**: https://mcp-server-production-644248751086.us-west1.run.app

Both environments support MCP connections from Claude Desktop.
