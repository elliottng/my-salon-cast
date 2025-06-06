"""JSON utilities for standardized JSON serialization and deserialization."""

import json
import logging
from typing import Any, Dict, Optional, Union
from datetime import datetime, date
from pathlib import Path

logger = logging.getLogger(__name__)


class DatetimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def serialize_json(
    data: Any,
    indent: Optional[int] = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False
) -> str:
    """
    Serialize data to JSON string with standardized settings.
    
    Args:
        data: Data to serialize
        indent: Indentation level (None for compact)
        ensure_ascii: Whether to escape non-ASCII characters
        sort_keys: Whether to sort dictionary keys
        
    Returns:
        JSON string
    """
    return json.dumps(
        data,
        indent=indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
        cls=DatetimeJSONEncoder
    )


def serialize_json_safe(
    data: Any,
    default_value: str = "{}",
    log_errors: bool = True,
    **kwargs
) -> str:
    """
    Safely serialize data to JSON, returning default on error.
    
    Args:
        data: Data to serialize
        default_value: Value to return on error
        log_errors: Whether to log serialization errors
        **kwargs: Additional arguments for json.dumps
        
    Returns:
        JSON string or default value
    """
    try:
        return serialize_json(data, **kwargs)
    except Exception as e:
        if log_errors:
            logger.error(f"JSON serialization failed: {e}")
        return default_value


def deserialize_json(
    json_str: str,
    default: Optional[Any] = None,
    log_errors: bool = True
) -> Any:
    """
    Deserialize JSON string with error handling.
    
    Args:
        json_str: JSON string to deserialize
        default: Default value on error
        log_errors: Whether to log deserialization errors
        
    Returns:
        Deserialized data or default value
    """
    try:
        return json.loads(json_str)
    except Exception as e:
        if log_errors:
            logger.error(f"JSON deserialization failed: {e}")
        return default


async def save_json_file(
    filepath: Union[str, Path],
    data: Any,
    create_dirs: bool = True,
    **json_kwargs
) -> bool:
    """
    Save data to a JSON file.
    
    Args:
        filepath: Target file path
        data: Data to save
        create_dirs: Whether to create parent directories
        **json_kwargs: Additional arguments for serialization
        
    Returns:
        True if successful, False otherwise
    """
    filepath = Path(filepath)
    
    try:
        if create_dirs:
            filepath.parent.mkdir(parents=True, exist_ok=True)
        
        json_content = serialize_json(data, **json_kwargs)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(json_content)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to save JSON file {filepath}: {e}")
        return False


async def load_json_file(
    filepath: Union[str, Path],
    default: Optional[Any] = None,
    log_errors: bool = True
) -> Any:
    """
    Load data from a JSON file.
    
    Args:
        filepath: Source file path
        default: Default value if file doesn't exist or fails
        log_errors: Whether to log errors
        
    Returns:
        Loaded data or default value
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        if log_errors:
            logger.warning(f"JSON file not found: {filepath}")
        return default
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return deserialize_json(content, default, log_errors)
        
    except Exception as e:
        if log_errors:
            logger.error(f"Failed to load JSON file {filepath}: {e}")
        return default


def get_json_size_bytes(data: Any) -> int:
    """
    Get the size in bytes of data when serialized to JSON.
    
    Args:
        data: Data to measure
        
    Returns:
        Size in bytes
    """
    try:
        json_str = serialize_json(data)
        return len(json_str.encode('utf-8'))
    except Exception:
        return 0
