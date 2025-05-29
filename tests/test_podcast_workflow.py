import pytest
import asyncio
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from app.podcast_workflow import (
    PodcastGeneratorService,
    PodcastRequest,
    PodcastEpisode,
    ExtractionError,
    DialogueTurn,  # Defined in podcast_workflow
    SourceAnalysis # Also defined in podcast_workflow
)
from app.llm_service import LLMNotInitializedError

# Mock the actual services that PodcastGeneratorService depends on
# We need to patch where they are *looked up*, which is in app.podcast_workflow
@patch('app.podcast_workflow.LLMService', new_callable=MagicMock)
@patch('app.podcast_workflow.GoogleCloudTtsService', new_callable=MagicMock)
class TestPodcastGeneratorService:

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

        # PodcastGeneratorService will call llm_service.generate_text_async for script generation.
        # It then parses the returned string (assumed JSON here) into DialogueTurn objects.
        mock_script_string_from_llm = '[{"speaker_id": "Host", "text": "Podcast script based on PDF.", "speaker_gender": "neutral"}]'
        # Ensure generate_text_async is treated as an AsyncMock
        if not isinstance(self.service.llm_service.generate_text_async, AsyncMock):
            self.service.llm_service.generate_text_async = AsyncMock()
        self.service.llm_service.generate_text_async.return_value = mock_script_string_from_llm
        
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
                assert episode.title == "Placeholder Title" # Matches placeholder in workflow
                assert episode.transcript == extracted_pdf_text[:500] + "... (truncated for placeholder)" # Matches placeholder in workflow
                assert episode.audio_filepath.startswith(tmpdir) # Check it's in the temp dir
                assert episode.audio_filepath.endswith(".mp3")

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
            "counter_arguments_or_perspectives": ["perspective W"]
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
                assert saved_data == llm_analysis_response
                assert episode.llm_source_analysis_path == expected_json_path
        
        mock_extract_url.assert_called_once_with(str(request.source_url)) # Ensure extraction was called
        self.service.llm_service.analyze_source_text_async.assert_called_once_with(extracted_text)

    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_llm_source_analysis_returns_error_dict(self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService):
        extracted_text = "Some text."
        llm_error_response = {"error": "LLM processing failed", "raw_response": "details..."}
        mock_extract_url.return_value = extracted_text
        self.service.llm_service.analyze_source_text_async.return_value = llm_error_response

        request = PodcastRequest(source_url="http://example.com/source")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir:
                mock_tempdir.return_value.__enter__.return_value = tmpdir
                episode = await self.service.generate_podcast_from_source(request)
        
        # Current logic logs error but continues with placeholder, llm_source_analysis_path should be None
        assert episode.llm_source_analysis_path is None
        # Check that the placeholder response is still generated (or adapt if behavior changes)
        assert episode.title == "Placeholder Title" 

    @pytest.mark.asyncio
    @patch('app.podcast_workflow.extract_content_from_url', new_callable=AsyncMock)
    async def test_llm_source_analysis_pydantic_error(self, mock_extract_url, MockGoogleCloudTtsService, MockLLMService):
        extracted_text = "Some text."
        # This dict will cause Pydantic validation error for SourceAnalysis (facts should be List[str])
        llm_malformed_response = {"key_themes": ["theme"], "facts": "not a list"} 
        mock_extract_url.return_value = extracted_text
        self.service.llm_service.analyze_source_text_async.return_value = llm_malformed_response

        request = PodcastRequest(source_url="http://example.com/source")
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch('app.podcast_workflow.tempfile.TemporaryDirectory') as mock_tempdir:
                mock_tempdir.return_value.__enter__.return_value = tmpdir
                episode = await self.service.generate_podcast_from_source(request)

        assert episode.llm_source_analysis_path is None
        assert episode.title == "Placeholder Title" # Still returns placeholder for now

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
