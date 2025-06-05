"""
OAuth 2.0 Authentication Middleware for MySalonCast MCP Server

Protects MCP endpoints with Bearer token authentication while keeping
health and OAuth endpoints publicly accessible.
"""

import logging
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.authentication import AuthenticationBackend, AuthCredentials, SimpleUser

logger = logging.getLogger(__name__)


class OAuthAuthenticationBackend(AuthenticationBackend):
    """OAuth Bearer token authentication backend"""
    
    async def authenticate(self, request: Request):
        """Authenticate request using Bearer token"""
        try:
            from app.oauth_models import get_oauth_storage
            
            # Check for Authorization header
            authorization = request.headers.get("Authorization")
            if not authorization:
                return None
            
            # Parse Bearer token
            if not authorization.startswith("Bearer "):
                return None
            
            token = authorization[7:]  # Remove "Bearer " prefix
            
            # Validate token
            oauth_storage = get_oauth_storage()
            access_token = oauth_storage.validate_token(token)
            
            if not access_token:
                return None
            
            # Create authenticated user with scopes
            scopes = access_token.scope.split()
            credentials = AuthCredentials(scopes)
            user = SimpleUser(access_token.client_id)
            
            return credentials, user
            
        except Exception as e:
            logger.error(f"OAuth authentication failed: {e}")
            return None


class OAuthMiddleware(BaseHTTPMiddleware):
    """OAuth middleware that protects MCP endpoints"""
    
    # Endpoints that don't require authentication
    PUBLIC_PATHS = {
        "/health",
        "/.well-known/oauth-authorization-server",
        "/auth/authorize", 
        "/auth/token",
        "/auth/consent"
    }
    
    # Paths that require OAuth authentication
    PROTECTED_PATHS = {
        "/resources",  # MCP resources
        "/tools",  # MCP tools
        "/prompts"  # MCP prompts
    }
    
    async def dispatch(self, request: Request, call_next):
        """Process request with OAuth protection"""
        
        # Get request path
        path = request.url.path
        
        # Allow public endpoints
        if path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # Allow OPTIONS requests (CORS preflight) without authentication
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Special handling for SSE endpoint - authenticate once then allow streaming
        if path == "/sse":
            # Check authentication for SSE connection initiation
            auth_result = await self._authenticate_request(request)
            if not auth_result:
                return JSONResponse({
                    "error": "unauthorized", 
                    "error_description": "Valid Bearer token required for MCP SSE access"
                }, status_code=401, headers={
                    "WWW-Authenticate": "Bearer"
                })
            
            # Add auth info to request state for SSE connection
            credentials, user = auth_result
            request.state.user = user
            request.state.credentials = credentials
            
            # Pass through to SSE handler without further middleware interference
            return await call_next(request)
        
        # Check if this is a protected MCP endpoint
        is_protected = any(path.startswith(protected) for protected in self.PROTECTED_PATHS)
        
        if is_protected:
            # Require authentication for MCP endpoints
            auth_result = await self._authenticate_request(request)
            if not auth_result:
                return JSONResponse({
                    "error": "unauthorized",
                    "error_description": "Valid Bearer token required for MCP access"
                }, status_code=401, headers={
                    "WWW-Authenticate": "Bearer"
                })
            
            # Add auth info to request state
            credentials, user = auth_result
            request.state.user = user
            request.state.credentials = credentials
        
        # Process request
        return await call_next(request)
    
    async def _authenticate_request(self, request: Request):
        """Authenticate request using OAuth backend"""
        backend = OAuthAuthenticationBackend()
        return await backend.authenticate(request)


def require_scope(required_scope: str):
    """Decorator to require specific OAuth scope"""
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            # Check if user is authenticated
            if not hasattr(request.state, 'credentials'):
                return JSONResponse({
                    "error": "unauthorized",
                    "error_description": "Authentication required"
                }, status_code=401)
            
            # Check if user has required scope
            if required_scope not in request.state.credentials.scopes:
                return JSONResponse({
                    "error": "forbidden", 
                    "error_description": f"Scope '{required_scope}' required"
                }, status_code=403)
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


def get_authenticated_client(request: Request) -> Optional[str]:
    """Get authenticated client ID from request"""
    if hasattr(request.state, 'user'):
        return request.state.user.display_name
    return None


def get_client_scopes(request: Request) -> list:
    """Get authenticated client scopes from request"""
    if hasattr(request.state, 'credentials'):
        return list(request.state.credentials.scopes)
    return []
