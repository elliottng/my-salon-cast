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

# Task 1.8: Model Context Protocol Server and API Implementation

## Task 1.8.1: FastAPI v.1 Extension (P1, L)
- [ ] Design the `app/main.py` FastAPI v.1 endpoints
- [ ] Implement the `app/main.py` FastAPI v.1 endpoints
- [ ] Extend existing `app/main.py` with FastAPI v.1 endpoints:
  - [ ] `POST /api/v1/podcasts/generate` (async job creation)
  - [ ] `GET /api/v1/podcasts/{id}/status` (progress monitoring - does this already exist? if not, let's not do it as an API)
  - [ ] `GET /api/v1/podcasts/{id}/audio` (file download)
  - [ ] `GET /api/v1/podcasts/{id}/transcript` (text download)

- [ ] Add rate limiting (IP-based, 5 requests/day for anonymous users)
- [ ] Integrate with existing `PodcastGeneratorService` workflow

## Task 1.8.2: Data Model Migration (P1, L)

### Phase 1: Extend PersonaResearch model in `app/podcast_models.py`
- [x] Add `invented_name: str` field
- [x] Add `gender: str` field
- [x] Add `tts_voice_id: str` field
- [x] Add `source_context: str` field
- [x] Add `creation_date: datetime` field

### Phase 2: Update `app/llm_service.py`
- [x] Modify `research_persona_async()` to assign invented names during creation
- [x] Implement deterministic gender assignment logic
- [x] Add Google TTS voice selection logic
- [x] Update PersonaResearch creation to populate new fields

### Phase 3: Migrate `app/podcast_workflow.py`
- [x] Remove temporary `persona_details_map` logic (~lines 180-220)
- [x] Update dialogue generation to use PersonaResearch model fields
- [x] Remove hardcoded name/gender assignment lists
- [x] Update TTS integration to use `PersonaResearch.tts_voice_id`

### Phase 4: Update dependent services
- [x] Modify `app/tts_service.py` to use PersonaResearch voice assignments
- [x] Update `app/audio_utils.py` DialogueTurn creation logic

### Phase 5: Create PodcastStatus model
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

### Phase 5.1: Add Status Updates Throughout Workflow (P1, M) 
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

### Phase 5.2: Create Status Check REST Endpoint (P1, S) 
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

### Phase 5.3: Add Status Persistence - Two-Stage Approach (P2, M)

#### Stage 1: Local Development with SQLite 
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

#### Stage 2: Production Deployment with Cloud SQL
- [ ] Document Cloud SQL setup process for PostgreSQL
- [ ] Create environment variable configuration (DATABASE_URL)
- [ ] Ensure SQLModel code works with both SQLite and PostgreSQL
- [ ] Add connection pooling for Cloud SQL
- [ ] Create database initialization scripts
- [ ] Add indexes for performance (task_id, created_at)
- [ ] Implement cleanup job for old tasks (30+ days)
- [ ] Handle database connection failures gracefully
- [ ] Document deployment configuration for GCP

### Phase 5.4: Implement True Async Processing (P2, L)
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

## Task 1.8.3: Direct FastMCP Implementation (P1, L)

### Phase 1.1: Install and Configure FastMCP 2.0 (P1, S) - COMPLETED
- [x] Install FastMCP 2.0: `pip install fastmcp`
- [x] Verify installation with `fastmcp version`
- [x] Update requirements.txt to include fastmcp
- [x] Create basic MCP server structure

### Phase 1.2: Create Base MCP Server Module (P1, M) - COMPLETED
- [x] Create `app/mcp_server.py` as the main MCP interface
- [x] Initialize FastMCP server with appropriate name and instructions
- [x] Set up proper logging and error handling
- [x] Create basic server lifecycle management

### Phase 1.3: Fix FastMCP Implementation - Core Setup (P1, S)
- [x] Fix FastMCP initialization to use single string parameter: `mcp = FastMCP("MySalonCast Podcast Generator")`
- [x] Remove incorrect `@mcp_server.on_event()` decorators (startup/shutdown)
- [x] Rename `mcp_server` to `mcp` throughout the file
- [x] Update `if __name__ == "__main__"` to use `mcp.app` instead of `mcp_server.app`
- [x] Add proper error handling patterns that return dicts instead of raising exceptions

### Phase 1.4: Async Tool Implementation (P1, L) - COMPLETED
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

### Phase 1.5: Resource Implementation (P1, M) - COMPLETED
- [x] Create `@mcp.resource("podcast://{task_id}/transcript")` for transcript access
- [x] Create `@mcp.resource("podcast://{task_id}/audio")` for audio file access
- [x] Create `@mcp.resource("podcast://{task_id}/metadata")` for episode metadata
- [x] Create `@mcp.resource("config://supported_formats")` for supported formats
- [x] Implement proper file path resolution from PodcastEpisode data
- [x] Handle file not found and invalid task_id cases

### Phase 1.6: End-to-End Testing of Async Tools (P1, M)
- [x] Test `generate_podcast_async` with various input combinations
- [ ] Test `generate_podcast_async_pydantic` with PodcastRequest models
- [x] Test `get_task_status` throughout generation lifecycle
- [x] Test resource access for completed podcasts
- [x] Test error handling for invalid inputs and failed generations
- [x] Create MCP client test scripts
- [x] Document any issues or improvements needed

### Phase 1.7: Sync Tool Implementation (P1, M)
- [ ] Create `@mcp.tool()` for `generate_podcast_sync`
  - [ ] Individual parameters matching async version
  - [ ] Call `await podcast_service.generate_podcast_from_source()`
  - [ ] Return complete episode data in dict format
- [ ] Create `@mcp.tool()` for `generate_podcast_sync_pydantic`
  - [ ] Accept PodcastRequest model directly
  - [ ] Same blocking behavior as individual params version
- [ ] Test sync tools with same scenarios as async

### Phase 1.8: Optional Enhancements (P2, S)
- [ ] Add `@mcp.prompt()` templates for common podcast generation requests
- [ ] Add progress callbacks to Context for real-time updates
- [ ] Create resource for listing all available tasks
- [ ] Add tool for cancelling in-progress tasks
- [ ] Consider adding webhook configuration via MCP

### Phase 2.1: Static Resources (P1, M)
- [x] Expose configuration as `@mcp.resource("config://app")`
- [x] Expose API documentation as `@mcp.resource("docs://api")`
- [x] Expose example requests as `@mcp.resource("examples://requests")`
- [x] Create resource for supported file formats

### Phase 2.2: Dynamic Resources - Podcast Data (P1, L)
- [ ] Create `@mcp.resource("podcast://{podcast_id}/transcript")` for transcripts
- [ ] Create `@mcp.resource("podcast://{podcast_id}/audio")` for audio files
- [ ] Create `@mcp.resource("podcast://{podcast_id}/outline")` for outlines

### Phase 2.3: Dynamic Resources - Job Status (P2, M)
- [ ] Create `@mcp.resource("jobs://{job_id}/status")` for generation progress status
- [ ] Create `@mcp.resource("jobs://{job_id}/logs")` for processing logs
- [ ] Create `@mcp.resource("jobs://{job_id}/warnings")` for warnings/errors
- [ ] Implement proper error handling for missing resources

### Phase 2.4: Dynamic Resources - LLM Outputs (P3, M)
- [ ] Create `@mcp.resource("research://{job_id}/{person_id}")` for persona research

### Phase 3.1: Core Prompt Templates (P2, M)
- [ ] Create `@mcp.prompt()` for podcast generation requests
- [ ] Create `@mcp.prompt()` for persona research prompts
- [ ] Include proper parameter validation and descriptions

### Phase 4.1: Service Integration (P1, L)
- [ ] Integrate with existing `PodcastGeneratorService`

### Phase 4.2: Model Compatibility (P1, M)
- [ ] Ensure MCP models work with existing Pydantic models
- [ ] If needed, create adapters for `PodcastRequest` → MCP tool parameters
- [ ] Maintain compatibility with `PodcastEpisode` output format
- [ ] If needed, handle type conversions between MCP and internal models

### Phase 4.3: File Management (P1, M)
- [ ] Integrate with existing temporary file management
- [ ] Expose generated audio files through MCP resources
- [ ] Handle cleanup of temporary directories appropriately
- [ ] Ensure proper file permissions and access

### Phase 5.1: MCP Context Integration (P1, M)
- [ ] Add Context parameter to tools for logging
- [ ] Implement progress reporting for podcast generation stages
- [ ] Add resource access for reading intermediate files
- [ ] Include request ID tracking for job correlation

### Phase 5.2: Error Handling and Validation (P1, M)
- [ ] Implement comprehensive error handling with ToolError/ResourceError
- [ ] Add input validation for all tool parameters
- [ ] Create meaningful error messages for clients
- [ ] Handle service initialization failures gracefully

### Phase 5.3: Authentication and Security (P2, M)
- [ ] Consider adding basic authentication if needed
- [ ] Implement rate limiting for resource-intensive operations
- [ ] Secure file access and temporary directory management
- [ ] Validate and sanitize all input parameters

### Phase 6.1: MCP-Specific Testing (P1, M)
- [ ] Create test suite for MCP tools using FastMCP Client
- [ ] Test resource access patterns
- [ ] Test prompt generation functionality
- [ ] Create integration tests with existing workflow

### Phase 6.2: Server Configuration (P1, S)
- [ ] Configure server for appropriate transport (stdio, HTTP)
- [ ] Set up proper logging levels
- [ ] Configure duplicate handling policies
- [ ] Set up custom error masking if needed

### Phase 6.3: Documentation and Examples (P2, S)
- [ ] Create usage examples for MCP clients
- [ ] Document available tools, resources, and prompts

### Phase 6.4: Deployment Integration (P1, M)
- [ ] Update existing deployment scripts to support MCP mode
- [ ] Create option to run as MCP server vs. HTTP API
- [ ] Ensure proper environment variable handling
- [ ] Test with actual MCP clients (Claude Desktop, etc.)

#### Implementation Notes

1. **Maintain Backward Compatibility**: Ensure existing HTTP API continues to work alongside MCP interface
2. **Leverage Existing Code**: Reuse as much of the current podcast generation logic as possible
3. **Progressive Implementation**: Start with core tools and add resources/prompts incrementally. Test along the way.
4. **Error Handling**: Implement comprehensive error handling for robust client experience
5. **Documentation**: Provide clear examples and documentation for MCP client integration
## Task 1.8.4: FastMCP Auto-Generation (P2, M)



## Task 1.8.5: Claude Desktop Integration (P1, M)

- [ ] Create MCP server entry point script for standalone execution
- [ ] Write Claude Desktop MCP configuration:
  - [ ] JSON configuration file
  - [ ] Environment variable setup
  - [ ] Installation and setup documentation
- [ ] Test end-to-end workflows:
  - [ ] Basic podcast generation through Claude
  - [ ] Status monitoring and polling
  - [ ] Persona profile access and discussion
  - [ ] Outline review and interaction
  - [ ] File download and access patterns
- [ ] Create user interaction templates and examples

## Task 1.8.6: Testing & Validation (P1, M)

### Create MCP client testing framework
- [ ] Tool invocation testing
- [ ] Resource access testing
- [ ] Prompt template validation

### Implement integration tests
- [ ] FastAPI ↔ MCP server integration
- [ ] Data model migration validation
- [ ] End-to-end podcast generation workflows

### Performance testing
- [ ] MCP server response times
- [ ] Status polling efficiency
- [ ] Resource access performance

### Documentation
- [ ] MCP server setup guide
- [ ] Claude Desktop integration guide
- [ ] Troubleshooting and debugging guide

## Task 1.8.7: Documentation & Deployment (P2, S)

- [ ] Update API documentation with new endpoints
- [ ] Create MCP server deployment guide
- [ ] Document data model migration process
- [ ] Update todo.md with future v.2 features (Wikipedia integration, standalone persona research)

---

**Total Estimated Effort:** ~6-8 weeks for complete implementation

**Critical Path:** Data model migration (Task 1.8.2) must complete before MCP implementation

### Task 1.9: Temporary File Management (P2, M)
- Implement temporary file storage
- Set up cleanup mechanism

### Task 1.10: Error Handling & Logging (P1, M)
- Implement error handling based on PRD
- Return appropriate HTTP status codes
- Set up logging

## Phase 2: Frontend Development

### Task 2.1: Basic HTML Structure & Styling (P1, M)
- Create responsive layout
- Style with Tailwind CSS
- Add input fields

### Task 2.2: JavaScript for Input Handling (P1, L)
- Implement client-side validation
- Handle PDF uploads
- Make API calls

### Task 2.3: UI for LLM Prompt Customization (P2, M)
- Create collapsible text areas
- Load default prompts
- Add reset functionality
- Implement validation

### Task 2.4: Displaying Results (P1, M)
- Integrate audio player
- Display transcript with disclaimer
- Add download buttons

### Task 2.5: User Feedback & Progress Indication (P1, M)
- Implement status updates
- Display error messages

## Phase 3: LLM Prompt Iteration

### Task 3.1: Source Analysis Prompt Iteration (P2, M)
- Refine prompt for extracting key themes, facts, and insights from source texts (corresponds to `analyze_source_text_async`).
- Test with diverse source materials (PDFs, YouTube, URLs).
- Evaluate quality of analysis against PRD requirements (Section 4.2.2).
- Iterate on prompt based on test results for clarity, comprehensiveness, and accuracy.

### Task 3.2: Persona Research Prompt Iteration (P2, M)
- Refine prompt for generating persona viewpoints, arguments, and speaking styles (corresponds to `research_persona_async`).
- Test with various persona types and complexities.
- Evaluate research quality against PRD requirements (Section 4.2.3).
- Iterate on prompt based on test results for depth, relevance, and nuance.

### Task 3.3: Podcast Outline Generation Prompt Iteration (P1, L)
- Refine 'Podcast Outline Generation' prompt from PRD 4.2.4 (corresponds to `generate_podcast_outline_async`).
- Test with varying numbers of prominent persons, desired podcast lengths, and custom user outline prompts.
- Evaluate outline structure, content prioritization, adherence to user inputs, and logical flow.
- Iterate on prompt for improved topic coverage, speaker balance, and overall coherence.

### Task 3.4: Dialogue Writing Prompt Iteration (P1, XL)
- Refine 'Dialogue Writing' prompt from PRD 4.2.5.1 (corresponds to `generate_dialogue_async`).
- Test with different outlines, persona research, prominent person details (including follower names/genders), and desired lengths.
- Evaluate dialogue naturalness, speaker attribution, character consistency, engagement, and adherence to length.
- Iterate on prompt for improved conversational flow, realism, and fulfillment of all dialogue requirements (e.g., disclaimers if prompted).

## Phase 4: Deployment & Security

### Task 4.1: Dockerize Application (P2, M)
- Create Dockerfiles
- Configure serving

### Task 4.2: Terraform Configurations (P1, L)
- Define Google Cloud resources
- Configure IAM roles
- Set up environment variables (sourcing sensitive values from Google Secret Manager)
- Configure network
- **Integrate Google Secret Manager for API keys and other sensitive data**
  - Provision Secret Manager via Terraform
  - Store API keys in Secret Manager
  - Update application to fetch secrets from Secret Manager in deployed environments

### Task 4.2.1: Initialize Terraform (P1, M)
- Run terraform init
- Run terraform plan
- Run terraform apply

### Task 4.3: Rate Limiting (P2, S)
- Implement IP-based rate limiting

### Task 4.4: HTTPS Configuration (P1, S)
- Ensure HTTPS
- Manage SSL certificates

### Task 4.5: Final Testing (P1, M)
- Test all V1 features
- Test security measures

## Phase 5: Documentation & Polish

### Task 5.1: User Guide/FAQ (P3, S)
- Create user documentation
- Explain V1 limitations
- Document rate limits and file sizes

### Task 5.2: Code Cleanup (P3, M)
- [x] Refactor test code for improved maintainability
  - [x] Refactor `test_podcast_workflow.py` to use fixtures and parameterized tests
  - [x] Refactor `test_content_extractor.py` to use class-based organization and utility methods
- [x] Refactor remaining application code
  - [x] Fix import paths for consistent execution across environments
  - [x] Add utility script for import path fixing
- [x] Add comprehensive comments
- [x] Document LLM interactions
