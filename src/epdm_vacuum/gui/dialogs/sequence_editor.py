"""
Sequence Editor Dialog

Dialog for creating and editing test sequences:
- Simple mode: Basic stage creation (vacuum + hold time)
- Advanced mode: Full parameter control
- Stage management: Add, remove, reorder, duplicate
- Real-time validation and duration preview
"""

from typing import Optional, Dict, Any
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
    QComboBox,
    QGroupBox,
    QMessageBox,
    QFrame,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from ...control.sequence import TestSequence, TestStage, SequenceMode

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
                mode=SequenceMode.SIMPLE,
            )
        
        self.current_mode = self.sequence.mode
        self.modified = False
        
        self.init_ui()
        self.populate_from_sequence()
        
        logger.info(f"SequenceEditorDialog initialized for sequence: {self.sequence.name}")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Sequence Editor")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        
        # Sequence metadata section
        metadata_group = self.create_metadata_section()
        layout.addWidget(metadata_group)
        
        # Mode selector
        mode_layout = self.create_mode_selector()
        layout.addLayout(mode_layout)
        
        # Stages table
        stages_group = self.create_stages_section()
        layout.addWidget(stages_group, stretch=1)
        
        # Stage controls
        controls_layout = self.create_stage_controls()
        layout.addLayout(controls_layout)
        
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
    
    def create_mode_selector(self) -> QHBoxLayout:
        """Create mode selector buttons."""
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel("Mode:"))
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Simple (Vacuum + Hold Time)", SequenceMode.SIMPLE)
        self.mode_combo.addItem("Advanced (Full Control)", SequenceMode.ADVANCED)
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        layout.addStretch()
        
        return layout
    
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
        """Update table columns based on current mode."""
        if self.current_mode == SequenceMode.SIMPLE:
            columns = ["#", "Name", "Vacuum (bar)", "Hold Time (s)", "Est. Duration (s)"]
            self.stages_table.setColumnCount(len(columns))
            self.stages_table.setHorizontalHeaderLabels(columns)
        else:
            columns = [
                "#", "Name", "Vacuum (bar)", "Hold Time (s)", 
                "Ramp Rate (bar/s)", "Sample Rate (Hz)", 
                "Delay (s)", "Max Force (kg)", "Est. Duration (s)"
            ]
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
        
        # Set mode
        if self.sequence.mode == SequenceMode.SIMPLE:
            self.mode_combo.setCurrentIndex(0)
        else:
            self.mode_combo.setCurrentIndex(1)
        
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
        name = stage.name or f"Stage {row + 1}"
        self.stages_table.setItem(row, col, QTableWidgetItem(name))
        col += 1
        
        # Vacuum
        self.stages_table.setItem(row, col, QTableWidgetItem(f"{stage.target_vacuum_bar:.3f}"))
        col += 1
        
        # Hold time
        self.stages_table.setItem(row, col, QTableWidgetItem(f"{stage.hold_time_seconds:.1f}"))
        col += 1
        
        if self.current_mode == SequenceMode.ADVANCED:
            # Ramp rate
            ramp = stage.ramp_rate_bar_per_sec or 0.1
            self.stages_table.setItem(row, col, QTableWidgetItem(f"{ramp:.3f}"))
            col += 1
            
            # Sample rate
            sample = stage.sample_rate_hz or 10.0
            self.stages_table.setItem(row, col, QTableWidgetItem(f"{sample:.1f}"))
            col += 1
            
            # Delay
            delay = stage.delay_before_seconds or 0.0
            self.stages_table.setItem(row, col, QTableWidgetItem(f"{delay:.1f}"))
            col += 1
            
            # Max force
            max_force = stage.max_force_kg or self.config_limits.get("max_force_kg", 800.0)
            self.stages_table.setItem(row, col, QTableWidgetItem(f"{max_force:.0f}"))
            col += 1
        
        # Estimated duration
        duration = stage.get_estimated_duration()
        item = QTableWidgetItem(f"{duration:.0f}")
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)
        self.stages_table.setItem(row, col, item)
    
    def on_mode_changed(self, index: int) -> None:
        """Handle mode change."""
        new_mode = self.mode_combo.itemData(index)
        
        if new_mode != self.current_mode:
            # Confirm if stages exist
            if len(self.sequence.stages) > 0:
                reply = QMessageBox.question(
                    self,
                    "Change Mode",
                    "Changing mode will update the table view but preserve your stages. Continue?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    # Revert combo box
                    self.mode_combo.blockSignals(True)
                    if self.current_mode == SequenceMode.SIMPLE:
                        self.mode_combo.setCurrentIndex(0)
                    else:
                        self.mode_combo.setCurrentIndex(1)
                    self.mode_combo.blockSignals(False)
                    return
            
            self.current_mode = new_mode
            self.sequence.mode = new_mode
            self.update_table_columns()
            self.refresh_stages_table()
            self.modified = True
            
            logger.info(f"Changed sequence mode to {new_mode.value}")
    
    def on_add_stage(self) -> None:
        """Add a new stage to the sequence."""
        # Create default stage
        if self.current_mode == SequenceMode.SIMPLE:
            stage = TestStage(
                target_vacuum_bar=0.5,
                hold_time_seconds=30.0,
            )
        else:
            stage = TestStage(
                target_vacuum_bar=0.5,
                hold_time_seconds=30.0,
                ramp_rate_bar_per_sec=0.1,
                sample_rate_hz=10.0,
                delay_before_seconds=0.0,
            )
        
        self.sequence.add_stage(stage)
        self.refresh_stages_table()
        self.update_status()
        self.modified = True
        
        # Select new row
        self.stages_table.selectRow(len(self.sequence.stages) - 1)
        
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
    
    def on_table_item_changed(self, item: QTableWidgetItem) -> None:
        """Handle table cell edit."""
        row = item.row()
        col = item.column()
        
        if row < 0 or row >= len(self.sequence.stages):
            return
        
        stage = self.sequence.stages[row]
        
        try:
            # Determine which field was edited
            if self.current_mode == SequenceMode.SIMPLE:
                field_map = {1: "name", 2: "target_vacuum_bar", 3: "hold_time_seconds"}
            else:
                field_map = {
                    1: "name", 2: "target_vacuum_bar", 3: "hold_time_seconds",
                    4: "ramp_rate_bar_per_sec", 5: "sample_rate_hz",
                    6: "delay_before_seconds", 7: "max_force_kg"
                }
            
            if col not in field_map:
                return
            
            field = field_map[col]
            value = item.text()
            
            # Update stage
            if field == "name":
                stage.name = value
            else:
                # Convert to float
                setattr(stage, field, float(value))
            
            self.modified = True
            self.update_status()
            
            # Refresh the row to update calculated fields
            self.stages_table.blockSignals(True)
            self.populate_stage_row(row, stage)
            self.stages_table.blockSignals(False)
            
        except ValueError as e:
            logger.warning(f"Invalid value entered in table: {e}")
            # Reset the item
            self.stages_table.blockSignals(True)
            self.populate_stage_row(row, stage)
            self.stages_table.blockSignals(False)
    
    def on_metadata_changed(self) -> None:
        """Handle metadata field changes."""
        self.modified = True
    
    def validate_sequence(self) -> bool:
        """
        Validate the current sequence and show results.
        
        Returns:
            bool: True if valid
        """
        # Update sequence from UI
        self.update_sequence_from_ui()
        
        # Validate
        is_valid, errors = self.sequence.validate(self.config_limits)
        
        if is_valid:
            self.validation_label.setText("Validation: OK")
            self.validation_label.setStyleSheet("color: green; font-weight: bold;")
            QMessageBox.information(self, "Validation", "Sequence is valid!")
        else:
            self.validation_label.setText("Validation: ERRORS")
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
            
            error_msg = "Validation errors:\n\n" + "\n".join(f"• {err}" for err in errors)
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
        is_valid, errors = self.sequence.validate(self.config_limits)
        if is_valid:
            self.validation_label.setText("Validation: OK")
            self.validation_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.validation_label.setText(f"Validation: {len(errors)} errors")
            self.validation_label.setStyleSheet("color: red; font-weight: bold;")
    
    def update_sequence_from_ui(self) -> None:
        """Update sequence object from UI fields."""
        self.sequence.name = self.name_edit.text()
        self.sequence.description = self.description_edit.toPlainText()
        self.sequence.mode = self.current_mode
    
    def on_save(self) -> None:
        """Handle save button click."""
        # Update sequence from UI
        self.update_sequence_from_ui()
        
        # Validate before saving
        is_valid, errors = self.sequence.validate(self.config_limits)
        if not is_valid:
            error_msg = "Cannot save invalid sequence:\n\n" + "\n".join(f"• {err}" for err in errors)
            QMessageBox.warning(self, "Validation Errors", error_msg)
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

