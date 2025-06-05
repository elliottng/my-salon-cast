#!/usr/bin/env python3
"""
Test SSE connection to the staging MCP server.
"""
import requests
import json
import time

STAGING_URL = "https://mcp-server-staging-644248751086.us-west1.run.app"

def get_access_token():
    """Get access token from OAuth flow"""
    # Step 1: Get OAuth discovery
    discovery_response = requests.get(f"{STAGING_URL}/.well-known/oauth-authorization-server")
    discovery = discovery_response.json()
    
    # Step 2: Authorize (auto-approved)
    auth_response = requests.get(f"{STAGING_URL}/auth/authorize", params={
        "response_type": "code",
        "client_id": "74-IKzpZVc7CuWPw94-KIkJc8tciz6peVuo8wa8seXg",
        "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        "scope": "claudeai",
        "code_challenge": "UUCeYlWCLJ4uC15qdoqdcWKlTWruf_wk-bJ0Tob0zsQ",
        "code_challenge_method": "S256",
        "state": "test_state"
    }, allow_redirects=False)
    
    # Extract code from redirect
    location = auth_response.headers.get('Location', '')
    code = location.split('code=')[1].split('&')[0]
    
    # Step 3: Exchange code for token
    token_response = requests.post(f"{STAGING_URL}/auth/token", data={
        "grant_type": "authorization_code",
        "client_id": "74-IKzpZVc7CuWPw94-KIkJc8tciz6peVuo8wa8seXg",
        "code": code,
        "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        "code_verifier": "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    })
    
    token_data = token_response.json()
    print(f"Token response: {token_data}")  # Debug
    return token_data["access_token"]

def test_sse_connection():
    """Test SSE connection with authentication"""
    print("🚀 Testing SSE Connection to MCP Server")
    print(f"URL: {STAGING_URL}")
    print("-" * 60)
    
    try:
        # Get access token
        print("🎫 Getting access token...")
        access_token = get_access_token()
        print(f"✅ Token obtained: {access_token[:20]}...")
        
        # Test SSE endpoint with authentication
        print("🔗 Connecting to SSE endpoint...")
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache"
        }
        
        # Make SSE request
        response = requests.get(f"{STAGING_URL}/sse", headers=headers, stream=True, timeout=10)
        
        print(f"📡 SSE Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ SSE Connection: SUCCESSFUL!")
            
            # Try to read some SSE data
            print("📖 Reading SSE stream...")
            for i, line in enumerate(response.iter_lines(decode_unicode=True)):
                if line:
                    print(f"📨 SSE Line {i}: {line}")
                if i >= 5:  # Just read a few lines
                    break
        else:
            print(f"❌ SSE Connection Failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ SSE Test Failed: {e}")

if __name__ == "__main__":
    test_sse_connection()
