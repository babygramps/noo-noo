"""
Config Module - Configuration Management

This module handles:
- Loading configuration from YAML files
- Environment variable management
- Hardware parameter settings
- TLB4 Modbus configuration
"""

from .settings import (
    Settings,
    get_settings,
    create_tlb4_config_from_settings,
    create_modbus_interface_from_settings,
)

__all__ = [
    "Settings",
    "get_settings",
    "create_tlb4_config_from_settings",
    "create_modbus_interface_from_settings",
]

