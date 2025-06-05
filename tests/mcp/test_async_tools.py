"""
Test async MCP tools directly
"""
import asyncio
import logging
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.podcast_workflow import PodcastGeneratorService
from app.status_manager import get_status_manager
from app.task_runner import get_task_runner

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPToolTester:
    """Direct tester for MCP tools without needing MCP protocol"""
    
    def __init__(self):
        self.podcast_service = PodcastGeneratorService()
        self.status_manager = get_status_manager()
        self.task_runner = get_task_runner()
        
    async def test_generate_podcast_async(self, **kwargs):
        """Test the generate_podcast_async tool logic"""
        logger.info("Testing generate_podcast_async with params: %s", kwargs)
        
        # This simulates what the MCP tool would do
        source_urls = kwargs.get("source_urls", [])
        source_pdf_path = kwargs.get("source_pdf_path")
        
        # Validation
        if not source_urls and not source_pdf_path:
            return {
                "success": False,
                "error": "Must provide either source_urls or source_pdf_path"
            }
            
        if source_urls and source_pdf_path:
            return {
                "success": False,
                "error": "Cannot provide both source_urls and source_pdf_path. Choose one input method."
            }
        
        # Create podcast request
        from app.podcast_models import PodcastRequest
        try:
            request = PodcastRequest(
                source_urls=source_urls or None,
                source_pdf_path=source_pdf_path or None,
                prominent_persons=kwargs.get("prominent_persons"),
                custom_prompt_for_outline=kwargs.get("custom_prompt"),
                desired_podcast_length_str=kwargs.get("podcast_length", "5-8 minutes"),
                webhook_url=kwargs.get("webhook_url"),
            )
        except Exception as e:
            return {
                "success": False,
                "error": f"Invalid request parameters: {str(e)}"
            }
        
        # Submit async task
        try:
            task_id = await self.podcast_service.generate_podcast_async(request)
            return {
                "success": True,
                "task_id": task_id,
                "status": "queued",
                "message": "Podcast generation task submitted successfully"
            }
        except Exception as e:
            logger.error(f"Error submitting podcast generation task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def test_get_task_status(self, task_id: str):
        """Test the get_task_status tool logic"""
        logger.info("Testing get_task_status for task_id: %s", task_id)
        
        try:
            status = self.status_manager.get_status(task_id)
            if not status:
                return {
                    "success": False,
                    "error": f"Task {task_id} not found"
                }
            
            result = {
                "success": True,
                "task_id": status.task_id,
                "status": status.status,
                "progress": status.progress_percentage,
                "created_at": status.created_at.isoformat() if status.created_at else None,
                "updated_at": status.last_updated_at.isoformat() if status.last_updated_at else None
            }
            
            if status.status == "completed" and status.result_episode:
                result["episode"] = status.result_episode.model_dump()
            elif status.status == "failed" and status.error_details:
                result["error"] = status.error_details.get("message", "Unknown error")
                result["details"] = status.error_details
                
            return result
            
        except Exception as e:
            logger.error(f"Error getting task status: {e}")
            return {
                "success": False,
                "error": str(e)
            }

async def test_full_workflow():
    """Test the complete async podcast generation workflow"""
    tester = MCPToolTester()
    
    # Test 1: Submit a podcast generation task
    logger.info("\n=== Test 1: Submit Podcast Generation ===")
    
    test_params = {
        "source_urls": ["https://en.wikipedia.org/wiki/Artificial_intelligence"],
        "podcast_length": "3-5 minutes",
    }
    
    result = await tester.test_generate_podcast_async(**test_params)
    logger.info("Generation result: %s", json.dumps(result, indent=2))
    
    if not result["success"]:
        logger.error("Failed to submit podcast generation")
        return
    
    task_id = result["task_id"]
    logger.info("Task ID: %s", task_id)
    
    # Test 2: Monitor task status
    logger.info("\n=== Test 2: Monitor Task Status ===")
    
    for i in range(60):  # Check for up to 2 minutes
        status = await tester.test_get_task_status(task_id)
        logger.info("Status check %d: %s", i+1, json.dumps({
            "status": status.get("status"),
            "progress": status.get("progress"),
            "success": status.get("success")
        }, indent=2))
        
        if status.get("status") in ["completed", "failed", "cancelled"]:
            logger.info("Final status: %s", json.dumps(status, indent=2))
            break
            
        await asyncio.sleep(2)
    
    # Test 3: Test validation errors
    logger.info("\n=== Test 3: Validation Errors ===")
    
    # No sources
    result = await tester.test_generate_podcast_async()
    logger.info("No sources result: %s", json.dumps(result, indent=2))
    
    # Both URL and PDF
    result = await tester.test_generate_podcast_async(
        source_urls=["https://example.com"],
        source_pdf_path="/path/to/file.pdf"
    )
    logger.info("Both sources result: %s", json.dumps(result, indent=2))
    
    
    # Test 4: Non-existent task
    logger.info("\n=== Test 4: Non-existent Task ===")
    result = await tester.test_get_task_status("non-existent-task-id")
    logger.info("Non-existent task result: %s", json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_full_workflow())
