import pytest
import asyncio
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from app.podcast_workflow import (
    PodcastGeneratorService,
    PodcastRequest,
    ExtractionError
)
from app.podcast_models import (
    PodcastEpisode,
    DialogueTurn,
    SourceAnalysis,
    PodcastOutline,
    OutlineSegment,
    PersonaResearch
)
from app.llm_service import LLMNotInitializedError


@pytest.fixture
def mock_podcast_data():
    return {
        "extracted_text": "This is the extracted content from a source.",
        "source_analysis": {
            "key_themes": ["theme1"],
            "facts": ["fact1"],
            "summary_points": ["point1"],
            "potential_biases": [],
            "counter_arguments_or_perspectives": [],
            "detailed_analysis": "This is a mock detailed analysis for the e2e test."
        },
        "persona_research": {
            "person_id": "person-a",
            "name": "Person A",
            "detailed_profile": "A comprehensive profile for Person A, known for opinions like 'Opinion 1' and a direct, formal speaking style. This summary captures their essence based on the source."
        }
    }

@pytest.fixture
def mock_podcast_models(mock_podcast_data):
    return {
        "outline": PodcastOutline(
            title_suggestion="E2E Test Podcast Title",
            summary_suggestion="E2E Test Podcast Summary.",
            segments=[
                OutlineSegment(
                    segment_id="s1",
                    segment_title="Introduction",
                    speaker_id="Host",
                    content_cue="Introduce the main topic.",
                    estimated_duration_seconds=30
                ),
                OutlineSegment(
                    segment_id="s2",
                    segment_title="Main Discussion",
                    speaker_id="Alice",
                    content_cue="Discuss fact1.",
                    estimated_duration_seconds=60
                )
            ]
        ),
        "dialogue_turns": [
            DialogueTurn(turn_id=1, speaker_id="Host", speaker_gender="Neutral", text="Welcome to our E2E test podcast.", source_mentions=[]),
            DialogueTurn(turn_id=2, speaker_id="Alice", speaker_gender="Female", text="Let's discuss fact1.", source_mentions=["fact1"])
        ]
    }


# Mock the actual services that PodcastGeneratorService depends on
# We need to patch where they are *looked up*, which is in app.podcast_workflow
@patch('app.podcast_workflow.LLMService', new_callable=MagicMock)
@patch('app.podcast_workflow.GoogleCloudTtsService', new_callable=MagicMock)
class TestPodcastGeneratorService:

    def setup_successful_mocks(self, mock_data, mock_models):
        """Set up mocks for a successful podcast generation flow"""
        # Mock LLM service methods
        self.service.llm_service.analyze_source_text_async = AsyncMock(return_value=mock_data["source_analysis"])
        self.service.llm_service.research_persona_async = AsyncMock(return_value=PersonaResearch(**mock_data["persona_research"]))
        self.service.llm_service.generate_podcast_outline_async = AsyncMock(return_value=mock_models["outline"])
        self.service.llm_service.generate_dialogue_async = AsyncMock(return_value=mock_models["dialogue_turns"])
        
        # Mock TTS service method
        self.service.tts_service.text_to_audio_async = AsyncMock(return_value="mock_segment.mp3")

    def verify_json_file_contents(self, file_path, expected_content):
        """Verify that a JSON file contains the expected content"""
        assert file_path is not None
        # Ensure the file exists before trying to open it
        assert os.path.exists(file_path), f"JSON file not found at {file_path}"
        with open(file_path, 'r') as f:
            saved_content = json.load(f)
            assert saved_content == expected_content

    def setup_method(self, method):
        """Setup for each test method."""
        # Instantiate the service. LLMService and GoogleCloudTtsService are already
        # patched at the class level, so self.service will use those MagicMocks.
        self.service = PodcastGeneratorService()

        # Now, self.service.llm_service IS the MockLLMService instance
        # (as injected into tests by the class decorator), and similarly for tts_service.
        # The MagicMock instances from class-level patches should be clean per test method.
        # Explicit reset_mock() here might be redundant or clear state needed by the test itself.

        # Ensure analyze_source_text_async is an AsyncMock on the llm_service mock for all tests
        # This ensures that any test can await this method and set its return_value/side_effect.
        self.service.llm_service.analyze_source_text_async = AsyncMock()
        # Other common mock configurations can go here.

    def test_podcast_generator_service_initialization_success(self, MockGoogleCloudTtsService, MockLLMService):
        """Test successful initialization of PodcastGeneratorService and its dependencies."""
        # Reset the class mocks just before this test's specific instantiation.
        # This ensures that any calls from setup_method (if it were to instantiate)
        # or previous tests (though new_callable=MagicMock should prevent this) don't interfere.
        MockLLMService.reset_mock()
        MockGoogleCloudTtsService.reset_mock()

        # Instantiate the service here to check its __init__ behavior directly
        # against the freshly reset class mocks.
        service_for_this_test = PodcastGeneratorService()

        MockLLMService.assert_called_once() # Called in PodcastGeneratorService.__init__
        MockGoogleCloudTtsService.assert_called_once() # Called in PodcastGeneratorService.__init__
        
        assert service_for_this_test.llm_service is not None
        # self.service.content_extractor is no longer an attribute
        assert service_for_this_test.tts_service is not None
        
        # Verify that the instances on service_for_this_test are indeed the mocks
        # This is an important check to ensure patching worked as expected for the instances.
        # MockLLMService() when called returns a MagicMock instance if not configured otherwise.
        # So, service_for_this_test.llm_service should be the result of MockLLMService().
        # And MockLLMService itself is the class mock.
        assert isinstance(service_for_this_test.llm_service, MagicMock)
        assert isinstance(service_for_this_test.tts_service, MagicMock)

        # Check that the llm_service instance on our test-local service is the one that MockLLMService produced.
        # This is a bit circular but confirms the linkage:
        # MockLLMService() returns an instance. That instance is service_for_this_test.llm_service.
        # We can check that MockLLMService.return_value is this instance.
        # However, this only works if MockLLMService was configured with a specific return_value beforehand.
        # For a simple new_callable=MagicMock, the call MockLLMService() creates a new MagicMock.
        # The key is that MockLLMService (the class mock) itself was called.


    @patch('app.podcast_workflow.LLMService') # Patch LLMService specifically for this test
    def test_podcast_generator_service_initialization_llm_failure(self, MockLLMServiceFailure, MockGoogleCloudTtsService, MockLLMService):
        """Test initialization when LLMService fails to initialize."""
        # Ensure the original MockLLMService from class decorator isn't used here
        # We use MockLLMServiceFailure which is local to this test method's decorators
        MockLLMServiceFailure.side_effect = LLMNotInitializedError("Test LLM Init Error")
        
        # We need to re-instantiate the service for this specific test case
        # because the setup_method already ran with the class-level mocks.
        # This is a bit tricky with class-level patching and per-test side effects.
        # A cleaner way might be to not use class-level patching if init needs varied mocking.
        
        # For now, let's assume the __init__ in PodcastGeneratorService is what we're testing
        # and it might set self.llm_service to None if LLMNotInitializedError is caught.
        with patch('app.podcast_workflow.LLMService', new=MockLLMServiceFailure):
             service_with_llm_fail = PodcastGeneratorService()
             assert service_with_llm_fail.llm_service is None
             # Check that other services might still be initialized
             # service_with_llm_fail.content_extractor is no longer an attribute
             assert service_with_llm_fail.tts_service is not None

    @pytest.mark.asyncio
    async def test_generate_podcast_llm_service_not_available(self, MockGoogleCloudTtsService, MockLLMService):
        """Test behavior when llm_service is None during generate_podcast_from_source call."""
        self.service.llm_service = None # Simulate LLM service failed to init
        sample_request = PodcastRequest(source_url="http://example.com/article")
        
        episode = await self.service.generate_podcast_from_source(sample_request)
        
        assert episode.title == "Error"
        assert episode.summary == "LLM Service Not Initialized"
        assert "LLM Service failed to initialize." in episode.warnings

    # --- Tests for Content Extraction --- 
    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_content_extraction_url_success(self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService):
        extracted_text = "Test content from URL"
        mock_extract_url.return_value = extracted_text
        # Mock LLM response to prevent downstream errors for this test's focus
        self.service.llm_service.analyze_source_text_async.return_value = {"key_themes": [], "facts": [], "summary_points": [], "potential_biases": [], "counter_arguments_or_perspectives": []}

        request = PodcastRequest(source_url="http://example.com/source")
        # Test with temp directory for file path generation
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir:
                mock_tempdir.return_value.__enter__.return_value = tmpdir
                episode = await self.service.generate_podcast_from_source(request)

                assert episode is not None
                mock_extract_url.assert_called_once_with(str(request.source_url))
                self.service.llm_service.analyze_source_text_async.assert_called_once_with(extracted_text)

    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_text_from_pdf_path', new_callable=AsyncMock) # New patch target
    async def test_content_extraction_pdf_path_triggers_workflow_error(self, mock_extract_pdf_path, MockGoogleCloudTtsService, MockLLMService):
        """Test that if extract_text_from_pdf_path raises ExtractionError, the workflow handles it."""
        fake_pdf_path = "/fake/path.to/nonexistent.pdf"
        request = PodcastRequest(source_pdf_path=fake_pdf_path)
        error_message = "Failed to extract from PDF path for testing"
        mock_extract_pdf_path.side_effect = ExtractionError(error_message)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir, \
                 patch('app.podcast_workflow.logger') as mock_logger: # Keep logger mock for error log assertion
                mock_tempdir.return_value.__enter__.return_value = tmpdir
                episode = await self.service.generate_podcast_from_source(request)

                assert episode is not None
                assert episode.title == "Error"
                assert episode.summary == "Content Extraction Failed"
                assert episode.transcript == ""
                assert f"Failed to extract content from PDF: {error_message}" in episode.warnings[0]
                
                mock_extract_pdf_path.assert_called_once_with(fake_pdf_path)
                # Check that the ExtractionError from extract_text_from_pdf_path was logged
                mock_logger.error.assert_any_call(
                    f"Content extraction from PDF path {fake_pdf_path} failed: {error_message}"
                )
                self.service.llm_service.analyze_source_text_async.assert_not_called()

    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_text_from_pdf_path', new_callable=AsyncMock)
    async def test_content_extraction_pdf_path_success(self, mock_extract_pdf_path, MockGoogleCloudTtsService, MockLLMService):
        """Test successful content extraction when a PDF path is provided."""
        fake_pdf_path = "/fake/path.to/real.pdf"
        extracted_pdf_text = "This is text from the PDF."
        mock_extract_pdf_path.return_value = extracted_pdf_text

        # Mock LLM and TTS responses for a successful workflow
        # This dictionary should match what SourceAnalysis expects after JSON parsing
        mock_analysis_response = {"key_themes": ["pdf"], "facts": ["fact from pdf"], "summary_points": ["summary of pdf"]}
        self.service.llm_service.analyze_source_text_async.return_value = mock_analysis_response

        # Mock outline generation to return None for this test, so dialogue is skipped
        if not isinstance(self.service.llm_service.generate_podcast_outline_async, AsyncMock):
            self.service.llm_service.generate_podcast_outline_async = AsyncMock()
        self.service.llm_service.generate_podcast_outline_async.return_value = None
        
        # Ensure text_to_audio_async is treated as an AsyncMock
        if not isinstance(self.service.tts_service.text_to_audio_async, AsyncMock):
            self.service.tts_service.text_to_audio_async = AsyncMock()
        self.service.tts_service.text_to_audio_async.return_value = "mock_audio_segment.mp3"
        # Mock pydub concatenation if needed, for now assume single segment or direct path usage
        # For simplicity, assume final audio path is directly from TTS if only one segment

        request = PodcastRequest(source_pdf_path=fake_pdf_path)

        with (
            tempfile.TemporaryDirectory() as tmpdir,
            patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir
        ):
                
                mock_tempdir.return_value.__enter__.return_value = tmpdir
                
                episode = await self.service.generate_podcast_from_source(request)

                mock_extract_pdf_path.assert_called_once_with(fake_pdf_path)
                self.service.llm_service.analyze_source_text_async.assert_called_once_with(extracted_pdf_text)
                # self.service.llm_service.generate_text_async.assert_called_once() # For script generation - To be enabled when implemented
                # self.service.tts_service.text_to_audio_async.assert_called_once() # To be enabled when implemented
                
                assert episode is not None
                assert episode.title == "Generation Incomplete" # Title remains default if outline fails
                assert episode.transcript == "Dialogue generation skipped due to missing prerequisites." # Transcript reflects skipped dialogue
                assert episode.audio_filepath == "placeholder.mp3" # Check for hardcoded placeholder

    @pytest.mark.asyncio
    async def test_generate_podcast_from_source_e2e_success(self, MockGoogleCloudTtsService, MockLLMService, mock_podcast_data, mock_podcast_models):
        """Test a full successful run of generate_podcast_from_source with all mocks."""
        # 1. Setup Mocks
        self.setup_successful_mocks(mock_podcast_data, mock_podcast_models)
        
        with patch('app.podcast_workflow.extract_content_from_url', AsyncMock(return_value=mock_podcast_data["extracted_text"])) as mock_extract_content, \
             patch('app.podcast_workflow.logger') as mock_logger:
            
            # 2. Prepare Request
            request_data = PodcastRequest(
                source_url="http://example.com/e2e-test",
                prominent_persons=["Person A"],
                desired_podcast_length_str="2 minutes"
            )

            # 3. Execute
            with tempfile.TemporaryDirectory() as tmpdir:
                with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir_context:
                    mock_tempdir_context.return_value.__enter__.return_value = tmpdir
                    episode = await self.service.generate_podcast_from_source(request_data)

                    # 4. Assertions - Episode Metadata
                    assert episode.title == "E2E Test Podcast Title"
                    assert episode.summary == "E2E Test Podcast Summary."
                    expected_transcript = "Host: Welcome to our E2E test podcast.\nAlice: Let's discuss fact1."
                    assert episode.transcript == expected_transcript
                    assert episode.warnings == []

                    # 5. Assertions - Saved JSON Files
                    # For source_analysis, expect only fields defined in SourceAnalysis model
                    expected_source_analysis_dict = {
                        "summary_points": mock_podcast_data["source_analysis"]["summary_points"],
                        "detailed_analysis": mock_podcast_data["source_analysis"]["detailed_analysis"]
                    }
                    self.verify_json_file_contents(
                        episode.llm_source_analysis_path, 
                        expected_source_analysis_dict
                    )
                    # For persona_research, the mock_podcast_data already matches the simplified PersonaResearch model
                    self.verify_json_file_contents(
                        episode.llm_persona_research_paths[0], 
                        mock_podcast_data["persona_research"]
                    )
                    self.verify_json_file_contents(
                        episode.llm_podcast_outline_path, 
                        mock_podcast_models["outline"].model_dump()
                    )
                    self.verify_json_file_contents(
                        episode.llm_dialogue_turns_path, 
                        [turn.model_dump() for turn in mock_podcast_models["dialogue_turns"]]
                    )
            
            # 6. Assertions - Service Method Calls
            mock_extract_content.assert_called_once_with(str(request_data.source_url))
            self.service.llm_service.analyze_source_text_async.assert_called_once_with(mock_podcast_data["extracted_text"])
            self.service.llm_service.research_persona_async.assert_called_once_with(
                source_text=mock_podcast_data["extracted_text"], 
                person_name="Person A"
            )
            self.service.llm_service.generate_podcast_outline_async.assert_called_once()
            self.service.llm_service.generate_dialogue_async.assert_called_once()
            
            # TODO: Implement and test audio generation & TTS functionality
            # Audio file assertions currently disabled; reinstate when implemented:
            # - TTS service calls for each dialogue turn (check call_count and specific calls)
            # - Audio filepath verification (should be in temp dir with .mp3 extension)
    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_content_extraction_url_failure(self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService):
        mock_extract_url.side_effect = ExtractionError("URL fetch failed")
        request = PodcastRequest(source_url="http://example.com/badurl")
        episode = await self.service.generate_podcast_from_source(request)

        assert episode.title == "Error"
        assert episode.summary == "Content Extraction Failed"
        assert "Failed to extract content from URL: URL fetch failed" in episode.warnings
        self.service.llm_service.analyze_source_text_async.assert_not_called()

    @pytest.mark.asyncio
    async def test_content_extraction_no_source_provided(self, MockGoogleCloudTtsService, MockLLMService):
        request = PodcastRequest() # No source_url or source_pdf_path
        episode = await self.service.generate_podcast_from_source(request)

        assert episode.title == "Error"
        assert episode.summary == "No Source Provided"
        assert "No source URL or PDF path provided." in episode.warnings
        self.service.llm_service.analyze_source_text_async.assert_not_called()

    # --- Tests for LLM Source Analysis --- 
    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_llm_source_analysis_success(self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService):
        extracted_text = "Some fascinating source text."
        llm_analysis_response = {
            "key_themes": ["theme A", "theme B"],
            "facts": ["fact X", "fact Y"],
            "summary_points": ["point 1"],
            "potential_biases": ["bias Z"],
            "counter_arguments_or_perspectives": ["perspective W"],
            "detailed_analysis": "This is a detailed analysis of the source text, covering themes, facts, and potential biases."
        }
        mock_extract_url.return_value = extracted_text
        self.service.llm_service.analyze_source_text_async.return_value = llm_analysis_response

        request = PodcastRequest(source_url="http://example.com/source")
        
        # We need to mock tempfile.TemporaryDirectory to control the path and check file creation
        with tempfile.TemporaryDirectory() as tmpdir: # Real temp dir for actual file write
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir_context:
                # Configure the context manager mock
                mock_tempdir_context.return_value.__enter__.return_value = tmpdir
                
                episode = await self.service.generate_podcast_from_source(request)

                expected_json_path = os.path.join(tmpdir, "source_analysis.json")
                assert os.path.exists(expected_json_path)
                with open(expected_json_path, 'r') as f:
                    saved_data = json.load(f)
                # Assert that all items in saved_data (from Pydantic model) are present and correct in llm_analysis_response (raw mock)
                for key, value in saved_data.items():
                    assert key in llm_analysis_response, f"Key '{key}' from saved_data not found in llm_analysis_response"
                    assert llm_analysis_response[key] == value, f"Value for key '{key}' does not match between saved_data and llm_analysis_response"
                # Optionally, assert that all *required* fields of SourceAnalysis are present in saved_data
                # This is implicitly handled by Pydantic validation if the model was created successfully.
                # However, to be explicit about what we expect to be saved:
                expected_keys_from_model = SourceAnalysis.model_fields.keys()
                for k in expected_keys_from_model:
                    if k in SourceAnalysis.model_fields and SourceAnalysis.model_fields[k].is_required():
                         assert k in saved_data, f"Required key '{k}' from SourceAnalysis model not in saved_data"
                assert episode.llm_source_analysis_path == expected_json_path
        
        mock_extract_url.assert_called_once_with(str(request.source_url)) # Ensure extraction was called
        self.service.llm_service.analyze_source_text_async.assert_called_once_with(extracted_text)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("llm_response_config, expected_title, expected_transcript_contains", [
        pytest.param(
            {"error": "LLM processing failed", "raw_response": "details..."}, 
            "Generation Incomplete", 
            "Dialogue generation skipped", # Looser check for transcript
            id="llm_returns_error_dict"
        ),
        pytest.param(
            {"key_themes": ["theme"], "facts": "not a list"}, # Pydantic error for SourceAnalysis
            "Generation Incomplete", 
            "Dialogue generation skipped",
            id="llm_returns_malformed_pydantic_data"
        )
    ])
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_llm_source_analysis_error_scenarios(
        self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService, 
        llm_response_config, expected_title, expected_transcript_contains
    ):
        """Test error handling when LLM source analysis returns errors or malformed data."""
        extracted_text = "Some text."
        mock_extract_url.return_value = extracted_text
        # Ensure analyze_source_text_async is an AsyncMock if not already set up by setup_method for all tests
        if not isinstance(self.service.llm_service.analyze_source_text_async, AsyncMock):
            self.service.llm_service.analyze_source_text_async = AsyncMock()
        self.service.llm_service.analyze_source_text_async.return_value = llm_response_config

        request = PodcastRequest(source_url="http://example.com/source")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir_context:
                mock_tempdir_context.return_value.__enter__.return_value = tmpdir
                episode = await self.service.generate_podcast_from_source(request)
        
        assert episode.llm_source_analysis_path is None
        assert episode.title == expected_title
        # Check if the transcript contains the expected substring, as exact match might be too brittle
        assert expected_transcript_contains in episode.transcript

# Note: Need to ensure LLMNotInitializedError and ExtractionError are accessible for these tests.
# They might need to be defined in app.common_exceptions or similar and imported.
# For now, assuming they are importable from app.podcast_workflow or defined within it for simplicity of example.
# If they are in llm_service.py and content_extractor.py respectively, they should be imported from there in podcast_workflow.py
# and then this test file would import them from podcast_workflow.py if that's where they are exposed.
# Let's assume for now they are correctly defined/imported in app.podcast_workflow for the service to use.

# To make LLMNotInitializedError and ExtractionError available for the test file, if they are defined in
# their respective service files (llm_service.py, content_extractor.py), you would typically
# ensure they are imported into app.podcast_workflow.py if PodcastGeneratorService catches them by name.
# Or, the tests could import them directly from their source if that's cleaner.
# For this example, I've added them to the imports from app.podcast_workflow, implying they are exposed there.
