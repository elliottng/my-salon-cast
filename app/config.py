"""Configuration management for MySalonCast MCP server with Cloud Run support."""

import os
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

# Import Google Cloud Secret Manager client (optional for local development)
try:
    from google.cloud import secretmanager
    SECRET_MANAGER_AVAILABLE = True
except ImportError:
    SECRET_MANAGER_AVAILABLE = False
    logging.warning("Google Cloud Secret Manager not available. Using environment variables.")

class Config:
    """Configuration class with environment detection and secret management."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.project_id = os.getenv("PROJECT_ID")
        self.region = os.getenv("REGION", "us-west1")
        
        # Initialize Secret Manager client if available and in cloud environment
        self.secret_client = None
        if SECRET_MANAGER_AVAILABLE and self.project_id and self.environment in ["staging", "production"]:
            try:
                self.secret_client = secretmanager.SecretManagerServiceClient()
                logging.info("Secret Manager client initialized successfully")
            except Exception as e:
                logging.warning(f"Failed to initialize Secret Manager client: {e}")
    
    @property
    def is_cloud_environment(self) -> bool:
        """Check if running in cloud environment (staging or production)."""
        return self.environment in ["staging", "production"]
    
    @property
    def is_local_environment(self) -> bool:
        """Check if running in local development environment."""
        return self.environment == "local"
    
    def get_secret(self, secret_id: str, fallback_env_var: Optional[str] = None) -> Optional[str]:
        """
        Get a secret from Secret Manager or fallback to environment variable.
        
        Args:
            secret_id: The Secret Manager secret ID
            fallback_env_var: Environment variable to use as fallback
            
        Returns:
            The secret value or None if not found
        """
        # Try Secret Manager first in cloud environments
        if self.secret_client and self.project_id:
            try:
                secret_name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
                response = self.secret_client.access_secret_version(request={"name": secret_name})
                secret_value = response.payload.data.decode("UTF-8")
                logging.debug(f"Retrieved secret {secret_id} from Secret Manager")
                return secret_value
            except Exception as e:
                logging.warning(f"Failed to retrieve secret {secret_id} from Secret Manager: {e}")
        
        # Fallback to environment variable
        if fallback_env_var:
            env_value = os.getenv(fallback_env_var)
            if env_value:
                logging.debug(f"Using environment variable {fallback_env_var} for {secret_id}")
                return env_value
        
        # Try direct environment variable with secret_id name (converted to env var format)
        env_var_name = secret_id.upper().replace("-", "_")
        env_value = os.getenv(env_var_name)
        if env_value:
            logging.debug(f"Using environment variable {env_var_name}")
            return env_value
        
        logging.warning(f"Secret {secret_id} not found in Secret Manager or environment variables")
        return None
    
    @property
    def gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from secrets or environment."""
        return self.get_secret("gemini-api-key", "GEMINI_API_KEY")
    
    @property
    def google_tts_api_key(self) -> Optional[str]:
        """Get Google TTS API key from secrets or environment."""
        return self.get_secret("google-tts-api-key", "GOOGLE_TTS_API_KEY")
    
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


@lru_cache()
def get_config() -> Config:
    """Get the application configuration (cached)."""
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
