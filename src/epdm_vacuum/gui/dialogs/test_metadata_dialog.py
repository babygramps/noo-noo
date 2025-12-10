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
    QCheckBox,
    QScrollArea,
    QSizePolicy,
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
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)
        
        layout = QVBoxLayout(self)
        
        # Create form sections
        self.create_basic_info_section(layout)
        self.create_material_section(layout)
        self.create_targets_section(layout)
        self.create_notes_section(layout)
        self.create_test_description_section(layout)
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
        self.test_name_edit.textChanged.connect(self.update_test_id)
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
        self.date_edit.dateChanged.connect(self.update_test_id)
        form.addRow("Date*:", self.date_edit)
        
        # Time picker
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("HH:mm:ss")
        self.time_edit.setTime(QTime.currentTime())
        self.time_edit.timeChanged.connect(self.update_test_id)
        form.addRow("Time*:", self.time_edit)
        
        # Test ID (auto-generated from test name + date + time)
        self.test_id_edit = QLineEdit()
        self.test_id_edit.setReadOnly(True)
        self.test_id_edit.setStyleSheet("background-color: #f0f0f0;")
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
    
    def create_test_description_section(self, parent_layout: QVBoxLayout) -> None:
        """Create test description section with checkbox and editable text."""
        group = QGroupBox("Test Description for Data Analysis")
        layout = QVBoxLayout()
        
        # Checkbox to include description
        self.include_description_checkbox = QCheckBox("Include test description in metadata (helps LLM/AI analyze the data)")
        self.include_description_checkbox.setChecked(True)
        self.include_description_checkbox.stateChanged.connect(self._on_description_checkbox_changed)
        layout.addWidget(self.include_description_checkbox)
        
        # Help text
        help_label = QLabel("This description explains how the test works and how to interpret the data. "
                           "It will be saved in the JSON metadata file alongside the CSV data.")
        help_label.setStyleSheet("color: #666; font-size: 9pt; margin-bottom: 8px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        # Editable test description
        self.test_description_edit = QTextEdit()
        self.test_description_edit.setPlaceholderText("Test description will appear here...")
        self.test_description_edit.setMinimumHeight(150)
        self.test_description_edit.setMaximumHeight(200)
        self.test_description_edit.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 9pt;
                background-color: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.test_description_edit)
        
        # Populate with default description
        self.test_description_edit.setPlainText(self._get_default_test_description())
        
        # Reset button
        reset_btn = QPushButton("Reset to Default")
        reset_btn.setMaximumWidth(120)
        reset_btn.clicked.connect(self._reset_test_description)
        layout.addWidget(reset_btn)
        
        group.setLayout(layout)
        parent_layout.addWidget(group)
    
    def _on_description_checkbox_changed(self, state: int) -> None:
        """Handle checkbox state change."""
        enabled = state == Qt.Checked
        self.test_description_edit.setEnabled(enabled)
        if enabled:
            self.test_description_edit.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 9pt;
                    background-color: #f8f9fa;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
        else:
            self.test_description_edit.setStyleSheet("""
                QTextEdit {
                    font-family: 'Consolas', 'Monaco', monospace;
                    font-size: 9pt;
                    background-color: #e9ecef;
                    color: #6c757d;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                }
            """)
    
    def _reset_test_description(self) -> None:
        """Reset test description to default."""
        self.test_description_edit.setPlainText(self._get_default_test_description())
    
    def _get_default_test_description(self) -> str:
        """Get the default test description text."""
        return """## EPDM Gasket Vacuum Seal Test - Operation Description

### Purpose
This test evaluates the vacuum sealing performance of EPDM gaskets by:
1. Drawing vacuum in a sealed test chamber containing the gasket
2. Monitoring vacuum level and force over time
3. Detecting any vacuum loss (leak) through the gasket seal

### Test Hardware Operation

**Vacuum System:**
- A vacuum pump creates negative pressure (vacuum) in the test chamber
- A vacuum isolation valve (vacuum_valve) connects/disconnects the pump from the chamber
- A vent valve (vent_valve) allows the chamber to return to atmospheric pressure

**Measurement System:**
- Pressure sensor measures chamber pressure (negative PSIG = vacuum)
- Load cells measure compression force on the gasket (in kg)

### Typical Test Sequence Flow

**Stage 1 - Evacuation:**
- Vent valve CLOSES (seals chamber from atmosphere)
- Vacuum valve OPENS (connects pump to chamber)
- Pump runs in CONTINUOUS mode
- Vacuum increases (pressure becomes more negative)
- Stage completes when target vacuum is reached OR time limit expires

**Stage 2 - Hold/Leak Check:**
- Vacuum valve CLOSES (isolates chamber from pump)
- Pump turns OFF
- Chamber remains sealed
- Any vacuum loss indicates a leak through the gasket
- Monitor vacuum_bar - it should remain stable if seal is good
- Leak rate = change in vacuum over time

**Stage 3 - Vent:**
- Vent valve OPENS (allows air into chamber)
- Chamber returns to atmospheric pressure (vacuum_bar → 0)
- Prepares for next cycle or test completion

### How to Analyze the Data

**For Seal Quality Assessment:**
1. Find the "Hold" stage data (pump_mode = "off", both valves closed)
2. Calculate vacuum change: initial_vacuum - final_vacuum
3. Calculate leak rate: vacuum_change / hold_time (mbar/min or bar/min)
4. Lower leak rate = better seal

**For Evacuation Performance:**
1. Find the "Evacuate" stage data (pump_mode = "continuous")
2. Check time to reach target vacuum (evacuation speed)
3. Monitor force during evacuation (gasket compression)

**Key Indicators:**
- vacuum_bar increasing during evacuation = system working correctly
- vacuum_bar stable during hold = good seal
- vacuum_bar decreasing during hold = leak detected
- Higher force values = more gasket compression

**Multi-Cycle Tests:**
- Tests may repeat the evacuate-hold-vent sequence multiple times
- Compare leak rates across cycles to assess seal degradation
- First cycle may show different behavior as gasket "seats"

**Data Quality Notes:**
- First few seconds after valve changes may show transient behavior
- Ignore data points during stage transitions
- Focus on steady-state portions of each stage for analysis"""
    
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
        # Test ID will be generated when test name is entered
        
        # Set default save location (will be updated when test ID changes)
        from pathlib import Path
        default_dir = Path.cwd() / "data"
        default_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate initial test ID
        self.update_test_id()
    
    def update_test_id(self) -> None:
        """Update test ID based on test name, date, and time."""
        # Get test name (sanitized for filename use)
        test_name = self.test_name_edit.text().strip()
        if not test_name:
            test_name = "UNNAMED_TEST"
        
        # Sanitize test name for use in filename
        # Replace spaces and special characters with underscores
        import re
        test_name_clean = re.sub(r'[^\w\-]', '_', test_name)
        
        # Get date and time
        date_str = self.date_edit.date().toString("yyyyMMdd")
        time_str = self.time_edit.time().toString("HHmmss")
        
        # Create test ID: TestName_YYYYMMDD_HHMMSS
        test_id = f"{test_name_clean}_{date_str}_{time_str}"
        
        # Update test ID field
        self.test_id_edit.setText(test_id)
        
        # Update default save location if not manually set
        from pathlib import Path
        default_dir = Path.cwd() / "data"
        default_dir.mkdir(parents=True, exist_ok=True)
        default_file = default_dir / f"{test_id}.csv"
        
        # Only update save path if it hasn't been manually browsed
        if not self.save_path or self.save_path.startswith(str(default_dir)):
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
        
        # Include test description if checkbox is checked
        if self.include_description_checkbox.isChecked():
            description = self.test_description_edit.toPlainText().strip()
            if description:
                metadata["user_test_description"] = description
                metadata["include_test_description"] = True
        else:
            metadata["include_test_description"] = False
        
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
    
    def populate_from_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Populate dialog fields from existing metadata.
        
        Args:
            metadata: Dictionary containing metadata to populate
        """
        # Basic info
        if "test_name" in metadata:
            self.test_name_edit.setText(metadata["test_name"])
        
        if "operator" in metadata:
            self.operator_edit.setText(metadata["operator"])
        
        if "date" in metadata:
            # Parse date/time string
            try:
                from datetime import datetime
                dt = datetime.strptime(metadata["date"], "%Y-%m-%d %H:%M:%S")
                self.date_edit.setDate(QDate(dt.year, dt.month, dt.day))
                self.time_edit.setTime(QTime(dt.hour, dt.minute, dt.second))
            except Exception as e:
                logger.warning(f"Failed to parse date '{metadata['date']}': {e}")
        
        # Material info
        if "material" in metadata:
            self.material_edit.setText(metadata["material"])
        
        if "sample_id" in metadata:
            self.sample_id_edit.setText(metadata["sample_id"])
        
        if "batch_lot" in metadata:
            self.batch_edit.setText(metadata["batch_lot"])
        
        # Test targets
        if "target_vacuum_bar" in metadata:
            self.target_vacuum_spin.setValue(float(metadata["target_vacuum_bar"]))
        
        if "target_force_kg" in metadata:
            self.target_force_spin.setValue(float(metadata["target_force_kg"]))
        
        if "target_time_seconds" in metadata:
            self.target_time_spin.setValue(int(metadata["target_time_seconds"]))
        
        # Notes
        if "notes" in metadata:
            self.notes_edit.setPlainText(metadata["notes"])
        
        # Test description
        if "include_test_description" in metadata:
            self.include_description_checkbox.setChecked(metadata["include_test_description"])
        
        if "user_test_description" in metadata:
            self.test_description_edit.setPlainText(metadata["user_test_description"])
        
        # Update test ID based on populated values
        self.update_test_id()
        
        logger.info("Populated metadata dialog from existing metadata")

