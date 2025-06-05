"""
String constants extracted from mcp_server.py for better maintainability.
All descriptions preserved exactly as originally written.
"""

PROMPT_DESCRIPTIONS = {
    "create_podcast_from_url": """Generates a prompt template for creating a podcast from one or more URLs with specific personas and length.
    
    Args:
        urls: List of source URLs to create a podcast from
        personas: Comma-separated list of personas/characters for the discussion
        length: Desired podcast length using a time string (e.g., "10 minutes")
    """,
    "discuss_persona_viewpoint": """Generate a prompt for exploring a persona's viewpoints from their research.
    
    Args:
        task_id: The podcast generation task ID
        person_id: The specific persona/person ID to explore
    """,
    "analyze_podcast_content": """Generates a prompt for analyzing different aspects of podcast content.
    
    Args:
        task_id: The podcast generation task ID  
        analysis_type: Type of analysis to perform
    """,
}

TOOL_DESCRIPTIONS = {
    "hello": """Returns a simple greeting.""",
    "generate_podcast_async": """
    Generate a podcast asynchronously using provided sources.
    Returns immediately with a task ID for status tracking.

    Args:
        ctx: MCP request context for correlation.
        source_urls: Optional list of article URLs.
        source_pdf_path: Optional PDF source path.
        prominent_persons: Optional list of personas to feature.
        custom_prompt: Optional custom instructions for the outline.
        podcast_length: Desired episode length string.
    """,
    "get_task_status": """
    Get the status of an async podcast generation task.
    
    Returns current status, progress percentage, and result when complete.
    
    Args:
        task_id: The task ID returned by generate_podcast_async
        
    Returns:
        Dict with status information and episode data when complete
    """,
    "cleanup_task_files": """
    Clean up files associated with a podcast generation task.
    
    Removes temporary files, audio segments, and LLM output files for the specified task
    based on the configured cleanup policy or optional override.

    Args:
        task_id: The ID of the podcast generation task to clean up.
        policy_override: Override default cleanup policy for this operation.
                         Options: "manual", "auto_on_complete", "auto_after_hours", 
                                  "auto_after_days", "retain_audio_only", "retain_all".
                                  
    Returns:
        A dictionary with cleanup status, files removed, and errors if any.
        Example: {"status": "success", "files_removed": 10, "errors": []}
    """,
    "configure_cleanup_policy": """
    Configure cleanup policies for MySalonCast file management.
    
    Updates the global cleanup configuration settings that control how and when
    temporary files are cleaned up after podcast generation.
    
    Args:
        default_policy: Default cleanup policy for new tasks.
        auto_cleanup_on_complete: Enable/disable auto cleanup when task completes.
        auto_cleanup_after_hours: Hours after completion to auto cleanup.
        auto_cleanup_after_days: Days after completion to auto cleanup.
        retain_audio_files: Retain final audio files.
        retain_transcripts: Retain final transcript files.
        retain_llm_outputs: Retain LLM output files (outlines, research).
        retain_audio_segments: Retain individual TTS audio segments.
        max_temp_size_mb: Maximum total size for temporary files.
        enable_background_cleanup: Enable/disable periodic background cleanup.
        
    Returns:
        A dictionary confirming the updated cleanup configuration.
    """,
    "get_service_health": """
    Get health and performance metrics for MySalonCast services.
    
    Returns current status and performance metrics for TTS service, task runner,
    and other critical components to help monitor service health in production.
    
    Args:
        include_details: Whether to include detailed performance metrics
    
    Returns:
        Dict with service health status and performance metrics
    """,
    "test_tts_service": """
    Test TTS service functionality and update health metrics.
    
    This tool is specifically for testing and validating TTS health monitoring.
    It triggers TTS operations within the MCP server process to update metrics.
    
    Args:
        text: Text to synthesize for testing.
        output_filename: Optional filename for the test audio output.
    
    Returns:
        Dict with TTS operation result and basic metrics
    """,
}

RESOURCE_DESCRIPTIONS = {
    "get_job_status_resource": """
    Get job status resource.
    Returns detailed status information for a podcast generation task.
    """,
    "get_job_logs_resource": """
    Get job logs resource.
    Returns structured log information for a podcast generation task.
    """,
    "get_job_warnings_resource": """
    Get job warnings resource.
    Returns warning and error information for a podcast generation task.
    """,
    "get_podcast_transcript_resource": """
    Get podcast transcript resource.
    Returns transcript content for a completed podcast.
    """,
    "get_podcast_audio_resource": """
    Get podcast audio resource.
    Returns audio file information for a completed podcast.
    """,
    "get_podcast_metadata_resource": """
    Get podcast metadata resource.
    Returns metadata for a completed podcast episode.
    """,
    "get_podcast_outline_resource": """
    Get podcast outline resource.
    Returns outline/structure information for a podcast episode.
    """,
    "get_persona_research_resource": """
    Get persona research resource for a specific person in a podcast generation task.
    Returns research data loaded from PersonaResearch JSON file.
    """,
    "get_cleanup_status_resource": """
    Get cleanup status and options for task files.
    Provides information about temporary files and cleanup policies.
    """,
    "get_cleanup_config_resource": """
    Get current cleanup configuration and policy settings.
    
    Returns the current cleanup policy configuration including default policies,
    retention settings, size limits, and background cleanup options.
    """,
}

MANIFEST_DESCRIPTIONS = {
    "SERVER_NAME": "MySalonCast MCP Server",
    "SERVER_DESCRIPTION": "AI-powered podcast generation platform with comprehensive content creation tools",
    "SERVER_VERSION": "1.0.0",
    "PROTOCOL_VERSION": "2024-11-05",
    "FEATURE_PODCAST_GENERATION": "Generate high-quality podcasts from various content sources",
    "FEATURE_CONTENT_ANALYSIS": "Analyze and extract insights from text, URLs, and documents",
    "FEATURE_PERSONA_RESEARCH": "Research and create detailed persona profiles",
    "FEATURE_VOICE_SYNTHESIS": "Multi-voice TTS with Google Cloud Text-to-Speech",
    "FEATURE_CLOUD_STORAGE": "Secure cloud storage for podcast assets",
    "FEATURE_WORKFLOW_MANAGEMENT": "End-to-end podcast creation workflow",
}
