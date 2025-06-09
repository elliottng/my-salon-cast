"""
OAuth 2.0 Authentication Middleware for MySalonCast MCP Server

Protects MCP endpoints with Bearer token authentication while keeping
health and OAuth endpoints publicly accessible.
"""

import logging
import os
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.authentication import AuthenticationBackend, AuthCredentials, SimpleUser

logger = logging.getLogger(__name__)


class ApiKeyAuthenticationBackend(AuthenticationBackend):
    """API key Bearer token authentication backend"""

    async def authenticate(self, conn):
        """Authenticate request using API key Bearer token"""
        try:
            # Check for Authorization header
            authorization = conn.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None

            token = authorization[7:]  # Remove "Bearer " prefix

            # Check against configured API keys
            valid_api_keys = self._get_valid_api_keys()

            if token in valid_api_keys:
                # Create authenticated user with full scopes for API key
                credentials = AuthCredentials(["mcp.read", "mcp.write", "admin"])
                user = SimpleUser(valid_api_keys[token])
                return credentials, user

            return None

        except Exception as e:
            logger.error(f"API key authentication failed: {e}")
            return None

    def _get_valid_api_keys(self) -> dict:
        """Get valid API keys from environment"""
        api_keys = {}

        # Primary API key for production use
        primary_key = os.getenv("MYSALONCAST_API_KEY")
        if primary_key:
            api_keys[primary_key] = "api-client"

        # Development API key for local testing
        dev_key = os.getenv("MYSALONCAST_DEV_API_KEY", "dev-key-12345")
        if os.getenv("ENVIRONMENT", "local") == "local":
            api_keys[dev_key] = "dev-client"

        # CI/CD API key for automated testing
        ci_key = os.getenv("MYSALONCAST_CI_API_KEY")
        if ci_key:
            api_keys[ci_key] = "ci-client"

        return api_keys


class OAuthAuthenticationBackend(AuthenticationBackend):
    """OAuth Bearer token authentication backend"""

    async def authenticate(self, conn):
        """Authenticate request using OAuth Bearer token"""
        try:
            from app.oauth_models import get_oauth_storage

            # Check for Authorization header
            authorization = conn.headers.get("Authorization")
            if not authorization or not authorization.startswith("Bearer "):
                return None

            token = authorization[7:]  # Remove "Bearer " prefix

            # Validate OAuth token
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


class HybridAuthenticationBackend(AuthenticationBackend):
    """Hybrid authentication supporting both OAuth and API keys"""

    def __init__(self):
        self.oauth_backend = OAuthAuthenticationBackend()
        self.api_key_backend = ApiKeyAuthenticationBackend()

    async def authenticate(self, conn):
        """Try OAuth first, then API key authentication"""
        # Try OAuth authentication first
        oauth_result = await self.oauth_backend.authenticate(conn)
        if oauth_result:
            return oauth_result

        # Fall back to API key authentication
        api_key_result = await self.api_key_backend.authenticate(conn)
        if api_key_result:
            return api_key_result

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
        """Process request with hybrid authentication protection"""

        # Skip authentication in local development environment
        environment = os.getenv("ENVIRONMENT", "local")
        if environment == "local":
            logger.debug("Skipping authentication in local development mode")
            return await call_next(request)

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
                    "error_description": "Valid Bearer token (OAuth or API key) required for MCP SSE access"
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
                    "error_description": "Valid Bearer token (OAuth or API key) required for MCP access"
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
        """Authenticate request using hybrid backend"""
        backend = HybridAuthenticationBackend()
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
