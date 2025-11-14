"""
Sequence Selector Widget

Widget for selecting and managing test sequences:
- Dropdown to select from available sequences
- Buttons for New, Load, Edit, Save As
- Display current sequence info
- Quick preview tooltip
"""

from typing import Optional
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QComboBox,
    QLabel,
    QGroupBox,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal

from ...control.sequence import TestSequence
from ...control.sequence_manager import SequenceManager

logger = logging.getLogger(__name__)


class SequenceSelectorWidget(QWidget):
    """
    Widget for selecting and managing test sequences.
    
    Provides UI for loading, creating, editing, and managing
    test sequences with file operations.
    """
    
    # Signals
    sequence_changed = pyqtSignal(TestSequence)  # Emitted when sequence changes
    edit_requested = pyqtSignal(TestSequence)  # Emitted when edit is requested
    new_requested = pyqtSignal()  # Emitted when new sequence is requested
    
    def __init__(self, sequence_manager: Optional[SequenceManager] = None, parent=None):
        """
        Initialize the sequence selector widget.
        
        Args:
            sequence_manager: SequenceManager instance
            parent: Parent widget
        """
        super().__init__(parent)
        
        self.sequence_manager = sequence_manager
        self.current_sequence: Optional[TestSequence] = None
        
        self.init_ui()
        self.refresh_sequence_list()
        
        logger.info("SequenceSelectorWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create group box
        group = QGroupBox("Test Sequence")
        group_layout = QVBoxLayout()
        
        # Sequence selection row
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Sequence:"))
        
        self.sequence_combo = QComboBox()
        self.sequence_combo.setMinimumWidth(200)
        self.sequence_combo.currentIndexChanged.connect(self.on_sequence_selected)
        select_layout.addWidget(self.sequence_combo, stretch=1)
        
        group_layout.addLayout(select_layout)
        
        # Info display row
        self.info_label = QLabel("No sequence loaded")
        self.info_label.setStyleSheet("color: gray; font-style: italic;")
        group_layout.addWidget(self.info_label)
        
        # Action buttons row
        buttons_layout = QHBoxLayout()
        
        self.new_btn = QPushButton("New")
        self.new_btn.setToolTip("Create a new sequence")
        self.new_btn.clicked.connect(self.on_new_sequence)
        buttons_layout.addWidget(self.new_btn)
        
        self.load_btn = QPushButton("Load...")
        self.load_btn.setToolTip("Load a sequence from file")
        self.load_btn.clicked.connect(self.on_load_sequence)
        buttons_layout.addWidget(self.load_btn)
        
        self.edit_btn = QPushButton("Edit")
        self.edit_btn.setToolTip("Edit the current sequence")
        self.edit_btn.clicked.connect(self.on_edit_sequence)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)
        
        self.save_as_btn = QPushButton("Save As...")
        self.save_as_btn.setToolTip("Save current sequence with a new name")
        self.save_as_btn.clicked.connect(self.on_save_as)
        self.save_as_btn.setEnabled(False)
        buttons_layout.addWidget(self.save_as_btn)
        
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setToolTip("Refresh sequence list")
        self.refresh_btn.clicked.connect(self.refresh_sequence_list)
        buttons_layout.addWidget(self.refresh_btn)
        
        buttons_layout.addStretch()
        
        group_layout.addLayout(buttons_layout)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def set_sequence_manager(self, manager: SequenceManager) -> None:
        """
        Set the sequence manager.
        
        Args:
            manager: SequenceManager instance
        """
        self.sequence_manager = manager
        self.refresh_sequence_list()
        logger.info("Sequence manager set")
    
    def refresh_sequence_list(self) -> None:
        """Refresh the list of available sequences."""
        if not self.sequence_manager:
            logger.warning("No sequence manager available")
            return
        
        # Block signals during refresh
        self.sequence_combo.blockSignals(True)
        
        # Save current selection
        current_text = self.sequence_combo.currentText()
        
        # Clear and repopulate
        self.sequence_combo.clear()
        self.sequence_combo.addItem("-- Select Sequence --", None)
        
        # Get available sequences
        sequence_names = self.sequence_manager.list_sequences()
        
        for name in sequence_names:
            # Get sequence info for tooltip
            info = self.sequence_manager.get_sequence_info(name)
            if info:
                tooltip = f"{info['name']}\n"
                tooltip += f"Stages: {info['stage_count']}\n"
                if info['description']:
                    tooltip += f"Description: {info['description']}"
                
                self.sequence_combo.addItem(name, name)
                self.sequence_combo.setItemData(
                    self.sequence_combo.count() - 1,
                    tooltip,
                    Qt.ToolTipRole
                )
        
        # Restore selection if possible
        if current_text:
            index = self.sequence_combo.findText(current_text)
            if index >= 0:
                self.sequence_combo.setCurrentIndex(index)
        
        # Re-enable signals
        self.sequence_combo.blockSignals(False)
        
        logger.info(f"Refreshed sequence list: {len(sequence_names)} sequences found")
    
    def on_sequence_selected(self, index: int) -> None:
        """Handle sequence selection from combo box."""
        if index <= 0:
            # No selection or placeholder
            self.current_sequence = None
            self.update_info_display()
            self.edit_btn.setEnabled(False)
            self.save_as_btn.setEnabled(False)
            return
        
        sequence_name = self.sequence_combo.itemData(index)
        if not sequence_name or not self.sequence_manager:
            return
        
        # Load the sequence
        sequence = self.sequence_manager.load_sequence(sequence_name)
        
        if sequence:
            self.current_sequence = sequence
            self.update_info_display()
            self.edit_btn.setEnabled(True)
            self.save_as_btn.setEnabled(True)
            
            # Emit signal
            self.sequence_changed.emit(sequence)
            
            logger.info(f"Selected sequence: {sequence.name}")
        else:
            QMessageBox.warning(
                self,
                "Load Error",
                f"Failed to load sequence '{sequence_name}'"
            )
    
    def on_new_sequence(self) -> None:
        """Handle new sequence request."""
        # Get name from user
        name, ok = QInputDialog.getText(
            self,
            "New Sequence",
            "Enter sequence name:",
            text="New Sequence"
        )
        
        if ok and name:
            # Check if already exists
            if self.sequence_manager and self.sequence_manager.sequence_exists(name):
                reply = QMessageBox.question(
                    self,
                    "Sequence Exists",
                    f"Sequence '{name}' already exists. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # Create new sequence
            if self.sequence_manager:
                sequence = self.sequence_manager.create_default_sequence(name)
            else:
                from ...control.sequence import TestSequence
                sequence = TestSequence(name=name)
            
            self.current_sequence = sequence
            
            # Emit signal to open editor
            self.new_requested.emit()
            
            logger.info(f"Created new sequence: {name}")
    
    def on_load_sequence(self) -> None:
        """Handle load sequence from file."""
        if not self.sequence_manager:
            QMessageBox.warning(self, "Error", "No sequence manager available")
            return
        
        # Open file dialog
        sequences_dir = str(self.sequence_manager.sequences_dir)
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Sequence",
            sequences_dir,
            "YAML Files (*.yaml *.yml);;All Files (*)"
        )
        
        if filename:
            # Extract just the filename
            from pathlib import Path
            name = Path(filename).stem
            
            # Load sequence
            sequence = self.sequence_manager.load_sequence(name)
            
            if sequence:
                self.current_sequence = sequence
                self.refresh_sequence_list()
                
                # Select the loaded sequence
                index = self.sequence_combo.findText(name)
                if index >= 0:
                    self.sequence_combo.setCurrentIndex(index)
                
                logger.info(f"Loaded sequence from file: {filename}")
            else:
                QMessageBox.warning(
                    self,
                    "Load Error",
                    f"Failed to load sequence from '{filename}'"
                )
    
    def on_edit_sequence(self) -> None:
        """Handle edit sequence request."""
        if self.current_sequence:
            self.edit_requested.emit(self.current_sequence)
            logger.info(f"Edit requested for sequence: {self.current_sequence.name}")
    
    def on_save_as(self) -> None:
        """Handle save as request."""
        if not self.current_sequence or not self.sequence_manager:
            return
        
        # Get new name from user
        name, ok = QInputDialog.getText(
            self,
            "Save As",
            "Enter new sequence name:",
            text=self.current_sequence.name
        )
        
        if ok and name:
            # Check if already exists
            if self.sequence_manager.sequence_exists(name):
                reply = QMessageBox.question(
                    self,
                    "Overwrite",
                    f"Sequence '{name}' already exists. Overwrite?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
            
            # Save with new name
            old_name = self.current_sequence.name
            self.current_sequence.name = name
            
            success = self.sequence_manager.save_sequence(self.current_sequence)
            
            if success:
                QMessageBox.information(
                    self,
                    "Saved",
                    f"Sequence saved as '{name}'"
                )
                self.refresh_sequence_list()
                
                # Select the new sequence
                index = self.sequence_combo.findText(name)
                if index >= 0:
                    self.sequence_combo.setCurrentIndex(index)
                
                logger.info(f"Sequence saved as: {name}")
            else:
                # Revert name on failure
                self.current_sequence.name = old_name
                QMessageBox.warning(
                    self,
                    "Save Error",
                    f"Failed to save sequence as '{name}'"
                )
    
    def update_info_display(self) -> None:
        """Update the sequence info display."""
        if self.current_sequence:
            info = f"{self.current_sequence.get_stage_count()} stages, "
            info += f"~{self.current_sequence.get_estimated_duration():.0f}s total"
            self.info_label.setText(info)
            self.info_label.setStyleSheet("color: black;")
        else:
            self.info_label.setText("No sequence loaded")
            self.info_label.setStyleSheet("color: gray; font-style: italic;")
    
    def get_current_sequence(self) -> Optional[TestSequence]:
        """
        Get the currently selected sequence.
        
        Returns:
            TestSequence or None
        """
        return self.current_sequence
    
    def set_current_sequence(self, sequence: TestSequence) -> None:
        """
        Set the current sequence programmatically.
        
        Args:
            sequence: TestSequence to set as current
        """
        self.current_sequence = sequence
        self.update_info_display()
        self.edit_btn.setEnabled(True)
        self.save_as_btn.setEnabled(True)
        
        # Try to find and select in combo box
        if sequence.name:
            index = self.sequence_combo.findText(sequence.name)
            if index >= 0:
                self.sequence_combo.blockSignals(True)
                self.sequence_combo.setCurrentIndex(index)
                self.sequence_combo.blockSignals(False)
        
        logger.info(f"Current sequence set to: {sequence.name}")

