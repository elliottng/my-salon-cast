"""Configuration management for MySalonCast MCP server with Cloud Run support."""

import os
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file at module import time
load_dotenv()

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
        
        # Check for deprecated environment variables
        if os.getenv("GOOGLE_TTS_API_KEY"):
            logging.warning("GOOGLE_TTS_API_KEY is deprecated and no longer used. TTS functionality is handled differently.")
        
        if missing_vars:
            logging.warning("Configuration warnings:")
            for var in missing_vars:
                if var == "GEMINI_API_KEY":
                    logging.warning(f"  - {var} not configured (podcast generation disabled)")
    
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
    def audio_bucket(self) -> Optional[str]:
        """Get the audio storage bucket name."""
        return os.getenv("AUDIO_BUCKET")
    
    @property
    def database_url(self) -> str:
        """Get the database URL."""
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL not configured")
        return url
    
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

    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration for uvicorn (used by both REST and MCP servers)."""
        base_config = {
            "host": self.server_host,
            "port": self.server_port,
            "access_log": True,
            "log_level": "info" if self.is_cloud_environment else "debug"
        }
        
        if self.is_cloud_environment:
            # Production/staging configuration for Cloud Run
            base_config.update({
                "workers": 1,  # Single worker for Cloud Run
                "timeout_keep_alive": 30,
                "timeout_graceful_shutdown": 30,
            })
        else:
            # Local development configuration
            base_config.update({
                "reload": False,  # Disable reload in production mode
                "log_level": "debug"
            })
            
        return base_config

    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for monitoring."""
        try:
            validation = self.validate_required_config()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "environment": self.environment,
                "service": "MySalonCast Server",
                "version": "1.0.0",
                "checks": {
                    "environment": "ok",
                    "configuration": "ok" if validation["valid"] else "warning",
                    "database": "ok",
                    "services": "ok"
                },
                "warnings": validation.get("warnings", []),
                "issues": validation.get("issues", [])
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "environment": self.environment,
                "error": str(e),
                "checks": {
                    "environment": "error",
                    "configuration": "error"
                }
            }

    def log_startup_info(self, server_type: str = "Server"):
        """Log startup information for monitoring."""
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info(f"MySalonCast {server_type} Starting")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Project ID: {self.project_id or 'Not set'}")
        logger.info(f"Host: {self.server_host}")
        logger.info(f"Port: {self.server_port}")
        logger.info(f"Cloud deployment: {self.is_cloud_environment}")
        
        # Log environment validation
        validation = self.validate_required_config()
        if validation["warnings"]:
            for warning in validation["warnings"]:
                logger.warning(f"Configuration: {warning}")
        if validation["issues"]:
            for issue in validation["issues"]:
                logger.error(f"Configuration issue: {issue}")
            if self.is_cloud_environment:
                raise RuntimeError("Configuration validation failed in cloud environment")
        else:
            logger.info("Configuration: All required settings validated")
        
        logger.info("=" * 60)

    def setup_logging(self):
        """Setup logging configuration for the environment."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)
        
        # Configure logging format
        if self.is_cloud_environment:
            # Structured logging for Cloud Logging
            format_str = '{"timestamp":"%(asctime)s","severity":"%(levelname)s","service":"mysaloncast","message":"%(message)s","logger":"%(name)s"}'
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
            logging.getLogger("httpx").setLevel(logging.WARNING)
            logging.getLogger("httpcore").setLevel(logging.WARNING)
            logging.getLogger("uvicorn.access").setLevel(logging.INFO)
        
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
        if not os.getenv("DATABASE_URL"):
            issues.append("DATABASE_URL not configured")
        
        # Check cloud storage configuration for cloud environments
        if self.is_cloud_environment:
            if not self.project_id:
                issues.append("PROJECT_ID not configured")
            
            if not self.audio_bucket:
                warnings.append("AUDIO_BUCKET not configured")
            
        
        # Warn about deprecated environment variables
        if os.getenv("GOOGLE_TTS_API_KEY"):
            warnings.append("GOOGLE_TTS_API_KEY is deprecated and no longer used")
        
        # Check Firecrawl configuration
        firecrawl_enabled = os.getenv("FIRECRAWL_ENABLED", "").lower() == "true"
        if firecrawl_enabled:
            if not os.getenv("FIRECRAWL_API_KEY"):
                warnings.append("FIRECRAWL_ENABLED is true but FIRECRAWL_API_KEY is not set")
            
            # Check if firecrawl-py is installed
            try:
                import firecrawl
            except ImportError:
                warnings.append("FIRECRAWL_ENABLED is true but firecrawl-py is not installed")
        
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


def setup_environment(server_type: str = "Server"):
    """Setup the application environment and configuration."""
    config = get_config()
    
    # Setup logging
    config.setup_logging()
    
    # Log startup information with server type
    config.log_startup_info(server_type)
    
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


def setup_production_environment(server_type: str = "MCP Server"):
    """Setup production environment configuration for MCP server."""
    config = get_config()
    
    # Setup logging
    config.setup_logging()
    
    # Log startup information with server type
    config.log_startup_info(server_type)
    
    return config


def get_server_config() -> Dict[str, Any]:
    """Get server configuration for uvicorn."""
    config = get_config()
    return config.get_server_config()


def get_health_status() -> Dict[str, Any]:
    """Get health status for monitoring."""
    config = get_config()
    return config.get_health_status()
