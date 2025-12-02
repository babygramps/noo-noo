"""
Hardware Configuration Dialog

Unified dialog for all hardware configuration:
- SPI Modules: Widgetlords PI-SPI-DIN relay/analog/digital I/O
- Modbus/RS485: TLB4 load cell transmitter settings
- Visual module cards with inline channel editing
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
    QComboBox,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QLabel,
    QGroupBox,
    QMessageBox,
    QHeaderView,
    QAbstractItemView,
    QDoubleSpinBox,
    QWidget,
    QScrollArea,
    QFrame,
    QSplitter,
    QGridLayout,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QTabWidget,
    QTabBar,
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen

logger = logging.getLogger(__name__)


# Light theme color palette
COLORS = {
    "bg_dark": "#f5f5f5",
    "bg_card": "#ffffff",
    "bg_hover": "#e8e8e8",
    "accent_blue": "#2563eb",
    "accent_cyan": "#0891b2",
    "text_primary": "#1f2937",
    "text_secondary": "#4b5563",
    "text_muted": "#9ca3af",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "relay": "#dc2626",
    "analog_in": "#0891b2",
    "digital_in": "#2563eb",
    "analog_out": "#d97706",
    "border": "#d1d5db",
}

# Module type definitions
MODULE_TYPES = {
    "PI-SPI-DIN-4KO": {
        "short": "4KO",
        "description": "4x Relay Outputs",
        "detail": "2A AC/DC SPDT relays",
        "io_type": "relay_output",
        "channels": 4,
        "max_per_ce": 4,
        "icon": "",
        "color": COLORS["relay"],
        "channel_prefix": "K",
    },
    "PI-SPI-DIN-8AI": {
        "short": "8AI",
        "description": "8x Analog Inputs",
        "detail": "0-10V / 4-20mA",
        "io_type": "analog_input",
        "channels": 8,
        "max_per_ce": 1,
        "icon": "",
        "color": COLORS["analog_in"],
        "channel_prefix": "AI",
    },
    "PI-SPI-DIN-8DI": {
        "short": "8DI",
        "description": "8x Digital Inputs",
        "detail": "12-24V isolated",
        "io_type": "digital_input",
        "channels": 8,
        "max_per_ce": 1,
        "icon": "",
        "color": COLORS["digital_in"],
        "channel_prefix": "DI",
    },
    "PI-SPI-DIN-4AO": {
        "short": "4AO",
        "description": "4x Analog Outputs",
        "detail": "0-10V output",
        "io_type": "analog_output",
        "channels": 4,
        "max_per_ce": 1,
        "icon": "",
        "color": COLORS["analog_out"],
        "channel_prefix": "AO",
    },
}

CHIP_ENABLES = ["CE0", "CE1", "CE2", "CE3", "CE4"]


class ChannelWidget(QFrame):
    """Compact inline channel editor widget."""
    
    changed = pyqtSignal()
    
    def __init__(self, channel_num: int, io_type: str, config: Dict, color: str, parent=None):
        super().__init__(parent)
        self.channel_num = channel_num
        self.io_type = io_type
        self.config = config
        self.color = color
        self.init_ui()
    
    def init_ui(self):
        self.setFixedHeight(44)
        self.setStyleSheet(f"""
            ChannelWidget {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['bg_hover']};
                border-radius: 6px;
                margin: 2px 0;
            }}
            ChannelWidget:hover {{
                border-color: {self.color};
            }}
            QLineEdit {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_primary']};
                font-size: 11px;
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                background-color: {COLORS['bg_hover']};
                border-radius: 3px;
            }}
            QCheckBox {{
                spacing: 4px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid {COLORS['text_muted']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {self.color};
                border-color: {self.color};
            }}
            QDoubleSpinBox, QSpinBox {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_secondary']};
                font-size: 10px;
                padding: 0 2px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # Channel indicator
        ch_label = QLabel(f"{self.channel_num}")
        ch_label.setFixedWidth(20)
        ch_label.setAlignment(Qt.AlignCenter)
        ch_label.setStyleSheet(f"""
            background-color: {self.color};
            color: white;
            font-weight: bold;
            font-size: 10px;
            border-radius: 10px;
            padding: 2px;
        """)
        layout.addWidget(ch_label)
        
        # Enabled checkbox
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(self.config.get("enabled", True))
        self.enabled_check.setToolTip("Enable/disable this channel")
        self.enabled_check.stateChanged.connect(self._on_change)
        layout.addWidget(self.enabled_check)
        
        # Name input
        self.name_edit = QLineEdit(self.config.get("name", f"Channel {self.channel_num}"))
        self.name_edit.setPlaceholderText("Channel name...")
        self.name_edit.setMinimumWidth(120)
        self.name_edit.textChanged.connect(self._on_change)
        layout.addWidget(self.name_edit, stretch=2)
        
        # Type-specific controls
        if self.io_type == "analog_input":
            # Voltage range
            range_label = QLabel("Range:")
            range_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            layout.addWidget(range_label)
            
            self.min_spin = QDoubleSpinBox()
            self.min_spin.setRange(-100, 100)
            self.min_spin.setValue(self.config.get("min_value", 0.0))
            self.min_spin.setFixedWidth(50)
            self.min_spin.setSuffix("V")
            self.min_spin.valueChanged.connect(self._on_change)
            layout.addWidget(self.min_spin)
            
            dash = QLabel("-")
            dash.setStyleSheet(f"color: {COLORS['text_muted']};")
            layout.addWidget(dash)
            
            self.max_spin = QDoubleSpinBox()
            self.max_spin.setRange(-100, 100)
            self.max_spin.setValue(self.config.get("max_value", 10.0))
            self.max_spin.setFixedWidth(50)
            self.max_spin.setSuffix("V")
            self.max_spin.valueChanged.connect(self._on_change)
            layout.addWidget(self.max_spin)
            
        elif self.io_type == "digital_input":
            # Invert option
            self.invert_check = QCheckBox("Invert")
            self.invert_check.setChecked(self.config.get("inverted", False))
            self.invert_check.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            self.invert_check.stateChanged.connect(self._on_change)
            layout.addWidget(self.invert_check)
        
        # Description
        self.desc_edit = QLineEdit(self.config.get("description", ""))
        self.desc_edit.setPlaceholderText("Description...")
        self.desc_edit.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
        self.desc_edit.textChanged.connect(self._on_change)
        layout.addWidget(self.desc_edit, stretch=2)
    
    def _on_change(self):
        self.config["enabled"] = self.enabled_check.isChecked()
        self.config["name"] = self.name_edit.text()
        self.config["description"] = self.desc_edit.text()
        
        if self.io_type == "analog_input":
            self.config["min_value"] = self.min_spin.value()
            self.config["max_value"] = self.max_spin.value()
        elif self.io_type == "digital_input":
            self.config["inverted"] = self.invert_check.isChecked()
        
        self.changed.emit()
    
    def get_config(self) -> Dict:
        return self.config


class ModuleCard(QFrame):
    """Modern module card with inline channel editing."""
    
    removed = pyqtSignal(object)
    changed = pyqtSignal()
    
    def __init__(self, module_config: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.module_config = module_config
        self.channel_widgets: List[ChannelWidget] = []
        self.expanded = True
        self.init_ui()
    
    def init_ui(self):
        module_type = self.module_config.get("module_type", "PI-SPI-DIN-4KO")
        info = MODULE_TYPES.get(module_type, MODULE_TYPES["PI-SPI-DIN-4KO"])
        color = info["color"]
        
        self.setStyleSheet(f"""
            ModuleCard {{
                background-color: {COLORS['bg_card']};
                border: 2px solid {color}40;
                border-radius: 12px;
                margin: 4px;
            }}
            ModuleCard:hover {{
                border-color: {color};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header section
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {color}20;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 1px solid {color}40;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        # Module icon and type badge
        icon_label = QLabel(info["icon"])
        icon_label.setStyleSheet(f"font-size: 24px;")
        header_layout.addWidget(icon_label)
        
        # Module info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        # Name row
        name_row = QHBoxLayout()
        self.name_edit = QLineEdit(self.module_config.get("name", ""))
        self.name_edit.setPlaceholderText("Module name...")
        self.name_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                border: none;
                color: {COLORS['text_primary']};
                font-size: 14px;
                font-weight: bold;
                padding: 0;
            }}
            QLineEdit:focus {{
                background-color: {COLORS['bg_hover']};
                border-radius: 4px;
                padding: 2px 6px;
            }}
        """)
        self.name_edit.textChanged.connect(self._on_name_change)
        name_row.addWidget(self.name_edit)
        
        # Type badge
        type_badge = QLabel(info["short"])
        type_badge.setStyleSheet(f"""
            background-color: {color};
            color: white;
            font-weight: bold;
            font-size: 10px;
            padding: 3px 8px;
            border-radius: 4px;
        """)
        name_row.addWidget(type_badge)
        
        info_layout.addLayout(name_row)
        
        # Description row
        desc_label = QLabel(f"{info['description']} • {info['detail']}")
        desc_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        info_layout.addWidget(desc_label)
        
        header_layout.addLayout(info_layout, stretch=1)
        
        # Chip Enable selector
        ce_layout = QVBoxLayout()
        ce_layout.setSpacing(2)
        
        ce_label = QLabel("Chip Enable")
        ce_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
        ce_label.setAlignment(Qt.AlignCenter)
        ce_layout.addWidget(ce_label)
        
        self.ce_combo = QComboBox()
        self.ce_combo.addItems(CHIP_ENABLES)
        self.ce_combo.setCurrentText(self.module_config.get("chip_enable", "CE0"))
        self.ce_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {color};
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 4px 12px;
                border-radius: 4px;
                min-width: 60px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                selection-background-color: {color};
            }}
        """)
        self.ce_combo.currentTextChanged.connect(self._on_ce_change)
        ce_layout.addWidget(self.ce_combo)
        
        header_layout.addLayout(ce_layout)
        
        # Address selector (only for 4KO)
        if info["max_per_ce"] > 1:
            addr_layout = QVBoxLayout()
            addr_layout.setSpacing(2)
            
            addr_label = QLabel("Address")
            addr_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
            addr_label.setAlignment(Qt.AlignCenter)
            addr_layout.addWidget(addr_label)
            
            self.addr_spin = QSpinBox()
            self.addr_spin.setRange(0, 3)
            self.addr_spin.setValue(self.module_config.get("address", 0))
            self.addr_spin.setStyleSheet(f"""
                QSpinBox {{
                    background-color: {COLORS['bg_hover']};
                    color: {COLORS['text_primary']};
                    font-weight: bold;
                    font-size: 11px;
                    padding: 4px 8px;
                    border-radius: 4px;
                    min-width: 50px;
                }}
            """)
            self.addr_spin.valueChanged.connect(self._on_addr_change)
            addr_layout.addWidget(self.addr_spin)
            
            header_layout.addLayout(addr_layout)
        else:
            self.addr_spin = None
        
        # Expand/collapse button
        self.expand_btn = QToolButton()
        self.expand_btn.setText("▼")
        self.expand_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                font-size: 12px;
                border: none;
                padding: 4px;
            }}
            QToolButton:hover {{
                color: {COLORS['text_primary']};
            }}
        """)
        self.expand_btn.clicked.connect(self.toggle_expand)
        header_layout.addWidget(self.expand_btn)
        
        # Remove button
        remove_btn = QToolButton()
        remove_btn.setText("✕")
        remove_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {COLORS['text_muted']};
                font-size: 14px;
                font-weight: bold;
                border: none;
                padding: 4px;
            }}
            QToolButton:hover {{
                color: {COLORS['danger']};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.removed.emit(self))
        header_layout.addWidget(remove_btn)
        
        main_layout.addWidget(header)
        
        # Channels section
        self.channels_frame = QFrame()
        self.channels_frame.setStyleSheet("background-color: transparent;")
        channels_layout = QVBoxLayout(self.channels_frame)
        channels_layout.setContentsMargins(12, 8, 12, 12)
        channels_layout.setSpacing(4)
        
        # Channel header
        ch_header = QLabel("CHANNELS")
        ch_header.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 10px;
            font-weight: bold;
            letter-spacing: 1px;
            padding: 4px 0;
        """)
        channels_layout.addWidget(ch_header)
        
        # Initialize channels
        self._init_channels(channels_layout, info)
        
        main_layout.addWidget(self.channels_frame)
    
    def _init_channels(self, layout: QVBoxLayout, info: Dict):
        """Initialize channel widgets."""
        io_type = info["io_type"]
        num_channels = info["channels"]
        color = info["color"]
        prefix = info["channel_prefix"]
        
        # Get or create channel configs
        channels = self.module_config.get("channels", [])
        if len(channels) != num_channels:
            channels = [
                {"channel": i, "name": f"{prefix}{i}", "enabled": True, "description": ""}
                for i in range(num_channels)
            ]
            self.module_config["channels"] = channels
        
        # Create channel widgets
        for i, ch_config in enumerate(channels):
            ch_config["channel"] = i
            widget = ChannelWidget(i, io_type, ch_config, color, self)
            widget.changed.connect(self.changed.emit)
            layout.addWidget(widget)
            self.channel_widgets.append(widget)
    
    def toggle_expand(self):
        """Toggle channel section visibility."""
        self.expanded = not self.expanded
        self.channels_frame.setVisible(self.expanded)
        self.expand_btn.setText("▼" if self.expanded else "▶")
    
    def _on_name_change(self, text: str):
        self.module_config["name"] = text
        self.changed.emit()
    
    def _on_ce_change(self, text: str):
        self.module_config["chip_enable"] = text
        self.changed.emit()
    
    def _on_addr_change(self, value: int):
        self.module_config["address"] = value
        self.changed.emit()
    
    def get_config(self) -> Dict:
        """Get current module configuration."""
        config = {
            "name": self.name_edit.text(),
            "module_type": self.module_config.get("module_type", "PI-SPI-DIN-4KO"),
            "chip_enable": self.ce_combo.currentText(),
            "address": self.addr_spin.value() if self.addr_spin else 0,
            "channels": [w.get_config() for w in self.channel_widgets],
        }
        return config


class ModuleTypeButton(QPushButton):
    """Styled button for adding module types."""
    
    def __init__(self, mod_type: str, info: Dict, parent=None):
        super().__init__(parent)
        self.mod_type = mod_type
        self.info = info
        self.init_ui()
    
    def init_ui(self):
        color = self.info["color"]
        self.setText(f"{self.info['icon']}  {self.info['short']}")
        self.setToolTip(f"{self.info['description']}\n{self.info['detail']}")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(40)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color}30;
                color: {color};
                font-weight: bold;
                font-size: 12px;
                border: 2px solid {color}50;
                border-radius: 8px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {color}50;
                border-color: {color};
            }}
            QPushButton:pressed {{
                background-color: {color};
                color: white;
            }}
        """)


class SPIConfigDialog(QDialog):
    """
    Unified hardware configuration dialog.
    
    Features:
    - Tabbed interface: SPI Modules + Modbus/RS485
    - Visual module cards with inline channel editing
    - Quick-add buttons for each module type
    - Dark theme with modern styling
    """
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file_path = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        self.spi_modules: List[Dict[str, Any]] = []
        self.module_cards: List[ModuleCard] = []
        self.modbus_config: Dict[str, Any] = {}
        self.test_interface = None  # For manual I/O testing
        
        self.init_ui()
        self.load_config()
        
        logger.info("Hardware Configuration dialog initialized")
    
    def closeEvent(self, event):
        """Clean up when dialog closes."""
        if self.test_interface:
            try:
                self.test_interface.disconnect()
                logger.info("Disconnected test interface")
            except Exception as e:
                logger.warning(f"Error disconnecting test interface: {e}")
        super().closeEvent(event)
    
    def init_ui(self):
        self.setWindowTitle("Hardware Configuration")
        self.setMinimumSize(950, 750)
        self.resize(1050, 800)
        
        # Light theme
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg_dark']};
            }}
            QScrollArea {{
                background-color: transparent;
                border: none;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['bg_card']};
                width: 10px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent_blue']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QTabWidget::pane {{
                border: none;
                background-color: transparent;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_secondary']};
                border: 1px solid {COLORS['border']};
                border-bottom: none;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['accent_blue']};
                font-weight: bold;
                border-bottom: 2px solid {COLORS['accent_blue']};
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {COLORS['bg_hover']};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("Hardware Configuration")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 22px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Configure SPI modules, Modbus communication, and I/O assignments")
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(subtitle)
        
        main_layout.addLayout(header_layout)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)
        
        # SPI Modules tab
        spi_tab = self.create_spi_tab()
        self.tab_widget.addTab(spi_tab, "SPI Modules")
        
        # Test I/O tab
        test_tab = self.create_test_io_tab()
        self.tab_widget.addTab(test_tab, "Test I/O")
        
        # Modbus tab
        modbus_tab = self.create_modbus_tab()
        self.tab_widget.addTab(modbus_tab, "Modbus / RS485")
        
        main_layout.addWidget(self.tab_widget, stretch=1)
        
        # Footer buttons
        footer = self.create_footer()
        main_layout.addLayout(footer)
    
    def create_spi_tab(self) -> QWidget:
        """Create the SPI modules configuration tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)
        
        # Quick-add toolbar
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Main content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Modules list (main area)
        modules_panel = self.create_modules_panel()
        content_layout.addWidget(modules_panel, stretch=3)
        
        # Sidebar with CE overview
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar, stretch=1)
        
        layout.addLayout(content_layout, stretch=1)
        
        return tab
    
    def create_test_io_tab(self) -> QWidget:
        """Create the Test I/O tab for manual hardware testing."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 12, 0, 0)
        main_layout.setSpacing(16)
        
        # Warning banner
        warning_frame = QFrame()
        warning_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #fef3c7;
                border: 1px solid {COLORS['warning']};
                border-radius: 6px;
                padding: 12px;
            }}
        """)
        warning_layout = QHBoxLayout(warning_frame)
        warning_icon = QLabel("WARNING")
        warning_icon.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLORS['warning']};")
        warning_layout.addWidget(warning_icon)
        warning_text = QLabel(
            "<b>Manual Hardware Test</b> - Use this panel to test individual relays and valves. "
            "Make sure it's safe to activate equipment before toggling."
        )
        warning_text.setStyleSheet(f"color: #92400e; font-size: 11px;")
        warning_text.setWordWrap(True)
        warning_layout.addWidget(warning_text, stretch=1)
        main_layout.addWidget(warning_frame)
        
        # Connection status
        status_frame = QFrame()
        status_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        status_layout = QHBoxLayout(status_frame)
        
        self.connection_status_label = QLabel("Not Connected")
        self.connection_status_label.setStyleSheet(f"color: {COLORS['danger']}; font-weight: bold;")
        status_layout.addWidget(self.connection_status_label)
        
        status_layout.addStretch()
        
        connect_btn = QPushButton("Connect to Hardware")
        connect_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #00b85c;
            }}
        """)
        connect_btn.clicked.connect(self.connect_for_testing)
        status_layout.addWidget(connect_btn)
        
        refresh_btn = QPushButton("Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_cyan']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_blue']};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh_test_io)
        status_layout.addWidget(refresh_btn)
        
        main_layout.addWidget(status_frame)
        
        # Scroll area for I/O controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.test_io_layout = QVBoxLayout(scroll_content)
        self.test_io_layout.setSpacing(16)
        
        # Relay outputs section
        self.relay_test_frame = self.create_relay_test_section()
        self.test_io_layout.addWidget(self.relay_test_frame)
        
        # Analog inputs section
        self.analog_test_frame = self.create_analog_test_section()
        self.test_io_layout.addWidget(self.analog_test_frame)
        
        # Digital inputs section
        self.digital_test_frame = self.create_digital_test_section()
        self.test_io_layout.addWidget(self.digital_test_frame)
        
        self.test_io_layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll, stretch=1)
        
        return tab
    
    def create_relay_test_section(self) -> QFrame:
        """Create the relay testing section."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Relay Outputs")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        header.addWidget(title)
        
        all_off_btn = QPushButton("All OFF")
        all_off_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['danger']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: #e55555;
            }}
        """)
        all_off_btn.clicked.connect(self.all_relays_off)
        header.addWidget(all_off_btn)
        
        header.addStretch()
        layout.addLayout(header)
        
        # Relay buttons container
        self.relay_buttons_layout = QGridLayout()
        self.relay_buttons_layout.setSpacing(8)
        self.relay_toggle_buttons: Dict[str, QPushButton] = {}
        
        layout.addLayout(self.relay_buttons_layout)
        
        # Placeholder text
        self.relay_placeholder = QLabel("Configure relay modules in the SPI Modules tab, then connect to test")
        self.relay_placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic; padding: 20px;")
        self.relay_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.relay_placeholder)
        
        return frame
    
    def create_analog_test_section(self) -> QFrame:
        """Create the analog input testing section."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        # Header
        title = QLabel("Analog Inputs")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Analog readings container
        self.analog_readings_layout = QGridLayout()
        self.analog_readings_layout.setSpacing(8)
        self.analog_reading_labels: Dict[str, QLabel] = {}
        
        layout.addLayout(self.analog_readings_layout)
        
        # Placeholder text
        self.analog_placeholder = QLabel("Configure analog input modules in the SPI Modules tab, then connect to test")
        self.analog_placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic; padding: 20px;")
        self.analog_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.analog_placeholder)
        
        return frame
    
    def create_digital_test_section(self) -> QFrame:
        """Create the digital input testing section."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)
        
        # Header
        title = QLabel("Digital Inputs")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Digital indicators container
        self.digital_indicators_layout = QGridLayout()
        self.digital_indicators_layout.setSpacing(8)
        self.digital_indicator_labels: Dict[str, QLabel] = {}
        
        layout.addLayout(self.digital_indicators_layout)
        
        # Placeholder text
        self.digital_placeholder = QLabel("Configure digital input modules in the SPI Modules tab, then connect to test")
        self.digital_placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; font-style: italic; padding: 20px;")
        self.digital_placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.digital_placeholder)
        
        return frame
    
    def connect_for_testing(self):
        """Connect to hardware for testing."""
        try:
            from ...daq.widgetlords_interface import WidgetLordsInterface
            
            # Get current config from cards
            current_modules = [card.get_config() for card in self.module_cards]
            
            if not current_modules:
                QMessageBox.warning(
                    self, "No Modules",
                    "Please configure at least one SPI module in the SPI Modules tab first."
                )
                return
            
            # Create and connect interface
            self.test_interface = WidgetLordsInterface(spi_modules_config=current_modules)
            
            if self.test_interface.connect():
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
                logger.info("Connected to hardware for testing")
                
                # Populate test controls
                self.populate_test_controls()
            else:
                self.connection_status_label.setText("Connection Failed")
                self.connection_status_label.setStyleSheet(f"color: {COLORS['danger']}; font-weight: bold;")
                QMessageBox.warning(self, "Connection Failed", "Could not connect to hardware.")
                
        except ImportError:
            # Mock mode for development
            self.connection_status_label.setText("Mock Mode (no hardware)")
            self.connection_status_label.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
            self.test_interface = None
            self.populate_test_controls()
            logger.warning("Widgetlords library not available - using mock mode")
            
        except Exception as e:
            logger.error(f"Failed to connect for testing: {e}")
            QMessageBox.critical(self, "Error", f"Failed to connect:\n{e}")
    
    def populate_test_controls(self):
        """Populate the test controls based on configured modules."""
        # Get current module configs
        current_modules = [card.get_config() for card in self.module_cards]
        
        # Clear existing controls
        self.clear_layout(self.relay_buttons_layout)
        self.clear_layout(self.analog_readings_layout)
        self.clear_layout(self.digital_indicators_layout)
        self.relay_toggle_buttons.clear()
        self.analog_reading_labels.clear()
        self.digital_indicator_labels.clear()
        
        relay_count = 0
        analog_count = 0
        digital_count = 0
        
        for module in current_modules:
            mod_type = module.get("module_type", "")
            mod_name = module.get("name", "unknown")
            channels = module.get("channels", [])
            
            if mod_type == "PI-SPI-DIN-4KO":
                # Add relay toggle buttons
                for ch in channels:
                    if ch.get("enabled", True):
                        ch_name = ch.get("name", f"K{ch.get('channel', 0)}")
                        ch_desc = ch.get("description", "")
                        
                        btn = self.create_relay_toggle_button(mod_name, ch_name, ch_desc, ch.get("channel", 0))
                        row = relay_count // 2
                        col = relay_count % 2
                        self.relay_buttons_layout.addWidget(btn, row, col)
                        self.relay_toggle_buttons[f"{mod_name}:{ch_name}"] = btn
                        relay_count += 1
                        
            elif mod_type == "PI-SPI-DIN-8AI":
                # Add analog reading displays
                for ch in channels:
                    if ch.get("enabled", True):
                        ch_name = ch.get("name", f"AI{ch.get('channel', 0)}")
                        ch_desc = ch.get("description", "")
                        
                        reading_widget = self.create_analog_reading_widget(mod_name, ch_name, ch_desc)
                        row = analog_count // 2
                        col = analog_count % 2
                        self.analog_readings_layout.addWidget(reading_widget, row, col)
                        analog_count += 1
                        
            elif mod_type == "PI-SPI-DIN-8DI":
                # Add digital input indicators
                for ch in channels:
                    if ch.get("enabled", True):
                        ch_name = ch.get("name", f"DI{ch.get('channel', 0)}")
                        ch_desc = ch.get("description", "")
                        
                        indicator_widget = self.create_digital_indicator_widget(mod_name, ch_name, ch_desc)
                        row = digital_count // 4
                        col = digital_count % 4
                        self.digital_indicators_layout.addWidget(indicator_widget, row, col)
                        digital_count += 1
        
        # Show/hide placeholders
        self.relay_placeholder.setVisible(relay_count == 0)
        self.analog_placeholder.setVisible(analog_count == 0)
        self.digital_placeholder.setVisible(digital_count == 0)
    
    def create_relay_toggle_button(self, module_name: str, channel_name: str, description: str, channel_num: int) -> QFrame:
        """Create a relay toggle button widget."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)
        
        # Header with name
        name_label = QLabel(f"<b>{channel_name}</b>")
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        layout.addWidget(name_label)
        
        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        # Module/channel info
        info_label = QLabel(f"{module_name} • Ch {channel_num}")
        info_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 9px;")
        layout.addWidget(info_label)
        
        # Toggle button
        toggle_btn = QPushButton("OFF")
        toggle_btn.setCheckable(True)
        toggle_btn.setProperty("module_name", module_name)
        toggle_btn.setProperty("channel_name", channel_name)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['text_secondary']};
                border: 2px solid {COLORS['text_muted']};
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background-color: {COLORS['relay']};
                color: white;
                border-color: {COLORS['relay']};
            }}
            QPushButton:hover {{
                border-color: {COLORS['relay']};
            }}
        """)
        toggle_btn.clicked.connect(lambda checked, m=module_name, c=channel_name, b=toggle_btn: 
                                   self.toggle_relay(m, c, checked, b))
        layout.addWidget(toggle_btn)
        
        # Store reference
        frame.toggle_btn = toggle_btn
        
        return frame
    
    def create_analog_reading_widget(self, module_name: str, channel_name: str, description: str) -> QFrame:
        """Create an analog reading display widget."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        
        # Header with name
        name_label = QLabel(f"<b>{channel_name}</b>")
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 12px;")
        layout.addWidget(name_label)
        
        # Description
        if description:
            desc_label = QLabel(description)
            desc_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            layout.addWidget(desc_label)
        
        # Reading value
        reading_label = QLabel("-- V")
        reading_label.setStyleSheet(f"""
            color: {COLORS['analog_in']};
            font-size: 20px;
            font-weight: bold;
            padding: 8px;
        """)
        reading_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(reading_label)
        
        # Store reference
        self.analog_reading_labels[f"{module_name}:{channel_name}"] = reading_label
        
        return frame
    
    def create_digital_indicator_widget(self, module_name: str, channel_name: str, description: str) -> QFrame:
        """Create a digital input indicator widget."""
        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 8px;
                padding: 10px;
            }}
        """)
        
        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Name
        name_label = QLabel(f"<b>{channel_name}</b>")
        name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 11px;")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        # Status indicator
        status_label = QLabel("OFF")
        status_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
            background-color: {COLORS['bg_dark']};
            border-radius: 4px;
        """)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setProperty("state", False)
        layout.addWidget(status_label)
        
        # State text
        state_text = QLabel("--")
        state_text.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        state_text.setAlignment(Qt.AlignCenter)
        layout.addWidget(state_text)
        
        # Store reference
        key = f"{module_name}:{channel_name}"
        self.digital_indicator_labels[key] = (status_label, state_text)
        
        return frame
    
    def toggle_relay(self, module_name: str, channel_name: str, state: bool, button: QPushButton):
        """Toggle a relay on/off."""
        button.setText("ON" if state else "OFF")
        
        if hasattr(self, 'test_interface') and self.test_interface:
            try:
                success = self.test_interface.set_relay(module_name, channel_name, state)
                if success:
                    logger.info(f"Relay {module_name}:{channel_name} set to {'ON' if state else 'OFF'}")
                else:
                    logger.warning(f"Failed to set relay {module_name}:{channel_name}")
                    button.setChecked(not state)  # Revert
                    button.setText("OFF" if state else "ON")
            except Exception as e:
                logger.error(f"Error toggling relay: {e}")
                button.setChecked(not state)
                button.setText("OFF" if state else "ON")
        else:
            # Mock mode
            logger.info(f"[MOCK] Relay {module_name}:{channel_name} would be {'ON' if state else 'OFF'}")
    
    def all_relays_off(self):
        """Turn all relays off."""
        for key, frame in self.relay_toggle_buttons.items():
            if hasattr(frame, 'toggle_btn'):
                btn = frame.toggle_btn
                if btn.isChecked():
                    btn.setChecked(False)
                    btn.setText("OFF")
                    parts = key.split(":")
                    if len(parts) == 2:
                        self.toggle_relay(parts[0], parts[1], False, btn)
    
    def refresh_test_io(self):
        """Refresh analog and digital input readings."""
        if hasattr(self, 'test_interface') and self.test_interface:
            try:
                data = self.test_interface.read()
                
                # Update analog readings
                analog_data = data.get("analog_inputs", {})
                for mod_name, readings in analog_data.items():
                    for ch_name, value in readings.items():
                        key = f"{mod_name}:{ch_name}"
                        if key in self.analog_reading_labels:
                            self.analog_reading_labels[key].setText(f"{value:.2f} V")
                
                # Update digital readings
                digital_data = data.get("digital_inputs", {})
                for mod_name, readings in digital_data.items():
                    for ch_name, value in readings.items():
                        key = f"{mod_name}:{ch_name}"
                        if key in self.digital_indicator_labels:
                            status_label, state_text = self.digital_indicator_labels[key]
                            if value:
                                status_label.setStyleSheet(f"color: {COLORS['success']}; font-size: 32px;")
                                state_text.setText("HIGH")
                                state_text.setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")
                            else:
                                status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 32px;")
                                state_text.setText("LOW")
                                state_text.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
                            
            except Exception as e:
                logger.error(f"Error reading inputs: {e}")
        else:
            # Mock mode - show placeholder values
            for key, label in self.analog_reading_labels.items():
                label.setText("0.00 V")
            for key, (status_label, state_text) in self.digital_indicator_labels.items():
                status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 32px;")
                state_text.setText("--")
    
    def clear_layout(self, layout):
        """Clear all widgets from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def create_modbus_tab(self) -> QWidget:
        """Create the Modbus/RS485 configuration tab."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 12, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(16)
        
        # Info banner
        info_frame = QFrame()
        info_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['warning']}20;
                border: 1px solid {COLORS['warning']}60;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        info_layout = QVBoxLayout(info_frame)
        info_text = QLabel(
            "<b>TLB4 Load Cell Transmitter</b><br>"
            "Configure RS485/Modbus RTU communication for the Laumas TLB4.<br>"
            "• Supports up to 4 load cells with 24-bit resolution<br>"
            "• Connection: USB-RS485 adapter to TLB4 A/B terminals"
        )
        info_text.setStyleSheet(f"color: {COLORS['warning']}; font-size: 11px;")
        info_text.setWordWrap(True)
        info_layout.addWidget(info_text)
        layout.addWidget(info_frame)
        
        # Enable toggle
        enable_frame = QFrame()
        enable_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        enable_layout = QHBoxLayout(enable_frame)
        
        self.modbus_enabled_check = QCheckBox("Enable Modbus Communication")
        self.modbus_enabled_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_primary']};
                font-size: 13px;
                font-weight: bold;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border-radius: 4px;
                border: 2px solid {COLORS['text_muted']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['success']};
                border-color: {COLORS['success']};
            }}
        """)
        enable_layout.addWidget(self.modbus_enabled_check)
        enable_layout.addStretch()
        layout.addWidget(enable_frame)
        
        # Connection settings
        conn_group = self.create_modbus_connection_group()
        layout.addWidget(conn_group)
        
        # Protocol settings
        protocol_group = self.create_modbus_protocol_group()
        layout.addWidget(protocol_group)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        return tab
    
    def create_modbus_connection_group(self) -> QFrame:
        """Create the Modbus connection settings group."""
        group = QFrame()
        group.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 16px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QLineEdit, QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['bg_hover']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
            QLineEdit:focus, QComboBox:focus {{
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Connection Settings")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Form layout
        form = QGridLayout()
        form.setSpacing(12)
        form.setColumnStretch(1, 1)
        
        # Serial Port
        port_label = QLabel("Serial Port:")
        port_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        form.addWidget(port_label, 0, 0)
        
        port_row = QHBoxLayout()
        self.modbus_port_edit = QLineEdit()
        self.modbus_port_edit.setPlaceholderText("/dev/ttyUSB0 or COM3")
        port_row.addWidget(self.modbus_port_edit, stretch=1)
        
        test_btn = QPushButton("Test")
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent_cyan']};
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {COLORS['accent_blue']};
            }}
        """)
        test_btn.clicked.connect(self.test_modbus_connection)
        port_row.addWidget(test_btn)
        
        form.addLayout(port_row, 0, 1)
        
        # Baudrate
        baud_label = QLabel("Baudrate:")
        baud_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        form.addWidget(baud_label, 1, 0)
        
        self.modbus_baudrate_combo = QComboBox()
        self.modbus_baudrate_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        form.addWidget(self.modbus_baudrate_combo, 1, 1)
        
        # Parity
        parity_label = QLabel("Parity:")
        parity_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        form.addWidget(parity_label, 2, 0)
        
        self.modbus_parity_combo = QComboBox()
        self.modbus_parity_combo.addItems(["None", "Even", "Odd"])
        form.addWidget(self.modbus_parity_combo, 2, 1)
        
        # Data/Stop bits row
        bits_row = QHBoxLayout()
        
        databits_label = QLabel("Data Bits:")
        databits_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bits_row.addWidget(databits_label)
        
        self.modbus_databits_combo = QComboBox()
        self.modbus_databits_combo.addItems(["8", "7"])
        self.modbus_databits_combo.setFixedWidth(80)
        bits_row.addWidget(self.modbus_databits_combo)
        
        bits_row.addSpacing(20)
        
        stopbits_label = QLabel("Stop Bits:")
        stopbits_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bits_row.addWidget(stopbits_label)
        
        self.modbus_stopbits_combo = QComboBox()
        self.modbus_stopbits_combo.addItems(["1", "2"])
        self.modbus_stopbits_combo.setFixedWidth(80)
        bits_row.addWidget(self.modbus_stopbits_combo)
        
        bits_row.addStretch()
        
        form.addWidget(QLabel(""), 3, 0)  # Spacer
        form.addLayout(bits_row, 3, 1)
        
        layout.addLayout(form)
        
        return group
    
    def create_modbus_protocol_group(self) -> QFrame:
        """Create the Modbus protocol settings group."""
        group = QFrame()
        group.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 16px;
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QSpinBox, QDoubleSpinBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['bg_hover']};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 12px;
            }}
        """)
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Protocol Settings")
        title.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)
        
        # Form layout
        form = QGridLayout()
        form.setSpacing(12)
        form.setColumnStretch(1, 1)
        
        # Slave Address
        slave_label = QLabel("Slave Address:")
        slave_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        form.addWidget(slave_label, 0, 0)
        
        self.modbus_slave_spin = QSpinBox()
        self.modbus_slave_spin.setRange(1, 247)
        self.modbus_slave_spin.setValue(1)
        form.addWidget(self.modbus_slave_spin, 0, 1)
        
        # Timeout
        timeout_label = QLabel("Timeout:")
        timeout_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        form.addWidget(timeout_label, 1, 0)
        
        self.modbus_timeout_spin = QDoubleSpinBox()
        self.modbus_timeout_spin.setRange(0.1, 10.0)
        self.modbus_timeout_spin.setValue(1.0)
        self.modbus_timeout_spin.setSuffix(" sec")
        self.modbus_timeout_spin.setSingleStep(0.1)
        form.addWidget(self.modbus_timeout_spin, 1, 1)
        
        # Debug mode
        self.modbus_debug_check = QCheckBox("Enable debug logging")
        self.modbus_debug_check.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text_muted']};
                font-size: 11px;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 2px solid {COLORS['text_muted']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent_cyan']};
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        form.addWidget(self.modbus_debug_check, 2, 1)
        
        layout.addLayout(form)
        
        return group
    
    def test_modbus_connection(self):
        """Test the Modbus connection."""
        port = self.modbus_port_edit.text().strip()
        if not port:
            QMessageBox.warning(self, "Test Connection", "Please enter a serial port first.")
            return
        
        QMessageBox.information(
            self, "Test Connection",
            f"Connection test for port: {port}\n\n"
            f"Baudrate: {self.modbus_baudrate_combo.currentText()}\n"
            f"Slave Address: {self.modbus_slave_spin.value()}\n\n"
            "Full connection testing requires actual hardware."
        )
    
    def create_toolbar(self) -> QFrame:
        """Create the quick-add toolbar."""
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 10px;
                padding: 8px;
            }}
        """)
        
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)
        
        label = QLabel("Add Module:")
        label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; font-weight: bold;")
        layout.addWidget(label)
        
        for mod_type, info in MODULE_TYPES.items():
            btn = ModuleTypeButton(mod_type, info)
            btn.clicked.connect(lambda checked, mt=mod_type: self.add_module(mt))
            layout.addWidget(btn)
        
        layout.addStretch()
        
        return toolbar
    
    def create_modules_panel(self) -> QWidget:
        """Create the scrollable modules panel."""
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']}40;
                border-radius: 12px;
            }}
        """)
        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        
        # Header
        header = QHBoxLayout()
        header_label = QLabel("Configured Modules")
        header_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: bold;
            padding: 8px;
        """)
        header.addWidget(header_label)
        
        self.module_count_label = QLabel("0 modules")
        self.module_count_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; padding: 8px;")
        header.addWidget(self.module_count_label)
        header.addStretch()
        
        panel_layout.addLayout(header)
        
        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background-color: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(8)
        self.cards_layout.addStretch()
        
        scroll.setWidget(self.cards_container)
        panel_layout.addWidget(scroll, stretch=1)
        
        # Empty state
        self.empty_state = QFrame()
        self.empty_state.setStyleSheet("background-color: transparent;")
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setAlignment(Qt.AlignCenter)
        
        empty_icon = QLabel("No Modules")
        empty_icon.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {COLORS['text_muted']};")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No SPI modules configured yet")
        empty_text.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
        empty_text.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_text)
        
        empty_hint = QLabel("Click a button above to add your first module")
        empty_hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        empty_hint.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_hint)
        
        panel_layout.addWidget(self.empty_state)
        
        return panel
    
    def create_sidebar(self) -> QFrame:
        """Create the sidebar with CE overview."""
        sidebar = QFrame()
        sidebar.setMinimumWidth(220)
        sidebar.setMaximumWidth(280)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 12px;
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Title
        title = QLabel("Chip Enables")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 14px;
            font-weight: bold;
        """)
        layout.addWidget(title)
        
        # CE indicators
        self.ce_indicators = {}
        for ce in CHIP_ENABLES:
            ce_frame = QFrame()
            ce_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS['bg_dark']};
                    border-radius: 8px;
                    padding: 8px;
                }}
            """)
            ce_layout = QVBoxLayout(ce_frame)
            ce_layout.setContentsMargins(12, 8, 12, 8)
            ce_layout.setSpacing(4)
            
            ce_header = QHBoxLayout()
            ce_label = QLabel(ce)
            ce_label.setStyleSheet(f"""
                color: {COLORS['text_primary']};
                font-weight: bold;
                font-size: 12px;
            """)
            ce_header.addWidget(ce_label)
            
            ce_status = QLabel("Empty")
            ce_status.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            ce_header.addWidget(ce_status, alignment=Qt.AlignRight)
            
            ce_layout.addLayout(ce_header)
            
            ce_modules = QLabel("")
            ce_modules.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
            ce_modules.setWordWrap(True)
            ce_layout.addWidget(ce_modules)
            
            self.ce_indicators[ce] = {"status": ce_status, "modules": ce_modules, "frame": ce_frame}
            layout.addWidget(ce_frame)
        
        layout.addStretch()
        
        # Help hint
        hint = QLabel("Tip: Each module is assigned to a Chip Enable (CE) line. "
                      "4KO relay modules can share a CE using different addresses.")
        hint.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        
        return sidebar
    
    def create_footer(self) -> QHBoxLayout:
        """Create footer with action buttons."""
        footer = QHBoxLayout()
        footer.setSpacing(12)
        
        help_btn = QPushButton("Help")
        help_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                font-size: 12px;
                border: 1px solid {COLORS['bg_hover']};
                border-radius: 6px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}
        """)
        help_btn.clicked.connect(self.show_help)
        footer.addWidget(help_btn)
        
        footer.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text_secondary']};
                font-size: 12px;
                border: 1px solid {COLORS['bg_hover']};
                border-radius: 6px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['text_primary']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        footer.addWidget(cancel_btn)
        
        save_btn = QPushButton("Save Configuration")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                font-size: 12px;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 10px 24px;
            }}
            QPushButton:hover {{
                background-color: #00b85c;
            }}
            QPushButton:pressed {{
                background-color: #009e4f;
            }}
        """)
        save_btn.clicked.connect(self.save_config)
        footer.addWidget(save_btn)
        
        return footer
    
    def add_module(self, module_type: str):
        """Add a new module of specified type."""
        info = MODULE_TYPES.get(module_type, MODULE_TYPES["PI-SPI-DIN-4KO"])
        
        # Generate default name
        existing_names = [m.get("name", "") for m in self.spi_modules]
        base_name = info["short"].lower()
        name = base_name
        counter = 1
        while name in existing_names:
            name = f"{base_name}_{counter}"
            counter += 1
        
        # Find next available CE
        ce = self.get_next_available_ce(module_type)
        
        # Create config
        config = {
            "name": name,
            "module_type": module_type,
            "chip_enable": ce,
            "address": 0,
            "channels": [
                {"channel": i, "name": f"{info['channel_prefix']}{i}", "enabled": True, "description": ""}
                for i in range(info["channels"])
            ],
        }
        
        self.spi_modules.append(config)
        self.refresh_ui()
        
        logger.info(f"Added module: {name} ({module_type}) on {ce}")
    
    def get_next_available_ce(self, module_type: str) -> str:
        """Get the next available chip enable for a module type."""
        used_ces = {}
        for m in self.spi_modules:
            ce = m.get("chip_enable", "CE0")
            if ce not in used_ces:
                used_ces[ce] = []
            used_ces[ce].append(m.get("module_type"))
        
        # 4KO modules can stack on same CE
        if module_type == "PI-SPI-DIN-4KO":
            for ce in CHIP_ENABLES:
                if ce not in used_ces:
                    return ce
                # Can share with other 4KO modules (up to 4)
                if all(t == "PI-SPI-DIN-4KO" for t in used_ces[ce]) and len(used_ces[ce]) < 4:
                    return ce
        else:
            for ce in CHIP_ENABLES:
                if ce not in used_ces:
                    return ce
        
        return "CE0"
    
    def remove_module(self, card: ModuleCard):
        """Remove a module."""
        idx = self.module_cards.index(card)
        if idx < len(self.spi_modules):
            name = self.spi_modules[idx].get("name", "Unknown")
            
            reply = QMessageBox.question(
                self,
                "Remove Module",
                f"Remove module '{name}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                del self.spi_modules[idx]
                self.refresh_ui()
                logger.info(f"Removed module: {name}")
    
    def refresh_ui(self):
        """Refresh the entire UI."""
        # Clear existing cards
        for card in self.module_cards:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
        self.module_cards.clear()
        
        # Clear layout
        while self.cards_layout.count() > 0:
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add cards
        for i, config in enumerate(self.spi_modules):
            card = ModuleCard(config, self)
            card.removed.connect(self.remove_module)
            card.changed.connect(self.on_module_changed)
            self.cards_layout.addWidget(card)
            self.module_cards.append(card)
        
        self.cards_layout.addStretch()
        
        # Update visibility
        self.empty_state.setVisible(len(self.spi_modules) == 0)
        
        # Update count
        self.module_count_label.setText(f"{len(self.spi_modules)} module{'s' if len(self.spi_modules) != 1 else ''}")
        
        # Update CE indicators
        self.update_ce_indicators()
    
    def on_module_changed(self):
        """Handle module configuration change."""
        # Update configs from cards
        self.spi_modules = [card.get_config() for card in self.module_cards]
        self.update_ce_indicators()
    
    def update_ce_indicators(self):
        """Update the CE status indicators."""
        ce_usage = {ce: [] for ce in CHIP_ENABLES}
        
        for m in self.spi_modules:
            ce = m.get("chip_enable", "CE0")
            if ce in ce_usage:
                info = MODULE_TYPES.get(m.get("module_type", ""), {})
                ce_usage[ce].append({
                    "name": m.get("name", "Unknown"),
                    "type": info.get("short", "?"),
                    "color": info.get("color", COLORS["text_muted"]),
                })
        
        for ce, modules in ce_usage.items():
            indicator = self.ce_indicators[ce]
            
            if modules:
                indicator["status"].setText(f"{len(modules)} module{'s' if len(modules) > 1 else ''}")
                indicator["status"].setStyleSheet(f"color: {COLORS['success']}; font-size: 10px;")
                
                module_texts = [f"<span style='color:{m['color']}'>{m['name']}</span>" for m in modules]
                indicator["modules"].setText(", ".join(module_texts))
                indicator["modules"].setVisible(True)
                
                indicator["frame"].setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_hover']};
                        border-radius: 8px;
                        border: 1px solid {modules[0]['color']}40;
                    }}
                """)
            else:
                indicator["status"].setText("Empty")
                indicator["status"].setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
                indicator["modules"].setText("")
                indicator["modules"].setVisible(False)
                indicator["frame"].setStyleSheet(f"""
                    QFrame {{
                        background-color: {COLORS['bg_dark']};
                        border-radius: 8px;
                    }}
                """)
    
    def load_config(self):
        """Load configuration from file."""
        try:
            if not self.config_file_path.exists():
                logger.warning(f"Config file not found: {self.config_file_path}")
                self.refresh_ui()
                return
            
            with open(self.config_file_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Load SPI modules
            self.spi_modules = config.get('hardware', {}).get('widgetlords', {}).get('spi_modules', [])
            
            # Deep copy to avoid modifying original
            self.spi_modules = [dict(m) for m in self.spi_modules]
            for m in self.spi_modules:
                m['channels'] = [dict(c) for c in m.get('channels', [])]
            
            self.refresh_ui()
            
            # Load Modbus config
            self.modbus_config = config.get('hardware', {}).get('modbus', {})
            self.load_modbus_ui()
            
            logger.info(f"Loaded {len(self.spi_modules)} SPI modules and Modbus config")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", f"Failed to load configuration:\n{e}")
    
    def load_modbus_ui(self):
        """Load Modbus configuration into UI elements."""
        self.modbus_enabled_check.setChecked(self.modbus_config.get('enabled', False))
        self.modbus_port_edit.setText(self.modbus_config.get('port', '/dev/ttyUSB0'))
        
        baudrate = str(self.modbus_config.get('baudrate', 9600))
        idx = self.modbus_baudrate_combo.findText(baudrate)
        if idx >= 0:
            self.modbus_baudrate_combo.setCurrentIndex(idx)
        
        parity = self.modbus_config.get('parity', 'None')
        idx = self.modbus_parity_combo.findText(parity)
        if idx >= 0:
            self.modbus_parity_combo.setCurrentIndex(idx)
        
        databits = str(self.modbus_config.get('databits', 8))
        idx = self.modbus_databits_combo.findText(databits)
        if idx >= 0:
            self.modbus_databits_combo.setCurrentIndex(idx)
        
        stopbits = str(int(self.modbus_config.get('stopbits', 1)))
        idx = self.modbus_stopbits_combo.findText(stopbits)
        if idx >= 0:
            self.modbus_stopbits_combo.setCurrentIndex(idx)
        
        self.modbus_slave_spin.setValue(self.modbus_config.get('slave_address', 1))
        self.modbus_timeout_spin.setValue(self.modbus_config.get('timeout', 1.0))
        self.modbus_debug_check.setChecked(self.modbus_config.get('debug', False))
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Get latest configs from cards
            self.spi_modules = [card.get_config() for card in self.module_cards]
            
            # Validate SPI modules
            for m in self.spi_modules:
                if not m.get("name"):
                    QMessageBox.warning(self, "Validation Error", "All modules must have a name.")
                    return
            
            # Load existing config
            if self.config_file_path.exists():
                with open(self.config_file_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                config = {}
            
            # Ensure structure
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'widgetlords' not in config['hardware']:
                config['hardware']['widgetlords'] = {}
            if 'modbus' not in config['hardware']:
                config['hardware']['modbus'] = {}
            
            # Save SPI modules config
            config['hardware']['widgetlords']['enabled'] = len(self.spi_modules) > 0
            config['hardware']['widgetlords']['spi_modules'] = self.spi_modules
            
            # Update legacy fields
            relay_module = next((m for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-4KO"), None)
            analog_module = next((m for m in self.spi_modules if m.get("module_type") == "PI-SPI-DIN-8AI"), None)
            
            if relay_module:
                pump_ch = next((c.get("channel", 0) for c in relay_module.get("channels", [])
                               if "pump" in c.get("name", "").lower() or "pump" in c.get("description", "").lower()), 0)
                config['hardware']['widgetlords']['pump_relay'] = pump_ch
            
            if analog_module:
                pressure_ch = next((c.get("channel", 0) for c in analog_module.get("channels", [])
                                   if "pressure" in c.get("name", "").lower() or "pressure" in c.get("description", "").lower()), 0)
                config['hardware']['widgetlords']['pressure_channel'] = pressure_ch
            
            # Save Modbus config
            config['hardware']['modbus']['enabled'] = self.modbus_enabled_check.isChecked()
            config['hardware']['modbus']['port'] = self.modbus_port_edit.text().strip()
            config['hardware']['modbus']['baudrate'] = int(self.modbus_baudrate_combo.currentText())
            config['hardware']['modbus']['parity'] = self.modbus_parity_combo.currentText()
            config['hardware']['modbus']['databits'] = int(self.modbus_databits_combo.currentText())
            config['hardware']['modbus']['stopbits'] = int(self.modbus_stopbits_combo.currentText())
            config['hardware']['modbus']['slave_address'] = self.modbus_slave_spin.value()
            config['hardware']['modbus']['timeout'] = self.modbus_timeout_spin.value()
            config['hardware']['modbus']['debug'] = self.modbus_debug_check.isChecked()
            
            # Save to file
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.spi_modules)} SPI modules and Modbus config")
            
            self.config_saved.emit()
            
            modbus_status = "enabled" if self.modbus_enabled_check.isChecked() else "disabled"
            QMessageBox.information(
                self, "Saved",
                f"Configuration saved successfully!\n\n"
                f"• {len(self.spi_modules)} SPI module(s)\n"
                f"• Modbus: {modbus_status}\n\n"
                f"Restart the application to apply changes."
            )
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            QMessageBox.critical(self, "Save Error", f"Failed to save configuration:\n{e}")
    
    def show_help(self):
        """Show help dialog."""
        help_text = f"""
        <div style='color: {COLORS["text_primary"]}; font-family: sans-serif;'>
        <h2>SPI Module Configuration</h2>
        
        <h3>Module Types</h3>
        <p><b style='color:{COLORS["relay"]}'>4KO - Relay Outputs</b>: 4 SPDT relays (2A AC/DC). 
        Can stack up to 4 modules on one CE using addresses 0-3.</p>
        
        <p><b style='color:{COLORS["analog_in"]}'>8AI - Analog Inputs</b>: 8 channels, 
        0-10V or 4-20mA (jumper selectable), 16-bit resolution.</p>
        
        <p><b style='color:{COLORS["digital_in"]}'>8DI - Digital Inputs</b>: 8 channels, 
        12-24V compatible, optically isolated.</p>
        
        <p><b style='color:{COLORS["analog_out"]}'>4AO - Analog Outputs</b>: 4 channels, 
        0-10V output, 12-bit DAC.</p>
        
        <h3>Chip Enables</h3>
        <p>Each module connects to a Chip Enable (CE) line:</p>
        <ul>
        <li>CE0 - GPIO8 (SPI0 default)</li>
        <li>CE1 - GPIO7 (SPI0 default)</li>
        <li>CE2 - GPIO24</li>
        <li>CE3 - GPIO23</li>
        <li>CE4 - GPIO18</li>
        </ul>
        
        <h3>Channel Naming Tips</h3>
        <ul>
        <li>Use descriptive names: <i>vacuum_pump</i>, <i>pressure_sensor</i></li>
        <li>Include location or function in description</li>
        <li>Names are used in code to control I/O</li>
        </ul>
        </div>
        """
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help")
        msg.setTextFormat(Qt.RichText)
        msg.setText(help_text)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {COLORS['bg_card']};
            }}
            QLabel {{
                color: {COLORS['text_primary']};
            }}
            QPushButton {{
                background-color: {COLORS['accent_cyan']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
        """)
        msg.exec_()
