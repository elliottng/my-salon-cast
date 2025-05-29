import pytest
import asyncio
import os
import json
import logging
import tempfile
from unittest.mock import patch, MagicMock, AsyncMock

from app.podcast_workflow import PodcastGeneratorService, PodcastRequest
from app.content_extraction import extract_content_from_url, extract_text_from_pdf_path
from app.common_exceptions import ExtractionError

# Configure logging to show detailed logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger()

@pytest.mark.asyncio
async def test_debug_podcast_generation():
    """
    A debug test that runs the actual podcast generation with minimal mocking
    to trace execution flow and find where it might be exiting prematurely.
    """
    logger.info("DEBUG TEST: Starting podcast generation debug test")
    
    # Instantiate the real service (no mocks for now)
    service = PodcastGeneratorService()
    
    # Mock only the content extraction to use a small, stable source
    with patch('app.content_extraction.extract_content_from_url', autospec=True) as mock_extract:
        # Return simple test content
        mock_extract.return_value = asyncio.Future()
        mock_extract.return_value.set_result(
            "This is a test podcast source. It contains some facts that could be used in a podcast."
        )
        
        # Create request with simple test data
        request = PodcastRequest(
            source_url="https://example.com/test",
            prominent_persons=["Host"],
            desired_podcast_length_str="1 minute"
        )
        
        logger.info("DEBUG TEST: About to call generate_podcast_from_source")
        try:
            # Non-tempdir version that won't clean up, for debugging purposes
            episode = await service.generate_podcast_from_source(request)
            logger.info(f"DEBUG TEST: generate_podcast_from_source completed. Episode title: {episode.title}")
            logger.info(f"DEBUG TEST: Warnings: {episode.warnings}")
            
            # Print summary of the episode
            print("\n--- Debug Test Results ---")
            print(f"Title: {episode.title}")
            print(f"Summary: {episode.summary}")
            print(f"Audio file: {episode.audio_filepath}")
            print(f"Source analysis path: {episode.llm_source_analysis_path}")
            print(f"Dialogue turns path: {episode.llm_dialogue_turns_path}")
            print(f"Number of warnings: {len(episode.warnings)}")
            if episode.warnings:
                print("\nWarnings:")
                for i, warning in enumerate(episode.warnings, 1):
                    print(f"  {i}. {warning}")
                    
            # Verify if the script progressed to generate audio files
            if episode.dialogue_turn_audio_paths:
                print(f"\nGenerated {len(episode.dialogue_turn_audio_paths)} audio files")
                for path in episode.dialogue_turn_audio_paths:
                    print(f"  - {path}")
            else:
                print("\nNo audio files were generated")
                
            return episode
            
        except Exception as e:
            logger.error(f"DEBUG TEST: Error during podcast generation: {e}", exc_info=True)
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    # When run directly, execute the test
    asyncio.run(test_debug_podcast_generation())
