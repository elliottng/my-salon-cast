"""Configuration management for MySalonCast MCP server with Cloud Run support."""

import os
import logging
from typing import Optional, Dict, Any

class Config:
    """Configuration class with environment detection and environment variable management."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.project_id = os.getenv("PROJECT_ID")
        self.region = os.getenv("REGION", "us-west1")
        
        # Log configuration warnings for missing required environment variables
        missing_vars = []
        if not self.gemini_api_key:
            missing_vars.append("GEMINI_API_KEY")
        if not self.google_tts_api_key:
            missing_vars.append("GOOGLE_TTS_API_KEY")
        
        if missing_vars:
            logging.warning("Configuration warnings:")
            for var in missing_vars:
                if var == "GEMINI_API_KEY":
                    logging.warning(f"  - {var} not configured (podcast generation disabled)")
                elif var == "GOOGLE_TTS_API_KEY":
                    logging.warning(f"  - {var} not configured (TTS features disabled)")
    
    @property
    def is_cloud_environment(self) -> bool:
        """Check if running in cloud environment (staging or production)."""
        return self.environment in ["staging", "production"]
    
    @property
    def is_local_environment(self) -> bool:
        """Check if running in local development environment."""
        return self.environment == "local"
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from environment variables."""
        return os.getenv("GEMINI_API_KEY")
    
    @property
    def google_tts_api_key(self) -> Optional[str]:
        """Get Google TTS API key from environment variables."""
        return os.getenv("GOOGLE_TTS_API_KEY")
    
    @property
    def audio_bucket(self) -> Optional[str]:
        """Get the audio storage bucket name."""
        return os.getenv("AUDIO_BUCKET")
    
    @property
    def database_bucket(self) -> Optional[str]:
        """Get the database storage bucket name."""
        return os.getenv("DATABASE_BUCKET")
    
    @property
    def database_url(self) -> str:
        """Get the database URL."""
        return os.getenv("DATABASE_URL", "sqlite:///podcast_status.db")
    
    @property
    def server_host(self) -> str:
        """Get the server host."""
        if self.is_cloud_environment:
            return "0.0.0.0"
        return os.getenv("HOST", "127.0.0.1")
    
    @property
    def server_port(self) -> int:
        """Get the server port."""
        return int(os.getenv("PORT", "8000"))
    
    @property
    def max_concurrent_generations(self) -> int:
        """Get maximum concurrent podcast generations."""
        default = 4 if self.environment == "production" else 2
        return int(os.getenv("MAX_CONCURRENT_GENERATIONS", str(default)))
    
    @property
    def cors_origins(self) -> list:
        """Get allowed CORS origins."""
        if self.is_local_environment:
            return ["*"]  # Allow all origins in local development
        
        origins_str = os.getenv("ALLOWED_ORIGINS", "")
        if origins_str:
            return [origin.strip() for origin in origins_str.split(",")]
        
        # Default production origins
        return ["https://*.google.com", "https://*.googleapis.com"]
    
    @property
    def log_level(self) -> str:
        """Get logging level."""
        return os.getenv("LOG_LEVEL", "INFO")
    
    @property
    def audio_cleanup_policy(self) -> str:
        """Get audio cleanup policy."""
        default = "auto_after_days" if self.environment == "production" else "auto_after_hours"
        return os.getenv("AUDIO_CLEANUP_POLICY", default)
    
    def setup_logging(self):
        """Setup logging configuration for the environment."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Configure logging format
        if self.is_cloud_environment:
            # Structured logging for Cloud Logging
            format_str = '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        else:
            # Human-readable logging for local development
            format_str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        
        logging.basicConfig(
            level=log_level,
            format=format_str,
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Set specific loggers to appropriate levels
        if log_level == logging.DEBUG:
            logging.getLogger("google.cloud").setLevel(logging.INFO)
            logging.getLogger("urllib3").setLevel(logging.WARNING)
        
        logging.info(f"Logging configured for {self.environment} environment at {self.log_level} level")
    
    def validate_required_config(self) -> Dict[str, Any]:
        """
        Validate that required configuration is available.
        
        Returns:
            Dict with validation results
        """
        issues = []
        warnings = []
        
        # Check API keys
        if not self.gemini_api_key:
            issues.append("GEMINI_API_KEY not configured")
        
        if not self.google_tts_api_key:
            warnings.append("GOOGLE_TTS_API_KEY not configured (TTS features disabled)")
        
        # Check cloud storage configuration for cloud environments
        if self.is_cloud_environment:
            if not self.project_id:
                issues.append("PROJECT_ID not configured")
            
            if not self.audio_bucket:
                warnings.append("AUDIO_BUCKET not configured")
            
            if not self.database_bucket:
                warnings.append("DATABASE_BUCKET not configured")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "environment": self.environment,
            "cloud_environment": self.is_cloud_environment
        }


def get_config() -> Config:
    """Get the application configuration."""
    return Config()


def setup_environment():
    """Setup the application environment and configuration."""
    config = get_config()
    
    # Setup logging
    config.setup_logging()
    
    # Validate configuration
    validation = config.validate_required_config()
    
    if not validation["valid"]:
        logging.error("Configuration validation failed:")
        for issue in validation["issues"]:
            logging.error(f"  - {issue}")
        raise RuntimeError("Invalid configuration. Cannot start application.")
    
    if validation["warnings"]:
        logging.warning("Configuration warnings:")
        for warning in validation["warnings"]:
            logging.warning(f"  - {warning}")
    
    logging.info(f"Environment setup complete for {config.environment}")
    logging.info(f"Server will run on {config.server_host}:{config.server_port}")
    logging.info(f"Max concurrent generations: {config.max_concurrent_generations}")
    
    return config
