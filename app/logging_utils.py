"""Logging utilities for standardized logging patterns."""

import logging
from typing import Optional, Dict, Any
from functools import wraps

logger = logging.getLogger(__name__)


def log_mcp_tool_call(
    tool_name: str,
    ctx: Any,
    extra_info: Optional[str] = None,
    params: Optional[Dict[str, Any]] = None
) -> tuple[str, Dict[str, Any]]:
    """
    Log an MCP tool call with standardized format.
    
    Args:
        tool_name: Name of the tool being called
        ctx: MCP context object
        extra_info: Additional information to include
        params: Tool parameters to log
        
    Returns:
        Tuple of (request_id, client_info)
    """
    request_id = getattr(ctx, 'request_id', 'unknown')
    client_info = getattr(ctx, 'client_info', {})
    
    log_msg = f"[{request_id}] MCP Tool '{tool_name}' called"
    if extra_info:
        log_msg += f" {extra_info}"
    
    if params:
        # Filter out sensitive information
        safe_params = {k: v for k, v in params.items() 
                      if k not in ['webhook_url', 'api_key', 'secret']}
        logger.info(f"{log_msg}, params: {safe_params}")
    else:
        logger.info(log_msg)
    
    return request_id, client_info


def log_mcp_resource_access(
    resource_name: str,
    params: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an MCP resource access with standardized format.
    
    Args:
        resource_name: Name of the resource being accessed
        params: Resource parameters to log
    """
    log_msg = f"Resource '{resource_name}' accessed"
    
    if params:
        param_str = ", ".join(f"{k}: {v}" for k, v in params.items())
        log_msg += f" for {param_str}"
    
    logger.info(log_msg)


def log_operation_start(
    operation: str,
    identifier: Optional[str] = None,
    **kwargs
) -> None:
    """
    Log the start of an operation.
    
    Args:
        operation: Operation name
        identifier: Optional identifier (e.g., task_id)
        **kwargs: Additional context to log
    """
    msg = f"Starting {operation}"
    if identifier:
        msg += f" for {identifier}"
    
    if kwargs:
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        msg += f" ({context})"
    
    logger.info(msg)


def log_operation_complete(
    operation: str,
    identifier: Optional[str] = None,
    success: bool = True,
    **kwargs
) -> None:
    """
    Log the completion of an operation.
    
    Args:
        operation: Operation name
        identifier: Optional identifier
        success: Whether operation succeeded
        **kwargs: Additional context to log
    """
    status = "completed successfully" if success else "failed"
    msg = f"{operation} {status}"
    
    if identifier:
        msg += f" for {identifier}"
    
    if kwargs:
        context = ", ".join(f"{k}={v}" for k, v in kwargs.items())
        msg += f" ({context})"
    
    if success:
        logger.info(msg)
    else:
        logger.error(msg)


def log_retry_attempt(
    operation: str,
    attempt: int,
    max_attempts: int,
    error: Optional[Exception] = None,
    identifier: Optional[str] = None
) -> None:
    """
    Log a retry attempt.
    
    Args:
        operation: Operation being retried
        attempt: Current attempt number (1-based)
        max_attempts: Maximum number of attempts
        error: Optional error that caused retry
        identifier: Optional identifier
    """
    msg = f"{operation} attempt {attempt}/{max_attempts}"
    
    if identifier:
        msg += f" for {identifier}"
    
    if error:
        msg += f": {str(error)}"
    
    logger.warning(msg)


def log_with_context(level: int = logging.INFO):
    """
    Decorator to log function calls with context.
    
    Args:
        level: Logging level to use
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.log(level, f"Calling {func_name}")
            try:
                result = await func(*args, **kwargs)
                logger.log(level, f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func_name} failed: {str(e)}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            func_name = func.__name__
            logger.log(level, f"Calling {func_name}")
            try:
                result = func(*args, **kwargs)
                logger.log(level, f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func_name} failed: {str(e)}")
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Import asyncio only when needed for the decorator
import asyncio
