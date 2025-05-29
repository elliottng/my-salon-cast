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
- [ ] Implement method for dialogue writing
- Manage API key securely
- Implement retry logic

### Task 1.5: Persona Research Logic (V1 Scope) (P1, M)
- Design prompts for persona research using Gemini's internal knowledge
- Process LLM output for views and speaking styles

### Task 1.6: TTS Service Wrapper (P1, M)
- Create Google Cloud Text-to-Speech wrapper
- Implement text-to-audio conversion
- Implement voice selection based on LLM characteristics

### Task 1.7: Core Podcast Generation Workflow (P1, L)
- Develop main workflow orchestration
- Handle intermediate data
- Implement source attribution
- Check for inappropriate content flag

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

## Phase 3: LLM Prompt Engineering

### Task 3.1: Source Analysis & Persona Research (P1, L)
- Develop prompts for text analysis
- Research personas using internal knowledge

### Task 3.2: Podcast Outline Generation Prompt (P1, M)
- Implement and refine 'Podcast Outline Generation' prompt from PRD 4.2.4
- Guide content prioritization
- Test outline generation with various inputs and persona combinations

### Task 3.3: Dialogue Writing (P1, XL)
- Develop prompts for conversational dialogue
- Target specified length
- Handle speaker attribution
- Implement disclaimer logic

### Task 3.4: Testing (P2, L)
- Test with various inputs
- Test disclaimer scenarios
- Test persona research
- Test prompt validation

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
