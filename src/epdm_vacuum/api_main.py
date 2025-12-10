#!/usr/bin/env python3
"""
EPDM Vacuum Fixture - FastAPI Server Entry Point

Main entry point for the FastAPI web application.
Provides REST API and WebSocket for real-time data streaming.

Usage:
    python -m epdm_vacuum.api_main
    uvicorn epdm_vacuum.api_main:app --host 0.0.0.0 --port 8000
"""

import sys
import logging
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .api.hardware_manager import get_hardware_manager
from .api.websocket import sensor_broadcaster, event_broadcaster
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


def setup_event_callbacks(hardware_manager, loop: asyncio.AbstractEventLoop):
    """
    Set up callbacks to bridge hardware events to WebSocket broadcasts.
    
    Args:
        hardware_manager: The HardwareManager instance
        loop: The running asyncio event loop (must be passed from async context)
    """
    
    def status_callback(status: str):
        asyncio.run_coroutine_threadsafe(
            event_broadcaster.broadcast_status(status),
            loop
        )
    
    def stage_callback(stage_index, stages_per_cycle, current_cycle, total_cycles, stage):
        asyncio.run_coroutine_threadsafe(
            event_broadcaster.broadcast_stage_change(
                stage_index,
                stage.name if stage else "Unknown",
                stages_per_cycle,
                current_cycle,
                total_cycles
            ),
            loop
        )
    
    def io_callback(device_name: str, state: bool):
        asyncio.run_coroutine_threadsafe(
            event_broadcaster.broadcast_io_change(device_name, state),
            loop
        )
    
    def progress_callback(progress: float, status: str):
        asyncio.run_coroutine_threadsafe(
            event_broadcaster.broadcast_progress(progress, status),
            loop
        )
    
    def completion_callback():
        asyncio.run_coroutine_threadsafe(
            event_broadcaster.broadcast_test_complete(),
            loop
        )
    
    hardware_manager.add_status_callback(status_callback)
    hardware_manager.add_stage_callback(stage_callback)
    hardware_manager.add_io_callback(io_callback)
    hardware_manager.add_progress_callback(progress_callback)
    hardware_manager.add_completion_callback(completion_callback)
    
    logger.info("Event callbacks configured for WebSocket broadcasting")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown of hardware and background tasks.
    """
    logger.info("=" * 60)
    logger.info("EPDM Vacuum Fixture API Server - Starting")
    logger.info("=" * 60)
    
    # Load configuration
    config_file = Path(__file__).parent / "config" / "hardware_config.yaml"
    settings = get_settings(str(config_file))
    setup_logging(settings)
    
    logger.info(f"Configuration loaded from: {config_file}")
    
    # Initialize hardware manager
    hw = get_hardware_manager()
    hw.initialize(str(config_file))
    
    # Set up sensor broadcaster
    sensor_broadcaster.set_hardware_manager(hw)
    
    # Set up event callbacks - capture running loop for thread-safe coroutine scheduling
    # Note: Must use get_running_loop() inside async context (get_event_loop() is deprecated)
    loop = asyncio.get_running_loop()
    setup_event_callbacks(hw, loop)
    
    # Start sensor broadcasting
    await sensor_broadcaster.start()
    
    logger.info("API server ready")
    logger.info("=" * 60)
    
    yield  # Server is running
    
    # Shutdown
    logger.info("=" * 60)
    logger.info("API Server shutting down...")
    
    await sensor_broadcaster.stop()
    hw.shutdown()
    
    logger.info("API Server shutdown complete")
    logger.info("=" * 60)


# Create FastAPI application
app = FastAPI(
    title="EPDM Vacuum Fixture API",
    description="Web API for vacuum seal testing system",
    version="2.0.0",
    lifespan=lifespan,
)

# Configure CORS for browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local network
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


def main():
    """Main API server entry point."""
    import uvicorn
    
    # Get API settings
    config_file = Path(__file__).parent / "config" / "hardware_config.yaml"
    settings = get_settings(str(config_file))
    
    api_host = settings.get("api", "host", default="0.0.0.0")
    api_port = settings.get("api", "port", default=8000)
    api_debug = settings.get("api", "debug", default=False)
    
    logger.info(f"Starting server on {api_host}:{api_port}")
    
    uvicorn.run(
        "epdm_vacuum.api_main:app",
        host=api_host,
        port=api_port,
        reload=api_debug,
        log_level="info",
    )


if __name__ == "__main__":
    main()
