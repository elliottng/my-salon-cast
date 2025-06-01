"""
Test the extended PersonaResearch model.
This verifies that the new fields added for MCP integration work as expected.
"""
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.podcast_models import PersonaResearch


def test_persona_research_basic():
    """Test that the basic PersonaResearch model still works as expected."""
    persona = PersonaResearch(
        person_id="socrates",
        name="Socrates",
        detailed_profile="Ancient Greek philosopher known for the Socratic method."
    )
    
    assert persona.person_id == "socrates"
    assert persona.name == "Socrates"
    assert "Ancient Greek philosopher" in persona.detailed_profile
    
    # New fields should be None by default
    assert persona.invented_name is None
    assert persona.gender is None
    assert persona.tts_voice_id is None
    assert persona.source_context is None
    assert persona.creation_date is None
    
    # Test serialization to dict
    persona_dict = persona.dict()
    assert "person_id" in persona_dict
    assert "invented_name" in persona_dict
    assert persona_dict["invented_name"] is None


def test_persona_research_extended():
    """Test the extended PersonaResearch model with all fields populated."""
    now = datetime.now()
    persona = PersonaResearch(
        person_id="socrates",
        name="Socrates",
        detailed_profile="Ancient Greek philosopher known for the Socratic method.",
        invented_name="Sam",
        gender="Male",
        tts_voice_id="en-US-Standard-D",
        source_context="Philosophy text about Socratic dialogues",
        creation_date=now
    )
    
    assert persona.person_id == "socrates"
    assert persona.invented_name == "Sam"
    assert persona.gender == "Male"
    assert persona.tts_voice_id == "en-US-Standard-D"
    assert persona.source_context == "Philosophy text about Socratic dialogues"
    assert persona.creation_date == now
    
    # Test serialization to dict
    persona_dict = persona.dict()
    assert persona_dict["invented_name"] == "Sam"
    assert persona_dict["gender"] == "Male"
    
    # Test JSON serialization
    import json
    persona_json = persona.json()
    parsed = json.loads(persona_json)
    assert parsed["invented_name"] == "Sam"
    assert parsed["gender"] == "Male"


def test_persona_research_partial():
    """Test that we can populate just some of the extended fields."""
    persona = PersonaResearch(
        person_id="socrates",
        name="Socrates",
        detailed_profile="Ancient Greek philosopher known for the Socratic method.",
        invented_name="Sam",
        gender="Male",
    )
    
    assert persona.person_id == "socrates"
    assert persona.invented_name == "Sam"
    assert persona.gender == "Male"
    assert persona.tts_voice_id is None
    assert persona.source_context is None
    assert persona.creation_date is None


if __name__ == "__main__":
    print("Running PersonaResearch model tests...")
    test_persona_research_basic()
    test_persona_research_extended()
    test_persona_research_partial()
    print("All tests passed!")
