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
        logger.info("=" * 60)
        logger.info("DAQ THREAD STARTED")
        logger.info("=" * 60)
        logger.info(f"  Sample rate: {self.sample_rate} Hz")
        logger.info(f"  Sample interval: {self.sample_interval:.3f} s")
        logger.info(f"  WidgetLords interface: {'CONNECTED' if self.widgetlords else 'NOT CONNECTED'}")
        logger.info(f"  Modbus interface: {'CONNECTED' if self.modbus else 'NOT CONNECTED'}")
        
        if self.widgetlords:
            modules = self.widgetlords.list_modules() if hasattr(self.widgetlords, 'list_modules') else {}
            logger.info(f"  WidgetLords modules: {modules}")
            
            # Log analog input modules specifically
            if hasattr(self.widgetlords, 'analog_input_modules'):
                for name, module in self.widgetlords.analog_input_modules.items():
                    logger.info(f"    Analog Module '{name}':")
                    logger.info(f"      Chip Enable: {module.chip_enable}")
                    logger.info(f"      Hardware initialized: {module._hardware is not None}")
                    for ch in module.channels:
                        if ch.enabled:
                            logger.info(f"      Ch{ch.channel} '{ch.name}': {ch.input_type}, "
                                      f"span {ch.low_input}->{ch.high_input} to {ch.low_output}->{ch.high_output} {ch.units}")
        
        self.running = True
        
        # Check hardware interfaces
        if self.widgetlords is None and self.modbus is None:
            logger.warning("=" * 60)
            logger.warning("NO HARDWARE INTERFACES - USING MOCK DATA")
            logger.warning("=" * 60)
        elif self.widgetlords is None:
            logger.warning("WidgetLords interface not initialized - analog inputs will use mock data")
        elif self.modbus is None:
            logger.warning("Modbus interface not initialized - load cells will use mock data")
        logger.info("=" * 60)
        
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
        
        # Track read count for verbose logging of first few reads
        if not hasattr(self, '_sensor_read_count'):
            self._sensor_read_count = 0
        self._sensor_read_count += 1
        
        # Read WidgetLords (pressure sensor)
        if self.widgetlords:
            try:
                wl_data = self.widgetlords.read()
                # Log first 5 reads at INFO level for debugging
                if self._sensor_read_count <= 5:
                    logger.info(f"[DAQ Read #{self._sensor_read_count}] WidgetLords data keys: {list(wl_data.keys())}")
                    pressure_keys = ["pressure_voltage", "pressure_psi", "vacuum_psi", "vacuum_bar"]
                    pressure_data = {k: wl_data.get(k) for k in pressure_keys if k in wl_data}
                    if pressure_data:
                        logger.info(f"  Pressure data: {pressure_data}")
                    # Also log raw analog inputs
                    if "analog_inputs_raw" in wl_data:
                        logger.info(f"  Raw analog inputs: {wl_data['analog_inputs_raw']}")
                else:
                    # Log at debug level after first 5
                    pressure_keys = ["pressure_voltage", "pressure_psi", "vacuum_psi", "vacuum_bar", "analog_inputs"]
                    pressure_data = {k: wl_data.get(k) for k in pressure_keys if k in wl_data}
                    if pressure_data:
                        logger.debug(f"WidgetLords pressure data: {pressure_data}")
            except Exception as e:
                logger.error(f"WidgetLords read error: {e}", exc_info=True)
                wl_data = {}
        else:
            # Mock data for development
            if self._sensor_read_count <= 5:
                logger.info(f"[DAQ Read #{self._sensor_read_count}] WidgetLords NOT CONNECTED - using mock data")
            else:
                logger.debug("WidgetLords not connected - using mock data")
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
                logger.error(f"Modbus read error: {e}", exc_info=True)
                modbus_data = {}
        else:
            # Mock data for development
            logger.debug("Modbus not connected - using mock data")
            modbus_data = {
                "gross_weight_kg": 100.0,
                "load_cell_1_kg": 25.0,
                "load_cell_2_kg": 25.0,
                "load_cell_3_kg": 25.0,
                "load_cell_4_kg": 25.0,
            }
        
        # Create human-readable datetime
        from datetime import datetime
        datetime_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Combine all data
        combined_data = {
            "timestamp": timestamp,
            "datetime": datetime_str,
            "stage_name": "N/A",  # Stage info not available in DAQ thread (only during test execution)
            "test_state": "monitoring",  # DAQ is continuous monitoring
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

