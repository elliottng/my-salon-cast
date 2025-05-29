class LLMProcessingError(Exception):
    """Custom exception for errors during LLM response processing."""
    pass

class ExtractionError(Exception):
    """Custom exception for errors during content extraction."""
    pass

class LLMNotInitializedError(Exception):
    """Custom exception for when the LLM service is not initialized."""
    pass

class TTSNotInitializedError(Exception):
    """Custom exception for when the TTS service is not initialized."""
    pass

class AudioGenerationError(Exception):
    """Custom exception for errors during audio generation or processing."""
    pass
