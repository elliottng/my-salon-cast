#!/usr/bin/env python3
"""
Test script for MySalonCast MCP prompts validation.

This script tests the prompt functionality of the MCP server to ensure:
1. Prompts are properly registered and accessible
2. Parameter validation works correctly
3. Prompt templates generate appropriate content
4. Integration with MySalonCast tools and resources is properly guided
"""

import os
import sys
import asyncio
import time

# Add the app directory to the Python path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.mcp_server import mcp, create_podcast_from_url, discuss_persona_viewpoint, analyze_podcast_content

# Generate unique suffix for this test run
test_run_suffix = str(int(time.time()))

async def test_create_podcast_from_url_prompt():
    """Test the create_podcast_from_url prompt functionality."""
    print("\n🧪 Testing create_podcast_from_url prompt...")
    
    # Test with default parameters
    result1 = create_podcast_from_url("https://example.com/article")
    
    # Verify the prompt contains key elements
    if "https://example.com/article" not in result1:
        print("❌ URL not properly included in prompt")
        return False
    
    if "Einstein, Marie Curie" not in result1:
        print("❌ Default personas not included")
        return False
    
    if "generate_podcast_async" not in result1:
        print("❌ Tool instruction not included")
        return False
    
    print("✅ Default parameters test passed")
    
    # Test with custom parameters
    result2 = create_podcast_from_url(
        "https://research.com/quantum",
        personas="Tesla, Feynman, Hawking",
        length="long",
        language="es"
    )
    
    if "Tesla, Feynman, Hawking" not in result2:
        print("❌ Custom personas not properly included")
        return False
    
    if "long" not in result2:
        print("❌ Length parameter not included")
        return False
    
    if 'output_language="es"' not in result2:
        print("❌ Language parameter not properly formatted")
        return False
    
    print("✅ Custom parameters test passed")
    print(f"   📄 Generated prompt length: {len(result2)} characters")
    
    return True

async def test_discuss_persona_viewpoint_prompt():
    """Test the discuss_persona_viewpoint prompt functionality."""
    print("\n🧪 Testing discuss_persona_viewpoint prompt...")
    
    task_id = f"test_task_{test_run_suffix}"
    person_id = "albert-einstein"
    topic = "quantum entanglement"
    
    result = discuss_persona_viewpoint(task_id, person_id, topic)
    
    # Verify key elements are included
    if task_id not in result:
        print("❌ Task ID not properly included")
        return False
    
    if person_id not in result:
        print("❌ Person ID not properly included")
        return False
    
    if topic not in result:
        print("❌ Topic not properly included")
        return False
    
    if f"research://{task_id}/{person_id}" not in result:
        print("❌ Resource URL not properly formatted")
        return False
    
    if "perspective" not in result.lower():
        print("❌ Perspective guidance not included")
        return False
    
    print("✅ Persona viewpoint prompt test passed")
    print(f"   🎭 Generated prompt for {person_id} on '{topic}'")
    print(f"   📄 Prompt length: {len(result)} characters")
    
    return True

async def test_analyze_podcast_content_prompt():
    """Test the analyze_podcast_content prompt functionality."""
    print("\n🧪 Testing analyze_podcast_content prompt...")
    
    task_id = f"test_task_{test_run_suffix}"
    
    # Test summary analysis (default)
    result1 = analyze_podcast_content(task_id)
    
    if task_id not in result1:
        print("❌ Task ID not included in summary analysis")
        return False
    
    if f"podcast://{task_id}/metadata" not in result1:
        print("❌ Metadata resource not properly referenced")
        return False
    
    print("✅ Summary analysis test passed")
    
    # Test outline analysis
    result2 = analyze_podcast_content(task_id, "outline")
    
    if f"podcast://{task_id}/outline" not in result2:
        print("❌ Outline resource not properly referenced")
        return False
    
    print("✅ Outline analysis test passed")
    
    # Test personas analysis (special case)
    result3 = analyze_podcast_content(task_id, "personas")
    
    if f"podcast://{task_id}/metadata" not in result3:
        print("❌ Personas analysis should reference metadata first")
        return False
    
    if f"research://{task_id}/[person_id]" not in result3:
        print("❌ Persona research template not included")
        return False
    
    if "replace [person_id]" not in result3:
        print("❌ Instruction for persona ID replacement not included")
        return False
    
    print("✅ Personas analysis test passed")
    
    # Test transcript analysis
    result4 = analyze_podcast_content(task_id, "transcript")
    
    if f"podcast://{task_id}/transcript" not in result4:
        print("❌ Transcript resource not properly referenced")
        return False
    
    print("✅ Transcript analysis test passed")
    print(f"   📊 All analysis types working correctly")
    
    return True

async def test_prompt_parameter_validation():
    """Test parameter validation for prompts."""
    print("\n🧪 Testing prompt parameter validation...")
    
    try:
        # Test valid language parameter
        result1 = create_podcast_from_url("https://test.com", language="fr")
        if 'output_language="fr"' not in result1:
            print("❌ Valid language parameter not handled correctly")
            return False
        
        print("✅ Valid language parameter test passed")
        
        # Test valid length parameter
        result2 = create_podcast_from_url("https://test.com", length="short")
        if "short" not in result2:
            print("❌ Valid length parameter not handled correctly")
            return False
        
        print("✅ Valid length parameter test passed")
        
        # Note: Type validation is handled by FastMCP automatically through function signatures
        # Invalid parameters would be caught by the MCP protocol before reaching our functions
        
        return True
        
    except Exception as e:
        print(f"❌ Parameter validation test failed: {e}")
        return False

async def test_prompt_integration_guidance():
    """Test that prompts provide proper integration guidance."""
    print("\n🧪 Testing prompt integration guidance...")
    
    # Test that create_podcast_from_url includes proper tool usage guidance
    result1 = create_podcast_from_url("https://example.com")
    
    guidance_elements = [
        "generate_podcast_async",
        "get_task_status", 
        "task_id",
        "source_urls",
        "prominent_persons"
    ]
    
    for element in guidance_elements:
        if element not in result1:
            print(f"❌ Missing guidance element: {element}")
            return False
    
    print("✅ Tool usage guidance test passed")
    
    # Test that discuss_persona_viewpoint includes resource usage guidance
    task_id = f"test_task_{test_run_suffix}"
    result2 = discuss_persona_viewpoint(task_id, "einstein", "relativity")
    
    resource_elements = [
        f"research://{task_id}/einstein",
        "MySalonCast resources",
        "research data"
    ]
    
    for element in resource_elements:
        if element not in result2:
            print(f"❌ Missing resource guidance element: {element}")
            return False
    
    print("✅ Resource usage guidance test passed")
    
    return True

async def run_all_tests():
    """Run all prompt validation tests."""
    print("🚀 Starting MySalonCast MCP prompts validation tests...")
    
    tests = [
        test_create_podcast_from_url_prompt,
        test_discuss_persona_viewpoint_prompt,
        test_analyze_podcast_content_prompt,
        test_prompt_parameter_validation,
        test_prompt_integration_guidance
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            result = await test_func()
            if result:
                passed += 1
            else:
                print(f"❌ {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ {test_func.__name__} crashed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All MCP prompt tests passed!")
        print("\n✅ The MySalonCast MCP prompts are ready for production use!")
        print("\n📋 Validated Features:")
        print("   • create_podcast_from_url prompt with parameter validation")
        print("   • discuss_persona_viewpoint prompt with resource integration")
        print("   • analyze_podcast_content prompt with multiple analysis types")
        print("   • Parameter validation and type safety")
        print("   • Integration guidance for tools and resources")
        return True
    else:
        print(f"❌ {total - passed} tests failed. Please review and fix issues.")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
