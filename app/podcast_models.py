import json
from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

class PodcastRequest(BaseModel):
    """Request model for podcast generation."""
    source_urls: Optional[List[str]] = None  # Support for multiple source URLs
    source_pdf_path: Optional[str] = None
    prominent_persons: Optional[List[str]] = None
    desired_podcast_length_str: Optional[str] = None
    custom_prompt_for_outline: Optional[str] = None
    host_invented_name: Optional[str] = None  # Added for host persona customization
    host_gender: Optional[str] = None  # Added for host persona customization
    custom_prompt_for_dialogue: Optional[str] = None  # Added for dialogue generation customization
    webhook_url: Optional[str] = None  # Webhook URL for completion callbacks
    
    @property
    def has_valid_sources(self) -> bool:
        """Check if the request has at least one valid source."""
        return (self.source_urls and len(self.source_urls) > 0) or (self.source_pdf_path is not None)

class SourceAnalysis(BaseModel):
    """
    Simplified structured analysis of the source text.
    """
    summary_points: List[str] = Field(..., description="Key summary points from the source text, as a list of strings.")
    detailed_analysis: str = Field(..., description="A more detailed, free-form textual analysis of the source content.")

class PersonaResearch(BaseModel):
    """
    Profile of a prominent person identified in the source material.
    Extended with additional fields for MCP integration.
    """
    person_id: str = Field(..., description="A unique identifier for the person (e.g., a slugified name).")
    name: str = Field(..., description="The full name of the prominent person.")
    detailed_profile: str = Field(..., description="A comprehensive textual profile of the person, summarizing their viewpoints, inferred speaking style, and any notable quotes or statements derived from the source text.")
    
    # MCP integration extensions - all optional with defaults
    invented_name: Optional[str] = Field(None, description="An assigned podcast speaker name (may differ from historical name)")
    gender: Optional[str] = Field(None, description="Assigned gender for TTS voice selection (Male, Female, or Neutral)")
    tts_voice_id: Optional[str] = Field(None, description="The specific TTS voice identifier assigned to this persona")
    tts_voice_params: Optional[dict] = Field(None, description="Additional TTS voice parameters including speaking_rate and pitch")
    source_context: Optional[str] = Field(None, description="The context or source material this persona was researched from")
    creation_date: Optional[datetime] = Field(None, description="When this persona research was created")

class OutlineSegment(BaseModel):
    """
    A single segment or section of the podcast outline.
    """
    segment_id: str = Field(..., description="Unique identifier for this segment.")
    segment_title: Optional[str] = Field(default=None, description="The title or topic of this podcast segment.")
    speaker_id: str = Field(..., description="Identifier for the speaker (e.g., 'Host', 'Persona_JohnDoe', 'Narrator').")
    content_cue: str = Field(..., description="A brief cue or summary of the content to be covered in this segment.")
    target_word_count: Optional[int] = Field(default=None, description="Target number of words for this segment's dialogue.")
    estimated_duration_seconds: Optional[int] = Field(default=None, description="Estimated duration for this segment in seconds.")

class DialogueTurn(BaseModel):
    """
    A single turn of dialogue in the podcast script.
    """
    turn_id: int = Field(..., description="Sequential ID for this turn of dialogue.")
    speaker_id: str = Field(..., description="Identifier for the speaker (e.g., 'Host', 'Persona_JohnDoe', 'Narrator').")
    speaker_gender: Optional[str] = Field(default=None, description="Gender of the speaker (e.g., 'Male', 'Female', 'Neutral'), used for TTS voice selection.")
    text: str = Field(..., description="The dialogue text for this turn.")
    source_mentions: Optional[List[str]] = Field(default_factory=list, description="List of source materials or facts referenced in this turn, for attribution. Defaults to an empty list if not provided.")

class PodcastOutline(BaseModel):
    """
    The overall structure of the podcast.
    """
    title_suggestion: str = Field(..., description="Suggested title for the podcast episode.")
    summary_suggestion: str = Field(..., description="Suggested brief summary for the podcast episode.")
    segments: List[OutlineSegment] = Field(..., description="List of podcast segments in order.")
    
    def format_for_display(self, format_type: str = "text") -> str:
        """
        Format the podcast outline for display in various formats.
        
        Args:
            format_type: The format to use ("text", "markdown", or "json")
            
        Returns:
            A formatted string representation of the podcast outline
        """
        if format_type == "json":
            return json.dumps(self.model_dump(), indent=2)
            
        # Calculate total duration
        total_duration_seconds = sum(segment.estimated_duration_seconds or 0 for segment in self.segments)
        total_minutes = total_duration_seconds // 60
        total_seconds = total_duration_seconds % 60
        
        if format_type == "markdown":
            lines = []
            lines.append(f"# {self.title_suggestion}")
            lines.append(f"")
            lines.append(f"**Summary**: {self.summary_suggestion}")
            lines.append(f"")
            lines.append(f"**Total Duration**: {total_minutes} min {total_seconds} sec ({total_duration_seconds} seconds)")
            lines.append(f"**Number of Segments**: {len(self.segments)}")
            lines.append(f"")
            lines.append(f"## Segments")
            
            for i, segment in enumerate(self.segments, 1):
                duration_min = (segment.estimated_duration_seconds or 0) // 60
                duration_sec = (segment.estimated_duration_seconds or 0) % 60
                
                lines.append(f"### {i}. {segment.segment_title or 'Untitled Segment'} ({duration_min}:{duration_sec:02d})")
                lines.append(f"**ID**: `{segment.segment_id}`")
                lines.append(f"**Speaker**: {segment.speaker_id}")
                if segment.target_word_count:
                    lines.append(f"**Target Word Count**: {segment.target_word_count} words")
                lines.append(f"**Duration**: {duration_min} min {duration_sec} sec ({segment.estimated_duration_seconds} seconds)")
                lines.append(f"")
                lines.append(f"**Content**:")
                lines.append(f"{segment.content_cue}")
                lines.append(f"")
            
            return "\n".join(lines)
        
        # Default to text format
        lines = []
        lines.append(f"Title: {self.title_suggestion}")
        lines.append(f"Summary: {self.summary_suggestion}")
        lines.append(f"Total Duration: {total_minutes} min {total_seconds} sec ({total_duration_seconds} seconds)")
        lines.append(f"Number of Segments: {len(self.segments)}")
        lines.append("")
        lines.append("SEGMENTS:")
        lines.append("-" * 80)
        
        for i, segment in enumerate(self.segments, 1):
            duration_min = (segment.estimated_duration_seconds or 0) // 60
            duration_sec = (segment.estimated_duration_seconds or 0) % 60
            
            lines.append(f"{i}. {segment.segment_title or 'Untitled Segment'} ({duration_min}:{duration_sec:02d})")
            lines.append(f"   ID: {segment.segment_id}")
            lines.append(f"   Speaker: {segment.speaker_id}")
            if segment.target_word_count:
                lines.append(f"   Target Word Count: {segment.target_word_count} words")
            lines.append(f"   Duration: {duration_min} min {duration_sec} sec ({segment.estimated_duration_seconds} seconds)")
            lines.append(f"   Content:")
            
            # Indent content for readability
            content_lines = segment.content_cue.split("\n")
            for content_line in content_lines:
                lines.append(f"     {content_line}")
            
            lines.append("-" * 80)
        
        return "\n".join(lines)


class PodcastEpisode(BaseModel):
    title: str
    summary: str
    transcript: str
    audio_filepath: str
    source_attributions: List[str]
    warnings: List[str]
    llm_source_analysis_paths: Optional[List[str]] = None
    # Path or Cloud URL to persona research JSON files (supports both local paths and GCS URLs)
    llm_persona_research_paths: Optional[List[str]] = None
    # Path or Cloud URL to podcast outline JSON file (supports both local paths and GCS URLs)
    llm_podcast_outline_path: Optional[str] = None
    llm_dialogue_turns_path: Optional[str] = None
    dialogue_turn_audio_paths: Optional[List[str]] = None  # Individual audio segment paths
    
    def is_cloud_path(self, path: str) -> bool:
        """Check if a path is a cloud URL (GCS, HTTP, or HTTPS)."""
        return path.startswith(('gs://', 'http://', 'https://'))
    
    def has_cloud_outline(self) -> bool:
        """Check if podcast outline is stored in cloud storage."""
        return self.llm_podcast_outline_path and self.is_cloud_path(self.llm_podcast_outline_path)
    
    def has_cloud_persona_research(self) -> bool:
        """Check if any persona research files are stored in cloud storage."""
        if not self.llm_persona_research_paths:
            return False
        return any(self.is_cloud_path(path) for path in self.llm_persona_research_paths)
    
    def get_cloud_research_count(self) -> int:
        """Get count of persona research files stored in cloud storage."""
        if not self.llm_persona_research_paths:
            return 0
        return sum(1 for path in self.llm_persona_research_paths if self.is_cloud_path(path))
    
    def get_local_research_count(self) -> int:
        """Get count of persona research files stored locally."""
        if not self.llm_persona_research_paths:
            return 0
        return sum(1 for path in self.llm_persona_research_paths if not self.is_cloud_path(path))


# --- Asynchronous Task Management Models ---

class PodcastTaskCreationResponse(BaseModel):
    """
    Response model for the immediate acknowledgment of a podcast generation task.
    """
    task_id: str = Field(..., description="Unique identifier for the podcast generation task.")
    status: Literal["queued"] = Field(default="queued", description="Initial status of the task, always 'queued' on creation.")
    message: str = Field(default="Podcast generation task has been successfully queued.", description="A human-readable message.")
    queued_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the task was queued (UTC).")

    class Config:
        use_enum_values = True


PodcastProgressStatus = Literal[
    "queued",
    "preprocessing_sources",
    "analyzing_sources",
    "researching_personas",
    "generating_outline",
    "generating_dialogue",
    "generating_audio_segments",
    "stitching_audio",
    "postprocessing_final_episode",
    "completed",
    "failed",
    "cancelled"
]


class ArtifactAvailability(BaseModel):
    """
    Tracks the availability of various intermediate and final artifacts generated during podcast creation.
    """
    source_content_extracted: bool = Field(default=False, description="Source materials downloaded and text extracted.")
    source_analysis_complete: bool = Field(default=False, description="Source material analysis artifacts available.")
    persona_research_complete: bool = Field(default=False, description="Persona research artifacts available.")
    podcast_outline_complete: bool = Field(default=False, description="Podcast outline artifact available.")
    dialogue_script_complete: bool = Field(default=False, description="Full dialogue script artifact available.")
    individual_audio_segments_complete: bool = Field(default=False, description="Individual dialogue turn audio segments generated.")
    final_podcast_audio_available: bool = Field(default=False, description="Final stitched podcast audio MP3 available.")
    final_podcast_transcript_available: bool = Field(default=False, description="Final full transcript (from dialogue) available.")


class PodcastStatus(BaseModel):
    """
    Comprehensive model for tracking the status and progress of an asynchronous podcast generation task.
    """
    task_id: str = Field(..., description="Unique identifier for the podcast generation task.")
    status: PodcastProgressStatus = Field(default="queued", description="Current detailed status of the podcast generation task.")
    status_description: Optional[str] = Field(None, description="Human-readable description of the current status or step.")
    progress_percentage: float = Field(default=0.0, ge=0, le=100, description="Overall progress percentage (0-100).")
    
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the task was created/queued (UTC).")
    last_updated_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp when the status was last updated (UTC).")
    
    # Using Any for request_data to avoid direct import of PodcastRequest from app.podcast_workflow here,
    # which can lead to circular dependencies. The actual type is app.podcast_workflow.PodcastRequest.
    request_data: Optional[Any] = Field(None, description="The original PodcastRequest data that initiated this task.")
    
    # PodcastEpisode is defined in this file. Using string literal for robustness against definition order.
    result_episode: Optional['PodcastEpisode'] = Field(None, description="The final PodcastEpisode object if generation is successful.")
    
    error_message: Optional[str] = Field(None, description="A summary of the error, if the task failed.")
    error_details: Optional[str] = Field(None, description="Detailed error information (e.g., a traceback snippet), if the task failed.")
    
    logs: List[str] = Field(default_factory=list, description="A list of key log messages or events during the task execution.")
    artifacts: ArtifactAvailability = Field(default_factory=ArtifactAvailability, description="Status of various generated artifacts.")

    class Config:
        use_enum_values = True # Ensures Literal values are used as strings

    def update_status(self, new_status: PodcastProgressStatus, description: Optional[str] = None, progress: Optional[float] = None):
        """Helper method to update status, progress, and last_updated_at timestamp."""
        self.status = new_status
        if description is not None:
            self.status_description = description
        if progress is not None:
            self.progress_percentage = min(max(progress, 0.0), 100.0) # Clamp progress to 0-100
        self.last_updated_at = datetime.utcnow()
        self.logs.append(f"{self.last_updated_at.isoformat()}Z - Status: {self.status}, Progress: {self.progress_percentage:.1f}%, Description: {self.status_description or 'N/A'}")
