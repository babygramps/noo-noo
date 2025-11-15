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
from .dialogs.test_metadata_dialog import TestMetadataDialog
from ..control.sequence_manager import SequenceManager
from ..logging.data_logger import DataLogger
from ..logging.buffer import DataBuffer

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
        
        # Data logging components
        self.data_buffer = DataBuffer(max_size=10000)
        self.data_logger = DataLogger(output_dir="data")
        
        # Track current test metadata and CSV path
        self.current_test_metadata: Optional[dict] = None
        self.current_csv_path: Optional[str] = None
        
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
        
        edit_metadata_action = QAction("Edit &Metadata", self)
        edit_metadata_action.setShortcut("Ctrl+M")
        edit_metadata_action.triggered.connect(self.on_edit_metadata)
        file_menu.addAction(edit_metadata_action)
        
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
        # Store data in buffer
        self.data_buffer.append(data)
        
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
        
        # Show metadata dialog to get test information and save location
        metadata_dialog = TestMetadataDialog(self)
        result = metadata_dialog.exec_()
        
        if result != QDialog.Accepted:
            logger.info("Test start cancelled by user")
            self.statusBar().showMessage("Test cancelled")
            return
        
        # Get metadata and save path
        test_metadata = metadata_dialog.get_metadata()
        csv_path = metadata_dialog.get_save_path()
        
        logger.info(f"Test metadata collected: {test_metadata}")
        logger.info(f"Data will be saved to: {csv_path}")
        
        # Store current test info for later editing
        self.current_test_metadata = test_metadata
        self.current_csv_path = csv_path
        
        # Clear data buffer for new test
        self.data_buffer.clear()
        
        # Initialize test status panel with sequence
        self.test_status_panel.set_sequence(current_seq)
        
        # Initialize hardware interfaces (if available)
        try:
            widgetlords_iface, modbus_iface = self.init_hardware_interfaces()
        except Exception as e:
            logger.warning(f"Failed to initialize hardware interfaces: {e}")
            logger.warning("Proceeding with mock data")
            widgetlords_iface = None
            modbus_iface = None
        
        # Create test controller with data logging
        from ..control.test_controller import TestController
        test_controller = TestController(
            widgetlords_interface=widgetlords_iface,
            modbus_interface=modbus_iface,
            data_logger=self.data_logger,
            csv_path=csv_path,
            test_metadata=test_metadata,
        )
        
        # Load sequence into controller
        if not test_controller.load_sequence(current_seq):
            QMessageBox.critical(
                self,
                "Error",
                "Failed to load test sequence into controller."
            )
            return
        
        # Create control thread with controller
        self.control_thread = ControlThread(
            test_controller=test_controller,
            sequence=current_seq
        )
        self.control_thread.status_update.connect(self.on_status_update)
        self.control_thread.test_complete.connect(self.on_test_complete)
        self.control_thread.stage_changed.connect(self.on_stage_changed)
        
        # Connect new signals for enhanced UI feedback
        self.control_thread.io_state_changed.connect(self.on_io_state_changed)
        self.control_thread.stage_progress_updated.connect(self.on_stage_progress_updated)
        self.control_thread.stage_completed.connect(self.on_stage_completed)
        
        self.control_thread.start()
        
        self.statusBar().showMessage(f"Test started: {test_metadata.get('test_name', 'Unnamed Test')}")
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
    
    def on_edit_metadata(self) -> None:
        """Handle edit metadata request."""
        logger.info("Opening metadata editor...")
        
        # Check if we have a current test or ask user to browse for a metadata file
        if not self.current_test_metadata and not self.current_csv_path:
            # No current test - ask if they want to browse for an existing file or create new
            reply = QMessageBox.question(
                self,
                "Edit Metadata",
                "No current test metadata found.\n\n"
                "Would you like to browse for an existing metadata file to edit?\n\n"
                "Click 'Yes' to browse, 'No' to create new metadata.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                return
            elif reply == QMessageBox.Yes:
                # Browse for existing metadata file
                from PyQt5.QtWidgets import QFileDialog
                json_file, _ = QFileDialog.getOpenFileName(
                    self,
                    "Select Metadata File",
                    "data/",
                    "JSON Files (*.json);;All Files (*.*)"
                )
                
                if not json_file:
                    return
                
                # Load existing metadata
                import json
                try:
                    with open(json_file, 'r') as f:
                        self.current_test_metadata = json.load(f)
                    # Derive CSV path from JSON path
                    from pathlib import Path
                    self.current_csv_path = str(Path(json_file).with_suffix('.csv'))
                    logger.info(f"Loaded metadata from: {json_file}")
                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Load Error",
                        f"Failed to load metadata file:\n{e}"
                    )
                    return
            else:
                # Create new metadata
                self.current_test_metadata = {}
                self.current_csv_path = None
        
        # Create metadata dialog
        metadata_dialog = TestMetadataDialog(self)
        
        # Pre-populate with existing metadata if available
        if self.current_test_metadata:
            metadata_dialog.populate_from_metadata(self.current_test_metadata)
        
        # Set the save path if we have one
        if self.current_csv_path:
            metadata_dialog.save_path = self.current_csv_path
            metadata_dialog.file_path_label.setText(self.current_csv_path)
        
        # Show dialog
        result = metadata_dialog.exec_()
        
        if result == QDialog.Accepted:
            # Get updated metadata
            updated_metadata = metadata_dialog.get_metadata()
            updated_csv_path = metadata_dialog.get_save_path()
            
            # Update stored values
            self.current_test_metadata = updated_metadata
            self.current_csv_path = updated_csv_path
            
            # Save metadata to JSON file
            from pathlib import Path
            import json
            
            metadata_path = Path(updated_csv_path).with_suffix('.json')
            try:
                with open(metadata_path, 'w') as f:
                    json.dump(updated_metadata, f, indent=2)
                
                QMessageBox.information(
                    self,
                    "Metadata Saved",
                    f"Metadata successfully saved to:\n{metadata_path}"
                )
                self.statusBar().showMessage(f"Metadata saved to {metadata_path}", 5000)
                logger.info(f"Metadata updated and saved to: {metadata_path}")
                
            except Exception as e:
                error_msg = f"Failed to save metadata: {e}"
                logger.error(error_msg, exc_info=True)
                QMessageBox.critical(
                    self,
                    "Save Error",
                    error_msg
                )
    
    def on_save_data(self) -> None:
        """Handle save data request - save current buffer to CSV."""
        logger.info("Saving data...")
        self.statusBar().showMessage("Saving data...")
        
        # Check if there's data to save
        if self.data_buffer.size() == 0:
            QMessageBox.information(
                self,
                "No Data",
                "There is no data to save. Start data acquisition first."
            )
            return
        
        # Ask user for save location
        from PyQt5.QtWidgets import QFileDialog
        from datetime import datetime
        
        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"manual_save_{timestamp}.csv"
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Data",
            f"data/{default_filename}",
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not filename:
            logger.info("Save cancelled by user")
            return
        
        # Ensure .csv extension
        if not filename.lower().endswith('.csv'):
            filename += '.csv'
        
        try:
            # Get all data from buffer
            buffer_data = self.data_buffer.get_all()
            
            if not buffer_data:
                QMessageBox.warning(
                    self,
                    "No Data",
                    "Buffer is empty, nothing to save."
                )
                return
            
            # Create basic metadata for manual save
            from datetime import datetime
            manual_save_metadata = {
                "save_type": "manual_save",
                "save_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "data_points": len(buffer_data),
                "note": "Data manually saved from buffer"
            }
            
            # Save to CSV using data logger (with metadata in separate JSON)
            filepath = self.data_logger.log_to_csv(
                buffer_data, 
                filename=filename,
                metadata=manual_save_metadata
            )
            
            if filepath:
                QMessageBox.information(
                    self,
                    "Data Saved",
                    f"Successfully saved {len(buffer_data)} data points to:\n{filepath}"
                )
                self.statusBar().showMessage(f"Data saved to {filepath}", 5000)
                logger.info(f"Saved {len(buffer_data)} data points to {filepath}")
            else:
                QMessageBox.warning(
                    self,
                    "Save Error",
                    "Failed to save data. Check logs for details."
                )
        
        except Exception as e:
            error_msg = f"Error saving data: {e}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(
                self,
                "Save Error",
                error_msg
            )
    
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

