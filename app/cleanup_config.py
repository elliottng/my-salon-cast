"""
Cleanup policy configuration for MySalonCast podcast generation tasks.
Provides configurable options for automatic file cleanup and retention policies.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CleanupPolicy(str, Enum):
    """Available cleanup policies for task files."""
    MANUAL = "manual"           # No automatic cleanup, require explicit cleanup_task_files calls
    AUTO_ON_COMPLETE = "auto_on_complete"  # Cleanup immediately when task completes
    AUTO_AFTER_HOURS = "auto_after_hours"  # Cleanup after specified hours since completion
    AUTO_AFTER_DAYS = "auto_after_days"    # Cleanup after specified days since completion
    RETAIN_AUDIO_ONLY = "retain_audio_only"  # Keep only final audio, remove temp files
    RETAIN_ALL = "retain_all"   # Never cleanup (for development/testing)


class CleanupConfig(BaseModel):
    """Configuration model for cleanup policies."""
    
    # Global default policy
    default_policy: CleanupPolicy = Field(
        default=CleanupPolicy.MANUAL,
        description="Default cleanup policy for all tasks"
    )
    
    # Time-based settings
    auto_cleanup_hours: int = Field(
        default=24,
        description="Hours after completion before auto cleanup (for AUTO_AFTER_HOURS policy)"
    )
    
    auto_cleanup_days: int = Field(
        default=7,
        description="Days after completion before auto cleanup (for AUTO_AFTER_DAYS policy)"
    )
    
    # File type preferences
    retain_audio_files: bool = Field(
        default=True,
        description="Whether to retain final audio files during cleanup"
    )
    
    retain_transcripts: bool = Field(
        default=True,
        description="Whether to retain transcript files during cleanup"
    )
    
    retain_llm_outputs: bool = Field(
        default=False,
        description="Whether to retain LLM intermediate output files"
    )
    
    retain_audio_segments: bool = Field(
        default=False,
        description="Whether to retain individual audio segment files"
    )
    
    # Size limits
    max_temp_size_mb: int = Field(
        default=500,
        description="Maximum total size of temp files per task in MB"
    )
    
    max_total_storage_gb: int = Field(
        default=5,
        description="Maximum total storage for all task files in GB"
    )
    
    # Advanced options
    cleanup_on_startup: bool = Field(
        default=False,
        description="Whether to cleanup orphaned temp directories on server startup"
    )
    
    enable_background_cleanup: bool = Field(
        default=True,
        description="Whether to enable background cleanup scheduler"
    )
    
    background_cleanup_interval_minutes: int = Field(
        default=60,
        description="Interval in minutes between background cleanup checks"
    )


class CleanupManager:
    """Manages cleanup policies and configuration for MySalonCast."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "cleanup_config.json"
        )
        self._config: Optional[CleanupConfig] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """Load cleanup configuration from file or create default."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config_data = json.load(f)
                self._config = CleanupConfig(**config_data)
                logger.info(f"Loaded cleanup config from {self.config_path}")
            else:
                self._config = CleanupConfig()
                self._save_config()
                logger.info(f"Created default cleanup config at {self.config_path}")
        except Exception as e:
            logger.error(f"Error loading cleanup config: {e}")
            self._config = CleanupConfig()
    
    def _save_config(self) -> None:
        """Save current configuration to file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            
            with open(self.config_path, 'w') as f:
                json.dump(self._config.model_dump(), f, indent=2)
            logger.info(f"Saved cleanup config to {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving cleanup config: {e}")
    
    @property
    def config(self) -> CleanupConfig:
        """Get current cleanup configuration."""
        if self._config is None:
            self._load_config()
        return self._config
    
    def update_config(self, **kwargs) -> CleanupConfig:
        """Update configuration with new values."""
        current_data = self.config.model_dump()
        current_data.update(kwargs)
        
        try:
            self._config = CleanupConfig(**current_data)
            self._save_config()
            logger.info(f"Updated cleanup config: {kwargs}")
            return self._config
        except Exception as e:
            logger.error(f"Error updating cleanup config: {e}")
            raise ValueError(f"Invalid configuration update: {e}")
    
    def get_policy_for_task(self, task_id: str) -> CleanupPolicy:
        """Get the cleanup policy for a specific task."""
        # In the future, this could support per-task policies
        # For now, return the default policy
        return self.config.default_policy
    
    def should_cleanup_now(self, task_id: str, completion_time: float) -> bool:
        """Determine if a task should be cleaned up now based on policy."""
        import time
        
        policy = self.get_policy_for_task(task_id)
        current_time = time.time()
        time_since_completion = current_time - completion_time
        
        if policy == CleanupPolicy.MANUAL:
            return False
        elif policy == CleanupPolicy.AUTO_ON_COMPLETE:
            return True
        elif policy == CleanupPolicy.AUTO_AFTER_HOURS:
            hours_elapsed = time_since_completion / 3600
            return hours_elapsed >= self.config.auto_cleanup_hours
        elif policy == CleanupPolicy.AUTO_AFTER_DAYS:
            days_elapsed = time_since_completion / (3600 * 24)
            return days_elapsed >= self.config.auto_cleanup_days
        elif policy == CleanupPolicy.RETAIN_AUDIO_ONLY:
            # This would trigger partial cleanup
            return True
        elif policy == CleanupPolicy.RETAIN_ALL:
            return False
        
        return False
    
    def get_cleanup_rules(self, task_id: str) -> Dict[str, bool]:
        """Get cleanup rules for what files to remove for a task."""
        policy = self.get_policy_for_task(task_id)
        config = self.config
        
        if policy == CleanupPolicy.RETAIN_ALL:
            return {
                "audio_files": False,
                "transcripts": False,
                "llm_outputs": False,
                "audio_segments": False,
                "temp_directories": False
            }
        elif policy == CleanupPolicy.RETAIN_AUDIO_ONLY:
            return {
                "audio_files": not config.retain_audio_files,
                "transcripts": not config.retain_transcripts,
                "llm_outputs": True,
                "audio_segments": True,
                "temp_directories": True
            }
        else:
            # For other policies, use the configuration preferences
            return {
                "audio_files": not config.retain_audio_files,
                "transcripts": not config.retain_transcripts,
                "llm_outputs": not config.retain_llm_outputs,
                "audio_segments": not config.retain_audio_segments,
                "temp_directories": True
            }


# Global cleanup manager instance
_cleanup_manager: Optional[CleanupManager] = None


def get_cleanup_manager() -> CleanupManager:
    """Get the global cleanup manager instance."""
    global _cleanup_manager
    if _cleanup_manager is None:
        _cleanup_manager = CleanupManager()
    return _cleanup_manager

# Initialize the global instance for easy import
cleanup_manager = get_cleanup_manager()
