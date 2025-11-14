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
)
from PyQt5.QtCore import Qt

from .widgets.display_widget import DisplayWidget
from .widgets.plot_widget import PlotWidget
from .widgets.control_panel import ControlPanel
from .threads.daq_thread import DataAcquisitionThread
from .threads.control_thread import ControlThread

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
        
        self.init_ui()
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
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def init_threads(self) -> None:
        """Initialize background threads."""
        # TODO: Initialize hardware interfaces and pass to threads
        
        # Create data acquisition thread
        self.daq_thread = DataAcquisitionThread()
        self.daq_thread.new_data.connect(self.on_new_data)
        self.daq_thread.error_occurred.connect(self.on_daq_error)
        
        # Create control thread
        self.control_thread = ControlThread()
        self.control_thread.status_update.connect(self.on_status_update)
        self.control_thread.test_complete.connect(self.on_test_complete)
        
        # Start DAQ thread
        self.daq_thread.start()
        
        logger.info("Background threads initialized")
    
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
    
    def on_start_test(self) -> None:
        """Handle start test request."""
        logger.info("Starting test...")
        self.statusBar().showMessage("Starting test...")
        
        # TODO: Implement test start logic
        if self.control_thread and not self.control_thread.isRunning():
            self.control_thread.start()
        
        logger.warning("TODO: Start test logic not fully implemented")
    
    def on_stop_test(self) -> None:
        """Handle stop test request."""
        logger.info("Stopping test...")
        self.statusBar().showMessage("Stopping test...")
        
        # TODO: Implement test stop logic
        if self.control_thread and self.control_thread.isRunning():
            self.control_thread.stop()
        
        logger.warning("TODO: Stop test logic not fully implemented")
    
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
    
    def show_about(self) -> None:
        """Show about dialog."""
        about_text = """
        <h2>EPDM Vacuum Seal Test Fixture</h2>
        <p>Version 1.1.0</p>
        <p>Control software for EPDM gasket vacuum seal testing system.</p>
        <p><b>Hardware:</b></p>
        <ul>
            <li>Raspberry Pi 5</li>
            <li>WidgetLords PLC DAQ</li>
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

