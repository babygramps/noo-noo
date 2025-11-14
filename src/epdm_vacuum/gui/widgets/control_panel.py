"""
Control Panel Widget - Test Control Interface

Provides buttons and controls for:
- Starting/stopping tests
- Manual pump control
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
)
from PyQt5.QtCore import pyqtSignal, Qt

logger = logging.getLogger(__name__)


class ControlPanel(QWidget):
    """
    Widget for test control operations.
    
    Emits signals for user actions:
    - Start/stop test
    - Pump control
    - Tare load cells
    - Save data
    """
    
    # Signals
    start_test_requested = pyqtSignal()
    stop_test_requested = pyqtSignal()
    pump_control_requested = pyqtSignal(bool)  # True = ON, False = OFF
    tare_requested = pyqtSignal()
    save_data_requested = pyqtSignal()
    
    def __init__(self):
        """Initialize the control panel."""
        super().__init__()
        
        self.test_running = False
        self.pump_on = False
        
        self.init_ui()
        logger.info("ControlPanel initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        
        # Test control group
        test_group = self.create_test_controls()
        layout.addWidget(test_group)
        
        # Pump control group
        pump_group = self.create_pump_controls()
        layout.addWidget(pump_group)
        
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
    
    def create_pump_controls(self) -> QGroupBox:
        """
        Create pump control buttons group.
        
        Returns:
            QGroupBox: Pump controls group
        """
        group = QGroupBox("Pump Control")
        layout = QVBoxLayout()
        
        # Pump toggle button
        self.pump_btn = QPushButton("Pump OFF")
        self.pump_btn.setMinimumHeight(50)
        self.pump_btn.setCheckable(True)
        self.pump_btn.setStyleSheet("""
            QPushButton { 
                font-size: 14pt; 
                font-weight: bold;
                background-color: #cccccc;
            }
            QPushButton:checked { 
                background-color: #4CAF50;
                color: white;
            }
        """)
        self.pump_btn.clicked.connect(self.on_pump_toggle)
        layout.addWidget(self.pump_btn)
        
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
        Programmatically set pump state.
        
        Args:
            on: True if pump should be on
        """
        self.pump_on = on
        self.pump_btn.setChecked(on)
        self.pump_btn.setText("Pump ON" if on else "Pump OFF")

