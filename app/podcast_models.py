import json
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

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
    llm_persona_research_paths: Optional[List[str]] = None
    llm_podcast_outline_path: Optional[str] = None
    llm_dialogue_turns_path: Optional[str] = None

