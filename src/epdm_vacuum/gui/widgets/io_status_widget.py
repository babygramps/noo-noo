"""
IO Status Widget - Real-time IO Device State Display

Shows the current state of all IO devices configured in hardware_config.yaml:
- Digital outputs (relays, valves)
- Analog outputs (if applicable)
- Real-time state updates with color-coded indicators
- Grouped by device type
"""

from typing import Optional, Dict, Any
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
    """
    
    def __init__(self, parent=None):
        """Initialize the IO status widget."""
        super().__init__(parent)
        
        self.io_devices: Dict[str, Dict[str, Any]] = {}
        self.device_states: Dict[str, Optional[bool]] = {}  # device_name -> state (True=OPEN, False=CLOSED, None=NOT SET)
        self.device_widgets: Dict[str, tuple] = {}  # device_name -> (indicator_label, state_label)
        
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
            
            # Load digital outputs
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
            
            # Load analog outputs (if any)
            analog_outputs = settings.get("io_devices", "analog_outputs", default=[])
            if isinstance(analog_outputs, list):
                for device in analog_outputs:
                    if isinstance(device, dict) and "name" in device:
                        device_name = device["name"]
                        self.io_devices[device_name] = {
                            "type": "Analog",
                            "description": device.get("description", ""),
                            "channel": device.get("channel", 0),
                            "min_value": device.get("min_value", 0.0),
                            "max_value": device.get("max_value", 10.0)
                        }
                        # Analog devices don't have boolean state
                        self.device_states[device_name] = None
            
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
        analog_devices = {k: v for k, v in self.io_devices.items() if v["type"] == "Analog"}
        
        # Create Digital Outputs group
        if digital_devices:
            digital_group = self._create_device_group("Digital Outputs", digital_devices)
            self.devices_container.addWidget(digital_group)
        
        # Create Analog Outputs group
        if analog_devices:
            analog_group = self._create_device_group("Analog Outputs", analog_devices)
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
        Update the analog value of a device.
        
        Args:
            device_name: Name of the device to update
            value: Analog value (e.g., voltage)
        """
        if device_name not in self.device_widgets:
            logger.warning(f"Device '{device_name}' not found in IO status widget")
            return
        
        indicator, state_label = self.device_widgets[device_name]
        
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

