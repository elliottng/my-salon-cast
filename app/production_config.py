"""
Production Configuration for MySalonCast MCP Server
Handles environment-specific settings, monitoring, and error handling for Cloud Run deployment.
"""

import os
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime

class ProductionConfig:
    """Production-specific configuration and utilities."""
    
    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local").lower()
        self.is_production = self.environment == "production"
        self.is_staging = self.environment == "staging"
        self.is_cloud = self.is_production or self.is_staging
        
    def setup_logging(self):
        """Configure logging for production environments."""
        if self.is_cloud:
            # Cloud Run structured logging
            logging.basicConfig(
                level=logging.INFO,
                format='{"timestamp":"%(asctime)s","severity":"%(levelname)s","service":"mcp-server","message":"%(message)s","logger":"%(name)s"}',
                stream=sys.stdout
            )
        else:
            # Local development logging
            logging.basicConfig(
                level=logging.DEBUG,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
        # Set specific log levels for noisy libraries
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('httpcore').setLevel(logging.WARNING)
        logging.getLogger('uvicorn.access').setLevel(logging.INFO)
        
    def get_server_config(self) -> Dict[str, Any]:
        """Get server configuration based on environment."""
        base_config = {
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", 8000)),
            "access_log": True,
            "log_level": "info"
        }
        
        if self.is_cloud:
            # Production/staging configuration
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
    
    def validate_required_env_vars(self) -> Dict[str, str]:
        """Validate required environment variables and return warnings."""
        required_vars = {
            "PROJECT_ID": "Google Cloud Project ID",
            "ENVIRONMENT": "Deployment environment"
        }
        
        conditional_vars = {
            # Only required in cloud environments
            "GEMINI_API_KEY": "Gemini API key for podcast generation",
            "GOOGLE_TTS_API_KEY": "Google Text-to-Speech API key"
        }
        
        missing = []
        warnings = []
        
        # Check required vars
        for var, description in required_vars.items():
            if not os.getenv(var):
                missing.append(f"{var} ({description})")
        
        # Check conditional vars for cloud environments
        if self.is_cloud:
            for var, description in conditional_vars.items():
                if not os.getenv(var):
                    missing.append(f"{var} ({description})")
        else:
            # Just warnings for local development
            for var, description in conditional_vars.items():
                if not os.getenv(var):
                    warnings.append(f"{var} not set - {description} features may be limited")
        
        if missing:
            error_msg = f"Missing required environment variables: {', '.join(missing)}"
            if self.is_cloud:
                raise EnvironmentError(error_msg)
            else:
                warnings.append(error_msg)
        
        return {"warnings": warnings}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status for monitoring."""
        try:
            env_validation = self.validate_required_env_vars()
            
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "environment": self.environment,
                "service": "MySalonCast MCP Server",
                "version": "1.0.0",
                "checks": {
                    "environment": "ok",
                    "configuration": "ok" if not env_validation["warnings"] else "warning",
                    "database": "ok",  # Assume OK, can be enhanced
                    "services": "ok"   # Assume OK, can be enhanced
                },
                "warnings": env_validation.get("warnings", [])
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
    
    def log_startup_info(self):
        """Log startup information for monitoring."""
        logger = logging.getLogger(__name__)
        
        logger.info("=" * 60)
        logger.info("MySalonCast MCP Server Starting")
        logger.info("=" * 60)
        logger.info(f"Environment: {self.environment}")
        logger.info(f"Project ID: {os.getenv('PROJECT_ID', 'Not set')}")
        logger.info(f"Host: {os.getenv('HOST', '0.0.0.0')}")
        logger.info(f"Port: {os.getenv('PORT', '8000')}")
        logger.info(f"Cloud deployment: {self.is_cloud}")
        
        # Log environment validation
        try:
            env_validation = self.validate_required_env_vars()
            if env_validation["warnings"]:
                for warning in env_validation["warnings"]:
                    logger.warning(f"Configuration: {warning}")
            else:
                logger.info("Configuration: All required environment variables present")
        except EnvironmentError as e:
            logger.error(f"Configuration error: {e}")
            if self.is_cloud:
                sys.exit(1)
        
        logger.info("=" * 60)

# Global production config instance
production_config = ProductionConfig()

def setup_production_environment():
    """Setup production environment configuration."""
    production_config.setup_logging()
    production_config.log_startup_info()
    return production_config

def get_server_config() -> Dict[str, Any]:
    """Get server configuration for uvicorn."""
    return production_config.get_server_config()

def get_health_status() -> Dict[str, Any]:
    """Get health status for monitoring."""
    return production_config.get_health_status()
