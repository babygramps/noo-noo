"""
Hardware Interface - Base Abstraction Layer

Provides the base interface for all hardware interactions.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HardwareInterface(ABC):
    """
    Abstract base class for hardware interfaces.
    
    All hardware interfaces (WidgetLords, Modbus, etc.) should inherit
    from this class and implement the required methods.
    """
    
    def __init__(self):
        """Initialize the hardware interface."""
        self.initialized = False
        self.error_count = 0
        self.last_error: Optional[str] = None
        logger.info(f"Initializing {self.__class__.__name__}")
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the hardware.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the hardware.
        
        Returns:
            bool: True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def read(self) -> Dict[str, Any]:
        """
        Read data from the hardware.
        
        Returns:
            Dict[str, Any]: Dictionary containing sensor readings
        """
        pass
    
    @abstractmethod
    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write data to the hardware.
        
        Args:
            data: Dictionary containing commands/values to write
            
        Returns:
            bool: True if write successful, False otherwise
        """
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """
        Check if hardware is connected and responding.
        
        Returns:
            bool: True if connected and responsive, False otherwise
        """
        pass
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of the hardware interface.
        
        Returns:
            Dict[str, Any]: Status information including connection state, errors, etc.
        """
        return {
            "initialized": self.initialized,
            "connected": self.is_connected(),
            "error_count": self.error_count,
            "last_error": self.last_error,
        }
    
    def handle_error(self, error: Exception) -> None:
        """
        Handle and log hardware errors.
        
        Args:
            error: The exception that occurred
        """
        self.error_count += 1
        self.last_error = str(error)
        logger.error(f"{self.__class__.__name__} error: {error}", exc_info=True)
    
    def reset_error_count(self) -> None:
        """Reset the error counter."""
        self.error_count = 0
        self.last_error = None
        logger.info(f"{self.__class__.__name__} error count reset")

