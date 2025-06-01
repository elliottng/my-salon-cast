import logging
from fastmcp import FastMCP
from app.podcast_workflow import PodcastGeneratorService, PodcastRequest
from app.podcast_models import PodcastEpisode
# For clarity, even if instantiated by PodcastGeneratorService
from app.llm_service import GeminiService
from app.tts_service import GoogleCloudTtsService

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize services required by MCP tools
# PodcastGeneratorService internally initializes GeminiService and GoogleCloudTtsService
# Ensure any required environment variables (e.g., API keys) are set for these services.
podcast_service = PodcastGeneratorService()
logger.info("PodcastGeneratorService initialized for MCP.")

# Initialize the FastMCP server
# The name is a unique identifier for your server.
# The description provides context to the LLM about the server's purpose.
mcp_server = FastMCP(
    name="MySalonCastMCP",
    description="This MCP server manages tasks related to the MySalonCast podcast generation workflow.",
)

# Example: Define a simple command (we can add more complex ones later)
@mcp_server.command()
async def hello(name: str = "world") -> str:
    """Returns a simple greeting."""
    logger.info(f"Command 'hello' called with name: {name}")
    return f"Hello, {name}!"


@mcp_server.tool()
async def generate_podcast(request_data: PodcastRequest) -> PodcastEpisode:
    """
    Generates a podcast episode based on the provided source URLs or PDF path.

    This tool orchestrates the entire podcast generation workflow, including:
    1. Content extraction from sources.
    2. Source analysis using an LLM.
    3. Persona research for prominent figures.
    4. Podcast outline generation.
    5. Dialogue script generation.
    6. Text-to-speech conversion for dialogue.
    7. Audio mixing and final episode production.

    Args:
        request_data: A PodcastRequest object containing details like source URLs,
                      PDF path, desired length, custom prompts, etc.

    Returns:
        A PodcastEpisode object containing the title, summary, transcript, audio filepath,
        and other metadata of the generated podcast. May return an error-like PodcastEpisode
        if generation fails.
    """
    logger.info(f"MCP Tool 'generate_podcast' called with request_data: {{request_data.model_dump_json(indent=2)}})
    try:
        episode = await podcast_service.generate_podcast_from_source(request_data=request_data)
        logger.info(f"MCP Tool 'generate_podcast' completed successfully. Episode title: {episode.title}")
        return episode
    except Exception as e:
        logger.error(f"MCP Tool 'generate_podcast' failed: {e}", exc_info=True)
        return PodcastEpisode(
            title="Error During Podcast Generation",
            summary=f"An error occurred: {str(e)}",
            transcript="",
            audio_filepath="",
            source_attributions=[],
            warnings=[f"Tool execution failed: {str(e)}"]
        )


@mcp_server.on_event("startup")
async def startup_event():
    logger.info("MySalonCastMCP server has started up successfully.")
    # Here you could add logic like connecting to databases, loading initial resources, etc.

@mcp_server.on_event("shutdown")
async def shutdown_event():
    logger.info("MySalonCastMCP server is shutting down.")
    # Here you could add cleanup logic like closing database connections.

if __name__ == "__main__":
    # This allows running the server directly for development/testing.
    # In a production setup, you might use a different way to run it (e.g., via Uvicorn programmatically).
    import uvicorn
    logger.info("Starting MySalonCastMCP server...")
    uvicorn.run(mcp_server.app, host="0.0.0.0", port=8000)
