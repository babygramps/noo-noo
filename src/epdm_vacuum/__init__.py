"""
EPDM Vacuum Fixture Control Software

A comprehensive control system for EPDM gasket vacuum seal testing,
running on Raspberry Pi 5 with PyQt5 GUI and Flask API.

Hardware Support:
- WidgetLords PLC DAQ (SPI) - Analog inputs and relay outputs
- TLB4 Load Cell Transmitter (Modbus RTU) - Four 200kg load cells
- SPT25-20-V30D Pressure Sensor - 0-30 PSI vacuum measurement
"""

__version__ = "1.1.0"
__author__ = "Your Name"
__license__ = "Proprietary"

# Package-level imports for convenience
from . import daq
from . import gui
from . import control
from . import logging as epdm_logging
from . import api
from . import config

__all__ = [
    "daq",
    "gui", 
    "control",
    "epdm_logging",
    "api",
    "config",
]

