#!/usr/bin/env python3
"""
EPDM Vacuum Fixture - GUI Application Entry Point

Main entry point for the PyQt5 GUI application.
"""

import sys
import logging
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
    """Main application entry point."""
    logger.info("=" * 60)
    logger.info("EPDM Vacuum Seal Test Fixture - Starting")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        config_file = Path(__file__).parent / "config" / "hardware_config.yaml"
        settings = get_settings(str(config_file))
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

