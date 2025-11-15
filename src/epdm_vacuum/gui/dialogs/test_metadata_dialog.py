"""
Test Metadata Dialog

Dialog for capturing test metadata before starting a test:
- Test name
- Operator name
- Material information
- Test targets (force, vacuum, time)
- Notes
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QDoubleSpinBox,
    QSpinBox,
    QPushButton,
    QGroupBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QDateEdit,
    QTimeEdit,
)
from PyQt5.QtCore import Qt, pyqtSignal, QDate, QTime

logger = logging.getLogger(__name__)


class TestMetadataDialog(QDialog):
    """
    Dialog for capturing test metadata.
    
    Collects information about the test, operator, material,
    and test targets before starting a test run.
    """
    
    metadata_accepted = pyqtSignal(dict, str)  # (metadata, save_path)
    
    def __init__(self, parent=None):
        """Initialize the metadata dialog."""
        super().__init__(parent)
        
        self.metadata: Dict[str, Any] = {}
        self.save_path: str = ""
        
        self.init_ui()
        self.set_default_values()
        
        logger.info("TestMetadataDialog initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Test Metadata")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        # Create form sections
        self.create_basic_info_section(layout)
        self.create_material_section(layout)
        self.create_targets_section(layout)
        self.create_notes_section(layout)
        self.create_file_location_section(layout)
        
        # Add buttons
        self.create_buttons(layout)
    
    def create_basic_info_section(self, parent_layout: QVBoxLayout) -> None:
        """Create basic information section."""
        group = QGroupBox("Test Information")
        form = QFormLayout()
        
        # Test name
        self.test_name_edit = QLineEdit()
        self.test_name_edit.setPlaceholderText("e.g., EPDM_Seal_Test_001")
        form.addRow("Test Name*:", self.test_name_edit)
        
        # Operator name
        self.operator_edit = QLineEdit()
        self.operator_edit.setPlaceholderText("e.g., John Smith")
        form.addRow("Operator*:", self.operator_edit)
        
        # Date picker
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat("yyyy-MM-dd")
        self.date_edit.setDate(QDate.currentDate())
        form.addRow("Date*:", self.date_edit)
        
        # Time picker
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime.currentTime())
        form.addRow("Time*:", self.time_edit)
        
        # Test ID (auto-generated)
        self.test_id_edit = QLineEdit()
        self.test_id_edit.setReadOnly(True)
        form.addRow("Test ID:", self.test_id_edit)
        
        group.setLayout(form)
        parent_layout.addWidget(group)
    
    def create_material_section(self, parent_layout: QVBoxLayout) -> None:
        """Create material information section."""
        group = QGroupBox("Material Information")
        form = QFormLayout()
        
        # Material type
        self.material_edit = QLineEdit()
        self.material_edit.setPlaceholderText("e.g., EPDM 70 Shore A")
        form.addRow("Material:", self.material_edit)
        
        # Sample ID
        self.sample_id_edit = QLineEdit()
        self.sample_id_edit.setPlaceholderText("e.g., SAMPLE-2025-001")
        form.addRow("Sample ID:", self.sample_id_edit)
        
        # Batch/Lot number
        self.batch_edit = QLineEdit()
        self.batch_edit.setPlaceholderText("e.g., LOT-ABC123")
        form.addRow("Batch/Lot:", self.batch_edit)
        
        group.setLayout(form)
        parent_layout.addWidget(group)
    
    def create_targets_section(self, parent_layout: QVBoxLayout) -> None:
        """Create test targets section."""
        group = QGroupBox("Test Targets (Optional)")
        form = QFormLayout()
        
        # Target vacuum
        self.target_vacuum_spin = QDoubleSpinBox()
        self.target_vacuum_spin.setRange(0.0, 1.0)
        self.target_vacuum_spin.setDecimals(3)
        self.target_vacuum_spin.setSuffix(" bar")
        self.target_vacuum_spin.setValue(0.0)
        self.target_vacuum_spin.setSpecialValueText("Not specified")
        form.addRow("Target Vacuum:", self.target_vacuum_spin)
        
        # Target force
        self.target_force_spin = QDoubleSpinBox()
        self.target_force_spin.setRange(0.0, 1000.0)
        self.target_force_spin.setDecimals(1)
        self.target_force_spin.setSuffix(" kg")
        self.target_force_spin.setValue(0.0)
        self.target_force_spin.setSpecialValueText("Not specified")
        form.addRow("Target Force:", self.target_force_spin)
        
        # Target time
        self.target_time_spin = QSpinBox()
        self.target_time_spin.setRange(0, 86400)
        self.target_time_spin.setSuffix(" seconds")
        self.target_time_spin.setValue(0)
        self.target_time_spin.setSpecialValueText("Not specified")
        form.addRow("Target Time:", self.target_time_spin)
        
        group.setLayout(form)
        parent_layout.addWidget(group)
    
    def create_notes_section(self, parent_layout: QVBoxLayout) -> None:
        """Create notes section."""
        group = QGroupBox("Notes")
        layout = QVBoxLayout()
        
        self.notes_edit = QTextEdit()
        self.notes_edit.setPlaceholderText("Additional notes or observations...")
        self.notes_edit.setMaximumHeight(100)
        layout.addWidget(self.notes_edit)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_file_location_section(self, parent_layout: QVBoxLayout) -> None:
        """Create file save location section."""
        group = QGroupBox("Data File Location")
        layout = QVBoxLayout()
        
        # File path display and browse button
        path_layout = QHBoxLayout()
        self.file_path_label = QLabel("No file selected")
        self.file_path_label.setWordWrap(True)
        path_layout.addWidget(self.file_path_label, stretch=1)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_save_location)
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        # Help text
        help_label = QLabel("Select where to save the test data CSV file.")
        help_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(help_label)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def create_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Create dialog buttons."""
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("Start Test")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept_and_validate)
        button_layout.addWidget(ok_btn)
        
        parent_layout.addLayout(button_layout)
    
    def set_default_values(self) -> None:
        """Set default values for fields."""
        # Date and time are already set to current in create_basic_info_section
        now = datetime.now()
        
        # Generate test ID from timestamp
        test_id = now.strftime("TEST_%Y%m%d_%H%M%S")
        self.test_id_edit.setText(test_id)
        
        # Set default save location
        from pathlib import Path
        default_dir = Path.cwd() / "data"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_file = default_dir / f"{test_id}.csv"
        self.save_path = str(default_file)
        self.file_path_label.setText(str(default_file))
    
    def browse_save_location(self) -> None:
        """Open file dialog to select save location."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Select Save Location",
            self.save_path,
            "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if filename:
            # Ensure .csv extension
            if not filename.lower().endswith('.csv'):
                filename += '.csv'
            
            self.save_path = filename
            self.file_path_label.setText(filename)
            logger.info(f"Save location set to: {filename}")
    
    def accept_and_validate(self) -> None:
        """Validate inputs and accept dialog."""
        # Validate required fields
        if not self.test_name_edit.text().strip():
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter a test name."
            )
            self.test_name_edit.setFocus()
            return
        
        if not self.operator_edit.text().strip():
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter an operator name."
            )
            self.operator_edit.setFocus()
            return
        
        if not self.save_path:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please select a save location for the data file."
            )
            return
        
        # Collect metadata
        self.metadata = self.collect_metadata()
        
        # Emit signal with metadata and save path
        self.metadata_accepted.emit(self.metadata, self.save_path)
        
        # Accept dialog
        self.accept()
    
    def collect_metadata(self) -> Dict[str, Any]:
        """
        Collect all metadata from form fields.
        
        Returns:
            Dict containing all metadata
        """
        # Combine date and time
        date_str = self.date_edit.date().toString("yyyy-MM-dd")
        time_str = self.time_edit.time().toString("HH:mm:ss")
        datetime_str = f"{date_str} {time_str}"
        
        metadata = {
            # Basic info
            "test_name": self.test_name_edit.text().strip(),
            "operator": self.operator_edit.text().strip(),
            "date": datetime_str,
            "test_id": self.test_id_edit.text(),
            
            # Material info
            "material": self.material_edit.text().strip(),
            "sample_id": self.sample_id_edit.text().strip(),
            "batch_lot": self.batch_edit.text().strip(),
            
            # Test targets (only include if non-zero)
            "target_vacuum_bar": self.target_vacuum_spin.value() if self.target_vacuum_spin.value() > 0 else None,
            "target_force_kg": self.target_force_spin.value() if self.target_force_spin.value() > 0 else None,
            "target_time_seconds": self.target_time_spin.value() if self.target_time_spin.value() > 0 else None,
            
            # Notes
            "notes": self.notes_edit.toPlainText().strip(),
        }
        
        # Remove empty optional fields
        metadata = {k: v for k, v in metadata.items() if v not in (None, "", [])}
        
        logger.info(f"Collected metadata: {metadata}")
        return metadata
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get the collected metadata.
        
        Returns:
            Dict containing metadata
        """
        return self.metadata
    
    def get_save_path(self) -> str:
        """
        Get the selected save path.
        
        Returns:
            str: Path to save data file
        """
        return self.save_path

