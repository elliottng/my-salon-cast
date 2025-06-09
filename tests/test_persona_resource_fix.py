#!/usr/bin/env python3
"""
Test the persona research resource access after fixing the task_directory bug.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(__file__))

from app.mcp_server import get_persona_research_resource

async def test_persona_resource_access():
    """Test persona research resource access with our previous task."""
    print("🔍 Testing Persona Research Resource Access")
    print("=" * 50)
    
    # Use the task ID from our previous successful run
    task_id = "b5f2efbd-2643-4d67-b503-ef01e721f98d"
    personas_to_test = ["brad_gerstner", "bill_gurley"]
    
    for person_id in personas_to_test:
        print(f"\n👤 Testing persona: {person_id}")
        print("-" * 30)
        
        try:
            result = await get_persona_research_resource(task_id=task_id, person_id=person_id)
            print(f"   ✅ Successfully retrieved resource for {person_id}")
            print(f"   📁 Has research: {result.get('has_research', False)}")
            print(f"   📄 File path: {result.get('research_file_path', 'N/A')}")
            print(f"   📊 File exists: {result.get('file_exists', False)}")
            
        except Exception as e:
            print(f"   ❌ Failed to get resource for {person_id}: {e}")
    
    print(f"\n📋 Test completed")

if __name__ == "__main__":
    asyncio.run(test_persona_resource_access())
