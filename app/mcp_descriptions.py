"""
String constants extracted from mcp_server.py for better maintainability.
All descriptions preserved exactly as originally written.
"""

PROMPT_DESCRIPTIONS = {
    "create_podcast_from_url": """Complete workflow guide for creating podcasts from URLs with specific personas.

🎯 WHEN TO USE:
- "Create a podcast from this URL"
- "I want [personas] to discuss this article"
- "Make a podcast about [topic] with [people]"

🔄 WORKFLOW:
1. Generate podcast with generate_podcast_async()
2. Monitor progress with get_task_status()
3. Access results via podcast resources
4. Analyze personas via research resources

📋 FEATURES:
- Multiple URLs and persona combinations
- Configurable length (5-18 minutes) and dialogue styles
- Step-by-step instructions with tool usage
- Resource access guidance for transcript, audio, metadata

Perfect for guided podcast creation from web content.""",

    "discuss_persona_viewpoint": """Focused exploration of persona research and viewpoints from completed podcast tasks.

🎯 WHEN TO USE:
- "Tell me about Einstein's perspective in task abc123"
- "What viewpoints does Marie Curie express?"
- "Explore the persona research for [person]"

🔍 ANALYSIS PROVIDED:
- Detailed persona research via research://task_id/person_id
- Background and expertise examination
- Viewpoint analysis and perspective exploration
- Historical context and accuracy assessment

📊 INSIGHTS:
- Key topics covered in persona profile
- Specific viewpoints expressed by historical figures
- How background influences their perspectives
- Potential questions they might raise

Ideal for educators and researchers understanding historical figure representation.""",

    "analyze_podcast_content": """Comprehensive analysis framework for examining completed podcast episodes.

🎯 WHEN TO USE:
- "Analyze my podcast abc123"
- "Break down the content structure"
- "Show me insights from this episode"

📊 ANALYSIS TYPES:
- outline: Structure and organization analysis
- transcript: Full dialogue and content review
- personas: Character research and authenticity
- summary: Overview with key metadata insights

🔍 EVALUATION:
- Key themes and topics identification
- Content structure and quality assessment
- Most interesting insights and discussion points
- Educational value and engagement factors

📋 DELIVERABLES:
- Thoughtful analysis with specific examples
- Quality ratings and recommendations
- Memorable quotes and highlights

Perfect for content creators and educators wanting detailed podcast evaluation.""",
}

TOOL_DESCRIPTIONS = {
    "hello": """Returns a simple greeting.""",
    "generate_podcast_async": """
Generate a podcast asynchronously from source materials with AI personas.

⭐ PRIMARY WORKFLOW ENTRY POINT - First step in podcast creation (2-8 minutes total)

WORKFLOW: Call this tool → get task_id → monitor with get_task_status() → access results via podcast:// resources

WHEN TO USE:
✅ "Create a podcast about [topic]"
✅ "Generate discussion between [person A] and [person B]"
✅ "Make podcast from this article"
✅ "I want [historical figures] to debate [topic]"

PARAMETERS:
- source_urls: News articles, research papers, Wikipedia (3-5 URLs optimal)
- prominent_persons: Historical figures like "Einstein", "Tesla" (2-4 works best)
- dialogue_style: "conversation" (collaborative), "debate" (opposing), "interview", "educational"
- podcast_length: "5 minutes" (quick), "7-10 minutes" (standard), "15+ minutes" (deep dive)

EXAMPLES:
Einstein + Newton debate relativity | Turing + Lovelace discuss AI | Sagan + Goodall on climate

TIMING: Short (2-4 min) | Medium (4-6 min) | Long (6-10 min)

RETURNS: task_id for monitoring with get_task_status()
    """,
    "get_task_status": """
    Get the status of an async podcast generation task.

    Returns current status, progress percentage, and result when complete.

    Args:
        task_id: The task ID returned by generate_podcast_async

    Returns:
        Dict with status information and episode data when complete
    """,
}

RESOURCE_DESCRIPTIONS = {
    "get_job_status_resource": """
🔍 ALWAYS AVAILABLE RESOURCE - Available immediately after generate_podcast_async()

WHEN TO USE:
✅ "Show me detailed status for task abc123"
✅ "What's the current progress?"
✅ "Give me technical details about the job"

CONTAINS:
- Current status and progress percentage
- Start/end timestamps
- Error information if failed
- Artifact availability flags

DIFFERENCE FROM get_task_status() TOOL:
- Tool: Better for monitoring, includes workflow guidance
- Resource: Raw data access, better for programmatic use

EXAMPLE RESPONSE:
{
    "task_id": "abc123",
    "status": "generating_dialogue",
    "progress_percentage": 65.0,
    "current_step": "Creating conversation between Einstein and Tesla",
    "start_time": "2024-01-15T10:30:00Z",
    "artifact_availability": {
        "source_analysis_complete": true,
        "podcast_outline_complete": true,
        "final_podcast_audio_available": false
    }
}
    """,
    "get_job_logs_resource": """
📋 ALWAYS AVAILABLE RESOURCE - Detailed execution logs and progress tracking

WHEN TO USE:
✅ "Show me the processing logs"
✅ "What steps have been completed?"
✅ "Debug why my podcast is taking so long"

CONTAINS:
- Timestamped log entries for each processing step
- Progress updates with detailed descriptions
- Sub-task completion status
- Performance timing data

LOG FORMAT:
"2024-01-15T10:32:15Z - [analyzing_sources] 15% - Source analysis complete"

EXAMPLE RESPONSE:
{
    "task_id": "abc123",
    "logs": [
        "2024-01-15T10:30:00Z - [queued] 0% - Podcast generation task queued",
        "2024-01-15T10:30:15Z - [preprocessing_sources] 5% - Content extracted",
        "2024-01-15T10:33:45Z - [researching_personas] 30% - Researching Einstein"
    ],
    "log_count": 12,
    "current_step": "researching_personas"
}
    """,
    "get_job_warnings_resource": """
⚠️ ALWAYS AVAILABLE RESOURCE - Issues, warnings, and error details

WHEN TO USE:
✅ "Are there any warnings or errors?"
✅ "Why did my podcast generation fail?"
✅ "What went wrong with task abc123?"

CONTAINS:
- Non-fatal warnings that didn't stop processing
- Error messages if task failed
- Content extraction issues
- Voice generation problems

WARNING TYPES:
- Content extraction warnings (some URLs failed)
- Persona research issues (person not found)
- Audio generation warnings (segments failed)

EXAMPLE RESPONSE:
{
    "task_id": "abc123",
    "warnings": [
        "Failed to extract content from URL https://example.com/broken-link",
        "TTS failed for turn 23: text too long, skipping audio"
    ],
    "warning_count": 2,
    "has_errors": false
}
    """,

    "get_podcast_transcript_resource": """Get the full transcript of a completed podcast episode.

📝 COMPLETION-REQUIRED RESOURCE - Only available after status="completed"

WHEN TO USE:
- "Show me the transcript" (after completion)
- "What did they talk about?"
- "Let me read the conversation"
- "What did Einstein say about relativity?"

CONTAINS:
- Complete dialogue with speaker labels
- Full conversation text from all personas
- Generated episode title and summary
- Character count for length assessment

FORMAT: Speaker-labeled dialogue (Host: Welcome... Einstein: Thank you...)

USE CASES:
- Content review before listening
- Text analysis and quote searching
- Sharing portions for social media
- Accessibility text alternative
- Research persona viewpoints

⚠️ PREREQUISITE: Always check get_task_status() first to confirm completion before accessing.""",

    "get_podcast_audio_resource": """Get audio file information for a completed podcast episode.

🎵 COMPLETION-REQUIRED RESOURCE - Only available after status="completed"

WHEN TO USE:
- "Where's the audio file?" (after completion)
- "I want to listen to my podcast"
- "Give me the MP3 file"
- "How do I download the audio?"

CONTAINS:
- Direct URL/path to final podcast audio file
- File size and format information (MP3, high-quality)
- Audio availability confirmation
- Download/streaming access details

FORMATS: MP3 for universal compatibility, typically 1MB per minute

USE CASES:
- Personal listening (stream/download)
- Sharing audio with others
- Publishing to podcast platforms
- Archiving for future reference
- Audio quality assessment

⚠️ PREREQUISITE: Audio generation is the final step - verify status="completed" first.""",

    "get_podcast_outline_resource": """Get the structural outline and segment organization of a completed podcast.

🗂️ COMPLETION-REQUIRED RESOURCE - Only available after status="completed"

WHEN TO USE:
- "Show me the podcast structure" (after completion)
- "What's the outline?"
- "How is the episode organized?"
- "What segments were created?"

CONTAINS:
- Detailed segment breakdown with topics
- Speaker assignments per segment
- Time allocations and pacing
- Content themes and focus areas
- Discussion flow organization

STRUCTURE: Introduction → Main Topics → Debates/Discussions → Conclusion

USE CASES:
- Content analysis and topic navigation
- Quality assessment of conversation flow
- Educational study of debate organization
- Production analysis of AI structure

⚠️ PREREQUISITE: Outline generated during creation - verify status="completed" first.""",

    "get_persona_research_resource": """Get detailed persona research for a specific person in a completed podcast.

🧠 COMPLETION-REQUIRED RESOURCE - Only available after status="completed"

WHEN TO USE:
- "Tell me about Einstein in this podcast"
- "What research was done on Tesla?"
- "How was [historical figure] characterized?"

PERSON_ID DISCOVERY: First get podcast://{task_id}/metadata to find available person_ids

CONTAINS:
- Comprehensive biographical information
- Historical context and core beliefs
- Speaking style and personality traits
- Topic expertise and viewpoints
- AI voice characteristics and settings

RESEARCH COMPONENTS:
- Biographical profile and accomplishments
- Viewpoints and philosophical positions
- Topic analysis and expertise areas
- Speaking style and communication patterns

USE CASES:
- Character understanding and dialogue analysis
- Educational research on historical figures
- Content validation of persona representation

⚠️ PREREQUISITE: Use exact person_id from metadata after verifying completion.""",
}

MANIFEST_DESCRIPTIONS = {
    "server_name": "MySalonCast MCP Server",
    "server_description": "AI-powered podcast generation platform with comprehensive content creation tools",
    "server_version": "0.1.0",
    "protocol_version": "2024-11-05",
    "feature_podcast_generation": "Generate high-quality podcasts from various content sources",
    "feature_content_analysis": "Analyze and extract insights from text, URLs, and documents",
    "feature_persona_research": "Research and create detailed persona profiles",
    "feature_voice_synthesis": "Multi-voice TTS with Google Cloud Text-to-Speech",
    "feature_cloud_storage": "Secure cloud storage for podcast assets",
    "feature_workflow_management": "End-to-end podcast creation workflow",
}
