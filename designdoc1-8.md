MySalonCast MCP Integration Design Document
Task 1.8: Model Context Protocol Server and API Implementation
Version: 1.1
 Date: Jun 2025
 Authors: Elliott & Claude
 Status: Design Phase, now slightly stale vs. the implementation plan in todo.md

1. Executive Summary
This document outlines the design and implementation strategy for exposing MySalonCast's podcast generation capabilities through the Model Context Protocol (MCP), enabling seamless integration with AI assistants like Claude Desktop. The approach leverages FastMCP's capabilities to create a unified system serving both traditional REST API clients and MCP-enabled AI tools, with MCP tools and resources providing a superset of functionality beyond the core API.
Key Objectives:
Enable Claude Desktop users to generate podcasts through natural conversation
Provide rich, interactive access to intermediate outputs (persona profiles, outlines, transcripts)
Support real-time status monitoring for long-running podcast generation
Build foundation for advanced persona interaction features

2. Technical Architecture Overview
2.1 Unified FastAPI + MCP Approach (Revised)
Strategy: Unified approach with MCP server capabilities as a superset of REST API endpoints.
Two Implementation Paths:
Core API Endpoints → Auto-converted to MCP using FastMCP.from_fastapi()
MCP-Specific Features → Directly implemented using FastMCP decorators
from fastmcp import FastMCP
from app.main import app  # Existing FastAPI application

# Path 1: Auto-generate MCP server from FastAPI endpoints
mcp_server = FastMCP.from_fastapi(
    app=app,
    name="MySalonCast MCP Server",
    route_maps=[
        RouteMap(methods=["POST"], pattern=r".*/generate.*", mcp_type=MCPType.TOOL),
        RouteMap(methods=["GET"], pattern=r".*/status.*", mcp_type=MCPType.RESOURCE),
    ]
)

# Path 2: Add MCP-specific tools/resources directly
@mcp_server.resource("persona://{podcast_id}/{person_id}/profile")
async def get_persona_profile(podcast_id: str, person_id: str) -> PersonaResearch:
    """Direct MCP resource - no REST API equivalent"""
    
@mcp_server.tool()
async def subscribe_to_podcast_updates(podcast_id: str) -> dict:
    """Direct MCP tool - optimized for AI interaction"""

Benefits:
Minimal API surface for web/mobile clients
Rich MCP interface for AI agents
No code duplication for shared functionality
MCP-optimized features don't clutter REST API
2.2 Deployment Architecture (Revised)
Unified MCP Server Architecture
┌─────────────────────────────────────────────────────────┐
│                FastMCP Unified Server                   │
├─────────────────────────────────────────────────────────┤
│  AUTO-GENERATED from FastAPI:                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │           FastAPI App                           │   │
│  │  • POST /api/v1/podcasts/generate → Tool       │   │
│  │  • GET  /api/v1/podcasts/{id}/status → Resource│   │
│  │  • GET  /api/v1/podcasts/{id}/audio → Resource │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  DIRECT FastMCP IMPLEMENTATION:                        │
│  • @mcp.resource("persona://{id}/{person}/profile")    │
│  • @mcp.resource("podcast://{id}/outline")             │
│  • @mcp.tool() subscribe_to_podcast_updates()          │
│  • @mcp.prompt() create_podcast_from_url()             │
├─────────────────────────────────────────────────────────┤
│  SHARED ACCESS TO:                                      │
│  • PodcastGeneratorService                             │
│  • Database/File Storage                               │
│  • LLM & TTS Services                                  │
└─────────────────────────────────────────────────────────┘

Client Access Patterns
┌─────────────────┐    ┌─────────────────────────────────┐
│   Web/Mobile    │    │        Claude Desktop          │
│     Clients     │    │        (MCP Client)             │
└─────────────────┘    └─────────────────────────────────┘
         │                               │
         │ HTTP REST                     │ MCP Protocol
         │                               │ (STDIO/HTTP)
         ▼                               ▼
┌─────────────────────────────────────────────────────────┐
│              FastAPI + FastMCP Server                  │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │   REST API      │  │       MCP Interface         │  │
│  │   Endpoints     │  │   (Auto + Direct Impl)     │  │
│  └─────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘


3. Data Structure Enhancements
3.1 Enhanced PersonaResearch Model & Current Implementation Analysis
Current Gender/Name Assignment Implementation
Location: app/podcast_workflow.py, lines ~180-220 in generate_podcast_from_source()
Current Process:
# 4.5. Assign Invented Names and Genders to Personas
MALE_INVENTED_NAMES = ["Liam", "Noah", "Oliver", ...]
FEMALE_INVENTED_NAMES = ["Olivia", "Emma", "Charlotte", ...]

persona_details_map: dict[str, dict[str, str]] = {}
persona_details_map["Host"] = {
    "invented_name": "Host",
    "gender": "Male", 
    "real_name": "Host"
}

# Round-robin gender assignment for personas
for pr_json_str in persona_research_docs_content:
    pr_data = json.loads(pr_json_str)
    persona_research_obj_temp = PersonaResearch(**pr_data)
    person_id = persona_research_obj_temp.person_id
    real_name = persona_research_obj_temp.name
    
    # Hardcoded gender assignment (not working reliably)
    assigned_gender = "neutral"  # Always defaults to neutral!
    
    # Name selection from lists...
    persona_details_map[person_id] = {
        "invented_name": invented_name,
        "gender": assigned_gender, 
        "real_name": real_name
    }

Problems with Current Implementation:
Not persisted in PersonaResearch model - only exists in temporary persona_details_map
Gender assignment broken - always defaults to "neutral"
Workflow-level logic - should be model-level for MCP access
Round-robin assignment - not deterministic across sessions
Required Code Changes for MCP Integration
Impact Assessment: This touches multiple components and requires careful migration.
Files Requiring Changes:
app/podcast_models.py - Extend PersonaResearch model
app/llm_service.py - Update research_persona_async() to assign names/voices
app/podcast_workflow.py - Remove temporary assignment logic
app/tts_service.py - Use PersonaResearch.tts_voice_id directly
app/audio_utils.py - Update DialogueTurn creation
Migration Strategy:
Phase 1: Extend PersonaResearch model with new fields
Phase 2: Update LLM service to assign names/voices during persona creation
Phase 3: Migrate workflow to use model fields instead of temporary mapping
Phase 4: Update TTS and audio services to use model fields
Phase 5: Remove legacy persona_details_map logic
Proposed Enhanced PersonaResearch Model:
class PersonaResearch(BaseModel):
    # Existing fields (unchanged)
    person_id: str
    name: str    
    detailed_profile: str
    
    # New fields for MCP integration
    invented_name: str      # Consistent invented name (e.g., "Alex" for Einstein)
    gender: str            # For TTS voice selection ("Male", "Female", "Neutral")
    tts_voice_id: str      # Pre-selected Google TTS voice ID
    source_context: str    # Description of sources used for profile
    creation_date: datetime

3.2 PodcastOutline Model
Current Structure: ✅ No changes needed - existing model is suitable for MCP access
title_suggestion, summary_suggestion, segments[]
Built-in format_for_display() method supports multiple output formats
3.3 PodcastStatus Model Use Cases (Expanded)
Primary Use Cases:
1. Real-Time Progress Monitoring
# User in Claude: "What's the status of my podcast?"
status = await get_podcast_status("podcast_123")
# Returns: "67% complete - Currently writing dialogue for segment 2 of 4"

2. Conditional Feature Access
# Claude checks what's available before offering options
if status.personas_available:
    # "Your persona profiles are ready! Would you like to discuss Einstein's viewpoint?"
if status.outline_available:
    # "The podcast outline is complete. Would you like to review it?"

3. Error Recovery Workflows
# When status == "error"
# Claude can:
# - Display user-friendly error message
# - Suggest retry options
# - Provide technical details if requested

4. Smart Polling Optimization
# Claude uses estimated_completion_minutes to:
# - Set appropriate check intervals
# - Inform user of expected wait times
# - Avoid excessive API calls

5. Progress-Based User Engagement
# Different conversation options based on progress:
# - Early stages: Discuss source material, modify personas
# - Mid stages: Review outline, adjust structure
# - Late stages: Preview transcript, prepare for completion

Complete PodcastStatus Model:
class PodcastStatus(BaseModel):
    podcast_id: str
    status: Literal[
        "queued", "analyzing_sources", "researching_personas",
        "personas_complete", "creating_outline", "outline_complete",
        "creating_dialogue", "dialogue_complete", "generating_transcript",
        "transcript_complete", "generating_audio", "audio_complete",
        "completed", "error"
    ]
    progress_percentage: int              # 0-100
    current_step_detail: str             # Human-readable current action
    estimated_completion_minutes: Optional[int]
    error_details: Optional[str]         # For error status
    detailed_log: List[str]              # Comprehensive log entries
    personas_available: List[str]        # person_ids of completed profiles
    outline_available: bool
    dialogue_available: bool
    transcript_available: bool
    audio_available: bool
    last_updated: datetime


4. MCP Server Design: v.1 vs v.1.1 (Revised)
4.1 MCP Server v.1: FastAPI Auto-Generated Components
Implementation: Auto-converted from REST API endpoints using FastMCP.from_fastapi()
Tools (from POST endpoints):
# Auto-generated from: POST /api/v1/podcasts/generate
generate_podcast(source_urls, prominent_persons, desired_length_minutes) -> dict

Primary Use Case: "Generate a podcast from this article featuring Einstein and Feynman"
Resources (from GET endpoints):
# Auto-generated from: GET /api/v1/podcasts/{id}/status    
podcast_status(podcast_id) -> PodcastStatus

# Auto-generated from: GET /api/v1/podcasts/{id}/metadata
podcast_metadata(podcast_id) -> dict

Primary Use Case: "What's the status of my podcast?" / "Show me the podcast details"
4.2 MCP Server v.1.1: Direct FastMCP Implementation
Implementation: Custom tools/resources with no REST API equivalents
Rich Content Resources:
@mcp.resource("persona://{podcast_id}/{person_id}/profile")
async def get_persona_profile(podcast_id: str, person_id: str) -> PersonaResearch

Primary Use Case: "What would Einstein think about quantum computing?" (conversational persona access)
@mcp.resource("podcast://{podcast_id}/outline") 
async def get_podcast_outline(podcast_id: str) -> PodcastOutline

Primary Use Case: "Show me the podcast structure and let's discuss segment timing"
@mcp.resource("podcast://{podcast_id}/transcript")
async def get_podcast_transcript(podcast_id: str) -> str

Primary Use Case: "Display the full transcript so I can review the dialogue quality"
AI-Optimized Tools:
@mcp.tool()
async def subscribe_to_podcast_updates(podcast_id: str) -> dict

Primary Use Case: "Keep me updated on progress" (optimizes subsequent status calls)
@mcp.tool()
async def extract_content_preview(source_url: str) -> dict

Primary Use Case: "What's in this article before I make a podcast?" (content validation)
Interaction Templates:
@mcp.prompt()
def create_podcast_from_url(url: str, personas: str, length: str) -> str

Primary Use Case: Natural language podcast requests with guided parameter input
@mcp.prompt()
def discuss_persona_viewpoint(podcast_id: str, person_id: str, topic: str) -> str

Primary Use Case: Structured persona discussion prompts for consistent AI interaction

5. Status Updates and Error Reporting
5.1 User-Facing Status Workflow
Primary Status States:
queued → Initial state after request submission
analyzing_sources → Content extraction and processing
researching_personas → LLM persona research in progress
personas_complete → PersonaResearch objects available via MCP
creating_outline → LLM outline generation in progress
outline_complete → PodcastOutline available via MCP
creating_dialogue → LLM dialogue writing in progress
dialogue_complete → Dialogue turns generated
generating_transcript → Transcript compilation
transcript_complete → Transcript available via MCP
generating_audio → TTS and audio stitching
audio_complete → Audio file available for download
completed → All outputs available
error → Generation failed with detailed error information
5.2 Subscribe to Updates Implementation
Problem: MCP doesn't support push notifications to Claude Desktop.
Solution: Smart polling optimization:
Server-side subscription tracking: Store user interest in specific podcast jobs
Optimized status responses: Provide more detailed information for subscribed jobs
Smart timing guidance: Return recommended next check times based on current progress
Proactive error notification: Immediate status updates when errors occur
Implementation Pattern:
# User subscribes to updates
await subscribe_to_podcast_updates("podcast_123")

# Server optimizes subsequent status calls
status = await get_podcast_status("podcast_123")
# Returns enhanced status with timing guidance for subscribers


6. Claude Desktop Integration
6.1 MCP Configuration
Claude Desktop MCP Server Configuration:
{
  "mcpServers": {
    "mysaloncast": {
      "command": "python",
      "args": ["-m", "mysaloncast.mcp_server"],
      "env": {
        "FASTMCP_SERVER_HOST": "localhost",
        "FASTMCP_SERVER_PORT": "8000"
      }
    }
  }
}

6.2 User Experience Workflows
Workflow 1: Basic Podcast Generation
User: "Generate a podcast from https://example.com/article with Einstein and Feynman discussing it"
Claude calls generate_podcast tool
Claude provides podcast_id and polling guidance
User: "What's the status?" → Claude calls get_podcast_status
When complete: Claude provides download URLs and transcript access
Workflow 2: Interactive Persona Discussion
After podcast generation completes
User: "What would Einstein think about quantum entanglement?"
Claude accesses persona://{podcast_id}/einstein/profile resource
Claude provides detailed response based on PersonaResearch profile
Ongoing conversation leverages persona context
Workflow 3: Outline Review and Discussion
User: "Show me the podcast outline"
Claude accesses podcast://{podcast_id}/outline resource
Claude displays formatted outline using format_for_display()
User: "Can we spend more time on segment 2?"
Claude discusses outline modifications (future: outline editing tools)

7. To Do List
See separate file

Critical Path: Data model migration (Task 1.8.2) must complete before MCP implementation

8. Future Roadmap (MCP Server v.2)
8.1 Standalone Persona Research
@mcp.tool()
async def create_persona_profile(
    person_name: str, 
    source_urls: List[str], 
    topic_focus: str
) -> PersonaResearch:
    """Generate PersonaResearch profile without podcast creation"""

8.2 Wikipedia Entity Management
@mcp.tool()
async def search_wikipedia_entities(query: str) -> List[dict]:
    """Find and disambiguate prominent persons"""

@mcp.tool() 
async def select_wikipedia_entity(entity_id: str) -> dict:
    """Confirm specific Wikipedia entity selection"""

8.3 Voice Chat Preparation
Enhanced TTS voice selection and consistency
Persona conversation context optimization
Integration with future voice chat protocols

9. Technical Considerations
9.1 Audio File Delivery
Challenge: Claude Desktop cannot trigger automatic downloads through MCP.
Solution: URL-based download approach:
MCP tools return clickable download URLs
Audio files served via existing FastAPI static file serving
Clear user instructions for manual download
9.2 Long-Running Process Management
Challenge: Podcast generation takes 2-5 minutes.
Solution: Async job queue with comprehensive status tracking:
Immediate job ID return from generation requests
Detailed status resources with progress indicators
Smart polling recommendations to optimize user experience
9.3 Error Handling Strategy
Graceful degradation when individual components fail
Comprehensive logging for development phase debugging
User-friendly error messages with recovery suggestions
MCP resource availability even when generation fails partially

10. Success Metrics
10.1 Technical Metrics
MCP server response times < 200ms for status queries
Successful end-to-end podcast generation rate > 95%
Claude Desktop integration setup success rate > 90%
10.2 User Experience Metrics
Average time from request to podcast completion
User engagement with persona profile resources
Error recovery and retry success rates
10.3 Development Metrics
Code reuse percentage between REST API and MCP server
Test coverage for MCP tools and resources
Documentation completeness and clarity

Conclusion
This design leverages FastMCP's dual capabilities to create a powerful, unified system that exposes MySalonCast's unique podcast generation capabilities to AI assistants. The approach minimizes code duplication while maximizing functionality through a superset of MCP-specific features, providing a solid foundation for rich interactive experiences with AI agents like Claude Desktop.
The phased implementation approach ensures rapid delivery of core functionality while maintaining flexibility for future enhancements like standalone persona research and voice chat capabilities.
