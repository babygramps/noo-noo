"""
DAQ Module - Hardware Abstraction Layer

This module provides interfaces for all hardware components:
- WidgetLords SPI modules (analog input, relay output)
- Modbus RTU communication (load cells)
- Sensor calibration management
"""

from .hardware_interface import HardwareInterface
from .widgetlords_interface import WidgetLordsInterface
from .modbus_interface import ModbusInterface
from .calibration import CalibrationManager

__all__ = [
    "HardwareInterface",
    "WidgetLordsInterface",
    "ModbusInterface",
    "CalibrationManager",
]

