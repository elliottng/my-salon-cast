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

## Authentication & Security

### Current Authentication Methods
- **OAuth 2.0 Framework**: Pre-configured for Claude.ai and webapp clients
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

### Podcast Generation Flow
1. **Input Validation**: PDF readability, URL accessibility, parameter validation
2. **Content Extraction**: Text from PDFs, transcripts from YouTube, web content
3. **LLM Processing**: 
   - Source analysis and persona research
   - Outline generation with segment structure
   - Dialogue script creation with character voices
4. **Audio Synthesis**: 
   - TTS generation with voice differentiation
   - Audio segment stitching (using pydub)
5. **Post-processing**: 
   - Cloud storage upload
   - Metadata generation
   - Status updates and cleanup

### Task Management
- **Async Processing**: Background task execution with ThreadPoolExecutor
- **Status Tracking**: Real-time progress logging with percentage completion
- **Cancellation Support**: Mid-process task cancellation capability
- **Error Handling**: Comprehensive error tracking and recovery

## Monitoring & Logging

### Logging Infrastructure
- **Centralized Logging**: Standardized log format across all components
- **Request Correlation**: MCP tool and resource access tracking
- **Progress Tracking**: Detailed pipeline stage logging with timestamps
- **Error Aggregation**: Structured error collection and warning systems

### Available Logs
- **MCP Operations**: Tool calls, resource access, validation errors
- **Pipeline Progress**: Step-by-step generation progress with percentages
- **Service Health**: Component initialization, API availability
- **Storage Operations**: Upload/download status, fallback triggers
- **Task Lifecycle**: Creation, execution, completion, cleanup events

### Health Monitoring
- **Service Status**: Component availability checks (LLM, TTS, Storage)
- **Configuration Validation**: Environment setup verification
- **Resource Utilization**: File system usage, storage quotas
- **Error Rates**: Failed generation attempts, service degradation

## Utility Architecture

### Code Organization (Recent Refactoring)
The codebase underwent extensive deduplication across 4 phases, eliminating 400+ lines of duplicate code:

**Utility Modules**:
- `storage_utils.py`: Cloud storage operations, directory management
- `mcp_utils.py`: MCP validation, response building, file collection
- `logging_utils.py`: Standardized logging with request correlation
- `http_utils.py`: HTTP requests with retry logic
- `json_utils.py`: Safe JSON serialization/deserialization

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
