#!/usr/bin/env python3
"""
EPDM Vacuum Fixture - GUI Application Entry Point

Main entry point for the PyQt5 GUI application.

Usage:
    python -m epdm_vacuum.app_main
    python -m epdm_vacuum.app_main --config /path/to/config.yaml
"""

import sys
import logging
import argparse
import os
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from .gui.main_window import MainWindow
from .config.settings import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("epdm_vacuum.log"),
    ],
)

# Temporarily suppress noisy Modbus logging (set to WARNING to hide INFO/DEBUG)
logging.getLogger("epdm_vacuum.daq.modbus_interface").setLevel(logging.WARNING)
logging.getLogger("minimalmodbus").setLevel(logging.WARNING)

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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="EPDM Vacuum Seal Test Fixture GUI Application"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to configuration YAML file (default: hardware_config.yaml)"
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def main():
    """Main application entry point."""
    # Parse command line arguments first
    args = parse_args()
    
    logger.info("=" * 60)
    logger.info("EPDM Vacuum Seal Test Fixture - Starting")
    logger.info("=" * 60)
    
    try:
        # Determine config file path
        if args.config:
            config_file = Path(args.config)
        else:
            config_file = Path(__file__).parent / "config" / "hardware_config.yaml"
        
        # Load configuration
        settings = get_settings(str(config_file))
        
        # Override log level if debug flag is set
        if args.debug:
            settings.set("logging", "log_level", value="DEBUG")
        
        # Also check LOG_LEVEL environment variable
        env_log_level = os.environ.get("LOG_LEVEL")
        if env_log_level:
            settings.set("logging", "log_level", value=env_log_level)
        
        setup_logging(settings)
        
        logger.info(f"Configuration loaded from: {config_file}")
        
        # Create Qt application
        app = QApplication(sys.argv)
        app.setApplicationName("EPDM Vacuum Fixture")
        app.setOrganizationName("Your Organization")
        
        logger.info("Qt application created")
        
        # Create and show main window
        window = MainWindow()
        window.show()
        
        logger.info("Main window displayed")
        logger.info("Application ready")
        
        # Start event loop
        exit_code = app.exec_()
        
        logger.info(f"Application exiting with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.critical(f"Fatal error during startup: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

