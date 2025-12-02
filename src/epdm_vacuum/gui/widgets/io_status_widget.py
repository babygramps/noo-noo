"""
IO Status Widget - Real-time IO Device State Display

Shows the current state of all IO devices configured in hardware_config.yaml:
- Digital outputs (relays, valves)
- Analog inputs (pressure sensors, etc. from SPI modules)
- Analog outputs (if applicable)
- Real-time state updates with color-coded indicators
- Grouped by device type
"""

from typing import Optional, Dict, Any, Union
import logging
from pathlib import Path

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QGridLayout,
    QGroupBox,
    QProgressBar,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class IOStatusWidget(QWidget):
    """
    Widget displaying real-time status of all IO devices.
    
    Shows all configured IO devices with visual indicators for:
    - OPEN/ON (green)
    - CLOSED/OFF (red)
    - NOT SET (gray)
    - Analog values with progress bars
    """
    
    def __init__(self, parent=None):
        """Initialize the IO status widget."""
        super().__init__(parent)
        
        self.io_devices: Dict[str, Dict[str, Any]] = {}
        self.device_states: Dict[str, Optional[bool]] = {}  # device_name -> state (True=OPEN, False=CLOSED, None=NOT SET)
        self.device_widgets: Dict[str, tuple] = {}  # device_name -> (indicator_label, state_label) or (indicator, value_label, progress_bar) for analog inputs
        self.analog_input_values: Dict[str, float] = {}  # device_name -> current value
        
        self.init_ui()
        self.load_io_devices()
        
        logger.info("IOStatusWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("IO Device Status")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        # Container for device groups
        self.devices_container = QVBoxLayout()
        self.devices_container.setSpacing(8)
        layout.addLayout(self.devices_container)
        
        layout.addStretch()
    
    def load_io_devices(self) -> None:
        """Load IO device configurations from hardware_config.yaml."""
        try:
            from ...config.settings import get_settings
            
            config_file = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
            settings = get_settings(str(config_file))
            
            # Load digital outputs from io_devices section
            digital_outputs = settings.get("io_devices", "digital_outputs", default=[])
            if isinstance(digital_outputs, list):
                for device in digital_outputs:
                    if isinstance(device, dict) and "name" in device:
                        device_name = device["name"]
                        self.io_devices[device_name] = {
                            "type": "Digital",
                            "description": device.get("description", ""),
                            "channel": device.get("channel", 0),
                            "default_state": device.get("default_state", False)
                        }
                        # Initialize state as NOT SET
                        self.device_states[device_name] = None
            
            # Load analog outputs from io_devices section (if any)
            analog_outputs = settings.get("io_devices", "analog_outputs", default=[])
            if isinstance(analog_outputs, list):
                for device in analog_outputs:
                    if isinstance(device, dict) and "name" in device:
                        device_name = device["name"]
                        self.io_devices[device_name] = {
                            "type": "AnalogOutput",
                            "description": device.get("description", ""),
                            "channel": device.get("channel", 0),
                            "min_value": device.get("min_value", 0.0),
                            "max_value": device.get("max_value", 10.0)
                        }
                        # Analog devices don't have boolean state
                        self.device_states[device_name] = None
            
            # Load SPI analog inputs from hardware.widgetlords.spi_modules
            # These are sensors like pressure transmitters
            spi_modules = settings.get("hardware", "widgetlords", "spi_modules", default=[])
            if isinstance(spi_modules, list):
                for module in spi_modules:
                    if isinstance(module, dict):
                        module_type = module.get("module_type", "")
                        module_name = module.get("name", "")
                        
                        # Only process analog input modules (8AI)
                        if module_type == "PI-SPI-DIN-8AI":
                            channels = module.get("channels", [])
                            for ch in channels:
                                if isinstance(ch, dict) and ch.get("enabled", False):
                                    ch_name = ch.get("name", f"ch{ch.get('channel', 0)}")
                                    self.io_devices[ch_name] = {
                                        "type": "AnalogInput",
                                        "module_name": module_name,
                                        "description": ch.get("description", ""),
                                        "channel": ch.get("channel", 0),
                                        "input_type": ch.get("input_type", "4-20mA"),
                                        "low_output": ch.get("low_output", 0.0),
                                        "high_output": ch.get("high_output", 100.0),
                                        "units": ch.get("units", ""),
                                    }
                                    # Initialize value as None
                                    self.analog_input_values[ch_name] = None
                                    logger.info(f"Loaded SPI analog input: {ch_name} ({ch.get('description', '')})")
            
            logger.info(f"Loaded {len(self.io_devices)} IO devices from config")
            
            # Create UI for loaded devices
            self._create_device_ui()
            
        except Exception as e:
            logger.error(f"Error loading IO devices: {e}", exc_info=True)
            # Create a message label indicating error
            error_label = QLabel("Error loading IO device configuration")
            error_label.setStyleSheet("color: #F44336; font-style: italic;")
            self.devices_container.addWidget(error_label)
    
    def _create_device_ui(self) -> None:
        """Create UI elements for all loaded IO devices."""
        if not self.io_devices:
            no_devices_label = QLabel("No IO devices configured")
            no_devices_label.setStyleSheet("color: #999; font-style: italic;")
            self.devices_container.addWidget(no_devices_label)
            return
        
        # Group devices by type
        digital_devices = {k: v for k, v in self.io_devices.items() if v["type"] == "Digital"}
        analog_input_devices = {k: v for k, v in self.io_devices.items() if v["type"] == "AnalogInput"}
        analog_output_devices = {k: v for k, v in self.io_devices.items() if v["type"] == "AnalogOutput"}
        
        # Create Analog Inputs group (sensors like pressure transmitters) - show first as they're most important
        if analog_input_devices:
            analog_input_group = self._create_analog_input_group("Analog Inputs (Sensors)", analog_input_devices)
            self.devices_container.addWidget(analog_input_group)
        
        # Create Digital Outputs group
        if digital_devices:
            digital_group = self._create_device_group("Digital Outputs", digital_devices)
            self.devices_container.addWidget(digital_group)
        
        # Create Analog Outputs group
        if analog_output_devices:
            analog_group = self._create_device_group("Analog Outputs", analog_output_devices)
            self.devices_container.addWidget(analog_group)
    
    def _create_device_group(self, title: str, devices: Dict[str, Dict[str, Any]]) -> QGroupBox:
        """
        Create a group box for a set of devices.
        
        Args:
            title: Group title
            devices: Dictionary of devices to display
        
        Returns:
            QGroupBox containing device status displays
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(4)
        
        for device_name, device_info in sorted(devices.items()):
            device_row = self._create_device_row(device_name, device_info)
            layout.addWidget(device_row)
        
        group.setLayout(layout)
        return group
    
    def _create_analog_input_group(self, title: str, devices: Dict[str, Dict[str, Any]]) -> QGroupBox:
        """
        Create a group box for analog input sensors (like pressure transmitters).
        
        Args:
            title: Group title
            devices: Dictionary of analog input devices to display
        
        Returns:
            QGroupBox containing analog input displays with progress bars
        """
        group = QGroupBox(title)
        group.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 1px solid #3498db;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #f8fbff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2980b9;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        for device_name, device_info in sorted(devices.items()):
            device_row = self._create_analog_input_row(device_name, device_info)
            layout.addWidget(device_row)
        
        group.setLayout(layout)
        return group
    
    def _create_analog_input_row(self, device_name: str, device_info: Dict[str, Any]) -> QFrame:
        """
        Create a row displaying an analog input sensor with value and progress bar.
        
        Args:
            device_name: Name of the device
            device_info: Device configuration info
        
        Returns:
            QFrame containing analog input display
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                padding: 6px;
            }
        """)
        
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(4)
        
        # Top row: Name, value, and units
        top_layout = QHBoxLayout()
        top_layout.setSpacing(8)
        
        # Status indicator (colored circle/LED)
        indicator = QLabel("●")
        indicator.setFont(QFont("Arial", 14))
        indicator.setFixedWidth(20)
        indicator.setAlignment(Qt.AlignCenter)
        indicator.setStyleSheet("color: #9E9E9E;")  # Gray = no data
        top_layout.addWidget(indicator)
        
        # Device name
        name_label = QLabel(device_name)
        name_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #2c3e50;")
        top_layout.addWidget(name_label)
        
        top_layout.addStretch()
        
        # Value label (large, prominent)
        units = device_info.get("units", "")
        value_label = QLabel("-- " + units)
        value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3498db;")
        value_label.setMinimumWidth(100)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        top_layout.addWidget(value_label)
        
        layout.addLayout(top_layout)
        
        # Progress bar showing value as percentage of range
        low_out = device_info.get("low_output", 0.0)
        high_out = device_info.get("high_output", 100.0)
        
        progress_bar = QProgressBar()
        progress_bar.setMinimum(0)
        progress_bar.setMaximum(100)
        progress_bar.setValue(0)
        progress_bar.setTextVisible(False)
        progress_bar.setMaximumHeight(8)
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: #ecf0f1;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        layout.addWidget(progress_bar)
        
        # Description row (if available)
        desc = device_info.get("description", "")
        if desc:
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("font-size: 9pt; color: #7f8c8d; font-style: italic;")
            layout.addWidget(desc_label)
        
        # Store references for updates (indicator, value_label, progress_bar, device_info)
        self.device_widgets[device_name] = (indicator, value_label, progress_bar, device_info)
        
        return frame
    
    def _create_device_row(self, device_name: str, device_info: Dict[str, Any]) -> QFrame:
        """
        Create a row displaying a single device.
        
        Args:
            device_name: Name of the device
            device_info: Device configuration info
        
        Returns:
            QFrame containing device display
        """
        frame = QFrame()
        frame.setFrameShape(QFrame.StyledPanel)
        frame.setStyleSheet("""
            QFrame {
                background-color: #fafafa;
                border: 1px solid #e0e0e0;
                border-radius: 3px;
                padding: 4px;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Status indicator (colored circle/LED)
        indicator = QLabel("●")
        indicator.setFont(QFont("Arial", 16))
        indicator.setFixedWidth(24)
        indicator.setAlignment(Qt.AlignCenter)
        self._update_indicator_color(indicator, None)  # Start as NOT SET
        layout.addWidget(indicator)
        
        # Device name
        name_label = QLabel(device_name)
        name_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #333;")
        name_label.setMinimumWidth(150)
        layout.addWidget(name_label)
        
        # State label
        state_label = QLabel("NOT SET")
        state_label.setStyleSheet("font-size: 10pt; color: #666;")
        state_label.setMinimumWidth(80)
        layout.addWidget(state_label)
        
        # Description
        if device_info.get("description"):
            desc_label = QLabel(device_info["description"])
            desc_label.setStyleSheet("font-size: 9pt; color: #999; font-style: italic;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label, stretch=1)
        else:
            layout.addStretch()
        
        # Store references for updates
        self.device_widgets[device_name] = (indicator, state_label)
        
        return frame
    
    def _update_indicator_color(self, indicator: QLabel, state: Optional[bool]) -> None:
        """
        Update indicator color based on state.
        
        Args:
            indicator: QLabel showing the colored indicator
            state: True=OPEN/ON, False=CLOSED/OFF, None=NOT SET
        """
        if state is True:
            # OPEN/ON - Green
            indicator.setStyleSheet("color: #4CAF50;")
        elif state is False:
            # CLOSED/OFF - Red
            indicator.setStyleSheet("color: #F44336;")
        else:
            # NOT SET - Gray
            indicator.setStyleSheet("color: #9E9E9E;")
    
    def set_device_state(self, device_name: str, state: bool) -> None:
        """
        Update the state of a specific device.
        
        Args:
            device_name: Name of the device to update
            state: True for OPEN/ON, False for CLOSED/OFF
        """
        if device_name not in self.device_widgets:
            logger.warning(f"Device '{device_name}' not found in IO status widget")
            return
        
        self.device_states[device_name] = state
        
        indicator, state_label = self.device_widgets[device_name]
        
        # Update indicator color
        self._update_indicator_color(indicator, state)
        
        # Update state text
        device_info = self.io_devices.get(device_name, {})
        if device_info.get("type") == "Digital":
            state_text = "OPEN" if state else "CLOSED"
        else:
            state_text = "ON" if state else "OFF"
        
        state_label.setText(state_text)
        
        # Update state label color
        if state:
            state_label.setStyleSheet("font-size: 10pt; color: #4CAF50; font-weight: bold;")
        else:
            state_label.setStyleSheet("font-size: 10pt; color: #F44336; font-weight: bold;")
        
        logger.debug(f"Updated device '{device_name}' state to: {state_text}")
    
    def set_device_analog_value(self, device_name: str, value: float) -> None:
        """
        Update the analog value of a device (for analog outputs).
        
        Args:
            device_name: Name of the device to update
            value: Analog value (e.g., voltage)
        """
        if device_name not in self.device_widgets:
            logger.warning(f"Device '{device_name}' not found in IO status widget")
            return
        
        widget_tuple = self.device_widgets[device_name]
        
        # Check if this is an analog input (has 4 elements) or analog output (has 2 elements)
        if len(widget_tuple) == 4:
            # Analog input - use the dedicated method
            self.update_analog_input_value(device_name, value)
            return
        
        indicator, state_label = widget_tuple
        
        # For analog devices, show the value
        device_info = self.io_devices.get(device_name, {})
        min_val = device_info.get("min_value", 0.0)
        max_val = device_info.get("max_value", 10.0)
        
        # Update indicator color based on value (green if > 0, gray if 0)
        state = value > (min_val + 0.01)
        self._update_indicator_color(indicator, state if state else None)
        
        # Update state text
        state_label.setText(f"{value:.2f} V")
        state_label.setStyleSheet("font-size: 10pt; color: #2196F3; font-weight: bold;")
        
        logger.debug(f"Updated device '{device_name}' analog value to: {value:.2f}")
    
    def update_analog_input_value(self, device_name: str, value: float) -> None:
        """
        Update the value of an analog input sensor (like pressure transmitter).
        
        Args:
            device_name: Name of the analog input device
            value: Scaled value in engineering units (e.g., PSI)
        """
        if device_name not in self.device_widgets:
            logger.debug(f"Analog input '{device_name}' not found in IO status widget")
            return
        
        widget_tuple = self.device_widgets[device_name]
        
        # Analog inputs have 4 elements: (indicator, value_label, progress_bar, device_info)
        if len(widget_tuple) != 4:
            logger.warning(f"Device '{device_name}' is not an analog input")
            return
        
        indicator, value_label, progress_bar, device_info = widget_tuple
        
        # Store value
        self.analog_input_values[device_name] = value
        
        # Get range for progress bar
        low_out = device_info.get("low_output", 0.0)
        high_out = device_info.get("high_output", 100.0)
        units = device_info.get("units", "")
        
        # Update value label
        value_label.setText(f"{value:.2f} {units}")
        
        # Calculate percentage for progress bar
        if abs(high_out - low_out) > 0.001:
            pct = int(100 * (value - low_out) / (high_out - low_out))
            pct = max(0, min(100, pct))  # Clamp to 0-100
        else:
            pct = 0
        
        progress_bar.setValue(pct)
        
        # Update indicator color based on value
        # Green if in normal range (>10% of range), yellow if low, red if very low or high
        if pct < 5:
            indicator.setStyleSheet("color: #e74c3c;")  # Red - very low
            value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #e74c3c;")
        elif pct < 20:
            indicator.setStyleSheet("color: #f39c12;")  # Yellow/orange - low
            value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #f39c12;")
        elif pct > 95:
            indicator.setStyleSheet("color: #e74c3c;")  # Red - very high
            value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #e74c3c;")
        else:
            indicator.setStyleSheet("color: #27ae60;")  # Green - normal
            value_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #3498db;")
        
        logger.debug(f"Updated analog input '{device_name}': {value:.2f} {units} ({pct}%)")
    
    def update_from_daq_data(self, data: Dict[str, Any]) -> None:
        """
        Update all analog input values from DAQ data dictionary.
        
        This method extracts analog input values from the data dict
        and updates the corresponding displays.
        
        Args:
            data: Data dictionary from DAQ thread containing sensor readings
        """
        # Update analog inputs from the nested structure
        analog_inputs = data.get("analog_inputs", {})
        for module_name, channels in analog_inputs.items():
            if isinstance(channels, dict):
                for ch_name, value in channels.items():
                    if ch_name in self.analog_input_values:
                        self.update_analog_input_value(ch_name, value)
        
        # Also check for legacy format keys (pressure_psi, vacuum_bar, etc.)
        if "pressure_psi" in data and "pressure_sensor" in self.analog_input_values:
            self.update_analog_input_value("pressure_sensor", data["pressure_psi"])
    
    def reset_device_state(self, device_name: str) -> None:
        """
        Reset a device to NOT SET state.
        
        Args:
            device_name: Name of the device to reset
        """
        if device_name not in self.device_widgets:
            return
        
        self.device_states[device_name] = None
        
        indicator, state_label = self.device_widgets[device_name]
        
        # Update to NOT SET
        self._update_indicator_color(indicator, None)
        state_label.setText("NOT SET")
        state_label.setStyleSheet("font-size: 10pt; color: #666;")
        
        logger.debug(f"Reset device '{device_name}' to NOT SET")
    
    def reset_all(self) -> None:
        """Reset all devices to NOT SET state."""
        for device_name in self.device_widgets.keys():
            self.reset_device_state(device_name)
        
        logger.info("Reset all IO device states")
    
    def get_device_state(self, device_name: str) -> Optional[bool]:
        """
        Get the current state of a device.
        
        Args:
            device_name: Name of the device
        
        Returns:
            True if OPEN/ON, False if CLOSED/OFF, None if NOT SET
        """
        return self.device_states.get(device_name)
    
    def get_all_states(self) -> Dict[str, Optional[bool]]:
        """
        Get all device states.
        
        Returns:
            Dictionary mapping device names to states
        """
        return self.device_states.copy()

