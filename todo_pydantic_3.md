# Todo: Pydantic AI Migration for GeminiService

## Overview
Migrate GeminiService methods to use Pydantic AI structured output and eliminate JSON string passing throughout the pipeline. This includes introducing the `PodcastDialogue` model and removing the deprecated `persona_details_map`.

## Phase 1: Create PodcastDialogue Model and Helper Functions (Low Risk)
**Goal**: Build the foundation - new models and migration helpers before making changes

### 1.1 Create PodcastDialogue Model in podcast_models.py
```python
class PodcastDialogue(BaseModel):
    """Container for dialogue turns with helper methods"""
    turns: List[DialogueTurn]
    
    def to_transcript(self) -> str:
        """Convert dialogue turns to simple speaker: text format"""
        return "\n".join(f"{turn.speaker_id}: {turn.text}" for turn in self.turns)
    
    @property
    def turn_count(self) -> int:
        """Total number of dialogue turns"""
        return len(self.turns)
    
    @property
    def speaker_list(self) -> List[str]:
        """List of unique speakers in the dialogue"""
        return list(dict.fromkeys(turn.speaker_id for turn in self.turns))
    
    @property
    def total_word_count(self) -> int:
        """Total word count across all turns"""
        return sum(len(turn.text.split()) for turn in self.turns)
    
    @property
    def estimated_duration_seconds(self) -> int:
        """Estimate duration based on average speaking rate"""
        # Assuming 150 words per minute average speaking rate
        return int((self.total_word_count / 150) * 60)
```

### 1.2 Create Data Migration Helper Functions
```python
# In app/utils/migration_helpers.py

def parse_source_analyses_safe(content: List[str]) -> List[SourceAnalysis]:
    """Safely parse JSON strings to SourceAnalysis objects with error handling"""
    result = []
    for i, json_str in enumerate(content):
        try:
            data = json.loads(json_str)
            source_analysis = SourceAnalysis(**data)
            result.append(source_analysis)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for source analysis {i}: {e}")
            # Could add a default/empty SourceAnalysis or skip
        except ValidationError as e:
            logger.error(f"Failed to validate SourceAnalysis {i}: {e}")
            # Handle missing/invalid fields gracefully
    return result

def parse_persona_research_safe(content: List[str]) -> List[PersonaResearch]:
    """Safely parse JSON strings to PersonaResearch objects with error handling"""
    result = []
    for i, json_str in enumerate(content):
        try:
            data = json.loads(json_str)
            persona = PersonaResearch(**data)
            result.append(persona)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON for persona {i}: {e}")
        except ValidationError as e:
            logger.error(f"Failed to validate PersonaResearch {i}: {e}")
    return result

def get_persona_by_id(personas: List[PersonaResearch], person_id: str) -> Optional[PersonaResearch]:
    """Find a persona by ID from the list"""
    for persona in personas:
        if persona.person_id == person_id:
            return persona
    return None
```

### 1.3 Create Fallback Methods for Pydantic AI
```python
# In llm_service.py

def _parse_outline_from_json(self, json_response: str) -> PodcastOutline:
    """Fallback method to parse JSON response to PodcastOutline"""
    cleaned_json = self._clean_json_string_from_markdown(json_response)
    data = json.loads(cleaned_json)
    return PodcastOutline(**data)

def _parse_dialogue_from_json(self, json_response: str) -> PodcastDialogue:
    """Fallback method to parse JSON response to PodcastDialogue"""
    cleaned_json = self._clean_json_string_from_markdown(json_response)
    data = json.loads(cleaned_json)
    turns = [DialogueTurn(**turn) for turn in data]
    return PodcastDialogue(turns=turns)
```

## Phase 2: Add Tests for New Data Flow (Critical)
**Goal**: Ensure the new Pydantic object flow works correctly before making changes

### 2.1 Create tests/test_pydantic_data_flow.py
- [ ] Test that SourceAnalysis objects flow correctly through pipeline
- [ ] Test that PersonaResearch objects flow correctly through pipeline
- [ ] Test that no JSON serialization/deserialization happens in main flow
- [ ] Test PodcastDialogue model methods and properties
- [ ] Test error cases: missing data, invalid data, empty lists

### 2.2 Test Migration Helpers
- [ ] Test `parse_source_analyses_safe()` with valid JSON
- [ ] Test `parse_source_analyses_safe()` with invalid JSON
- [ ] Test `parse_persona_research_safe()` with mixed valid/invalid data
- [ ] Test `get_persona_by_id()` with existing and non-existing IDs

### 2.3 Integration Tests
- [ ] Test full workflow with Pydantic objects (no JSON strings)
- [ ] Test that all file outputs still work correctly
- [ ] Test that status updates use correct object properties
- [ ] Test edge cases: 0 personas, 1 persona, multiple personas

## Phase 3: Update Data Flow to Use Pydantic Objects Throughout (High Impact)
**Goal**: Change the entire data pipeline to pass Pydantic objects instead of JSON strings

### 3.1 Update podcast_workflow.py Data Structures
- [ ] Change `source_analyses_content: List[str] = []` to `source_analyses: List[SourceAnalysis] = []` (line ~451)
- [ ] Change `persona_research_docs_content: List[str] = []` to `persona_research_docs: List[PersonaResearch] = []` (line ~451)
- [ ] Remove `.model_dump_json()` from source analysis append (line ~584)
- [ ] Remove `.model_dump_json()` from persona research append (line ~688)
- [ ] Remove `.model_dump_json()` from host persona append (line ~814)
- [ ] Update all references to these variables throughout the file

### 3.2 Remove persona_details_map Creation
- [ ] Delete entire `persona_details_map` creation block (lines ~820-831)
- [ ] Remove `persona_details_map` from `generate_podcast_outline_async` call (line ~892)
- [ ] Remove `persona_details_map` from `generate_dialogue_async` call (line ~1043)

### 3.3 Update generate_podcast_outline_async Method Signature
- [ ] Change `source_analyses: list[str]` to `source_analyses: List[SourceAnalysis]`
- [ ] Change `persona_research_docs: list[str]` to `persona_research_docs: List[PersonaResearch]`
- [ ] Remove `persona_details_map` parameter entirely
- [ ] Update method docstring to reflect new parameter types

### 3.4 Update generate_podcast_outline_async Implementation
- [ ] Remove JSON parsing logic for source analyses (currently parses JSON strings)
- [ ] Remove JSON parsing logic for persona research documents
- [ ] Update persona ID extraction to use `pr.person_id` directly from objects
- [ ] Update prompt building to extract data from Pydantic objects directly

### 3.5 Update generate_dialogue_async Method Signature
- [ ] Verify `source_analyses: list[SourceAnalysis]` (already expects objects)
- [ ] Verify `persona_research_docs: list[PersonaResearch]` (already expects objects)
- [ ] Remove `persona_details_map` parameter
- [ ] Update method docstring

### 3.6 Update _generate_segment_dialogue and _build_segment_dialogue_prompt Methods
- [ ] Remove `persona_details_map` parameter from both methods
- [ ] Extract speaker details directly from `persona_research_docs` list
- [ ] Update speaker lookup logic to use `get_persona_by_id()` helper
- [ ] Replace persona_details_map lookups with PersonaResearch object access

### 3.7 Update JSON Parsing in podcast_workflow.py
- [ ] Remove JSON parsing in dialogue generation section (lines ~997-1010)
- [ ] Remove JSON parsing for persona research (lines ~1012-1027)
- [ ] Pass objects directly instead of parsing JSON strings
- [ ] Use migration helpers during transition if needed

### 3.8 Update generate_dialogue_async to Return PodcastDialogue
- [ ] Change return type from `List[DialogueTurn]` to `PodcastDialogue`
- [ ] Update method implementation to return `PodcastDialogue(turns=all_dialogue_turns)`
- [ ] Update method docstring to reflect new return type
- [ ] Import `PodcastDialogue` at top of llm_service.py

### 3.9 Update podcast_workflow.py for PodcastDialogue
- [ ] Add `podcast_dialogue: Optional[PodcastDialogue] = None` variable
- [ ] Update dialogue generation call to receive `PodcastDialogue`
- [ ] Extract turns: `dialogue_turns_list = podcast_dialogue.turns if podcast_dialogue else []`
- [ ] Update transcript generation to use `podcast_transcript = podcast_dialogue.to_transcript()`
- [ ] Update logging to use `podcast_dialogue.turn_count` and `podcast_dialogue.estimated_duration_seconds`
- [ ] Update all conditional checks from `if dialogue_turns_list:` to `if podcast_dialogue and podcast_dialogue.turns:`
- [ ] Update status messages to use PodcastDialogue properties

## Phase 4: Convert Methods to Pydantic AI Structured Output (Medium Risk)
**Goal**: Use Pydantic AI for direct structured output generation

### 4.1 Update generate_podcast_outline_async to Use Pydantic AI
- [ ] Replace JSON response parsing with Pydantic AI call:
  ```python
  try:
      podcast_outline = await self.generate_text_async(
          final_prompt, 
          result_type=PodcastOutline,
          timeout_seconds=360
      )
  except ValidationError as e:
      logger.error(f"Structured output validation failed: {e.errors()}")
      # Fallback to JSON parsing
      json_response = await self.generate_text_async(final_prompt)
      podcast_outline = self._parse_outline_from_json(json_response)
  ```
- [ ] Remove `_clean_json_string_from_markdown` call
- [ ] Remove `json.loads()` and JSON parsing try/except blocks
- [ ] Keep duration validation logic (`_validate_and_adjust_segments`)
- [ ] Add proper error handling for ValidationError, UserError, ModelRetry

### 4.2 Update _generate_segment_dialogue to Use Pydantic AI
- [ ] Change to generate PodcastDialogue directly:
  ```python
  try:
      dialogue_response = await self.generate_text_async(
          segment_prompt,
          result_type=PodcastDialogue,
          timeout_seconds=360
      )
      return dialogue_response.turns
  except ValidationError as e:
      logger.error(f"Dialogue generation validation failed: {e}")
      # Fallback to JSON parsing
      json_response = await self.generate_text_async(segment_prompt)
      dialogue = self._parse_dialogue_from_json(json_response)
      return dialogue.turns
  ```
- [ ] Remove JSON cleaning and parsing logic
- [ ] Handle turn ID assignment after getting structured output
- [ ] Add fallback for validation failures

### 4.3 Update Error Handling Strategy
- [ ] Add comprehensive ValidationError handling with detailed logging
- [ ] Implement fallback to JSON parsing when structured output fails
- [ ] Add UserError and ModelRetry exception handling
- [ ] Log validation errors with `e.errors()` for debugging
- [ ] Consider implementing retry logic for transient failures

## Phase 5: Cleanup and Documentation (Low Risk)
**Goal**: Remove deprecated code and update documentation

### 5.1 Remove Deprecated Code
- [ ] Remove all references to `persona_details_map`
- [ ] Remove unused JSON parsing helper methods (keep migration helpers)
- [ ] Remove `.model_dump_json()` calls that are no longer needed
- [ ] Clean up imports

### 5.2 Update Documentation
- [ ] Update method docstrings to reflect new signatures
- [ ] Document the new data flow in a README or design doc
- [ ] Add examples of new usage patterns
- [ ] Document error handling and fallback strategies

### 5.3 Optional: Remove Migration Helpers
- [ ] Once stable, consider removing migration helper functions
- [ ] Remove any temporary backward compatibility code

## Success Criteria
- [ ] All tests pass with new Pydantic object flow
- [ ] No JSON string passing between major components
- [ ] Pydantic AI structured output working with proper error handling
- [ ] Code is cleaner and more type-safe
- [ ] Performance is equal or better than JSON parsing approach
- [ ] persona_details_map completely eliminated

## Notes
- Git revert can be used if issues arise (no feature flags needed)
- Monitor LLM response quality with structured output
- Keep fallback JSON parsing logic initially for safety
- Consider performance benchmarking before/after migration
- Migration helpers provide safety during transition
- Remove persona_details_map completely (duplicates PersonaResearch)