"""HTTP utilities for common HTTP operations with retry logic."""

import asyncio
import logging
from typing import Dict, Any, Optional, Union
import aiohttp
import httpx

logger = logging.getLogger(__name__)


async def send_webhook_with_retry(
    url: str,
    payload: Dict[str, Any],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    timeout: float = 10.0,
    identifier: Optional[str] = None
) -> bool:
    """
    Send a webhook notification with exponential backoff retry logic.
    
    Args:
        url: The webhook URL
        payload: JSON payload to send
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries
        timeout: Request timeout in seconds
        identifier: Optional identifier for logging (e.g., task_id)
        
    Returns:
        True if successful, False if all attempts failed
    """
    retry_delay = initial_delay
    log_prefix = f"[{identifier}] " if identifier else ""
    
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status < 300:
                        logger.info(f"{log_prefix}Webhook sent successfully")
                        return True
                    else:
                        logger.warning(
                            f"{log_prefix}Webhook returned status {response.status}, "
                            f"attempt {attempt + 1}/{max_retries}"
                        )
        except Exception as e:
            logger.warning(
                f"{log_prefix}Webhook failed, "
                f"attempt {attempt + 1}/{max_retries}: {str(e)}"
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
    
    logger.error(f"{log_prefix}Failed to send webhook after {max_retries} attempts")
    return False


async def fetch_json_with_retry(
    url: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """
    Fetch JSON data from a URL with retry logic.
    
    Args:
        url: The URL to fetch from
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries
        timeout: Request timeout in seconds
        headers: Optional headers to include
        
    Returns:
        JSON data as dictionary, or None if failed
    """
    retry_delay = initial_delay
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(
                f"HTTP {e.response.status_code} error fetching {url}, "
                f"attempt {attempt + 1}/{max_retries}"
            )
        except Exception as e:
            logger.warning(
                f"Error fetching {url}, "
                f"attempt {attempt + 1}/{max_retries}: {str(e)}"
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay)
            retry_delay *= 2
    
    logger.error(f"Failed to fetch {url} after {max_retries} attempts")
    return None


def build_webhook_payload(
    task_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build a standardized webhook payload.
    
    Args:
        task_id: Task identifier
        status: Task status
        result: Optional result data
        error: Optional error message
        extra_fields: Additional fields to include
        
    Returns:
        Webhook payload dictionary
    """
    from datetime import datetime
    
    payload = {
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    if result:
        payload["result"] = result
    
    if error:
        payload["error"] = error
    
    if extra_fields:
        payload.update(extra_fields)
    
    return payload
