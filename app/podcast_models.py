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
    Simplified profile of a prominent person identified in the source material.
    """
    person_id: str = Field(..., description="A unique identifier for the person (e.g., a slugified name).")
    name: str = Field(..., description="The full name of the prominent person.")
    detailed_profile: str = Field(..., description="A comprehensive textual profile of the person, summarizing their viewpoints, inferred speaking style, and any notable quotes or statements derived from the source text.")

class OutlineSegment(BaseModel):
    """
    A single segment or section of the podcast outline.
    """
    segment_id: str = Field(..., description="Unique identifier for this segment.")
    segment_title: Optional[str] = Field(default=None, description="The title or topic of this podcast segment.")
    speaker_id: str = Field(..., description="Identifier for the speaker (e.g., 'Host', 'Persona_JohnDoe', 'Narrator').")
    content_cue: str = Field(..., description="A brief cue or summary of the content to be covered in this segment.")
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

