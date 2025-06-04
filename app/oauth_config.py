"""
OAuth 2.0 Client Configuration for MySalonCast MCP Server

This module provides pre-configured OAuth clients for Claude.ai and MySalonCast webapp.
Uses a simplified approach with fixed client credentials and configuration.
"""

import os
import secrets
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class OAuthClient:
    """OAuth client configuration"""
    client_id: str
    client_secret: str
    redirect_uris: List[str]
    auto_approve: bool = False
    scopes: List[str] = None
    description: str = ""
    
    def __post_init__(self):
        if self.scopes is None:
            self.scopes = ["mcp.read", "mcp.write"]


class OAuthClientManager:
    """Manages OAuth client configurations for MySalonCast MCP server"""
    
    def __init__(self):
        self._clients = self._load_clients()
    
    def _load_clients(self) -> Dict[str, OAuthClient]:
        """Load pre-configured OAuth clients"""
        
        # Get client secrets from environment variables
        claude_secret = os.getenv("CLAUDE_CLIENT_SECRET")
        webapp_secret = os.getenv("WEBAPP_CLIENT_SECRET")
        
        # Generate secure secrets if not provided (for development)
        if not claude_secret:
            claude_secret = secrets.token_urlsafe(32)
            print(f"Generated Claude client secret: {claude_secret}")
            print("Set CLAUDE_CLIENT_SECRET environment variable for production")
        
        if not webapp_secret:
            webapp_secret = secrets.token_urlsafe(32)
            print(f"Generated webapp client secret: {webapp_secret}")
            print("Set WEBAPP_CLIENT_SECRET environment variable for production")
        
        return {
            "claude-ai": OAuthClient(
                client_id="claude-ai",
                client_secret=claude_secret,
                redirect_uris=[
                    "https://claude.ai/oauth/callback",
                    "https://claude.ai/api/oauth/callback",
                    "https://api.claude.ai/oauth/callback"
                ],
                auto_approve=True,  # Auto-approve Claude.ai to reduce friction
                scopes=["mcp.read", "mcp.write"],
                description="Claude.ai AI Assistant"
            ),
            "mysaloncast-webapp": OAuthClient(
                client_id="mysaloncast-webapp",
                client_secret=webapp_secret,
                redirect_uris=[
                    "https://mysaloncast.com/oauth/callback",
                    "http://localhost:3000/oauth/callback",  # Local development
                    "http://localhost:5173/oauth/callback"   # Vite dev server
                ],
                auto_approve=False,  # Require consent for webapp
                scopes=["mcp.read", "mcp.write", "admin"],
                description="MySalonCast Web Application"
            )
        }
    
    def get_client(self, client_id: str) -> Optional[OAuthClient]:
        """Get OAuth client by client_id"""
        return self._clients.get(client_id)
    
    def validate_client(self, client_id: str, client_secret: str = None) -> bool:
        """Validate client credentials"""
        client = self.get_client(client_id)
        if not client:
            return False
        
        if client_secret is not None:
            return client.client_secret == client_secret
        
        return True
    
    def validate_redirect_uri(self, client_id: str, redirect_uri: str) -> bool:
        """Validate redirect URI for a client"""
        client = self.get_client(client_id)
        if not client:
            return False
        
        return redirect_uri in client.redirect_uris
    
    def get_client_scopes(self, client_id: str) -> List[str]:
        """Get supported scopes for a client"""
        client = self.get_client(client_id)
        return client.scopes if client else []
    
    def should_auto_approve(self, client_id: str) -> bool:
        """Check if client should be auto-approved (skip consent screen)"""
        client = self.get_client(client_id)
        return client.auto_approve if client else False
    
    def list_clients(self) -> Dict[str, Dict]:
        """List all configured clients (without secrets)"""
        return {
            client_id: {
                "description": client.description,
                "redirect_uris": client.redirect_uris,
                "scopes": client.scopes,
                "auto_approve": client.auto_approve
            }
            for client_id, client in self._clients.items()
        }


# Global OAuth client manager instance
_oauth_manager = None

def get_oauth_manager() -> OAuthClientManager:
    """Get global OAuth client manager instance"""
    global _oauth_manager
    if _oauth_manager is None:
        _oauth_manager = OAuthClientManager()
    return _oauth_manager


# OAuth scopes definition
OAUTH_SCOPES = {
    "mcp.read": "Read access to MCP tools and resources",
    "mcp.write": "Write access to MCP tools (podcast generation, etc.)",
    "admin": "Administrative access to MySalonCast features"
}


def get_scope_description(scope: str) -> str:
    """Get human-readable description for OAuth scope"""
    return OAUTH_SCOPES.get(scope, f"Unknown scope: {scope}")
