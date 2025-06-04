# Detailed To-Do List for LLM Coding Agent (Aligned with MySalonCast PRD Version 1.1 - V1 Scope with Terraform)

This to-do list is broken down for a single LLM coding agent, focusing on actionable development tasks. Priorities are suggested (P1 = High, P2 = Medium, P3 = Low). Effort is relative (S = Small, M = Medium, L = Large, XL = Extra Large).

## Phase 1: Backend Core Logic & API Endpoints

### Task 1.1: Setup Project & Environment (P1, S) 
- [x] Initialize Python project (e.g., Flask/FastAPI)
- [x] Set up virtual environment and install basic dependencies
- [x] Structure project directories
- [x] Install Terraform CLI
- [x] Set up Terraform state backend

### Task 1.2: Input Validation Module (P1, M) 
- [x] Define validation rules for PDF uploads (file type, size limits)
- [x] Define validation rules for URL inputs (format, accessibility)
- [x] Implement validation logic in FastAPI endpoints
- [x] Unit tests for validation functions
- [x] Error handling and user feedback



### Task 1.5: Content Extraction Service (V1 Scope) (P1, L)
- [x] Implement PDF text extraction
- [x] Implement YouTube transcript fetching
- [x] Implement best-effort text extraction for simple URLs
- [x] Unit tests for content extraction functions
- [x] Basic error handling for failed extractions
- [x] Handle errors gracefully

### Task 1.6: LLM Interaction Service Wrapper (P1, M) 
- [x] Create Google Gemini 2.5 Pro API wrapper
- [x] Implement method for source analysis
- [x] Implement method for persona research
- [x] Implement method for podcast outline generation (Ref: PRD 4.2.4 detailed prompt)
- [x] Implement method for dialogue writing
- [x] Manage API key securely
- [x] Implement retry logic

### Task 1.7: TTS Service Wrapper (P1, M) 
- [x] Create Google Cloud Text-to-Speech wrapper
- [x] Implement text-to-audio conversion
- [x] Implement voice selection based on LLM characteristics

### Task 1.8: Core Podcast Generation Workflow (P1, L)
- [x] Establish `PodcastGeneratorService` for workflow orchestration (`generate_podcast_from_source` method).
- [x] Integrate `PodcastRequest` as input and `PodcastEpisode` as output.
- [x] Implement temporary directory management for job-specific files.
- [x] Integrate content extraction for URLs (PDF path handling needs improvement).
- [x] Integrate LLM call for source text analysis (`LLMService.analyze_source_text_async`).
- [x] Integrate LLM call for generating podcast title and summary.
- [x] Integrate LLM call for generating main podcast script content.
- [x] Integrate TTS call for converting the main script to audio.
- [x] Basic error handling returning placeholder `PodcastEpisode` on critical failures.
- [x] Implement core LLM-driven persona research service (`GeminiService.research_persona_async`)
- [x] Integrate persona research calls into `PodcastGeneratorService` workflow
- [x] Utilize `PersonaResearch` data for podcast outline and dialogue generation
- [x] Implement LLM-driven detailed podcast outline generation (multi-segment).
- [x] Refine LLM dialogue writing to iterate through outline segments, producing `DialogueTurn` objects.
- [x] Implement audio stitching of multiple `DialogueTurn` audio segments using `pydub`.
- [x] Enhance transcript generation by concatenating text from `DialogueTurn` objects.
- [ ] Implement detailed source attribution: LLM-provided mentions compiled into `PodcastEpisode.source_attributions` and appended to transcript.
- [ ] Implement robust content flag checking based on LLM safety ratings, populating `PodcastEpisode.warnings`.
- [x] Implement serialization of all specified intermediate LLM outputs (source analysis, persona research, outline, dialogue turns) to temp JSON files.
- [x] Ensure `PodcastEpisode` includes file paths to all serialized intermediate LLM outputs.
- [ ] Improve PDF content extraction to correctly handle file paths (currently expects `UploadFile`).

# Phase 2: Model Context Protocol Server and API Implementation

## 1.1: FastAPI v.1 Extension (P1, L)
- [ ] Design the `app/main.py` FastAPI v.1 endpoints
- [ ] Implement the `app/main.py` FastAPI v.1 endpoints
- [ ] Extend existing `app/main.py` with FastAPI v.1 endpoints:
  - [ ] `POST /api/v1/podcasts/generate` (async job creation)
  - [ ] `GET /api/v1/podcasts/{id}/status` (progress monitoring - does this already exist? if not, let's not do it as an API)
  - [ ] `GET /api/v1/podcasts/{id}/audio` (file download)
  - [ ] `GET /api/v1/podcasts/{id}/transcript` (text download)

- [ ] Add rate limiting (IP-based, 5 requests/day for anonymous users)
- [ ] Integrate with existing `PodcastGeneratorService`

## 1.2: Data Model Migration (P1, L)

### 1.2.1: Extend PersonaResearch model in `app/podcast_models.py`
- [x] Add `invented_name: str` field
- [x] Add `gender: str` field
- [x] Add `tts_voice_id: str` field
- [x] Add `source_context: str` field
- [x] Add `creation_date: datetime` field

### 1.2.2: Update `app/llm_service.py`
- [x] Modify `research_persona_async()` to assign invented names during creation
- [x] Implement deterministic gender assignment logic
- [x] Add Google TTS voice selection logic
- [x] Update PersonaResearch creation to populate new fields

### 1.2.3: Migrate `app/podcast_workflow.py`
- [x] Remove temporary `persona_details_map` logic (~lines 180-220)
- [x] Update dialogue generation to use PersonaResearch model fields
- [x] Remove hardcoded name/gender assignment lists
- [x] Update TTS integration to use `PersonaResearch.tts_voice_id`

### 1.2.4: Update dependent services
- [x] Modify `app/tts_service.py` to use PersonaResearch voice assignments
- [x] Update `app/audio_utils.py` DialogueTurn creation logic

### 1.2.5: Create PodcastStatus model
- [x] Create PodcastStatus model for comprehensive status tracking (COMPLETED)
  - [x] Define PodcastProgressStatus Literal type with all status states
  - [x] Create PodcastStatus Pydantic model with all fields
  - [x] Add ArtifactAvailability tracking model
  - [x] Include update_status() helper method
- [x] Create StatusManager for thread-safe status management (COMPLETED)
  - [x] Implement singleton pattern with get_status_manager()
  - [x] Add CRUD operations: create, get, update, delete
  - [x] Include artifact tracking and error handling
  - [x] Write comprehensive test coverage
- [x] Implement dual sync/async API support in workflow (COMPLETED)
  - [x] Refactor to _generate_podcast_internal() 
  - [x] Keep generate_podcast_from_source() backwards compatible
  - [x] Add generate_podcast_async() for async mode
  - [x] Create and update status in both modes

## 1.3: Add Status Updates Throughout Workflow (P1, M) 
- [x] Add status update after source extraction completes
  - [x] Update to "analyzing_sources" with progress ~15%
  - [x] Set artifact: source_content_extracted = True
- [x] Add status update after source analysis
  - [x] Update to "researching_personas" with progress ~30%
  - [x] Set artifact: source_analysis_complete = True
- [x] Add status update after persona research
  - [x] Update to "generating_outline" with progress ~45%
  - [x] Set artifact: persona_research_complete = True
- [x] Add status update after outline generation
  - [x] Update to "generating_dialogue" with progress ~60%
  - [x] Set artifact: podcast_outline_complete = True
- [x] Add status update after dialogue generation
  - [x] Update to "generating_audio_segments" with progress ~75%
  - [x] Set artifact: dialogue_script_complete = True
- [x] Add status update during audio generation
  - [x] Update progress incrementally as segments complete
  - [x] Set artifact: individual_audio_segments_complete = True
- [x] Add status update after audio stitching
  - [x] Update to "postprocessing_final_episode" with progress ~95%
  - [x] Set artifact: final_podcast_audio_available = True
- [x] Update to "completed" with episode result at 100%

### 1.3.1: Create Status Check REST Endpoint (P1, S) 
- [x] Add GET `/status/{task_id}` endpoint to main.py
  - [x] Return PodcastStatus model directly
  - [x] Handle 404 if task_id not found
  - [x] Include all status fields and artifacts
- [x] Add GET `/status` endpoint to list all statuses
  - [x] Support pagination parameters
  - [x] Return list of PodcastStatus objects
- [x] Add DELETE `/status/{task_id}` for cleanup
- [x] Update API documentation
- [x] Add POST `/generate/podcast_async/` endpoint for async generation
  - [x] Returns task_id immediately
  - [x] Enables status tracking via task_id
- [x] Create comprehensive test scripts
  - [x] test_status_rest_api.py for REST API testing
  - [x] test_status_simple.py for direct service testing
  - [x] test_status_endpoints.py for async HTTP testing

### 1.3.2: Add Status Persistence - Two-Stage Approach (P2, M)

#### 1.3.2.1: Stage 1: Local Development with SQLite 
- [x] Install SQLModel dependency (SQLAlchemy + Pydantic)
- [x] Create database models (PodcastStatusDB) using SQLModel
- [x] Setup SQLite database connection with environment variable fallback
- [x] Migrate StatusManager methods to use database:
  - [x] create_status() - Insert new status records
  - [x] get_status() - Query by task_id
  - [x] update_status() - Update existing records
  - [x] list_statuses() - Query with pagination
  - [x] delete_status() - Remove records
- [x] Add JSON serialization for complex fields (request_data, result_episode)
- [x] Test all CRUD operations with SQLite locally

**Completion Notes:**
- Created `app/database.py` with SQLModel integration
- Refactored `StatusManager` to use database persistence
- Fixed circular imports by moving `PodcastRequest` to `podcast_models.py`
- Database file `podcast_status.db` created automatically
- All REST API endpoints working with database persistence
- Tested with `test_database_persistence.py` and `test_status_rest_api.py`

#### 1.3.2.2: Production Deployment with SQLite


## 1.4: Implement True Async Processing (P2, L)
- [x] Add background task processing with asyncio
- [x] Update _generate_podcast_internal to spawn background task when async_mode=True
- [x] Implement proper task cancellation support
- [x] Add task queue management
- [x] Handle concurrent task limits
- [x] Add webhook/callback support for completion notifications

**Completion Notes:**
- Created `app/task_runner.py` with ThreadPoolExecutor for background processing
- Implemented async wrappers for podcast generation with proper error handling
- Added task cancellation support with status updates
- Created queue management with concurrent task limits (max 3 by default)
- Added webhook notifications for task completion/failure/cancellation
- Fixed TaskRunner lifetime counter to correctly track total_submitted tasks even after completion

## 1.5: Direct FastMCP Implementation (P1, L)

### 1.5.1: Install and Configure FastMCP 2.0 (P1, S) - COMPLETED
- [x] Install FastMCP 2.0: `pip install fastmcp`
- [x] Verify installation with `fastmcp version`
- [x] Update requirements.txt to include fastmcp
- [x] Create basic MCP server structure

### 1.5.2: Create Base MCP Server Module (P1, M) - COMPLETED
- [x] Create `app/mcp_server.py` as the main MCP interface
- [x] Initialize FastMCP server with appropriate name and instructions
- [x] Set up proper logging and error handling
- [x] Create basic server lifecycle management

### 1.5.3: Fix FastMCP Implementation - Core Setup (P1, S)
- [x] Fix FastMCP initialization to use single string parameter: `mcp = FastMCP("MySalonCast Podcast Generator")`
- [x] Remove incorrect `@mcp_server.on_event()` decorators (startup/shutdown)
- [x] Rename `mcp_server` to `mcp` throughout the file
- [x] Update `if __name__ == "__main__"` to use `mcp.app` instead of `mcp_server.app`
- [x] Add proper error handling patterns that return dicts instead of raising exceptions

## 1.6: Async Tool Implementation (P1, L) - COMPLETED
- [x] Create `@mcp.tool()` for `generate_podcast_async`
  - [x] Individual parameters: source_urls, source_pdf_path, prominent_persons, etc.
  - [x] Convert parameters to PodcastRequest internally
  - [x] Call `podcast_service.generate_podcast_async()`
  - [x] Return dict with task_id and initial status
  - [x] Handle validation errors gracefully
- [x] Create `@mcp.tool()` for `generate_podcast_async_pydantic`
  - [x] Accept PodcastRequest model directly
  - [x] Pass through to service
  - [x] Return same format as individual params version
- [x] Create `@mcp.tool()` for `get_task_status`
  - [x] Accept task_id parameter
  - [x] Query StatusManager for current status
  - [x] Return status, progress, and result when complete
  - [x] Handle invalid task_id gracefully

## 1.7: Resource Implementation (P1, M) - COMPLETED
- [x] Create `@mcp.resource("podcast://{task_id}/transcript")` for transcript access
- [x] Create `@mcp.resource("podcast://{task_id}/audio")` for audio file access
- [x] Create `@mcp.resource("podcast://{task_id}/metadata")` for episode metadata
- [x] Create `@mcp.resource("config://supported_formats")` for supported formats
- [x] Implement proper file path resolution from PodcastEpisode data
- [x] Handle file not found and invalid task_id cases

## 1.8: End-to-End Testing of Async Tools (P1, M)
- [x] Test `generate_podcast_async` with various input combinations
- [ ] Test `generate_podcast_async_pydantic` with PodcastRequest models
- [x] Test `get_task_status` throughout generation lifecycle
- [x] Test resource access for completed podcasts
- [x] Test error handling for invalid inputs and failed generations
- [x] Create MCP client test scripts
- [x] Document any issues or improvements needed

## 1.9: Sync Tool Implementation (P1, M) POSTPONED TO V1.1
- [ ] Create `@mcp.tool()` for `generate_podcast_sync`
  - [ ] Individual parameters matching async version
  - [ ] Call `await podcast_service.generate_podcast_from_source()`
  - [ ] Return complete episode data in dict format
- [ ] Create `@mcp.tool()` for `generate_podcast_sync_pydantic`
  - [ ] Accept PodcastRequest model directly
  - [ ] Same blocking behavior as individual params version
- [ ] Test sync tools with same scenarios as async

## 1.10: Optional Enhancements (P2, S) -POSTPONED TO V1.1
- [ ] Add `@mcp.prompt()` templates for common podcast generation requests
- [ ] Add progress callbacks to Context for real-time updates
- [ ] Create resource for listing all available tasks
- [ ] Add tool for cancelling in-progress tasks
- [ ] Consider adding webhook configuration via MCP

## 1.11: Static Resources (P1, M)
- [x] Expose configuration as `@mcp.resource("config://app")`
- [x] Expose API documentation as `@mcp.resource("docs://api")`
- [x] Expose example requests as `@mcp.resource("examples://requests")`
- [x] Create resource for supported file formats

## 1.12: Dynamic Resources - Podcast Data (P1, L)
- [x] Create `@mcp.resource("podcast://{podcast_id}/transcript")` for transcripts
- [x] Create `@mcp.resource("podcast://{podcast_id}/audio")` for audio files
- [x] Create `@mcp.resource("podcast://{podcast_id}/outline")` for outlines

## 1.13: Dynamic Resources - Job Status (P2, M)
- [x] Create `@mcp.resource("jobs://{job_id}/status")` for generation progress status
- [x] Create `@mcp.resource("jobs://{job_id}/logs")` for processing logs
- [x] Create `@mcp.resource("jobs://{job_id}/warnings")` for warnings/errors
- [x] Implement proper error handling for missing resources

## 1.14: Dynamic Resources - LLM Outputs (P2, M)
- [x] Create `@mcp.resource("research://{job_id}/{person_id}")` for persona research

## 1.15: Core Prompt Templates (P2, M)
- [x] Create `@mcp.prompt()` for podcast generation requests
- [x] Create `@mcp.prompt()` for persona research prompts
- [x] Include proper parameter validation and descriptions

## 1.16: Service Integration (P1, L)
- [x] Integrate with existing `PodcastGeneratorService`
**Completion Notes:** done in earlier phases

## 1.17: Validate Model Compatibility (P1, S)
- [x] Ensure MCP models work with existing Pydantic models
- [x] If needed, create adapters for `PodcastRequest` → MCP tool parameters
- [x] Maintain compatibility with `PodcastEpisode` output format
- [x] If needed, handle type conversions between MCP and internal models
**Completion Notes:** done in earlier phases

## 1.18: File Management (P1, M)
- [x] Add direct audio file content access via MCP resources (`files://{task_id}/audio/content`)
- [x] Implement configurable cleanup policy for temporary directories
- [x] Add file access security validation (path safety, ownership checks)
- [x] Create audio segments resource for individual dialogue turns

**Completion Notes:** 
- [x] `files://{task_id}/audio/content` - Returns base64-encoded audio content
- [x] `files://{task_id}/segments` - Lists audio segment metadata  
- [x] `files://{task_id}/segments/{segment_id}` - Individual segment content
- [x] `files://{task_id}/cleanup` - Cleanup status and policy info
- [x] `cleanup_task_files` tool - Enhanced with configurable policies
- [x] `configure_cleanup_policy` tool - Policy configuration management
- [x] `config://cleanup` resource - View current cleanup settings
- [x] Security validation: `_validate_file_access()` and `_validate_task_ownership()`
- [x] Cleanup configuration system with 6 policy types and selective file removal

## 1.19: MCP Context Integration (P1, M)
- [x] Add Context parameter to tools for logging
- [x] **Implement enhanced progress reporting for podcast generation stages**
  - [x] Added detailed progress logging to source analysis phase
  - [x] Added detailed progress logging to persona research phase  
  - [x] Added detailed progress logging to outline generation phase
  - [x] Added detailed progress logging to dialogue generation phase
  - [x] Added detailed progress logging to TTS audio generation phase
  - [x] Added detailed progress logging to audio stitching phase
  - [x] Added detailed progress logging to final episode creation phase
  - [x] Enhanced StatusManager with `add_progress_log()` method for sub-task tracking
  - [x] Enhanced `update_status()` with optional `progress_details` parameter
  - [x] Comprehensive test coverage for all workflow phases (58 progress logs)
  - [x] Error handling and failure scenario logging (success [x], failure [ ], warning [ ])

  - [x] **Phase 5.1 Option 2: Enhanced Progress Reporting - COMPLETE**
- [ ] Add resource access for reading intermediate files
- [ ] Include request ID tracking for job correlation

## 1.20: Error Handling and Validation (P1, M)
- [x] Import and use FastMCP's ToolError exceptions instead of returning error dictionaries
- [x] Add basic input validation for critical parameters (task_id, source_urls, file paths)
- [x] Implement comprehensive error handling with ToolError/ResourceError
- [x] Add input validation for all tool parameters
- [x] Create meaningful error messages for clients
- [x] Handle service initialization failures gracefully

**Completion Notes (a1696992):**
- [x] Imported ToolError from fastmcp.exceptions in mcp_server.py
- [x] Replaced all error dictionaries with proper ToolError exceptions in core tools
- [x] Added comprehensive input validation for generate_podcast_async (URL/PDF limits, formats)
- [x] Added task_id validation for status and cleanup tools (length, format requirements)
- [x] Fixed ToolError usage to use positional arguments instead of keyword arguments
- [x] Created and ran comprehensive test suite with 8 test cases
- [x] All validation scenarios working correctly with informative error messages

## 1.21: Authentication and Security (P2, M)
- [ ] Consider adding basic authentication if needed
- [ ] Implement rate limiting for resource-intensive operations
- [x] Secure file access and temporary directory management

## 1.22: MCP-Specific Testing (P1, M)
- [x] Create test suite for MCP tools using FastMCP Client
- [x] Test resource access patterns
- [x] Test prompt generation functionality
- [x] Create integration tests with existing workflow

**Completion Notes:**
- [x] Complete MCP test suite created (test_mcp_client.py, test_mcp_prompts.py, etc.)
- [x] All resource access patterns tested and validated
- [x] Prompt template testing with 100% pass rate (5/5 tests) (789f226c)
- [x] Comprehensive integration test (test_mcp_integration.py) (1b8fd7fb)
- [x] Fixed status polling premature failures in integration tests (9ad08000)

### Phase 6.1a: Resource Validation and Fixes (P1, M) [NEW SECTION]
- [x] Validate and fix all podcast resources (transcript, audio, metadata, outline)
- [x] Validate and fix all job resources (status, logs, warnings)
- [x] Implement persona research resource with comprehensive testing
- [x] Fix field mapping issues and attribute access patterns
- [x] Add proper error handling for missing tasks and episodes

**Completion Notes:**
- [x] Fixed podcast://{task_id}/transcript resource validation (305e8542)
- [x] Fixed podcast://{task_id}/audio resource with file existence checks (fe64de0e)
- [x] Fixed podcast://{task_id}/metadata resource with timestamp handling (8f48c785)
- [x] Fixed podcast://{task_id}/outline resource to read from JSON files (3393bc97)
- [x] Fixed jobs://{task_id}/warnings resource with proper field mapping (25c77a68)
- [x] Fixed jobs://{task_id}/status and logs resources (e5e55484)
- [x] Implemented research://{task_id}/{person_id} with 8/8 tests passing (5e1eeafa)
- [x] Fixed SourceAnalysis field mismatch (key_topics/main_arguments) (fae4b362)

## 1.22: TTS Health Monitoring and Production Readiness (P1, M) [NEW SECTION]
- [x] Implement comprehensive TTS health monitoring system
- [x] Add TTS metrics collection with thread pool monitoring
- [x] Create MCP health monitoring tools for production deployment
- [x] Validate health monitoring accuracy with process isolation testing
- [x] Enhance TTS service with improved concurrency and error handling

**Completion Notes (1c92a4c6):**
- [x] Added TtsMetrics class with detailed performance tracking
- [x] Implemented safe thread pool metrics calculation for different Python versions
- [x] Enhanced ThreadPoolExecutor from 4 to 16 workers for better concurrency
- [x] Added get_service_health MCP tool for real-time service monitoring
- [x] Added test_tts_service MCP tool for validation testing
- [x] Fixed TTS async thread pool shutdown errors (64a35a56)
- [x] Comprehensive health monitoring validation with 5 critical checks passing
- [x] Production-ready health features for Cloud Run deployment

## 1.23: MCP Context and Parameter Flow Fixes (P1, S) [NEW SECTION]
- [x] Fix MCP Context parameter usage according to FastMCP specification
- [x] Resolve parameter mapping issues between MCP tools and internal models
- [x] Fix async test compatibility and response parsing
- [x] Update environment variable naming for consistency

**Completion Notes:**
- [x] Fixed MCP Context parameter usage in FastMCP specification (522f865d)
- [x] Fixed podcast_length parameter validation and mapping (02b68a8d)
- [x] Fixed get_task_status tool model attribute access vs dict access (2b45d81d)
- [x] Renamed GOOGLE_API_KEY to GEMINI_API_KEY for clarity (1be243b4)
- [x] All 6 MCP async tests now pass with 100% success rate

## 1.24: Server Configuration (P1, S)
- [x] Configure server for appropriate transport (stdio, HTTP)
- [x] Set up proper logging levels
- [ ] Configure duplicate handling policies
- [ ] Set up custom error masking if needed

**Completion Notes:**
- [x] FastMCP 2.0 server configured with Streamable HTTP transport
- [x] MCP server runs on port 8000 with `/mcp` endpoint
- [x] Proper logging configuration throughout MCP tools and resources

## 1.25: Documentation and Examples (P2, S)
- [x] Create usage examples for MCP clients
- [x] Document available tools, resources, and prompts

**Completion Notes:**
- [x] Comprehensive API documentation via docs://api resource
- [x] Example requests and responses documented
- [x] MCP prompt templates with parameter guidance
- [x] Test scripts serve as usage examples
{{ ... }}

## Phase 7: LLM Prompt Iteration 

### 1.1: Source Analysis Prompt Iteration (P2, M) 
- [x] Refine prompt for extracting key themes, facts, and insights from source texts (corresponds to `analyze_source_text_async`).
- [x] Test with diverse source materials (PDFs, YouTube, URLs).
- [x] Evaluate quality of analysis against PRD requirements (Section 4.2.2).
- [x] Iterate on prompt based on test results for clarity, comprehensiveness, and accuracy.

### 1.2: Persona Research Prompt Iteration (P2, M) 
- [x] Refine prompt for generating persona viewpoints, arguments, and speaking styles (corresponds to `research_persona_async`).
- [x] Test with various persona types and complexities.
- [x] Evaluate research quality against PRD requirements (Section 4.2.3).
- [x] Iterate on prompt based on test results for depth, relevance, and nuance.
**Note: Completed through extensive testing and validation in MCP integration**

### 1.3: Podcast Outline Generation Prompt Iteration (P1, L) 
- [x] Refine 'Podcast Outline Generation' prompt from PRD 4.2.4 (corresponds to `generate_podcast_outline_async`).
- [x] Test with varying numbers of prominent persons, desired podcast lengths, and custom user outline prompts.
- [x] Evaluate outline structure, content prioritization, adherence to user inputs, and logical flow.
- [x] Iterate on prompt for improved topic coverage, speaker balance, and overall coherence.

### 1.4: Dialogue Writing Prompt Iteration (P1, XL) 
- [x] Refine 'Dialogue Writing' prompt from PRD 4.2.5.1 (corresponds to `generate_dialogue_async`).
- [x] Test with different outlines, persona research, prominent person details (including follower names/genders), and desired lengths.
- [x] Evaluate dialogue naturalness, speaker attribution, character consistency, engagement, and adherence to length.
- [x] Iterate on prompt for improved conversational flow, realism, and fulfillment of all dialogue requirements (e.g., disclaimers if prompted).

## Phase 8: Deployment & Security


### 1.1: Rate Limiting (P2, S)
- [ ] Implement IP-based rate limiting
- [ ] Add request throttling for expensive operations

### 1.2: HTTPS Configuration (P1, S)
- [ ] Ensure HTTPS for all endpoints
- [ ] Manage SSL certificates
- [ ] Configure secure headers

### 1.3: Final Testing (P1, M)
- [ ] Test all V1 features in production environment
- [ ] Test security measures and vulnerability scanning
- [ ] Load testing and performance validation

## Phase 9: Documentation & Polish

### 1.1: User Guide/FAQ (P3, S)
- [ ] Create user documentation for MCP integration
- [ ] Explain V1 limitations and features
- [ ] Document rate limits and file sizes
- [ ] Create troubleshooting guide

### 1.2: Code Cleanup (P3, M) 
- [x] Refactor test code for improved maintainability
  - [x] Refactor `test_podcast_workflow.py` to use fixtures and parameterized tests
  - [x] Refactor `test_content_extractor.py` to use class-based organization and utility methods
- [x] Refactor remaining application code
  - [x] Fix import paths for consistent execution across environments
  - [x] Add utility script for import path fixing
- [x] Add comprehensive comments
- [x] Document LLM interactions

### 1.3: Performance Monitoring (P2, M)
- [ ] Set up application monitoring and alerting
- [ ] Configure performance metrics collection
- [ ] Implement health check endpoints
- [ ] Add observability for production debugging

## 1.4: User Experience & Documentation (P1, S) 
- [x] Claude Desktop integration testing and validation 
  - [x] Basic podcast generation through Claude
  - [x] Status monitoring and polling
  - [x] Persona profile access and discussion
  - [x] Outline review and interaction
  - [x] File download and access patterns
- [x] Create user interaction templates and examples 
- [x] **NEW**: Claude.ai website integration documentation 
  - [x] Remote MCP server connection instructions
  - [x] Pro/Max user setup guide
  - [x] Enterprise/Team organization setup
  - [x] Example conversations and workflows
  - [x] Security and privacy considerations

{{ ... }}

## Phase 4: OAuth 2.0 Implementation

### Overview
OAuth 2.0 implementation focused on **2 specific clients**: Claude.ai and MySalonCast webapp. This simplified approach gets Claude.ai working quickly while supporting future expansion to additional LLMs (Gemini, ChatGPT, etc.) by adding client configurations incrementally.

### Architecture Strategy
- **Pre-configured clients** (no dynamic registration)
- **Simple client storage** (config file or in-memory)
- **Client-specific authorization flows** (auto-approve vs consent screen)
- **Minimal viable security** (expandable later)
- **Incremental expansion** (5 tasks per additional LLM)

### Task 1: Core OAuth Infrastructure (2-3 weeks)

#### 1.1: OAuth Discovery Endpoint (P1, S) 
- [✅] Implement `/.well-known/oauth-authorization-server`
- [✅] Return proper OAuth metadata for 2-client setup
- [✅] Include all required endpoint URLs
- [✅] Use dynamic base URL detection for production

### 1.2: Client Configuration System (P1, S) 
- [✅] Create 2-client configuration structure
- [✅] Pre-configure Claude.ai client credentials
- [✅] Pre-configure MySalonCast webapp client credentials
- [✅] Add client validation by client_id
- [✅] Support multiple redirect URIs per client

### 1.3: Authorization Endpoint (P1, M) 
- [✅] Implement `/auth/authorize` GET endpoint
- [✅] Validate client_id and redirect_uri against config
- [✅] Generate secure authorization codes (10min expiration)
- [✅] Handle state parameter for CSRF protection
- [ ] Create simple consent UI for webapp client
- [✅] Auto-approve Claude.ai client (skip consent)

### 1.4: Token Exchange Endpoint (P1, M) 
- [✅] Implement `/auth/token` POST endpoint
- [✅] Validate client credentials against configuration
- [✅] Exchange authorization codes for access tokens
- [✅] Generate secure access tokens (1hr expiration)
- [ ] Support PKCE verification (recommended for webapp)
- [✅] Return proper OAuth 2.0 token response

### 1.5: Token Validation & MCP Protection (P1, M) 
- [✅] Create token validation middleware
- [✅] Protect MCP endpoints with Bearer token auth
- [✅] Return 401 for missing/invalid tokens
- [✅] Maintain health endpoint accessibility
- [✅] Add token storage and cleanup

### Task 2: Client-Specific Features (1-2 weeks)

#### 2.1: Claude.ai Integration (P1, S) 
- [✅] Test OAuth discovery with Claude.ai
- [✅] Verify auto-approval flow works
- [✅] Test full Claude.ai → MCP workflow
- [✅] Document Claude.ai setup process
- [✅] Deploy and test in production

### 2.2: MySalonCast Webapp Integration (P2, M) 
- [ ] Design simple consent screen UI
- [ ] Implement authorization approval/denial
- [ ] Add CORS configuration for webapp domain
- [ ] Test webapp OAuth flow end-to-end
- [ ] Add basic scope validation (read/write)

### 2.3: Security & Configuration (P1, S) 
- [✅] Add OAuth settings to `app/config.py`
- [✅] Configure client secrets in environment variables
- [ ] Implement basic rate limiting on OAuth endpoints
- [✅] Add request validation and error handling
- [✅] Secure token generation with proper entropy

### Task 3: Testing & Deployment (1 week)

#### 3.1: OAuth Flow Testing (P1, S) 
- [✅] Create automated tests for OAuth flows
- [✅] Test Claude.ai client flow
- [✅] Test MySalonCast webapp client flow
- [✅] Test error conditions and edge cases
- [✅] Validate security measures

### 3.2: Production Deployment (P1, S) 
- [ ] Update deployment configuration with OAuth secrets
- [ ] Deploy OAuth endpoints to staging
- [ ] Test both clients against staging
- [ ] Deploy to production
- [ ] Monitor OAuth endpoint health

### 3.3: Documentation (P2, S) 
- [ ] Document 2-client OAuth architecture
- [ ] Create setup guides for both clients
- [ ] Add troubleshooting documentation
- [ ] Document expansion process for additional LLMs

## Future Expansion Strategy

### Adding Additional LLMs (5 tasks per LLM)
When adding Gemini, ChatGPT, or other LLMs:
- [ ] Research new LLM's OAuth requirements
- [ ] Add client configuration to config file
- [ ] Test OAuth flow with new LLM
- [ ] Update documentation
- [ ] Deploy updated configuration

### Example Client Configuration
```python
OAUTH_CLIENTS = {
    "claude-ai": {
        "client_secret": "env:CLAUDE_CLIENT_SECRET",
        "redirect_uris": ["https://claude.ai/oauth/callback"],
        "auto_approve": True,
        "scopes": ["mcp.read", "mcp.write"]
    },
    "mysaloncast-webapp": {
        "client_secret": "env:WEBAPP_CLIENT_SECRET",
        "redirect_uris": ["https://mysaloncast.com/oauth/callback"],
        "auto_approve": False,
        "scopes": ["mcp.read", "mcp.write", "admin"]
    }
}
```

## Success Criteria
- [ ] Claude.ai can complete full OAuth flow and access MCP tools
- [ ] MySalonCast webapp can authenticate and access MCP endpoints
- [ ] OAuth endpoints return proper error responses
- [ ] System can easily expand to support additional LLM clients
- [ ] All flows work in both staging and production environments

## Files to Create/Modify
- `app/mcp_server.py` - Add OAuth endpoints
- `app/oauth_config.py` - Client configuration (new file)
- `app/oauth_models.py` - OAuth data models (new file)
- `app/config.py` - Add OAuth environment settings
- `templates/oauth_consent.html` - Simple consent UI (new file)
- `requirements.txt` - Add OAuth dependencies

## Dependencies
- `authlib` - OAuth 2.0 implementation library
- `python-jose` - JWT token handling (if using JWT tokens)
- `jinja2` - Template rendering for consent UI

**Total Scope: ~40 tasks vs 170+ in comprehensive plan**
**Timeline: 4-6 weeks vs 3-4 months**
**Focus: Get Claude.ai working + scalable foundation**

## Phase 5: Deployment & Security


### 1.1: Rate Limiting (P2, S)
- [ ] Implement IP-based rate limiting
- [ ] Add request throttling for expensive operations

### 1.2: HTTPS Configuration (P1, S)
- [ ] Ensure HTTPS for all endpoints
- [ ] Manage SSL certificates
- [ ] Configure secure headers

### 1.3: Final Testing (P1, M)
- [ ] Test all V1 features in production environment
- [ ] Test security measures and vulnerability scanning
- [ ] Load testing and performance validation

## Phase 6: Documentation & Polish

### 1.1: User Guide/FAQ (P3, S)
- [ ] Create user documentation for MCP integration
- [ ] Explain V1 limitations and features
- [ ] Document rate limits and file sizes
- [ ] Create troubleshooting guide

### 1.2: Code Cleanup (P3, M) 
- [x] Refactor test code for improved maintainability
  - [x] Refactor `test_podcast_workflow.py` to use fixtures and parameterized tests
  - [x] Refactor `test_content_extractor.py` to use class-based organization and utility methods
- [x] Refactor remaining application code
  - [x] Fix import paths for consistent execution across environments
  - [x] Add utility script for import path fixing
- [x] Add comprehensive comments
- [x] Document LLM interactions

### 1.3: Performance Monitoring (P2, M)
- [ ] Set up application monitoring and alerting
- [ ] Configure performance metrics collection
- [ ] Implement health check endpoints
- [ ] Add observability for production debugging

## 1.4: User Experience & Documentation (P1, S) 
- [x] Claude Desktop integration testing and validation 
  - [x] Basic podcast generation through Claude
  - [x] Status monitoring and polling
  - [x] Persona profile access and discussion
  - [x] Outline review and interaction
  - [x] File download and access patterns
- [x] Create user interaction templates and examples 
- [x] **NEW**: Claude.ai website integration documentation 
  - [x] Remote MCP server connection instructions
  - [x] Pro/Max user setup guide
  - [x] Enterprise/Team organization setup
  - [x] Example conversations and workflows
  - [x] Security and privacy considerations

{{ ... }}

## Phase 7: LLM Prompt Iteration 

### 1.1: Source Analysis Prompt Iteration (P2, M) 
- [x] Refine prompt for extracting key themes, facts, and insights from source texts (corresponds to `analyze_source_text_async`).
- [x] Test with diverse source materials (PDFs, YouTube, URLs).
- [x] Evaluate quality of analysis against PRD requirements (Section 4.2.2).
- [x] Iterate on prompt based on test results for clarity, comprehensiveness, and accuracy.

### 1.2: Persona Research Prompt Iteration (P2, M) 
- [x] Refine prompt for generating persona viewpoints, arguments, and speaking styles (corresponds to `research_persona_async`).
- [x] Test with various persona types and complexities.
- [x] Evaluate research quality against PRD requirements (Section 4.2.3).
- [x] Iterate on prompt based on test results for depth, relevance, and nuance.
**Note: Completed through extensive testing and validation in MCP integration**

### 1.3: Podcast Outline Generation Prompt Iteration (P1, L) 
- [x] Refine 'Podcast Outline Generation' prompt from PRD 4.2.4 (corresponds to `generate_podcast_outline_async`).
- [x] Test with varying numbers of prominent persons, desired podcast lengths, and custom user outline prompts.
- [x] Evaluate outline structure, content prioritization, adherence to user inputs, and logical flow.
- [x] Iterate on prompt for improved topic coverage, speaker balance, and overall coherence.

### 1.4: Dialogue Writing Prompt Iteration (P1, XL) 
- [x] Refine 'Dialogue Writing' prompt from PRD 4.2.5.1 (corresponds to `generate_dialogue_async`).
- [x] Test with different outlines, persona research, prominent person details (including follower names/genders), and desired lengths.
- [x] Evaluate dialogue naturalness, speaker attribution, character consistency, engagement, and adherence to length.
- [x] Iterate on prompt for improved conversational flow, realism, and fulfillment of all dialogue requirements (e.g., disclaimers if prompted).

## Phase 8: Deployment & Security


### 1.1: Rate Limiting (P2, S)
- [ ] Implement IP-based rate limiting
- [ ] Add request throttling for expensive operations

### 1.2: HTTPS Configuration (P1, S)
- [ ] Ensure HTTPS for all endpoints
- [ ] Manage SSL certificates
- [ ] Configure secure headers

### 1.3: Final Testing (P1, M)
- [ ] Test all V1 features in production environment
- [ ] Test security measures and vulnerability scanning
- [ ] Load testing and performance validation

## Phase 9: Documentation & Polish

### 1.1: User Guide/FAQ (P3, S)
- [ ] Create user documentation for MCP integration
- [ ] Explain V1 limitations and features
- [ ] Document rate limits and file sizes
- [ ] Create troubleshooting guide

### 1.2: Code Cleanup (P3, M) 
- [x] Refactor test code for improved maintainability
  - [x] Refactor `test_podcast_workflow.py` to use fixtures and parameterized tests
  - [x] Refactor `test_content_extractor.py` to use class-based organization and utility methods
- [x] Refactor remaining application code
  - [x] Fix import paths for consistent execution across environments
  - [x] Add utility script for import path fixing
- [x] Add comprehensive comments
- [x] Document LLM interactions

### 1.3: Performance Monitoring (P2, M)
- [ ] Set up application monitoring and alerting
- [ ] Configure performance metrics collection
- [ ] Implement health check endpoints
- [ ] Add observability for production debugging

## 1.4: User Experience & Documentation (P1, S) 
- [x] Claude Desktop integration testing and validation 
  - [x] Basic podcast generation through Claude
  - [x] Status monitoring and polling
  - [x] Persona profile access and discussion
  - [x] Outline review and interaction
  - [x] File download and access patterns
- [x] Create user interaction templates and examples 
- [x] **NEW**: Claude.ai website integration documentation 
  - [x] Remote MCP server connection instructions
  - [x] Pro/Max user setup guide
  - [x] Enterprise/Team organization setup
  - [x] Example conversations and workflows
  - [x] Security and privacy considerations

{{ ... }}
