#!/usr/bin/env python3
"""
EPDM Vacuum Fixture - API Server Entry Point

Main entry point for the Flask API application.
"""

import sys
import logging
from pathlib import Path

from .api.routes import create_app
from .config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("epdm_vacuum_api.log"),
    ],
)

logger = logging.getLogger(__name__)


def setup_logging(settings):
    """
    Configure logging based on settings.
    
    Args:
        settings: Settings instance
    """
    log_level = settings.get("logging", "log_level", default="INFO")
    level = getattr(logging, log_level.upper(), logging.INFO)
    
    logging.getLogger().setLevel(level)
    logger.info(f"Logging level set to {log_level}")


def main():
    """Main API server entry point."""
    logger.info("=" * 60)
    logger.info("EPDM Vacuum Fixture API Server - Starting")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config_file = Path(__file__).parent / "config" / "hardware_config.yaml"
        settings = get_settings(str(config_file))
        setup_logging(settings)
        
        logger.info(f"Configuration loaded from: {config_file}")
        
        # Get API settings
        api_host = settings.get("api", "host", default="0.0.0.0")
        api_port = settings.get("api", "port", default=8000)
        api_debug = settings.get("api", "debug", default=False)
        
        # Create Flask app
        app = create_app(debug=api_debug)
        
        logger.info(f"Flask app created (debug={'ON' if api_debug else 'OFF'})")
        logger.info(f"API server will listen on {api_host}:{api_port}")
        logger.info("API ready")
        
        # Run Flask development server
        # Note: For production, use a WSGI server like gunicorn
        app.run(host=api_host, port=api_port, debug=api_debug)
        
        return 0
        
    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

