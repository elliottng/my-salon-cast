"""
Test suite for Phase 2: Pydantic Data Flow Testing
Tests the new Pydantic object flow and migration helpers before making workflow changes.
"""

import pytest
import json
import sys
import os
from typing import List
from unittest.mock import Mock, patch

# Add the project root to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.podcast_models import (
    PodcastDialogue, 
    DialogueTurn, 
    SourceAnalysis, 
    PersonaResearch, 
    OutlineSegment,
    PodcastOutline
)
from app.utils.migration_helpers import (
    parse_source_analyses_safe,
    parse_persona_research_safe,
    get_persona_by_id,
    convert_legacy_dialogue_json
)


class TestPodcastDialogueModel:
    """Test PodcastDialogue model functionality"""
    
    def test_podcast_dialogue_creation(self):
        """Test basic PodcastDialogue creation and properties"""
        turns = [
            DialogueTurn(
                turn_id=1,
                speaker_id="Host",
                speaker_gender="Female", 
                text="Welcome to our podcast about technology innovations!",
                source_mentions=["Tech Report 2024"]
            ),
            DialogueTurn(
                turn_id=2,
                speaker_id="Expert_Johnson", 
                speaker_gender="Male",
                text="Thank you for having me. The advances in AI are remarkable.",
                source_mentions=["AI Research Paper", "Industry Analysis"]
            ),
            DialogueTurn(
                turn_id=3,
                speaker_id="Host",
                speaker_gender="Female",
                text="Can you elaborate on the practical applications?",
                source_mentions=[]
            )
        ]
        
        dialogue = PodcastDialogue(turns=turns)
        
        # Test properties
        assert dialogue.turn_count == 3
        assert dialogue.speaker_list == ["Host", "Expert_Johnson"]
        assert dialogue.total_word_count > 0  # Should count words from all turns
        assert dialogue.estimated_duration_seconds > 0  # Should estimate based on word count
        
        # Test transcript generation
        transcript = dialogue.to_transcript()
        assert "Host: Welcome to our podcast" in transcript
        assert "Expert_Johnson: Thank you" in transcript
        assert "Host: Can you elaborate" in transcript
        
    def test_empty_dialogue(self):
        """Test PodcastDialogue with empty turns"""
        dialogue = PodcastDialogue(turns=[])
        
        assert dialogue.turn_count == 0
        assert dialogue.speaker_list == []
        assert dialogue.total_word_count == 0
        assert dialogue.estimated_duration_seconds == 0
        assert dialogue.to_transcript() == ""
        
    def test_single_speaker_dialogue(self):
        """Test dialogue with only one speaker"""
        turns = [
            DialogueTurn(turn_id=1, speaker_id="Narrator", text="This is a monologue.", source_mentions=[]),
            DialogueTurn(turn_id=2, speaker_id="Narrator", text="It continues here.", source_mentions=[])
        ]
        
        dialogue = PodcastDialogue(turns=turns)
        
        assert dialogue.turn_count == 2
        assert dialogue.speaker_list == ["Narrator"]
        assert "monologue" in dialogue.to_transcript()
        

class TestMigrationHelpers:
    """Test migration helper functions"""
    
    def test_parse_source_analyses_safe_valid_json(self):
        """Test parsing valid source analysis JSON"""
        valid_json = json.dumps([
            {
                "summary_points": ["Key point 1", "Key point 2"],
                "detailed_analysis": "This is a detailed analysis of the source material."
            },
            {
                "summary_points": ["Another point"],
                "detailed_analysis": "Another detailed analysis."
            }
        ])
        
        result = parse_source_analyses_safe(valid_json)
        
        assert len(result) == 2
        assert isinstance(result[0], SourceAnalysis)
        assert isinstance(result[1], SourceAnalysis)
        assert result[0].summary_points == ["Key point 1", "Key point 2"]
        assert "detailed analysis" in result[0].detailed_analysis
        
    def test_parse_source_analyses_safe_invalid_json(self):
        """Test parsing invalid JSON gracefully"""
        invalid_json = "{ invalid json structure"
        
        result = parse_source_analyses_safe(invalid_json)
        
        assert result == []  # Should return empty list on error
        
    def test_parse_source_analyses_safe_empty_data(self):
        """Test parsing empty/None data"""
        assert parse_source_analyses_safe("") == []
        assert parse_source_analyses_safe(None) == []
        assert parse_source_analyses_safe([]) == []
        
    def test_parse_source_analyses_safe_already_parsed(self):
        """Test when data is already SourceAnalysis objects"""
        source_analysis = SourceAnalysis(
            summary_points=["Test point"],
            detailed_analysis="Test analysis"
        )
        
        result = parse_source_analyses_safe([source_analysis])
        
        assert len(result) == 1
        assert result[0] is source_analysis  # Should return same objects
        
    def test_parse_persona_research_safe_valid_json(self):
        """Test parsing valid persona research JSON"""
        valid_json = json.dumps([
            {
                "person_id": "expert1",
                "name": "Dr. Jane Smith",
                "detailed_profile": "AI researcher with expertise in machine learning."
            },
            {
                "person_id": "expert2", 
                "name": "Prof. John Doe",
                "detailed_profile": "Technology analyst and industry expert."
            }
        ])
        
        result = parse_persona_research_safe(valid_json)
        
        assert len(result) == 2
        assert isinstance(result[0], PersonaResearch)
        assert result[0].person_id == "expert1"
        assert result[0].name == "Dr. Jane Smith"
        assert result[1].person_id == "expert2"
        
    def test_parse_persona_research_safe_mixed_valid_invalid(self):
        """Test parsing JSON with some invalid entries"""
        mixed_json = json.dumps([
            {
                "person_id": "expert1",
                "name": "Dr. Jane Smith", 
                "detailed_profile": "Valid profile"
            },
            {
                "person_id": "expert2",
                # Missing required 'name' field
                "detailed_profile": "Invalid entry - missing name"
            }
        ])
        
        # Should return empty list due to validation error (graceful handling)
        result = parse_persona_research_safe(mixed_json)
        assert result == []  # Our helper gracefully handles validation errors
        
    def test_get_persona_by_id_existing(self):
        """Test finding existing persona by ID"""
        personas = [
            PersonaResearch(person_id="expert1", name="Dr. Smith", detailed_profile="Profile 1"),
            PersonaResearch(person_id="expert2", name="Prof. Doe", detailed_profile="Profile 2")
        ]
        
        found = get_persona_by_id(personas, "expert1")
        
        assert found is not None
        assert found.person_id == "expert1"
        assert found.name == "Dr. Smith"
        
    def test_get_persona_by_id_nonexistent(self):
        """Test finding non-existent persona by ID"""
        personas = [
            PersonaResearch(person_id="expert1", name="Dr. Smith", detailed_profile="Profile 1")
        ]
        
        found = get_persona_by_id(personas, "nonexistent")
        
        assert found is None
        
    def test_get_persona_by_id_empty_list(self):
        """Test finding persona in empty list"""
        found = get_persona_by_id([], "any_id")
        
        assert found is None
        
    def test_convert_legacy_dialogue_json_valid(self):
        """Test converting valid legacy dialogue JSON"""
        dialogue_json = json.dumps([
            {"turn_id": 1, "speaker_id": "Host", "text": "Hello"},
            {"turn_id": 2, "speaker_id": "Guest", "text": "Hi there"}
        ])
        
        result = convert_legacy_dialogue_json(dialogue_json)
        
        assert len(result) == 2
        assert result[0]["turn_id"] == 1
        assert result[0]["speaker_id"] == "Host"
        assert result[1]["text"] == "Hi there"
        
    def test_convert_legacy_dialogue_json_invalid(self):
        """Test converting invalid legacy dialogue JSON"""
        invalid_json = "{ malformed json"
        
        result = convert_legacy_dialogue_json(invalid_json)
        
        assert result == []


class TestDataFlowIntegration:
    """Test that Pydantic objects flow correctly through the pipeline"""
    
    def test_source_analysis_object_flow(self):
        """Test SourceAnalysis objects maintain integrity through processing"""
        source_analysis = SourceAnalysis(
            summary_points=["Innovation in AI", "Market disruption", "Future trends"],
            detailed_analysis="Comprehensive analysis of technological advances and their market impact."
        )
        
        # Test object serialization/deserialization maintains data
        as_dict = source_analysis.model_dump()
        reconstructed = SourceAnalysis(**as_dict)
        
        assert reconstructed.summary_points == source_analysis.summary_points
        assert reconstructed.detailed_analysis == source_analysis.detailed_analysis
        
    def test_persona_research_object_flow(self):
        """Test PersonaResearch objects maintain integrity through processing"""
        persona = PersonaResearch(
            person_id="tech_expert", 
            name="Dr. Tech Innovator",
            detailed_profile="Leading researcher in emerging technologies with 15 years experience.",
            invented_name="Dr. Innovation",
            gender="Female",
            tts_voice_id="en-US-Jenny-Neural"
        )
        
        # Test object maintains all fields through serialization
        as_dict = persona.model_dump()
        reconstructed = PersonaResearch(**as_dict)
        
        assert reconstructed.person_id == persona.person_id
        assert reconstructed.name == persona.name
        assert reconstructed.invented_name == persona.invented_name
        assert reconstructed.gender == persona.gender
        assert reconstructed.tts_voice_id == persona.tts_voice_id
        
    def test_dialogue_object_flow(self):
        """Test DialogueTurn and PodcastDialogue objects maintain integrity"""
        turns = [
            DialogueTurn(
                turn_id=1,
                speaker_id="Host",
                speaker_gender="Female",
                text="Welcome to our show!",
                source_mentions=["Show intro"]
            ),
            DialogueTurn(
                turn_id=2, 
                speaker_id="Expert",
                speaker_gender="Male",
                text="Thank you for having me.",
                source_mentions=[]
            )
        ]
        
        dialogue = PodcastDialogue(turns=turns)
        
        # Test serialization maintains structure
        as_dict = dialogue.model_dump()
        reconstructed = PodcastDialogue(**as_dict)
        
        assert reconstructed.turn_count == dialogue.turn_count
        assert reconstructed.speaker_list == dialogue.speaker_list
        assert reconstructed.to_transcript() == dialogue.to_transcript()
        
    def test_no_json_serialization_in_main_flow(self):
        """Test that main flow uses objects, not JSON strings"""
        # This test ensures we're working with objects, not JSON strings
        source_analyses = [
            SourceAnalysis(summary_points=["Point 1"], detailed_analysis="Analysis 1"),
            SourceAnalysis(summary_points=["Point 2"], detailed_analysis="Analysis 2")
        ]
        
        personas = [
            PersonaResearch(person_id="p1", name="Person 1", detailed_profile="Profile 1"),
            PersonaResearch(person_id="p2", name="Person 2", detailed_profile="Profile 2")
        ]
        
        # Test that we can work with these as objects directly
        assert all(isinstance(sa, SourceAnalysis) for sa in source_analyses)
        assert all(isinstance(p, PersonaResearch) for p in personas)
        
        # Test persona lookup works with objects
        found_persona = get_persona_by_id(personas, "p1")
        assert found_persona is not None
        assert found_persona.name == "Person 1"


class TestErrorCases:
    """Test error handling and edge cases"""
    
    def test_missing_required_fields(self):
        """Test handling of missing required fields"""
        with pytest.raises(Exception):  # ValidationError
            DialogueTurn(turn_id=1)  # Missing required fields
            
    def test_invalid_data_types(self):
        """Test handling of invalid data types"""
        with pytest.raises(Exception):  # ValidationError
            SourceAnalysis(
                summary_points="Not a list",  # Should be List[str]
                detailed_analysis=123  # Should be str
            )
            
    def test_empty_lists_handling(self):
        """Test handling of empty lists"""
        # These should work fine
        dialogue = PodcastDialogue(turns=[])
        assert dialogue.turn_count == 0
        
        empty_source_analyses = parse_source_analyses_safe("[]")
        assert empty_source_analyses == []
        
    def test_edge_case_zero_personas(self):
        """Test workflow with zero personas"""
        personas = parse_persona_research_safe("[]")
        assert len(personas) == 0
        
        found = get_persona_by_id(personas, "any_id")
        assert found is None
        
    def test_edge_case_single_persona(self):
        """Test workflow with single persona"""
        single_persona_json = json.dumps([{
            "person_id": "solo_expert",
            "name": "Dr. Solo",
            "detailed_profile": "The only expert we need."
        }])
        
        personas = parse_persona_research_safe(single_persona_json)
        assert len(personas) == 1
        
        found = get_persona_by_id(personas, "solo_expert")
        assert found is not None
        assert found.name == "Dr. Solo"
        
    def test_edge_case_multiple_personas(self):
        """Test workflow with multiple personas"""
        multi_persona_json = json.dumps([
            {"person_id": "expert1", "name": "Dr. First", "detailed_profile": "Profile 1"},
            {"person_id": "expert2", "name": "Dr. Second", "detailed_profile": "Profile 2"},  
            {"person_id": "expert3", "name": "Dr. Third", "detailed_profile": "Profile 3"}
        ])
        
        personas = parse_persona_research_safe(multi_persona_json)
        assert len(personas) == 3
        
        # Test finding each persona
        for i, expected_id in enumerate(["expert1", "expert2", "expert3"], 1):
            found = get_persona_by_id(personas, expected_id)
            assert found is not None
            assert f"Dr. {['First', 'Second', 'Third'][i-1]}" in found.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
