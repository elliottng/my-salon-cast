from typing import List, Optional
from pydantic import BaseModel, Field

class SourceAnalysis(BaseModel):
    """
    Structured analysis of the source text.
    """
    key_themes: List[str] = Field(..., description="List of key themes identified in the source text.")
    facts: List[str] = Field(..., description="List of important facts extracted from the source text.")
    summary_points: Optional[List[str]] = Field(default=None, description="Bulleted or numbered summary points from the source text.")
    potential_biases: Optional[List[str]] = Field(default=None, description="Potential biases identified in the source text.")
    counter_arguments_or_perspectives: Optional[List[str]] = Field(default=None, description="Counter arguments or alternative perspectives found.")

class PersonaResearch(BaseModel):
    """
    Detailed profile of a prominent person identified in the source material.
    """
    person_id: str = Field(..., description="A unique identifier for the person (e.g., a slugified name).")
    name: str = Field(..., description="The full name of the prominent person.")
    viewpoints: List[str] = Field(..., description="Key viewpoints, opinions, or arguments associated with this person from the source text.")
    speaking_style: Optional[str] = Field(default=None, description="Observed or inferred speaking style (e.g., 'analytical', 'passionate', 'cautious').")
    key_quotes: Optional[List[str]] = Field(default=None, description="Direct memorable quotes from this person in the source text, if any.")

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

