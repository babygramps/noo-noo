"""
DAQ Module - Hardware Abstraction Layer

This module provides interfaces for all hardware components:
- WidgetLords SPI modules (analog input, relay output)
- Modbus RTU communication (load cells)
- LCD display via Arduino (status display)
- Sensor calibration management
"""

from .hardware_interface import HardwareInterface
from .widgetlords_interface import WidgetLordsInterface
from .modbus_interface import ModbusInterface
from .calibration import CalibrationManager
from .lcd_interface import LCDInterface, create_lcd_interface_from_config, list_serial_ports

__all__ = [
    "HardwareInterface",
    "WidgetLordsInterface",
    "ModbusInterface",
    "CalibrationManager",
    "LCDInterface",
    "create_lcd_interface_from_config",
    "list_serial_ports",
]

