"""
Test suite for Workflow Integration
Tests that the existing workflow components still work with the new Pydantic infrastructure.
"""

import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, AsyncMock

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.podcast_models import (
    PodcastRequest, 
    SourceAnalysis, 
    PersonaResearch, 
    PodcastDialogue,
    DialogueTurn,
    PodcastOutline,
    OutlineSegment,
    PodcastEpisode
)
from app.utils.migration_helpers import (
    parse_source_analyses_safe,
    parse_persona_research_safe,
    get_persona_by_id,
    convert_legacy_dialogue_json
)


class TestWorkflowDataIntegration:
    """Test that workflow components can handle the new data structures"""
    
    def test_podcast_request_with_pydantic_objects(self):
        """Test PodcastRequest can work with Pydantic objects"""
        request = PodcastRequest(
            source_urls=["https://example.com/article1", "https://example.com/article2"],
            prominent_persons=["tech_expert", "industry_analyst"],
            desired_podcast_length_str="15 minutes"
        )
        
        assert request.has_valid_sources is True
        assert len(request.source_urls or []) == 2
        assert len(request.prominent_persons or []) == 2
        assert request.desired_podcast_length_str == "15 minutes"
        
    def test_source_analysis_integration(self):
        """Test SourceAnalysis objects work in the workflow context"""
        source_analyses = [
            SourceAnalysis(
                summary_points=["AI breakthrough in healthcare", "New diagnostic tools"],
                detailed_analysis="Comprehensive analysis of AI applications in medical diagnosis"
            ),
            SourceAnalysis(
                summary_points=["Market trends", "Investment patterns"],
                detailed_analysis="Analysis of venture capital investment in AI startups"
            )
        ]
        
        # Test that we can aggregate data from multiple sources
        all_points = []
        for sa in source_analyses:
            all_points.extend(sa.summary_points)
        
        assert len(all_points) == 4
        assert "AI breakthrough in healthcare" in all_points
        assert "Market trends" in all_points
        
    def test_persona_research_integration(self):
        """Test PersonaResearch objects work in the workflow context"""
        personas = [
            PersonaResearch(
                person_id="dr_smith",
                name="Dr. Sarah Smith",
                detailed_profile="AI researcher with focus on healthcare applications",
                invented_name="Dr. Innovation",
                gender="Female",
                tts_voice_id="en-US-Jenny-Neural"
            ),
            PersonaResearch(
                person_id="prof_jones",
                name="Prof. Michael Jones", 
                detailed_profile="Technology analyst and investment advisor",
                invented_name="Prof. Insight",
                gender="Male",
                tts_voice_id="en-US-Guy-Neural"
            )
        ]
        
        # Test persona lookup functionality
        found_persona = get_persona_by_id(personas, "dr_smith")
        assert found_persona is not None
        assert found_persona.name == "Dr. Sarah Smith"
        assert found_persona.invented_name == "Dr. Innovation"
        
        # Test voice selection
        voices = [p.tts_voice_id for p in personas if p.tts_voice_id]
        assert len(voices) == 2
        assert "en-US-Jenny-Neural" in voices
        
    def test_dialogue_workflow_integration(self):
        """Test PodcastDialogue works in the workflow context"""
        dialogue = PodcastDialogue(turns=[
            DialogueTurn(
                turn_id=1,
                speaker_id="Host",
                speaker_gender="Female",
                text="Welcome to our podcast about AI innovations in healthcare!",
                source_mentions=["Healthcare AI Report 2024"]
            ),
            DialogueTurn(
                turn_id=2,
                speaker_id="Dr_Innovation",
                speaker_gender="Female", 
                text="Thank you for having me. The potential for AI in diagnostics is tremendous.",
                source_mentions=["Medical AI Research", "Diagnostic Tools Study"]
            ),
            DialogueTurn(
                turn_id=3,
                speaker_id="Prof_Insight",
                speaker_gender="Male",
                text="I agree. From an investment perspective, we're seeing unprecedented growth.",
                source_mentions=["VC Investment Report", "Market Analysis Q4"]
            )
        ])
        
        # Test dialogue properties for workflow use
        assert dialogue.turn_count == 3
        assert dialogue.speaker_list == ["Host", "Dr_Innovation", "Prof_Insight"] 
        assert dialogue.total_word_count > 0
        assert dialogue.estimated_duration_seconds > 0
        
        # Test transcript generation for final episode
        transcript = dialogue.to_transcript()
        assert "Welcome to our podcast" in transcript
        assert "Dr_Innovation:" in transcript
        assert "Prof_Insight:" in transcript
        
    def test_podcast_episode_with_dialogue(self):
        """Test PodcastEpisode can be created with PodcastDialogue"""
        dialogue = PodcastDialogue(turns=[
            DialogueTurn(
                turn_id=1,
                speaker_id="Host",
                text="This is our podcast episode.",
                source_mentions=[]
            )
        ])
        
        episode = PodcastEpisode(
            title="Test Episode",
            summary="A test episode summary",
            transcript=dialogue.to_transcript(),  # Use dialogue's transcript method
            audio_filepath="",
            source_attributions=[],
            warnings=[]
        )
        
        assert episode.title == "Test Episode"
        assert "This is our podcast episode" in episode.transcript
        assert episode.audio_filepath == ""


class TestLegacyDataCompatibility:
    """Test that legacy JSON data can be migrated to new Pydantic objects"""
    
    def test_legacy_source_analysis_migration(self):
        """Test migrating legacy source analysis JSON"""
        legacy_json = json.dumps([
            {
                "summary_points": ["Legacy point 1", "Legacy point 2"],
                "detailed_analysis": "Legacy detailed analysis content"
            }
        ])
        
        migrated = parse_source_analyses_safe(legacy_json)
        
        assert len(migrated) == 1
        assert isinstance(migrated[0], SourceAnalysis)
        assert migrated[0].summary_points == ["Legacy point 1", "Legacy point 2"]
        assert "Legacy detailed analysis" in migrated[0].detailed_analysis
        
    def test_legacy_persona_research_migration(self):
        """Test migrating legacy persona research JSON"""
        legacy_json = json.dumps([
            {
                "person_id": "legacy_expert",
                "name": "Legacy Expert Name",
                "detailed_profile": "Legacy expert profile information"
            }
        ])
        
        migrated = parse_persona_research_safe(legacy_json)
        
        assert len(migrated) == 1
        assert isinstance(migrated[0], PersonaResearch)
        assert migrated[0].person_id == "legacy_expert"
        assert migrated[0].name == "Legacy Expert Name"
        
    def test_legacy_dialogue_migration(self):
        """Test migrating legacy dialogue JSON"""
        legacy_json = json.dumps([
            {"turn_id": 1, "speaker_id": "Host", "text": "Legacy host text"},
            {"turn_id": 2, "speaker_id": "Expert", "text": "Legacy expert text"}
        ])
        
        migrated_data = convert_legacy_dialogue_json(legacy_json)
        
        assert len(migrated_data) == 2
        assert migrated_data[0]["speaker_id"] == "Host"
        assert migrated_data[1]["speaker_id"] == "Expert"
        
        # Test conversion to PodcastDialogue
        turns = [DialogueTurn(**turn_data) for turn_data in migrated_data]
        dialogue = PodcastDialogue(turns=turns)
        
        assert dialogue.turn_count == 2
        assert "Legacy host text" in dialogue.to_transcript()
        assert "Legacy expert text" in dialogue.to_transcript()


class TestWorkflowErrorHandling:
    """Test error handling in workflow components"""
    
    def test_invalid_source_analysis_handling(self):
        """Test handling of invalid source analysis data"""
        invalid_json = '{"invalid": "structure"}'
        
        result = parse_source_analyses_safe(invalid_json)
        
        # Should return empty list, not crash
        assert result == []
        
    def test_invalid_persona_research_handling(self):
        """Test handling of invalid persona research data"""
        invalid_json = '{"missing_required_fields": true}'
        
        result = parse_persona_research_safe(invalid_json)
        
        # Should return empty list, not crash  
        assert result == []
        
    def test_empty_dialogue_handling(self):
        """Test handling of empty dialogue"""
        empty_dialogue = PodcastDialogue(turns=[])
        
        assert empty_dialogue.turn_count == 0
        assert empty_dialogue.speaker_list == []
        assert empty_dialogue.to_transcript() == ""
        assert empty_dialogue.estimated_duration_seconds == 0
        
        # Should still work in episode creation
        episode = PodcastEpisode(
            title="Empty Episode",
            summary="Empty summary",
            transcript=empty_dialogue.to_transcript(),
            audio_filepath="",
            source_attributions=[],
            warnings=[]
        )
        
        assert episode.transcript == ""
        assert episode.audio_filepath == ""


class TestFilePathIntegration:
    """Test that file path handling still works with new objects"""
    
    def test_episode_file_paths(self):
        """Test that PodcastEpisode file paths work correctly"""
        episode = PodcastEpisode(
            title="Test Episode",
            summary="Test summary",
            transcript="Host: Hello\nGuest: Hi there",
            audio_filepath="/tmp/test_audio.mp3",
            source_attributions=[],
            warnings=[]
        )
        
        # Test cloud path detection using is_cloud_path method
        assert episode.is_cloud_path("gs://bucket/audio.mp3") is True
        assert episode.is_cloud_path("https://example.com/audio.mp3") is True
        assert episode.is_cloud_path("/local/path/audio.mp3") is False
        
        # Test that episode maintains its properties
        assert episode.title == "Test Episode"
        assert episode.audio_filepath == "/tmp/test_audio.mp3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
