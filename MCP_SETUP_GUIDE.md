# MySalonCast MCP Server Setup Guide

## Overview

MySalonCast provides a Model Context Protocol (MCP) server that allows Claude Desktop to generate salon-style podcasts directly through natural conversation. This guide shows you how to connect Claude Desktop to your MySalonCast MCP server.

## What is MCP?

The Model Context Protocol (MCP) allows Claude Desktop to connect to external servers and access custom tools and resources. With MySalonCast's MCP server, you can:

- **Generate Podcasts**: Convert URLs or PDFs into engaging audio conversations
- **Monitor Progress**: Track generation status in real-time  
- **Access Resources**: View podcast episodes, persona research, and outlines
- **Browse Content**: Explore generated content through Claude Desktop

## Quick Start

### Option 1: Claude.ai Website (Remote MCP)

The easiest way to use MySalonCast is through Claude.ai with our deployed Cloud Run services:

#### **For Claude Pro/Max Users:**
1. **Navigate to Integrations**: Go to [Settings > Integrations](https://claude.ai/settings/integrations) in Claude.ai
2. **Add Custom Integration**: Click "Add custom integration" at the bottom of the section
3. **Enter Server URL**: Use one of our deployed endpoints:
   - **Production**: `https://mcp-server-production-644248751086.us-west1.run.app`
   - **Staging**: `https://mcp-server-staging-644248751086.us-west1.run.app`
4. **Configure Integration**: Click "Add" to finish setup
5. **Enable in Chat**: Use the Search and tools menu in any chat to enable MySalonCast tools

#### **For Claude Enterprise/Team (Owners/Primary Owners):**
1. **Navigate to Organization Settings**: Go to [Settings > Integrations](https://claude.ai/settings/integrations)
2. **Switch to Organization View**: Toggle to "Organization integrations" at the top
3. **Add Integration**: Click "Add custom integration" in the Integrations section
4. **Enter Server URL**: Use our production endpoint: `https://mcp-server-production-644248751086.us-west1.run.app`
5. **Complete Setup**: Click "Add" to configure for your organization
6. **User Authentication**: Team members will individually authenticate as needed

**✅ Advantages of Claude.ai Integration:**
- No local setup required
- Always uses latest deployed version
- Works from any device with web browser
- Automatic updates when we deploy new features

### Option 2: Claude Desktop (Local Development)

For development and customization, you can run MySalonCast locally:

### 1. Start Your Local MCP Server

```bash
# In your MySalonCast project directory
source venv/bin/activate
python -m app.mcp_server
```

The server will start on `http://localhost:8000` and display:
```
INFO: MySalonCast MCP Server running on http://localhost:8000
INFO: Available tools: 8 tools, 6 resources, 4 prompts
```

### 2. Configure Claude Desktop

Add this configuration to your Claude Desktop MCP settings:

**File Location:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**
```json
{
  "mcpServers": {
    "mysaloncast": {
      "command": "python",
      "args": ["-m", "uvicorn", "app.mcp_server:mcp.app", "--host", "localhost", "--port", "8000"],
      "cwd": "/path/to/your/mysaloncast/project"
    }
  }
}
```

**Important**: Replace `/path/to/your/mysaloncast/project` with your actual project path.

### 3. Restart Claude Desktop

After saving the configuration, restart Claude Desktop. You should see "MySalonCast" appear in the MCP section.

## Using MySalonCast in Claude.ai

Once you've added the integration to Claude.ai:

### **Enable Tools in Chat**
1. Start a new conversation in Claude.ai
2. Click the **Search and tools** menu (🔍 icon)
3. Find "MySalonCast" in the integrations list
4. Enable the tools you want to use:
   - ✅ **Generate Podcast Async** - For creating podcasts
   - ✅ **Get Task Status** - For monitoring progress
   - ✅ **Get Service Health** - For system checks
   - ✅ **Hello** - For testing connection

### **Example Conversation**
```
User: I want to create a podcast from this research paper about quantum computing. 
Use Richard Feynman and Neil deGrasse Tyson as the personas, and make it a 
medium-length episode focusing on practical applications.

URL: https://arxiv.org/abs/2023.12345

Claude: I'll help you create a podcast from that quantum computing paper! Let me 
use MySalonCast to generate it with Feynman and Tyson as personas.

[Claude calls generate_podcast_async tool]

Great! I've started generating your podcast. Here's what's happening:

📋 **Task ID**: task_abc123
🎭 **Personas**: Richard Feynman, Neil deGrasse Tyson  
📏 **Length**: Medium (~15-20 minutes)
🔄 **Status**: Processing...

The system is now:
1. Extracting content from the research paper
2. Creating persona research for Feynman and Tyson
3. Generating a conversational outline
4. Creating the audio dialogue

Would you like me to check the progress?
```

### **Monitor Progress**
```
User: Yes, please check the status

Claude: [Calls get_task_status tool]

📊 **Status Update for task_abc123:**
- ✅ Content extraction: Complete
- ✅ Persona research: Complete  
- 🔄 Outline generation: In progress (75%)
- ⏳ Audio generation: Pending
- ⏳ Final assembly: Pending

Estimated completion: 3-5 minutes
```

### **Access Results**
```
User: Is it ready now?

Claude: [Calls get_task_status tool]

🎉 **Podcast Complete!**

Your quantum computing podcast with Feynman and Tyson is ready:

📎 **Audio File**: [Download Link]
📋 **Outline**: Available via resources
🔍 **Persona Research**: Detailed character profiles created
⏱️ **Duration**: 18:32
📊 **Quality**: High-quality TTS with natural conversation flow

Would you like me to show you the outline or help you create another episode?
```

## Available Tools & Usage

### 🎙️ Podcast Generation Tools

#### `generate_podcast_async`
Starts async podcast generation from a URL or PDF.

**Example Claude conversation:**
```
Generate a podcast about artificial intelligence from this article: https://example.com/ai-article

Use Einstein and Marie Curie as the personas, and make it a medium-length episode.
```

#### `get_generation_status`  
Check the progress of a podcast generation.

**Example:**
```
What's the status of my podcast generation? Task ID: task_123
```

#### `cancel_generation`
Cancel a running podcast generation.

**Example:**
```
Cancel the podcast generation for task ID: task_123
```

### 📁 Resource Access Tools

#### `list_podcast_episodes`
Browse all generated podcast episodes.

**Example:**
```
Show me all my podcast episodes
```

#### `get_podcast_details`
Get detailed information about a specific episode.

**Example:**
```
Show me details for podcast episode ID: ep_456
```

### 🔧 System Tools

#### `get_system_status`
Check server health and capacity.

**Example:**
```
Check the system status of MySalonCast
```

#### `hello`
Test MCP connection.

**Example:**
```
Test the MySalonCast connection
```

## Available Resources

Resources provide read-only access to your content:

- **`podcast_episodes`**: List all podcast episodes
- **`persona_research/{person_id}`**: Individual persona research files
- **`podcast_outline/{task_id}`**: Podcast episode outlines
- **`audio_files/{episode_id}`**: Generated audio files
- **`system_logs`**: Recent system activity logs
- **`capacity_metrics`**: Current system capacity

## Available Prompts

Pre-built prompt templates for common tasks:

- **`create_podcast_from_url`**: Template for URL-based podcast generation
- **`create_podcast_from_pdf`**: Template for PDF-based podcast generation  
- **`analyze_podcast_episode`**: Template for episode analysis
- **`suggest_improvements`**: Template for content improvement suggestions

## Environment Setup

### Local Development
```bash
# Required environment variables
export GEMINI_API_KEY="your-gemini-api-key"
export PROJECT_ID="your-gcp-project-id"
export ENVIRONMENT="local"

# Start the server
python -m app.mcp_server
```

### Cloud Environments

Your MCP server can also connect to deployed environments:

**Production (Recommended for Claude.ai):**
```
Server URL: https://mcp-server-production-644248751086.us-west1.run.app
- ✅ Stable and reliable
- ✅ Latest features
- ✅ Full functionality
- ✅ Monitored and maintained
```

**Staging (Testing new features):**
```
Server URL: https://mcp-server-staging-644248751086.us-west1.run.app
- ⚠️ May have experimental features
- ⚠️ Occasional downtime for updates
- ✅ Good for testing new functionality
```

**Local Development:**
```json
{
  "mcpServers": {
    "mysaloncast-local": {
      "command": "python",
      "args": ["-m", "uvicorn", "app.mcp_server:mcp.app", "--host", "localhost", "--port", "8000"],
      "cwd": "/path/to/mysaloncast"
    }
  }
}
```

## Security & Privacy (Claude.ai Integration)

When using MySalonCast through Claude.ai:

### **⚠️ Important Security Notes**
- MySalonCast processes URLs and PDFs you provide
- Generated content is stored temporarily in our Google Cloud Storage
- Audio files are accessible via public URLs during processing
- We follow Google Cloud security best practices
- No personal data is stored beyond the current session

### **Best Practices**
- ✅ Only provide URLs to public content you're authorized to use
- ✅ Review tool calls before approving audio generation
- ✅ Be mindful of copyright when using commercial content
- ✅ Use staging environment for testing sensitive workflows

### **Data Handling**
- **Input Processing**: URLs and PDFs are processed server-side
- **Temporary Storage**: Generated files stored in GCS buckets  
- **Public URLs**: Audio files accessible via time-limited public links
- **Cleanup**: Files automatically cleaned up based on retention policies

## Troubleshooting

### Common Issues

**1. "MCP server not found"**
- Verify the `cwd` path in your configuration is correct
- Ensure you have activated the virtual environment
- Check that all dependencies are installed

**2. "Connection refused"**
- Make sure the MCP server is running on port 8000
- Check for port conflicts with other applications
- Verify firewall settings

**3. "Import errors"**
- Ensure all requirements are installed: `pip install -r requirements.txt`
- Check that your virtual environment is activated
- Verify Python path includes the project directory

### Debug Mode

Start the server with debug logging:
```bash
export LOG_LEVEL=debug
python -m app.mcp_server
```

### Health Check

Test server connectivity:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "podcast_generator": "available",
    "mcp_server": "running"
  }
}
```

## Example Workflow

Here's a complete example of using MySalonCast through Claude Desktop:

1. **Start conversation**: "I want to create a podcast from this research paper"

2. **Provide URL**: Share the URL or upload a PDF

3. **Customize**: "Use Richard Feynman and Neil deGrasse Tyson as personas, make it a long episode"

4. **Generate**: Claude will call `generate_podcast_async` and return a task ID

5. **Monitor**: "What's the status?" - Claude checks progress

6. **Access**: Once complete, "Show me the podcast details" or "Play the audio"

7. **Explore**: "What other episodes do I have?" - Browse your content library

## Advanced Configuration

### Custom Personas

Create custom persona research files in `/temp_files/persona_research/` and they'll be available for podcast generation.

### Audio Settings

Modify TTS settings in `app/production_config.py`:
```python
TTS_SETTINGS = {
    "voice_name": "en-US-Neural2-J",
    "speaking_rate": 1.1,
    "pitch": 0.0
}
```

### Storage Configuration

Configure cloud storage in your environment:
```bash
export GOOGLE_CLOUD_STORAGE_BUCKET="your-bucket-name"
export ENVIRONMENT="production"
```

## Support

- **Health Status**: `/health` endpoint
- **Logs**: Check `app/logs/` directory
- **Issues**: Check Cloud Run logs for deployed environments
- **Documentation**: This guide and inline code comments

Happy podcasting! 🎙️✨
