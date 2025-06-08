## Design Document: Core Podcast Generation Workflow (Revised)

**1. Overview & Goals**

The Core Podcast Generation Workflow orchestrates services (`ContentExtractionService`, `LLMService`, `TTSService`) to produce a podcast episode. Output includes a single audio file, transcript, title, and summary, suitable for an API endpoint.

**2. Orchestration Logic**

*   **Class & File:** Logic resides in `PodcastGeneratorService` within `app/podcast_workflow.py`.
*   **Triggering:** The service will have a primary method, e.g., `async def generate_podcast_from_source(self, input_data: PodcastRequest) -> PodcastEpisode:`.

**3. Final Output Structure**

The workflow produces a `PodcastEpisode` (Pydantic model):

```python
# In app/schemas.py or app/models.py
from pydantic import BaseModel, HttpUrl
from typing import List, Optional

class PodcastEpisode(BaseModel):
    title: str
    summary: str
    transcript: str
    audio_filepath: str      # Path to the final combined audio file
    source_attributions: List[str]
    warnings: List[str]      # For content flags or other issues
    # Optional: Links/paths to downloadable intermediate LLM outputs
    llm_source_analysis_path: Optional[str] = None
    llm_persona_research_paths: Optional[List[str]] = None
    llm_podcast_outline_path: Optional[str] = None
    llm_dialogue_turns_path: Optional[str] = None
```

**4. Error Handling Strategy**

*   **Initial Approach: Fail Fast.** If a critical step (content extraction, core LLM calls, final audio stitching) fails, the workflow halts. Custom exceptions (e.g., `OutlineGenerationError`, `TTSError`) will be raised and propagated.

**5. Intermediate Data & State Management**

*   **Data Flow & Storage:**
    *   **In-Memory:** Transient data like Python objects for immediate processing.
    *   **Temporary File Storage (Task 1.9):**
        *   Large raw text from content extraction (if above a threshold).
        *   Individual audio segments from `TTSService` before stitching.
        *   **Structured LLM Outputs (for download/debug):** `SourceAnalysis`, `PersonaResearch`, `OutlineSegment` lists, and `DialogueTurn` lists will be serialized to JSON files (e.g., `source_analysis.json`, `podcast_outline.json`) in a job-specific temporary directory.
        *   The `PodcastGeneratorService` manages this temporary directory and its cleanup.
*   **Data Structures:** Pydantic models for structured data:
    ```python
    class SourceAnalysis(BaseModel): # ... key_themes, facts
    class PersonaResearch(BaseModel): # ... name, viewpoints, speaking_style
    class OutlineSegment(BaseModel): # ... segment_title, speaker_id, content_cue
    class DialogueTurn(BaseModel): # ... speaker_id, speaker_gender, text, source_mentions
    ```

**6. Feature Implementation Details**

*   **A. Workflow Sequence (High-Level):**
    1.  Receive input.
    2.  **Content Extraction:** Use `ContentExtractionService`.
    3.  **LLM - Source Analysis:** Use `LLMService.analyze_source_text_async`. Serialize result to `source_analysis.json` in temp dir.
    4.  **LLM - Persona Research:** For each prominent person, use `LLMService.research_persona_async`. Serialize results to `persona_research_{person_id}.json` in temp dir.
    5.  **LLM - Podcast Outline Generation:** Use `LLMService.generate_podcast_outline_async`. Serialize result to `podcast_outline.json` in temp dir.
    6.  **LLM - Dialogue Writing:** Iterate through outline. For each segment, use `LLMService.generate_dialogue_async`. The LLM incorporates source mentions and assigns follower genders. Collect all `DialogueTurn` objects. Serialize the list to `dialogue_turns.json` in temp dir.
    7.  **Content Flag Check:** Inspect safety ratings from LLM responses. If flagged, prepare a warning.
    8.  **TTS - Dialogue to Audio:** For each `DialogueTurn`, call `TTSService.text_to_audio_async`. Store temporary audio file paths.
    9.  **Audio Stitching:** Combine temporary audio segments into a single MP3 using `pydub`.
    10. **Transcript Generation:** Concatenate `DialogueTurn.text`.
    11. **Source Attribution Finalization:** Compile source mentions. Append to transcript and add to `PodcastEpisode.source_attributions`.
    12. **Title & Summary Generation (Optional LLM Call):** Generate title and summary.
    13. **Return `PodcastEpisode`:** Populate and return, including paths to the serialized LLM outputs.

*   **B. Source Attribution (PRD 4.2.7.2):** LLM prompted for in-dialogue mentions. Consolidated list appended to transcript and included in `PodcastEpisode`.

*   **C. Inappropriate Content Flag (PRD 4.2.7.1):** `LLMService` returns safety ratings. `PodcastGeneratorService` checks ratings. If flagged, a warning is added to `PodcastEpisode.warnings`.

*   **D. Dialogue Segmentation & TTS Mapping:** Dialogue processed as `DialogueTurn` objects. Each turn sent to `TTSService`. `LLMService` assigns speaker gender for TTS.

*   **E. Audio Stitching:** Use `pydub` to combine individual TTS audio segments into a final MP3. `ffmpeg` required.

**7. Dependencies**

*   `pydub`
*   Existing services: `ContentExtractionService`, `LLMService`, `TTSService`.

**8. Open Questions/Future Considerations**

*   Detailed logic for podcast title/summary generation.
*   Specific thresholds for content safety flags.
*   Handling very long dialogues exceeding TTS limits.
