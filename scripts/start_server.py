#!/usr/bin/env python3
"""
MySalonCast MCP Server startup script with environment detection.
"""

import os
import sys
import uvicorn
import logging
from app.config import get_config

def main():
    """Main startup function."""
    try:
        # Get configuration
        config = get_config()
        
        # Create necessary directories in Cloud Run
        if config.is_cloud_environment:
            os.makedirs("/tmp/database", exist_ok=True)
            os.makedirs("/tmp/audio", exist_ok=True)
            logging.info("Created Cloud Run directories")
        
        # Start the server
        logging.info(f"Starting MySalonCast MCP Server in {config.environment} environment")
        logging.info(f"Server will be available at http://{config.server_host}:{config.server_port}")
        
        uvicorn.run(
            "app.main:app",
            host=config.server_host,
            port=config.server_port,
            reload=config.is_local_environment,  # Only enable reload in local development
            log_level=config.log_level.lower(),
            access_log=True,
            server_header=False,  # Hide server header for security
            date_header=False     # Hide date header for security
        )
        
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
