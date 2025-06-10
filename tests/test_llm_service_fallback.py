"""
Test suite for LLM Service Fallback Methods
Tests the new Pydantic AI fallback methods in GeminiService.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, AsyncMock
from pydantic import ValidationError

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.llm_service import GeminiService
from app.podcast_models import PodcastDialogue, DialogueTurn, PodcastOutline, OutlineSegment


class TestGeminiServiceFallback:
    """Test GeminiService fallback methods"""
    
    @pytest.fixture
    def mock_gemini_service(self):
        """Create a mock GeminiService for testing"""
        service = GeminiService()
        # Mock the actual LLM client to avoid real API calls
        service._client = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_generate_with_fallback_success(self, mock_gemini_service):
        """Test successful Pydantic AI structured output generation"""
        # Mock a successful Pydantic AI response
        mock_response = PodcastDialogue(turns=[
            DialogueTurn(
                turn_id=1,
                speaker_id="Host", 
                speaker_gender="Female",
                text="Welcome to our show!",
                source_mentions=[]
            )
        ])
        
        with patch.object(mock_gemini_service, 'generate_text_async', return_value=mock_response):
            result = await mock_gemini_service.generate_with_fallback(
                prompt="Generate dialogue",
                result_type=PodcastDialogue
            )
            
        assert isinstance(result, PodcastDialogue)
        assert result.turn_count == 1
        assert result.turns[0].speaker_id == "Host"
    
    @pytest.mark.asyncio 
    async def test_generate_with_fallback_validation_error(self, mock_gemini_service):
        """Test fallback when Pydantic AI returns invalid data"""
        # Mock Pydantic AI to raise ValidationError first, then return JSON
        mock_fallback_response = json.dumps([
            {"turn_id": 1, "speaker_id": "Host", "text": "Fallback response"}
        ])
        
        # First call raises ValidationError, second call returns JSON
        with patch.object(mock_gemini_service, 'generate_text_async', side_effect=[
            ValidationError.from_exception_data("test", []),
            mock_fallback_response
        ]):
            result = await mock_gemini_service.generate_with_fallback(
                prompt="Generate dialogue",
                result_type=PodcastDialogue
            )
                
        # Should return the JSON string from fallback
        assert isinstance(result, str)
        assert "Fallback response" in result
    
    def test_parse_json_with_validation_valid_json(self, mock_gemini_service):
        """Test parsing valid JSON with Pydantic validation"""
        valid_json = json.dumps([
            {"turn_id": 1, "speaker_id": "Host", "text": "Hello"},
            {"turn_id": 2, "speaker_id": "Guest", "text": "Hi there"}
        ])
        
        result = mock_gemini_service.parse_json_with_validation(
            json_text=valid_json,
            target_type=DialogueTurn
        )
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert isinstance(result[0], DialogueTurn)
        assert result[0].speaker_id == "Host"
        assert result[1].speaker_id == "Guest"
    
    def test_parse_json_with_validation_invalid_json(self, mock_gemini_service):
        """Test parsing invalid JSON gracefully"""
        invalid_json = "{ malformed json structure"
        
        result = mock_gemini_service.parse_json_with_validation(
            json_text=invalid_json,
            target_type=DialogueTurn
        )
        
        assert result is None  # Should return None on error
    
    def test_parse_json_with_validation_validation_error(self, mock_gemini_service):
        """Test handling Pydantic validation errors"""
        # JSON that parses but fails validation (missing required fields)
        invalid_structure_json = json.dumps([
            {"turn_id": 1}  # Missing required speaker_id and text
        ])
        
        result = mock_gemini_service.parse_json_with_validation(
            json_text=invalid_structure_json,
            target_type=DialogueTurn
        )
        
        assert result is None  # Should return None on validation error
    
    def test_parse_json_with_validation_empty_data(self, mock_gemini_service):
        """Test parsing empty or None data"""
        # Test empty string
        result1 = mock_gemini_service.parse_json_with_validation("", DialogueTurn)
        assert result1 is None
        
        # Test None (convert to empty string first)
        result2 = mock_gemini_service.parse_json_with_validation("", DialogueTurn)
        assert result2 is None


class TestLLMServiceIntegration:
    """Test integration scenarios with LLM service"""
    
    @pytest.fixture
    def mock_gemini_service(self):
        """Create a mock GeminiService for testing"""
        service = GeminiService()
        service._client = Mock()
        return service
    
    @pytest.mark.asyncio
    async def test_outline_generation_with_fallback(self, mock_gemini_service):
        """Test outline generation with fallback to JSON parsing"""
        # Test that outline generation can fallback gracefully
        outline_json = json.dumps({
            "title": "Test Podcast",
            "segments": [
                {
                    "segment_id": 1,
                    "title": "Introduction",
                    "description": "Opening segment",
                    "source_mentions": []
                }
            ]
        })
        
        # First call raises ValidationError, second call returns JSON
        with patch.object(mock_gemini_service, 'generate_text_async', side_effect=[
            ValidationError.from_exception_data("test", []),
            outline_json
        ]):
            result = await mock_gemini_service.generate_with_fallback(
                prompt="Generate outline",
                result_type=PodcastOutline
            )
                
        # Should return JSON string from fallback
        assert isinstance(result, str)
        assert "Test Podcast" in result
        assert "Introduction" in result
    
    @pytest.mark.asyncio
    async def test_dialogue_generation_with_fallback(self, mock_gemini_service):
        """Test dialogue generation with fallback to JSON parsing"""
        # Test that dialogue generation can fallback gracefully
        dialogue_json = json.dumps([
            {
                "turn_id": 1,
                "speaker_id": "Host",
                "speaker_gender": "Female", 
                "text": "Welcome listeners!",
                "source_mentions": ["Intro script"]
            },
            {
                "turn_id": 2,
                "speaker_id": "Expert",
                "speaker_gender": "Male",
                "text": "Thank you for having me on the show.",
                "source_mentions": []
            }
        ])
        
        # First call raises ValidationError, second call returns JSON
        with patch.object(mock_gemini_service, 'generate_text_async', side_effect=[
            ValidationError.from_exception_data("test", []),
            dialogue_json
        ]):
            result = await mock_gemini_service.generate_with_fallback(
                prompt="Generate dialogue",
                result_type=PodcastDialogue
            )
                
        # Should return JSON string from fallback
        assert isinstance(result, str)
        assert "Welcome listeners" in result
        assert "Thank you for having me" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
