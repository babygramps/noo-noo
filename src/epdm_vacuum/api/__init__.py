"""
API Module - Flask REST API

This module provides HTTP API endpoints for:
- Remote monitoring of test status
- Real-time data access
- Basic control operations (optional)
"""

from .routes import create_app
from .models import SensorData, TestStatus

__all__ = ["create_app", "SensorData", "TestStatus"]

