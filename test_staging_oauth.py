#!/usr/bin/env python3
"""
OAuth 2.0 Integration Test for Staging Environment

Tests the complete OAuth flow against the deployed staging environment:
1. OAuth discovery endpoint
2. Authorization flow (Claude.ai client)
3. Token exchange
4. MCP endpoint protection
5. Token introspection

Usage: python test_staging_oauth.py
"""

import requests
import json
import time
import hashlib
import base64
import secrets
from urllib.parse import urlparse, parse_qs

# Staging environment configuration
STAGING_BASE_URL = "https://mcp-server-staging-644248751086.us-west1.run.app"
CLAUDE_CLIENT_ID = "claude-ai"
CLAUDE_REDIRECT_URI = "https://claude.ai/oauth/callback"

def generate_pkce():
    """Generate PKCE code verifier and challenge"""
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

def test_oauth_discovery():
    """Test OAuth 2.0 discovery endpoint"""
    print("🔍 Testing OAuth Discovery...")
    
    response = requests.get(f"{STAGING_BASE_URL}/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    
    metadata = response.json()
    assert metadata["issuer"] == STAGING_BASE_URL
    assert metadata["authorization_endpoint"] == f"{STAGING_BASE_URL}/auth/authorize"
    assert metadata["token_endpoint"] == f"{STAGING_BASE_URL}/auth/token"
    assert "S256" in metadata["code_challenge_methods_supported"]
    assert "mcp.read" in metadata["scopes_supported"]
    assert "mcp.write" in metadata["scopes_supported"]
    
    print("✅ OAuth Discovery: PASSED")
    return metadata

def test_authorization_flow():
    """Test OAuth authorization flow with Claude.ai client"""
    print("🔐 Testing Authorization Flow...")
    
    code_verifier, code_challenge = generate_pkce()
    state = secrets.token_urlsafe(16)
    
    # Build authorization URL
    auth_params = {
        "response_type": "code",
        "client_id": CLAUDE_CLIENT_ID,
        "redirect_uri": CLAUDE_REDIRECT_URI,
        "scope": "mcp.read mcp.write",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256"
    }
    
    auth_url = f"{STAGING_BASE_URL}/auth/authorize"
    response = requests.get(auth_url, params=auth_params, allow_redirects=False)
    
    # Should redirect with authorization code (auto-approval for Claude.ai)
    assert response.status_code == 302
    
    location = response.headers.get("location")
    assert location is not None
    assert location.startswith(CLAUDE_REDIRECT_URI)
    
    # Parse authorization code from redirect
    parsed = urlparse(location)
    query_params = parse_qs(parsed.query)
    
    assert "code" in query_params
    assert query_params["state"][0] == state
    
    auth_code = query_params["code"][0]
    
    print("✅ Authorization Flow: PASSED")
    return auth_code, code_verifier

def test_token_exchange(auth_code, code_verifier):
    """Test token exchange endpoint"""
    print("🎫 Testing Token Exchange...")
    
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": CLAUDE_REDIRECT_URI,
        "client_id": CLAUDE_CLIENT_ID,
        "code_verifier": code_verifier
    }
    
    response = requests.post(f"{STAGING_BASE_URL}/auth/token", data=token_data)
    assert response.status_code == 200
    
    token_response = response.json()
    assert "access_token" in token_response
    assert token_response["token_type"] == "Bearer"
    assert "expires_in" in token_response
    assert "scope" in token_response
    
    access_token = token_response["access_token"]
    
    print("✅ Token Exchange: PASSED")
    print(f"\nAccess Token: {access_token}\n")
    return access_token

def test_mcp_endpoint_protection(access_token):
    """Test that MCP endpoints require valid tokens"""
    print("🛡️ Testing MCP Endpoint Protection...")
    
    # Test without token - should fail
    response = requests.get(f"{STAGING_BASE_URL}/sse")
    assert response.status_code == 401
    error = response.json()
    assert error["error"] == "unauthorized"
    
    # Test with invalid token - should fail
    headers = {"Authorization": "Bearer invalid-token"}
    response = requests.get(f"{STAGING_BASE_URL}/sse", headers=headers)
    assert response.status_code == 401
    
    # Test with valid token - should work (or timeout waiting for SSE)
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(f"{STAGING_BASE_URL}/sse", headers=headers, timeout=3)
        # If we get here without timeout, check it's not unauthorized
        assert response.status_code != 401
    except requests.exceptions.Timeout:
        # Timeout is expected for SSE endpoint - it means auth worked
        print("  (SSE endpoint timed out as expected - auth successful)")
    except requests.exceptions.ReadTimeout:
        # ReadTimeout is also expected for SSE endpoint
        print("  (SSE endpoint read timeout as expected - auth successful)")
    except Exception as e:
        # Handle other connection errors that might occur with SSE
        if "Read timed out" in str(e) or "timeout" in str(e).lower():
            print("  (SSE endpoint timed out as expected - auth successful)")
        else:
            raise e
    
    print("✅ MCP Endpoint Protection: PASSED")

def test_token_introspection(access_token):
    """Test token introspection endpoint"""
    print("🔍 Testing Token Introspection...")
    
    introspect_data = {
        "token": access_token,
        "client_id": CLAUDE_CLIENT_ID
    }
    
    response = requests.post(f"{STAGING_BASE_URL}/auth/introspect", data=introspect_data)
    assert response.status_code == 200
    
    introspection = response.json()
    assert introspection["active"] == True
    assert introspection["client_id"] == CLAUDE_CLIENT_ID
    assert "scope" in introspection
    assert "exp" in introspection
    
    print("✅ Token Introspection: PASSED")

def test_health_endpoint():
    """Test that health endpoint is publicly accessible"""
    print("🏥 Testing Health Endpoint...")
    
    response = requests.get(f"{STAGING_BASE_URL}/health")
    assert response.status_code == 200
    
    health = response.json()
    assert health["status"] == "healthy"
    assert health["environment"] == "staging"
    
    print("✅ Health Endpoint: PASSED")

def main():
    """Run all OAuth integration tests"""
    print("🚀 Starting OAuth 2.0 Staging Integration Tests")
    print(f"Testing against: {STAGING_BASE_URL}")
    print("-" * 60)
    
    try:
        # Run all tests in sequence
        test_health_endpoint()
        metadata = test_oauth_discovery()
        auth_code, code_verifier = test_authorization_flow()
        access_token = test_token_exchange(auth_code, code_verifier)
        test_mcp_endpoint_protection(access_token)
        test_token_introspection(access_token)
        
        print("-" * 60)
        print("🎉 ALL TESTS PASSED!")
        print("✅ OAuth 2.0 integration is working correctly in staging")
        print("✅ Ready for Claude.ai remote MCP server integration")
        
    except Exception as e:
        print(f"❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)

if __name__ == "__main__":
    main()
