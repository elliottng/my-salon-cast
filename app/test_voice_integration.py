import logging
import asyncio
from app.tts_service import GoogleCloudTtsService
from app.llm_service import GeminiService

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_voice_selection():
    """Test the integration between LLM service and TTS service for voice selection."""
    logger.info("Initializing TTS service...")
    tts_service = GoogleCloudTtsService()
    
    logger.info("Initializing LLM service with TTS service...")
    llm_service = GeminiService(tts_service=tts_service)
    
    # Create a simple test persona for each gender
    test_data = [
        {"person_id": "test1", "person_name": "John Doe", "source_text": "Male philosopher from ancient Greece."},
        {"person_id": "test2", "person_name": "Jane Smith", "source_text": "Female scientist from the 20th century."},
        {"person_id": "test3", "person_name": "Alex Johnson", "source_text": "Non-binary educator from modern times."}
    ]
    
    for data in test_data:
        logger.info(f"Testing persona research for {data['person_name']}...")
        try:
            persona = await llm_service.research_persona_async(
                source_text=data["source_text"],
                person_name=data["person_name"]
            )
            
            # Log the assigned voice parameters
            logger.info(f"Persona details: {persona.name}")
            logger.info(f"  Gender: {persona.gender}")
            logger.info(f"  Voice ID: {persona.tts_voice_id if persona.tts_voice_id else 'None'}")
            
            # Log voice parameters if available
            if persona.tts_voice_params:
                logger.info(f"  Speaking Rate: {persona.tts_voice_params.get('speaking_rate', 'Default')}")
                logger.info(f"  Pitch: {persona.tts_voice_params.get('pitch', 'Default')}")
            else:
                logger.info("  No voice parameters available")
            logger.info("---")
        
        except Exception as e:
            logger.error(f"Error testing persona {data['person_name']}: {str(e)}")
    
    logger.info("Voice selection integration test complete!")

if __name__ == "__main__":
    asyncio.run(test_voice_selection())
