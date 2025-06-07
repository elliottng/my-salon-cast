#!/usr/bin/env python3
"""
Simple test to check PydanticAI and Logfire integration after rollback.
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ.setdefault('ENVIRONMENT', 'local')
os.environ.setdefault('LOGFIRE_LOG_CONTENT', 'true')

# Import Logfire early
try:
    import logfire
    print("📊 Logfire imported successfully")
except Exception as e:
    print(f"❌ Failed to import Logfire: {e}")

from app.llm_service import GeminiService
from app.config import setup_environment

async def test_simple_pydantic():
    print("🧪 Testing PydanticAI integration after rollback")
    
    # Setup environment
    setup_environment()
    
    # Initialize service
    service = GeminiService()
    print(f"✅ GeminiService initialized")
    print(f"📋 use_pydantic_ai = {service.use_pydantic_ai}")
    print(f"🤖 pydantic_agent = {service.pydantic_agent is not None}")
    
    if service.use_pydantic_ai and service.pydantic_agent:
        print("🚀 Testing simple text generation...")
        try:
            result = await service.generate_text_async("Say hello in one word", timeout_seconds=30)
            print(f"✅ Result: {result}")
        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("ℹ️  PydanticAI not enabled, skipping test")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_simple_pydantic())
