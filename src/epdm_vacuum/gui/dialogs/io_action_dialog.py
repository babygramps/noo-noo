"""
I/O Action Dialog

Dialog for creating and editing I/O actions within a test stage.
"""

from typing import Optional, Dict, Any, List
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QCheckBox,
    QLineEdit,
    QLabel,
    QGroupBox,
)
from PyQt5.QtCore import Qt

from ...control.sequence import IOAction, IOActionType, IOActionTiming

logger = logging.getLogger(__name__)


class IOActionDialog(QDialog):
    """
    Dialog for creating/editing individual I/O actions.
    """
    
    def __init__(self, io_action: Optional[IOAction] = None, 
                 available_devices: Optional[List[str]] = None,
                 parent=None):
        """
        Initialize the I/O action dialog.
        
        Args:
            io_action: Existing IOAction to edit (creates new if None)
            available_devices: List of available device names
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.io_action = io_action
        self.available_devices = available_devices or []
        self.is_new = (io_action is None)
        
        if self.io_action is None:
            self.io_action = IOAction(device_name="")
        
        self.init_ui()
        self.populate_from_action()
        
        logger.debug("IOActionDialog initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("I/O Action")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Form layout for parameters
        form = QFormLayout()
        
        # Device selection
        self.device_combo = QComboBox()
        if self.available_devices:
            self.device_combo.addItems(self.available_devices)
            self.device_combo.setEditable(True)
        else:
            self.device_combo.setEditable(True)
            self.device_combo.setPlaceholderText("Enter device name...")
        form.addRow("Device:", self.device_combo)
        
        # Action type
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItem("Digital Output (ON/OFF)", IOActionType.DIGITAL_OUTPUT)
        self.action_type_combo.addItem("Analog Output (Value)", IOActionType.ANALOG_OUTPUT)
        self.action_type_combo.addItem("Pulse (Timed)", IOActionType.PULSE)
        self.action_type_combo.currentIndexChanged.connect(self.on_action_type_changed)
        form.addRow("Action Type:", self.action_type_combo)
        
        # Value - depends on action type
        value_layout = QHBoxLayout()
        
        self.digital_checkbox = QCheckBox("ON")
        self.digital_checkbox.setChecked(False)
        value_layout.addWidget(self.digital_checkbox)
        
        self.analog_spinbox = QDoubleSpinBox()
        self.analog_spinbox.setRange(0.0, 10.0)
        self.analog_spinbox.setDecimals(2)
        self.analog_spinbox.setSuffix(" V")
        self.analog_spinbox.setVisible(False)
        value_layout.addWidget(self.analog_spinbox)
        
        value_layout.addStretch()
        form.addRow("Value:", value_layout)
        
        # Timing
        self.timing_combo = QComboBox()
        self.timing_combo.addItem("Before Stage", IOActionTiming.BEFORE_STAGE)
        self.timing_combo.addItem("Start of Stage", IOActionTiming.START_OF_STAGE)
        self.timing_combo.addItem("During Stage", IOActionTiming.DURING_STAGE)
        self.timing_combo.addItem("End of Stage", IOActionTiming.END_OF_STAGE)
        self.timing_combo.addItem("After Stage", IOActionTiming.AFTER_STAGE)
        form.addRow("Timing:", self.timing_combo)
        
        # Delay
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setRange(0.0, 300.0)
        self.delay_spinbox.setDecimals(1)
        self.delay_spinbox.setSuffix(" s")
        form.addRow("Delay:", self.delay_spinbox)
        
        # Duration (for pulse/timed actions)
        self.duration_spinbox = QDoubleSpinBox()
        self.duration_spinbox.setRange(0.0, 300.0)
        self.duration_spinbox.setDecimals(1)
        self.duration_spinbox.setSuffix(" s")
        self.duration_spinbox.setSpecialValueText("N/A")
        form.addRow("Duration:", self.duration_spinbox)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("Optional description...")
        form.addRow("Description:", self.description_edit)
        
        layout.addLayout(form)
        
        # Dialog buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.on_ok)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
    
    def populate_from_action(self) -> None:
        """Populate UI from IOAction object."""
        # Device
        if self.io_action.device_name:
            index = self.device_combo.findText(self.io_action.device_name)
            if index >= 0:
                self.device_combo.setCurrentIndex(index)
            else:
                self.device_combo.setEditText(self.io_action.device_name)
        
        # Action type
        for i in range(self.action_type_combo.count()):
            if self.action_type_combo.itemData(i) == self.io_action.action_type:
                self.action_type_combo.setCurrentIndex(i)
                break
        
        # Value
        if self.io_action.action_type == IOActionType.DIGITAL_OUTPUT:
            self.digital_checkbox.setChecked(bool(self.io_action.value))
        elif self.io_action.action_type == IOActionType.ANALOG_OUTPUT:
            try:
                self.analog_spinbox.setValue(float(self.io_action.value))
            except (TypeError, ValueError):
                self.analog_spinbox.setValue(0.0)
        
        # Timing
        for i in range(self.timing_combo.count()):
            if self.timing_combo.itemData(i) == self.io_action.timing:
                self.timing_combo.setCurrentIndex(i)
                break
        
        # Delay
        self.delay_spinbox.setValue(self.io_action.delay_seconds)
        
        # Duration
        if self.io_action.duration_seconds is not None:
            self.duration_spinbox.setValue(self.io_action.duration_seconds)
        else:
            self.duration_spinbox.setValue(0.0)
        
        # Description
        self.description_edit.setText(self.io_action.description)
        
        # Update value widget visibility
        self.on_action_type_changed()
    
    def on_action_type_changed(self) -> None:
        """Handle action type change to show/hide appropriate value widget."""
        action_type = self.action_type_combo.currentData()
        
        if action_type == IOActionType.DIGITAL_OUTPUT:
            self.digital_checkbox.setVisible(True)
            self.analog_spinbox.setVisible(False)
            self.duration_spinbox.setEnabled(False)
        elif action_type == IOActionType.ANALOG_OUTPUT:
            self.digital_checkbox.setVisible(False)
            self.analog_spinbox.setVisible(True)
            self.duration_spinbox.setEnabled(False)
        elif action_type == IOActionType.PULSE:
            self.digital_checkbox.setVisible(True)
            self.analog_spinbox.setVisible(False)
            self.duration_spinbox.setEnabled(True)
    
    def on_ok(self) -> None:
        """Handle OK button click."""
        # Update IOAction from UI
        self.io_action.device_name = self.device_combo.currentText().strip()
        self.io_action.action_type = self.action_type_combo.currentData()
        
        # Value based on type
        if self.io_action.action_type == IOActionType.DIGITAL_OUTPUT:
            self.io_action.value = self.digital_checkbox.isChecked()
        elif self.io_action.action_type == IOActionType.ANALOG_OUTPUT:
            self.io_action.value = self.analog_spinbox.value()
        elif self.io_action.action_type == IOActionType.PULSE:
            self.io_action.value = self.digital_checkbox.isChecked()
        
        self.io_action.timing = self.timing_combo.currentData()
        self.io_action.delay_seconds = self.delay_spinbox.value()
        
        # Duration (only for pulse or if specified)
        if self.duration_spinbox.value() > 0:
            self.io_action.duration_seconds = self.duration_spinbox.value()
        else:
            self.io_action.duration_seconds = None
        
        self.io_action.description = self.description_edit.text().strip()
        
        # Validate
        is_valid, errors = self.io_action.validate()
        if not is_valid:
            from PyQt5.QtWidgets import QMessageBox
            error_msg = "Validation errors:\n\n" + "\n".join(f"• {err}" for err in errors)
            QMessageBox.warning(self, "Validation Error", error_msg)
            return
        
        self.accept()
    
    def get_io_action(self) -> IOAction:
        """
        Get the configured IOAction.
        
        Returns:
            IOAction: The configured action
        """
        return self.io_action

