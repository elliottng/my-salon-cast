import pytest
import json
from unittest.mock import AsyncMock, patch, Mock
import asyncio

from app.llm_service import GeminiService
from app.podcast_models import PodcastOutline, OutlineSegment, DialogueTurn, PersonaResearch, SourceAnalysis
from app.common_exceptions import LLMProcessingError

SAMPLE_SOURCE_TEXT_FOR_ANALYSIS = """
Artificial intelligence is rapidly changing the world.
Its applications span from healthcare to finance, offering new solutions.
However, ethical considerations and potential biases are important topics of discussion.
"""

@pytest.fixture
def gemini_service():
    return GeminiService()

@pytest.mark.asyncio
async def test_generate_podcast_outline_async_success(gemini_service):
    sample_outline_data = {
        "title_suggestion": "Test Title",
        "summary_suggestion": "Test Summary",
        "segments": [
            {
                "segment_id": "s1",
                "segment_title": "Intro",
                "speaker_id": "Host",
                "content_cue": "Introduce topic",
                "estimated_duration_seconds": 60
            }
        ]
    }
    mock_response_json = json.dumps(sample_outline_data)

    # Create mock Pydantic model instances
    mock_source_analysis = SourceAnalysis(
        summary_points=["Key summary point 1", "Another important point"],
        detailed_analysis="This is a sample detailed analysis for the podcast outline test."
    )
    mock_persona_research = PersonaResearch(
        person_id="person-b",
        name="Person B",
        viewpoints=["viewpoint X", "viewpoint Y"]
    )

    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_response_json)) as mock_generate_text:
        outline = await gemini_service.generate_podcast_outline_async(
            source_analyses=[mock_source_analysis],
            persona_research_docs=[mock_persona_research],
            desired_podcast_length_str="5 minutes",
            num_prominent_persons=1,
            names_prominent_persons_list=["Person A"]  # This could be Person B to align with mock_persona_research if strict consistency is needed, but for the mock, it might not matter.
        )
        mock_generate_text.assert_called_once()
        assert isinstance(outline, PodcastOutline)
        assert outline.title_suggestion == "Test Title"
        assert len(outline.segments) == 1
        assert outline.segments[0].segment_id == "s1"

@pytest.mark.asyncio
async def test_generate_podcast_outline_async_invalid_json(gemini_service):
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value="not a json string {[")) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.generate_podcast_outline_async(
                source_analyses=["dummy analysis"],
                persona_research_docs=[],
                desired_podcast_length_str="1 min",
                num_prominent_persons=0,
                names_prominent_persons_list=[]
            )
        assert "not valid JSON" in str(excinfo.value)

@pytest.mark.asyncio
async def test_generate_podcast_outline_async_validation_error(gemini_service):
    invalid_outline_data = {"title_suggestion": "Test Title"} # Missing required fields
    mock_response_json = json.dumps(invalid_outline_data)
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_response_json)) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.generate_podcast_outline_async(
                source_analyses=["dummy analysis"],
                persona_research_docs=[],
                desired_podcast_length_str="1 min",
                num_prominent_persons=0,
                names_prominent_persons_list=[]
            )
        assert "Failed to generate any dialogue turns for the podcast" in str(excinfo.value)

@pytest.mark.asyncio
async def test_generate_dialogue_async_success(gemini_service):
    sample_dialogue_data = [
        {
            "turn_id": 1,
            "speaker_id": "Host",
            "speaker_gender": "Neutral",
            "text": "Hello world",
            "source_mentions": []
        },
        {
            "turn_id": 2,
            "speaker_id": "Alice",
            "speaker_gender": "Female",
            "text": "Hi Host!",
            "source_mentions": ["source A"]
        }
    ]
    mock_response_json = json.dumps(sample_dialogue_data)
    test_podcast_outline = PodcastOutline(title_suggestion="T", summary_suggestion="S", segments=[])

    # Create mock Pydantic model instances
    mock_source_analysis_obj = SourceAnalysis(
        summary_points=["Dialogue context summary 1", "Dialogue context summary 2"],
        detailed_analysis="Detailed analysis providing context for dialogue generation."
    )
    mock_persona_research_obj = PersonaResearch(
        person_id="person-a",
        name="Person A",
        viewpoints=["viewpoint1", "viewpoint2"]
    )

    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_response_json)) as mock_generate_text:
        dialogue_turns = await gemini_service.generate_dialogue_async(
            podcast_outline=test_podcast_outline,
            source_analyses=[mock_source_analysis_obj], 
            persona_research_docs=[mock_persona_research_obj], 
            desired_podcast_length_str="5 minutes",
            num_prominent_persons=1,
            prominent_persons_details=[("Alice", "A", "Female")]
        )
        mock_generate_text.assert_called_once()
        assert isinstance(dialogue_turns, list)
        assert len(dialogue_turns) == 2
        assert isinstance(dialogue_turns[0], DialogueTurn)
        assert dialogue_turns[0].turn_id == 1
        assert dialogue_turns[1].speaker_id == "Alice"

@pytest.mark.asyncio
async def test_generate_dialogue_async_invalid_json_format(gemini_service):
    test_podcast_outline = PodcastOutline(title_suggestion="T", summary_suggestion="S", segments=[])
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value="not a json list")) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.generate_dialogue_async(test_podcast_outline, [], [], "", 0, [])
        assert "Failed to generate any dialogue turns for the podcast" in str(excinfo.value)

@pytest.mark.asyncio
async def test_generate_dialogue_async_not_a_list(gemini_service):
    mock_response_json = json.dumps({"not_a_list": True})
    test_podcast_outline = PodcastOutline(title_suggestion="T", summary_suggestion="S", segments=[])
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_response_json)) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.generate_dialogue_async(test_podcast_outline, [], [], "", 0, [])
        assert "Failed to generate any dialogue turns for the podcast" in str(excinfo.value)

@pytest.mark.asyncio
async def test_generate_dialogue_async_item_validation_error(gemini_service):
    invalid_dialogue_item_data = [{"turn_id": 1}] # Missing speaker_id, text
    mock_response_json = json.dumps(invalid_dialogue_item_data)
    test_podcast_outline = PodcastOutline(title_suggestion="T", summary_suggestion="S", segments=[])
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_response_json)) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.generate_dialogue_async(test_podcast_outline, [], [], "", 0, [])
        assert "Failed to generate any dialogue turns for the podcast" in str(excinfo.value)



@pytest.mark.asyncio
async def test_analyze_source_text_async_success(gemini_service):
    """Test successful analysis of source text with default instructions."""
    sample_analysis_data = {
        "summary_points": ["AI is transformative.", "Ethical concerns exist."],
        "detailed_analysis": "The text discusses AI's broad impact and related ethical questions."
    }
    # Simulate that generate_text_async returns a markdown-wrapped JSON string
    mock_llm_response_str = f"```json\n{json.dumps(sample_analysis_data)}\n```"

    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_llm_response_str)) as mock_generate_text:
        analysis_result = await gemini_service.analyze_source_text_async(SAMPLE_SOURCE_TEXT_FOR_ANALYSIS)

        mock_generate_text.assert_called_once()
        # Optional: More specific assertion about the prompt construction if desired
        # called_prompt = mock_generate_text.call_args[0][0]
        # assert SAMPLE_SOURCE_TEXT_FOR_ANALYSIS in called_prompt

        assert isinstance(analysis_result, SourceAnalysis)
        assert analysis_result.summary_points == sample_analysis_data["summary_points"]
        assert analysis_result.detailed_analysis == sample_analysis_data["detailed_analysis"]


@pytest.mark.asyncio
async def test_analyze_source_text_async_invalid_json_response(gemini_service):
    """Test analyze_source_text_async when the LLM returns a non-JSON string."""
    malformed_json_string = "```json\n{\"summary_points\": [\"AI is transformative.\", \"Ethical concerns exist.\"invalid_json```"
    
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=malformed_json_string)) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.analyze_source_text_async(SAMPLE_SOURCE_TEXT_FOR_ANALYSIS)
        
        mock_generate_text.assert_called_once()
        assert "Response was not valid JSON after cleaning Markdown" in str(excinfo.value)


@pytest.mark.asyncio
async def test_analyze_source_text_async_pydantic_validation_error(gemini_service):
    """Test analyze_source_text_async when LLM returns JSON that fails Pydantic validation."""
    # summary_points should be a list, but here it's a string
    invalid_structure_data = {
        "summary_points": "This should be a list, not a string.",
        "detailed_analysis": "The detailed analysis is present and correct."
    }
    mock_llm_response_str = f"```json\n{json.dumps(invalid_structure_data)}\n```"

    with patch.object(gemini_service, 'generate_text_async', AsyncMock(return_value=mock_llm_response_str)) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.analyze_source_text_async(SAMPLE_SOURCE_TEXT_FOR_ANALYSIS)
        
        mock_generate_text.assert_called_once()
        # Check for part of the Pydantic validation error message or our custom wrapper message
        assert "Failed to validate the structure of the LLM response for source analysis" in str(excinfo.value)


@pytest.mark.asyncio
async def test_analyze_source_text_async_generate_text_raises_exception(gemini_service):
    """Test analyze_source_text_async when generate_text_async raises an exception."""
    original_exception_message = "Simulated API error"
    
    with patch.object(gemini_service, 'generate_text_async', AsyncMock(side_effect=RuntimeError(original_exception_message))) as mock_generate_text:
        with pytest.raises(LLMProcessingError) as excinfo:
            await gemini_service.analyze_source_text_async(SAMPLE_SOURCE_TEXT_FOR_ANALYSIS)
        
        mock_generate_text.assert_called_once()
        # Check that our custom error message is present, and optionally the original exception's message
        assert "LLM API error during source analysis" in str(excinfo.value) # Check for the more specific part of the wrapped error
        assert original_exception_message in str(excinfo.value)
