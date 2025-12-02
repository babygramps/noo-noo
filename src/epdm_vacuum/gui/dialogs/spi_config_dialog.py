"""
SPI Configuration Dialog - Widgetlords Module Assignment

Dialog for configuring Widgetlords PI-SPI-DIN modules with:
- Assign modules to chip selects (CE0-CE4)
- Configure module addresses (0-3 for stacking)
- Assign I/O channels to functions
- Support for all PI-SPI-DIN module types
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
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QGridLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QIcon, QPalette

logger = logging.getLogger(__name__)


# Available Widgetlords module types with their capabilities
MODULE_TYPES = {
    "PI-SPI-DIN-4KO": {
        "description": "4 Channel Relay Output Module",
        "io_type": "relay_output",
        "channels": 4,
        "max_per_ce": 4,  # Up to 4 modules per chip enable (addresses 0-3)
        "icon": "🔌",
        "color": "#E53935",  # Red for relays
    },
    "PI-SPI-DIN-8AI": {
        "description": "8 Channel Analog Input Module (0-10V/4-20mA)",
        "io_type": "analog_input", 
        "channels": 8,
        "max_per_ce": 1,
        "icon": "📊",
        "color": "#43A047",  # Green for analog inputs
    },
    "PI-SPI-DIN-8DI": {
        "description": "8 Channel Digital Input Module",
        "io_type": "digital_input",
        "channels": 8,
        "max_per_ce": 1,
        "icon": "⚡",
        "color": "#1E88E5",  # Blue for digital inputs
    },
    "PI-SPI-DIN-4AO": {
        "description": "4 Channel Analog Output Module (0-10V)",
        "io_type": "analog_output",
        "channels": 4,
        "max_per_ce": 1,
        "icon": "📈",
        "color": "#FB8C00",  # Orange for analog outputs
    },
}

# Chip Enable definitions (GPIO pins)
CHIP_ENABLES = {
    "CE0": {"gpio": 8, "description": "GPIO8 (SPI0 CE0)"},
    "CE1": {"gpio": 7, "description": "GPIO7 (SPI0 CE1)"},
    "CE2": {"gpio": 24, "description": "GPIO24"},
    "CE3": {"gpio": 23, "description": "GPIO23"},
    "CE4": {"gpio": 18, "description": "GPIO18"},
}


class SPIModuleCard(QFrame):
    """
    A card widget representing a configured SPI module.
    """
    
    removed = pyqtSignal(object)
    edited = pyqtSignal(object)
    
    def __init__(self, module_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.module_config = module_config
        self.init_ui()
    
    def init_ui(self):
        """Initialize the card UI."""
        self.setFrameStyle(QFrame.Box | QFrame.Raised)
        self.setLineWidth(2)
        
        module_type = self.module_config.get("module_type", "PI-SPI-DIN-4KO")
        module_info = MODULE_TYPES.get(module_type, MODULE_TYPES["PI-SPI-DIN-4KO"])
        
        # Set card color based on module type
        color = module_info["color"]
        self.setStyleSheet(f"""
            SPIModuleCard {{
                background-color: white;
                border: 2px solid {color};
                border-radius: 8px;
                padding: 8px;
                margin: 4px;
            }}
            SPIModuleCard:hover {{
                border: 3px solid {color};
                background-color: #f5f5f5;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(4)
        
        # Header with icon and type
        header_layout = QHBoxLayout()
        
        icon_label = QLabel(module_info["icon"])
        icon_label.setStyleSheet("font-size: 24pt;")
        header_layout.addWidget(icon_label)
        
        type_label = QLabel(f"<b>{module_type}</b>")
        type_label.setStyleSheet(f"color: {color}; font-size: 11pt;")
        header_layout.addWidget(type_label, stretch=1)
        
        # Chip Enable badge
        ce = self.module_config.get("chip_enable", "CE0")
        ce_badge = QLabel(ce)
        ce_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            font-weight: bold;
            padding: 4px 8px;
            border-radius: 4px;
        """)
        header_layout.addWidget(ce_badge)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(module_info["description"])
        desc_label.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(desc_label)
        
        # Module details
        name = self.module_config.get("name", "Unnamed Module")
        addr = self.module_config.get("address", 0)
        
        details_label = QLabel(f"Name: <b>{name}</b> | Address: <b>{addr}</b>")
        details_label.setStyleSheet("font-size: 9pt;")
        layout.addWidget(details_label)
        
        # Channel summary
        channels = self.module_config.get("channels", [])
        active_channels = sum(1 for ch in channels if ch.get("enabled", True))
        total_channels = module_info["channels"]
        
        channel_label = QLabel(f"Channels: {active_channels}/{total_channels} active")
        channel_label.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(channel_label)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        edit_btn = QPushButton("Edit")
        edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }}
            QPushButton:hover {{
                background-color: {self._darken_color(color)};
            }}
        """)
        edit_btn.clicked.connect(lambda: self.edited.emit(self))
        btn_layout.addWidget(edit_btn)
        
        remove_btn = QPushButton("Remove")
        remove_btn.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        btn_layout.addWidget(remove_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        # Darken by 20%
        r = max(0, int(r * 0.8))
        g = max(0, int(g * 0.8))
        b = max(0, int(b * 0.8))
        return f"#{r:02x}{g:02x}{b:02x}"


class ModuleEditorDialog(QDialog):
    """
    Dialog for editing a single SPI module configuration.
    """
    
    def __init__(self, module_config: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        
        self.module_config = module_config or {
            "name": "",
            "module_type": "PI-SPI-DIN-4KO",
            "chip_enable": "CE0",
            "address": 0,
            "channels": [],
        }
        self.result_config = None
        
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """Initialize the editor UI."""
        self.setWindowTitle("Configure SPI Module")
        self.setMinimumSize(700, 600)
        
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel("SPI Module Configuration")
        title.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333; margin-bottom: 10px;")
        layout.addWidget(title)
        
        # Module settings group
        settings_group = QGroupBox("Module Settings")
        settings_layout = QFormLayout()
        settings_layout.setSpacing(12)
        
        # Module name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., relay_module_1, pressure_inputs")
        settings_layout.addRow("Module Name:", self.name_edit)
        
        # Module type
        self.type_combo = QComboBox()
        for mod_type, info in MODULE_TYPES.items():
            self.type_combo.addItem(f"{info['icon']} {mod_type} - {info['description']}", mod_type)
        self.type_combo.currentIndexChanged.connect(self.on_type_changed)
        settings_layout.addRow("Module Type:", self.type_combo)
        
        # Chip Enable
        self.ce_combo = QComboBox()
        for ce_name, ce_info in CHIP_ENABLES.items():
            self.ce_combo.addItem(f"{ce_name} ({ce_info['description']})", ce_name)
        settings_layout.addRow("Chip Enable:", self.ce_combo)
        
        # Address (for stacking 4KO modules)
        self.address_spin = QSpinBox()
        self.address_spin.setRange(0, 3)
        self.address_spin.setValue(0)
        self.address_label = QLabel("📝 Address 0-3 for stacking multiple 4KO modules on same chip enable")
        self.address_label.setStyleSheet("color: #666; font-size: 9pt;")
        settings_layout.addRow("Address:", self.address_spin)
        settings_layout.addRow("", self.address_label)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # Channel configuration group
        self.channel_group = QGroupBox("Channel Configuration")
        self.channel_layout = QVBoxLayout()
        
        # Channel table
        self.channel_table = QTableWidget()
        self.channel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.channel_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.channel_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.channel_layout.addWidget(self.channel_table)
        
        self.channel_group.setLayout(self.channel_layout)
        layout.addWidget(self.channel_group, stretch=1)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Module")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        save_btn.clicked.connect(self.save_module)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
        
        # Initialize channel table
        self.refresh_channel_table()
    
    def on_type_changed(self):
        """Handle module type change."""
        module_type = self.type_combo.currentData()
        module_info = MODULE_TYPES.get(module_type, {})
        
        # Show/hide address selector based on module type
        can_stack = module_info.get("max_per_ce", 1) > 1
        self.address_spin.setVisible(can_stack)
        self.address_label.setVisible(can_stack)
        
        # Reset channels for new type
        num_channels = module_info.get("channels", 4)
        self.module_config["channels"] = [
            {"channel": i, "name": f"Channel {i}", "enabled": True}
            for i in range(num_channels)
        ]
        
        self.refresh_channel_table()
    
    def refresh_channel_table(self):
        """Refresh the channel configuration table."""
        module_type = self.type_combo.currentData() if self.type_combo.currentData() else "PI-SPI-DIN-4KO"
        module_info = MODULE_TYPES.get(module_type, MODULE_TYPES["PI-SPI-DIN-4KO"])
        
        io_type = module_info.get("io_type", "relay_output")
        num_channels = module_info.get("channels", 4)
        
        # Configure table columns based on IO type
        if io_type == "relay_output":
            self.channel_table.setColumnCount(4)
            self.channel_table.setHorizontalHeaderLabels(["Ch", "Enabled", "Name", "Description"])
        elif io_type == "analog_input":
            self.channel_table.setColumnCount(6)
            self.channel_table.setHorizontalHeaderLabels(["Ch", "Enabled", "Name", "Min V", "Max V", "Description"])
        elif io_type == "digital_input":
            self.channel_table.setColumnCount(5)
            self.channel_table.setHorizontalHeaderLabels(["Ch", "Enabled", "Name", "Invert", "Description"])
        else:
            self.channel_table.setColumnCount(4)
            self.channel_table.setHorizontalHeaderLabels(["Ch", "Enabled", "Name", "Description"])
        
        # Get or create channel configs
        channels = self.module_config.get("channels", [])
        if len(channels) != num_channels:
            channels = [
                {"channel": i, "name": f"Channel {i}", "enabled": True}
                for i in range(num_channels)
            ]
            self.module_config["channels"] = channels
        
        self.channel_table.setRowCount(num_channels)
        
        for row, ch_config in enumerate(channels):
            # Channel number
            ch_item = QTableWidgetItem(str(row))
            ch_item.setTextAlignment(Qt.AlignCenter)
            self.channel_table.setItem(row, 0, ch_item)
            
            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(ch_config.get("enabled", True))
            enabled_check.stateChanged.connect(lambda state, r=row: self.on_channel_enabled_changed(r, state))
            enabled_widget = QWidget()
            enabled_layout = QHBoxLayout(enabled_widget)
            enabled_layout.addWidget(enabled_check)
            enabled_layout.setAlignment(Qt.AlignCenter)
            enabled_layout.setContentsMargins(0, 0, 0, 0)
            self.channel_table.setCellWidget(row, 1, enabled_widget)
            
            # Name
            name_edit = QLineEdit(ch_config.get("name", f"Channel {row}"))
            name_edit.textChanged.connect(lambda text, r=row: self.on_channel_name_changed(r, text))
            self.channel_table.setCellWidget(row, 2, name_edit)
            
            # Additional columns based on IO type
            if io_type == "analog_input":
                min_spin = QDoubleSpinBox()
                min_spin.setRange(-1000, 1000)
                min_spin.setValue(ch_config.get("min_value", 0.0))
                min_spin.valueChanged.connect(lambda val, r=row: self.on_channel_value_changed(r, "min_value", val))
                self.channel_table.setCellWidget(row, 3, min_spin)
                
                max_spin = QDoubleSpinBox()
                max_spin.setRange(-1000, 1000)
                max_spin.setValue(ch_config.get("max_value", 10.0))
                max_spin.valueChanged.connect(lambda val, r=row: self.on_channel_value_changed(r, "max_value", val))
                self.channel_table.setCellWidget(row, 4, max_spin)
                
                desc_edit = QLineEdit(ch_config.get("description", ""))
                desc_edit.textChanged.connect(lambda text, r=row: self.on_channel_desc_changed(r, text))
                self.channel_table.setCellWidget(row, 5, desc_edit)
                
            elif io_type == "digital_input":
                invert_check = QCheckBox()
                invert_check.setChecked(ch_config.get("inverted", False))
                invert_check.stateChanged.connect(lambda state, r=row: self.on_channel_invert_changed(r, state))
                invert_widget = QWidget()
                invert_layout = QHBoxLayout(invert_widget)
                invert_layout.addWidget(invert_check)
                invert_layout.setAlignment(Qt.AlignCenter)
                invert_layout.setContentsMargins(0, 0, 0, 0)
                self.channel_table.setCellWidget(row, 3, invert_widget)
                
                desc_edit = QLineEdit(ch_config.get("description", ""))
                desc_edit.textChanged.connect(lambda text, r=row: self.on_channel_desc_changed(r, text))
                self.channel_table.setCellWidget(row, 4, desc_edit)
            else:
                desc_edit = QLineEdit(ch_config.get("description", ""))
                desc_edit.textChanged.connect(lambda text, r=row: self.on_channel_desc_changed(r, text))
                self.channel_table.setCellWidget(row, 3, desc_edit)
        
        # Set column widths
        header = self.channel_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.channel_table.setColumnWidth(0, 40)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        self.channel_table.setColumnWidth(1, 60)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        for i in range(3, self.channel_table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
    
    def on_channel_enabled_changed(self, row: int, state: int):
        """Handle channel enabled change."""
        if row < len(self.module_config.get("channels", [])):
            self.module_config["channels"][row]["enabled"] = (state == Qt.Checked)
    
    def on_channel_name_changed(self, row: int, text: str):
        """Handle channel name change."""
        if row < len(self.module_config.get("channels", [])):
            self.module_config["channels"][row]["name"] = text
    
    def on_channel_desc_changed(self, row: int, text: str):
        """Handle channel description change."""
        if row < len(self.module_config.get("channels", [])):
            self.module_config["channels"][row]["description"] = text
    
    def on_channel_value_changed(self, row: int, key: str, value: float):
        """Handle channel analog value change."""
        if row < len(self.module_config.get("channels", [])):
            self.module_config["channels"][row][key] = value
    
    def on_channel_invert_changed(self, row: int, state: int):
        """Handle channel invert change."""
        if row < len(self.module_config.get("channels", [])):
            self.module_config["channels"][row]["inverted"] = (state == Qt.Checked)
    
    def load_config(self):
        """Load existing configuration into the form."""
        self.name_edit.setText(self.module_config.get("name", ""))
        
        # Set module type
        module_type = self.module_config.get("module_type", "PI-SPI-DIN-4KO")
        for i in range(self.type_combo.count()):
            if self.type_combo.itemData(i) == module_type:
                self.type_combo.setCurrentIndex(i)
                break
        
        # Set chip enable
        ce = self.module_config.get("chip_enable", "CE0")
        for i in range(self.ce_combo.count()):
            if self.ce_combo.itemData(i) == ce:
                self.ce_combo.setCurrentIndex(i)
                break
        
        # Set address
        self.address_spin.setValue(self.module_config.get("address", 0))
        
        # Trigger type change to set up proper visibility
        self.on_type_changed()
        
        # Reload channels from config
        self.refresh_channel_table()
    
    def save_module(self):
        """Save the module configuration."""
        name = self.name_edit.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Validation Error", "Module name is required.")
            return
        
        self.result_config = {
            "name": name,
            "module_type": self.type_combo.currentData(),
            "chip_enable": self.ce_combo.currentData(),
            "address": self.address_spin.value(),
            "channels": self.module_config.get("channels", []),
        }
        
        logger.info(f"Saving module configuration: {name} ({self.result_config['module_type']}) on {self.result_config['chip_enable']}")
        self.accept()


class SPIConfigDialog(QDialog):
    """
    Main dialog for configuring Widgetlords SPI modules.
    
    Allows users to:
    - Add/edit/remove SPI modules
    - Assign chip selects and addresses
    - Configure individual channels
    - Save configuration to hardware_config.yaml
    """
    
    # Signal emitted when configuration is saved
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        """Initialize the SPI configuration dialog."""
        super().__init__(parent)
        
        self.config_file_path = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        self.spi_modules: List[Dict[str, Any]] = []
        self.module_cards: List[SPIModuleCard] = []
        
        self.init_ui()
        self.load_config()
        
        logger.info("SPIConfigDialog initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Widgetlords SPI Module Configuration")
        self.setMinimumSize(1000, 700)
        
        layout = QVBoxLayout(self)
        
        # Title and description
        title = QLabel("🔧 Widgetlords SPI Module Configuration")
        title.setStyleSheet("font-size: 18pt; font-weight: bold; color: #1976D2; margin-bottom: 5px;")
        layout.addWidget(title)
        
        subtitle = QLabel("Configure PI-SPI-DIN modules, chip selects, and I/O assignments")
        subtitle.setStyleSheet("font-size: 10pt; color: #666; margin-bottom: 15px;")
        layout.addWidget(subtitle)
        
        # Hardware info banner
        info_banner = self.create_info_banner()
        layout.addWidget(info_banner)
        
        # Main content - split view
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Chip Enable overview
        left_panel = self.create_chip_enable_overview()
        splitter.addWidget(left_panel)
        
        # Right panel - Module cards
        right_panel = self.create_module_panel()
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 700])
        layout.addWidget(splitter, stretch=1)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.help_btn = QPushButton("Help")
        self.help_btn.clicked.connect(self.show_help)
        button_layout.addWidget(self.help_btn)
        
        button_layout.addStretch()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton("Save Configuration")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 24px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.save_btn.clicked.connect(self.save_config)
        button_layout.addWidget(self.save_btn)
        
        layout.addLayout(button_layout)
    
    def create_info_banner(self) -> QGroupBox:
        """Create the hardware information banner."""
        banner = QGroupBox("About PI-SPI-DIN Modules")
        banner.setStyleSheet("""
            QGroupBox {
                font-size: 10pt;
                font-weight: bold;
                border: 2px solid #2196F3;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
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
            "<b>Available Modules:</b><br>"
            "• <b style='color:#E53935;'>PI-SPI-DIN-4KO</b>: 4× Relay Outputs (2A AC/DC SPDT) - up to 4 modules per CE<br>"
            "• <b style='color:#43A047;'>PI-SPI-DIN-8AI</b>: 8× Analog Inputs (0-10V or 4-20mA selectable)<br>"
            "• <b style='color:#1E88E5;'>PI-SPI-DIN-8DI</b>: 8× Digital Inputs (12-24V)<br>"
            "• <b style='color:#FB8C00;'>PI-SPI-DIN-4AO</b>: 4× Analog Outputs (0-10V)<br><br>"
            "<b>Chip Enables (CE0-CE4):</b> Each CE can address different module types. "
            "The 4KO relay module supports stacking up to 4 modules on the same CE using addresses 0-3."
        )
        info_text.setStyleSheet("font-size: 9pt; color: #1565C0; font-weight: normal;")
        info_text.setWordWrap(True)
        layout.addWidget(info_text)
        
        banner.setLayout(layout)
        return banner
    
    def create_chip_enable_overview(self) -> QGroupBox:
        """Create the chip enable overview panel."""
        panel = QGroupBox("Chip Enable Status")
        panel.setMinimumWidth(280)
        layout = QVBoxLayout()
        
        # Chip enable status tree
        self.ce_tree = QTreeWidget()
        self.ce_tree.setHeaderLabels(["Chip Enable", "Status"])
        self.ce_tree.setRootIsDecorated(True)
        self.ce_tree.setAlternatingRowColors(True)
        
        # Populate tree with chip enables
        for ce_name, ce_info in CHIP_ENABLES.items():
            ce_item = QTreeWidgetItem([ce_name, "Empty"])
            ce_item.setData(0, Qt.UserRole, ce_name)
            ce_item.setToolTip(0, ce_info["description"])
            self.ce_tree.addTopLevelItem(ce_item)
        
        layout.addWidget(self.ce_tree)
        
        # Quick add buttons
        add_layout = QVBoxLayout()
        
        add_label = QLabel("Quick Add Module:")
        add_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        add_layout.addWidget(add_label)
        
        for mod_type, info in MODULE_TYPES.items():
            btn = QPushButton(f"{info['icon']} {mod_type}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {info['color']};
                    color: white;
                    text-align: left;
                    padding: 6px 12px;
                    border-radius: 4px;
                    margin: 2px;
                }}
                QPushButton:hover {{
                    background-color: {self._darken_color(info['color'])};
                }}
            """)
            btn.clicked.connect(lambda checked, mt=mod_type: self.add_module(mt))
            add_layout.addWidget(btn)
        
        layout.addLayout(add_layout)
        
        panel.setLayout(layout)
        return panel
    
    def create_module_panel(self) -> QWidget:
        """Create the module cards panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Configured Modules")
        header_label.setStyleSheet("font-size: 12pt; font-weight: bold;")
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        add_btn = QPushButton("+ Add Module")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        add_btn.clicked.connect(lambda: self.add_module())
        header_layout.addWidget(add_btn)
        
        layout.addLayout(header_layout)
        
        # Scrollable area for module cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.cards_container)
        layout.addWidget(scroll, stretch=1)
        
        # Empty state message
        self.empty_label = QLabel(
            "<center>"
            "<p style='font-size: 14pt; color: #999;'>No modules configured</p>"
            "<p style='color: #bbb;'>Click '+ Add Module' or use the Quick Add buttons to get started</p>"
            "</center>"
        )
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)
        
        return panel
    
    def _darken_color(self, hex_color: str) -> str:
        """Darken a hex color."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, int(r * 0.8))
        g = max(0, int(g * 0.8))
        b = max(0, int(b * 0.8))
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def add_module(self, module_type: Optional[str] = None):
        """Add a new module."""
        logger.info(f"Adding new module of type: {module_type or 'user choice'}")
        
        # Create default config
        initial_config = {
            "name": "",
            "module_type": module_type or "PI-SPI-DIN-4KO",
            "chip_enable": self.get_next_available_ce(),
            "address": 0,
            "channels": [],
        }
        
        dialog = ModuleEditorDialog(initial_config, self)
        if dialog.exec_() == QDialog.Accepted and dialog.result_config:
            self.spi_modules.append(dialog.result_config)
            self.refresh_module_cards()
            self.refresh_ce_tree()
            logger.info(f"Added module: {dialog.result_config['name']}")
    
    def get_next_available_ce(self) -> str:
        """Get the next available chip enable."""
        used_ces = set()
        for module in self.spi_modules:
            # 4KO modules can share CE, others cannot
            if module.get("module_type") != "PI-SPI-DIN-4KO":
                used_ces.add(module.get("chip_enable"))
        
        for ce_name in CHIP_ENABLES.keys():
            if ce_name not in used_ces:
                return ce_name
        
        return "CE0"
    
    def edit_module(self, card: SPIModuleCard):
        """Edit an existing module."""
        idx = self.module_cards.index(card)
        if idx < len(self.spi_modules):
            module_config = self.spi_modules[idx].copy()
            
            dialog = ModuleEditorDialog(module_config, self)
            if dialog.exec_() == QDialog.Accepted and dialog.result_config:
                self.spi_modules[idx] = dialog.result_config
                self.refresh_module_cards()
                self.refresh_ce_tree()
                logger.info(f"Updated module: {dialog.result_config['name']}")
    
    def remove_module(self, card: SPIModuleCard):
        """Remove a module."""
        idx = self.module_cards.index(card)
        if idx < len(self.spi_modules):
            module_name = self.spi_modules[idx].get("name", "Unknown")
            
            reply = QMessageBox.question(
                self,
                "Confirm Remove",
                f"Are you sure you want to remove module '{module_name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.spi_modules[idx]
                self.refresh_module_cards()
                self.refresh_ce_tree()
                logger.info(f"Removed module: {module_name}")
    
    def refresh_module_cards(self):
        """Refresh all module cards."""
        # Clear existing cards
        for card in self.module_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.module_cards.clear()
        
        # Remove the stretch at the end
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add cards for each module
        for module_config in self.spi_modules:
            card = SPIModuleCard(module_config, self)
            card.edited.connect(self.edit_module)
            card.removed.connect(self.remove_module)
            self.cards_layout.addWidget(card)
            self.module_cards.append(card)
        
        # Add stretch at end
        self.cards_layout.addStretch()
        
        # Show/hide empty message
        self.empty_label.setVisible(len(self.spi_modules) == 0)
    
    def refresh_ce_tree(self):
        """Refresh the chip enable tree view."""
        for i in range(self.ce_tree.topLevelItemCount()):
            ce_item = self.ce_tree.topLevelItem(i)
            ce_name = ce_item.data(0, Qt.UserRole)
            
            # Remove existing children
            ce_item.takeChildren()
            
            # Find modules using this CE
            modules_on_ce = [m for m in self.spi_modules if m.get("chip_enable") == ce_name]
            
            if modules_on_ce:
                ce_item.setText(1, f"{len(modules_on_ce)} module(s)")
                for module in modules_on_ce:
                    mod_item = QTreeWidgetItem([
                        f"  {module.get('name', 'Unnamed')}",
                        module.get('module_type', 'Unknown')
                    ])
                    ce_item.addChild(mod_item)
                ce_item.setExpanded(True)
            else:
                ce_item.setText(1, "Empty")
    
    def load_config(self):
        """Load SPI module configuration from hardware_config.yaml."""
        try:
            if not self.config_file_path.exists():
                logger.warning(f"Config file not found: {self.config_file_path}")
                self.refresh_module_cards()
                self.refresh_ce_tree()
                return
            
            with open(self.config_file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load SPI modules from config
            self.spi_modules = config.get('hardware', {}).get('widgetlords', {}).get('spi_modules', [])
            
            # If no modules defined, try to migrate from old format
            if not self.spi_modules:
                self.spi_modules = self._migrate_old_config(config)
            
            self.refresh_module_cards()
            self.refresh_ce_tree()
            
            logger.info(f"Loaded {len(self.spi_modules)} SPI modules from config")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", f"Failed to load configuration:\n{e}")
    
    def _migrate_old_config(self, config: Dict) -> List[Dict]:
        """Migrate from old widgetlords config format."""
        modules = []
        
        # Check for old-style config
        old_wl = config.get('hardware', {}).get('widgetlords', {})
        
        if old_wl.get('enabled'):
            # Create a default relay module based on pump_relay setting
            pump_relay = old_wl.get('pump_relay', 0)
            
            modules.append({
                "name": "relay_module",
                "module_type": "PI-SPI-DIN-4KO",
                "chip_enable": "CE0",
                "address": 0,
                "channels": [
                    {"channel": i, "name": f"Relay K{i+1}", "enabled": True, 
                     "description": "Vacuum pump" if i == pump_relay else ""}
                    for i in range(4)
                ],
            })
            
            # Create a default analog input module for pressure
            pressure_channel = old_wl.get('pressure_channel', 0)
            
            modules.append({
                "name": "analog_inputs",
                "module_type": "PI-SPI-DIN-8AI",
                "chip_enable": "CE1",
                "address": 0,
                "channels": [
                    {"channel": i, "name": f"AI{i}", "enabled": True,
                     "min_value": 0.0, "max_value": 10.0,
                     "description": "Pressure sensor" if i == pressure_channel else ""}
                    for i in range(8)
                ],
            })
            
            logger.info("Migrated old widgetlords config to new SPI module format")
        
        return modules
    
    def save_config(self):
        """Save SPI module configuration to hardware_config.yaml."""
        try:
            # Load existing config
            if self.config_file_path.exists():
                with open(self.config_file_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Ensure structure exists
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'widgetlords' not in config['hardware']:
                config['hardware']['widgetlords'] = {}
            
            # Update with new SPI modules configuration
            config['hardware']['widgetlords']['enabled'] = len(self.spi_modules) > 0
            config['hardware']['widgetlords']['spi_modules'] = self.spi_modules
            
            # Keep legacy fields for backward compatibility
            # Find first relay module and analog input for legacy config
            relay_module = next((m for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-4KO"), None)
            analog_module = next((m for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-8AI"), None)
            
            if relay_module:
                # Find first channel marked for vacuum pump
                pump_channel = next(
                    (ch.get("channel", 0) for ch in relay_module.get("channels", []) 
                     if "pump" in ch.get("description", "").lower() or "pump" in ch.get("name", "").lower()),
                    0
                )
                config['hardware']['widgetlords']['pump_relay'] = pump_channel
            
            if analog_module:
                # Find first channel marked for pressure
                pressure_channel = next(
                    (ch.get("channel", 0) for ch in analog_module.get("channels", [])
                     if "pressure" in ch.get("description", "").lower() or "pressure" in ch.get("name", "").lower()),
                    0
                )
                config['hardware']['widgetlords']['pressure_channel'] = pressure_channel
            
            # Save to file
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.spi_modules)} SPI modules to {self.config_file_path}")
            
            # Summary for user
            relay_count = sum(1 for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-4KO")
            analog_in_count = sum(1 for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-8AI")
            digital_in_count = sum(1 for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-8DI")
            analog_out_count = sum(1 for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-4AO")
            
            QMessageBox.information(
                self,
                "Configuration Saved",
                f"Successfully saved SPI module configuration:\n\n"
                f"• {relay_count} Relay Output module(s) (4KO)\n"
                f"• {analog_in_count} Analog Input module(s) (8AI)\n"
                f"• {digital_in_count} Digital Input module(s) (8DI)\n"
                f"• {analog_out_count} Analog Output module(s) (4AO)\n\n"
                f"Total: {len(self.spi_modules)} module(s)"
            )
            
            # Emit signal
            self.config_saved.emit()
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
    
    def show_help(self):
        """Show help dialog."""
        help_text = """
<h2>Widgetlords SPI Module Configuration</h2>

<h3>About PI-SPI-DIN Modules</h3>
<p>These DIN-rail mounted I/O modules communicate with the Raspberry Pi via SPI bus.
Each module connects to a <b>Chip Enable (CE)</b> line for addressing.</p>

<h3>Available Chip Enables</h3>
<table border="1" cellpadding="4">
<tr><th>CE</th><th>GPIO</th><th>Notes</th></tr>
<tr><td>CE0</td><td>GPIO8</td><td>SPI0 default CE0</td></tr>
<tr><td>CE1</td><td>GPIO7</td><td>SPI0 default CE1</td></tr>
<tr><td>CE2</td><td>GPIO24</td><td>Extended CE</td></tr>
<tr><td>CE3</td><td>GPIO23</td><td>Extended CE</td></tr>
<tr><td>CE4</td><td>GPIO18</td><td>Extended CE</td></tr>
</table>

<h3>Module Types</h3>
<p><b>PI-SPI-DIN-4KO (Relay Output):</b></p>
<ul>
<li>4 SPDT relay outputs, 2A AC/DC rating</li>
<li>Uses MCP23S08 GPIO expander</li>
<li><b>Stacking:</b> Up to 4 modules per CE using addresses 0-3</li>
<li>Set address with jumpers J3-A0 and J3-A1</li>
</ul>

<p><b>PI-SPI-DIN-8AI (Analog Input):</b></p>
<ul>
<li>8 analog input channels</li>
<li>0-10V or 4-20mA input (jumper selectable)</li>
<li>16-bit ADC resolution</li>
</ul>

<p><b>PI-SPI-DIN-8DI (Digital Input):</b></p>
<ul>
<li>8 digital input channels</li>
<li>12-24V input compatible</li>
<li>Optically isolated</li>
</ul>

<p><b>PI-SPI-DIN-4AO (Analog Output):</b></p>
<ul>
<li>4 analog output channels</li>
<li>0-10V output range</li>
<li>12-bit DAC resolution</li>
</ul>

<h3>Wiring Guide</h3>
<ol>
<li>Connect PI-SPI-DIN-RTC-RS485 base module to Pi GPIO header</li>
<li>Daisy-chain I/O modules using 16-pin ribbon cables</li>
<li>Apply 9-24VDC power to each module</li>
<li>Configure CE and address settings to match this dialog</li>
</ol>

<h3>Tips</h3>
<ul>
<li>Use descriptive names for modules and channels</li>
<li>Document which physical terminal each channel connects to</li>
<li>For 4KO modules, set hardware address jumpers to match config</li>
<li>Test modules individually before full system integration</li>
</ul>
        """
        
        QMessageBox.information(self, "SPI Module Configuration Help", help_text)

