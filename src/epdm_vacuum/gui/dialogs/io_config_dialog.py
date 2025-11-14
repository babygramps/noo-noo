"""
IO Configuration Dialog

Dialog for configuring IO devices (valves, relays, sensors) with:
- Add/Edit/Delete devices
- Configure names, descriptions, channels, types
- Save to hardware_config.yaml
- Support for WidgetLords PI-SPI-DIN modules
"""

from typing import Optional, List, Dict, Any
import logging
from pathlib import Path
import yaml

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QComboBox,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QLabel,
    QGroupBox,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

logger = logging.getLogger(__name__)


class IOConfigDialog(QDialog):
    """
    Dialog for configuring IO devices.
    
    Allows users to add, edit, and remove IO devices that will be
    saved to hardware_config.yaml and used during test execution.
    """
    
    # Signal emitted when configuration is saved
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the IO configuration dialog."""
        super().__init__(parent)
        
        self.config_file_path = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        self.io_devices: List[Dict[str, Any]] = []
        self.current_edit_index: Optional[int] = None
        
        self.init_ui()
        self.load_config()
        
        logger.info("IOConfigDialog initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("IO Device Configuration")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("IO Device Configuration")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Configure digital and analog IO devices (valves, relays, sensors)")
        subtitle.setStyleSheet("font-size: 10pt; color: #666; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Hardware info banner
        hw_banner = self.create_hardware_banner()
        layout.addWidget(hw_banner)
        
        # Main content area with table and form side-by-side
        content_layout = QHBoxLayout()
        
        # Left side: Device list/table
        left_panel = self.create_device_list_panel()
        content_layout.addWidget(left_panel, stretch=1)
        
        # Right side: Edit form
        right_panel = self.create_edit_form_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        layout.addLayout(content_layout)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_hardware_banner(self) -> QGroupBox:
        """Create hardware information banner."""
        banner = QGroupBox("Hardware: WidgetLords PI-SPI-DIN Modules")
        banner.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #E3F2FD;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        layout = QVBoxLayout()
        
        info_text = QLabel(
            "• PI-SPI-DIN-4KO: 4× Relay Outputs (Channels 0-3)\n"
            "• PI-SPI-DIN-8AI: 8× Analog Inputs (Channels 0-7)\n"
            "• PI-SPI-DIN-8DI: 8× Digital Inputs (Channels 0-7)\n"
            "• Configure devices below to match your hardware setup"
        )
        info_text.setStyleSheet("font-size: 9pt; color: #1976D2; font-weight: normal;")
        layout.addWidget(info_text)
        
        banner.setLayout(layout)
        return banner
    
    def create_device_list_panel(self) -> QGroupBox:
        """Create the device list panel with table."""
        panel = QGroupBox("Configured Devices")
        layout = QVBoxLayout()
        
        # Device table
        self.device_table = QTableWidget()
        self.device_table.setColumnCount(5)
        self.device_table.setHorizontalHeaderLabels(["Name", "Type", "Channel", "I/O", "Description"])
        self.device_table.horizontalHeader().setStretchLastSection(True)
        self.device_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.device_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.device_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.device_table.itemSelectionChanged.connect(self.on_device_selected)
        
        # Set column widths
        header = self.device_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.Stretch)
        
        layout.addWidget(self.device_table)
        
        # Buttons below table
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Device")
        self.add_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 6px 12px;")
        self.add_btn.clicked.connect(self.add_device)
        btn_layout.addWidget(self.add_btn)
        
        self.remove_btn = QPushButton("Remove")
        self.remove_btn.setEnabled(False)
        self.remove_btn.clicked.connect(self.remove_device)
        btn_layout.addWidget(self.remove_btn)
        
        self.duplicate_btn = QPushButton("Duplicate")
        self.duplicate_btn.setEnabled(False)
        self.duplicate_btn.clicked.connect(self.duplicate_device)
        btn_layout.addWidget(self.duplicate_btn)
        
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        panel.setLayout(layout)
        return panel
    
    def create_edit_form_panel(self) -> QGroupBox:
        """Create the edit form panel."""
        panel = QGroupBox("Device Properties")
        layout = QVBoxLayout()
        
        form = QFormLayout()
        form.setSpacing(8)
        
        # Device Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., vacuum_pump, vent_valve")
        self.name_edit.textChanged.connect(self.on_form_changed)
        form.addRow("Device Name:", self.name_edit)
        
        # Description
        self.description_edit = QLineEdit()
        self.description_edit.setPlaceholderText("e.g., Main vacuum pump relay")
        self.description_edit.textChanged.connect(self.on_form_changed)
        form.addRow("Description:", self.description_edit)
        
        # Type (Digital/Analog)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["Digital Output", "Digital Input", "Analog Output", "Analog Input"])
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form.addRow("Device Type:", self.type_combo)
        
        # Channel number
        self.channel_spin = QSpinBox()
        self.channel_spin.setRange(0, 15)
        self.channel_spin.setValue(0)
        self.channel_spin.valueChanged.connect(self.on_form_changed)
        form.addRow("Channel:", self.channel_spin)
        
        # Default state (for outputs only)
        self.default_state_check = QCheckBox("ON/OPEN by default")
        self.default_state_check.stateChanged.connect(self.on_form_changed)
        form.addRow("Default State:", self.default_state_check)
        
        # Analog-specific settings
        self.analog_settings_group = QGroupBox("Analog Settings")
        analog_layout = QFormLayout()
        
        self.min_value_spin = QSpinBox()
        self.min_value_spin.setRange(-1000, 1000)
        self.min_value_spin.setValue(0)
        self.min_value_spin.setSuffix(" V")
        analog_layout.addRow("Min Value:", self.min_value_spin)
        
        self.max_value_spin = QSpinBox()
        self.max_value_spin.setRange(-1000, 1000)
        self.max_value_spin.setValue(10)
        self.max_value_spin.setSuffix(" V")
        analog_layout.addRow("Max Value:", self.max_value_spin)
        
        self.analog_settings_group.setLayout(analog_layout)
        self.analog_settings_group.setVisible(False)
        form.addRow(self.analog_settings_group)
        
        layout.addLayout(form)
        
        # Update button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.clear_form_btn = QPushButton("Clear Form")
        self.clear_form_btn.clicked.connect(self.clear_form)
        btn_layout.addWidget(self.clear_form_btn)
        
        self.update_btn = QPushButton("Update Device")
        self.update_btn.setEnabled(False)
        self.update_btn.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 6px 12px;")
        self.update_btn.clicked.connect(self.update_device)
        btn_layout.addWidget(self.update_btn)
        
        layout.addLayout(btn_layout)
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def on_type_changed(self, type_text: str) -> None:
        """Handle device type change."""
        # Show/hide analog settings
        is_analog = "Analog" in type_text
        self.analog_settings_group.setVisible(is_analog)
        
        # Show/hide default state for outputs only
        is_output = "Output" in type_text
        self.default_state_check.setVisible(is_output)
        
        self.on_form_changed()
    
    def on_form_changed(self) -> None:
        """Handle form field changes."""
        # Enable update button if name is not empty
        has_name = len(self.name_edit.text().strip()) > 0
        self.update_btn.setEnabled(has_name)
    
    def load_config(self) -> None:
        """Load IO devices from hardware_config.yaml."""
        try:
            if not self.config_file_path.exists():
                logger.warning(f"Config file not found: {self.config_file_path}")
                return
            
            with open(self.config_file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            self.io_devices.clear()
            
            # Load digital outputs
            digital_outputs = config.get('io_devices', {}).get('digital_outputs', [])
            for device in digital_outputs:
                device['io_type'] = 'output'
                device['device_type'] = 'digital'
                self.io_devices.append(device)
            
            # Load digital inputs
            digital_inputs = config.get('io_devices', {}).get('digital_inputs', [])
            for device in digital_inputs:
                device['io_type'] = 'input'
                device['device_type'] = 'digital'
                self.io_devices.append(device)
            
            # Load analog outputs
            analog_outputs = config.get('io_devices', {}).get('analog_outputs', [])
            for device in analog_outputs:
                device['io_type'] = 'output'
                device['device_type'] = 'analog'
                self.io_devices.append(device)
            
            # Load analog inputs
            analog_inputs = config.get('io_devices', {}).get('analog_inputs', [])
            for device in analog_inputs:
                device['io_type'] = 'input'
                device['device_type'] = 'analog'
                self.io_devices.append(device)
            
            self.refresh_table()
            logger.info(f"Loaded {len(self.io_devices)} IO devices from config")
            
        except Exception as e:
            logger.error(f"Error loading IO config: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", f"Failed to load configuration:\n{e}")
    
    def refresh_table(self) -> None:
        """Refresh the device table with current devices."""
        self.device_table.setRowCount(len(self.io_devices))
        
        for row, device in enumerate(self.io_devices):
            # Name
            self.device_table.setItem(row, 0, QTableWidgetItem(device.get('name', '')))
            
            # Type
            device_type = device.get('device_type', 'digital')
            type_str = "Digital" if device_type == "digital" else "Analog"
            self.device_table.setItem(row, 1, QTableWidgetItem(type_str))
            
            # Channel
            channel = device.get('channel', 0)
            self.device_table.setItem(row, 2, QTableWidgetItem(str(channel)))
            
            # I/O direction
            io_type = device.get('io_type', 'output')
            io_str = "Output" if io_type == "output" else "Input"
            self.device_table.setItem(row, 3, QTableWidgetItem(io_str))
            
            # Description
            desc = device.get('description', '')
            self.device_table.setItem(row, 4, QTableWidgetItem(desc))
    
    def on_device_selected(self) -> None:
        """Handle device selection in table."""
        selected_rows = self.device_table.selectionModel().selectedRows()
        
        if selected_rows:
            self.remove_btn.setEnabled(True)
            self.duplicate_btn.setEnabled(True)
            
            # Load device into form
            row = selected_rows[0].row()
            self.current_edit_index = row
            self.load_device_into_form(self.io_devices[row])
        else:
            self.remove_btn.setEnabled(False)
            self.duplicate_btn.setEnabled(False)
            self.current_edit_index = None
    
    def load_device_into_form(self, device: Dict[str, Any]) -> None:
        """Load a device's properties into the edit form."""
        self.name_edit.setText(device.get('name', ''))
        self.description_edit.setText(device.get('description', ''))
        self.channel_spin.setValue(device.get('channel', 0))
        
        # Set type
        device_type = device.get('device_type', 'digital')
        io_type = device.get('io_type', 'output')
        
        if device_type == 'digital' and io_type == 'output':
            self.type_combo.setCurrentText("Digital Output")
        elif device_type == 'digital' and io_type == 'input':
            self.type_combo.setCurrentText("Digital Input")
        elif device_type == 'analog' and io_type == 'output':
            self.type_combo.setCurrentText("Analog Output")
        elif device_type == 'analog' and io_type == 'input':
            self.type_combo.setCurrentText("Analog Input")
        
        # Default state
        default_state = device.get('default_state', False)
        self.default_state_check.setChecked(default_state)
        
        # Analog settings
        if device_type == 'analog':
            self.min_value_spin.setValue(int(device.get('min_value', 0)))
            self.max_value_spin.setValue(int(device.get('max_value', 10)))
    
    def clear_form(self) -> None:
        """Clear the edit form."""
        self.name_edit.clear()
        self.description_edit.clear()
        self.channel_spin.setValue(0)
        self.type_combo.setCurrentIndex(0)
        self.default_state_check.setChecked(False)
        self.min_value_spin.setValue(0)
        self.max_value_spin.setValue(10)
        self.current_edit_index = None
        self.device_table.clearSelection()
    
    def add_device(self) -> None:
        """Add a new device."""
        self.clear_form()
        self.name_edit.setFocus()
    
    def update_device(self) -> None:
        """Update or add device from form."""
        name = self.name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Device name cannot be empty.")
            return
        
        # Validate name is unique (except for current device being edited)
        for i, device in enumerate(self.io_devices):
            if i != self.current_edit_index and device.get('name') == name:
                QMessageBox.warning(self, "Validation Error", f"Device name '{name}' already exists.")
                return
        
        # Build device dict
        type_text = self.type_combo.currentText()
        device_type = 'analog' if 'Analog' in type_text else 'digital'
        io_type = 'input' if 'Input' in type_text else 'output'
        
        device = {
            'name': name,
            'description': self.description_edit.text().strip(),
            'channel': self.channel_spin.value(),
            'device_type': device_type,
            'io_type': io_type,
        }
        
        if io_type == 'output':
            device['default_state'] = self.default_state_check.isChecked()
        
        if device_type == 'analog':
            device['min_value'] = float(self.min_value_spin.value())
            device['max_value'] = float(self.max_value_spin.value())
        
        # Update or add
        if self.current_edit_index is not None:
            self.io_devices[self.current_edit_index] = device
            logger.info(f"Updated device: {name}")
        else:
            self.io_devices.append(device)
            logger.info(f"Added device: {name}")
        
        self.refresh_table()
        self.clear_form()
    
    def remove_device(self) -> None:
        """Remove selected device."""
        if self.current_edit_index is not None:
            device_name = self.io_devices[self.current_edit_index].get('name', 'Unknown')
            
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Are you sure you want to remove device '{device_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.io_devices[self.current_edit_index]
                self.refresh_table()
                self.clear_form()
                logger.info(f"Removed device: {device_name}")
    
    def duplicate_device(self) -> None:
        """Duplicate selected device."""
        if self.current_edit_index is not None:
            device = self.io_devices[self.current_edit_index].copy()
            device['name'] = f"{device['name']}_copy"
            device['channel'] = (device.get('channel', 0) + 1) % 16
            
            self.io_devices.append(device)
            self.refresh_table()
            logger.info(f"Duplicated device: {device['name']}")
    
    def save_config(self) -> None:
        """Save configuration to hardware_config.yaml."""
        try:
            # Load existing config
            with open(self.config_file_path, 'r') as f:
                config = yaml.safe_load(f) or {}
            
            # Ensure io_devices section exists
            if 'io_devices' not in config:
                config['io_devices'] = {}
            
            # Organize devices by type
            digital_outputs = []
            digital_inputs = []
            analog_outputs = []
            analog_inputs = []
            
            for device in self.io_devices:
                device_copy = device.copy()
                # Remove internal fields
                device_copy.pop('device_type', None)
                device_copy.pop('io_type', None)
                
                if device['device_type'] == 'digital' and device['io_type'] == 'output':
                    digital_outputs.append(device_copy)
                elif device['device_type'] == 'digital' and device['io_type'] == 'input':
                    digital_inputs.append(device_copy)
                elif device['device_type'] == 'analog' and device['io_type'] == 'output':
                    analog_outputs.append(device_copy)
                elif device['device_type'] == 'analog' and device['io_type'] == 'input':
                    analog_inputs.append(device_copy)
            
            # Update config
            config['io_devices']['digital_outputs'] = digital_outputs
            config['io_devices']['digital_inputs'] = digital_inputs
            config['io_devices']['analog_outputs'] = analog_outputs
            config['io_devices']['analog_inputs'] = analog_inputs
            
            # Save to file
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.io_devices)} IO devices to config")
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Successfully saved {len(self.io_devices)} IO device(s) to configuration."
            )
            
            # Emit signal
            self.config_saved.emit()
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving IO config: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
    
    def show_help(self) -> None:
        """Show help dialog."""
        help_text = """
<h3>IO Device Configuration Help</h3>

<h4>WidgetLords PI-SPI-DIN Hardware:</h4>
<ul>
<li><b>PI-SPI-DIN-4KO:</b> 4 relay outputs (Channels 0-3)</li>
<li><b>PI-SPI-DIN-8AI:</b> 8 analog inputs (Channels 0-7)</li>
<li><b>PI-SPI-DIN-8DI:</b> 8 digital inputs (Channels 0-7)</li>
</ul>

<h4>Device Types:</h4>
<ul>
<li><b>Digital Output:</b> Relays, valves (ON/OFF control)</li>
<li><b>Digital Input:</b> Switches, sensors (ON/OFF reading)</li>
<li><b>Analog Output:</b> Variable voltage outputs (0-10V)</li>
<li><b>Analog Input:</b> Sensors, 4-20mA loops (voltage reading)</li>
</ul>

<h4>Configuration Tips:</h4>
<ul>
<li>Use descriptive names (e.g., vacuum_pump, vent_valve)</li>
<li>Match channel numbers to your physical wiring</li>
<li>Set default states for safety-critical outputs</li>
<li>For analog inputs, set min/max to match sensor range</li>
</ul>

<h4>Example Devices:</h4>
<ul>
<li>vacuum_pump (Digital Output, Channel 0)</li>
<li>vent_valve (Digital Output, Channel 1)</li>
<li>pressure_sensor (Analog Input, Channel 0, 0-10V)</li>
</ul>
        """
        
        QMessageBox.information(self, "Help", help_text)

