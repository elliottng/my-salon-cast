# MySalonCast MCP Quick Reference

## Available MCP Tools

### 🎙️ Core Podcast Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `hello` | Test MCP connection | "Test the MySalonCast connection" |
| `generate_podcast_async` | Start podcast generation from URL/PDF | "Generate a podcast from https://example.com with Einstein and Curie" |
| ~~`generate_podcast_async_pydantic`~~ | ~~Start podcast with Pydantic model (deprecated)~~ | ~~Advanced programmatic usage~~ |
| `get_task_status` | Check generation progress | "What's the status of task task_123?" |

### 🧹 Management Tools

| Tool | Description | Example Usage |
|------|-------------|---------------|
| `cleanup_task_files` | Clean up task temporary files | "Clean up files for task task_123" |
| `configure_cleanup_policy` | Set file cleanup policies | "Set cleanup policy to keep files for 7 days" |
| `get_service_health` | Check system health | "Check MySalonCast system status" |
| `test_tts_service` | Test text-to-speech service | "Test the TTS service" |

## Available MCP Resources

### 📁 Content Resources

| Resource | Description | Access Pattern |
|----------|-------------|----------------|
| `podcast_episodes` | List all episodes | "Show me all my podcast episodes" |
| `persona_research/{person_id}` | Individual persona research | "Show research for Einstein" |
| `podcast_outline/{task_id}` | Episode outlines | "Show outline for task task_123" |
| `audio_files/{episode_id}` | Generated audio files | "Get audio for episode ep_456" |
| `system_logs` | Recent system activity | "Show recent system logs" |
| `capacity_metrics` | System capacity info | "Check system capacity" |

## Available MCP Prompts

### 📝 Generation Prompts

| Prompt | Description | Usage |
|--------|-------------|-------|
| `create_podcast_from_url` | URL podcast template | Pre-built prompt for URL input |
| `create_podcast_from_pdf` | PDF podcast template | Pre-built prompt for PDF input |
| `analyze_podcast_episode` | Episode analysis template | Analyze generated content |
| `suggest_improvements` | Improvement suggestions | Get content enhancement ideas |

## Common Claude Desktop Commands

### Generate a Podcast
```
Create a podcast from this article: https://example.com/article

Use these personas:
- Albert Einstein (theoretical physics perspective)
- Marie Curie (experimental science perspective)

Make it a medium-length episode and focus on the practical applications.
```

### Check Progress
```
What's the status of my podcast generation? The task ID is task_abc123.
```

### Browse Content
```
Show me all my podcast episodes from the last week.
```

### System Health
```
Check the MySalonCast system status and capacity.
```

### Access Specific Content
```
Show me the outline for task task_abc123 and the research files for Einstein.
```

## Connection Setup (Claude Desktop)

### 1. Claude.ai Website (Easiest) ⭐

**For Claude Pro/Max Users:**
1. Go to [Settings > Integrations](https://claude.ai/settings/integrations) in Claude.ai
2. Click "Add custom integration"
3. Enter server URL: `https://mcp-server-production-644248751086.us-west1.run.app`
4. Click "Add" to finish setup
5. Enable tools in any chat via the Search and tools menu (🔍 icon)

**For Claude Enterprise/Team (Owners only):**
1. Go to [Settings > Integrations](https://claude.ai/settings/integrations)
2. Toggle to "Organization integrations"
3. Click "Add custom integration"
4. Enter server URL: `https://mcp-server-production-644248751086.us-west1.run.app`
5. Click "Add" to configure for organization

### 2. Claude Desktop (Local Development)

```json
{
  "mcpServers": {
    "mysaloncast": {
      "command": "python",
      "args": ["-m", "uvicorn", "app.mcp_server:mcp.app", "--host", "localhost", "--port", "8000"],
      "cwd": "/path/to/mysaloncast"
    }
  }
}
```

### 3. Production Environment

```json
{
  "mcpServers": {
    "mysaloncast-prod": {
      "command": "curl",
      "args": ["-X", "POST", "https://mcp-server-production-644248751086.us-west1.run.app/mcp"]
    }
  }
}
```

## Claude.ai Usage Examples

### Enable MySalonCast in Claude.ai
```
1. Start a new conversation
2. Click the Search and tools menu (🔍)
3. Find "MySalonCast" and enable desired tools:
   ✅ Generate Podcast Async
   ✅ Get Task Status  
   ✅ Get Service Health
   ✅ Hello (for testing)
```

### Ready-to-Use Phrases for Claude.ai
```
"Create a podcast from https://example.com/article using Einstein and Curie as personas"

"Check the status of my podcast generation task_abc123"

"Show me all my podcast episodes"

"Test the MySalonCast connection"

"Generate a medium-length podcast about AI from this PDF: [upload file]"
```

## Troubleshooting

### Quick Checks
```bash
# Test server
curl http://localhost:8000/health

# Check logs
tail -f app/logs/app.log

# Verify MCP tools
python -c "from app.mcp_server import mcp; print(f'Tools: {len(mcp.tools)}')"
```

### Environment Variables
```bash
export GEMINI_API_KEY="your-key"
export PROJECT_ID="your-project"
export ENVIRONMENT="local"
```

For complete setup instructions, see [MCP_SETUP_GUIDE.md](./MCP_SETUP_GUIDE.md).
