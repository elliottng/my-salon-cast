# Product Requirements Document: "MySalonCast"
Version: 1.1 (V1 Scope with Terraform) Date: May 27, 2025 Author: Gemini AI Assistant Status: Draft

1. Introduction and Purpose
This document outlines the product requirements for "MySalonCast," a web application designed to convert PDF documents and web links into engaging, conversational audio podcasts. The application allows users to specify prominent individuals whose perspectives and speaking styles should influence the podcast content, offering an informative and entertaining way for intellectually curious professionals to consume information. This PRD is intended for the development team, including the LLM coding agent, to understand the scope and requirements of the Version 1 (V1) project.

2. Goals and Objectives
Primary Goal: Enable users to easily transform textual and web-based content (primarily PDFs and YouTube video transcripts for V1) into conversational audio podcasts.
Provide an engaging and entertaining alternative to reading, particularly for on-the-go consumption.
Allow users to experience content through the synthesized perspectives and styles of prominent individuals they admire or find interesting, based on the LLM's internal knowledge for V1.
Offer a simple, anonymous, and free-to-use service for a niche audience.
Empower users with a degree of control over the AI generation process by allowing modification of core LLM prompts.

3. Target Audience
Intellectually curious professionals seeking:
Efficient ways to consume articles, research papers (primarily as PDFs in V1), and video content.
Engaging and entertaining learning experiences.
Novel ways to explore topics through the lens of well-known personalities or experts.
A tool for personal learning and staying informed on diverse subjects.

4. Core Features and Functionality (V1 Scope)
4.1. Content Input
PDF Upload: Users can upload one PDF document per request.
URL Input: Users can provide up to three URLs per request.
For V1, primary URL support is for YouTube videos (for transcript extraction).
Other URLs (articles, research papers) will be processed on a best-effort basis, ideally expecting direct links to PDF documents or simple, easily parsable text if not YouTube links. Robust extraction of main content from general web articles is a V2 feature.
Prominent Person Specification (Optional): Users can specify the names of zero to three prominent persons. These names will be used to research their viewpoints and characteristic speaking styles (based on LLM's internal knowledge for V1) to influence the podcast dialogue.
UI: Three separate optional text input fields for prominent persons' names.
Podcast Length Definition: Users can define the desired approximate length of the podcast, with a maximum duration of ten minutes.
UI: A slider or dropdown menu to select duration (e.g., 2 mins, 5 mins, 7 mins, 10 mins).

4.2. Content Processing and Podcast Generation (V1 Scope)
4.2.1. Input Validation:
PDFs: Check for basic readability (not corrupted, text-extractable).
URLs: Validate for reachability (HTTP 200 OK).
Error Handling: If validation fails, display a clear error message (e.g., "PDF is corrupted or password-protected," "URL is not accessible or invalid") next to the respective input field, allowing the user to modify their inputs without losing other entered data.

4.2.2. Content Extraction (V1 Scope):
PDFs: Extract all selectable text.
URLs (YouTube): Attempt to fetch available official or auto-generated transcripts.
Other URLs (Articles/Papers - V1 Best Effort): For V1, direct extraction of main article content from general, complex HTML webpages is deferred. The system will attempt basic text extraction if content is easily accessible (e.g., plain text sites or direct PDF links). Users should be guided that PDF uploads or YouTube links are preferred for V1 for best results with other URLs.
Error Handling & User Notification:
Unreadable PDF: "Could not extract text from the provided PDF. It might be an image-only PDF or corrupted."
Missing YouTube Transcript: "No transcript available for the provided YouTube link. This source cannot be processed for audio content."
Paywalled Content: "Content at [URL] appears to be behind a paywall. Only publicly accessible content can be processed. If a limited preview is available, it may be used if substantial." If a snippet is too short (e.g., <200 words), treat as failed extraction for that source.
General URL Extraction Failure (V1): "Could not reliably extract content from [URL]. For best results in V1, please use PDF uploads or YouTube links."
General Extraction Failure: "Failed to extract content from [URL/PDF name]."
Multiple Source Synthesis & Prioritization: The LLM will be instructed to synthesize content from all successfully extracted sources. There is no default priority order for conflicting information. When prominent persons are specified, the LLM should guide them to select or emphasize information that aligns with their researched viewpoints and persona, fostering a natural and opinionated discussion.

4.2.3. LLM Step 1: Source Analysis & Persona Research (Google Gemini 2.5 Pro - V1 Scope):
The LLM (Google Gemini 2.5 Pro) analyzes the extracted textual content to identify key themes, arguments, and information.
If prominent persons are named, the LLM researches their publicly known views, opinions, and characteristic speaking styles relevant to the source material based on its internal training data for V1. Integration with an external live search API for persona research is a V2 feature.
Fallback for Persona Research: If sufficient information isn't found for a specified person (based on LLM's internal knowledge), a message like "Could not find enough information to distinctly model [Person's Name] using current knowledge. A generic 'Expert' persona will be used instead for this speaker" will be shown, and that slot will use a generic persona.

4.2.4. LLM Step 2: Briefing Document & Outline Generation (Google Gemini 2.5 Pro):
The LLM generates an internal briefing document summarizing key views and speaking styles of the named persons (if any).
The LLM brainstorms ideas based on the analyzed sources and these personas' views.
A rough outline for the podcast is created (e.g., intro, key point 1 with discussion, key point 2 with discussion, counter-arguments if applicable, conclusion).

4.2.5. LLM Step 3: Dialogue Writing (Google Gemini 2.5 Pro):
The LLM writes the podcast dialogue based on the outline.
Style: Conversational, informative (accurately reflecting source information), entertaining, and viewpoint-driven (speakers express views consistent with researched personas or assigned roles).
Speakers:
If prominent persons are specified, dialogue lines are attributed to them (e.g., "[Elon Musk]:", "[Oprah Winfrey]:").
If no persons are specified, dialogue is between 1-2 generic speakers (e.g., "Host:", "Analyst:", or "Narrator:"). The tone will be informative and engaging.
Clarity: Dialogue clearly indicates which speaker represents which persona/viewpoint.
Length Adherence: The script's word count will target the user's specified duration (approx. 150 words/minute).

4.2.6. Text-to-Speech (TTS) Conversion:
The generated dialogue script is converted into an audio file using Google Cloud Text-to-Speech AI API.
Voice Selection: Voice selection is fully automated based on the LLM's persona analysis from Step 1 and the briefing document from Step 2. The system will map described characteristics (e.g., gender, perceived age, tone) to appropriate, distinct standard voices from Google Cloud TTS in a best-effort manner. Users will have no direct control over voice selection.
Multiple Speakers: When multiple prominent persons are specified (or generic speakers are used), different, distinct voices will be automatically assigned to distinguish between them.

4.3. Output and Delivery
In-Browser Audio Playback: The generated audio podcast is playable directly within the web browser using a standard HTML5 audio player.
Audio Download: The audio podcast (e.g., MP3 format) is available for download by the user.
Transcript Display: The full transcript of the podcast dialogue is displayed alongside the audio player. Original sources used for generation will be listed at the end of the transcript.
Transcript Download: The transcript (e.g., .txt file), including source attribution at the end, is available for download.
No Preview Before Conversion: The content generation process is one-shot. Users will not be able to preview or edit the transcript before the audio is generated.

4.4. User Customization of LLM Prompts
Display of Default Prompts: The application will display the default, raw LLM prompts used for:
Source Analysis & Persona Research
Briefing Document & Outline Generation
Dialogue Writing
UI for Modification:
Prompts will be displayed in collapsible/expandable text areas (e.g., using <textarea>) below the main input form, perhaps under an "Advanced Settings" or "Customize AI Prompts" section.
Each prompt will have a "Reset to Default" button.
Users can edit these prompts before submitting the overall request.
Clear disclaimers should be provided about how modifying prompts can significantly affect output quality or lead to errors.
Implement client-side or server-side validation for modified prompts to check for basic syntax issues (e.g., unbalanced brackets if applicable to prompt structure) or excessive length. For example, display a warning if a prompt exceeds a defined character limit (e.g., 1000 characters) as overly long or malformed custom prompts might lead to API errors or significantly degraded generation quality.

4.5. User Flow
Landing and Input Page: The user accesses the web application, which presents a single page for all inputs.
Content Input (All on one page):
User optionally uploads one PDF document (drag-and-drop supported).
User optionally inputs up to three URLs in designated fields.
User optionally inputs the names of zero to three prominent persons in designated fields.
User selects the desired approximate podcast length (maximum ten minutes) using a slider or dropdown menu.
Advanced Settings - LLM Prompt Customization (Optional, on the same page):
User can click to expand an "Advanced Settings" or "Customize AI Prompts" section.
Default, raw LLM prompts for "Source Analysis & Persona Research," "Briefing Document & Outline Generation," and "Dialogue Writing" are displayed in collapsible/expandable text areas.
User can optionally modify one or more of these prompts directly within the text areas.
A "Reset to Default" button is available for each prompt.
Submission & Processing:
User clicks the "Generate Podcast" button.
Frontend performs basic client-side input validation (e.g., URL format, number of URLs, PDF file type and size up to 20MB).
The request (including any modified prompts) is sent to the backend.
The frontend will display key status updates to the user during processing (e.g., "Processing...", "Generating audio..."). Granular real-time updates are a V2 feature.
Results Display (On the same page or a new view):
Upon completion, the generated audio podcast is playable directly within the web browser using a standard HTML5 audio player.
A download button for the audio podcast (e.g., MP3 format) is available.
The full transcript of the podcast dialogue is displayed alongside the audio player. Original sources used for generation will be listed at the end of the transcript.
A download button for the transcript (e.g., .txt file), including source attribution, is available.
If any errors occurred during processing, clear error messages (as defined in Section 7) are displayed prominently, with guidance for V1 focused on common errors and retrying.
Users will not be able to preview or edit the transcript before the audio is generated.

5. Technical Specifications (V1 Scope)
Backend: Python (e.g., Flask or FastAPI).
Frontend: JavaScript (Vanilla JS or a lightweight framework like Vue.js/React if deemed necessary later, but prioritize simplicity), HTML5, CSS3.
Responsive Design: The web application must be responsive and usable on common desktop and mobile browser sizes.
LLM Interaction: All LLM operations will utilize Google Gemini 2.5 Pro via its API.
TTS API: Google Cloud Text-to-Speech AI API.
Search API for Persona Research: Not included in V1. See Section 17.

5.1. Suggested Libraries/Tools (for V1 consideration)
PDF Text Extraction (Python): PyPDF2 or pdfplumber.
Web Content Extraction (Python - for V1 limited URL support, e.g., YouTube): youtube-transcript-api. (Libraries like BeautifulSoup4 or newspaper3k for general scraping are more relevant for V2).
Backend Framework (Python): FastAPI or Flask.
Frontend Styling (Optional): Consider a utility-first CSS framework like Tailwind CSS for rapid responsive UI development.
PDF Malware Scanning (Python Backend): Deferred to V2.

6. User Authentication and PII
No User Accounts: User authentication will not be required.
No PII Storage: No personally identifiable information (PII) will be stored. The application will be anonymous to use.

7. Error Handling (General) (V1 Scope)
Beyond input validation and content extraction:
LLM API Errors: "Podcast generation failed due to an issue with the language model (Gemini 2.5 Pro). Please try again later or adjust your inputs/prompts."
TTS API Errors: "Audio generation failed. Please try again."
Search API Errors: (Not applicable for V1).
Content Generation Failures (Unexpected): "An unexpected error occurred during content generation. Please try again."
Exceeding Processing Limits (Internal): "The request is too complex or long to process with current settings. Please try reducing the number of sources or requested podcast length."
Graceful Handling (V1 Scope): The system should handle common errors gracefully, inform the user clearly. For V1, focus on preserving user input state for client-side validation errors. For complex backend failures, a generic error message with a suggestion to "try again with different inputs" is acceptable. More elaborate state preservation and recovery across all errors is a V2 feature.

7.1. Error Handling Matrix Example (V1 Scope)
This matrix provides examples of how different errors might be handled for V1, complementing the specific error messages defined elsewhere.
Stage	Typical Error	Example User Message (from existing PRD or new)	Proposed Action/UX Response (V1)	Relevant PRD Sections
Input Validation	Unreadable/Corrupted PDF	"PDF is corrupted or password-protected." / "Could not extract text from the provided PDF..."	Display error next to PDF input field; allow re-upload or removal of the PDF.	4.2.1, 4.2.2
URL not accessible/invalid	"URL is not accessible or invalid."	Display error next to the specific URL input field; allow correction or removal.	4.2.1
PDF Exceeds Size Limit (20MB)	"Uploaded PDF exceeds the 20MB size limit. Please upload a smaller file."	Prevent upload on client-side if possible; server-side rejection with clear message.	8
Content Extraction	Paywalled Content	"Content at [URL] appears to be behind a paywall..."	Inform user; proceed with other sources or allow user to remove/replace the problematic URL.	4.2.2
Missing YouTube Transcript	"No transcript available for the provided YouTube link..."	Inform user; proceed with other sources or allow removal of the YouTube link.	4.2.2
LLM Processing	Google Gemini 2.5 Pro API Error	"Podcast generation failed due to an issue with the language model (Gemini 2.5 Pro)..."	Inform user; suggest trying again later or modifying inputs/prompts.	7
Insufficient Persona Data (V1)	"Could not find enough information to distinctly model [Person's Name]..."	Inform user; confirm defaulting to a generic 'Expert' persona for that slot.	4.2.3
TTS Conversion	Google Cloud TTS API Error	"Audio generation failed. Please try again."	Inform user; suggest trying again. Potential to retry automatically once on backend.	7
System Limits	Exceeding URL/Persona Count	"Maximum 3 URLs allowed. Please remove extra URLs." / "Maximum 3 prominent persons allowed."	Client-side validation to prevent submission; server-side rejection if bypassed.	8
Content Policy	Potentially Inappropriate Content Generated	(No direct user error)	Prepend disclaimer to transcript as per section 13.2.	13.2

8. System Limitations (Hard Limits) (V1 Scope)
Maximum of three URLs per request.
Maximum podcast length of ten minutes.
Maximum of three prominent persons specified.
Uploaded PDF size limit: 20MB.

9. Data Management (Temporary Storage)
Uploaded Files (PDFs): Temporarily stored on the server filesystem or a cloud bucket (e.g., Google Cloud Storage - Standard or Nearline for cost, given infrequent access after initial processing).
Extracted Text & Intermediate LLM Outputs: May be stored in memory during a request or temporarily on disk/cache if too large.
Generated Content (Text Transcripts, Audio Files): Stored temporarily to allow user access for playback and download.
Retention Policy: All user-specific temporary data (uploaded PDFs, generated audio, transcripts) will be automatically deleted after 24 hours from creation. This provides a reasonable window for users to access their content. No permanent storage of user-submitted or generated content linked to a session beyond this window.
Mechanism: Cron job or scheduled task for cleanup.

10. Deployment
Deployment Platform: The application will be deployed on Google Cloud. Infrastructure components will be defined and managed using Terraform as an Infrastructure as Code (IaC) approach. The deployment process will involve applying these Terraform configurations to provision and update resources.
Database: Not explicitly required for core functionality due to no user accounts and temporary data storage. If simple caching or task queuing is needed, Redis or a similar in-memory store could be considered, or filesystem-based queuing for simplicity.

10.1. System Architecture Overview
The application will consist of the following key components, which will be defined and provisioned via Terraform configurations where applicable:
10.1.1. Frontend Client:
A responsive web interface built with HTML5, CSS3, and JavaScript.
Handles user input, client-side validation, submission of data to the backend API, and display of results including key status updates for V1.
Likely hosted as static assets (e.g., on Google Cloud Storage with a CDN) or served by a simple web server integrated with the backend.
10.1.2. Backend API Server:
A Python-based application (e.g., using FastAPI or Flask).
Deployed on a scalable platform like Google Cloud Run.
Responsible for:
Receiving and validating user requests.
Orchestrating the content processing pipeline.
Managing temporary file storage for uploads and generated content.
Interfacing with all external services (LLM, TTS for V1).
10.1.3. Content Processing Logic (Part of Backend):
Modules for extracting text from PDFs.
Modules for fetching and parsing content from YouTube transcripts (V1).
Logic for synthesizing information from multiple sources.
10.1.4. External Services (V1 Scope):
Google Gemini 2.5 Pro: For all LLM operations (source analysis, persona research using internal knowledge, outline generation, dialogue writing).
Google Cloud Text-to-Speech API: For converting the final dialogue script to audio.
10.1.5. Temporary Data Storage:
Google Cloud Storage will be used for temporary storage of uploaded PDF files, intermediate extracted text (if large), and final generated audio and transcript files.
Files will be subject to the 24-hour retention policy.
10.1.6. Basic Interaction Flow:
User interacts with the Frontend Client.
Frontend sends a request (PDF, URLs, persona names, custom prompts if any) to the Backend API Server.
Backend API validates inputs, stores any uploaded PDF in Temporary Data Storage.
Backend API executes Content Processing Logic, then makes sequential calls to Google Gemini 2.5 Pro API (for analysis, outline, dialogue), and Google Cloud Text-to-Speech API. (Web Search API calls are for V2).
Generated audio and transcript are stored in Temporary Data Storage.
Backend API returns URLs to the generated files (or the files themselves, depending on implementation) and the transcript text to the Frontend Client.
Frontend Client displays the results to the user. Key status updates are provided throughout backend processing for V1.

11. Security and Privacy (V1 Scope)
Handling Uploaded Content:
Treat all uploaded content as sensitive, even if anonymous.
Ensure secure transmission (HTTPS).
Restrict server-side access to these files.
Implement the data retention policy strictly.
Sanitize filenames and validate file types upon upload.
PDF Malware Scanning is deferred to V2.
Abuse Prevention:
Rate Limiting: Implement IP-based rate limiting to allow a maximum of 5 podcast generations per IP address per day.
Input Size Limits: Enforce PDF size limits (20MB) and potentially limits on the amount of text extracted from URLs.
Prompt Injection: While users can edit prompts, be aware of potential prompt injection if prompts are constructed by concatenating user input directly into critical instructions. The system should treat modifiable prompt sections as user input to the actual underlying system prompt which should have robust instructions.
LLM and TTS API Keys: Securely store and manage API keys. Do not expose them client-side.

12. Performance and Scalability (V1 Scope)
Expected Processing Times (Typical Inputs - e.g., 1 PDF of 10 pages, 1 YouTube link, 2 personas, 5-min podcast - V1 Scope):
Input Validation & Content Extraction: 5-30 seconds.
LLM Processing (Gemini 2.5 Pro, no external search for V1): 20 seconds - 2 minutes (may be slightly faster without search API integration).
TTS Conversion: 10-60 seconds.
Total: Aim for a typical generation time of 1-4 minutes for V1.
User Feedback (V1 Scope): The frontend will display key status updates to the user during the different stages of processing (e.g., "Processing your request...", "Generating dialogue...", "Converting to audio..."). Granular, real-time progress updates are a V2 feature.
Scalability:
Designed for a small user base (low hundreds).
Stateless backend design where possible to allow easy horizontal scaling of compute instances (e.g., on Cloud Run).
Asynchronous task processing for podcast generation is highly recommended for optimal UX, even in V1 if feasible within complexity limits.

13. Content Policy & Moderation
13.1. Content Restrictions: There will be no automated content filtering or topic restrictions imposed by the application on user-submitted source materials or on the topics users wish to explore.
13.2. Generated Content Disclaimer: If the LLM (Google Gemini 2.5 Pro), during dialogue generation, detects that its own output might contain potentially inappropriate, highly biased, or sensitive content, a standardized disclaimer will be automatically prepended to the beginning of the podcast transcript. The audio generation will still proceed. The disclaimer would read: "Disclaimer: This podcast is AI-generated. The content reflects information synthesized from the provided sources through the lens of the requested personas. It may contain viewpoints or interpretations that could be considered sensitive, controversial, or incomplete. Listener discretion is advised." The audio itself will not contain this disclaimer read out.

15. Key Dependencies (V1 Scope)
The successful development and operation of "MySalonCast" (V1) will rely on the following key external services and technologies:
15.1. External APIs:
Google Gemini 2.5 Pro API: Essential for all core natural language processing tasks, including source analysis, persona research augmentation (using internal knowledge for V1), outline generation, and dialogue writing. Requires an active Google Cloud project with the API enabled and appropriate credentials.
Google Cloud Text-to-Speech AI API: Required for converting the generated textual dialogue into audible speech. Requires an active Google Cloud project with the API enabled and appropriate credentials.
Web Search API: (Dependency for V2, not V1)
15.2. Cloud Platform & Services:
Google Cloud Platform: The chosen platform for deployment, including:
A compute service (e.g., Google Cloud Run) for hosting the backend API.
A storage service (Google Cloud Storage) for temporary file hosting (uploaded PDFs, generated audio/transcripts) and potentially Terraform state.
15.3. Backend Development Environment:
Python: The programming language for the backend application.
Associated Python libraries for web framework (e.g., FastAPI/Flask), PDF processing, YouTube transcript extraction, and API interactions (see Section 5.1 for suggestions).
15.4. Frontend Development Environment:
Standard web technologies: HTML5, CSS3, JavaScript.
15.5. (Potentially) YouTube Data API:
If a more robust method than web scraping or third-party libraries is required for fetching YouTube transcripts, direct use of the YouTube Data API might be considered, which would involve API quotas and compliance. For V1, simpler methods are preferred.
15.6. Infrastructure as Code Tooling:
Terraform CLI: For defining and provisioning Google Cloud infrastructure.

16. Future Considerations (Out of Scope for V1 or V2 unless specified in Sec 17)
User accounts for saving history or preferences.
More advanced voice customization (e.g., voice cloning, if ethically and technically feasible).
Support for more input types (e.g., DOCX, EPUB).
Direct integration with services like Pocket or Instapaper.
Sharing generated podcasts via unique links.
Language support beyond English.
Analytics on popular topics or personas (anonymized).

17. V2 and Beyond: Planned Future Requirements
This section outlines features and enhancements that are planned for implementation in Version 2 (V2) or later releases of "MySalonCast." The V1 architecture should be designed with consideration for the future integration of these capabilities where feasible.
17.1. Enhanced Persona Research via Web Search API:
Integrate an external web search API (e.g., Google Custom Search API) to provide the LLM with up-to-date, real-time information for researching prominent persons' views, opinions, and speaking styles, augmenting its internal knowledge base (currently in PRD section 4.2.3, 15.1 for reference).
17.2. Advanced Content Extraction from General URLs:
Implement robust functionality to extract the main textual content from a wide variety of general web articles and research paper URLs (beyond direct PDF links or simple text sites). This will involve more sophisticated parsing and scraping techniques (e.g., using libraries like BeautifulSoup4 and newspaper3k more extensively, as suggested in PRD section 5.1).
17.3. PDF Malware Scanning:
Integrate a malware scanning solution for uploaded PDF files (e.g., using ClamAV bindings or a cloud provider's service) to enhance security (currently in PRD section 11, 5.1 for reference).
17.4. Granular Real-Time Progress Updates:
Implement a more sophisticated system for providing users with granular, real-time progress updates during the podcast generation pipeline (e.g., using WebSockets or Server-Sent Events) (currently in PRD section 4.5, 12 for reference).
17.5. Elaborate Error Recovery and State Preservation:
Enhance error handling to more comprehensively preserve user input state across a wider range of backend processing errors, allowing users to more easily modify inputs and retry without losing their work (currently in PRD section 7 for reference).
17.6. User Accounts and History:
Introduce optional user accounts to allow users to save their generation history, preferences, and potentially store generated podcasts for longer than the anonymous 24-hour window.
