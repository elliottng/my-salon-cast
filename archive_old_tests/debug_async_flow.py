#!/usr/bin/env python3
"""
Debug async flow to understand the execution pattern
"""

import asyncio
import sys
import os
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import environment
from dotenv import load_dotenv
load_dotenv()
os.environ['GOOGLE_API_KEY'] = os.environ.get('GEMINI_API_KEY')

from app.mcp_server import mcp
from app.podcast_models import PodcastRequest
from app.task_runner import get_task_runner
from app.podcast_workflow import get_podcast_service
from app.status_manager import get_status_manager
import uuid

async def trace_async_flow():
    """Trace the async flow of podcast generation"""
    
    print("\n🔍 TRACING ASYNC PODCAST GENERATION FLOW\n")
    
    # Create a simple request
    request = PodcastRequest(
        source_urls=["http://localhost:9999/test_content.html"],
        desired_podcast_length_str="3_to_5_minutes"
    )
    
    # Get services
    podcast_service = get_podcast_service()
    status_manager = get_status_manager()
    task_runner = get_task_runner()
    
    # Generate task ID
    task_id = str(uuid.uuid4())
    print(f"📝 Task ID: {task_id}")
    
    print("\n1️⃣ CALLING generate_podcast_async...")
    try:
        # Call with async mode
        returned_task_id, episode = await podcast_service._generate_podcast_internal(
            request_data=request,
            async_mode=True,
            background_task_id=None
        )
        
        print(f"\n✅ Returned immediately with task_id: {returned_task_id}")
        print(f"📦 Episode placeholder: {episode.title}")
        
        # Check task runner state
        print(f"\n2️⃣ TASK RUNNER STATE:")
        print(f"   Running tasks: {task_runner.get_running_task_count()}")
        print(f"   Queue status: {task_runner.get_queue_status()}")
        
        # Monitor status for a bit
        print(f"\n3️⃣ MONITORING STATUS:")
        for i in range(5):
            await asyncio.sleep(2)
            status = status_manager.get_status(returned_task_id)
            if status:
                print(f"   [{i}] Status: {status.status} ({status.progress_percentage}%) - {status.status_message}")
                if status.status in ["completed", "failed"]:
                    break
            else:
                print(f"   [{i}] Status not found!")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check final task runner state
    print(f"\n4️⃣ FINAL TASK RUNNER STATE:")
    print(f"   Running tasks: {task_runner.get_running_task_count()}")
    print(f"   Active tasks: {task_runner.get_active_tasks()}")

if __name__ == "__main__":
    # Start HTTP server in background
    import subprocess
    http_server = subprocess.Popen(
        ["python3", "-m", "http.server", "9999"],
        cwd=project_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    try:
        asyncio.run(trace_async_flow())
    finally:
        http_server.terminate()
