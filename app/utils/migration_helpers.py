"""
Migration helper functions for safely converting legacy JSON string data to Pydantic objects.
These helpers enable gradual migration and error isolation during the Pydantic AI transition.
"""
import json
import logging
from typing import List, Optional, Union

from app.podcast_models import SourceAnalysis, PersonaResearch

logger = logging.getLogger(__name__)


def parse_source_analyses_safe(json_data: Union[str, List[dict], List[SourceAnalysis]]) -> List[SourceAnalysis]:
    """
    Safely convert source analysis data to List[SourceAnalysis] objects.
    
    Args:
        json_data: Can be JSON string, list of dicts, or already parsed objects
        
    Returns:
        List[SourceAnalysis]: Parsed objects, empty list on error
    """
    if not json_data:
        return []
    
    # Already parsed objects
    if isinstance(json_data, list) and all(isinstance(item, SourceAnalysis) for item in json_data):
        return json_data
    
    try:
        # Handle JSON string
        if isinstance(json_data, str):
            parsed_data = json.loads(json_data)
        else:
            parsed_data = json_data
            
        # Convert list of dicts to SourceAnalysis objects
        if isinstance(parsed_data, list):
            return [SourceAnalysis(**item) for item in parsed_data]
        else:
            logger.warning(f"Expected list but got {type(parsed_data)}: {parsed_data}")
            return []
            
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse source analyses: {e}")
        return []


def parse_persona_research_safe(json_data: Union[str, List[dict], List[PersonaResearch]]) -> List[PersonaResearch]:
    """
    Safely convert persona research data to List[PersonaResearch] objects.
    
    Args:
        json_data: Can be JSON string, list of dicts, or already parsed objects
        
    Returns:
        List[PersonaResearch]: Parsed objects, empty list on error
    """
    if not json_data:
        return []
    
    # Already parsed objects
    if isinstance(json_data, list) and all(isinstance(item, PersonaResearch) for item in json_data):
        return json_data
    
    try:
        # Handle JSON string
        if isinstance(json_data, str):
            parsed_data = json.loads(json_data)
        else:
            parsed_data = json_data
            
        # Convert list of dicts to PersonaResearch objects
        if isinstance(parsed_data, list):
            return [PersonaResearch(**item) for item in parsed_data]
        else:
            logger.warning(f"Expected list but got {type(parsed_data)}: {parsed_data}")
            return []
            
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse persona research: {e}")
        return []


def get_persona_by_id(persona_research_list: List[PersonaResearch], person_id: str) -> Optional[PersonaResearch]:
    """
    Helper to find a persona by ID from a list of PersonaResearch objects.
    Replaces the need for persona_details_map lookups.
    
    Args:
        persona_research_list: List of PersonaResearch objects
        person_id: The person_id to search for
        
    Returns:
        PersonaResearch object if found, None otherwise
    """
    for persona in persona_research_list:
        if persona.person_id == person_id:
            return persona
    
    logger.warning(f"Persona with ID '{person_id}' not found in research list")
    return None


def convert_legacy_dialogue_json(json_data: Union[str, List[dict]]) -> List[dict]:
    """
    Helper to safely convert legacy dialogue JSON strings to list of dicts.
    Used during transition period before full Pydantic AI migration.
    
    Args:
        json_data: JSON string or list of dicts
        
    Returns:
        List[dict]: Dialogue turn dictionaries, empty list on error
    """
    if not json_data:
        return []
    
    try:
        # Handle JSON string
        if isinstance(json_data, str):
            parsed_data = json.loads(json_data)
        else:
            parsed_data = json_data
            
        # Ensure we have a list
        if isinstance(parsed_data, list):
            return parsed_data
        else:
            logger.warning(f"Expected list but got {type(parsed_data)}: {parsed_data}")
            return []
            
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.error(f"Failed to parse dialogue JSON: {e}")
        return []
