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
    QTabWidget,
    QDoubleSpinBox,
    QWidget,
    QScrollArea,
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
        self.modbus_config: Dict[str, Any] = {}
        
        self.init_ui()
        self.load_config()
        
        logger.info("IOConfigDialog initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Hardware Configuration")
        self.setMinimumSize(950, 700)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("Hardware Configuration")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; color: #333; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Configure IO devices, Modbus communication, and other hardware settings")
        subtitle.setStyleSheet("font-size: 10pt; color: #666; margin-bottom: 10px;")
        layout.addWidget(subtitle)
        
        # Create tab widget for different configuration sections
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 8px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                color: white;
            }
        """)
        
        # IO Devices tab
        io_tab = self.create_io_devices_tab()
        self.tab_widget.addTab(io_tab, "IO Devices")
        
        # Modbus tab
        modbus_tab = self.create_modbus_tab()
        self.tab_widget.addTab(modbus_tab, "Modbus/RS485")
        
        layout.addWidget(self.tab_widget)
        
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
    
    def create_io_devices_tab(self) -> QWidget:
        """Create the IO devices configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
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
        
        return tab
    
    def create_modbus_tab(self) -> QWidget:
        """Create the Modbus configuration tab."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Create scroll area for the form
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # Modbus/RS485 Information Banner
        info_banner = QGroupBox("Modbus RTU Communication Setup")
        info_banner.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #FF9800;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #FFF3E0;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "Configure RS485/Modbus RTU communication for Laumas TLB4 Load Cell Transmitter\n"
            "• Hardware: TLB4 supports up to 4 load cells, Modbus RTU Slave protocol\n"
            "• Connection: Use USB-RS485 adapter (e.g., USB-485M, Waveshare USB-RS485)\n"
            "• Wiring: Connect RS485 A/B terminals between adapter and TLB4\n"
            "• Power: Ensure TLB4 has 12-24 VDC power supply\n"
            "• Default: 9600 baud, 8 data bits, no parity, 1 stop bit, slave address 1"
        )
        info_text.setStyleSheet("font-size: 9pt; color: #E65100; font-weight: normal;")
        info_layout.addWidget(info_text)
        info_banner.setLayout(info_layout)
        layout.addWidget(info_banner)
        
        # Enable/Disable Modbus
        enable_group = QGroupBox("Modbus Status")
        enable_layout = QHBoxLayout()
        self.modbus_enabled_check = QCheckBox("Enable Modbus Communication")
        self.modbus_enabled_check.setStyleSheet("font-weight: bold; font-size: 10pt;")
        self.modbus_enabled_check.stateChanged.connect(self.on_modbus_enabled_changed)
        enable_layout.addWidget(self.modbus_enabled_check)
        enable_layout.addStretch()
        enable_group.setLayout(enable_layout)
        layout.addWidget(enable_group)
        
        # Connection Settings
        conn_group = QGroupBox("Connection Settings")
        conn_form = QFormLayout()
        conn_form.setSpacing(12)
        
        # Serial Port
        port_layout = QHBoxLayout()
        self.modbus_port_edit = QLineEdit()
        self.modbus_port_edit.setPlaceholderText("e.g., COM3 (Windows) or /dev/ttyUSB0 (Linux)")
        port_layout.addWidget(self.modbus_port_edit)
        
        test_port_btn = QPushButton("Test Connection")
        test_port_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 4px 12px;")
        test_port_btn.clicked.connect(self.test_modbus_connection)
        port_layout.addWidget(test_port_btn)
        
        port_help = QLabel("📝 Serial port for USB-RS485 adapter")
        port_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        conn_form.addRow("Serial Port:", port_layout)
        conn_form.addRow("", port_help)
        
        # Baudrate
        self.modbus_baudrate_combo = QComboBox()
        self.modbus_baudrate_combo.addItems(["1200", "2400", "4800", "9600", "19200", "38400", "57600", "115200"])
        self.modbus_baudrate_combo.setCurrentText("9600")
        
        baud_help = QLabel("📝 Communication speed (bits/second). Common: 9600, 19200")
        baud_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        conn_form.addRow("Baudrate:", self.modbus_baudrate_combo)
        conn_form.addRow("", baud_help)
        
        # Parity
        self.modbus_parity_combo = QComboBox()
        self.modbus_parity_combo.addItems(["None", "Even", "Odd", "Mark", "Space"])
        self.modbus_parity_combo.setCurrentText("None")
        
        parity_help = QLabel("📝 Error checking method. Common: None or Even")
        parity_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        conn_form.addRow("Parity:", self.modbus_parity_combo)
        conn_form.addRow("", parity_help)
        
        # Data Bits
        self.modbus_databits_combo = QComboBox()
        self.modbus_databits_combo.addItems(["7", "8"])
        self.modbus_databits_combo.setCurrentText("8")
        
        databits_help = QLabel("📝 Number of data bits per byte. Standard: 8")
        databits_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        conn_form.addRow("Data Bits:", self.modbus_databits_combo)
        conn_form.addRow("", databits_help)
        
        # Stop Bits
        self.modbus_stopbits_combo = QComboBox()
        self.modbus_stopbits_combo.addItems(["1", "1.5", "2"])
        self.modbus_stopbits_combo.setCurrentText("1")
        
        stopbits_help = QLabel("📝 Stop bits for byte separation. Standard: 1")
        stopbits_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        conn_form.addRow("Stop Bits:", self.modbus_stopbits_combo)
        conn_form.addRow("", stopbits_help)
        
        conn_group.setLayout(conn_form)
        layout.addWidget(conn_group)
        
        # Modbus Protocol Settings
        protocol_group = QGroupBox("Modbus Protocol Settings")
        protocol_form = QFormLayout()
        protocol_form.setSpacing(12)
        
        # Slave Address
        self.modbus_slave_spin = QSpinBox()
        self.modbus_slave_spin.setRange(1, 247)
        self.modbus_slave_spin.setValue(1)
        
        slave_help = QLabel("📝 Modbus device address (1-247). Check device configuration")
        slave_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        protocol_form.addRow("Slave Address:", self.modbus_slave_spin)
        protocol_form.addRow("", slave_help)
        
        # Timeout
        self.modbus_timeout_spin = QDoubleSpinBox()
        self.modbus_timeout_spin.setRange(0.1, 10.0)
        self.modbus_timeout_spin.setValue(1.0)
        self.modbus_timeout_spin.setSingleStep(0.1)
        self.modbus_timeout_spin.setSuffix(" sec")
        
        timeout_help = QLabel("📝 Communication timeout. Increase if getting errors")
        timeout_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        protocol_form.addRow("Timeout:", self.modbus_timeout_spin)
        protocol_form.addRow("", timeout_help)
        
        # Byte Order (Endianness)
        self.modbus_byteorder_combo = QComboBox()
        self.modbus_byteorder_combo.addItems(["Big Endian (>)", "Little Endian (<)"])
        self.modbus_byteorder_combo.setCurrentText("Big Endian (>)")
        
        byteorder_help = QLabel("📝 Byte order for multi-byte values. Common: Big Endian")
        byteorder_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        protocol_form.addRow("Byte Order:", self.modbus_byteorder_combo)
        protocol_form.addRow("", byteorder_help)
        
        # Word Order
        self.modbus_wordorder_combo = QComboBox()
        self.modbus_wordorder_combo.addItems(["High Word First (>)", "Low Word First (<)"])
        self.modbus_wordorder_combo.setCurrentText("High Word First (>)")
        
        wordorder_help = QLabel("📝 Word order for 32-bit values")
        wordorder_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        protocol_form.addRow("Word Order:", self.modbus_wordorder_combo)
        protocol_form.addRow("", wordorder_help)
        
        protocol_group.setLayout(protocol_form)
        layout.addWidget(protocol_group)
        
        # Advanced Settings
        advanced_group = QGroupBox("Advanced Settings")
        advanced_form = QFormLayout()
        advanced_form.setSpacing(12)
        
        # Close port after each communication
        self.modbus_close_port_check = QCheckBox("Close port after each read")
        close_help = QLabel("📝 Enable if multiple programs access the port")
        close_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        advanced_form.addRow("Port Management:", self.modbus_close_port_check)
        advanced_form.addRow("", close_help)
        
        # Debug mode
        self.modbus_debug_check = QCheckBox("Enable debug logging")
        debug_help = QLabel("📝 Log all Modbus communication for troubleshooting")
        debug_help.setStyleSheet("color: #666; font-size: 9pt;")
        
        advanced_form.addRow("Debug Mode:", self.modbus_debug_check)
        advanced_form.addRow("", debug_help)
        
        advanced_group.setLayout(advanced_form)
        layout.addWidget(advanced_group)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        return tab
    
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
    
    def on_modbus_enabled_changed(self) -> None:
        """Handle Modbus enabled checkbox change."""
        enabled = self.modbus_enabled_check.isChecked()
        logger.debug(f"Modbus enabled changed to: {enabled}")
    
    def test_modbus_connection(self) -> None:
        """Test Modbus connection with current settings."""
        try:
            port = self.modbus_port_edit.text().strip()
            if not port:
                QMessageBox.warning(self, "Test Connection", "Please enter a serial port first.")
                return
            
            baudrate = int(self.modbus_baudrate_combo.currentText())
            slave_address = self.modbus_slave_spin.value()
            
            logger.info(f"Testing Modbus connection: port={port}, baudrate={baudrate}, slave={slave_address}")
            
            QMessageBox.information(
                self,
                "Test Connection",
                f"Connection test initiated for:\n\n"
                f"Port: {port}\n"
                f"Baudrate: {baudrate}\n"
                f"Slave Address: {slave_address}\n\n"
                f"Note: Full connection testing requires actual hardware.\n"
                f"This validates the configuration parameters."
            )
            
        except Exception as e:
            logger.error(f"Error testing Modbus connection: {e}", exc_info=True)
            QMessageBox.critical(self, "Test Error", f"Failed to test connection:\n{e}")
    
    def load_config(self) -> None:
        """Load IO devices and Modbus config from hardware_config.yaml."""
        try:
            if not self.config_file_path.exists():
                logger.warning(f"Config file not found: {self.config_file_path}")
                return
            
            with open(self.config_file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load IO devices
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
            
            # Load Modbus configuration
            modbus_config = config.get('hardware', {}).get('modbus', {})
            self.modbus_config = modbus_config
            
            # Populate Modbus form fields
            self.modbus_enabled_check.setChecked(modbus_config.get('enabled', False))
            self.modbus_port_edit.setText(modbus_config.get('port', '/dev/ttyUSB0'))
            
            baudrate = str(modbus_config.get('baudrate', 9600))
            index = self.modbus_baudrate_combo.findText(baudrate)
            if index >= 0:
                self.modbus_baudrate_combo.setCurrentIndex(index)
            
            self.modbus_slave_spin.setValue(modbus_config.get('slave_address', 1))
            self.modbus_timeout_spin.setValue(modbus_config.get('timeout', 1.0))
            
            # Load additional Modbus settings if they exist
            parity = modbus_config.get('parity', 'None')
            parity_index = self.modbus_parity_combo.findText(parity)
            if parity_index >= 0:
                self.modbus_parity_combo.setCurrentIndex(parity_index)
            
            databits = str(modbus_config.get('databits', 8))
            databits_index = self.modbus_databits_combo.findText(databits)
            if databits_index >= 0:
                self.modbus_databits_combo.setCurrentIndex(databits_index)
            
            stopbits = str(modbus_config.get('stopbits', 1))
            stopbits_index = self.modbus_stopbits_combo.findText(stopbits)
            if stopbits_index >= 0:
                self.modbus_stopbits_combo.setCurrentIndex(stopbits_index)
            
            byteorder = modbus_config.get('byteorder', 'big')
            if byteorder == 'little':
                self.modbus_byteorder_combo.setCurrentText("Little Endian (<)")
            else:
                self.modbus_byteorder_combo.setCurrentText("Big Endian (>)")
            
            wordorder = modbus_config.get('wordorder', 'big')
            if wordorder == 'little':
                self.modbus_wordorder_combo.setCurrentText("Low Word First (<)")
            else:
                self.modbus_wordorder_combo.setCurrentText("High Word First (>)")
            
            self.modbus_close_port_check.setChecked(modbus_config.get('close_port_after_each_call', False))
            self.modbus_debug_check.setChecked(modbus_config.get('debug', False))
            
            logger.info(f"Loaded Modbus configuration from config")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
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
            
            # Save Modbus configuration
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'modbus' not in config['hardware']:
                config['hardware']['modbus'] = {}
            
            # Get parity value
            parity_text = self.modbus_parity_combo.currentText()
            
            # Get byte order
            byteorder_text = self.modbus_byteorder_combo.currentText()
            byteorder = 'little' if 'Little' in byteorder_text else 'big'
            
            # Get word order
            wordorder_text = self.modbus_wordorder_combo.currentText()
            wordorder = 'little' if 'Low' in wordorder_text else 'big'
            
            # Convert stopbits to float if needed
            stopbits_str = self.modbus_stopbits_combo.currentText()
            try:
                stopbits = float(stopbits_str)
            except:
                stopbits = 1.0
            
            config['hardware']['modbus'] = {
                'enabled': self.modbus_enabled_check.isChecked(),
                'port': self.modbus_port_edit.text().strip(),
                'baudrate': int(self.modbus_baudrate_combo.currentText()),
                'slave_address': self.modbus_slave_spin.value(),
                'timeout': self.modbus_timeout_spin.value(),
                'parity': parity_text,
                'databits': int(self.modbus_databits_combo.currentText()),
                'stopbits': stopbits,
                'byteorder': byteorder,
                'wordorder': wordorder,
                'close_port_after_each_call': self.modbus_close_port_check.isChecked(),
                'debug': self.modbus_debug_check.isChecked(),
            }
            
            logger.info(f"Prepared Modbus config: enabled={config['hardware']['modbus']['enabled']}, "
                       f"port={config['hardware']['modbus']['port']}, "
                       f"baudrate={config['hardware']['modbus']['baudrate']}")
            
            # Save to file
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.io_devices)} IO devices and Modbus config to {self.config_file_path}")
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Successfully saved configuration:\n\n"
                f"• {len(self.io_devices)} IO device(s)\n"
                f"• Modbus: {'Enabled' if config['hardware']['modbus']['enabled'] else 'Disabled'}\n"
                f"• Port: {config['hardware']['modbus']['port']}\n"
                f"• Baudrate: {config['hardware']['modbus']['baudrate']}"
            )
            
            # Emit signal
            self.config_saved.emit()
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
    
    def show_help(self) -> None:
        """Show help dialog."""
        help_text = """
<h3>Hardware Configuration Help</h3>

<h4>IO Devices - WidgetLords PI-SPI-DIN Hardware:</h4>
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

<h4>Modbus/RS485 - TLB4 Load Cell Transmitter:</h4>
<ul>
<li><b>Hardware:</b> Laumas TLB4 discrete/analog load cell transmitter</li>
<li><b>Protocol:</b> Modbus RTU Slave over RS-485</li>
<li><b>Inputs:</b> Up to 4 load cells (±39 mV, 24-bit resolution)</li>
<li><b>Communication:</b> RS-485, up to 115.2k baud</li>
<li><b>Connection:</b> Use USB-485M adapter (AutomationDirect or similar)</li>
<li><b>Default Settings:</b> 9600 baud, 8 data bits, no parity, 1 stop bit</li>
</ul>

<h4>Configuration Tips:</h4>
<ul>
<li><b>IO Devices:</b> Use descriptive names, match channel numbers to physical wiring</li>
<li><b>Modbus Port:</b> Windows: COM3, COM4, etc. | Linux: /dev/ttyUSB0, /dev/ttyUSB1</li>
<li><b>Slave Address:</b> Check device DIP switches or configuration (typically 1)</li>
<li><b>Baudrate:</b> Must match TLB4 setting (check device display/manual)</li>
<li><b>Troubleshooting:</b> Enable debug logging to see all Modbus communication</li>
<li><b>Test Connection:</b> Use the test button to verify serial port and parameters</li>
</ul>

<h4>Example Configuration:</h4>
<ul>
<li><b>Modbus Port:</b> COM3 (Windows) or /dev/ttyUSB0 (Linux)</li>
<li><b>Baudrate:</b> 9600</li>
<li><b>Slave Address:</b> 1</li>
<li><b>Parity:</b> None</li>
<li><b>Data Bits:</b> 8</li>
<li><b>Stop Bits:</b> 1</li>
</ul>

<h4>Hardware Connections:</h4>
<ul>
<li>1. Connect USB-RS485 adapter to PC USB port</li>
<li>2. Wire RS485 A/B terminals to TLB4 RS485 terminals</li>
<li>3. Verify TLB4 power supply (12-24 VDC)</li>
<li>4. Check TLB4 address matches configuration</li>
<li>5. Test connection before starting measurements</li>
</ul>
        """
        
        QMessageBox.information(self, "Help", help_text)

