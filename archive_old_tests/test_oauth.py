#!/usr/bin/env python3
"""
OAuth 2.0 Test Script for MySalonCast MCP Server

Tests the full OAuth flow with both Claude.ai and webapp clients.
"""

import requests
import json
import time
import sys
from urllib.parse import parse_qs, urlparse

BASE_URL = "http://localhost:8000"

def test_oauth_discovery():
    """Test OAuth discovery endpoint"""
    print("🔍 Testing OAuth Discovery Endpoint...")
    
    response = requests.get(f"{BASE_URL}/.well-known/oauth-authorization-server")
    
    if response.status_code == 200:
        metadata = response.json()
        print(f"✅ Discovery successful")
        print(f"   Issuer: {metadata.get('issuer')}")
        print(f"   Auth endpoint: {metadata.get('authorization_endpoint')}")
        print(f"   Token endpoint: {metadata.get('token_endpoint')}")
        return True
    else:
        print(f"❌ Discovery failed: {response.status_code}")
        return False

def test_claude_oauth_flow():
    """Test Claude.ai OAuth flow (auto-approval)"""
    print("\n🤖 Testing Claude.ai OAuth Flow...")
    
    # Step 1: Authorization request
    auth_params = {
        "response_type": "code",
        "client_id": "claude-ai",
        "redirect_uri": "https://claude.ai/oauth/callback",
        "scope": "mcp.read mcp.write",
        "state": "test123"
    }
    
    response = requests.get(f"{BASE_URL}/auth/authorize", params=auth_params, allow_redirects=False)
    
    if response.status_code != 302:
        print(f"❌ Authorization failed: {response.status_code}")
        return None
    
    # Extract authorization code from redirect
    location = response.headers.get("location", "")
    parsed_url = urlparse(location)
    query_params = parse_qs(parsed_url.query)
    auth_code = query_params.get("code", [None])[0]
    
    if not auth_code:
        print(f"❌ No authorization code in redirect: {location}")
        return None
    
    print(f"✅ Auto-approval successful, auth code: {auth_code[:20]}...")
    
    # Step 2: Token exchange
    token_data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "client_id": "claude-ai",
        "redirect_uri": "https://claude.ai/oauth/callback"
    }
    
    response = requests.post(f"{BASE_URL}/auth/token", data=token_data)
    
    if response.status_code != 200:
        print(f"❌ Token exchange failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return None
    
    token_response = response.json()
    access_token = token_response.get("access_token")
    
    print(f"✅ Token exchange successful")
    print(f"   Access token: {access_token[:20]}...")
    print(f"   Expires in: {token_response.get('expires_in')} seconds")
    print(f"   Scope: {token_response.get('scope')}")
    
    return access_token

def test_webapp_oauth_flow():
    """Test MySalonCast webapp OAuth flow (consent required)"""
    print("\n🌐 Testing MySalonCast Webapp OAuth Flow...")
    
    auth_params = {
        "response_type": "code", 
        "client_id": "mysaloncast-webapp",
        "redirect_uri": "http://localhost:3000/oauth/callback",
        "scope": "mcp.read mcp.write",
        "state": "webapp123"
    }
    
    response = requests.get(f"{BASE_URL}/auth/authorize", params=auth_params)
    
    if response.status_code != 200:
        print(f"❌ Authorization failed: {response.status_code}")
        return False
    
    consent_response = response.json()
    
    if consent_response.get("message") == "consent_required":
        print(f"✅ Consent required as expected")
        print(f"   Client: {consent_response.get('client_id')}")
        print(f"   Scope: {consent_response.get('scope')}")
        print(f"   Consent URL: {consent_response.get('consent_url')}")
        return True
    else:
        print(f"❌ Expected consent requirement, got: {consent_response}")
        return False

def test_token_introspection(access_token):
    """Test token introspection endpoint"""
    if not access_token:
        return False
        
    print("\n🔍 Testing Token Introspection...")
    
    # Test valid token
    response = requests.post(f"{BASE_URL}/auth/introspect", data={"token": access_token})
    
    if response.status_code != 200:
        print(f"❌ Introspection failed: {response.status_code}")
        return False
    
    introspection = response.json()
    
    if introspection.get("active"):
        print(f"✅ Token is active")
        print(f"   Client: {introspection.get('client_id')}")
        print(f"   Scope: {introspection.get('scope')}")
    else:
        print(f"❌ Token reported as inactive")
        return False
    
    # Test invalid token
    response = requests.post(f"{BASE_URL}/auth/introspect", data={"token": "invalid_token"})
    invalid_result = response.json()
    
    if not invalid_result.get("active"):
        print(f"✅ Invalid token correctly rejected")
        return True
    else:
        print(f"❌ Invalid token was accepted")
        return False

def test_mcp_protection(access_token):
    """Test MCP endpoint protection"""
    print("\n🛡️ Testing MCP Endpoint Protection...")
    
    # Test without token (should fail)
    response = requests.get(f"{BASE_URL}/sse")
    
    if response.status_code == 401:
        print(f"✅ Unauthorized access correctly blocked")
    else:
        print(f"❌ Expected 401, got {response.status_code}")
        return False
    
    # Test with valid token (should succeed - SSE will timeout but that's expected)
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Just test that we get past authentication (don't wait for SSE stream)
        response = requests.get(f"{BASE_URL}/sse", headers=headers, timeout=1)
        # If we get here without timeout, check status
        if response.status_code != 401:
            print(f"✅ Authorized access succeeded")
            return True
        else:
            print(f"❌ Token authentication failed: {response.status_code}")
            return False
    except Exception as e:
        # Any timeout/connection error likely means we got past auth and SSE started
        if "timed out" in str(e).lower() or "timeout" in str(e).lower():
            print(f"✅ Authorized access succeeded (SSE stream timeout expected)")
            return True
        else:
            print(f"❌ Unexpected error: {e}")
            return False

def test_health_endpoint():
    """Test that health endpoint remains public"""
    print("\n❤️ Testing Health Endpoint (should be public)...")
    
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        health = response.json()
        print(f"✅ Health endpoint accessible")
        print(f"   Status: {health.get('status')}")
        return True
    else:
        print(f"❌ Health endpoint failed: {response.status_code}")
        return False

def main():
    """Run all OAuth tests"""
    print("🚀 MySalonCast OAuth 2.0 Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 6
    
    # Test 1: Discovery
    if test_oauth_discovery():
        tests_passed += 1
    
    # Test 2: Claude.ai flow  
    access_token = test_claude_oauth_flow()
    if access_token:
        tests_passed += 1
    
    # Test 3: Webapp flow
    if test_webapp_oauth_flow():
        tests_passed += 1
    
    # Test 4: Token introspection
    if test_token_introspection(access_token):
        tests_passed += 1
    
    # Test 5: MCP protection
    if test_mcp_protection(access_token):
        tests_passed += 1
    
    # Test 6: Health endpoint
    if test_health_endpoint():
        tests_passed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All OAuth tests passed! Ready for Claude.ai integration.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Check the output above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
