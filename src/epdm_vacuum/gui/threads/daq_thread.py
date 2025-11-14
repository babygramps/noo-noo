"""
Data Acquisition Thread

Background thread for continuously reading sensor data without blocking the GUI.
Emits signals with new data for GUI updates.
"""

from typing import Optional, Dict, Any
import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class DataAcquisitionThread(QThread):
    """
    Background thread for data acquisition from hardware.
    
    Continuously reads sensors at a specified rate and emits
    data to the main GUI thread via signals.
    """
    
    # Signals
    new_data = pyqtSignal(dict)  # Emitted when new data is available
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    
    def __init__(
        self,
        sample_rate: float = 10.0,
        widgetlords_interface=None,
        modbus_interface=None,
    ):
        """
        Initialize the DAQ thread.
        
        Args:
            sample_rate: Sampling rate in Hz
            widgetlords_interface: WidgetLords hardware interface
            modbus_interface: Modbus hardware interface
        """
        super().__init__()
        
        self.sample_rate = sample_rate
        self.sample_interval = 1.0 / sample_rate
        self.running = False
        
        self.widgetlords = widgetlords_interface
        self.modbus = modbus_interface
        
        logger.info(f"DAQ thread initialized with sample rate: {sample_rate} Hz")
    
    def run(self) -> None:
        """
        Main thread execution loop.
        
        Continuously reads sensors at the specified rate until stopped.
        """
        logger.info("DAQ thread started")
        self.running = True
        
        # TODO: Initialize hardware interfaces if not already done
        if self.widgetlords is None or self.modbus is None:
            logger.warning("Hardware interfaces not initialized - using mock data")
        
        while self.running:
            try:
                # Read all sensors
                data = self.read_sensors()
                
                # Emit data to GUI
                self.new_data.emit(data)
                
                # Sleep to maintain sample rate
                time.sleep(self.sample_interval)
                
            except Exception as e:
                error_msg = f"DAQ error: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.error_occurred.emit(error_msg)
                
                # Brief pause before retrying
                time.sleep(0.5)
        
        logger.info("DAQ thread stopped")
    
    def read_sensors(self) -> Dict[str, Any]:
        """
        Read all sensors and compile data.
        
        Returns:
            Dict containing all sensor readings with timestamp
        """
        timestamp = time.time()
        
        # Read WidgetLords (pressure sensor)
        if self.widgetlords:
            try:
                wl_data = self.widgetlords.read()
            except Exception as e:
                logger.error(f"WidgetLords read error: {e}")
                wl_data = {}
        else:
            # Mock data for development
            wl_data = {
                "pressure_voltage": 5.0,
                "pressure_psi": 15.0,
                "vacuum_bar": 0.0,
            }
        
        # Read Modbus (load cells)
        if self.modbus:
            try:
                modbus_data = self.modbus.read()
            except Exception as e:
                logger.error(f"Modbus read error: {e}")
                modbus_data = {}
        else:
            # Mock data for development
            modbus_data = {
                "gross_weight_kg": 100.0,
                "load_cell_1_kg": 25.0,
                "load_cell_2_kg": 25.0,
                "load_cell_3_kg": 25.0,
                "load_cell_4_kg": 25.0,
            }
        
        # Combine all data
        combined_data = {
            "timestamp": timestamp,
            **wl_data,
            **modbus_data,
        }
        
        return combined_data
    
    def stop(self) -> None:
        """Stop the DAQ thread gracefully."""
        logger.info("Stopping DAQ thread...")
        self.running = False
    
    def set_sample_rate(self, rate: float) -> None:
        """
        Change the sampling rate.
        
        Args:
            rate: New sample rate in Hz
        """
        if rate <= 0:
            logger.error(f"Invalid sample rate: {rate}")
            return
        
        self.sample_rate = rate
        self.sample_interval = 1.0 / rate
        logger.info(f"Sample rate changed to {rate} Hz")
    
    def set_hardware_interfaces(self, widgetlords=None, modbus=None) -> None:
        """
        Set hardware interface objects.
        
        Args:
            widgetlords: WidgetLords interface
            modbus: Modbus interface
        """
        if widgetlords:
            self.widgetlords = widgetlords
            logger.info("WidgetLords interface set")
        
        if modbus:
            self.modbus = modbus
            logger.info("Modbus interface set")

