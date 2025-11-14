"""
Sequence Editor Dialog

Dialog for creating and editing test sequences:
- Simple mode: Basic stage creation (vacuum + hold time)
- Advanced mode: Full parameter control
- Stage management: Add, remove, reorder, duplicate
- Real-time validation and duration preview
"""

from typing import Optional, Dict, Any, List
import logging

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTextEdit,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QRadioButton,
    QComboBox,
    QGroupBox,
    QMessageBox,
    QFrame,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from ...control.sequence import TestSequence, TestStage, IOAction, IOActionType, IOActionTiming, PumpMode

logger = logging.getLogger(__name__)


class SequenceEditorDialog(QDialog):
    """
    Dialog for creating and editing test sequences.
    
    Supports both simple and advanced modes with validation
    and visual feedback.
    """
    
    # Signal emitted when sequence is saved
    sequence_saved = pyqtSignal(TestSequence)
    
    def __init__(self, sequence: Optional[TestSequence] = None, 
                 config_limits: Optional[Dict[str, Any]] = None,
                 parent=None):
        """
        Initialize the sequence editor dialog.
        
        Args:
            sequence: Existing sequence to edit (creates new if None)
            config_limits: Safety limits from configuration
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.sequence = sequence
        self.config_limits = config_limits or {}
        self.is_new = (sequence is None)
        
        # If no sequence provided, create a default one
        if self.sequence is None:
            self.sequence = TestSequence(
                name="New Sequence",
                description="",
            )
        
        self.modified = False
        
        # Load available I/O devices from config
        self.available_io_devices = self._load_io_devices()
        
        self.init_ui()
        self.populate_from_sequence()
        
        logger.info(f"SequenceEditorDialog initialized for sequence: {self.sequence.name}")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Sequence Editor")
        self.setMinimumSize(1000, 800)
        
        layout = QVBoxLayout(self)
        
        # Sequence metadata section
        metadata_group = self.create_metadata_section()
        layout.addWidget(metadata_group)
        
        # Stages table
        stages_group = self.create_stages_section()
        layout.addWidget(stages_group)
        
        # Stage controls
        controls_layout = self.create_stage_controls()
        layout.addLayout(controls_layout)
        
        # Stage configuration panel (for selected stage)
        self.stage_config_group = self.create_stage_config_section()
        layout.addWidget(self.stage_config_group, stretch=1)
        
        # Status and duration preview
        status_layout = self.create_status_section()
        layout.addLayout(status_layout)
        
        # Dialog buttons
        button_layout = self.create_dialog_buttons()
        layout.addLayout(button_layout)
    
    def create_metadata_section(self) -> QGroupBox:
        """Create the metadata input section."""
        group = QGroupBox("Sequence Information")
        layout = QGridLayout()
        
        # Sequence name
        layout.addWidget(QLabel("Name:"), 0, 0)
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter sequence name...")
        self.name_edit.textChanged.connect(self.on_metadata_changed)
        layout.addWidget(self.name_edit, 0, 1, 1, 3)
        
        # Description
        layout.addWidget(QLabel("Description:"), 1, 0, Qt.AlignTop)
        self.description_edit = QTextEdit()
        self.description_edit.setMaximumHeight(60)
        self.description_edit.setPlaceholderText("Optional description...")
        self.description_edit.textChanged.connect(self.on_metadata_changed)
        layout.addWidget(self.description_edit, 1, 1, 1, 3)
        
        group.setLayout(layout)
        return group
    
    
    def create_stages_section(self) -> QGroupBox:
        """Create the stages table section."""
        group = QGroupBox("Test Stages")
        layout = QVBoxLayout()
        
        # Create table
        self.stages_table = QTableWidget()
        self.stages_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.stages_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.stages_table.itemChanged.connect(self.on_table_item_changed)
        
        # Set up columns based on current mode
        self.update_table_columns()
        
        layout.addWidget(self.stages_table)
        
        group.setLayout(layout)
        return group
    
    def update_table_columns(self) -> None:
        """Update table columns."""
        columns = ["#", "Name", "Setpoint (bar)", "Time Limit (s)", "Pump Mode", "Est. Duration (s)"]
        self.stages_table.setColumnCount(len(columns))
        self.stages_table.setHorizontalHeaderLabels(columns)
        
        # Set column widths
        header = self.stages_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # #
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Name
        for i in range(2, len(columns)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
    
    def create_stage_controls(self) -> QHBoxLayout:
        """Create stage management buttons."""
        layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Stage")
        self.add_btn.clicked.connect(self.on_add_stage)
        layout.addWidget(self.add_btn)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(self.on_duplicate_stage)
        self.duplicate_btn.setEnabled(False)
        layout.addWidget(self.duplicate_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.clicked.connect(self.on_remove_stage)
        self.remove_btn.setEnabled(False)
        layout.addWidget(self.remove_btn)
        
        layout.addSpacing(20)
        
        self.move_up_btn = QPushButton("Move Up")
        self.move_up_btn.clicked.connect(self.on_move_up)
        self.move_up_btn.setEnabled(False)
        layout.addWidget(self.move_up_btn)
        
        self.move_down_btn = QPushButton("Move Down")
        self.move_down_btn.clicked.connect(self.on_move_down)
        self.move_down_btn.setEnabled(False)
        layout.addWidget(self.move_down_btn)
        
        layout.addStretch()
        
        # Connect selection changed signal
        self.stages_table.itemSelectionChanged.connect(self.on_selection_changed)
        
        return layout
    
    def create_stage_config_section(self) -> QGroupBox:
        """Create the stage configuration panel."""
        group = QGroupBox("Stage Configuration")
        group.setEnabled(False)  # Disabled until a stage is selected
        layout = QVBoxLayout()
        
        # Stage name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Stage Name:"))
        self.stage_name_edit = QLineEdit()
        self.stage_name_edit.textChanged.connect(self.on_stage_config_changed)
        name_layout.addWidget(self.stage_name_edit)
        layout.addLayout(name_layout)
        
        # Completion conditions group
        completion_group = QGroupBox("Completion Conditions (stage ends when FIRST condition is met)")
        completion_layout = QGridLayout()
        
        # Vacuum setpoint
        self.setpoint_enabled = QCheckBox("Vacuum Setpoint:")
        self.setpoint_enabled.setChecked(True)
        self.setpoint_enabled.stateChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.setpoint_enabled, 0, 0)
        
        self.setpoint_spinbox = QDoubleSpinBox()
        self.setpoint_spinbox.setRange(0.0, 1.0)
        self.setpoint_spinbox.setDecimals(3)
        self.setpoint_spinbox.setSuffix(" bar")
        self.setpoint_spinbox.setValue(0.5)
        self.setpoint_spinbox.valueChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.setpoint_spinbox, 0, 1)
        
        # Time limit
        self.time_enabled = QCheckBox("Time Limit:")
        self.time_enabled.setChecked(True)
        self.time_enabled.stateChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.time_enabled, 1, 0)
        
        self.time_spinbox = QDoubleSpinBox()
        self.time_spinbox.setRange(0.0, 3600.0)
        self.time_spinbox.setDecimals(1)
        self.time_spinbox.setSuffix(" seconds")
        self.time_spinbox.setValue(30.0)
        self.time_spinbox.valueChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.time_spinbox, 1, 1)
        
        # Minimum time
        self.min_time_enabled = QCheckBox("Minimum Time:")
        self.min_time_enabled.setChecked(False)
        self.min_time_enabled.stateChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.min_time_enabled, 2, 0)
        
        self.min_time_spinbox = QDoubleSpinBox()
        self.min_time_spinbox.setRange(0.0, 600.0)
        self.min_time_spinbox.setDecimals(1)
        self.min_time_spinbox.setSuffix(" seconds")
        self.min_time_spinbox.setValue(0.0)
        self.min_time_spinbox.setEnabled(False)
        self.min_time_spinbox.valueChanged.connect(self.on_stage_config_changed)
        completion_layout.addWidget(self.min_time_spinbox, 2, 1)
        
        # Connect min time checkbox to enable/disable spinbox
        self.min_time_enabled.stateChanged.connect(
            lambda state: self.min_time_spinbox.setEnabled(state == Qt.Checked)
        )
        
        completion_group.setLayout(completion_layout)
        layout.addWidget(completion_group)
        
        # Pump control group
        pump_group = QGroupBox("Pump Control Mode")
        pump_layout = QVBoxLayout()
        
        self.pump_continuous_radio = QRadioButton("Continuous ON - Pump runs continuously during stage")
        self.pump_continuous_radio.toggled.connect(self.on_stage_config_changed)
        pump_layout.addWidget(self.pump_continuous_radio)
        
        self.pump_maintain_radio = QRadioButton("Maintain Vacuum - Pump cycles to maintain setpoint")
        self.pump_maintain_radio.setChecked(True)
        self.pump_maintain_radio.toggled.connect(self.on_stage_config_changed)
        pump_layout.addWidget(self.pump_maintain_radio)
        
        self.pump_off_radio = QRadioButton("OFF - Pump stays off (for venting/manual stages)")
        self.pump_off_radio.toggled.connect(self.on_stage_config_changed)
        pump_layout.addWidget(self.pump_off_radio)
        
        pump_group.setLayout(pump_layout)
        layout.addWidget(pump_group)
        
        # I/O Device States
        io_group = self.create_io_control_panel()
        layout.addWidget(io_group)
        
        group.setLayout(layout)
        return group
    
    def create_io_control_panel(self) -> QGroupBox:
        """Create the I/O control panel section."""
        group = QGroupBox("I/O Device States")
        layout = QVBoxLayout()
        
        # Info label with helpful guidance
        info_label = QLabel(
            "ℹ️ Common setup: inlet_valve CLOSED, vent_valve CLOSED at start then OPEN at end."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-style: italic; padding: 5px;")
        layout.addWidget(info_label)
        
        # I/O states table - shows ALL available devices
        self.io_table = QTableWidget()
        self.io_table.setColumnCount(4)
        self.io_table.setHorizontalHeaderLabels(["Device", "Type", "State at Start", "State at End"])
        self.io_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.io_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.io_table.setMaximumHeight(200)
        self.io_table.setEditTriggers(QAbstractItemView.NoEditTriggers)  # Use custom widgets
        
        # Set column widths
        header = self.io_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)  # Device
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Start state
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # End state
        
        layout.addWidget(self.io_table)
        
        # Note about vacuum pump
        pump_note = QLabel("Note: Vacuum pump is controlled automatically - it will turn ON at stage start and OFF at stage end.")
        pump_note.setWordWrap(True)
        pump_note.setStyleSheet("color: #0066cc; font-size: 10pt; padding: 5px; background-color: #f0f8ff; border-radius: 3px;")
        layout.addWidget(pump_note)
        
        group.setLayout(layout)
        return group
    
    def create_status_section(self) -> QHBoxLayout:
        """Create status and validation display."""
        layout = QHBoxLayout()
        
        # Validation status
        self.validation_label = QLabel("Validation: OK")
        self.validation_label.setStyleSheet("color: green; font-weight: bold;")
        layout.addWidget(self.validation_label)
        
        layout.addStretch()
        
        # Duration preview
        self.duration_label = QLabel("Total Duration: 0s")
        layout.addWidget(self.duration_label)
        
        return layout
    
    def create_dialog_buttons(self) -> QHBoxLayout:
        """Create dialog action buttons."""
        layout = QHBoxLayout()
        
        # Validate button
        validate_btn = QPushButton("Validate")
        validate_btn.clicked.connect(self.validate_sequence)
        layout.addWidget(validate_btn)
        
        layout.addStretch()
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        # Save button
        self.save_btn = QPushButton("Save")
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self.on_save)
        layout.addWidget(self.save_btn)
        
        return layout
    
    def populate_from_sequence(self) -> None:
        """Populate UI with sequence data."""
        # Set metadata
        self.name_edit.setText(self.sequence.name)
        self.description_edit.setPlainText(self.sequence.description)
        
        # Populate stages
        self.refresh_stages_table()
        
        # Update status
        self.update_status()
    
    def refresh_stages_table(self) -> None:
        """Refresh the stages table from sequence data."""
        # Block signals during refresh
        self.stages_table.blockSignals(True)
        
        # Clear and resize table
        self.stages_table.setRowCount(len(self.sequence.stages))
        
        # Populate rows
        for i, stage in enumerate(self.sequence.stages):
            self.populate_stage_row(i, stage)
        
        # Re-enable signals
        self.stages_table.blockSignals(False)
        
        logger.debug(f"Refreshed stages table with {len(self.sequence.stages)} stages")
    
    def populate_stage_row(self, row: int, stage: TestStage) -> None:
        """Populate a table row with stage data."""
        col = 0
        
        # Stage number
        item = QTableWidgetItem(str(row + 1))
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
        col += 1
        
        # Name
        item = QTableWidgetItem(stage.name)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
        col += 1
        
        # Setpoint (vacuum)
        vacuum_str = f"{stage.target_vacuum_bar:.3f}" if stage.target_vacuum_bar is not None else "—"
        item = QTableWidgetItem(vacuum_str)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
        col += 1
        
        # Time limit
        time_str = f"{stage.max_time_seconds:.0f}" if stage.max_time_seconds is not None else "—"
        item = QTableWidgetItem(time_str)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
        col += 1
        
        # Pump mode
        pump_str = stage.pump_mode.value.title()
        item = QTableWidgetItem(pump_str)
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
        col += 1
        
        # Estimated duration
        duration = stage.get_estimated_duration()
        item = QTableWidgetItem(f"{duration:.0f}")
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
    
    
    def on_add_stage(self) -> None:
        """Add a new stage to the sequence."""
        # Create default stage with sensible defaults
        stage = TestStage(
            name=f"Stage {len(self.sequence.stages) + 1}",
            target_vacuum_bar=0.5,
            max_time_seconds=30.0,
            min_time_seconds=0.0,
            pump_mode=PumpMode.MAINTAIN_VACUUM,
        )
        
        # Auto-generate essential I/O actions for vacuum operation
        self._add_default_io_actions(stage)
        
        self.sequence.add_stage(stage)
        self.refresh_stages_table()
        self.update_status()
        self.modified = True
        
        # Select new row
        self.stages_table.selectRow(len(self.sequence.stages) - 1)
        
        # Refresh stage config panel and I/O table
        self.refresh_stage_config()
        self.refresh_io_table()
        
        logger.info("Added new stage to sequence")
    
    def on_duplicate_stage(self) -> None:
        """Duplicate the selected stage."""
        row = self.stages_table.currentRow()
        if row >= 0:
            self.sequence.duplicate_stage(row)
            self.refresh_stages_table()
            self.update_status()
            self.modified = True
            
            # Select duplicated row
            self.stages_table.selectRow(row + 1)
            
            logger.info(f"Duplicated stage {row + 1}")
    
    def on_remove_stage(self) -> None:
        """Remove the selected stage."""
        row = self.stages_table.currentRow()
        if row >= 0:
            # Confirm deletion
            reply = QMessageBox.question(
                self,
                "Remove Stage",
                f"Remove stage {row + 1}?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.sequence.remove_stage(row)
                self.refresh_stages_table()
                self.update_status()
                self.modified = True
                
                logger.info(f"Removed stage {row + 1}")
    
    def on_move_up(self) -> None:
        """Move selected stage up."""
        row = self.stages_table.currentRow()
        if row > 0:
            self.sequence.move_stage(row, row - 1)
            self.refresh_stages_table()
            self.stages_table.selectRow(row - 1)
            self.modified = True
            
            logger.info(f"Moved stage {row + 1} up")
    
    def on_move_down(self) -> None:
        """Move selected stage down."""
        row = self.stages_table.currentRow()
        if row >= 0 and row < len(self.sequence.stages) - 1:
            self.sequence.move_stage(row, row + 1)
            self.refresh_stages_table()
            self.stages_table.selectRow(row + 1)
            self.modified = True
            
            logger.info(f"Moved stage {row + 1} down")
    
    def on_selection_changed(self) -> None:
        """Handle stage selection change."""
        row = self.stages_table.currentRow()
        has_selection = row >= 0
        
        self.duplicate_btn.setEnabled(has_selection)
        self.remove_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and row > 0)
        self.move_down_btn.setEnabled(has_selection and row < len(self.sequence.stages) - 1)
        
        # Update stage configuration panel and I/O table
        self.refresh_stage_config()
        self.refresh_io_table()
    
    def on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle table cell edit (table is now read-only, so this shouldn't be called)."""
        # Table is now read-only, edits happen in the stage config panel
        pass
    
    def on_metadata_changed(self) -> None:
        """Handle metadata field changes."""
        self.modified = True
    
    def on_stage_config_changed(self) -> None:
        """Handle changes in the stage configuration panel."""
        row = self.stages_table.currentRow()
        if row < 0 or row >= len(self.sequence.stages):
            return
        
        stage = self.sequence.stages[row]
        
        # Update stage from UI
        stage.name = self.stage_name_edit.text()
        
        # Update setpoint
        if self.setpoint_enabled.isChecked():
            stage.target_vacuum_bar = self.setpoint_spinbox.value()
            self.setpoint_spinbox.setEnabled(True)
        else:
            stage.target_vacuum_bar = None
            self.setpoint_spinbox.setEnabled(False)
        
        # Update time limit
        if self.time_enabled.isChecked():
            stage.max_time_seconds = self.time_spinbox.value()
            self.time_spinbox.setEnabled(True)
        else:
            stage.max_time_seconds = None
            self.time_spinbox.setEnabled(False)
        
        # Update minimum time
        if self.min_time_enabled.isChecked():
            stage.min_time_seconds = self.min_time_spinbox.value()
        else:
            stage.min_time_seconds = 0.0
        
        # Update pump mode
        if self.pump_continuous_radio.isChecked():
            stage.pump_mode = PumpMode.CONTINUOUS
        elif self.pump_maintain_radio.isChecked():
            stage.pump_mode = PumpMode.MAINTAIN_VACUUM
        elif self.pump_off_radio.isChecked():
            stage.pump_mode = PumpMode.OFF
        
        # Refresh table row to show updated values
        self.stages_table.blockSignals(True)
        self.populate_stage_row(row, stage)
        self.stages_table.blockSignals(False)
        
        self.modified = True
        self.update_status()
    
    def refresh_stage_config(self) -> None:
        """Refresh the stage configuration panel with selected stage data."""
        row = self.stages_table.currentRow()
        
        if row < 0 or row >= len(self.sequence.stages):
            self.stage_config_group.setEnabled(False)
            return
        
        self.stage_config_group.setEnabled(True)
        stage = self.sequence.stages[row]
        
        # Block signals during refresh
        self.stage_name_edit.blockSignals(True)
        self.setpoint_enabled.blockSignals(True)
        self.setpoint_spinbox.blockSignals(True)
        self.time_enabled.blockSignals(True)
        self.time_spinbox.blockSignals(True)
        self.min_time_enabled.blockSignals(True)
        self.min_time_spinbox.blockSignals(True)
        
        # Set values
        self.stage_name_edit.setText(stage.name)
        
        # Setpoint
        if stage.target_vacuum_bar is not None:
            self.setpoint_enabled.setChecked(True)
            self.setpoint_spinbox.setValue(stage.target_vacuum_bar)
            self.setpoint_spinbox.setEnabled(True)
        else:
            self.setpoint_enabled.setChecked(False)
            self.setpoint_spinbox.setEnabled(False)
        
        # Time limit
        if stage.max_time_seconds is not None:
            self.time_enabled.setChecked(True)
            self.time_spinbox.setValue(stage.max_time_seconds)
            self.time_spinbox.setEnabled(True)
        else:
            self.time_enabled.setChecked(False)
            self.time_spinbox.setEnabled(False)
        
        # Minimum time
        if stage.min_time_seconds > 0:
            self.min_time_enabled.setChecked(True)
            self.min_time_spinbox.setValue(stage.min_time_seconds)
            self.min_time_spinbox.setEnabled(True)
        else:
            self.min_time_enabled.setChecked(False)
            self.min_time_spinbox.setEnabled(False)
        
        # Pump mode
        if stage.pump_mode == PumpMode.CONTINUOUS:
            self.pump_continuous_radio.setChecked(True)
        elif stage.pump_mode == PumpMode.MAINTAIN_VACUUM:
            self.pump_maintain_radio.setChecked(True)
        elif stage.pump_mode == PumpMode.OFF:
            self.pump_off_radio.setChecked(True)
        
        # Re-enable signals
        self.stage_name_edit.blockSignals(False)
        self.setpoint_enabled.blockSignals(False)
        self.setpoint_spinbox.blockSignals(False)
        self.time_enabled.blockSignals(False)
        self.time_spinbox.blockSignals(False)
        self.min_time_enabled.blockSignals(False)
        self.min_time_spinbox.blockSignals(False)
        
        logger.debug(f"Refreshed stage config panel for stage {row + 1}")
    
    def validate_sequence(self) -> bool:
        """
        Validate the current sequence and show results.
        
        Returns:
            bool: True if valid
        """
        # Update sequence from UI
        self.update_sequence_from_ui()
        
        # Validate
        is_valid, errors, warnings = self.sequence.validate(self.config_limits)
        
        if is_valid:
            if warnings:
                self.validation_label.setText(f"Validation: OK ({len(warnings)} warnings)")
                self.validation_label.setStyleSheet("color: orange; font-weight: bold;")
                
                # Show warnings to user
                warning_msg = "Sequence is valid, but has warnings:\n\n" + "\n".join(f"• {warn}" for warn in warnings)
                warning_msg += "\n\nThese are recommendations, not errors. The sequence will run, but may not work as expected."
                QMessageBox.warning(self, "Validation Warnings", warning_msg)
            else:
                self.validation_label.setText("Validation: OK")
                self.validation_label.setStyleSheet("color: green; font-weight: bold;")
                QMessageBox.information(self, "Validation", "Sequence is valid with no warnings!")
        else:
            self.validation_label.setText("Validation: ERRORS")
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
            
            error_msg = "Validation errors:\n\n" + "\n".join(f"• {err}" for err in errors)
            
            if warnings:
                error_msg += "\n\nWarnings:\n" + "\n".join(f"• {warn}" for warn in warnings)
            
            QMessageBox.warning(self, "Validation Errors", error_msg)
        
        return is_valid
    
    def update_status(self) -> None:
        """Update status displays."""
        # Update duration
        duration = self.sequence.get_estimated_duration()
        minutes = int(duration // 60)
        seconds = int(duration % 60)
        self.duration_label.setText(f"Total Duration: ~{minutes}m {seconds}s ({len(self.sequence.stages)} stages)")
        
        # Quick validation check
        is_valid, errors, warnings = self.sequence.validate(self.config_limits)
        if is_valid:
            if warnings:
                self.validation_label.setText(f"Validation: OK ({len(warnings)} warnings)")
                self.validation_label.setStyleSheet("color: orange; font-weight: bold;")
                self.validation_label.setToolTip("\n".join(warnings))
            else:
                self.validation_label.setText("Validation: OK")
                self.validation_label.setStyleSheet("color: green; font-weight: bold;")
                self.validation_label.setToolTip("")
        else:
            self.validation_label.setText(f"Validation: {len(errors)} errors")
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
            self.validation_label.setToolTip("\n".join(errors[:3]))  # Show first 3 errors
    
    def update_sequence_from_ui(self) -> None:
        """Update sequence object from UI fields."""
        self.sequence.name = self.name_edit.text()
        self.sequence.description = self.description_edit.toPlainText()
    
    def on_save(self) -> None:
        """Handle save button click."""
        # Update sequence from UI
        self.update_sequence_from_ui()
        
        # Validate before saving
        is_valid, errors, warnings = self.sequence.validate(self.config_limits)
        if not is_valid:
            error_msg = "Cannot save invalid sequence:\n\n" + "\n".join(f"• {err}" for err in errors)
            QMessageBox.warning(self, "Validation Errors", error_msg)
            return
        
        # Show warnings but allow saving
        if warnings:
            warning_msg = "Sequence has warnings:\n\n" + "\n".join(f"• {warn}" for warn in warnings)
            warning_msg += "\n\nDo you want to save anyway?"
            
            reply = QMessageBox.question(
                self,
                "Save with Warnings?",
                warning_msg,
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.No:
                return
        
        # Emit signal and accept dialog
        self.sequence_saved.emit(self.sequence)
        self.accept()
        
        logger.info(f"Sequence '{self.sequence.name}' saved")
    
    def closeEvent(self, event) -> None:
        """Handle dialog close."""
        if self.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "You have unsaved changes. Close anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
        
        event.accept()
    
    def _load_io_devices(self) -> List[str]:
        """
        Load available I/O device names from configuration.
        
        Returns:
            List of device names
        """
        try:
            from ...config.settings import get_settings
            from pathlib import Path
            
            config_file = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
            settings = get_settings(str(config_file))
            
            devices = []
            
            # Load digital outputs
            digital_outputs = settings.get("io_devices", "digital_outputs", default=[])
            if isinstance(digital_outputs, list):
                for device in digital_outputs:
                    if isinstance(device, dict) and "name" in device:
                        devices.append(device["name"])
            
            # Load analog outputs
            analog_outputs = settings.get("io_devices", "analog_outputs", default=[])
            if isinstance(analog_outputs, list):
                for device in analog_outputs:
                    if isinstance(device, dict) and "name" in device:
                        devices.append(device["name"])
            
            logger.debug(f"Loaded {len(devices)} I/O devices from config")
            return devices
            
        except Exception as e:
            logger.warning(f"Could not load I/O devices from config: {e}")
            return []
    
    def refresh_io_table(self) -> None:
        """Refresh I/O states table for currently selected stage."""
        row = self.stages_table.currentRow()
        
        if row < 0 or row >= len(self.sequence.stages):
            self.io_table.setRowCount(0)
            return
        
        stage = self.sequence.stages[row]
        
        # Block signals during refresh
        self.io_table.blockSignals(True)
        
        # Get all available I/O devices from configuration
        io_devices = self._get_io_device_configs()
        
        # Set table size to show ALL devices
        self.io_table.setRowCount(len(io_devices))
        
        # Populate each row with device info
        for i, (device_name, device_config) in enumerate(io_devices.items()):
            # Device name
            name_item = QTableWidgetItem(device_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.io_table.setItem(i, 0, name_item)
            
            # Device type
            device_type = device_config.get("type", "Digital")
            type_item = QTableWidgetItem(device_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.io_table.setItem(i, 1, type_item)
            
            # Get current states from stage I/O actions
            start_state = self._get_io_state_from_stage(stage, device_name, IOActionTiming.START_OF_STAGE)
            end_state = self._get_io_state_from_stage(stage, device_name, IOActionTiming.END_OF_STAGE)
            
            # State at Start - combo box or checkbox
            if device_type == "Digital":
                start_combo = QComboBox()
                start_combo.addItems(["Not Set", "CLOSED", "OPEN"])
                start_combo.setCurrentText(start_state)
                start_combo.currentTextChanged.connect(
                    lambda state, dev=device_name, timing=IOActionTiming.START_OF_STAGE: 
                    self._on_io_state_changed(dev, timing, state)
                )
                self.io_table.setCellWidget(i, 2, start_combo)
            else:
                # For analog, would need spinbox - for now just show text
                start_item = QTableWidgetItem(start_state)
                self.io_table.setItem(i, 2, start_item)
            
            # State at End - combo box or checkbox
            if device_type == "Digital":
                end_combo = QComboBox()
                end_combo.addItems(["Not Set", "CLOSED", "OPEN"])
                end_combo.setCurrentText(end_state)
                end_combo.currentTextChanged.connect(
                    lambda state, dev=device_name, timing=IOActionTiming.END_OF_STAGE:
                    self._on_io_state_changed(dev, timing, state)
                )
                self.io_table.setCellWidget(i, 3, end_combo)
            else:
                # For analog, would need spinbox
                end_item = QTableWidgetItem(end_state)
                self.io_table.setItem(i, 3, end_item)
        
        # Re-enable signals
        self.io_table.blockSignals(False)
        
        logger.debug(f"Refreshed I/O table with {len(io_devices)} devices")
    
    def _get_io_device_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available I/O device configurations.
        
        Returns:
            Dict mapping device_name to configuration dict with 'type' field
        """
        try:
            from ...config.settings import get_settings
            from pathlib import Path
            
            config_file = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
            settings = get_settings(str(config_file))
            
            devices = {}
            
            # Load digital outputs
            digital_outputs = settings.get("io_devices", "digital_outputs", default=[])
            if isinstance(digital_outputs, list):
                for device in digital_outputs:
                    if isinstance(device, dict) and "name" in device:
                        devices[device["name"]] = {
                            "type": "Digital",
                            "description": device.get("description", ""),
                            "channel": device.get("channel", 0)
                        }
            
            # Load analog outputs
            analog_outputs = settings.get("io_devices", "analog_outputs", default=[])
            if isinstance(analog_outputs, list):
                for device in analog_outputs:
                    if isinstance(device, dict) and "name" in device:
                        devices[device["name"]] = {
                            "type": "Analog",
                            "description": device.get("description", ""),
                            "channel": device.get("channel", 0),
                            "min_value": device.get("min_value", 0.0),
                            "max_value": device.get("max_value", 10.0)
                        }
            
            return devices
            
        except Exception as e:
            logger.warning(f"Could not load I/O device configs: {e}")
            return {}
    
    def _get_io_state_from_stage(self, stage: TestStage, device_name: str, timing: IOActionTiming) -> str:
        """
        Get the current state of a device at a specific timing from stage's I/O actions.
        
        Args:
            stage: TestStage to check
            device_name: Name of the I/O device
            timing: Timing point to check
        
        Returns:
            String representation of the state ("Not Set", "CLOSED", "OPEN", or value)
        """
        # Find matching I/O action
        for action in stage.io_actions:
            if action.device_name == device_name and action.timing == timing:
                if isinstance(action.value, bool):
                    return "OPEN" if action.value else "CLOSED"
                else:
                    return str(action.value)
        
        return "Not Set"
    
    def _on_io_state_changed(self, device_name: str, timing: IOActionTiming, state: str) -> None:
        """
        Handle when user changes an I/O device state.
        
        Args:
            device_name: Name of the device
            timing: Timing point (START_OF_STAGE or END_OF_STAGE)
            state: New state ("Not Set", "CLOSED", "OPEN")
        """
        row = self.stages_table.currentRow()
        if row < 0 or row >= len(self.sequence.stages):
            return
        
        stage = self.sequence.stages[row]
        
        # Remove existing action for this device/timing if it exists
        for i, action in enumerate(stage.io_actions):
            if action.device_name == device_name and action.timing == timing:
                stage.remove_io_action(i)
                break
        
        # Add new action if state is not "Not Set"
        if state != "Not Set":
            value = (state == "OPEN")  # CLOSED = False, OPEN = True
            
            new_action = IOAction(
                device_name=device_name,
                action_type=IOActionType.DIGITAL_OUTPUT,
                value=value,
                timing=timing,
                delay_seconds=0.0,
                description=f"Set {device_name} to {state} at {timing.value.replace('_', ' ')}"
            )
            
            stage.add_io_action(new_action)
            logger.debug(f"Updated {device_name} at {timing.value} to {state}")
        
        self.modified = True
        self.update_status()
    
    def _add_default_io_actions(self, stage: TestStage) -> None:
        """
        Add default I/O actions required for basic vacuum operation.
        
        Args:
            stage: TestStage to add I/O actions to
        """
        # Set default states for common devices
        defaults = {
            "inlet_valve": {"start": False, "end": False},  # CLOSED throughout
            "vent_valve": {"start": False, "end": True},  # CLOSED at start, OPEN at end
            "safety_valve": {"start": False, "end": False},  # CLOSED throughout
        }
        
        for device_name, states in defaults.items():
            if device_name in self.available_io_devices:
                # Add start state
                stage.add_io_action(IOAction(
                    device_name=device_name,
                    action_type=IOActionType.DIGITAL_OUTPUT,
                    value=states["start"],
                    timing=IOActionTiming.START_OF_STAGE,
                    delay_seconds=0.0,
                    description=f"Set {device_name} to {'OPEN' if states['start'] else 'CLOSED'} at stage start"
                ))
                
                # Add end state if different from start
                if states["end"] != states["start"]:
                    stage.add_io_action(IOAction(
                        device_name=device_name,
                        action_type=IOActionType.DIGITAL_OUTPUT,
                        value=states["end"],
                        timing=IOActionTiming.END_OF_STAGE,
                        delay_seconds=0.0,
                        description=f"Set {device_name} to {'OPEN' if states['end'] else 'CLOSED'} at stage end"
                    ))
        
        logger.info(f"Added {len(stage.io_actions)} default I/O actions to stage")

