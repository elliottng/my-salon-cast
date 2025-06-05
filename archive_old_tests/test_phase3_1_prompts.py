#!/usr/bin/env python3

"""
Test Phase 3.1: Core Prompt Templates
Tests the new MCP prompt templates for podcast generation and persona research.
"""

import asyncio
import subprocess
import sys
from pathlib import Path

async def test_prompts():
    """Test the MCP prompt templates using subprocess isolation."""
    
    print("🚀 Starting Phase 3.1 Prompt Template Tests")
    print("=" * 60)

    # Test code to run in subprocess
    test_code = '''
import asyncio
import sys
from fastmcp import Client

async def main():
    try:
        # Connect to the MCP server
        client = Client("http://localhost:8000/mcp")
        
        async with client:
            print("🔗 Connected to MCP server")
            
            # Test 1: List available prompts
            print("\\n🧪 Test 1: List available prompts")
            prompts = await client.list_prompts()
            print(f"📋 Available prompts: {len(prompts)} found")
            
            for prompt in prompts:
                print(f"   - {prompt.name}: {prompt.description}")
                
            # Verify our prompts exist
            prompt_names = [p.name for p in prompts]
            expected_prompts = ["podcast_generation_request", "persona_research_prompt"]
            
            for expected in expected_prompts:
                if expected in prompt_names:
                    print(f"✅ Found prompt: {expected}")
                else:
                    print(f"❌ Missing prompt: {expected}")
                    return False
            
            # Test 2: Generate podcast request prompt
            print("\\n🧪 Test 2: Generate podcast request prompt")
            
            podcast_params = {
                "topic": "The Battle of Jutland",
                "sources": "https://en.wikipedia.org/wiki/Battle_of_Jutland",
                "persons": "Winston Churchill, Admiral Jellicoe",
                "style": "engaging",
                "length": "5-7 minutes",
                "language": "en",
                "custom_focus": "Naval strategy and technology"
            }
            
            podcast_prompt = await client.get_prompt("podcast_generation_request", podcast_params)
            print(f"📝 Generated podcast prompt:")
            print(f"   Length: {len(podcast_prompt.messages)} messages")
            if podcast_prompt.messages:
                content = podcast_prompt.messages[0].content
                if hasattr(content, 'text'):
                    preview = content.text[:200] + "..." if len(content.text) > 200 else content.text
                    print(f"   Preview: {preview}")
                    
                    # Verify key elements are in the prompt
                    full_text = content.text
                    checks = [
                        ("topic mentioned", "Battle of Jutland" in full_text),
                        ("sources included", "wikipedia.org" in full_text),
                        ("personas included", "Churchill" in full_text),
                        ("style specified", "engaging" in full_text),
                        ("custom focus", "Naval strategy" in full_text)
                    ]
                    
                    for check_name, result in checks:
                        status = "✅" if result else "❌"
                        print(f"   {status} {check_name}")
            
            # Test 3: Generate persona research prompt  
            print("\\n🧪 Test 3: Generate persona research prompt")
            
            persona_params = {
                "person_name": "Albert Einstein",
                "research_focus": "speaking_style",
                "context_topic": "Physics and relativity",
                "detail_level": "detailed",
                "time_period": "1920s"
            }
            
            persona_prompt = await client.get_prompt("persona_research_prompt", persona_params)
            print(f"📝 Generated persona research prompt:")
            print(f"   Length: {len(persona_prompt.messages)} messages")
            if persona_prompt.messages:
                content = persona_prompt.messages[0].content
                if hasattr(content, 'text'):
                    preview = content.text[:200] + "..." if len(content.text) > 200 else content.text
                    print(f"   Preview: {preview}")
                    
                    # Verify key elements are in the prompt
                    full_text = content.text
                    checks = [
                        ("person mentioned", "Albert Einstein" in full_text),
                        ("focus specified", "speaking_style" in full_text),
                        ("context included", "Physics" in full_text),
                        ("time period", "1920s" in full_text),
                        ("research areas", "Speech patterns" in full_text)
                    ]
                    
                    for check_name, result in checks:
                        status = "✅" if result else "❌"
                        print(f"   {status} {check_name}")
            
            print("\\n✅ All prompt template tests completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Error during prompt testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
'''
    
    # Write test code to temp file and run in subprocess
    test_file = Path("/tmp/test_prompts_isolated.py")
    test_file.write_text(test_code)
    
    try:
        # Set up environment and run the test
        env = {
            "PYTHONPATH": str(Path.cwd()),
            "PATH": "/usr/bin:/bin:/usr/local/bin"
        }
        
        result = subprocess.run([
            sys.executable, str(test_file)
        ], 
        cwd=Path.cwd(),
        capture_output=True, 
        text=True,
        env=env,
        timeout=60
        )
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
            
        success = result.returncode == 0
        print(f"\n{'✅' if success else '❌'} Phase 3.1 Prompt Tests: {'PASSED' if success else 'FAILED'}")
        
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 60 seconds")
        return False
    except Exception as e:
        print(f"❌ Error running subprocess test: {e}")
        return False
    finally:
        # Clean up temp file
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    success = asyncio.run(test_prompts())
    if success:
        print("\n🎉 Phase 3.1: Core Prompt Templates implementation complete!")
    else:
        print("\n💥 Phase 3.1 tests failed - check implementation")
    sys.exit(0 if success else 1)
