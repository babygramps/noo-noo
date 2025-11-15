"""
Main Window - Primary GUI Interface

The main application window that contains all UI components:
- Real-time data display
- Live plotting
- Control panel
- Menu and status bar
"""

from typing import Optional
import logging

from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QStatusBar,
    QMenuBar,
    QAction,
    QMessageBox,
    QDialog,
)
from PyQt5.QtCore import Qt

from .widgets.display_widget import DisplayWidget
from .widgets.plot_widget import PlotWidget
from .widgets.control_panel import ControlPanel
from .widgets.sequence_selector import SequenceSelectorWidget
from .widgets.test_status_panel import TestStatusPanel
from .threads.daq_thread import DataAcquisitionThread
from .threads.control_thread import ControlThread
from .dialogs.sequence_editor import SequenceEditorDialog
from .dialogs.io_config_dialog import IOConfigDialog
from ..control.sequence_manager import SequenceManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """
    Main application window for the vacuum test fixture.
    
    Integrates all GUI components and manages the application lifecycle.
    """
    
    def __init__(self):
        """Initialize the main window."""
        super().__init__()
        
        self.daq_thread: Optional[DataAcquisitionThread] = None
        self.control_thread: Optional[ControlThread] = None
        self.sequence_manager: Optional[SequenceManager] = None
        
        self.init_ui()
        self.init_sequence_manager()
        self.init_threads()
        
        logger.info("MainWindow initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("EPDM Vacuum Seal Test Fixture")
        self.setGeometry(100, 100, 1280, 720)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Create display widget for real-time values
        self.display_widget = DisplayWidget()
        main_layout.addWidget(self.display_widget)
        
        # Create plot widget for charts
        self.plot_widget = PlotWidget()
        main_layout.addWidget(self.plot_widget, stretch=1)
        
        # Create test status panel (stage progress + IO status)
        self.test_status_panel = TestStatusPanel()
        main_layout.addWidget(self.test_status_panel)
        
        # Create sequence selector
        self.sequence_selector = SequenceSelectorWidget()
        main_layout.addWidget(self.sequence_selector)
        
        # Create control panel
        self.control_panel = ControlPanel()
        main_layout.addWidget(self.control_panel)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create status bar
        self.statusBar().showMessage("Ready")
        
        # Connect control panel signals
        self.control_panel.start_test_requested.connect(self.on_start_test)
        self.control_panel.stop_test_requested.connect(self.on_stop_test)
        self.control_panel.pump_control_requested.connect(self.on_pump_control)
        self.control_panel.tare_requested.connect(self.on_tare)
        self.control_panel.save_data_requested.connect(self.on_save_data)
        
        # Connect sequence selector signals
        self.sequence_selector.sequence_changed.connect(self.on_sequence_changed)
        self.sequence_selector.edit_requested.connect(self.on_edit_sequence)
        self.sequence_selector.new_requested.connect(self.on_new_sequence)
        
        logger.info("UI initialized")
    
    def create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        save_action = QAction("&Save Data", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.on_save_data)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Sequence menu
        sequence_menu = menubar.addMenu("&Sequence")
        
        new_seq_action = QAction("&New Sequence", self)
        new_seq_action.setShortcut("Ctrl+N")
        new_seq_action.triggered.connect(self.on_new_sequence)
        sequence_menu.addAction(new_seq_action)
        
        load_seq_action = QAction("&Load Sequence", self)
        load_seq_action.setShortcut("Ctrl+O")
        load_seq_action.triggered.connect(self.on_load_sequence)
        sequence_menu.addAction(load_seq_action)
        
        edit_seq_action = QAction("&Edit Sequence", self)
        edit_seq_action.setShortcut("Ctrl+E")
        edit_seq_action.triggered.connect(self.on_edit_current_sequence)
        sequence_menu.addAction(edit_seq_action)
        
        sequence_menu.addSeparator()
        
        save_seq_action = QAction("&Save Sequence", self)
        save_seq_action.setShortcut("Ctrl+Shift+S")
        save_seq_action.triggered.connect(self.on_save_sequence)
        sequence_menu.addAction(save_seq_action)
        
        # Test menu
        test_menu = menubar.addMenu("&Test")
        
        start_action = QAction("&Start Test", self)
        start_action.setShortcut("F5")
        start_action.triggered.connect(self.on_start_test)
        test_menu.addAction(start_action)
        
        stop_action = QAction("St&op Test", self)
        stop_action.setShortcut("F6")
        stop_action.triggered.connect(self.on_stop_test)
        test_menu.addAction(stop_action)
        
        test_menu.addSeparator()
        
        tare_action = QAction("&Tare Load Cells", self)
        tare_action.triggered.connect(self.on_tare)
        test_menu.addAction(tare_action)
        
        # Settings menu
        settings_menu = menubar.addMenu("&Settings")
        
        io_config_action = QAction("&IO Device Configuration", self)
        io_config_action.setShortcut("Ctrl+I")
        io_config_action.triggered.connect(self.open_io_config)
        settings_menu.addAction(io_config_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_sequence_manager(self) -> None:
        """Initialize the sequence manager."""
        from ..config.settings import get_settings
        from pathlib import Path
        
        # Load settings to get safety limits
        config_file = Path(__file__).parent.parent / "config" / "hardware_config.yaml"
        settings = get_settings(str(config_file))
        
        # Get safety limits for validation
        config_limits = {
            "max_vacuum_bar": settings.get("safety", "max_vacuum_bar", default=1.0),
            "max_force_kg": settings.get("safety", "max_force_kg", default=800.0),
            "max_single_cell_kg": settings.get("safety", "max_single_cell_kg", default=250.0),
        }
        
        # Create sequence manager
        sequences_dir = settings.get("sequences", "directory", default="sequences")
        self.sequence_manager = SequenceManager(sequences_dir, config_limits)
        
        # Set manager in sequence selector
        self.sequence_selector.set_sequence_manager(self.sequence_manager)
        
        logger.info("Sequence manager initialized")
    
    def init_threads(self) -> None:
        """Initialize background threads."""
        # Initialize hardware interfaces from configuration
        widgetlords_iface, modbus_iface = self.init_hardware_interfaces()
        
        # Create data acquisition thread with hardware interfaces
        self.daq_thread = DataAcquisitionThread(
            widgetlords_interface=widgetlords_iface,
            modbus_interface=modbus_iface
        )
        self.daq_thread.new_data.connect(self.on_new_data)
        self.daq_thread.error_occurred.connect(self.on_daq_error)
        
        # Create control thread
        self.control_thread = ControlThread()
        self.control_thread.status_update.connect(self.on_status_update)
        self.control_thread.test_complete.connect(self.on_test_complete)
        
        # Start DAQ thread
        self.daq_thread.start()
        
        logger.info("Background threads initialized")
    
    def init_hardware_interfaces(self):
        """
        Initialize hardware interfaces from configuration.
        
        Returns:
            tuple: (widgetlords_interface, modbus_interface)
        """
        from ..config.settings import get_settings
        from ..daq import WidgetLordsInterface, ModbusInterface
        from pathlib import Path
        
        # Load hardware configuration
        config_file = Path(__file__).parent.parent / "config" / "hardware_config.yaml"
        settings = get_settings(str(config_file))
        
        widgetlords_iface = None
        modbus_iface = None
        
        # Initialize WidgetLords interface if enabled
        widgetlords_config = settings.get("hardware", "widgetlords", default={})
        if widgetlords_config.get("enabled", False):
            try:
                widgetlords_iface = WidgetLordsInterface()
                widgetlords_iface.connect()
                logger.info("WidgetLords interface initialized")
            except Exception as e:
                logger.error(f"Failed to initialize WidgetLords interface: {e}")
        
        # Initialize Modbus interface if enabled
        modbus_config = settings.get("hardware", "modbus", default={})
        if modbus_config.get("enabled", False):
            try:
                # Extract all modbus configuration parameters
                modbus_iface = ModbusInterface(
                    port=modbus_config.get("port", "/dev/ttyUSB0"),
                    slave_address=modbus_config.get("slave_address", 1),
                    baudrate=modbus_config.get("baudrate", 9600),
                    timeout=modbus_config.get("timeout", 1.0),
                    parity=modbus_config.get("parity", "None"),
                    databits=modbus_config.get("databits", 8),
                    stopbits=modbus_config.get("stopbits", 1.0),
                    byteorder=modbus_config.get("byteorder", "big"),
                    wordorder=modbus_config.get("wordorder", "big"),
                    close_port_after_each_call=modbus_config.get("close_port_after_each_call", False),
                    debug=modbus_config.get("debug", False),
                )
                modbus_iface.connect()
                logger.info(f"Modbus interface initialized on {modbus_config.get('port')}")
            except Exception as e:
                logger.error(f"Failed to initialize Modbus interface: {e}")
                logger.error(f"  Port: {modbus_config.get('port')}")
                logger.error(f"  Baudrate: {modbus_config.get('baudrate')}")
                logger.error(f"  Slave Address: {modbus_config.get('slave_address')}")
        
        return widgetlords_iface, modbus_iface
    
    def on_new_data(self, data: dict) -> None:
        """
        Handle new data from DAQ thread.
        
        Args:
            data: Dictionary containing sensor readings
        """
        # Update display widget
        self.display_widget.update_values(data)
        
        # Update plot widget
        self.plot_widget.add_data_point(data)
    
    def on_daq_error(self, error_msg: str) -> None:
        """
        Handle DAQ errors.
        
        Args:
            error_msg: Error message
        """
        logger.error(f"DAQ error: {error_msg}")
        self.statusBar().showMessage(f"Error: {error_msg}", 5000)
    
    def on_status_update(self, status: str) -> None:
        """
        Handle status updates from control thread.
        
        Args:
            status: Status message
        """
        self.statusBar().showMessage(status)
        logger.info(f"Status: {status}")
    
    def on_test_complete(self) -> None:
        """Handle test completion."""
        logger.info("Test completed")
        self.statusBar().showMessage("Test completed", 5000)
        QMessageBox.information(self, "Test Complete", "The test has completed successfully.")
        
        # Reset test status panel after a brief delay (so user can see final state)
        # This could be optional - comment out if you want to keep the display
        # QTimer.singleShot(10000, self.test_status_panel.reset)  # Reset after 10 seconds
    
    def on_start_test(self) -> None:
        """Handle start test request."""
        logger.info("Starting test...")
        self.statusBar().showMessage("Starting test...")
        
        # Get current sequence
        current_seq = self.sequence_selector.get_current_sequence()
        
        # Validate sequence is selected
        if not current_seq:
            QMessageBox.warning(
                self,
                "No Sequence Selected",
                "Please select a test sequence before starting."
            )
            return
        
        # Create new control thread with sequence
        if self.control_thread and self.control_thread.isRunning():
            logger.warning("Control thread already running")
            return
        
        # Initialize test status panel with sequence
        self.test_status_panel.set_sequence(current_seq)
        
        # TODO: Create test controller with hardware interfaces
        # For now, create control thread without controller (will use placeholder)
        self.control_thread = ControlThread(sequence=current_seq)
        self.control_thread.status_update.connect(self.on_status_update)
        self.control_thread.test_complete.connect(self.on_test_complete)
        self.control_thread.stage_changed.connect(self.on_stage_changed)
        
        # Connect new signals for enhanced UI feedback
        self.control_thread.io_state_changed.connect(self.on_io_state_changed)
        self.control_thread.stage_progress_updated.connect(self.on_stage_progress_updated)
        self.control_thread.stage_completed.connect(self.on_stage_completed)
        
        self.control_thread.start()
        
        logger.info(f"Started test with sequence: {current_seq.name if current_seq else 'None'}")
    
    def on_stop_test(self) -> None:
        """Handle stop test request."""
        logger.info("Stopping test...")
        self.statusBar().showMessage("Stopping test...")
        
        # Stop control thread
        if self.control_thread and self.control_thread.isRunning():
            self.control_thread.stop()
        
        # Reset test status panel
        self.test_status_panel.reset()
        
        logger.info("Test stopped by user")
    
    def on_pump_control(self, state: bool) -> None:
        """
        Handle pump control request.
        
        Args:
            state: True to turn pump on, False to turn off
        """
        logger.info(f"Setting pump to {'ON' if state else 'OFF'}")
        self.statusBar().showMessage(f"Pump {'ON' if state else 'OFF'}")
        
        # TODO: Implement pump control via hardware interface
        logger.warning("TODO: Pump control not implemented")
    
    def on_tare(self) -> None:
        """Handle tare request."""
        logger.info("Taring load cells...")
        self.statusBar().showMessage("Taring load cells...")
        
        # TODO: Implement tare via hardware interface
        logger.warning("TODO: Tare function not implemented")
    
    def on_save_data(self) -> None:
        """Handle save data request."""
        logger.info("Saving data...")
        self.statusBar().showMessage("Saving data...")
        
        # TODO: Implement data save logic
        logger.warning("TODO: Save data function not implemented")
    
    def on_sequence_changed(self, sequence) -> None:
        """
        Handle sequence selection change.
        
        Args:
            sequence: TestSequence that was selected
        """
        logger.info(f"Sequence changed to: {sequence.name}")
        self.statusBar().showMessage(f"Loaded sequence: {sequence.name}")
    
    def on_stage_changed(self, current: int, total: int, stage_name: str) -> None:
        """
        Handle stage change during test execution.
        
        Args:
            current: Current stage index
            total: Total number of stages
            stage_name: Name of the current stage
        """
        status = f"Executing: Stage {current + 1}/{total} - {stage_name}"
        self.statusBar().showMessage(status)
        logger.info(f"Stage changed: {status}")
        
        # Update test status panel
        self.test_status_panel.set_current_stage(current, stage_name)
    
    def on_io_state_changed(self, device_name: str, state: bool) -> None:
        """
        Handle IO device state change.
        
        Args:
            device_name: Name of the IO device
            state: True for OPEN/ON, False for CLOSED/OFF
        """
        self.test_status_panel.set_io_device_state(device_name, state)
        logger.debug(f"IO state updated in UI: {device_name} -> {state}")
    
    def on_stage_progress_updated(self, percentage: float, status_text: str) -> None:
        """
        Handle stage progress update.
        
        Args:
            percentage: Progress percentage (0.0 to 1.0)
            status_text: Status message
        """
        self.test_status_panel.update_stage_progress(percentage, status_text)
    
    def on_stage_completed(self, stage_index: int, completion_reason: str) -> None:
        """
        Handle stage completion.
        
        Args:
            stage_index: Index of completed stage
            completion_reason: Reason for completion
        """
        self.test_status_panel.mark_stage_complete(stage_index, completion_reason)
        logger.info(f"Stage {stage_index} completed in UI: {completion_reason}")
    
    def on_new_sequence(self) -> None:
        """Handle new sequence request."""
        logger.info("Creating new sequence...")
        
        # Create default sequence
        if self.sequence_manager:
            sequence = self.sequence_manager.create_default_sequence()
        else:
            from ..control.sequence import TestSequence
            sequence = TestSequence(name="New Sequence")
        
        # Open editor dialog
        self.open_sequence_editor(sequence)
    
    def on_load_sequence(self) -> None:
        """Handle load sequence request from menu."""
        # Delegate to sequence selector widget
        self.sequence_selector.on_load_sequence()
    
    def on_edit_sequence(self, sequence) -> None:
        """
        Handle edit sequence request.
        
        Args:
            sequence: TestSequence to edit
        """
        self.open_sequence_editor(sequence)
    
    def on_edit_current_sequence(self) -> None:
        """Handle edit current sequence from menu."""
        current_seq = self.sequence_selector.get_current_sequence()
        if current_seq:
            self.open_sequence_editor(current_seq)
        else:
            QMessageBox.information(
                self,
                "No Sequence",
                "Please select a sequence first."
            )
    
    def on_save_sequence(self) -> None:
        """Handle save current sequence."""
        current_seq = self.sequence_selector.get_current_sequence()
        if current_seq and self.sequence_manager:
            success = self.sequence_manager.save_sequence(current_seq)
            if success:
                self.statusBar().showMessage(f"Saved sequence: {current_seq.name}", 3000)
                QMessageBox.information(
                    self,
                    "Saved",
                    f"Sequence '{current_seq.name}' saved successfully."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Failed to save sequence '{current_seq.name}'"
                )
        else:
            QMessageBox.information(
                self,
                "No Sequence",
                "Please select a sequence first."
            )
    
    def open_sequence_editor(self, sequence) -> None:
        """
        Open the sequence editor dialog.
        
        Args:
            sequence: TestSequence to edit
        """
        # Get config limits
        config_limits = None
        if self.sequence_manager:
            config_limits = self.sequence_manager.config_limits
        
        # Create and show editor dialog
        editor = SequenceEditorDialog(sequence, config_limits, self)
        editor.sequence_saved.connect(self.on_sequence_saved)
        
        result = editor.exec_()
        
        if result == QDialog.Accepted:
            logger.info(f"Sequence editor completed for: {sequence.name}")
    
    def on_sequence_saved(self, sequence) -> None:
        """
        Handle sequence saved from editor.
        
        Args:
            sequence: TestSequence that was saved
        """
        if self.sequence_manager:
            success = self.sequence_manager.save_sequence(sequence)
            if success:
                self.statusBar().showMessage(f"Saved sequence: {sequence.name}", 3000)
                
                # Refresh sequence list and select the saved sequence
                self.sequence_selector.refresh_sequence_list()
                self.sequence_selector.set_current_sequence(sequence)
                
                logger.info(f"Sequence saved: {sequence.name}")
            else:
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Failed to save sequence '{sequence.name}'"
                )
    
    def open_io_config(self) -> None:
        """Open IO device configuration dialog."""
        logger.info("Opening IO configuration dialog...")
        
        dialog = IOConfigDialog(self)
        dialog.config_saved.connect(self.on_io_config_saved)
        dialog.exec_()
    
    def on_io_config_saved(self) -> None:
        """Handle IO configuration saved."""
        logger.info("IO configuration saved, reloading IO status widget...")
        
        # Reload IO status widget to show new devices
        if hasattr(self, 'test_status_panel') and self.test_status_panel:
            # Reset and reload IO devices
            self.test_status_panel.reset_all_io_states()
            
            # Recreate IO status widget with new config
            from .widgets.io_status_widget import IOStatusWidget
            new_io_widget = IOStatusWidget()
            
            # Replace the old widget (this is a bit hacky, but works)
            if self.test_status_panel.io_status_widget:
                # Get the parent layout
                old_widget = self.test_status_panel.io_status_widget
                parent = old_widget.parent()
                
                # Note: A full reload would require restarting the app
                # For now, just inform the user
                QMessageBox.information(
                    self,
                    "Configuration Saved",
                    "IO configuration has been saved.\n\n"
                    "Note: New IO devices will be available after restarting the application."
                )
    
    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """
        <h2>EPDM Vacuum Seal Test Fixture</h2>
        <p>Version 1.1.0</p>
        <p>Control software for EPDM gasket vacuum seal testing system.</p>
        <p><b>Hardware:</b></p>
        <ul>
            <li>Raspberry Pi 5</li>
            <li>WidgetLords PI-SPI-DIN PLC Modules</li>
            <li>TLB4 Load Cell Transmitter</li>
            <li>SPT25-20-V30D Pressure Sensor</li>
        </ul>
        """
        QMessageBox.about(self, "About", about_text)
    
    def closeEvent(self, event) -> None:
        """
        Handle window close event.
        
        Args:
            event: Close event
        """
        logger.info("Closing application...")
        
        # Stop threads gracefully
        if self.daq_thread and self.daq_thread.isRunning():
            self.daq_thread.stop()
            self.daq_thread.wait(2000)
        
        if self.control_thread and self.control_thread.isRunning():
            self.control_thread.stop()
            self.control_thread.wait(2000)
        
        event.accept()
        logger.info("Application closed")

