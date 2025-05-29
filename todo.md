# Detailed To-Do List for LLM Coding Agent (Aligned with MySalonCast PRD Version 1.1 - V1 Scope with Terraform)

This to-do list is broken down for a single LLM coding agent, focusing on actionable development tasks. Priorities are suggested (P1 = High, P2 = Medium, P3 = Low). Effort is relative (S = Small, M = Medium, L = Large, XL = Extra Large).

## Phase 1: Backend Core Logic & API Endpoints

### Task 1.1: Setup Project & Environment (P1, S) ✓
- [x] Initialize Python project (e.g., Flask/FastAPI)
- [x] Set up virtual environment and install basic dependencies
- [x] Structure project directories
- [x] Install Terraform CLI
- [x] Set up Terraform state backend

### Task 1.2: Input Validation Module (P1, M) ✓
- [x] Define validation rules for PDF uploads (file type, size limits)
- [x] Define validation rules for URL inputs (format, accessibility)
- [x] Implement validation logic in FastAPI endpoints
- [x] Unit tests for validation functions
- [x] Error handling and user feedback

### Task 1.3: Content Extraction Service (V1 Scope) (P1, L)
- [x] Implement PDF text extraction
- [x] Implement YouTube transcript fetching
- [x] Implement best-effort text extraction for simple URLs
- [x] Unit tests for content extraction functions
- [x] Basic error handling for failed extractions
- [x] Handle errors gracefully

### Task 1.4: LLM Interaction Service Wrapper (P1, M)
- Create Google Gemini 2.5 Pro API wrapper
- [x] Implement method for source analysis
- [x] Implement method for persona research
- [x] Implement method for podcast outline generation (Ref: PRD 4.2.4 detailed prompt)
- [x] Implement method for dialogue writing
- [x] Manage API key securely
- [x] Implement retry logic

### Task 1.6: TTS Service Wrapper (P1, M) ✓
- [x] Create Google Cloud Text-to-Speech wrapper
- [x] Implement text-to-audio conversion
- [x] Implement voice selection based on LLM characteristics

### Task 1.7: Core Podcast Generation Workflow (P1, L)
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
- [ ] Implement LLM-driven detailed podcast outline generation (multi-segment).
- [ ] Refine LLM dialogue writing to iterate through outline segments, producing `DialogueTurn` objects.
- [ ] Implement audio stitching of multiple `DialogueTurn` audio segments using `pydub`.
- [ ] Enhance transcript generation by concatenating text from `DialogueTurn` objects.
- [ ] Implement detailed source attribution: LLM-provided mentions compiled into `PodcastEpisode.source_attributions` and appended to transcript.
- [ ] Implement robust content flag checking based on LLM safety ratings, populating `PodcastEpisode.warnings`.
- [ ] Implement serialization of all specified intermediate LLM outputs (source analysis, persona research, outline, dialogue turns) to temp JSON files.
- [ ] Ensure `PodcastEpisode` includes file paths to all serialized intermediate LLM outputs.
- [ ] Improve PDF content extraction to correctly handle file paths (currently expects `UploadFile`).

### Task 1.8: API Endpoint Definition (P1, M)
- Design and implement main API endpoint
- Include validation for custom prompts
- Handle file uploads and responses

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
- Refactor code
- Add comments
- Document LLM interactions
