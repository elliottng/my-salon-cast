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
The output of this step will be one document per source, and one document per specified prominent person.

4.2.4. LLM Step 2: Outline Generation (Google Gemini 2.5 Pro):

LLM Prompt: Podcast Outline Generation
Role: You are an expert podcast script developer and debate moderator. Your primary objective is to create a comprehensive, engaging, and informative podcast outline based on the provided materials.

Overall Podcast Goals:

Educate: Clearly summarize and explain the key topics, findings, and information presented in the source documents for an audience of intellectually curious professionals.
Explore Perspectives: If prominent persons are specified, the podcast must clearly articulate their known viewpoints and perspectives on the topics, drawing from their provided persona research documents.
Facilitate Insightful Discussion/Debate: If these prominent persons have differing opinions, or if source materials present conflicting yet important viewpoints, the podcast should feature a healthy, robust debate and discussion, allowing for strong expression of these differing standpoints.
Inputs Provided to You:

Source Analysis Documents: [Assume these are provided, detailing key themes, arguments, and raw information extracted from each PDF/URL source. e.g., "Source1_Analysis.txt", "Source2_Analysis.txt"]
Persona Research Documents: [Assume these are provided if prominent persons were named, detailing their known views, characteristic speaking styles, and relevant opinions on topics likely to be in the source material. e.g., "PersonaA_Profile.txt", "PersonaB_Profile.txt"]
Desired Podcast Length: [User-specified, e.g., "7 minutes"]
Number of Prominent Persons Specified: [e.g., "2" or "0"]
Names of Prominent People Specified: [e.g., "Persona A, Persona B" or "None"]
Task: Generate a Podcast Outline

Create a detailed outline that structures the podcast. The outline should serve as a blueprint for the subsequent dialogue writing step.

Outline Structure Requirements:

Your outline must include the following sections, with specific content tailored to the inputs:

I. Introduction (Approx. 10-15% of podcast length)
A.  Opening Hook: Suggest a compelling question or statement to grab the listener's attention, related to the core topic.
B.  Topic Overview: Briefly introduce the main subject(s) to be discussed, derived from the source analyses.
C.  Speaker Introduction:
* If prominent persons are specified (based on "Names of Prominent People Specified"): Introduce them by name (e.g., "Today, we'll explore these topics through the synthesized perspectives of [Name of Persona A] and [Name of Persona B]..."). Indicate their general relevance or contrasting viewpoints if immediately obvious.
* If no persons are specified: Plan for a "Host" and an "Analyst/Expert" or similar generic roles.

II. Main Body Discussion Segments (Approx. 70-80% of podcast length)
* Divide the main body into 2-4 distinct thematic segments.
* For each segment:
1.  Theme/Topic Identification: Clearly state the specific theme or key question this segment will address (derived from source analyses).
2.  Core Information Summary: Outline the key facts, data, or educational points from the source documents that need to be explained to the listener regarding this theme.
3.  Persona Integration & Discussion (if prominent persons are specified):
a.  Initial Viewpoints: Plan how each named persona will introduce their perspective or initial thoughts on this theme, drawing from their corresponding persona research document.
b.  Points of Alignment/Conflict: Identify if this theme highlights agreement or disagreement between the named personas, or between a persona and the source material, or conflicting information between sources.
c.  Structuring Debate (if conflict/disagreement is identified):
* Outline a sequence for named personas to strongly express their differing viewpoints.
* Suggest moments for direct engagement (e.g., "[Name of Persona A] challenges [Name of Persona B]'s point on X by stating Y," or "How does [Name of Persona A]'s view reconcile with Source Document 2's finding on Z?").
* Ensure the debate remains constructive and focused on elucidating the topic for the listener.
d.  Supporting Evidence: Note key pieces of information or brief quotes from the source analysis documents that personas should reference to support their arguments or that the narrator should use for clarification.
4.  Presenting Conflicting Source Information (if no personas, or if relevant beyond persona debate): If the source documents themselves contain important conflicting information on this theme, outline how this will be presented and explored.

III. Conclusion (Approx. 10-15% of podcast length)
A.  Summary of Key Takeaways: Briefly recap the main educational points and the core arguments/perspectives discussed.
B.  Final Persona Thoughts (if prominent persons specified): Allow a brief concluding remark from each named persona, summarizing their stance or a final reflection.
C.  Outro: Suggest a closing statement.

Guiding Principles for Outline Content:

Educational Priority: The primary goal is to make complex information accessible and understandable. Persona discussions and debates should illuminate the topic.
Authentic Persona Representation: When personas are used, their contributions should be consistent with their researched views and styles, as detailed in their persona research documents. They should be guided to select and emphasize information aligning with their persona.
Natural and Engaging Flow: Even with debates, the overall podcast should feel conversational and engaging.
Length Adherence: The proposed structure and depth of discussion in the outline should be feasible within the target podcast length (approx. 150 words per minute of dialogue). Allocate rough timings or emphasis to sections.
Objectivity in Narration: When a narrator/host is explaining core information from sources, it should be presented objectively before personas offer their specific takes.
Output Format:

Provide the outline in a clear, hierarchical format (e.g., Markdown with headings and nested bullets).
Clearly indicate which named persona (or generic role) is intended to voice specific points or lead particular exchanges.


4.2.5. LLM Step 3: Dialogue Writing (Google Gemini 2.5 Pro):

The LLM writes the podcast dialogue based on the provided Podcast Outline Document (from LLM Step 2 / Section 4.2.4). It will also be provided with the Source Analysis Documents and Persona Research Documents (from LLM Step 1 / Section 4.2.3) for contextual reference and to accurately represent information and viewpoints. 

Style: Conversational, informative (accurately reflecting source information), entertaining, and viewpoint-driven (speakers express views consistent with researched personas or assigned roles). 
Speakers: A 'Host' role will always be present to guide the conversation, introduce topics from the outline, and provide narration.
If prominent persons are specified: 
In addition to the Host, there will be one speaker representing each specified prominent person.
Each representative speaker will be assigned a first name by the LLM. This name will begin with the same initial as the prominent person they represent (e.g., if 'Cardano Ada' is a specified prominent person, the representative speaker might be named 'Casey'; if 'Polkadot Gavin' is specified, 'Parker').
These representative speakers will be introduced by the Host, for example, as followers or advocates of the prominent person's known viewpoints (e.g., "Joining us is Casey, who will be sharing insights reflecting Cardano Ada's perspectives, and Parker, who will articulate viewpoints in line with Polkadot Gavin's known positions...").
Dialogue lines for these representatives should clearly reflect the researched viewpoints and characteristic speaking styles of the prominent individuals they follow, as detailed in their Persona Research Documents and cued in the Podcast Outline.
Attribution in the script will be to their assigned first name (e.g., "Casey:", "Parker:").
If no prominent persons are specified: 
The dialogue will primarily feature the 'Host' and may include one additional generic speaker role, such as 'Analyst' or 'Expert', if needed to present different facets of the information from the source documents, as guided by the outline. 
The tone will be informative and engaging. 
Speaker Gender Assignment for TTS: To ensure distinct voices for Text-to-Speech (TTS) conversion (as per Section 4.2.6), each speaker in the dialogue script will be assigned a gender characteristic ('Male' or 'Female') by the system. This assignment is primarily for vocal differentiation for the TTS service:
Host: The Host will be assigned a consistent gender characteristic by the system (e.g., a default such as 'Female' voice, or a gender chosen to contrast with other initial speakers).
Follower Speakers: Each follower speaker will be assigned a gender characteristic by the system (e.g., using an alternating pattern such as Follower 1: 'Male', Follower 2: 'Female') to promote vocal diversity. This assigned gender is independent of any inferred gender of the prominent person the follower represents. The LLM, when generating the follower's first name (as described above), should select a name congruent with this system-assigned gender.
Generic Speakers (e.g., 'Analyst'): If used, these speakers will also be assigned a gender characteristic by the system to ensure vocal distinction.
Clarity: Dialogue clearly indicates which speaker represents which prominent person's viewpoint (if applicable) or their assigned generic role. 
Length Adherence: The script's word count will target the user's specified duration (approx. 150 words/minute). 

4.2.5.1. Draft Dialogue Writing Prompt:

Based on all the provided inputs, write the full dialogue script.
Key Instructions & Guidelines:
Adherence to Outline:


The Podcast Outline Document is the primary source. Follow its structure, flow, assigned speakers for particular points, and integrate any specific instructions it contains (e.g., how to introduce topics, sequence debates, or reference evidence).
Ensure all thematic segments from the outline are covered in the dialogue. You have discretion to focus on more interesting themes at the expense of less interesting themes.
Dialogue Style:


Conversational & Engaging: The dialogue should flow naturally, like a real conversation. Avoid overly formal or robotic language.
Informative: Accurately reflect the key information from the Source Analysis Documents as guided by the outline.
Entertaining: Where appropriate and consistent with the topic and personas, inject elements that make the podcast enjoyable to listen to.
Viewpoint-Driven: Speakers, especially followers, must express views consistent with their researched personas or assigned roles. The dialogue should highly viewpoint diversity through healthy debate.
Speaker Roles & Dialogue:


Host:
The Host guides the conversation, introduces topics and segments as per the outline, provides necessary narration or summaries of source information, and facilitates discussions.
Ensure the Host's dialogue is clear and helps maintain the podcast's structure.
Follower Speakers (if prominent persons were specified):
Name Generation: For each follower speaker, you must generate a first name. This name MUST start with the provided Initial and MUST be congruent with the System-Assigned Gender provided for that follower. (e.g., If Initial is 'A' and System-Assigned Gender is 'Female', a name like 'Alice' or 'Anna' would be appropriate).
Introduction: The Host will introduce these speakers as followers/advocates of the prominent person's viewpoints (e.g., "Joining us is [Follower's Generated Name], who will be sharing insights reflecting [Prominent Person]'s perspectives...").
Content: Their dialogue must strongly and accurately reflect the viewpoints, opinions, and characteristic speaking style of the prominent person they represent, drawing from the Persona Research Document and as cued by the Podcast Outline.
Attribution: Ensure their lines are clearly attributable to their generated first name (e.g., "[Generated Follower Name]:").
Generic Speakers (if no prominent persons were specified):
If the outline includes roles like 'Analyst' or 'Expert' in addition to the Host, write their dialogue to be informative and engaging, fulfilling the purpose outlined for them.
Integrating Content & Discussions:


Seamlessly weave in facts, data, or educational points from the Source Analysis Documents when the outline calls for it.
If the outline details a debate or discussion between speakers, create dynamic and robust exchanges that allow for the strong expression of differing standpoints, while keeping the discussion constructive and focused.
Clarity of Representation:


The dialogue must make it clear which prominent person's viewpoint a follower represents, or what the role of a generic speaker is.
Length Adherence:


The total word count of the script should closely target the user's specified podcast duration, calculated at approximately 150 words per minute. You have discretion to manage the depth of discussion for each outline point accordingly.
Output Format Requirements:
Provide the output as a clean dialogue script.
Each line of dialogue must start with the speaker's name (e.g., "Host:", "[Generated Follower Name]:", "Analyst:") followed by a colon and then the spoken text.
Ensure clear delineation between speakers.



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
