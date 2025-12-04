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
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize, QTimer
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen
from PyQt5.QtWidgets import QApplication

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
        # Taller height for analog inputs to fit span configuration
        height = 72 if self.io_type == "analog_input" else 44
        self.setFixedHeight(height)
        self.setStyleSheet(f"""
            ChannelWidget {{
                background-color: {COLORS['bg_dark']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin: 2px 0;
            }}
            ChannelWidget:hover {{
                border-color: {self.color};
            }}
            QLineEdit {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                color: {COLORS['text_primary']};
                font-size: 11px;
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                border-color: {self.color};
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
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                color: {COLORS['text_primary']};
                font-size: 10px;
                padding: 1px 2px;
            }}
            QDoubleSpinBox:focus, QSpinBox:focus {{
                border-color: {self.color};
            }}
            QComboBox {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                color: {COLORS['text_primary']};
                font-size: 10px;
                padding: 2px 4px;
            }}
            QComboBox:focus {{
                border-color: {self.color};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 16px;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 4, 8, 4)
        main_layout.setSpacing(4)
        
        # Top row: channel indicator, enabled, name, description
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        
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
        top_row.addWidget(ch_label)
        
        # Enabled checkbox
        self.enabled_check = QCheckBox()
        self.enabled_check.setChecked(self.config.get("enabled", True))
        self.enabled_check.setToolTip("Enable/disable this channel")
        self.enabled_check.stateChanged.connect(self._on_change)
        top_row.addWidget(self.enabled_check)
        
        # Name input
        self.name_edit = QLineEdit(self.config.get("name", f"Channel {self.channel_num}"))
        self.name_edit.setPlaceholderText("Channel name...")
        self.name_edit.setMinimumWidth(100)
        self.name_edit.textChanged.connect(self._on_change)
        top_row.addWidget(self.name_edit, stretch=2)
        
        # Description (for non-analog types, or as tooltip for analog)
        if self.io_type != "analog_input":
            self.desc_edit = QLineEdit(self.config.get("description", ""))
            self.desc_edit.setPlaceholderText("Description...")
            self.desc_edit.setStyleSheet(f"color: {COLORS['text_secondary']}; font-style: italic;")
            self.desc_edit.textChanged.connect(self._on_change)
            top_row.addWidget(self.desc_edit, stretch=2)
        
        # Digital input: Invert option
        if self.io_type == "digital_input":
            self.invert_check = QCheckBox("Invert")
            self.invert_check.setChecked(self.config.get("inverted", False))
            self.invert_check.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            self.invert_check.stateChanged.connect(self._on_change)
            top_row.addWidget(self.invert_check)
        
        # Relay output: Normally Open option
        if self.io_type == "relay":
            self.normally_open_check = QCheckBox("NO")
            self.normally_open_check.setChecked(self.config.get("normally_open", False))
            self.normally_open_check.setToolTip(
                "Normally Open (NO) valve:\n"
                "  • Valve is OPEN when relay is OFF\n"
                "  • Valve is CLOSED when relay is ON\n\n"
                "Normally Closed (NC) valve:\n"
                "  • Valve is CLOSED when relay is OFF\n"
                "  • Valve is OPEN when relay is ON\n\n"
                "The software automatically inverts relay commands for NO valves."
            )
            self.normally_open_check.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            self.normally_open_check.stateChanged.connect(self._on_change)
            top_row.addWidget(self.normally_open_check)
        
        main_layout.addLayout(top_row)
        
        # Analog input: Second row with span configuration
        if self.io_type == "analog_input":
            span_row = QHBoxLayout()
            span_row.setSpacing(6)
            
            # Input type selector
            type_label = QLabel("Input:")
            type_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            span_row.addWidget(type_label)
            
            self.input_type_combo = QComboBox()
            self.input_type_combo.addItems(["4-20mA", "0-10V", "0-5V"])
            self.input_type_combo.setCurrentText(self.config.get("input_type", "4-20mA"))
            self.input_type_combo.setFixedWidth(70)
            self.input_type_combo.currentTextChanged.connect(self._on_change)
            span_row.addWidget(self.input_type_combo)
            
            span_row.addSpacing(8)
            
            # Low span: input value = output value
            low_label = QLabel("Low:")
            low_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            span_row.addWidget(low_label)
            
            self.low_input_spin = QDoubleSpinBox()
            self.low_input_spin.setRange(0, 100)
            self.low_input_spin.setDecimals(1)
            self.low_input_spin.setValue(self.config.get("low_input", 4.0))
            self.low_input_spin.setFixedWidth(50)
            self.low_input_spin.valueChanged.connect(self._on_change)
            span_row.addWidget(self.low_input_spin)
            
            eq1 = QLabel("=")
            eq1.setStyleSheet(f"color: {COLORS['text_muted']};")
            span_row.addWidget(eq1)
            
            self.low_output_spin = QDoubleSpinBox()
            self.low_output_spin.setRange(-10000, 10000)
            self.low_output_spin.setDecimals(2)
            self.low_output_spin.setValue(self.config.get("low_output", 0.0))
            self.low_output_spin.setFixedWidth(60)
            self.low_output_spin.valueChanged.connect(self._on_change)
            span_row.addWidget(self.low_output_spin)
            
            span_row.addSpacing(8)
            
            # High span: input value = output value
            high_label = QLabel("High:")
            high_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            span_row.addWidget(high_label)
            
            self.high_input_spin = QDoubleSpinBox()
            self.high_input_spin.setRange(0, 100)
            self.high_input_spin.setDecimals(1)
            self.high_input_spin.setValue(self.config.get("high_input", 20.0))
            self.high_input_spin.setFixedWidth(50)
            self.high_input_spin.valueChanged.connect(self._on_change)
            span_row.addWidget(self.high_input_spin)
            
            eq2 = QLabel("=")
            eq2.setStyleSheet(f"color: {COLORS['text_muted']};")
            span_row.addWidget(eq2)
            
            self.high_output_spin = QDoubleSpinBox()
            self.high_output_spin.setRange(-10000, 10000)
            self.high_output_spin.setDecimals(2)
            self.high_output_spin.setValue(self.config.get("high_output", 100.0))
            self.high_output_spin.setFixedWidth(60)
            self.high_output_spin.valueChanged.connect(self._on_change)
            span_row.addWidget(self.high_output_spin)
            
            span_row.addSpacing(8)
            
            # Units
            units_label = QLabel("Units:")
            units_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            span_row.addWidget(units_label)
            
            self.units_edit = QLineEdit(self.config.get("units", ""))
            self.units_edit.setPlaceholderText("PSI")
            self.units_edit.setFixedWidth(50)
            self.units_edit.textChanged.connect(self._on_change)
            span_row.addWidget(self.units_edit)
            
            span_row.addStretch()
            main_layout.addLayout(span_row)
    
    def _on_change(self):
        self.config["enabled"] = self.enabled_check.isChecked()
        self.config["name"] = self.name_edit.text()
        
        if self.io_type == "analog_input":
            self.config["input_type"] = self.input_type_combo.currentText()
            self.config["low_input"] = self.low_input_spin.value()
            self.config["low_output"] = self.low_output_spin.value()
            self.config["high_input"] = self.high_input_spin.value()
            self.config["high_output"] = self.high_output_spin.value()
            self.config["units"] = self.units_edit.text()
        elif self.io_type == "digital_input":
            self.config["description"] = self.desc_edit.text()
            self.config["inverted"] = self.invert_check.isChecked()
        elif self.io_type == "relay":
            if hasattr(self, 'desc_edit'):
                self.config["description"] = self.desc_edit.text()
            if hasattr(self, 'normally_open_check'):
                self.config["normally_open"] = self.normally_open_check.isChecked()
        else:
            if hasattr(self, 'desc_edit'):
                self.config["description"] = self.desc_edit.text()
        
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
    
    def __init__(self, parent=None, shared_interface=None):
        """
        Initialize the SPI configuration dialog.
        
        Args:
            parent: Parent widget
            shared_interface: Optional shared WidgetLordsInterface from main app.
                             If provided, this interface will be used for testing
                             instead of creating a new one.
        """
        super().__init__(parent)
        self.config_file_path = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        self.spi_modules: List[Dict[str, Any]] = []
        self.module_cards: List[ModuleCard] = []
        self.modbus_config: Dict[str, Any] = {}
        
        # For manual I/O testing - use shared interface if provided
        self.test_interface = shared_interface
        self._owns_interface = shared_interface is None  # Track if we created it
        
        self.init_ui()
        self.load_config()
        
        # If shared interface provided and connected, show as connected
        if shared_interface and shared_interface.is_connected():
            self._update_connection_status(connected=True, shared=True)
        
        logger.info("Hardware Configuration dialog initialized" + 
                   (" with shared interface" if shared_interface else ""))
    
    def _update_connection_status(self, connected: bool, shared: bool = False):
        """Update the connection status display."""
        if hasattr(self, 'connection_status_label'):
            if connected:
                status = "Connected (Shared)" if shared else "Connected"
                self.connection_status_label.setText(status)
                self.connection_status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
                if hasattr(self, 'connect_btn'):
                    self.connect_btn.setText("Reconnect" if not shared else "Using Shared")
                    self.connect_btn.setEnabled(not shared)
            else:
                self.connection_status_label.setText("Not Connected")
                self.connection_status_label.setStyleSheet(f"color: {COLORS['text_muted']};")
    
    def closeEvent(self, event):
        """Clean up when dialog closes."""
        # Only disconnect if we created the interface ourselves
        if self.test_interface and self._owns_interface:
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
        
        # Calibration tab
        calibration_tab = self.create_calibration_tab()
        self.tab_widget.addTab(calibration_tab, "⚖ Calibration")
        
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
        # If we already have a shared interface, just populate controls
        if self.test_interface and self.test_interface.is_connected():
            logger.info("Using existing shared interface for testing")
            self.populate_test_controls()
            self._sync_button_states_from_manager()
            return
        
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
            self._owns_interface = True  # We created it, we own it
            
            if self.test_interface.connect():
                self.connection_status_label.setText("Connected")
                self.connection_status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
                logger.info("Connected to hardware for testing")
                
                # Populate test controls
                self.populate_test_controls()
                self._sync_button_states_from_manager()
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
            self._sync_button_states_from_manager()
            logger.warning("Widgetlords library not available - using mock mode")
            
        except Exception as e:
            logger.error(f"Failed to connect for testing: {e}")
            QMessageBox.critical(self, "Error", f"Failed to connect:\n{e}")
    
    def _sync_button_states_from_manager(self):
        """Sync toggle button states from the global relay state manager."""
        try:
            from ...daq.relay_state_manager import relay_state_manager
            
            all_states = relay_state_manager.get_all_states()
            
            for key, btn in self.relay_toggle_buttons.items():
                parts = key.split(":")
                if len(parts) == 2:
                    module_name, channel_name = parts
                    state = all_states.get(module_name, {}).get(channel_name, False)
                    btn.blockSignals(True)
                    btn.setChecked(state)
                    btn.setText("ON" if state else "OFF")
                    btn.blockSignals(False)
            
            logger.debug(f"Synced {len(self.relay_toggle_buttons)} relay buttons from state manager")
        except Exception as e:
            logger.warning(f"Could not sync button states: {e}")
    
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
                        ch_units = ch.get("units", "V")
                        ch_input_type = ch.get("input_type", "4-20mA")
                        
                        reading_widget = self.create_analog_reading_widget(
                            mod_name, ch_name, ch_desc, ch_units, ch_input_type
                        )
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
    
    def create_analog_reading_widget(self, module_name: str, channel_name: str, description: str, 
                                      units: str = "", input_type: str = "4-20mA") -> QFrame:
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
        
        # Description with input type
        desc_text = description if description else ""
        if input_type:
            desc_text = f"{desc_text} ({input_type})" if desc_text else input_type
        if desc_text:
            desc_label = QLabel(desc_text)
            desc_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 10px;")
            layout.addWidget(desc_label)
        
        # Reading value with units
        unit_text = units if units else "V"
        reading_label = QLabel(f"-- {unit_text}")
        reading_label.setStyleSheet(f"""
            color: {COLORS['analog_in']};
            font-size: 20px;
            font-weight: bold;
            padding: 8px;
        """)
        reading_label.setAlignment(Qt.AlignCenter)
        reading_label.setProperty("units", unit_text)
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
                
                # Update analog readings (already scaled by interface)
                analog_data = data.get("analog_inputs", {})
                for mod_name, readings in analog_data.items():
                    for ch_name, value in readings.items():
                        key = f"{mod_name}:{ch_name}"
                        if key in self.analog_reading_labels:
                            label = self.analog_reading_labels[key]
                            units = label.property("units") or "V"
                            label.setText(f"{value:.2f} {units}")
                
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
            # Mock mode - show placeholder values with units
            for key, label in self.analog_reading_labels.items():
                units = label.property("units") or "V"
                label.setText(f"0.00 {units}")
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
    
    def create_calibration_tab(self) -> QWidget:
        """Create the Calibration tab for TLB4 load cell real calibration."""
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(0, 12, 0, 0)
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
        # SOFTWARE CALIBRATION WIZARD
        # This calibrates in your app, not on the TLB4 hardware
        # =====================================================================
        sw_cal_frame = QFrame()
        sw_cal_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #e8eaf6;
                border: 2px solid #5c6bc0;
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        sw_cal_layout = QVBoxLayout(sw_cal_frame)
        
        # Title
        sw_title = QLabel("🔧 Software Calibration Wizard")
        sw_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3949ab;")
        sw_cal_layout.addWidget(sw_title)
        
        sw_desc = QLabel(
            "Calibrate individual load cell channels in software. This converts raw Modbus values to kg.\n"
            "Formula: Weight (kg) = (Raw Value - Zero Offset) / Calibration Factor"
        )
        sw_desc.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']}; margin-bottom: 10px;")
        sw_desc.setWordWrap(True)
        sw_cal_layout.addWidget(sw_desc)
        
        # Channel selector
        channel_row = QHBoxLayout()
        channel_label = QLabel("Select Channel:")
        channel_label.setStyleSheet("font-weight: bold; color: #3949ab;")
        channel_row.addWidget(channel_label)
        
        self.sw_channel_combo = QComboBox()
        self.sw_channel_combo.addItems(["Channel 1", "Channel 2", "Channel 3", "Channel 4"])
        self.sw_channel_combo.setStyleSheet(f"""
            QComboBox {{
                padding: 8px 12px;
                border: 2px solid #5c6bc0;
                border-radius: 6px;
                background-color: {COLORS['bg_card']};
                font-size: 12px;
                min-width: 120px;
            }}
        """)
        self.sw_channel_combo.currentIndexChanged.connect(self.update_sw_cal_display)
        channel_row.addWidget(self.sw_channel_combo)
        channel_row.addStretch()
        
        # Current raw value display
        self.sw_raw_label = QLabel("Current Raw: ---")
        self.sw_raw_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #3949ab;
            font-family: 'Consolas', 'Monaco', monospace;
            background-color: white;
            padding: 8px 15px;
            border-radius: 6px;
            border: 1px solid #c5cae9;
        """)
        channel_row.addWidget(self.sw_raw_label)
        
        sw_cal_layout.addLayout(channel_row)
        
        # Calibration status
        status_row = QHBoxLayout()
        self.sw_cal_status = QLabel("Status: Not calibrated")
        self.sw_cal_status.setStyleSheet("font-size: 11px; color: #e65100;")
        status_row.addWidget(self.sw_cal_status)
        status_row.addStretch()
        
        self.sw_zero_label = QLabel("Zero: ---")
        self.sw_zero_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']};")
        status_row.addWidget(self.sw_zero_label)
        
        self.sw_factor_label = QLabel("Factor: ---")
        self.sw_factor_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']}; margin-left: 15px;")
        status_row.addWidget(self.sw_factor_label)
        
        sw_cal_layout.addLayout(status_row)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("background-color: #9fa8da; margin: 10px 0;")
        divider.setFixedHeight(1)
        sw_cal_layout.addWidget(divider)
        
        # Step 1: Zero
        step1_layout = QHBoxLayout()
        step1_label = QLabel("Step 1: Remove all weight from scale, then click →")
        step1_label.setStyleSheet("font-size: 11px;")
        step1_layout.addWidget(step1_label)
        
        self.sw_zero_btn = QPushButton("Capture Zero")
        self.sw_zero_btn.setStyleSheet("""
            QPushButton {
                background-color: #5c6bc0;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #3f51b5; }
            QPushButton:disabled { background-color: #c5cae9; }
        """)
        self.sw_zero_btn.clicked.connect(self.perform_sw_zero_calibration)
        step1_layout.addWidget(self.sw_zero_btn)
        sw_cal_layout.addLayout(step1_layout)
        
        # Step 2: Span
        step2_layout = QHBoxLayout()
        step2_label = QLabel("Step 2: Place known weight on scale:")
        step2_label.setStyleSheet("font-size: 11px;")
        step2_layout.addWidget(step2_label)
        
        self.sw_weight_spin = QDoubleSpinBox()
        self.sw_weight_spin.setRange(0.001, 10000.0)
        self.sw_weight_spin.setDecimals(3)
        self.sw_weight_spin.setValue(5.0)
        self.sw_weight_spin.setSuffix(" kg")
        self.sw_weight_spin.setStyleSheet("""
            QDoubleSpinBox {
                font-size: 12px;
                padding: 6px 10px;
                border: 2px solid #5c6bc0;
                border-radius: 6px;
                background-color: white;
                min-width: 100px;
            }
        """)
        step2_layout.addWidget(self.sw_weight_spin)
        
        self.sw_span_btn = QPushButton("Capture Span")
        self.sw_span_btn.setStyleSheet("""
            QPushButton {
                background-color: #43a047;
                color: white;
                font-size: 12px;
                font-weight: bold;
                padding: 8px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #2e7d32; }
            QPushButton:disabled { background-color: #a5d6a7; }
        """)
        self.sw_span_btn.clicked.connect(self.perform_sw_span_calibration)
        step2_layout.addWidget(self.sw_span_btn)
        sw_cal_layout.addLayout(step2_layout)
        
        # Result and clear
        result_row = QHBoxLayout()
        self.sw_result_label = QLabel("")
        self.sw_result_label.setStyleSheet("font-size: 11px;")
        self.sw_result_label.setWordWrap(True)
        result_row.addWidget(self.sw_result_label, stretch=1)
        
        self.sw_clear_btn = QPushButton("Clear Calibration")
        self.sw_clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #ef5350;
                color: white;
                font-size: 11px;
                padding: 6px 12px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #c62828; }
        """)
        self.sw_clear_btn.clicked.connect(self.clear_sw_calibration)
        result_row.addWidget(self.sw_clear_btn)
        sw_cal_layout.addLayout(result_row)
        
        layout.addWidget(sw_cal_frame)
        
        # =====================================================================
        # Error Code Reference (Hardware Calibration)
        # =====================================================================
        error_group = QGroupBox("Hardware Calibration Error Codes")
        error_group.setStyleSheet(f"""
            QGroupBox {{
                font-size: 11px;
                font-weight: bold;
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: {COLORS['bg_card']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
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
        
        # =====================================================================
        # Reset / Undo Calibration Section
        # =====================================================================
        reset_frame = QFrame()
        reset_frame.setStyleSheet(f"""
            QFrame {{
                background-color: #e8f5e9;
                border: 2px solid #66bb6a;
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        reset_layout = QVBoxLayout(reset_frame)
        
        reset_title = QLabel("🔄 Reset / Undo Calibration")
        reset_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #2e7d32;")
        reset_layout.addWidget(reset_title)
        
        reset_text = QLabel(
            "The TLB4 doesn't have an 'undo' command. To reset calibration:\n\n"
            "<b>Option 1: Re-Calibrate</b>\n"
            "• Simply perform Zero Calibration again (with empty scale)\n"
            "• Then perform Span Calibration with a known accurate weight\n"
            "• Each new calibration overwrites the previous one\n\n"
            "<b>Option 2: Theoretical Calibration (Factory Reset)</b>\n"
            "• Use the TLB4 front panel buttons to access CALIB → FS-TEO\n"
            "• Enter your load cell specifications (capacity, sensitivity in mV/V)\n"
            "• This resets to calculated values based on load cell specs\n\n"
            "<b>Option 3: Software Tare</b>\n"
            "• For quick zeroing without changing calibration, use the Tare button\n"
            "• Tare only affects the displayed value, not the actual calibration"
        )
        reset_text.setStyleSheet("font-size: 11px; color: #1b5e20; line-height: 1.4;")
        reset_text.setWordWrap(True)
        reset_layout.addWidget(reset_text)
        
        layout.addWidget(reset_frame)
        
        layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Setup calibration update timer
        self.cal_update_timer = QTimer()
        self.cal_update_timer.timeout.connect(self.update_calibration_display)
        self.cal_update_timer.start(500)  # Update every 500ms
        
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
                background-color: {COLORS['bg_card']};
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
        desc_label.setStyleSheet(f"font-size: 11px; color: {COLORS['text_secondary']}; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet(f"background-color: {color}; opacity: 0.3;")
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # Instructions
        instructions_label = QLabel("Instructions:")
        instructions_label.setStyleSheet(f"font-size: 11px; font-weight: bold; color: {COLORS['text_primary']}; margin-top: 5px;")
        layout.addWidget(instructions_label)
        
        for i, instruction in enumerate(instructions, 1):
            instr_label = QLabel(f"  {i}. {instruction}")
            instr_label.setStyleSheet(f"font-size: 10px; color: {COLORS['text_secondary']}; margin-left: 10px;")
            layout.addWidget(instr_label)
        
        layout.addSpacing(10)
        
        return card
    
    def update_calibration_display(self) -> None:
        """Update the live weight display in calibration tab.
        
        Uses cached data from the DAQ thread to avoid serial port conflicts.
        The modbus interface's get_calibration_status() returns the last
        reading from the DAQ thread, which updates at ~10Hz.
        """
        try:
            # Get parent main window to access modbus interface
            main_window = self.parent()
            if main_window and hasattr(main_window, 'modbus_interface') and main_window.modbus_interface:
                interface = main_window.modbus_interface
                
                # Get cached status - this doesn't make additional serial reads
                status = interface.get_calibration_status()
                
                if status.get('connected', False):
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
        
        # Also update software calibration display if it exists
        if hasattr(self, 'sw_channel_combo'):
            try:
                self.update_sw_cal_display()
            except Exception:
                pass  # Ignore errors in SW cal display update
    
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
    
    # =========================================================================
    # Software Calibration Methods
    # =========================================================================
    
    def update_sw_cal_display(self) -> None:
        """Update the software calibration display for the selected channel."""
        try:
            channel = self.sw_channel_combo.currentIndex() + 1
            
            main_window = self.parent()
            if main_window and hasattr(main_window, 'modbus_interface') and main_window.modbus_interface:
                interface = main_window.modbus_interface
                
                # Get current raw value
                success, raw_value, _ = interface.get_channel_raw_value(channel)
                if success:
                    self.sw_raw_label.setText(f"Current Raw: {raw_value}")
                else:
                    self.sw_raw_label.setText("Current Raw: ---")
                
                # Get calibration settings
                cal = interface.get_software_calibration(channel)
                if cal.get('is_calibrated'):
                    self.sw_cal_status.setText("Status: ✓ Calibrated")
                    self.sw_cal_status.setStyleSheet("font-size: 11px; color: #2e7d32; font-weight: bold;")
                    self.sw_zero_label.setText(f"Zero: {cal['zero_offset']:.0f}")
                    self.sw_factor_label.setText(f"Factor: {cal['calibration_factor']:.2f} pts/kg")
                else:
                    self.sw_cal_status.setText("Status: Not calibrated")
                    self.sw_cal_status.setStyleSheet("font-size: 11px; color: #e65100;")
                    self.sw_zero_label.setText(f"Zero: {cal['zero_offset']:.0f}")
                    self.sw_factor_label.setText("Factor: ---")
                    
                self.sw_zero_btn.setEnabled(True)
                self.sw_span_btn.setEnabled(True)
            else:
                self.sw_raw_label.setText("Current Raw: (not connected)")
                self.sw_cal_status.setText("Status: Disconnected")
                self.sw_cal_status.setStyleSheet("font-size: 11px; color: #c62828;")
                self.sw_zero_btn.setEnabled(False)
                self.sw_span_btn.setEnabled(False)
                
        except Exception as e:
            logger.warning(f"Error updating SW cal display: {e}")
    
    def perform_sw_zero_calibration(self) -> None:
        """Perform software zero calibration for the selected channel."""
        try:
            channel = self.sw_channel_combo.currentIndex() + 1
            
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'modbus_interface') or not main_window.modbus_interface:
                QMessageBox.warning(self, "Error", "Modbus interface not available.")
                return
            
            interface = main_window.modbus_interface
            
            # Confirm
            reply = QMessageBox.question(
                self,
                "Software Zero Calibration",
                f"Channel {channel} - ZERO CALIBRATION\n\n"
                f"Please confirm:\n"
                f"• The scale for channel {channel} is EMPTY\n"
                f"• The reading is stable\n\n"
                f"This will save the current raw value as the zero offset.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Perform calibration
            success, message = interface.software_calibrate_zero(channel)
            
            if success:
                self.sw_result_label.setText(f"✓ Channel {channel}: {message}")
                self.sw_result_label.setStyleSheet("font-size: 11px; color: #2e7d32; font-weight: bold;")
                QMessageBox.information(self, "Zero Captured", f"✓ Channel {channel}\n\n{message}")
            else:
                self.sw_result_label.setText(f"✗ {message}")
                self.sw_result_label.setStyleSheet("font-size: 11px; color: #c62828; font-weight: bold;")
                QMessageBox.warning(self, "Error", message)
            
            self.update_sw_cal_display()
            
        except Exception as e:
            logger.error(f"SW zero calibration error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Calibration failed:\n{e}")
    
    def perform_sw_span_calibration(self) -> None:
        """Perform software span calibration for the selected channel."""
        try:
            channel = self.sw_channel_combo.currentIndex() + 1
            known_weight = self.sw_weight_spin.value()
            
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'modbus_interface') or not main_window.modbus_interface:
                QMessageBox.warning(self, "Error", "Modbus interface not available.")
                return
            
            interface = main_window.modbus_interface
            
            # Check if zero was done first
            cal = interface.get_software_calibration(channel)
            if cal.get('zero_offset', 0) == 0:
                reply = QMessageBox.warning(
                    self,
                    "Zero Not Set",
                    f"Channel {channel} has no zero offset set.\n\n"
                    f"It's recommended to capture zero first (with empty scale).\n\n"
                    f"Continue anyway with zero offset = 0?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return
            
            # Confirm
            reply = QMessageBox.question(
                self,
                "Software Span Calibration",
                f"Channel {channel} - SPAN CALIBRATION\n\n"
                f"Known weight: {known_weight:.3f} kg\n\n"
                f"Please confirm:\n"
                f"• {known_weight:.3f} kg is on the scale for channel {channel}\n"
                f"• The reading is stable\n\n"
                f"This will calculate the calibration factor.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            # Perform calibration
            success, message = interface.software_calibrate_span(channel, known_weight)
            
            if success:
                self.sw_result_label.setText(f"✓ Channel {channel}: {message}")
                self.sw_result_label.setStyleSheet("font-size: 11px; color: #2e7d32; font-weight: bold;")
                QMessageBox.information(self, "Span Captured", f"✓ Channel {channel}\n\n{message}\n\nCalibration complete!")
            else:
                self.sw_result_label.setText(f"✗ {message}")
                self.sw_result_label.setStyleSheet("font-size: 11px; color: #c62828; font-weight: bold;")
                QMessageBox.warning(self, "Error", message)
            
            self.update_sw_cal_display()
            
        except Exception as e:
            logger.error(f"SW span calibration error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Calibration failed:\n{e}")
    
    def clear_sw_calibration(self) -> None:
        """Clear software calibration for the selected channel."""
        try:
            channel = self.sw_channel_combo.currentIndex() + 1
            
            main_window = self.parent()
            if not main_window or not hasattr(main_window, 'modbus_interface') or not main_window.modbus_interface:
                QMessageBox.warning(self, "Error", "Modbus interface not available.")
                return
            
            interface = main_window.modbus_interface
            
            reply = QMessageBox.question(
                self,
                "Clear Calibration",
                f"Clear software calibration for Channel {channel}?\n\n"
                f"This will reset zero offset and calibration factor to defaults.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            success, message = interface.clear_software_calibration(channel)
            
            if success:
                self.sw_result_label.setText(f"Channel {channel}: Calibration cleared")
                self.sw_result_label.setStyleSheet("font-size: 11px; color: #666;")
            else:
                QMessageBox.warning(self, "Error", message)
            
            self.update_sw_cal_display()
            
        except Exception as e:
            logger.error(f"Clear calibration error: {e}", exc_info=True)
            QMessageBox.critical(self, "Error", f"Failed to clear calibration:\n{e}")
    
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
            
            # Save software calibration values from the Modbus interface
            main_window = self.parent()
            if main_window and hasattr(main_window, 'modbus_interface') and main_window.modbus_interface:
                interface = main_window.modbus_interface
                
                # Ensure TLB4 config structure exists
                if 'tlb4' not in config['hardware']['modbus']:
                    config['hardware']['modbus']['tlb4'] = {}
                if 'channel_scaling' not in config['hardware']['modbus']['tlb4']:
                    config['hardware']['modbus']['tlb4']['channel_scaling'] = {}
                
                channel_scaling = config['hardware']['modbus']['tlb4']['channel_scaling']
                
                # Save each channel's software calibration
                for ch in range(1, 5):
                    cal = interface.get_software_calibration(ch)
                    ch_key = f"channel_{ch}"
                    
                    if ch_key not in channel_scaling:
                        channel_scaling[ch_key] = {}
                    
                    channel_scaling[ch_key]['zero_offset'] = cal.get('zero_offset', 0.0)
                    channel_scaling[ch_key]['calibration_factor'] = cal.get('calibration_factor', 1.0)
                    channel_scaling[ch_key]['is_calibrated'] = cal.get('is_calibrated', False)
                    channel_scaling[ch_key]['enabled'] = cal.get('enabled', True)
                
                logger.info("Saved software calibration values for all channels")
            
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
