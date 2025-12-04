"""
Control Panel Widget - Test Control Interface

Provides buttons and controls for:
- Starting/stopping tests
- Manual pump and valve control
- Tare operations
- Data saving
"""

import logging

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


class ControlPanel(QWidget):
    """
    Widget for test control operations.
    
    Emits signals for user actions:
    - Start/stop test
    - Pump and valve control
    - Tare load cells
    - Save data
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
        
        self.test_running = False
        self.pump_on = False
        self.valve_states = {
            "vent_valve": False,
            "vacuum_valve": False,
        }
        
        # Pending action flags to prevent callback interference
        # When a user clicks a button, we set these flags to prevent
        # the RelayStateManager callback from fighting with the click handler
        self._pending_pump_action = False
        self._pending_valve_actions = set()
        
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
        
        Returns:
            QGroupBox: I/O controls group
        """
        group = QGroupBox("Pump & Valves")
        layout = QGridLayout()
        layout.setSpacing(8)
        
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
        self.pump_btn.setToolTip("Toggle vacuum pump ON/OFF")
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
        self.vacuum_valve_btn.setToolTip("Vacuum valve - connects pump to chamber\nOPEN to draw vacuum")
        self.vacuum_valve_btn.clicked.connect(lambda checked: self.on_valve_toggle("vacuum_valve"))
        layout.addWidget(self.vacuum_valve_btn, 1, 0)
        
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
        self.vent_valve_btn.setToolTip("Vent valve - releases chamber to atmosphere\nOPEN to release vacuum")
        self.vent_valve_btn.clicked.connect(lambda checked: self.on_valve_toggle("vent_valve"))
        layout.addWidget(self.vent_valve_btn, 1, 1)
        
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
        """
        Handle pump toggle button click.
        
        Similar to valve handling, uses _pending_pump_action flag to prevent
        the RelayStateManager callback from interfering with the click handling.
        """
        self.pump_on = self.pump_btn.isChecked()
        
        # Update button text immediately for responsive UI
        self.pump_btn.setText("Pump ON" if self.pump_on else "Pump OFF")
        logger.info(f"[ControlPanel] Pump {'ON' if self.pump_on else 'OFF'} requested")
        
        # Mark pending action to prevent callback interference
        self._pending_pump_action = True
        
        # Emit signal to request hardware change
        self.pump_control_requested.emit(self.pump_on)
        
        # Clear pending flag
        self._pending_pump_action = False
        logger.info(f"[ControlPanel] Pump action complete")
    
    def on_valve_toggle(self, valve_name: str) -> None:
        """
        Handle valve toggle button click.
        
        NOTE: This is called when the user physically clicks the button.
        The button's checked state has ALREADY been toggled by Qt before
        this handler is called. We read the new state and emit a signal
        to request the hardware change.
        
        The RelayStateManager callback (on_relay_state_changed) will be
        called during the hardware write, but we use _pending_valve_action
        to prevent it from fighting with this handler.
        """
        logger.info(f"[ControlPanel] on_valve_toggle called for: {valve_name}")
        
        if valve_name == "vacuum_valve":
            btn = self.vacuum_valve_btn
        elif valve_name == "vent_valve":
            btn = self.vent_valve_btn
        else:
            logger.warning(f"Unknown valve: {valve_name}")
            return
        
        state = btn.isChecked()
        self.valve_states[valve_name] = state
        logger.info(f"[ControlPanel] {valve_name} button checked={state}, requesting hardware change")
        
        # Update button text immediately for responsive UI
        valve_label = valve_name.replace("_", " ").title()
        btn.setText(f"{valve_label}\n{'OPEN' if state else 'CLOSED'}")
        
        # Mark that we're handling this valve action (prevents callback interference)
        if not hasattr(self, '_pending_valve_actions'):
            self._pending_valve_actions = set()
        self._pending_valve_actions.add(valve_name)
        
        # Emit signal to request hardware change
        logger.info(f"[ControlPanel] Emitting valve_control_requested({valve_name}, {state})")
        self.valve_control_requested.emit(valve_name, state)
        
        # Clear pending flag after signal handling completes
        self._pending_valve_actions.discard(valve_name)
        logger.info(f"[ControlPanel] Valve action complete for {valve_name}")
    
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
    
    def set_valve_state(self, valve_name: str, state: bool) -> None:
        """
        Programmatically set valve state (without emitting signal).
        
        Args:
            valve_name: Name of the valve ("vacuum_valve" or "vent_valve")
            state: True for OPEN, False for CLOSED
        """
        if valve_name == "vacuum_valve":
            btn = self.vacuum_valve_btn
        elif valve_name == "vent_valve":
            btn = self.vent_valve_btn
        else:
            logger.warning(f"Unknown valve: {valve_name}")
            return
        
        self.valve_states[valve_name] = state
        valve_label = valve_name.replace("_", " ").title()
        
        btn.blockSignals(True)
        btn.setChecked(state)
        btn.setText(f"{valve_label}\n{'OPEN' if state else 'CLOSED'}")
        btn.blockSignals(False)
    
    def _sync_from_relay_manager(self) -> None:
        """Sync button states from the global relay state manager."""
        try:
            from ...daq.relay_state_manager import relay_state_manager
            
            # Sync pump state
            pump_state = relay_state_manager.get_state("relay_module", "vacuum_pump")
            self.set_pump_state(pump_state)
            
            # Sync valve states
            for valve_name in ["vacuum_valve", "vent_valve"]:
                state = relay_state_manager.get_state("relay_module", valve_name)
                self.set_valve_state(valve_name, state)
            
            logger.debug("Control panel synced from relay state manager")
        except Exception as e:
            logger.debug(f"Could not sync from relay manager: {e}")
    
    def on_relay_state_changed(self, module_name: str, channel_name: str, state: bool) -> None:
        """
        Handle relay state change from global RelayStateManager.
        
        This callback is triggered when ANY component changes relay state,
        including this ControlPanel's own button clicks. We need to avoid
        interfering with in-progress user actions.
        
        Args:
            module_name: Name of the relay module
            channel_name: Name of the channel/device
            state: New state (True = ON/OPEN)
        """
        # Check if this is from our own pending action (avoid feedback loop)
        pending = getattr(self, '_pending_valve_actions', set())
        if channel_name in pending:
            logger.debug(f"[ControlPanel] Ignoring callback for {channel_name} - pending user action")
            return
        
        pending_pump = getattr(self, '_pending_pump_action', False)
        if channel_name == "vacuum_pump" and pending_pump:
            logger.debug(f"[ControlPanel] Ignoring callback for pump - pending user action")
            return
        
        logger.debug(f"[ControlPanel] on_relay_state_changed: {channel_name} -> {state}")
        
        if channel_name == "vacuum_pump":
            self.set_pump_state(state)
        elif channel_name in ["vacuum_valve", "vent_valve"]:
            self.set_valve_state(channel_name, state)

