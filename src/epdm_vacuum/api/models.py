"""
API Models - Data Models for REST API

Defines data structures for API requests and responses.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SensorData:
    """
    Sensor data snapshot.
    
    Represents a single moment of sensor readings.
    """
    timestamp: float
    vacuum_bar: float
    pressure_psi: float
    gross_weight_kg: float
    load_cell_1_kg: float
    load_cell_2_kg: float
    load_cell_3_kg: float
    load_cell_4_kg: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SensorData":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class TestStatus:
    """
    Test status information.
    
    Provides current state of the test system.
    """
    state: str
    test_running: bool
    pump_on: bool
    start_time: Optional[float]
    elapsed_time: float
    data_points_collected: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStatus":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SafetyStatus:
    """
    Safety system status.
    
    Provides current safety state and limits.
    """
    state: str
    safe_to_operate: bool
    max_vacuum_bar: float
    max_force_kg: float
    violation_counts: Dict[str, int]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyStatus":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class SystemInfo:
    """
    System information.
    
    Provides overall system status and capabilities.
    """
    version: str
    hardware_connected: bool
    uptime_seconds: float
    total_tests_run: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SystemInfo":
        """Create from dictionary."""
        return cls(**data)


class APIResponse:
    """
    Standard API response wrapper.
    
    Provides consistent response format for all endpoints.
    """
    
    @staticmethod
    def success(data: Any = None, message: str = "Success") -> Dict[str, Any]:
        """
        Create success response.
        
        Args:
            data: Response data
            message: Success message
        
        Returns:
            Dict: Response dictionary
        """
        return {
            "status": "success",
            "message": message,
            "data": data,
            "timestamp": datetime.now().isoformat(),
        }
    
    @staticmethod
    def error(message: str, code: int = 500, details: Any = None) -> Dict[str, Any]:
        """
        Create error response.
        
        Args:
            message: Error message
            code: HTTP status code
            details: Additional error details
        
        Returns:
            Dict: Response dictionary
        """
        return {
            "status": "error",
            "message": message,
            "code": code,
            "details": details,
            "timestamp": datetime.now().isoformat(),
        }


def validate_sensor_data(data: Dict[str, Any]) -> bool:
    """
    Validate sensor data dictionary.
    
    Args:
        data: Sensor data to validate
    
    Returns:
        bool: True if valid
    """
    required_keys = [
        "timestamp",
        "vacuum_bar",
        "pressure_psi",
        "gross_weight_kg",
    ]
    
    for key in required_keys:
        if key not in data:
            logger.warning(f"Missing required key in sensor data: {key}")
            return False
    
    return True


def format_sensor_data_for_api(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format raw sensor data for API response.
    
    Args:
        raw_data: Raw sensor data from hardware
    
    Returns:
        Dict: Formatted data
    """
    return {
        "timestamp": raw_data.get("timestamp", 0.0),
        "vacuum": {
            "bar": raw_data.get("vacuum_bar", 0.0),
            "psi": raw_data.get("vacuum_psi", 0.0),
        },
        "pressure": {
            "psi": raw_data.get("pressure_psi", 0.0),
            "voltage": raw_data.get("pressure_voltage", 0.0),
        },
        "force": {
            "total_kg": raw_data.get("gross_weight_kg", 0.0),
            "load_cells": [
                raw_data.get("load_cell_1_kg", 0.0),
                raw_data.get("load_cell_2_kg", 0.0),
                raw_data.get("load_cell_3_kg", 0.0),
                raw_data.get("load_cell_4_kg", 0.0),
            ],
        },
    }

