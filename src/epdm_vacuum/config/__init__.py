"""
Config Module - Configuration Management

This module handles:
- Loading configuration from YAML files
- Environment variable management
- Hardware parameter settings
"""

from .settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]

