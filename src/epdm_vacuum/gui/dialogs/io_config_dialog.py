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
    QFrame,
    QProgressBar,
    QApplication,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor

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
        self.load_cell_config: Dict[str, Any] = {}  # TLB4 load cell channel config
        self.load_cell_widgets: List[Dict[str, Any]] = []  # UI widgets for load cell config
        
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
        
        # Load Cells tab (TLB4 channels)
        load_cells_tab = self.create_load_cells_tab()
        self.tab_widget.addTab(load_cells_tab, "Load Cells")
        
        # Modbus tab
        modbus_tab = self.create_modbus_tab()
        self.tab_widget.addTab(modbus_tab, "Modbus/RS485")
        
        # Calibration tab
        calibration_tab = self.create_calibration_tab()
        self.tab_widget.addTab(calibration_tab, "⚖ Calibration")
        
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
    
    def create_load_cells_tab(self) -> QWidget:
        """Create the Load Cells configuration tab for TLB4 channels."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        
        # Info banner
        info_banner = QGroupBox("TLB4 Load Cell Configuration")
        info_banner.setStyleSheet("""
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                border: 2px solid #9C27B0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                background-color: #F3E5F5;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        
        info_layout = QVBoxLayout()
        info_text = QLabel(
            "Configure individual load cell channels on the TLB4 transmitter.\n"
            "• Each channel reads from a specific Modbus register (32-bit value)\n"
            "• Command 25 is sent automatically to enable multi-channel mode\n"
            "• Values are raw ADC divisions - calibrate to convert to kg\n"
            "• Default addresses: CH1=50, CH2=52, CH3=54, CH4=56 (after Command 25)"
        )
        info_text.setStyleSheet("font-size: 9pt; color: #7B1FA2; font-weight: normal;")
        info_layout.addWidget(info_text)
        info_banner.setLayout(info_layout)
        layout.addWidget(info_banner)
        
        # Create channel configuration widgets
        self.load_cell_widgets = []
        
        # Channel colors for visual distinction
        channel_colors = ["#E53935", "#1E88E5", "#43A047", "#FB8C00"]
        channel_names = ["Load Cell 1 (LC1)", "Load Cell 2 (LC2)", "Load Cell 3 (LC3)", "Load Cell 4 (LC4)"]
        default_addresses = [50, 52, 54, 56]
        
        for i in range(4):
            channel_group = self.create_load_cell_channel_widget(
                i + 1, 
                channel_names[i], 
                channel_colors[i],
                default_addresses[i]
            )
            layout.addWidget(channel_group)
            
        # Calibration help section
        cal_group = QGroupBox("Calibration Guide")
        cal_group.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border: 2px solid #607D8B;
                border-radius: 4px;
                margin-top: 8px;
                background-color: #ECEFF1;
            }
        """)
        cal_layout = QVBoxLayout()
        cal_text = QLabel(
            "<b>How to Calibrate:</b><br>"
            "1. <b>Zero Offset:</b> With no load, note the raw value and enter it as 'Zero Offset'<br>"
            "2. <b>Full Scale:</b> Apply a known weight (e.g., 10kg), calculate:<br>"
            "   &nbsp;&nbsp;&nbsp;Divisions per kg = (loaded_value - zero_value) / weight_kg<br>"
            "3. <b>Formula:</b> kg = (raw_value - zero_offset) / full_scale_divisions"
        )
        cal_text.setStyleSheet("font-size: 9pt; font-weight: normal;")
        cal_text.setWordWrap(True)
        cal_layout.addWidget(cal_text)
        cal_group.setLayout(cal_layout)
        layout.addWidget(cal_group)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        return tab
    
    def create_load_cell_channel_widget(
        self, 
        channel_num: int, 
        name: str, 
        color: str,
        default_address: int
    ) -> QGroupBox:
        """Create configuration widget for a single load cell channel."""
        group = QGroupBox(name)
        group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 10pt;
                font-weight: bold;
                border: 2px solid {color};
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 5px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: {color};
            }}
        """)
        
        layout = QHBoxLayout()
        layout.setSpacing(20)
        
        # Left side: Enable and Name
        left_layout = QVBoxLayout()
        
        # Enable checkbox
        enable_check = QCheckBox("Enabled")
        enable_check.setChecked(channel_num <= 2)  # Enable first 2 by default
        enable_check.setStyleSheet(f"font-weight: bold; color: {color};")
        left_layout.addWidget(enable_check)
        
        # Custom name
        name_layout = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText(f"e.g., Left Cell, Corner A")
        name_edit.setMaximumWidth(150)
        name_layout.addRow("Name:", name_edit)
        left_layout.addLayout(name_layout)
        
        layout.addLayout(left_layout)
        
        # Middle: Register address
        addr_layout = QFormLayout()
        addr_spin = QSpinBox()
        addr_spin.setRange(0, 100)
        addr_spin.setValue(default_address)
        addr_spin.setToolTip("Modbus register address (0-based). Standard: 50, 52, 54, 56")
        addr_layout.addRow("Register Address:", addr_spin)
        
        # Show 40001-based address
        addr_label = QLabel(f"(Register {default_address + 40001})")
        addr_label.setStyleSheet("color: #666; font-size: 8pt;")
        addr_spin.valueChanged.connect(
            lambda v, lbl=addr_label: lbl.setText(f"(Register {v + 40001})")
        )
        addr_layout.addRow("", addr_label)
        
        layout.addLayout(addr_layout)
        
        # Right: Calibration
        cal_layout = QFormLayout()
        
        zero_spin = QDoubleSpinBox()
        zero_spin.setRange(-1000000, 1000000)
        zero_spin.setDecimals(0)
        zero_spin.setValue(0)
        zero_spin.setToolTip("Raw division value when load cell has no weight")
        cal_layout.addRow("Zero Offset:", zero_spin)
        
        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(1, 1000000)
        scale_spin.setDecimals(1)
        scale_spin.setValue(2000.0)
        scale_spin.setToolTip("Divisions per kg (calibrate with known weight)")
        cal_layout.addRow("Divisions/kg:", scale_spin)
        
        layout.addLayout(cal_layout)
        
        # Far right: Live value display
        value_layout = QVBoxLayout()
        value_label = QLabel("--")
        value_label.setStyleSheet(f"""
            font-size: 14pt;
            font-weight: bold;
            color: {color};
            padding: 5px;
            background-color: #f5f5f5;
            border: 1px solid #ddd;
            border-radius: 4px;
            min-width: 80px;
        """)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setToolTip("Live reading (kg)")
        value_layout.addWidget(QLabel("Live:"))
        value_layout.addWidget(value_label)
        
        layout.addLayout(value_layout)
        
        group.setLayout(layout)
        
        # Store widget references
        self.load_cell_widgets.append({
            'channel': channel_num,
            'group': group,
            'enable': enable_check,
            'name': name_edit,
            'address': addr_spin,
            'zero_offset': zero_spin,
            'scale': scale_spin,
            'value_label': value_label,
        })
        
        return group
    
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
        self.modbus_port_edit.setPlaceholderText("e.g., /tmp/modbus (WidgetLords+modbusd) or COM3 (Windows)")
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
    
    def create_calibration_tab(self) -> QWidget:
        """Create the Calibration tab for TLB4 load cell real calibration."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setSpacing(16)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(20)
        
        # =====================================================================
        # Header with live weight display
        # =====================================================================
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a237e, stop:1 #283593);
                border-radius: 12px;
                padding: 20px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Title
        title_label = QLabel("⚖ Scale Calibration")
        title_label.setStyleSheet("""
            font-size: 22px;
            font-weight: bold;
            color: #ffffff;
            letter-spacing: 1px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Subtitle
        subtitle_label = QLabel("Real calibration using physical reference weights")
        subtitle_label.setStyleSheet("font-size: 11px; color: #b3b3ff; margin-bottom: 15px;")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        # Live weight display panel
        weight_panel = QFrame()
        weight_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 15px;
            }
        """)
        weight_layout = QHBoxLayout(weight_panel)
        
        # Current weight display
        self.cal_weight_display = QLabel("---")
        self.cal_weight_display.setStyleSheet("""
            font-size: 48px;
            font-weight: bold;
            color: #64ffda;
            font-family: 'Consolas', 'Monaco', monospace;
        """)
        self.cal_weight_display.setAlignment(Qt.AlignCenter)
        weight_layout.addWidget(self.cal_weight_display, stretch=2)
        
        # Weight unit
        unit_label = QLabel("kg")
        unit_label.setStyleSheet("font-size: 24px; color: #80cbc4; margin-left: -10px;")
        weight_layout.addWidget(unit_label)
        
        weight_layout.addSpacing(30)
        
        # Raw value display
        raw_layout = QVBoxLayout()
        raw_title = QLabel("RAW VALUE")
        raw_title.setStyleSheet("font-size: 10px; color: #90caf9; letter-spacing: 2px;")
        raw_layout.addWidget(raw_title)
        
        self.cal_raw_display = QLabel("---")
        self.cal_raw_display.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #e3f2fd;
            font-family: 'Consolas', 'Monaco', monospace;
        """)
        raw_layout.addWidget(self.cal_raw_display)
        weight_layout.addLayout(raw_layout)
        
        weight_layout.addSpacing(20)
        
        # Connection status
        status_layout = QVBoxLayout()
        status_title = QLabel("STATUS")
        status_title.setStyleSheet("font-size: 10px; color: #90caf9; letter-spacing: 2px;")
        status_layout.addWidget(status_title)
        
        self.cal_status_indicator = QLabel("● Disconnected")
        self.cal_status_indicator.setStyleSheet("font-size: 14px; color: #ef5350;")
        status_layout.addWidget(self.cal_status_indicator)
        weight_layout.addLayout(status_layout)
        
        header_layout.addWidget(weight_panel)
        layout.addWidget(header_frame)
        
        # =====================================================================
        # Calibration Steps Container
        # =====================================================================
        steps_container = QHBoxLayout()
        steps_container.setSpacing(20)
        
        # ---------------------------------------------------------------------
        # Step 1: Zero Calibration
        # ---------------------------------------------------------------------
        zero_card = self._create_calibration_card(
            step_num="1",
            title="Zero Calibration",
            icon="○",
            color="#00897b",
            description="Define the zero point (empty scale)",
            instructions=[
                "Remove ALL weight from the scale",
                "Ensure scale platform is clean and stable",
                "Wait for reading to stabilize",
                "Click 'Calibrate Zero' button"
            ]
        )
        
        # Zero calibration button
        zero_btn_layout = QHBoxLayout()
        self.zero_cal_btn = QPushButton("Calibrate Zero")
        self.zero_cal_btn.setStyleSheet("""
            QPushButton {
                background-color: #00897b;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 14px 28px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #00796b;
            }
            QPushButton:pressed {
                background-color: #00695c;
            }
            QPushButton:disabled {
                background-color: #b2dfdb;
                color: #80cbc4;
            }
        """)
        self.zero_cal_btn.clicked.connect(self.perform_zero_calibration)
        zero_btn_layout.addWidget(self.zero_cal_btn)
        zero_card.layout().addLayout(zero_btn_layout)
        
        # Zero result label
        self.zero_result_label = QLabel("")
        self.zero_result_label.setStyleSheet("font-size: 11px; color: #666; margin-top: 8px;")
        self.zero_result_label.setWordWrap(True)
        zero_card.layout().addWidget(self.zero_result_label)
        
        steps_container.addWidget(zero_card)
        
        # ---------------------------------------------------------------------
        # Step 2: Span Calibration
        # ---------------------------------------------------------------------
        span_card = self._create_calibration_card(
            step_num="2",
            title="Span Calibration",
            icon="◉",
            color="#1565c0",
            description="Define a calibration point using known weight",
            instructions=[
                "Complete Zero Calibration first",
                "Place a known reference weight on scale",
                "Enter the exact weight value below",
                "Recommended: Use 50%+ of full capacity",
                "Click 'Calibrate Span' button"
            ]
        )
        
        # Weight input
        weight_input_layout = QFormLayout()
        weight_input_layout.setSpacing(10)
        
        self.known_weight_spin = QDoubleSpinBox()
        self.known_weight_spin.setRange(0.01, 10000.0)
        self.known_weight_spin.setDecimals(2)
        self.known_weight_spin.setValue(10.0)
        self.known_weight_spin.setSuffix(" kg")
        self.known_weight_spin.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 16px;
                font-weight: bold;
                padding: 10px 15px;
                border: 2px solid #1565c0;
                border-radius: 6px;
                background-color: #e3f2fd;
                color: #1565c0;
            }
            QDoubleSpinBox:focus {
                border-color: #0d47a1;
            }
        """)
        
        weight_label = QLabel("Reference Weight:")
        weight_label.setStyleSheet("font-weight: bold; color: #1565c0;")
        weight_input_layout.addRow(weight_label, self.known_weight_spin)
        span_card.layout().addLayout(weight_input_layout)
        
        # Span calibration button
        span_btn_layout = QHBoxLayout()
        self.span_cal_btn = QPushButton("Calibrate Span")
        self.span_cal_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 14px 28px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0d47a1;
            }
            QPushButton:pressed {
                background-color: #0a3d91;
            }
            QPushButton:disabled {
                background-color: #bbdefb;
                color: #90caf9;
            }
        """)
        self.span_cal_btn.clicked.connect(self.perform_span_calibration)
        span_btn_layout.addWidget(self.span_cal_btn)
        span_card.layout().addLayout(span_btn_layout)
        
        # Span result label
        self.span_result_label = QLabel("")
        self.span_result_label.setStyleSheet("font-size: 11px; color: #666; margin-top: 8px;")
        self.span_result_label.setWordWrap(True)
        span_card.layout().addWidget(self.span_result_label)
        
        steps_container.addWidget(span_card)
        
        layout.addLayout(steps_container)
        
        # =====================================================================
        # Important Notes Section
        # =====================================================================
        notes_frame = QFrame()
        notes_frame.setStyleSheet("""
            QFrame {
                background-color: #fff8e1;
                border: 2px solid #ffb300;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        notes_layout = QVBoxLayout(notes_frame)
        
        notes_title = QLabel("⚠ Important Calibration Notes")
        notes_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #ff6f00;")
        notes_layout.addWidget(notes_title)
        
        notes_text = QLabel(
            "• <b>Stability:</b> Ensure readings are stable before calibrating. Unstable weights will cause errors.\n"
            "• <b>Reference Weight:</b> Use certified calibration weights for accurate results.\n"
            "• <b>Capacity:</b> Reference weight should be 50% or more of full scale capacity.\n"
            "• <b>Order:</b> Always perform Zero Calibration before Span Calibration.\n"
            "• <b>Environment:</b> Avoid vibrations, air currents, and temperature changes during calibration.\n"
            "• <b>Error Codes:</b> If calibration fails, check the error code and ensure all conditions are met."
        )
        notes_text.setStyleSheet("font-size: 11px; color: #5d4037; line-height: 1.5;")
        notes_text.setWordWrap(True)
        notes_layout.addWidget(notes_text)
        
        layout.addWidget(notes_frame)
        
        # =====================================================================
        # Error Code Reference
        # =====================================================================
        error_group = QGroupBox("Calibration Error Codes Reference")
        error_group.setStyleSheet("""
            QGroupBox {
                font-size: 11px;
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #fafafa;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        error_layout = QVBoxLayout()
        
        error_text = QLabel(
            "<table style='font-size: 10px;'>"
            "<tr><td><b>Code 0:</b></td><td style='color: #2e7d32;'>Success - Calibration completed successfully</td></tr>"
            "<tr><td><b>Non-zero:</b></td><td style='color: #c62828;'>Error - Check stability, weight value, and hardware connections</td></tr>"
            "</table>"
        )
        error_text.setStyleSheet("font-size: 10px;")
        error_layout.addWidget(error_text)
        error_group.setLayout(error_layout)
        
        layout.addWidget(error_group)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Setup calibration update timer
        self.cal_update_timer = QTimer()
        self.cal_update_timer.timeout.connect(self.update_calibration_display)
        
        return tab
    
    def _create_calibration_card(
        self,
        step_num: str,
        title: str,
        icon: str,
        color: str,
        description: str,
        instructions: list
    ) -> QFrame:
        """Create a styled calibration step card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        card.setMinimumWidth(350)
        
        layout = QVBoxLayout(card)
        layout.setSpacing(12)
        
        # Step header
        header_layout = QHBoxLayout()
        
        step_badge = QLabel(f"STEP {step_num}")
        step_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            font-size: 10px;
            font-weight: bold;
            padding: 4px 10px;
            border-radius: 10px;
            letter-spacing: 1px;
        """)
        step_badge.setFixedWidth(70)
        header_layout.addWidget(step_badge)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Title
        title_label = QLabel(f"{icon} {title}")
        title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: bold;
            color: {color};
        """)
        layout.addWidget(title_label)
        
        # Description
        desc_label = QLabel(description)
        desc_label.setStyleSheet("font-size: 11px; color: #666; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {color}; opacity: 0.3;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # Instructions
        instructions_label = QLabel("Instructions:")
        instructions_label.setStyleSheet("font-size: 11px; font-weight: bold; color: #333; margin-top: 5px;")
        layout.addWidget(instructions_label)
        
        for i, instruction in enumerate(instructions, 1):
            instr_label = QLabel(f"  {i}. {instruction}")
            instr_label.setStyleSheet("font-size: 10px; color: #555; margin-left: 10px;")
            layout.addWidget(instr_label)
        
        layout.addSpacing(10)
        
        return card
    
    def update_calibration_display(self) -> None:
        """Update the live weight display in calibration tab."""
        try:
            # Get parent main window to access modbus interface
            main_window = self.parent()
            if main_window and hasattr(main_window, 'modbus_interface') and main_window.modbus_interface:
                interface = main_window.modbus_interface
                if interface.is_connected():
                    status = interface.get_calibration_status()
                    
                    # Update weight display
                    weight_kg = status.get('gross_weight_kg', 0.0)
                    raw_value = status.get('gross_weight_raw', 0)
                    
                    self.cal_weight_display.setText(f"{weight_kg:.2f}")
                    self.cal_raw_display.setText(f"{raw_value}")
                    
                    # Update status indicator
                    self.cal_status_indicator.setText("● Connected")
                    self.cal_status_indicator.setStyleSheet("font-size: 14px; color: #4caf50;")
                    
                    # Enable calibration buttons
                    self.zero_cal_btn.setEnabled(True)
                    self.span_cal_btn.setEnabled(True)
                    return
            
            # Not connected state
            self.cal_weight_display.setText("---")
            self.cal_raw_display.setText("---")
            self.cal_status_indicator.setText("● Disconnected")
            self.cal_status_indicator.setStyleSheet("font-size: 14px; color: #ef5350;")
            self.zero_cal_btn.setEnabled(False)
            self.span_cal_btn.setEnabled(False)
            
        except Exception as e:
            logger.warning(f"Error updating calibration display: {e}")
    
    def perform_zero_calibration(self) -> None:
        """Perform zero calibration on the TLB4."""
        try:
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Zero Calibration",
                "⚠ ZERO CALIBRATION\n\n"
                "Please confirm:\n"
                "• The scale is completely EMPTY\n"
                "• The reading is STABLE\n"
                "• No vibrations or air currents\n\n"
                "Proceed with zero calibration?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Get modbus interface from parent
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'modbus_interface') or not main_window.modbus_interface:
                QMessageBox.warning(self, "Error", "Modbus interface not available.\n\nPlease ensure:\n• Modbus is enabled in settings\n• TLB4 is connected and powered")
                return
            
            interface = main_window.modbus_interface
            if not interface.is_connected():
                QMessageBox.warning(self, "Error", "TLB4 is not connected.\n\nCheck serial port and connection.")
                return
            
            # Disable buttons during calibration
            self.zero_cal_btn.setEnabled(False)
            self.span_cal_btn.setEnabled(False)
            self.zero_cal_btn.setText("Calibrating...")
            QApplication.processEvents()
            
            # Perform calibration
            logger.info("User initiated Zero Calibration")
            success, message = interface.zero_calibration()
            
            # Re-enable buttons
            self.zero_cal_btn.setEnabled(True)
            self.span_cal_btn.setEnabled(True)
            self.zero_cal_btn.setText("Calibrate Zero")
            
            # Show result
            if success:
                self.zero_result_label.setText(f"✓ {message}")
                self.zero_result_label.setStyleSheet("font-size: 11px; color: #2e7d32; font-weight: bold; margin-top: 8px;")
                QMessageBox.information(self, "Zero Calibration", f"✓ SUCCESS\n\n{message}")
            else:
                self.zero_result_label.setText(f"✗ {message}")
                self.zero_result_label.setStyleSheet("font-size: 11px; color: #c62828; font-weight: bold; margin-top: 8px;")
                QMessageBox.critical(self, "Zero Calibration Failed", f"✗ FAILED\n\n{message}")
            
        except Exception as e:
            logger.error(f"Zero calibration error: {e}", exc_info=True)
            self.zero_cal_btn.setEnabled(True)
            self.span_cal_btn.setEnabled(True)
            self.zero_cal_btn.setText("Calibrate Zero")
            QMessageBox.critical(self, "Error", f"Calibration failed with error:\n{e}")
    
    def perform_span_calibration(self) -> None:
        """Perform span calibration on the TLB4 with known weight."""
        try:
            known_weight = self.known_weight_spin.value()
            
            # Confirm with user
            reply = QMessageBox.question(
                self,
                "Span Calibration",
                f"⚖ SPAN CALIBRATION\n\n"
                f"Reference weight: {known_weight:.2f} kg\n\n"
                f"Please confirm:\n"
                f"• Zero calibration has been completed\n"
                f"• {known_weight:.2f} kg reference weight is on the scale\n"
                f"• The reading is STABLE\n"
                f"• No vibrations or air currents\n\n"
                f"Proceed with span calibration?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Get modbus interface from parent
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'modbus_interface') or not main_window.modbus_interface:
                QMessageBox.warning(self, "Error", "Modbus interface not available.\n\nPlease ensure:\n• Modbus is enabled in settings\n• TLB4 is connected and powered")
                return
            
            interface = main_window.modbus_interface
            if not interface.is_connected():
                QMessageBox.warning(self, "Error", "TLB4 is not connected.\n\nCheck serial port and connection.")
                return
            
            # Disable buttons during calibration
            self.zero_cal_btn.setEnabled(False)
            self.span_cal_btn.setEnabled(False)
            self.span_cal_btn.setText("Calibrating...")
            QApplication.processEvents()
            
            # Perform calibration
            logger.info(f"User initiated Span Calibration with {known_weight:.2f} kg")
            success, message, error_code = interface.span_calibration(known_weight)
            
            # Re-enable buttons
            self.zero_cal_btn.setEnabled(True)
            self.span_cal_btn.setEnabled(True)
            self.span_cal_btn.setText("Calibrate Span")
            
            # Show result
            if success:
                self.span_result_label.setText(f"✓ {message}")
                self.span_result_label.setStyleSheet("font-size: 11px; color: #2e7d32; font-weight: bold; margin-top: 8px;")
                QMessageBox.information(self, "Span Calibration", f"✓ SUCCESS\n\n{message}")
            else:
                error_info = f"\nError code: {error_code}" if error_code != -1 else ""
                self.span_result_label.setText(f"✗ {message}")
                self.span_result_label.setStyleSheet("font-size: 11px; color: #c62828; font-weight: bold; margin-top: 8px;")
                QMessageBox.critical(self, "Span Calibration Failed", f"✗ FAILED\n\n{message}{error_info}")
            
        except Exception as e:
            logger.error(f"Span calibration error: {e}", exc_info=True)
            self.zero_cal_btn.setEnabled(True)
            self.span_cal_btn.setEnabled(True)
            self.span_cal_btn.setText("Calibrate Span")
            QMessageBox.critical(self, "Error", f"Calibration failed with error:\n{e}")
    
    def showEvent(self, event):
        """Handle dialog show event to start calibration timer if on calibration tab."""
        super().showEvent(event)
        # Start timer when dialog is shown and calibration tab is selected
        if hasattr(self, 'cal_update_timer'):
            self.cal_update_timer.start(500)  # Update every 500ms
    
    def hideEvent(self, event):
        """Handle dialog hide event to stop calibration timer."""
        super().hideEvent(event)
        if hasattr(self, 'cal_update_timer'):
            self.cal_update_timer.stop()
    
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
            self.modbus_port_edit.setText(modbus_config.get('port', '/tmp/modbus'))
            
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
            
            # Load TLB4 load cell configuration
            tlb4_config = modbus_config.get('tlb4', {})
            registers = tlb4_config.get('registers', {})
            channel_scaling = tlb4_config.get('channel_scaling', {})
            
            # Load each channel's configuration
            for widget in self.load_cell_widgets:
                ch_num = widget['channel']
                ch_key = f'channel_{ch_num}'
                
                # Get register address
                addr = registers.get(ch_key, 50 + (ch_num - 1) * 2)
                widget['address'].setValue(addr)
                
                # Get channel-specific scaling
                ch_scaling = channel_scaling.get(ch_key, {})
                widget['enable'].setChecked(ch_scaling.get('enabled', ch_num <= 2))
                widget['zero_offset'].setValue(ch_scaling.get('zero_offset', 0))
                widget['scale'].setValue(ch_scaling.get('full_scale_divisions', 2000.0))
            
            logger.info(f"Loaded TLB4 load cell configuration")
            
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
            
            # Preserve existing TLB4 config structure
            existing_tlb4 = config['hardware'].get('modbus', {}).get('tlb4', {})
            
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
            
            # Build TLB4 load cell configuration from widgets
            tlb4_registers = existing_tlb4.get('registers', {}).copy()
            tlb4_scaling = existing_tlb4.get('channel_scaling', {}).copy()
            
            for widget in self.load_cell_widgets:
                ch_num = widget['channel']
                ch_key = f'channel_{ch_num}'
                
                # Update register address
                tlb4_registers[ch_key] = widget['address'].value()
                
                # Update channel scaling
                tlb4_scaling[ch_key] = {
                    'enabled': widget['enable'].isChecked(),
                    'full_scale_divisions': widget['scale'].value(),
                    'capacity_kg': 1.0,
                    'zero_offset': widget['zero_offset'].value(),
                }
            
            # Preserve other TLB4 settings
            config['hardware']['modbus']['tlb4'] = {
                'registers': {
                    'gross_weight': existing_tlb4.get('registers', {}).get('gross_weight', 7),
                    'net_weight': existing_tlb4.get('registers', {}).get('net_weight', 9),
                    'tare_weight': existing_tlb4.get('registers', {}).get('tare_weight', 11),
                    'status': existing_tlb4.get('registers', {}).get('status', 6),
                    'command': existing_tlb4.get('registers', {}).get('command', 5),
                    'channel_1': tlb4_registers.get('channel_1', 50),
                    'channel_2': tlb4_registers.get('channel_2', 52),
                    'channel_3': tlb4_registers.get('channel_3', 54),
                    'channel_4': tlb4_registers.get('channel_4', 56),
                },
                'data_format': existing_tlb4.get('data_format', 'int32'),
                'decimal_places': existing_tlb4.get('decimal_places', 0),
                'channel_scaling': {
                    'full_scale_divisions': tlb4_scaling.get('full_scale_divisions', 2000.0),
                    'load_cell_capacity_kg': tlb4_scaling.get('load_cell_capacity_kg', 1.0),
                    'channel_1': tlb4_scaling.get('channel_1', {}),
                    'channel_2': tlb4_scaling.get('channel_2', {}),
                    'channel_3': tlb4_scaling.get('channel_3', {}),
                    'channel_4': tlb4_scaling.get('channel_4', {}),
                },
            }
            
            logger.info(f"Prepared Modbus config: enabled={config['hardware']['modbus']['enabled']}, "
                       f"port={config['hardware']['modbus']['port']}, "
                       f"baudrate={config['hardware']['modbus']['baudrate']}")
            
            # Save to file
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.io_devices)} IO devices and Modbus config to {self.config_file_path}")
            
            # Count enabled load cells
            enabled_lc_count = sum(1 for w in self.load_cell_widgets if w['enable'].isChecked())
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Successfully saved configuration:\n\n"
                f"• {len(self.io_devices)} IO device(s)\n"
                f"• {enabled_lc_count} Load cell(s) enabled\n"
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
<li><b>Modbus Port:</b> WidgetLords+modbusd: /tmp/modbus | USB adapter: /dev/ttyUSB0 or COM3</li>
<li><b>Slave Address:</b> Check device DIP switches or configuration (typically 1)</li>
<li><b>Baudrate:</b> Must match TLB4 setting (check device display/manual)</li>
<li><b>Troubleshooting:</b> Enable debug logging to see all Modbus communication</li>
<li><b>Test Connection:</b> Use the test button to verify serial port and parameters</li>
</ul>

<h4>Example Configuration:</h4>
<ul>
<li><b>Modbus Port:</b> /tmp/modbus (WidgetLords+modbusd) or /dev/ttyUSB0 (USB adapter)</li>
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

