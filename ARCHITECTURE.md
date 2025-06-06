# MySalonCast Technical Architecture

## Overview

MySalonCast is a cloud-native **Model Context Protocol (MCP) server** that converts PDF documents and web content into conversational audio podcasts. Users access the system exclusively through Claude.ai's remote MCP server integration, which establishes server-to-server connections to our hosted service.

## System Architecture

### Core Components

```
Claude.ai ──── MCP Protocol ──── MySalonCast MCP Server ──── Podcast Generation Pipeline
                                        │
                                        ├── Google Cloud TTS
                                        ├── Google Gemini LLM
                                        ├── Cloud Storage (GCS)
                                        └── Local SQLite Database
```

### Component Details

**MCP Server** (`app/mcp_server.py`)
- FastMCP framework-based server exposing tools and resources
- Handles Claude.ai connections via MCP protocol
- Provides 8 tools and 10 resources for podcast generation and management
- Primary interface for all user interactions

**Podcast Generation Pipeline** (`app/podcast_workflow.py`)
- Asynchronous processing pipeline (3-5 minute generation time)
- Supports sync and async modes (async is primary use case)
- Orchestrates content extraction, LLM processing, and TTS synthesis

**Content Processing**
- PDF text extraction (`app/content_extractor.py`)
- YouTube transcript extraction 
- URL content extraction (best-effort for non-YouTube URLs)

**AI Services**
- Google Gemini 2.5 Pro for content analysis and dialogue generation
- Google Cloud TTS for audio synthesis with voice differentiation

## Data Storage

### File Storage Strategy
- **Local Development**: Files stored in `./outputs/` directory structure
- **Cloud Production**: Google Cloud Storage with bucket-based organization
- **Automatic Fallback**: Cloud operations fall back to local storage on failure
- **Implementation**: `app/storage.py` - CloudStorageManager with fallback logic

### Storage Layout
```
Cloud Storage (GCS):
├── podcasts/{task_id}/audio/
│   ├── final_podcast.mp3
│   └── segment_*.mp3
├── text/{task_id}/
│   ├── outline.json
│   ├── persona_research_{person_id}.json
│   └── transcript.txt
└── episodes/{task_id}/
    └── metadata.json

Local Fallback:
├── outputs/audio/{task_id}/
├── temp_files/{task_id}/
└── podcast_status.db (SQLite)
```

### Database
- **Primary**: SQLite database (`podcast_status.db`) for task status, logs, and metadata
- **Location**: Local filesystem with potential GCS backup
- **Schema**: Task tracking, progress logs, episode metadata, cleanup policies
- **Implementation**: `app/database.py` - PodcastStatusDB class

## Model Context Protocol (MCP) Server

### MCP Interface (`app/mcp_server.py`)
MySalonCast's primary interface is an MCP server that integrates with Claude.ai through the Model Context Protocol. The server exposes a comprehensive set of tools and resources for podcast generation and management.

#### MCP Tools (8 total)
- **generate_podcast_async**: Start async podcast generation, returns task_id
- **get_task_status**: Retrieve status, progress, and results for running tasks  
- **list_task_statuses**: List all task statuses with pagination
- **delete_task_status**: Remove completed task data
- **cancel_task**: Cancel running podcast generation
- **cleanup_task_files**: Remove temporary files and artifacts
- **get_cleanup_status**: View cleanup policies and file status
- **get_queue_status**: Monitor task queue and worker capacity

#### MCP Resources (10 total)
- **Job Status Resources**: `job_status/{task_id}`, `job_logs/{task_id}`, `job_warnings/{task_id}`
- **Podcast Content**: `podcast_transcript/{task_id}`, `podcast_audio/{task_id}`, `podcast_metadata/{task_id}`
- **Intermediate Content**: `podcast_outline/{task_id}`, `persona_research/{task_id}/{person_id}`
- **System Resources**: `cleanup_status`, `cleanup_config`

#### MCP Configuration (`app/mcp_descriptions.py`)
- Detailed descriptions for all tools, resources, and prompts
- Documentation strings for Claude.ai integration
- Parameter validation and error handling specifications

### Utility Architecture Supporting MCP
- **Request Validation**: `app/mcp_utils.py` - validate_task_id, validate_person_id
- **Resource Building**: Standardized response builders for consistent MCP responses
- **Error Handling**: `handle_resource_error` for consistent error messaging
- **File Operations**: Centralized file collection and cleanup utilities

## FastAPI REST Endpoints

### REST API Server (`app/main.py`)
In addition to the MCP interface, MySalonCast provides a traditional REST API for web applications and direct HTTP access.

#### Content Processing Endpoints
- **POST /process/pdf/** - Upload and extract text from PDF files
- **POST /process/url/** - Extract content from web URLs  
- **POST /process/youtube/** - Extract transcripts from YouTube videos

#### Podcast Generation Endpoints
- **POST /generate/elements** - Generate podcast outline and research (sync)
- **POST /generate/async** - Start async podcast generation, returns task_id
- **GET /podcast/{podcast_id}/audio** - Stream complete podcast audio with HTML player
- **GET /podcast/{podcast_id}/segment/{segment_id}** - Stream individual audio segments

#### Task Management Endpoints
- **GET /status/{task_id}** - Get detailed task status and progress
- **GET /status/list** - List all task statuses with pagination
- **DELETE /status/{task_id}** - Delete task status and cleanup
- **POST /cancel/{task_id}** - Cancel running task
- **GET /queue/status** - Monitor task queue and worker capacity

#### System Endpoints
- **GET /** - API information and environment status
- **GET /health** - Health check endpoint

### REST API Features
- **CORS Support**: Environment-specific origin configuration
- **Static File Serving**: Local audio file serving in development
- **Error Handling**: Consistent HTTP status codes and error messages
- **Request Validation**: Pydantic models for request/response validation

## Authentication & Security

### Current Authentication Methods
- **OAuth 2.0 Framework**: Pre-configured for Claude.ai and webapp clients (`app/oauth_config.py`)
- **Client Credentials**: Environment-based secrets (CLAUDE_CLIENT_SECRET, WEBAPP_CLIENT_SECRET)
- **Auto-generated Secrets**: Development fallback with secure token generation
- **Scopes**: `mcp.read`, `mcp.write` for resource access control

### Security Features
- Environment-based credential management
- Automatic secret generation for development
- Secure token handling for production deployments

## Deployment Architecture

### Infrastructure (Terraform)
- **Platform**: Google Cloud Platform (GCP)
- **Environments**: Staging and Production with separate resource isolation
- **Compute**: Cloud Run for serverless container deployment
- **Storage**: GCS buckets with lifecycle policies (30-day auto-deletion)
- **APIs**: Cloud Run, Cloud Build, Cloud Storage enabled
- **Configuration**: `terraform/main.tf`, `terraform/variables.tf`

### Environment Configuration
- **Staging**: `{project_id}-staging-audio`, `{project_id}-staging-database` buckets
- **Production**: `{project_id}-production-audio`, `{project_id}-production-database` buckets
- **Auto-scaling**: Cloud Run handles 4 concurrent users maximum
- **Lifecycle**: 30-day automatic file cleanup on storage buckets

### CI/CD Pipeline
- **Build**: Cloud Build (`cloudbuild.yaml`) for container images
- **Deploy**: Terraform for infrastructure management
- **Configuration**: Environment-specific templates (`.env.staging.template`, `.env.production.template`)

## Processing Pipeline

### Podcast Generation Flow (`app/podcast_workflow.py`)
1. **Input Validation**: PDF readability, URL accessibility, parameter validation
2. **Content Extraction**: Text from PDFs, transcripts from YouTube, web content (`app/content_extractor.py`)
3. **LLM Processing**: 
   - Source analysis and persona research (`app/llm_service.py`)
   - Outline generation with segment structure
   - Dialogue script creation with character voices
4. **Audio Synthesis**: 
   - TTS generation with voice differentiation (`app/tts_service.py`)
   - Audio segment stitching (using pydub)
5. **Post-processing**: 
   - Cloud storage upload (`app/storage.py`)
   - Metadata generation
   - Status updates and cleanup (`app/status_manager.py`)

### Task Management (`app/task_runner.py`)
- **Async Processing**: Background task execution with ThreadPoolExecutor
- **Status Tracking**: Real-time progress logging with percentage completion
- **Cancellation Support**: Mid-process task cancellation capability
- **Error Handling**: Comprehensive error tracking and recovery

## Monitoring & Logging

### Logging Infrastructure
- **Centralized Logging**: Standardized log format across all components (`app/logging_utils.py`)
- **Request Correlation**: MCP tool and resource access tracking
- **Progress Tracking**: Detailed pipeline stage logging with timestamps
- **Error Aggregation**: Structured error collection and warning systems

### Available Logs
- **MCP Operations**: Tool calls, resource access, validation errors (`app/mcp_server.py`)
- **Pipeline Progress**: Step-by-step generation progress with percentages (`app/podcast_workflow.py`)
- **Service Health**: Component initialization, API availability (`app/main.py`, `app/config.py`)
- **Storage Operations**: Upload/download status, fallback triggers (`app/storage.py`)
- **Task Lifecycle**: Creation, execution, completion, cleanup events (`app/task_runner.py`, `app/status_manager.py`)

### Health Monitoring
- **Service Status**: Component availability checks (LLM, TTS, Storage)
- **Configuration Validation**: Environment setup verification (`app/config.py`)
- **Resource Utilization**: File system usage, storage quotas
- **Error Rates**: Failed generation attempts, service degradation

## Utility Architecture

### Code Organization (Recent Refactoring)
The codebase underwent extensive deduplication across 4 phases, eliminating 400+ lines of duplicate code:

**Utility Modules**:
- `app/storage_utils.py`: Cloud storage operations, directory management
- `app/mcp_utils.py`: MCP validation, response building, file collection  
- `app/logging_utils.py`: Standardized logging with request correlation
- `app/http_utils.py`: HTTP requests with retry logic
- `app/json_utils.py`: Safe JSON serialization/deserialization

**Benefits**:
- Consistent error handling and validation across all components
- Unified logging format for better debugging
- Centralized file operations with automatic fallback
- Standardized response formats for MCP resources and tools

## Scalability & Performance

### Current Capacity
- **Concurrent Users**: 4 simultaneous podcast generations
- **Generation Time**: 3-5 minutes per podcast
- **File Retention**: 30-day automatic cleanup
- **Cache Strategy**: In-memory text file caching with TTL

### Performance Optimizations
- **Async Processing**: Non-blocking podcast generation
- **Resource Pooling**: Shared service instances across requests
- **Storage Fallback**: Automatic local fallback for reliability
- **Progress Streaming**: Real-time status updates during generation

This architecture provides a robust, scalable foundation for converting documents into conversational podcasts while maintaining high reliability through comprehensive error handling and automatic fallbacks.
