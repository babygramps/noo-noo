"""
Control Panel Widget - Test Control Interface

Provides buttons and controls for:
- Starting/stopping tests
- Manual pump and valve control
- Tare operations
- Data saving

Device names are loaded from hardware_config.yaml using device_role
to ensure compatibility across different hardware configurations.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QGroupBox,
    QGridLayout,
)
from PyQt5.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)


def _load_device_config_from_yaml() -> Dict[str, Dict]:
    """
    Load device configuration from hardware config.
    
    Returns:
        Dict mapping device_role to config dict containing:
        - name: actual channel name
        - normally_open: bool (True for NO valves, False for NC)
        
        e.g.: {"vacuum_valve": {"name": "vacuum", "normally_open": True}}
    """
    role_to_config = {}
    
    try:
        import yaml
        config_file = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f)
            
            # Check SPI modules for relay channels
            spi_modules = config.get("hardware", {}).get("widgetlords", {}).get("spi_modules", [])
            for module in spi_modules:
                if module.get("module_type") == "PI-SPI-DIN-4KO":
                    for ch in module.get("channels", []):
                        ch_name = ch.get("name", "")
                        normally_open = ch.get("normally_open", False)
                        
                        if ch_name:
                            ch_config = {"name": ch_name, "normally_open": normally_open}
                            # Map common names to roles
                            if "pump" in ch_name.lower():
                                role_to_config["vacuum_pump"] = ch_config
                            elif "vent" in ch_name.lower():
                                role_to_config["vent_valve"] = ch_config
                            elif "vacuum" in ch_name.lower() and "pump" not in ch_name.lower():
                                role_to_config["vacuum_valve"] = ch_config
            
            # Also check io_devices section for explicit roles
            io_devices = config.get("io_devices", {})
            for device in io_devices.get("digital_outputs", []):
                device_name = device.get("name", "")
                device_role = device.get("device_role", "")
                normally_open = device.get("normally_open", False)
                if device_role and device_name:
                    # io_devices takes precedence
                    role_to_config[device_role] = {"name": device_name, "normally_open": normally_open}
            
            logger.info(f"Loaded device config: {role_to_config}")
        else:
            logger.warning(f"Config file not found: {config_file}")
            
    except Exception as e:
        logger.error(f"Failed to load device config: {e}")
    
    # Fallback defaults if nothing found
    if "vacuum_pump" not in role_to_config:
        role_to_config["vacuum_pump"] = {"name": "vacuum_pump", "normally_open": False}
    if "vacuum_valve" not in role_to_config:
        role_to_config["vacuum_valve"] = {"name": "vacuum_valve", "normally_open": False}
    if "vent_valve" not in role_to_config:
        role_to_config["vent_valve"] = {"name": "vent_valve", "normally_open": False}
    
    return role_to_config


class ControlPanel(QWidget):
    """
    Widget for test control operations.
    
    Emits signals for user actions:
    - Start/stop test
    - Pump and valve control
    - Tare load cells
    - Save data
    
    Device names are loaded dynamically from hardware_config.yaml
    to support different naming conventions across deployments.
    """
    
    # Signals
    start_test_requested = pyqtSignal()
    stop_test_requested = pyqtSignal()
    pump_control_requested = pyqtSignal(bool)  # True = ON, False = OFF
    valve_control_requested = pyqtSignal(str, bool)  # (valve_name, state) - True = OPEN, False = CLOSED
    tare_requested = pyqtSignal()
    save_data_requested = pyqtSignal()
    
    def __init__(self):
        """Initialize the control panel."""
        super().__init__()
        
        # Load device config from hardware_config.yaml
        # Contains: role -> {"name": actual_channel_name, "normally_open": bool}
        self.device_config = _load_device_config_from_yaml()
        
        # Extract just the names for backward compatibility
        self.device_names = {role: cfg["name"] for role, cfg in self.device_config.items()}
        logger.info(f"ControlPanel using device config: {self.device_config}")
        
        self.test_running = False
        self.pump_on = False
        
        # Use actual channel names for valve states
        self.valve_states = {
            self.device_names["vent_valve"]: False,
            self.device_names["vacuum_valve"]: False,
        }
        
        # Store role -> button mapping for updates
        self.valve_buttons: Dict[str, QPushButton] = {}
        
        self.init_ui()
        self._sync_from_relay_manager()
        logger.info("ControlPanel initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        
        # Test control group
        test_group = self.create_test_controls()
        layout.addWidget(test_group)
        
        # Pump & Valve control group
        io_group = self.create_io_controls()
        layout.addWidget(io_group)
        
        # Utility controls group
        utility_group = self.create_utility_controls()
        layout.addWidget(utility_group)
    
    def create_test_controls(self) -> QGroupBox:
        """
        Create test control buttons group.
        
        Returns:
            QGroupBox: Test controls group
        """
        group = QGroupBox("Test Control")
        layout = QVBoxLayout()
        
        # Start test button
        self.start_btn = QPushButton("Start Test")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet("QPushButton { font-size: 14pt; font-weight: bold; }")
        self.start_btn.clicked.connect(self.on_start_test)
        layout.addWidget(self.start_btn)
        
        # Stop test button
        self.stop_btn = QPushButton("Stop Test")
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet("QPushButton { font-size: 14pt; font-weight: bold; }")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_test)
        layout.addWidget(self.stop_btn)
        
        group.setLayout(layout)
        return group
    
    def create_io_controls(self) -> QGroupBox:
        """
        Create pump and valve control buttons group.
        
        Device names are loaded from hardware_config.yaml to support
        different naming conventions across deployments.
        
        Returns:
            QGroupBox: I/O controls group
        """
        group = QGroupBox("Pump & Valves")
        layout = QGridLayout()
        layout.setSpacing(8)
        
        # Get actual channel names and NO/NC config
        pump_cfg = self.device_config.get("vacuum_pump", {"name": "vacuum_pump", "normally_open": False})
        vacuum_valve_cfg = self.device_config.get("vacuum_valve", {"name": "vacuum_valve", "normally_open": False})
        vent_valve_cfg = self.device_config.get("vent_valve", {"name": "vent_valve", "normally_open": False})
        
        pump_name = pump_cfg["name"]
        vacuum_valve_name = vacuum_valve_cfg["name"]
        vent_valve_name = vent_valve_cfg["name"]
        
        # NO/NC descriptions for tooltips
        vacuum_valve_type = "Normally Open (NO)" if vacuum_valve_cfg["normally_open"] else "Normally Closed (NC)"
        vent_valve_type = "Normally Open (NO)" if vent_valve_cfg["normally_open"] else "Normally Closed (NC)"
        
        # Pump toggle button (row 0)
        self.pump_btn = QPushButton("Pump OFF")
        self.pump_btn.setMinimumHeight(45)
        self.pump_btn.setCheckable(True)
        self.pump_btn.setStyleSheet("""
            QPushButton { 
                font-size: 12pt; 
                font-weight: bold;
                background-color: #e0e0e0;
                border: 2px solid #999;
                border-radius: 4px;
            }
            QPushButton:checked { 
                background-color: #4CAF50;
                color: white;
                border-color: #388E3C;
            }
            QPushButton:hover {
                border-color: #666;
            }
        """)
        self.pump_btn.setToolTip(f"Toggle vacuum pump ON/OFF\n(Channel: {pump_name})")
        self.pump_btn.clicked.connect(self.on_pump_toggle)
        layout.addWidget(self.pump_btn, 0, 0, 1, 2)
        
        # Vacuum Valve toggle (row 1, left) - connects pump to chamber
        self.vacuum_valve_btn = QPushButton("Vacuum Valve\nCLOSED")
        self.vacuum_valve_btn.setMinimumHeight(45)
        self.vacuum_valve_btn.setCheckable(True)
        self.vacuum_valve_btn.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                font-weight: bold;
                background-color: #ffcdd2;
                border: 2px solid #c62828;
                border-radius: 4px;
                color: #b71c1c;
            }
            QPushButton:checked { 
                background-color: #c8e6c9;
                color: #1b5e20;
                border-color: #2e7d32;
            }
            QPushButton:hover {
                border-width: 3px;
            }
        """)
        self.vacuum_valve_btn.setToolTip(
            f"Vacuum valve - connects pump to chamber\n"
            f"OPEN to draw vacuum\n"
            f"(Channel: {vacuum_valve_name}, {vacuum_valve_type})"
        )
        # Pass the ACTUAL channel name from config, not the role
        self.vacuum_valve_btn.clicked.connect(lambda checked, name=vacuum_valve_name: self.on_valve_toggle_by_name(name, "vacuum_valve"))
        layout.addWidget(self.vacuum_valve_btn, 1, 0)
        self.valve_buttons["vacuum_valve"] = self.vacuum_valve_btn
        
        # Vent Valve toggle (row 1, right) - releases vacuum
        self.vent_valve_btn = QPushButton("Vent Valve\nCLOSED")
        self.vent_valve_btn.setMinimumHeight(45)
        self.vent_valve_btn.setCheckable(True)
        self.vent_valve_btn.setStyleSheet("""
            QPushButton { 
                font-size: 10pt; 
                font-weight: bold;
                background-color: #ffcdd2;
                border: 2px solid #c62828;
                border-radius: 4px;
                color: #b71c1c;
            }
            QPushButton:checked { 
                background-color: #c8e6c9;
                color: #1b5e20;
                border-color: #2e7d32;
            }
            QPushButton:hover {
                border-width: 3px;
            }
        """)
        self.vent_valve_btn.setToolTip(
            f"Vent valve - releases chamber to atmosphere\n"
            f"OPEN to release vacuum\n"
            f"(Channel: {vent_valve_name}, {vent_valve_type})"
        )
        # Pass the ACTUAL channel name from config, not the role
        self.vent_valve_btn.clicked.connect(lambda checked, name=vent_valve_name: self.on_valve_toggle_by_name(name, "vent_valve"))
        layout.addWidget(self.vent_valve_btn, 1, 1)
        self.valve_buttons["vent_valve"] = self.vent_valve_btn
        
        group.setLayout(layout)
        return group
    
    def create_utility_controls(self) -> QGroupBox:
        """
        Create utility buttons group.
        
        Returns:
            QGroupBox: Utility controls group
        """
        group = QGroupBox("Utilities")
        layout = QVBoxLayout()
        
        # Tare button
        self.tare_btn = QPushButton("Tare Load Cells")
        self.tare_btn.setMinimumHeight(40)
        self.tare_btn.clicked.connect(self.on_tare)
        layout.addWidget(self.tare_btn)
        
        # Save data button
        self.save_btn = QPushButton("Save Data")
        self.save_btn.setMinimumHeight(40)
        self.save_btn.clicked.connect(self.on_save_data)
        layout.addWidget(self.save_btn)
        
        group.setLayout(layout)
        return group
    
    def on_start_test(self) -> None:
        """Handle start test button click."""
        logger.info("Start test requested")
        self.test_running = True
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.start_test_requested.emit()
    
    def on_stop_test(self) -> None:
        """Handle stop test button click."""
        logger.info("Stop test requested")
        self.test_running = False
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        self.stop_test_requested.emit()
    
    def on_pump_toggle(self) -> None:
        """Handle pump toggle button click."""
        self.pump_on = self.pump_btn.isChecked()
        
        if self.pump_on:
            self.pump_btn.setText("Pump ON")
            logger.info("Pump ON requested")
        else:
            self.pump_btn.setText("Pump OFF")
            logger.info("Pump OFF requested")
        
        self.pump_control_requested.emit(self.pump_on)
    
    def on_valve_toggle_by_name(self, channel_name: str, valve_role: str) -> None:
        """
        Handle valve toggle button click.
        
        Args:
            channel_name: The actual channel name from hardware config (e.g., "vacuum", "vent")
            valve_role: The role for display purposes (e.g., "vacuum_valve", "vent_valve")
        """
        btn = self.valve_buttons.get(valve_role)
        if not btn:
            logger.warning(f"No button found for role: {valve_role}")
            return
        
        state = btn.isChecked()
        self.valve_states[channel_name] = state
        
        # Update button text using the display role
        valve_label = valve_role.replace("_", " ").title()
        if state:
            btn.setText(f"{valve_label}\nOPEN")
            logger.info(f"{valve_role} ({channel_name}) OPEN requested")
        else:
            btn.setText(f"{valve_label}\nCLOSED")
            logger.info(f"{valve_role} ({channel_name}) CLOSED requested")
        
        # Emit signal with the ACTUAL channel name (what hardware expects)
        self.valve_control_requested.emit(channel_name, state)
    
    def on_tare(self) -> None:
        """Handle tare button click."""
        logger.info("Tare requested")
        self.tare_requested.emit()
    
    def on_save_data(self) -> None:
        """Handle save data button click."""
        logger.info("Save data requested")
        self.save_data_requested.emit()
    
    def set_test_running(self, running: bool) -> None:
        """
        Programmatically set test running state.
        
        Args:
            running: True if test is running
        """
        self.test_running = running
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
    
    def set_pump_state(self, on: bool) -> None:
        """
        Programmatically set pump state (without emitting signal).
        
        Args:
            on: True if pump should be on
        """
        self.pump_on = on
        self.pump_btn.blockSignals(True)
        self.pump_btn.setChecked(on)
        self.pump_btn.setText("Pump ON" if on else "Pump OFF")
        self.pump_btn.blockSignals(False)
    
    def set_valve_state_by_role(self, valve_role: str, state: bool) -> None:
        """
        Programmatically set valve state by role (without emitting signal).
        
        Args:
            valve_role: Role of the valve ("vacuum_valve" or "vent_valve")
            state: True for OPEN, False for CLOSED
        """
        btn = self.valve_buttons.get(valve_role)
        if not btn:
            logger.warning(f"Unknown valve role: {valve_role}")
            return
        
        channel_name = self.device_names.get(valve_role, valve_role)
        self.valve_states[channel_name] = state
        valve_label = valve_role.replace("_", " ").title()
        
        btn.blockSignals(True)
        btn.setChecked(state)
        btn.setText(f"{valve_label}\n{'OPEN' if state else 'CLOSED'}")
        btn.blockSignals(False)
    
    def _sync_from_relay_manager(self) -> None:
        """Sync button states from the global relay state manager."""
        try:
            from ...daq.relay_state_manager import relay_state_manager
            
            # Sync pump state using actual channel name from config
            pump_name = self.device_names.get("vacuum_pump", "vacuum_pump")
            pump_state = relay_state_manager.get_state("relay_module", pump_name)
            self.set_pump_state(pump_state)
            
            # Sync valve states using actual channel names from config
            for valve_role in ["vacuum_valve", "vent_valve"]:
                channel_name = self.device_names.get(valve_role, valve_role)
                state = relay_state_manager.get_state("relay_module", channel_name)
                self.set_valve_state_by_role(valve_role, state)
            
            logger.debug("Control panel synced from relay state manager")
        except Exception as e:
            logger.debug(f"Could not sync from relay manager: {e}")
    
    def _get_role_for_channel(self, channel_name: str) -> Optional[str]:
        """
        Get the role for a given channel name.
        
        Args:
            channel_name: Actual channel name from hardware
            
        Returns:
            Role name if found, None otherwise
        """
        for role, name in self.device_names.items():
            if name == channel_name:
                return role
        return None
    
    def on_relay_state_changed(self, module_name: str, channel_name: str, state: bool) -> None:
        """
        Handle relay state change from global manager.
        
        Args:
            module_name: Name of the relay module
            channel_name: Name of the channel/device (actual hardware name)
            state: New state (True = ON/OPEN)
        """
        # Check if this is the pump
        pump_name = self.device_names.get("vacuum_pump", "vacuum_pump")
        if channel_name == pump_name:
            self.set_pump_state(state)
            return
        
        # Check valve roles
        role = self._get_role_for_channel(channel_name)
        if role in ["vacuum_valve", "vent_valve"]:
            self.set_valve_state_by_role(role, state)

