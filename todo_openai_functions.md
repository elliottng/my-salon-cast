# OpenAI Responses API Function Calling Integration for MySalonCast

You are tasked with implementing OpenAI Responses API function calling integration for MySalonCast. Create a clean, minimal interface that allows external applications (like Bridgette.app) to generate podcasts through OpenAI's stateful Responses API with real-time progress tracking.

## Key Requirements:

- Single-file implementation targeting small user base (10-50 users)
- Implement function handlers that work with OpenAI's Responses API
- Handle async podcast generation with real-time progress tracking using existing MySalonCast infrastructure
- Support PDF uploads via base64 encoding
- Leverage existing MySalonCast progress tracking and status management
- Keep implementation simple and maintainable

## Architecture Flow:
External App → OpenAI Responses API → MySalonCast Function Handlers → MySalonCast REST API → Progress updates → Response chain

## Focus Areas:

- Function handlers that process OpenAI Responses API function calls
- Simple client for MySalonCast REST API communication
- Real-time progress polling using existing status endpoint
- Function result formatting for Responses API consumption
- Basic error handling with structured responses
- Integration with existing MySalonCast 4-endpoint REST API

Create a working integration layer that leverages MySalonCast's existing sophisticated progress tracking while providing clean function calling interface for OpenAI's Responses API.

# OpenAI Responses API Function Handlers Implementation - Todo List

## Single Phase: MySalonCast Function Interface

### Quick Setup (15 minutes)

- [ ] Create single Python file: `openai_functions.py`
- [ ] Install dependencies: `pip install openai requests python-dotenv`
- [ ] Set environment variables: `OPENAI_API_KEY`, `MYSALONCAST_API_URL`, `MYSALONCAST_API_KEY`
- [ ] Add basic configuration validation

### MySalonCast API Client (30 minutes)

- [ ] Create `MySalonCastClient` class with session management
- [ ] Implement `generate_podcast_async()` method calling `POST /generate/podcast_async/`
- [ ] Implement `upload_pdf()` method calling `POST /process/pdf/`
- [ ] Implement `get_task_status()` method calling `GET /status/{task_id}`
- [ ] Implement `get_podcast_audio()` method calling `GET /podcast/{podcast_id}/audio`
- [ ] Add basic error handling and request headers

### Function Handler Implementation (45 minutes)

- [ ] Create `handle_generate_podcast()` function handler
- [ ] Create `handle_upload_pdf_for_podcast()` function handler
- [ ] Create `handle_check_podcast_status()` function handler
- [ ] Create `handle_get_podcast_audio()` function handler
- [ ] Add function result formatting for Responses API
- [ ] Add parameter validation and error handling

### Progress Tracking Integration (30 minutes)

- [ ] Create progress polling utility using existing `/status/{task_id}` endpoint
- [ ] Parse `PodcastStatus` response for progress percentage and status
- [ ] Map MySalonCast status stages to user-friendly messages
- [ ] Format progress updates for Responses API consumption
- [ ] Add completion detection and result extraction

### Progress Message Mapping (15 minutes)

- [ ] Map "preprocessing_sources" to "Preparing your content..."
- [ ] Map "analyzing_sources" to "Analyzing source material..."
- [ ] Map "researching_personas" to "Researching speaker personas..."
- [ ] Map "generating_outline" to "Creating podcast structure..."
- [ ] Map "generating_dialogue" to "Writing speaker dialogue..."
- [ ] Map "generating_audio_segments" to "Generating AI voices..."
- [ ] Map "stitching_audio" to "Finalizing your podcast..."
- [ ] Map "completed" to success message with audio URL

### PDF Processing Integration (20 minutes)

- [ ] Add base64 PDF encoding function
- [ ] Integrate PDF upload with MySalonCast `/process/pdf/` endpoint
- [ ] Add file size validation (reject >10MB)
- [ ] Chain PDF processing with podcast generation
- [ ] Handle PDF processing errors and responses

### Function Response Formatting (20 minutes)

- [ ] Create standardized function response format for Responses API
- [ ] Add success/error response structures
- [ ] Format task IDs and progress data for consumption
- [ ] Add audio URL and metadata formatting
- [ ] Create consistent error message formatting

### Error Handling and Validation (20 minutes)

- [ ] Handle MySalonCast API connection errors
- [ ] Handle invalid URLs and PDF processing errors
- [ ] Handle task not found and timeout scenarios
- [ ] Add input parameter validation
- [ ] Create user-friendly error messages for function responses

### Function Registry and Dispatcher (15 minutes)

- [ ] Create function registry mapping function names to handlers
- [ ] Implement function call dispatcher
- [ ] Add function parameter extraction and validation
- [ ] Add function execution logging
- [ ] Create function metadata for OpenAI integration

### Testing and Validation (30 minutes)

- [ ] Test `generate_podcast` function with sample URLs
- [ ] Test PDF upload and processing function
- [ ] Test progress tracking through complete workflow
- [ ] Test error scenarios and edge cases
- [ ] Verify function response formats match Responses API expectations
- [ ] Test integration with actual MySalonCast REST API

### Documentation and Configuration (15 minutes)

- [ ] Create function schema documentation for external integration
- [ ] Document required environment variables
- [ ] Add function usage examples
- [ ] Create error code documentation
- [ ] Add deployment and setup instructions

## Implementation Structure

### Single File Organization (~300 lines)
```
openai_functions.py
├── Configuration and environment setup
├── MySalonCastClient class
├── Function handler implementations
├── Progress tracking utilities
├── Response formatting functions
├── Error handling and validation
├── Function registry and dispatcher
└── Integration examples and documentation
```

### Core Function Handlers

- `handle_generate_podcast(source_urls, desired_length, speakers, pdf_content=None)`
- `handle_upload_pdf_for_podcast(pdf_content, filename=None)`
- `handle_check_podcast_status(task_id)`
- `handle_get_podcast_audio(task_id)`

### Integration Points

- MySalonCast REST API (4 endpoints)
- OpenAI Responses API function calling format
- Existing MySalonCast progress tracking infrastructure
- Base64 PDF encoding/decoding

### Response Format Standards

- Success responses with structured data
- Error responses with user-friendly messages
- Progress updates with percentage and descriptions
- Audio delivery with URLs and metadata

## Success Criteria

- [ ] External apps can call MySalonCast functions via OpenAI Responses API
- [ ] Real-time progress tracking works through function calls
- [ ] PDF uploads process seamlessly
- [ ] Audio files are delivered when generation completes
- [ ] Error scenarios return helpful structured responses
- [ ] Implementation integrates cleanly with existing MySalonCast infrastructure
- [ ] Function handlers work with OpenAI's stateful conversation model

**Total implementation time:** ~4 hours  
**Key focus:** Clean function interface for OpenAI Responses API integration with MySalonCast

This creates a bridge layer that allows any application using OpenAI's Responses API to access MySalonCast's podcast generation capabilities with sophisticated progress tracking.
