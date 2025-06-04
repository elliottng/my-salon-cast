"""
OAuth 2.0 Data Models for MySalonCast MCP Server

Pydantic models for OAuth request/response handling and in-memory storage.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import datetime, timedelta
import secrets
import hashlib
import time


class AuthorizationRequest(BaseModel):
    """OAuth authorization request parameters"""
    response_type: Literal["code"] = "code"
    client_id: str
    redirect_uri: str
    scope: Optional[str] = "mcp.read mcp.write"
    state: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: Optional[Literal["S256"]] = None


class TokenRequest(BaseModel):
    """OAuth token exchange request parameters"""
    grant_type: Literal["authorization_code"] = "authorization_code"
    code: str
    redirect_uri: str
    client_id: str
    client_secret: Optional[str] = None
    code_verifier: Optional[str] = None


class TokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour
    scope: str
    refresh_token: Optional[str] = None


class AuthorizationCode:
    """Authorization code storage"""
    def __init__(self, client_id: str, redirect_uri: str, scope: str, 
                 code_challenge: Optional[str] = None, state: Optional[str] = None):
        self.code = secrets.token_urlsafe(32)
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.scope = scope
        self.code_challenge = code_challenge
        self.state = state
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(minutes=10)  # 10 minute expiration
        self.used = False
    
    def is_expired(self) -> bool:
        """Check if authorization code is expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if authorization code is valid (not used and not expired)"""
        return not self.used and not self.is_expired()
    
    def mark_used(self):
        """Mark authorization code as used"""
        self.used = True


class AccessToken:
    """Access token storage"""
    def __init__(self, client_id: str, scope: str):
        self.token = secrets.token_urlsafe(32)
        self.client_id = client_id
        self.scope = scope
        self.created_at = datetime.now()
        self.expires_at = self.created_at + timedelta(hours=1)  # 1 hour expiration
    
    def is_expired(self) -> bool:
        """Check if access token is expired"""
        return datetime.now() > self.expires_at
    
    def is_valid(self) -> bool:
        """Check if access token is valid (not expired)"""
        return not self.is_expired()
    
    def has_scope(self, required_scope: str) -> bool:
        """Check if token has required scope"""
        token_scopes = self.scope.split()
        return required_scope in token_scopes


class OAuthStorage:
    """In-memory OAuth storage for authorization codes and access tokens"""
    
    def __init__(self):
        self._auth_codes: Dict[str, AuthorizationCode] = {}
        self._access_tokens: Dict[str, AccessToken] = {}
        self._last_cleanup = time.time()
    
    def store_auth_code(self, auth_code: AuthorizationCode) -> str:
        """Store authorization code and return the code string"""
        self._auth_codes[auth_code.code] = auth_code
        self._cleanup_expired()
        return auth_code.code
    
    def get_auth_code(self, code: str) -> Optional[AuthorizationCode]:
        """Get authorization code by code string"""
        self._cleanup_expired()
        return self._auth_codes.get(code)
    
    def consume_auth_code(self, code: str) -> Optional[AuthorizationCode]:
        """Get and mark authorization code as used"""
        auth_code = self.get_auth_code(code)
        if auth_code and auth_code.is_valid():
            auth_code.mark_used()
            return auth_code
        return None
    
    def store_access_token(self, access_token: AccessToken) -> str:
        """Store access token and return the token string"""
        self._access_tokens[access_token.token] = access_token
        self._cleanup_expired()
        return access_token.token
    
    def get_access_token(self, token: str) -> Optional[AccessToken]:
        """Get access token by token string"""
        self._cleanup_expired()
        return self._access_tokens.get(token)
    
    def validate_token(self, token: str, required_scope: str = None) -> Optional[AccessToken]:
        """Validate access token and optional scope"""
        access_token = self.get_access_token(token)
        if not access_token or not access_token.is_valid():
            return None
        
        if required_scope and not access_token.has_scope(required_scope):
            return None
        
        return access_token
    
    def _cleanup_expired(self):
        """Cleanup expired codes and tokens (run periodically)"""
        current_time = time.time()
        
        # Only cleanup every 5 minutes to avoid performance impact
        if current_time - self._last_cleanup < 300:
            return
        
        # Remove expired authorization codes
        expired_codes = [
            code for code, auth_code in self._auth_codes.items()
            if auth_code.is_expired()
        ]
        for code in expired_codes:
            del self._auth_codes[code]
        
        # Remove expired access tokens
        expired_tokens = [
            token for token, access_token in self._access_tokens.items()
            if access_token.is_expired()
        ]
        for token in expired_tokens:
            del self._access_tokens[token]
        
        self._last_cleanup = current_time
    
    def get_stats(self) -> Dict:
        """Get storage statistics"""
        self._cleanup_expired()
        return {
            "active_auth_codes": len(self._auth_codes),
            "active_access_tokens": len(self._access_tokens),
            "last_cleanup": datetime.fromtimestamp(self._last_cleanup).isoformat()
        }


# Utility functions for PKCE (Proof Key for Code Exchange)
def verify_code_challenge(code_verifier: str, code_challenge: str) -> bool:
    """Verify PKCE code challenge against code verifier"""
    # For S256 method: base64url(sha256(code_verifier)) == code_challenge
    import base64
    
    code_sha = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge_computed = base64.urlsafe_b64encode(code_sha).decode('utf-8').rstrip('=')
    
    return code_challenge_computed == code_challenge


# Global OAuth storage instance
_oauth_storage = None

def get_oauth_storage() -> OAuthStorage:
    """Get global OAuth storage instance"""
    global _oauth_storage
    if _oauth_storage is None:
        _oauth_storage = OAuthStorage()
    return _oauth_storage
