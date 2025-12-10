"""
API Module - FastAPI REST API and WebSocket

This module provides:
- HTTP REST API endpoints for monitoring and control
- WebSocket endpoint for real-time data streaming
- Hardware manager singleton for thread-safe hardware access
"""

from .hardware_manager import HardwareManager, get_hardware_manager
from .websocket import connection_manager, sensor_broadcaster, event_broadcaster
from .routes import router

__all__ = [
    "HardwareManager",
    "get_hardware_manager",
    "connection_manager",
    "sensor_broadcaster",
    "event_broadcaster",
    "router",
]
