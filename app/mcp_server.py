import logging
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from app.podcast_workflow import PodcastGeneratorService
from app.podcast_models import PodcastRequest, PodcastEpisode
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner
from app.tts_service import GoogleCloudTtsService
from app.llm_service import GeminiService
from app.config import setup_production_environment, get_config, get_server_config, get_health_status
from fastmcp.prompts.prompt import Message
from pydantic import Field
from typing import Literal, Optional, List
from datetime import datetime
from starlette.responses import JSONResponse, StreamingResponse, Response
from starlette.routing import Route
import os
import tempfile
import base64
import mimetypes
from pathlib import Path
import logging
import json
import asyncio
from app.mcp_descriptions import (
    PROMPT_DESCRIPTIONS,
    TOOL_DESCRIPTIONS,
    RESOURCE_DESCRIPTIONS,
    MANIFEST_DESCRIPTIONS
)
from app.mcp_utils import (
    validate_task_id, validate_person_id, download_and_parse_json, 
    build_resource_response, get_task_status_or_error, 
    build_job_status_response, build_job_logs_response, build_job_warnings_response,
    handle_resource_error, collect_file_info,
    build_podcast_transcript_response, build_podcast_audio_response
)
from app.logging_utils import log_mcp_tool_call, log_mcp_resource_access

# Setup production environment and logging
config = get_config()
production_config = setup_production_environment()
logger = logging.getLogger(__name__)

# Initialize services required by MCP tools
podcast_service = PodcastGeneratorService()
status_manager = get_status_manager()
task_runner = get_task_runner()
logger.info("Services initialized for MCP.")

# Initialize the FastMCP server with correct API
mcp = FastMCP("MySalonCast Podcast Generator")

# =============================================================================
# CREATE THE HTTP APP FOR UVICORN
# =============================================================================
app = mcp.http_app(transport="sse")

# Add CORS middleware first (before OAuth middleware)
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

# Add OAuth middleware to protect MCP endpoints
from app.oauth_middleware import OAuthMiddleware
app.add_middleware(OAuthMiddleware)

# =============================================================================
# MCP PROMPTS
# =============================================================================

@mcp.prompt(description=PROMPT_DESCRIPTIONS["create_podcast_from_url"])
def create_podcast_from_url(
    urls: List[str],
    personas: str = "Einstein, Marie Curie",
    length: str = "10 minutes",
) -> str:
    url_list = ", ".join(urls)
    personas_list = ", ".join([f'"{p.strip()}"' for p in personas.split(",")])
    return f"""I'd like to create a podcast discussion from these URLs: {url_list}

Please generate a conversational podcast featuring these personas: {personas}

Requirements:
- Length: {length}
- Style: Natural conversation with different perspectives from each persona
- Include interesting insights and contrasting viewpoints

Use the MySalonCast tools to:
1. First, generate the podcast: generate_podcast_async with source_urls=[{url_list}], prominent_persons=[{personas_list}], podcast_length="{length}"
2. Monitor progress with: get_task_status using the returned task_id
3. Access results via the podcast resources when complete

What aspects of this content would you like the personas to focus on?"""

@mcp.prompt(description=PROMPT_DESCRIPTIONS["discuss_persona_viewpoint"])
def discuss_persona_viewpoint(
    task_id: str,
    person_id: str,
) -> str:
    return f"""Let's explore {person_id}'s viewpoints from podcast task {task_id}.

Please use the MySalonCast resource:
research://{task_id}/{person_id}
to review their detailed_profile and background information.

Based on that research, help me understand:
- What key topics are covered in the profile?
- What viewpoints does {person_id} express about those topics?
- How does their background influence these perspectives?
- What questions or follow ups might they raise?"""

@mcp.prompt(description=PROMPT_DESCRIPTIONS["analyze_podcast_content"])
def analyze_podcast_content(
    task_id: str,
    analysis_type: Literal["outline", "transcript", "personas", "summary"] = "summary"
) -> str:
    resource_map = {
        "outline": f"podcast://{task_id}/outline",
        "transcript": f"podcast://{task_id}/transcript", 
        "personas": f"research://{task_id}/[person_id]",
        "summary": f"podcast://{task_id}/metadata"
    }
    
    if analysis_type == "personas":
        return f"""Let's analyze the persona research for this podcast task: {task_id}

First, get the podcast metadata to see available personas: podcast://{task_id}/metadata

Then for each persona, examine their research:
- research://{task_id}/[person_id] (replace [person_id] with actual IDs)

Help me understand:
- What personas were researched for this podcast?
- What are their key characteristics and expertise areas?
- How do their perspectives complement each other?
- What interesting contrasts or synergies exist between them?"""
    
    return f"""Let's analyze the {analysis_type} for podcast task: {task_id}

Please access the resource: {resource_map[analysis_type]}

Based on the {analysis_type} data, help me understand:
- What are the key themes and topics covered?
- How well structured is the content?
- What are the most interesting insights or discussion points?
- Are there any areas that could be enhanced or expanded?

Provide a thoughtful analysis with specific examples from the content."""

# =============================================================================
# MCP TOOLS  
# =============================================================================

# Simple test tool
@mcp.tool(description=TOOL_DESCRIPTIONS["hello"])
async def hello(name: str = "world") -> str:
    logger.info(f"Tool 'hello' called with name: {name}")
    return f"Hello, {name}!"

# Async podcast generation with individual parameters
@mcp.tool(description=TOOL_DESCRIPTIONS["generate_podcast_async"])
async def generate_podcast_async(
    ctx,
    source_urls: List[str] = None,
    source_pdf_path: str = None,
    prominent_persons: List[str] = None,
    podcast_length: str = "10 minutes",
    dialogue_style: str = "conversation",
    custom_prompt: str = None,
    podcast_name: str = None,
    webhook_url: str = None
) -> dict:
    # Use standardized logging
    request_id, client_info = log_mcp_tool_call("generate_podcast_async", ctx)
    
    try:
        # Convert individual parameters to PodcastRequest object
        request = PodcastRequest(
            source_urls=source_urls,
            source_pdf_path=source_pdf_path,
            prominent_persons=prominent_persons,
            desired_podcast_length_str=podcast_length,
            custom_prompt_for_outline=custom_prompt,
            webhook_url=webhook_url
            # Note: dialogue_style and podcast_name don't have direct mappings in PodcastRequest
            # These could be added to PodcastRequest in the future if needed
        )
        
        # Configure generator - it creates its own service instances
        generator = PodcastGeneratorService()
        
        # Use the async generation mode
        task_id = await generator.generate_podcast_async(request)
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": f"Podcast generation started for task: {task_id}",
            "request_details": {
                "source_count": len(request.source_urls) if request.source_urls else 0,
                "has_webhook": bool(request.webhook_url),
                "persona_count": len(request.prominent_persons) if request.prominent_persons else 0
            }
        }
    except Exception as e:
        logger.error(f"[{request_id}] Failed to start podcast generation: {str(e)}")
        raise ToolError(f"Failed to start podcast generation: {str(e)}")

# Get status of async task
@mcp.tool(description=TOOL_DESCRIPTIONS["get_task_status"])
async def get_task_status(ctx, task_id: str) -> dict:
    # Enhanced logging with MCP context 
    request_id = getattr(ctx, 'request_id', 'unknown')
    logger.info(f"[{request_id}] MCP Tool 'get_task_status' called for task_id: {task_id}")
    
    if not task_id or not task_id.strip():
        raise ToolError("task_id is required")
    
    try:
        # Get current status from StatusManager
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            logger.warning(f"[{request_id}] Task {task_id} not found")
            return {
                "task_id": task_id, 
                "status": "not_found",
                "message": f"Task {task_id} not found"
            }
        
        logger.info(f"[{request_id}] Retrieved status for task {task_id}: {status_info.status}")
        return {"status": "success", "data": status_info}
        
    except Exception as e:
        logger.error(f"[{request_id}] Error getting task status: {e}")
        return {
            "task_id": task_id,
            "status": "error", 
            "error": f"Failed to get task status: {str(e)}"
        }

# =============================================================================
# PHASE 4.4: Job Status and Podcast Resources
# =============================================================================

@mcp.resource("jobs://{task_id}/status", description=RESOURCE_DESCRIPTIONS["get_job_status_resource"])
async def get_job_status_resource(task_id: str) -> dict:
    logger.info(f"Resource 'job status' accessed for task_id: {task_id}")
    
    try:
        status_info = await get_task_status_or_error(status_manager, task_id)
        return build_job_status_response(task_id, status_info)
    except Exception as e:
        handle_resource_error(e, task_id, "retrieve job status")

@mcp.resource("jobs://{task_id}/logs", description=RESOURCE_DESCRIPTIONS["get_job_logs_resource"])
async def get_job_logs_resource(task_id: str) -> dict:
    logger.info(f"Resource 'job logs' accessed for task_id: {task_id}")
    
    try:
        status_info = await get_task_status_or_error(status_manager, task_id)
        
        # Extract logs from status info
        logs = status_info.logs if hasattr(status_info, 'logs') and status_info.logs else []
        
        return build_job_logs_response(task_id, logs)
        
    except Exception as e:
        handle_resource_error(e, task_id, "retrieve job logs")

@mcp.resource("jobs://{task_id}/warnings", description=RESOURCE_DESCRIPTIONS["get_job_warnings_resource"])
async def get_job_warnings_resource(task_id: str) -> dict:
    logger.info(f"Resource 'job warnings' accessed for task_id: {task_id}")
    
    try:
        status_info = await get_task_status_or_error(status_manager, task_id)
        
        # Extract warnings from episode data if available
        warnings = []
        if status_info.result_episode and hasattr(status_info.result_episode, 'warnings'):
            warnings = status_info.result_episode.warnings or []
        
        return build_job_warnings_response(task_id, status_info, warnings)
        
    except Exception as e:
        handle_resource_error(e, task_id, "retrieve job warnings")

@mcp.resource("podcast://{task_id}/transcript", description=RESOURCE_DESCRIPTIONS["get_podcast_transcript_resource"])
async def get_podcast_transcript_resource(task_id: str) -> dict:
    logger.info(f"Resource 'podcast transcript' accessed for task_id: {task_id}")
    
    try:
        status_info = await get_task_status_or_error(status_manager, task_id, require_episode=True)
        return build_podcast_transcript_response(task_id, status_info.result_episode)
    except Exception as e:
        handle_resource_error(e, task_id, "retrieve podcast transcript")

@mcp.resource("podcast://{task_id}/audio", description=RESOURCE_DESCRIPTIONS["get_podcast_audio_resource"])
async def get_podcast_audio_resource(task_id: str) -> dict:
    logger.info(f"Resource 'podcast audio' accessed for task_id: {task_id}")
    
    try:
        status_info = await get_task_status_or_error(status_manager, task_id, require_episode=True)
        return build_podcast_audio_response(task_id, status_info.result_episode)
    except Exception as e:
        handle_resource_error(e, task_id, "retrieve podcast audio")

@mcp.resource("outline://{task_id}", description=RESOURCE_DESCRIPTIONS["get_podcast_outline_resource"])
async def get_podcast_outline_resource(task_id: str) -> dict:
    logger.info(f"Resource 'podcast outline' accessed for task_id: {task_id}")
    
    # Basic input validation
    validate_task_id(task_id)
    
    # Get the status manager and fetch the task status
    status_manager = get_status_manager()
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        # Try to get outline from the file path or cloud URL stored in the episode
        outline_data = None
        outline_file_path = status_info.result_episode.llm_podcast_outline_path
        
        if outline_file_path:
            from app.storage import CloudStorageManager
            cloud_storage = CloudStorageManager()
            
            outline_data = await download_and_parse_json(
                cloud_storage,
                outline_file_path,
                "outline"
            )
        
        return build_resource_response(
            task_id=task_id,
            data=outline_data,
            resource_type="outline",
            additional_fields={
                "has_outline": outline_data is not None,
                "outline_file_path": outline_file_path,
                "resource_type": "podcast_outline"
            }
        )
        
    except Exception as e:
        if "Task not found" in str(e):
            raise ToolError(f"Task not found: {task_id}")
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve podcast outline: {str(e)}")

@mcp.resource("research://{task_id}/{person_id}", description=RESOURCE_DESCRIPTIONS["get_persona_research_resource"])
async def get_persona_research_resource(task_id: str, person_id: str) -> dict:
    logger.info(f"Resource 'persona research' accessed for task_id: {task_id}, person_id: {person_id}")
    
    # Basic input validation
    validate_task_id(task_id)
    validate_person_id(person_id)
    
    status_manager = get_status_manager()
    
    try:
        status_info = status_manager.get_status(task_id)
        
        if not status_info:
            raise ToolError(f"Task not found: {task_id}")
        
        if not status_info.result_episode:
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        
        # Build research file path based on available persona research paths
        research_file_path = None
        
        # Check if we have persona research paths available
        if status_info.result_episode and hasattr(status_info.result_episode, 'llm_persona_research_paths') and status_info.result_episode.llm_persona_research_paths:
            # Look for the persona research file for this specific person_id
            import os
            for path in status_info.result_episode.llm_persona_research_paths:
                # Check if this path is for the requested person_id
                if f"persona_research_{person_id}.json" in path:
                    research_file_path = path
                    break
            
            # If no specific path was found but we have research paths, try to infer the directory
            if not research_file_path and status_info.result_episode.llm_persona_research_paths:
                # Get the directory from the first research path
                sample_path = status_info.result_episode.llm_persona_research_paths[0]
                # Extract the directory part
                if '/' in sample_path:
                    dir_path = os.path.dirname(sample_path)
                    research_file_path = os.path.join(dir_path, f"persona_research_{person_id}.json")
                else:
                    # If we can't infer a directory, just use the person_id pattern
                    research_file_path = f"persona_research_{person_id}.json"
        
        # Check if the file exists for the specified person_id
        if research_file_path:
            # Check if the file exists (this is a simplified check, actual existence check would vary)
            import os
            if research_file_path.startswith(("gs://", "http://", "https://")) or os.path.exists(research_file_path):
                logger.info(f"Found persona research file at: {research_file_path}")
            else:
                # File doesn't exist - let's list available person IDs
                available_persons = []
                # Extract task directory from research file path
                task_directory = None
                if research_file_path:
                    import os
                    task_directory = os.path.dirname(research_file_path)
                
                if task_directory and os.path.exists(task_directory):
                    for filename in os.listdir(task_directory):
                        if filename.startswith("persona_research_") and filename.endswith(".json"):
                            available_person_id = filename[17:-5]  # Remove "persona_research_" and ".json"
                            available_persons.append(available_person_id)
                
                if available_persons:
                    raise ToolError(f"Person '{person_id}' not found in task {task_id}. Available persons: {', '.join(available_persons)}")
                else:
                    raise ToolError(f"No persona research files found for task: {task_id}")
        
        # Read and parse the PersonaResearch JSON file or download from cloud
        research_data = None
        file_exists = False
        file_size = 0
        
        if research_file_path:
            from app.storage import CloudStorageManager
            cloud_storage = CloudStorageManager()
            
            research_data = await download_and_parse_json(
                cloud_storage,
                research_file_path,
                "persona research"
            )
            
            if research_data:
                file_exists = True
                # Calculate approximate file size from JSON content
                import json
                file_size = len(json.dumps(research_data).encode('utf-8'))
        
        return build_resource_response(
            task_id=task_id,
            data=research_data,
            resource_type="persona_research",
            additional_fields={
                "person_id": person_id,
                "has_research": research_data is not None,
                "research_file_path": research_file_path,
                "file_exists": file_exists,
                "file_size_bytes": file_size,
                "resource_type": "persona_research"
            }
        )
        
    except Exception as e:
        if "Task not found" in str(e) or "not found in task" in str(e):
            raise
        elif "not available" in str(e):
            raise ToolError(f"Podcast episode not available for task: {task_id}")
        raise ToolError(f"Failed to retrieve persona research: {str(e)}")

# =============================================================================
# OAUTH 2.0 ENDPOINTS
# =============================================================================

# OAuth Discovery Endpoint for Claude.ai integration
async def oauth_discovery(request):
    """
    OAuth 2.0 Authorization Server Metadata endpoint.
    
    RFC 8414 compliant discovery endpoint that returns metadata about the OAuth server.
    Claude.ai uses this endpoint to discover OAuth capabilities and endpoints.
    """
    try:
        # Get the base URL from the request - handle Cloud Run HTTPS forwarding
        scheme = request.url.scheme
        
        # Check for X-Forwarded-Proto header (Cloud Run uses this)
        forwarded_proto = request.headers.get("x-forwarded-proto")
        if forwarded_proto:
            scheme = forwarded_proto
        
        # Force HTTPS for production/staging environments
        if request.url.netloc.endswith(".run.app"):
            scheme = "https"
        
        base_url = f"{scheme}://{request.url.netloc}"
        
        # OAuth 2.0 Authorization Server Metadata
        metadata = {
            "issuer": base_url,
            "authorization_endpoint": f"{base_url}/auth/authorize",
            "token_endpoint": f"{base_url}/auth/token",
            "registration_endpoint": f"{base_url}/auth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "client_credentials"],
            "code_challenge_methods_supported": ["S256"],
            "scopes_supported": ["mcp.read", "mcp.write"],
            "token_endpoint_auth_methods_supported": ["client_secret_post", "client_secret_basic"],
            "introspection_endpoint": f"{base_url}/auth/introspect",
            "revocation_endpoint": f"{base_url}/auth/revoke",
            # Additional metadata for Claude.ai compatibility
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
            "claims_supported": ["iss", "sub", "aud", "exp", "iat", "scope"],
            "request_uri_parameter_supported": False,
            "require_request_uri_registration": False
        }
        
        logger.info(f"OAuth discovery endpoint accessed from: {request.client.host}")
        return JSONResponse(metadata, headers={
            "Content-Type": "application/json",
            "Cache-Control": "public, max-age=3600"  # Cache for 1 hour
        })
        
    except Exception as e:
        logger.error(f"OAuth discovery endpoint failed: {e}")
        return JSONResponse({
            "error": "server_error",
            "error_description": "Internal server error"
        }, status_code=500)

# OAuth Authorization Endpoint
async def oauth_authorize(request):
    """
    OAuth 2.0 Authorization Endpoint
    
    Handles authorization requests from OAuth clients (Claude.ai, MySalonCast webapp).
    Supports auto-approval for Claude.ai and consent screen for webapp.
    """
    try:
        from app.oauth_config import get_oauth_manager
        from app.oauth_models import get_oauth_storage, AuthorizationRequest, AuthorizationCode
        from urllib.parse import parse_qs, urlencode, urlparse
        
        oauth_manager = get_oauth_manager()
        oauth_storage = get_oauth_storage()
        
        # Parse query parameters
        query_params = dict(request.query_params)
        
        # Validate required parameters
        if not query_params.get("client_id"):
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing client_id parameter"
            }, status_code=400)
        
        if not query_params.get("redirect_uri"):
            return JSONResponse({
                "error": "invalid_request", 
                "error_description": "Missing redirect_uri parameter"
            }, status_code=400)
        
        # Validate client
        client_id = query_params["client_id"]
        redirect_uri = query_params["redirect_uri"]
        
        if not oauth_manager.validate_client(client_id, redirect_uri=redirect_uri):
            # Check if this appears to be a Claude.ai client that needs re-registration
            if "claude.ai" in redirect_uri.lower():
                return JSONResponse({
                    "error": "invalid_client",
                    "error_description": "Client registration expired or not found. Please re-register at /auth/register"
                }, status_code=400)
            else:
                return JSONResponse({
                    "error": "invalid_client",
                    "error_description": "Unknown client_id"
                }, status_code=400)
        
        if not oauth_manager.validate_redirect_uri(client_id, redirect_uri):
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Invalid redirect_uri for client"
            }, status_code=400)
        
        # Get optional parameters
        scope = query_params.get("scope", "mcp.read mcp.write")
        state = query_params.get("state")
        code_challenge = query_params.get("code_challenge")
        code_challenge_method = query_params.get("code_challenge_method", "S256")
        
        # Validate PKCE if provided
        if code_challenge and code_challenge_method != "S256":
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Only S256 code_challenge_method supported"
            }, status_code=400)
        
        # Check if client should be auto-approved (Claude.ai)
        if oauth_manager.should_auto_approve(client_id, redirect_uri=redirect_uri):
            # Auto-approve: generate authorization code and redirect
            auth_code = AuthorizationCode(
                client_id=client_id,
                redirect_uri=redirect_uri,
                scope=scope,
                code_challenge=code_challenge,
                state=state
            )
            
            code = oauth_storage.store_auth_code(auth_code)
            
            # Build redirect URL with authorization code
            redirect_params = {"code": code}
            if state:
                redirect_params["state"] = state
            
            redirect_url = f"{redirect_uri}?{urlencode(redirect_params)}"
            
            logger.info(f"Auto-approved OAuth authorization for client: {client_id}")
            
            # Return redirect response
            from starlette.responses import RedirectResponse
            return RedirectResponse(url=redirect_url, status_code=302)
        
        else:
            # Show consent screen for webapp clients
            # For now, return a simple JSON response indicating consent needed
            # TODO: Implement HTML consent screen in future
            return JSONResponse({
                "message": "consent_required",
                "client_id": client_id,
                "scope": scope,
                "redirect_uri": redirect_uri,
                "state": state,
                "consent_url": f"/auth/consent?{urlencode(query_params)}"
            }, status_code=200)
    
    except Exception as e:
        logger.error(f"OAuth authorization endpoint failed: {e}")
        return JSONResponse({
            "error": "server_error",
            "error_description": "Internal server error"
        }, status_code=500)

# OAuth Token Exchange Endpoint
async def oauth_token(request):
    """
    OAuth 2.0 Token Endpoint
    
    Exchanges authorization codes for access tokens.
    Validates client credentials and PKCE if provided.
    """
    try:
        from app.oauth_config import get_oauth_manager
        from app.oauth_models import get_oauth_storage, TokenRequest, TokenResponse, AccessToken, verify_code_challenge
        
        oauth_manager = get_oauth_manager()
        oauth_storage = get_oauth_storage()
        
        # Parse form data
        form_data = await request.form()
        token_request = dict(form_data)
        
        # Validate required parameters
        grant_type = token_request.get("grant_type")
        if grant_type not in ["authorization_code", "client_credentials"]:
            return JSONResponse({
                "error": "unsupported_grant_type",
                "error_description": "Only authorization_code and client_credentials grant types supported"
            }, status_code=400)
        
        client_id = token_request.get("client_id")
        if not client_id:
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing client_id parameter"
            }, status_code=400)
        
        client_secret = token_request.get("client_secret")
        redirect_uri = token_request.get("redirect_uri")
        
        # Validate client credentials
        if not oauth_manager.validate_client(client_id, client_secret, redirect_uri=redirect_uri):
            return JSONResponse({
                "error": "invalid_client",
                "error_description": "Invalid client credentials"
            }, status_code=401)
        
        # Handle client_credentials grant (server-to-server)
        if grant_type == "client_credentials":
            scope = token_request.get("scope", "mcp.read mcp.write")
            
            # Generate access token directly
            token = AccessToken(
                client_id=client_id,
                scope=scope
            )
            
            access_token = oauth_storage.store_access_token(token)
            
            return JSONResponse({
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": scope,
                "refresh_token": None
            })
        
        # Handle authorization_code grant (user-facing)
        code = token_request.get("code")
        if not code:
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing code parameter"
            }, status_code=400)
        
        code_verifier = token_request.get("code_verifier")
        
        # Get and consume authorization code
        auth_code = oauth_storage.consume_auth_code(code)
        if not auth_code:
            return JSONResponse({
                "error": "invalid_grant",
                "error_description": "Invalid or expired authorization code"
            }, status_code=400)
        
        # Validate authorization code parameters
        if auth_code.client_id != client_id:
            return JSONResponse({
                "error": "invalid_grant",
                "error_description": "Authorization code issued to different client"
            }, status_code=400)
        
        if redirect_uri and auth_code.redirect_uri != redirect_uri:
            return JSONResponse({
                "error": "invalid_grant",
                "error_description": "Redirect URI mismatch"
            }, status_code=400)
        
        # Validate PKCE if used
        if auth_code.code_challenge:
            if not code_verifier:
                return JSONResponse({
                    "error": "invalid_request",
                    "error_description": "Missing code_verifier for PKCE"
                }, status_code=400)
            
            if not verify_code_challenge(code_verifier, auth_code.code_challenge):
                return JSONResponse({
                    "error": "invalid_grant",
                    "error_description": "Invalid code_verifier"
                }, status_code=400)
        
        # Generate access token
        access_token = AccessToken(
            client_id=client_id,
            scope=auth_code.scope
        )
        
        token_value = oauth_storage.store_access_token(access_token)
        
        # Return token response
        response = TokenResponse(
            access_token=token_value,
            token_type="Bearer",
            expires_in=3600,  # 1 hour
            scope=auth_code.scope
        )
        
        logger.info(f"Issued access token for client: {client_id}")
        
        return JSONResponse(response.dict())
    
    except Exception as e:
        logger.error(f"OAuth token endpoint failed: {e}")
        return JSONResponse({
            "error": "server_error",
            "error_description": "Internal server error"
        }, status_code=500)

# OAuth Token Introspection Endpoint
async def oauth_introspect(request):
    """
    OAuth 2.0 Token Introspection Endpoint (RFC 7662)
    
    Allows clients to check if a token is valid and get token metadata.
    """
    try:
        from app.oauth_models import get_oauth_storage
        
        oauth_storage = get_oauth_storage()
        
        # Parse form data
        form_data = await request.form()
        token = form_data.get("token")
        
        if not token:
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing token parameter"
            }, status_code=400)
        
        # Validate token
        access_token = oauth_storage.validate_token(token)
        
        if not access_token:
            # Token is invalid/expired
            return JSONResponse({
                "active": False
            })
        
        # Token is valid - return metadata
        response = {
            "active": True,
            "client_id": access_token.client_id,
            "scope": access_token.scope,
            "exp": int(access_token.expires_at.timestamp()),
            "iat": int(access_token.created_at.timestamp())
        }
        
        return JSONResponse(response)
    
    except Exception as e:
        logger.error(f"OAuth introspection endpoint failed: {e}")
        return JSONResponse({
            "error": "server_error",
            "error_description": "Internal server error"
        }, status_code=500)

# OAuth Dynamic Client Registration Endpoint
async def oauth_register(request):
    """
    OAuth 2.0 Dynamic Client Registration Endpoint (RFC 7591)
    
    Allows clients to register themselves with the authorization server.
    """
    try:
        from app.oauth_models import get_oauth_storage, ClientRegistrationRequest, ClientRegistrationResponse
        
        oauth_storage = get_oauth_storage()
        
        # Parse JSON request body
        request_body = await request.json()
        registration_request = ClientRegistrationRequest.parse_obj(request_body)
        
        # Validate client metadata
        if not registration_request.client_name:
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing client_name parameter"
            }, status_code=400)
        
        if not registration_request.redirect_uris:
            return JSONResponse({
                "error": "invalid_request",
                "error_description": "Missing redirect_uris parameter"
            }, status_code=400)
        
        # Register client and generate client ID and secret
        response = oauth_storage.register_client(registration_request)
        
        # Return client registration response
        logger.info(f"Registered new client: {response.client_id}")
        
        return JSONResponse(response.dict())
    
    except Exception as e:
        logger.error(f"OAuth client registration endpoint failed: {e}")
        return JSONResponse({
            "error": "server_error",
            "error_description": "Internal server error"
        }, status_code=500)

# =============================================================================
# HEALTH AND MONITORING ENDPOINTS
# =============================================================================

async def health_check(request):
    """Health check endpoint for Cloud Run and container orchestration."""
    try:
        # Use production configuration health status
        health_status = get_health_status()
        
        # Enhanced service checks
        if podcast_service and status_manager and task_runner:
            health_status["checks"]["services"] = "ok"
        else:
            health_status["status"] = "degraded"
            health_status["checks"]["services"] = "error"
        
        # Return appropriate status code
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(health_status, status_code=status_code)
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status_code=500)

# =============================================================================
# MCP ROOT ENDPOINT
# =============================================================================

async def mcp_root(request):
    """Root endpoint providing MCP server information and manifest."""
    try:
        # Determine base URL with HTTPS enforcement for cloud deployments
        base_url = f"{request.url.scheme}://{request.url.netloc}"
        
        # Force HTTPS for Cloud Run deployments
        if (request.headers.get("x-forwarded-proto") == "https" or 
            ".run.app" in request.url.netloc):
            base_url = f"https://{request.url.netloc}"
        
        manifest = {
            "name": MANIFEST_DESCRIPTIONS["server_name"],
            "description": MANIFEST_DESCRIPTIONS["server_description"],
            "version": "1.0.0",
            "protocol_version": "2024-11-05",
            "capabilities": {
                "resources": True,
                "tools": True,
                "prompts": False,
                "logging": True
            },
            "endpoints": {
                "mcp": {
                    "sse": f"{base_url}/sse",
                    "websocket": None
                },
                "oauth": {
                    "discovery": f"{base_url}/.well-known/oauth-authorization-server",
                    "authorization": f"{base_url}/auth/authorize", 
                    "token": f"{base_url}/auth/token",
                    "introspection": f"{base_url}/auth/introspect",
                    "registration": f"{base_url}/auth/register"
                },
                "health": f"{base_url}/health"
            },
            "features": {
                "podcast_generation": MANIFEST_DESCRIPTIONS["feature_podcast_generation"],
                "content_analysis": MANIFEST_DESCRIPTIONS["feature_content_analysis"], 
                "persona_research": MANIFEST_DESCRIPTIONS["feature_persona_research"],
                "voice_synthesis": MANIFEST_DESCRIPTIONS["feature_voice_synthesis"],
                "cloud_storage": MANIFEST_DESCRIPTIONS["feature_cloud_storage"],
                "workflow_management": MANIFEST_DESCRIPTIONS["feature_workflow_management"]
            },
            "authentication": {
                "type": "hybrid",
                "methods": ["oauth2", "bearer"],
                "required": True,
                "oauth2": {
                    "scopes": ["mcp.read", "mcp.write"],
                    "flows": ["authorization_code", "client_credentials"]
                },
                "bearer": {
                    "description": "API key authentication for server-to-server integration",
                    "scopes": ["mcp.read", "mcp.write", "admin"]
                }
            }
        }
        
        return JSONResponse(manifest)
        
    except Exception as e:
        logger.error(f"Error in MCP root endpoint: {e}")
        return JSONResponse({
            "error": "internal_server_error",
            "message": "Failed to generate MCP manifest",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }, status_code=500)

# =============================================================================
# REGISTER ROUTES
# =============================================================================

# Add OAuth and health routes to the app
mcp_root_route = Route("/", mcp_root, methods=["GET"])
oauth_discovery_route = Route("/.well-known/oauth-authorization-server", oauth_discovery, methods=["GET"])
oauth_authorize_route = Route("/auth/authorize", oauth_authorize, methods=["GET"])
oauth_token_route = Route("/auth/token", oauth_token, methods=["POST"]) 
oauth_introspect_route = Route("/auth/introspect", oauth_introspect, methods=["POST"])
oauth_register_route = Route("/auth/register", oauth_register, methods=["POST"])
health_route = Route("/health", health_check, methods=["GET"])

app.router.routes.extend([mcp_root_route, oauth_discovery_route, oauth_authorize_route, oauth_token_route, oauth_introspect_route, oauth_register_route, health_route])

# =============================================================================
if __name__ == "__main__":
    # Run the server using Starlette/Uvicorn
    import uvicorn
    logger.info("Starting MySalonCast MCP server...")
    
    # Get production configuration
    server_config = get_server_config()
    
    # Run with uvicorn using production configuration
    # IMPORTANT: The MCP server runs on the configured port
    # All client code should connect to this port
    # The MySalonCastMCPClient class in tests/mcp/client.py implements the correct approach
    uvicorn.run(app, **server_config)
