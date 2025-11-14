"""
Test Status Panel - Combined Stage Progress and IO Status

Container widget that combines:
- Stage progress timeline
- IO device status display
- Clean, professional layout with proper styling
"""

from typing import Optional
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QSplitter,
)
from PyQt5.QtCore import Qt, pyqtSignal

from .stage_progress_widget import StageProgressWidget
from .io_status_widget import IOStatusWidget
from ...control.sequence import TestSequence

logger = logging.getLogger(__name__)


class TestStatusPanel(QWidget):
    """
    Combined panel showing stage progress and IO status.
    
    This widget serves as the main container for displaying:
    - Test stage progression timeline
    - Real-time IO device states
    - Updates from control thread signals
    """
    
    def __init__(self, parent=None):
        """Initialize the test status panel."""
        super().__init__(parent)
        
        self.stage_progress_widget: Optional[StageProgressWidget] = None
        self.io_status_widget: Optional[IOStatusWidget] = None
        
        self.init_ui()
        logger.info("TestStatusPanel initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        # Main container frame with styling
        main_frame = QFrame()
        main_frame.setFrameShape(QFrame.StyledPanel)
        main_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #e0e0e0;
                border-radius: 6px;
            }
        """)
        
        # Layout for main frame
        frame_layout = QHBoxLayout(main_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        
        # Create splitter for resizable sections
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #e0e0e0;
                width: 2px;
            }
            QSplitter::handle:hover {
                background-color: #2196F3;
            }
        """)
        
        # Create stage progress widget
        self.stage_progress_widget = StageProgressWidget()
        splitter.addWidget(self.stage_progress_widget)
        
        # Create IO status widget
        self.io_status_widget = IOStatusWidget()
        splitter.addWidget(self.io_status_widget)
        
        # Set initial splitter sizes (60% stage progress, 40% IO status)
        splitter.setSizes([600, 400])
        
        frame_layout.addWidget(splitter)
        
        # Add frame to main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(main_frame)
        
        # Set minimum height
        self.setMinimumHeight(200)
    
    # ========== Stage Progress Methods ==========
    
    def set_sequence(self, sequence: TestSequence) -> None:
        """
        Set the test sequence to display.
        
        Args:
            sequence: TestSequence to visualize
        """
        if self.stage_progress_widget:
            self.stage_progress_widget.set_sequence(sequence)
        
        logger.info(f"Test status panel loaded sequence: {sequence.name}")
    
    def set_current_stage(self, stage_index: int, stage_name: str) -> None:
        """
        Set the currently executing stage.
        
        Args:
            stage_index: Index of current stage (0-based)
            stage_name: Name of the current stage
        """
        if self.stage_progress_widget:
            self.stage_progress_widget.set_current_stage(stage_index, stage_name)
        
        logger.info(f"Test status panel: current stage set to {stage_index} - {stage_name}")
    
    def update_stage_progress(self, percentage: float, status_text: str) -> None:
        """
        Update progress within the current stage.
        
        Args:
            percentage: Progress percentage (0.0 to 1.0)
            status_text: Status message (e.g., elapsed time)
        """
        if self.stage_progress_widget:
            self.stage_progress_widget.update_progress(percentage, status_text)
    
    def mark_stage_complete(self, stage_index: int, completion_reason: str) -> None:
        """
        Mark a stage as completed.
        
        Args:
            stage_index: Index of completed stage
            completion_reason: Reason for completion
        """
        if self.stage_progress_widget:
            self.stage_progress_widget.mark_stage_complete(stage_index, completion_reason)
        
        logger.info(f"Test status panel: stage {stage_index} completed - {completion_reason}")
    
    # ========== IO Status Methods ==========
    
    def set_io_device_state(self, device_name: str, state: bool) -> None:
        """
        Update the state of a specific IO device.
        
        Args:
            device_name: Name of the device to update
            state: True for OPEN/ON, False for CLOSED/OFF
        """
        if self.io_status_widget:
            self.io_status_widget.set_device_state(device_name, state)
        
        logger.debug(f"Test status panel: IO device '{device_name}' set to {state}")
    
    def set_io_device_analog_value(self, device_name: str, value: float) -> None:
        """
        Update the analog value of an IO device.
        
        Args:
            device_name: Name of the device to update
            value: Analog value
        """
        if self.io_status_widget:
            self.io_status_widget.set_device_analog_value(device_name, value)
        
        logger.debug(f"Test status panel: IO device '{device_name}' analog value set to {value}")
    
    def reset_io_device_state(self, device_name: str) -> None:
        """
        Reset an IO device to NOT SET state.
        
        Args:
            device_name: Name of the device to reset
        """
        if self.io_status_widget:
            self.io_status_widget.reset_device_state(device_name)
    
    def reset_all_io_states(self) -> None:
        """Reset all IO devices to NOT SET state."""
        if self.io_status_widget:
            self.io_status_widget.reset_all()
        
        logger.info("Test status panel: all IO states reset")
    
    # ========== Combined Reset ==========
    
    def reset(self) -> None:
        """Reset both stage progress and IO status to initial state."""
        if self.stage_progress_widget:
            self.stage_progress_widget.reset()
        
        if self.io_status_widget:
            self.io_status_widget.reset_all()
        
        logger.info("Test status panel reset")
    
    # ========== Convenience Methods ==========
    
    def get_io_device_state(self, device_name: str) -> Optional[bool]:
        """
        Get the current state of an IO device.
        
        Args:
            device_name: Name of the device
        
        Returns:
            True if OPEN/ON, False if CLOSED/OFF, None if NOT SET
        """
        if self.io_status_widget:
            return self.io_status_widget.get_device_state(device_name)
        return None

