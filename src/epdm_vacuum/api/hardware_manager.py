"""
Hardware Manager - Singleton for Thread-Safe Hardware Access

Provides centralized access to all hardware interfaces for the web API.
Ensures only one instance controls the hardware at any time.
"""

from typing import Optional, Dict, Any, List, Callable
import logging
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class HardwareManager:
    """
    Singleton manager for all hardware interfaces.
    
    Thread-safe access to:
    - WidgetLords SPI modules (relays, analog inputs)
    - Modbus TLB4 load cell transmitter
    - Test controller for sequence execution
    """
    
    _instance: Optional["HardwareManager"] = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if HardwareManager._initialized:
            return
        
        self.widgetlords_interface = None
        self.modbus_interface = None
        self.test_controller = None
        self.data_logger = None
        self.sequence_manager = None
        self.google_drive_uploader = None
        
        # State tracking
        self._connected = False
        self._test_running = False
        self._current_sequence = None
        self._test_thread: Optional[threading.Thread] = None
        self._current_csv_path: Optional[str] = None  # Track CSV path for upload
        
        # Config limits for sequence validation (populated during initialize)
        self._config_limits: Optional[Dict[str, Any]] = None
        
        # Sensor data cache (updated by background thread)
        self._sensor_data: Dict[str, Any] = {}
        self._sensor_lock = threading.Lock()
        self._sensor_thread: Optional[threading.Thread] = None
        self._sensor_thread_running = False
        
        # Callbacks for test events
        self._status_callbacks: List[Callable[[str], None]] = []
        self._stage_callbacks: List[Callable] = []
        self._completion_callbacks: List[Callable] = []
        self._io_callbacks: List[Callable[[str, bool], None]] = []
        self._progress_callbacks: List[Callable[[float, str], None]] = []
        
        HardwareManager._initialized = True
        logger.info("HardwareManager singleton created")
    
    def initialize(self, config_path: Optional[str] = None) -> bool:
        """
        Initialize all hardware interfaces from configuration.
        
        Args:
            config_path: Path to hardware_config.yaml (uses default if None)
        
        Returns:
            bool: True if initialization successful
        """
        try:
            from ..config.settings import get_settings
            from ..daq import WidgetLordsInterface, ModbusInterface
            from ..control.sequence_manager import SequenceManager
            from ..logging.data_logger import DataLogger
            
            # Determine config file path
            if config_path is None:
                config_path = str(Path(__file__).parent.parent / "config" / "hardware_config.yaml")
            
            settings = get_settings(config_path)
            logger.info(f"Loading hardware configuration from: {config_path}")
            
            # Initialize WidgetLords interface
            widgetlords_config = settings.get("hardware", "widgetlords", default={})
            if widgetlords_config.get("enabled", False):
                try:
                    spi_modules = widgetlords_config.get("spi_modules", [])
                    self.widgetlords_interface = WidgetLordsInterface(spi_modules_config=spi_modules)
                    self.widgetlords_interface.connect()
                    logger.info(f"WidgetLords interface initialized with {len(spi_modules)} SPI module(s)")
                except Exception as e:
                    logger.error(f"Failed to initialize WidgetLords interface: {e}")
            
            # Initialize Modbus interface
            modbus_config = settings.get("hardware", "modbus", default={})
            if modbus_config.get("enabled", False):
                try:
                    from ..config.settings import create_modbus_interface_from_settings
                    self.modbus_interface = create_modbus_interface_from_settings(settings)
                    self.modbus_interface.connect()
                    logger.info(f"Modbus interface initialized on {modbus_config.get('port')}")
                except Exception as e:
                    logger.error(f"Failed to initialize Modbus interface: {e}")
            
            # Initialize sequence manager with config limits
            # Build io_device_roles from io_devices config section
            io_device_roles = {}
            io_devices_config = settings.get("io_devices", default={})
            for device in io_devices_config.get("digital_outputs", []):
                device_name = device.get("name")
                device_role = device.get("device_role")
                if device_name and device_role:
                    io_device_roles[device_name] = device_role
            
            self._config_limits = {
                "max_vacuum_bar": settings.get("safety", "max_vacuum_bar", default=1.0),
                "max_force_kg": settings.get("safety", "max_force_kg", default=800.0),
                "max_single_cell_kg": settings.get("safety", "max_single_cell_kg", default=250.0),
                "io_device_roles": io_device_roles,
            }
            logger.info(f"Config limits loaded: max_vacuum={self._config_limits['max_vacuum_bar']} bar, "
                       f"max_force={self._config_limits['max_force_kg']} kg, "
                       f"device_roles={list(io_device_roles.keys())}")
            
            sequences_dir = settings.get("sequences", "directory", default="sequences")
            self.sequence_manager = SequenceManager(sequences_dir, self._config_limits)
            logger.info("Sequence manager initialized")
            
            # Initialize data logger
            self.data_logger = DataLogger(output_dir="data")
            logger.info("Data logger initialized")
            
            # Initialize Google Drive uploader
            self._init_google_drive(settings)
            
            self._connected = True
            
            # Start sensor reading thread
            self._start_sensor_thread()
            
            logger.info("Hardware initialization complete")
            return True
            
        except Exception as e:
            logger.error(f"Hardware initialization failed: {e}", exc_info=True)
            return False
    
    def _init_google_drive(self, settings) -> None:
        """Initialize Google Drive uploader from settings."""
        try:
            from .google_drive import create_uploader_from_config
            
            # Get full config as dict
            google_drive_config = settings.get("google_drive", default={})
            
            if not google_drive_config.get("enabled", False):
                logger.info("Google Drive upload disabled in config")
                return
            
            self.google_drive_uploader = create_uploader_from_config({"google_drive": google_drive_config})
            
            if self.google_drive_uploader:
                # Start the retry loop for failed uploads
                self.google_drive_uploader.start_retry_loop()
                logger.info("Google Drive uploader initialized and retry loop started")
            else:
                logger.warning("Google Drive uploader not configured properly")
                
        except Exception as e:
            logger.error(f"Failed to initialize Google Drive uploader: {e}", exc_info=True)
    
    def shutdown(self) -> None:
        """Shutdown all hardware interfaces gracefully."""
        logger.info("Shutting down hardware manager...")
        
        # Stop sensor thread
        self._stop_sensor_thread()
        
        # Stop Google Drive uploader retry loop
        if self.google_drive_uploader:
            self.google_drive_uploader.stop_retry_loop()
        
        # Stop any running test
        if self._test_running:
            self.stop_test()
        
        # Disconnect interfaces
        if self.widgetlords_interface:
            try:
                # Safe shutdown - turn off pump
                self.widgetlords_interface.set_relay("relay_module", "vacuum_pump", False)
                self.widgetlords_interface.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting WidgetLords: {e}")
        
        if self.modbus_interface:
            try:
                self.modbus_interface.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Modbus: {e}")
        
        self._connected = False
        logger.info("Hardware manager shutdown complete")
    
    def _start_sensor_thread(self) -> None:
        """Start background thread for continuous sensor reading."""
        if self._sensor_thread_running:
            return
        
        self._sensor_thread_running = True
        self._sensor_thread = threading.Thread(target=self._sensor_loop, daemon=True)
        self._sensor_thread.start()
        logger.info("Sensor reading thread started")
    
    def _stop_sensor_thread(self) -> None:
        """Stop the sensor reading thread."""
        self._sensor_thread_running = False
        if self._sensor_thread:
            self._sensor_thread.join(timeout=2.0)
            self._sensor_thread = None
        logger.info("Sensor reading thread stopped")
    
    def _sensor_loop(self) -> None:
        """Background loop for reading sensors at 10Hz."""
        sample_interval = 0.1  # 10Hz
        
        while self._sensor_thread_running:
            try:
                data = self._read_sensors()
                with self._sensor_lock:
                    self._sensor_data = data
            except Exception as e:
                logger.error(f"Sensor read error: {e}")
            
            time.sleep(sample_interval)
    
    def _read_sensors(self) -> Dict[str, Any]:
        """Read all sensors and return combined data."""
        from datetime import datetime
        
        timestamp = time.time()
        datetime_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        data = {
            "timestamp": timestamp,
            "datetime": datetime_str,
        }
        
        # Read WidgetLords (pressure sensor)
        if self.widgetlords_interface and self.widgetlords_interface.is_connected():
            try:
                wl_data = self.widgetlords_interface.read()
                data.update(wl_data)
            except Exception as e:
                logger.error(f"WidgetLords read error: {e}")
                data.update({
                    "pressure_voltage": 0.0,
                    "pressure_mA": 0.0,
                    "pressure_psi": 0.0,
                    "vacuum_bar": 0.0,
                })
        else:
            # Mock data when not connected
            data.update({
                "pressure_voltage": 5.0,
                "pressure_mA": 10.0,
                "pressure_psi": 7.0,
                "vacuum_psi": 7.7,
                "vacuum_bar": 0.0,
            })
        
        # Read Modbus (load cells)
        if self.modbus_interface and self.modbus_interface.is_connected():
            try:
                modbus_data = self.modbus_interface.read()
                data.update(modbus_data)
            except Exception as e:
                logger.error(f"Modbus read error: {e}")
                data.update({
                    "gross_weight_kg": 0.0,
                    "total_force_kg": 0.0,
                    "load_cell_1_kg": 0.0,
                    "load_cell_2_kg": 0.0,
                    "load_cell_3_kg": 0.0,
                    "load_cell_4_kg": 0.0,
                })
        else:
            # Mock data when not connected
            data.update({
                "gross_weight_kg": 0.0,
                "total_force_kg": 0.0,
                "load_cell_1_kg": 0.0,
                "load_cell_2_kg": 0.0,
                "load_cell_3_kg": 0.0,
                "load_cell_4_kg": 0.0,
            })
        
        # Add test state info
        data["test_running"] = self._test_running
        if self._current_sequence:
            data["sequence_name"] = self._current_sequence.name
        
        return data
    
    def get_sensor_data(self) -> Dict[str, Any]:
        """Get the latest sensor data (thread-safe)."""
        with self._sensor_lock:
            return self._sensor_data.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        status = {
            "connected": self._connected,
            "widgetlords_connected": (
                self.widgetlords_interface is not None and 
                self.widgetlords_interface.is_connected()
            ),
            "modbus_connected": (
                self.modbus_interface is not None and 
                self.modbus_interface.is_connected()
            ),
            "test_running": self._test_running,
            "current_sequence": self._current_sequence.name if self._current_sequence else None,
            "google_drive_enabled": self.google_drive_uploader is not None,
        }
        
        # Add pending uploads count if Drive is enabled
        if self.google_drive_uploader:
            pending = self.google_drive_uploader.get_pending_uploads()
            status["google_drive_pending_uploads"] = len(pending)
        
        return status
    
    # === Hardware Control Methods ===
    
    def set_pump(self, state: bool) -> tuple[bool, str]:
        """
        Control the vacuum pump.
        
        Args:
            state: True to turn on, False to turn off
        
        Returns:
            tuple: (success, message)
        """
        if not self.widgetlords_interface or not self.widgetlords_interface.is_connected():
            return False, "Hardware not connected"
        
        try:
            success = self.widgetlords_interface.set_relay("relay_module", "vacuum_pump", state)
            if success:
                return True, f"Pump {'ON' if state else 'OFF'}"
            else:
                return False, "Failed to set pump state (may be blocked by interlock)"
        except Exception as e:
            logger.error(f"Error controlling pump: {e}")
            return False, str(e)
    
    def set_valve(self, valve_name: str, state: bool) -> tuple[bool, str]:
        """
        Control a valve.
        
        VALVE TYPE: Valves are NORMALLY-OPEN (NO):
        - state=True → valve physically CLOSED (relay energized)
        - state=False → valve physically OPEN (relay de-energized)
        
        Args:
            valve_name: Name of valve (vacuum_valve, vent_valve)
            state: True for CLOSED, False for OPEN
        
        Returns:
            tuple: (success, message)
        """
        if not self.widgetlords_interface or not self.widgetlords_interface.is_connected():
            return False, "Hardware not connected"
        
        try:
            success = self.widgetlords_interface.set_relay("relay_module", valve_name, state)
            state_str = "CLOSED" if state else "OPEN"
            if success:
                return True, f"{valve_name}: {state_str}"
            else:
                return False, f"Failed to set {valve_name} (may be blocked by interlock)"
        except Exception as e:
            logger.error(f"Error controlling {valve_name}: {e}")
            return False, str(e)
    
    def tare_load_cells(self) -> tuple[bool, str]:
        """
        Tare the load cells.
        
        Returns:
            tuple: (success, message)
        """
        if not self.modbus_interface or not self.modbus_interface.is_connected():
            return False, "Modbus not connected"
        
        try:
            success = self.modbus_interface.tare_load_cells()
            if success:
                return True, "Tare complete"
            else:
                return False, "Tare failed"
        except Exception as e:
            logger.error(f"Error taring load cells: {e}")
            return False, str(e)
    
    def get_io_states(self) -> Dict[str, bool]:
        """
        Get current IO device states.
        
        Returns physical states (not relay states):
        - For valves (NO type): True = physically OPEN, False = physically CLOSED
          (inverted from relay state since relay ON = valve closed)
        - For pump: True = ON, False = OFF (direct relay state)
        """
        try:
            from ..daq.relay_state_manager import relay_state_manager
            all_states = relay_state_manager.get_all_states()
            
            # Valves that need inversion (NO type: relay ON = valve CLOSED)
            no_valves = {"vacuum_valve", "vent_valve"}
            
            # Flatten to simple dict with valve inversion
            result = {}
            for module_name, channels in all_states.items():
                for channel_name, relay_state in channels.items():
                    if channel_name in no_valves:
                        # Invert for NO valves: relay ON means valve CLOSED
                        # Return physical state: True = OPEN, False = CLOSED
                        result[channel_name] = not relay_state
                    else:
                        # Pump and other devices: relay state = device state
                        result[channel_name] = relay_state
            return result
        except Exception as e:
            logger.error(f"Error getting IO states: {e}")
            return {}
    
    # === Test Execution Methods ===
    
    def get_sequences(self) -> List[Dict[str, Any]]:
        """Get list of available test sequences."""
        if not self.sequence_manager:
            return []
        
        sequences = []
        for filename in self.sequence_manager.list_sequences():
            try:
                seq = self.sequence_manager.load_sequence(filename)
                if seq:
                    # Use filename as the identifier (for loading), but show display name
                    sequences.append({
                        "name": filename,  # Use filename for API lookups
                        "display_name": seq.name,  # Human-readable name from YAML
                        "description": seq.description,
                        "stages": len(seq.stages),
                        "cycles": seq.cycles,
                    })
            except Exception as e:
                logger.error(f"Error loading sequence {filename}: {e}")
        
        return sequences
    
    def get_sequence(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific sequence by name."""
        if not self.sequence_manager:
            return None
        
        try:
            seq = self.sequence_manager.load_sequence(name)
            if seq:
                return seq.to_dict()
        except Exception as e:
            logger.error(f"Error loading sequence {name}: {e}")
        
        return None
    
    def start_test(self, sequence_name: str, metadata: Optional[Dict[str, Any]] = None) -> tuple[bool, str]:
        """
        Start a test with the specified sequence.
        
        Args:
            sequence_name: Name of sequence to run
            metadata: Optional test metadata
        
        Returns:
            tuple: (success, message)
        """
        if self._test_running:
            return False, "Test already running"
        
        if not self.sequence_manager:
            return False, "Sequence manager not initialized"
        
        # Load sequence
        sequence = self.sequence_manager.load_sequence(sequence_name)
        if not sequence:
            return False, f"Sequence '{sequence_name}' not found"
        
        # Validate sequence with config limits for safety checks and device role detection
        is_valid, errors, warnings = sequence.validate(self._config_limits)
        if not is_valid:
            return False, f"Invalid sequence: {', '.join(errors)}"
        
        # Log warnings if any (but don't block test start)
        for warning in warnings:
            logger.warning(f"Sequence validation warning: {warning}")
        
        self._current_sequence = sequence
        
        # Generate CSV path using test_id from metadata if available
        from datetime import datetime
        import re
        
        test_id = None
        if metadata:
            test_id = metadata.get('test_id')
        
        if test_id:
            # Sanitize test_id for use as filename (remove unsafe characters)
            safe_test_id = re.sub(r'[^\w\-]', '_', str(test_id))
            csv_path = f"data/{safe_test_id}.csv"
            logger.info(f"Using test_id for filename: {safe_test_id}")
        else:
            # Fallback to generic timestamp-based naming
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_path = f"data/test_{timestamp}.csv"
            logger.info(f"No test_id in metadata, using timestamp filename: test_{timestamp}")
        
        self._current_csv_path = csv_path  # Store for Google Drive upload
        
        # Create test controller
        from ..control.test_controller import TestController
        self.test_controller = TestController(
            widgetlords_interface=self.widgetlords_interface,
            modbus_interface=self.modbus_interface,
            data_logger=self.data_logger,
            csv_path=csv_path,
            test_metadata=metadata or {},
        )
        
        # Set callbacks
        self.test_controller.status_callback = self._on_status_update
        self.test_controller.stage_callback = self._on_stage_change
        self.test_controller.io_callback = self._on_io_change
        self.test_controller.progress_callback = self._on_progress_update
        self.test_controller.completion_callback = self._on_stage_complete
        
        # Load sequence into controller
        if not self.test_controller.load_sequence(sequence):
            return False, "Failed to load sequence into controller"
        
        # Start test in background thread
        self._test_running = True
        self._test_thread = threading.Thread(target=self._run_test, daemon=True)
        self._test_thread.start()
        
        logger.info(f"Test started with sequence: {sequence_name}")
        return True, f"Test started: {sequence_name}"
    
    def _run_test(self) -> None:
        """Background thread for running test."""
        csv_path = self._current_csv_path  # Capture before it's cleared
        try:
            success = self.test_controller.run_test()
            logger.info(f"Test completed: {'success' if success else 'failed'}")
            
            # Upload to Google Drive if enabled
            if csv_path and self.google_drive_uploader:
                self._upload_test_data(csv_path)
                
        except Exception as e:
            logger.error(f"Test execution error: {e}", exc_info=True)
        finally:
            self._test_running = False
            self._current_sequence = None
            self._current_csv_path = None
            # Notify completion callbacks
            for callback in self._completion_callbacks:
                try:
                    callback()
                except Exception as e:
                    logger.error(f"Completion callback error: {e}")
    
    def stop_test(self) -> tuple[bool, str]:
        """Stop the running test."""
        if not self._test_running:
            return False, "No test running"
        
        try:
            if self.test_controller:
                self.test_controller.stop_test()
            
            # Safe shutdown - turn off pump
            if self.widgetlords_interface and self.widgetlords_interface.is_connected():
                self.widgetlords_interface.set_relay("relay_module", "vacuum_pump", False)
            
            self._test_running = False
            logger.info("Test stopped by user")
            return True, "Test stopped"
        except Exception as e:
            logger.error(f"Error stopping test: {e}")
            return False, str(e)
    
    def get_test_status(self) -> Dict[str, Any]:
        """Get current test execution status."""
        status = {
            "running": self._test_running,
            "sequence": self._current_sequence.name if self._current_sequence else None,
        }
        
        if self.test_controller and self._test_running:
            status.update({
                "state": self.test_controller.state.value if self.test_controller.state else "idle",
                "stage_index": self.test_controller.current_stage_index,
                "total_stages": len(self._current_sequence.stages) if self._current_sequence else 0,
            })
        
        return status
    
    # === Callback Methods ===
    
    def add_status_callback(self, callback: Callable[[str], None]) -> None:
        """Add callback for status updates."""
        self._status_callbacks.append(callback)
    
    def add_stage_callback(self, callback: Callable) -> None:
        """Add callback for stage changes."""
        self._stage_callbacks.append(callback)
    
    def add_completion_callback(self, callback: Callable) -> None:
        """Add callback for test completion."""
        self._completion_callbacks.append(callback)
    
    def add_io_callback(self, callback: Callable[[str, bool], None]) -> None:
        """Add callback for IO state changes."""
        self._io_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """Add callback for progress updates."""
        self._progress_callbacks.append(callback)
    
    def _on_status_update(self, status: str) -> None:
        """Handle status update from test controller."""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
    
    def _on_stage_change(self, stage_index: int, stages_per_cycle: int, 
                         current_cycle: int, total_cycles: int, stage) -> None:
        """Handle stage change from test controller."""
        for callback in self._stage_callbacks:
            try:
                callback(stage_index, stages_per_cycle, current_cycle, total_cycles, stage)
            except Exception as e:
                logger.error(f"Stage callback error: {e}")
    
    def _on_io_change(self, device_name: str, state: bool) -> None:
        """Handle IO state change from test controller."""
        for callback in self._io_callbacks:
            try:
                callback(device_name, state)
            except Exception as e:
                logger.error(f"IO callback error: {e}")
    
    def _on_progress_update(self, progress: float, status: str) -> None:
        """Handle progress update from test controller."""
        for callback in self._progress_callbacks:
            try:
                callback(progress, status)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")
    
    def _on_stage_complete(self, stage_index: int, reason: str) -> None:
        """Handle stage completion from test controller."""
        logger.info(f"Stage {stage_index} completed: {reason}")
    
    # === Google Drive Upload Methods ===
    
    def _upload_test_data(self, csv_path: str) -> None:
        """Upload test data to Google Drive (called after test completion)."""
        if not self.google_drive_uploader:
            return
        
        try:
            logger.info(f"Uploading test data to Google Drive: {csv_path}")
            success, message = self.google_drive_uploader.upload_test_data(csv_path)
            if success:
                logger.info(f"Google Drive upload successful: {message}")
            else:
                logger.warning(f"Google Drive upload queued for retry: {message}")
        except Exception as e:
            logger.error(f"Google Drive upload error: {e}", exc_info=True)
    
    def get_drive_status(self) -> Dict[str, Any]:
        """Get Google Drive uploader status."""
        if not self.google_drive_uploader:
            return {
                "enabled": False,
                "message": "Google Drive upload not configured"
            }
        
        return self.google_drive_uploader.get_status()
    
    def get_pending_uploads(self) -> List[Dict[str, Any]]:
        """Get list of pending Google Drive uploads."""
        if not self.google_drive_uploader:
            return []
        
        return self.google_drive_uploader.get_pending_uploads()
    
    def force_drive_retry(self) -> tuple[bool, str]:
        """Force immediate retry of pending Google Drive uploads."""
        if not self.google_drive_uploader:
            return False, "Google Drive upload not configured"
        
        return self.google_drive_uploader.force_retry()
    
    def manual_drive_upload(self, filename: str) -> tuple[bool, str]:
        """Manually upload a file to Google Drive."""
        if not self.google_drive_uploader:
            return False, "Google Drive upload not configured"
        
        return self.google_drive_uploader.manual_upload(filename)
    
    def set_drive_callbacks(
        self,
        on_success: Optional[Callable[[str, str], None]] = None,
        on_failure: Optional[Callable[[str, str, bool], None]] = None
    ) -> None:
        """Set callbacks for Google Drive upload events."""
        if not self.google_drive_uploader:
            return
        
        if on_success:
            self.google_drive_uploader.add_success_callback(on_success)
        if on_failure:
            self.google_drive_uploader.add_failure_callback(on_failure)


# Global instance accessor
def get_hardware_manager() -> HardwareManager:
    """Get the singleton HardwareManager instance."""
    return HardwareManager()


