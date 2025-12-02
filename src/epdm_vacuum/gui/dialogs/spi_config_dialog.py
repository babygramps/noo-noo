"""
SPI Configuration Dialog - Widgetlords Module Assignment

Modern, streamlined dialog for configuring Widgetlords PI-SPI-DIN modules with:
- Visual module cards with inline channel editing
- Drag-style chip select assignment
- Beautiful, modern UI with smooth interactions
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
)
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QSize
from PyQt5.QtGui import QFont, QColor, QPalette, QPainter, QBrush, QPen

logger = logging.getLogger(__name__)


# Modern color palette
COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_card": "#16213e",
    "bg_hover": "#1f3460",
    "accent_blue": "#0f4c75",
    "accent_cyan": "#3282b8",
    "text_primary": "#eaeaea",
    "text_secondary": "#a0a0a0",
    "text_muted": "#6a6a8a",
    "success": "#00d26a",
    "warning": "#ffc107",
    "danger": "#ff6b6b",
    "relay": "#ff6b6b",
    "analog_in": "#4ecdc4",
    "digital_in": "#45b7d1",
    "analog_out": "#f7b731",
}

# Module type definitions with modern styling
MODULE_TYPES = {
    "PI-SPI-DIN-4KO": {
        "short": "4KO",
        "description": "4× Relay Outputs",
        "detail": "2A AC/DC SPDT relays",
        "io_type": "relay_output",
        "channels": 4,
        "max_per_ce": 4,
        "icon": "⚡",
        "color": COLORS["relay"],
        "channel_prefix": "K",
    },
    "PI-SPI-DIN-8AI": {
        "short": "8AI",
        "description": "8× Analog Inputs",
        "detail": "0-10V / 4-20mA",
        "io_type": "analog_input",
        "channels": 8,
        "max_per_ce": 1,
        "icon": "📊",
        "color": COLORS["analog_in"],
        "channel_prefix": "AI",
    },
    "PI-SPI-DIN-8DI": {
        "short": "8DI",
        "description": "8× Digital Inputs",
        "detail": "12-24V isolated",
        "io_type": "digital_input",
        "channels": 8,
        "max_per_ce": 1,
        "icon": "◉",
        "color": COLORS["digital_in"],
        "channel_prefix": "DI",
    },
    "PI-SPI-DIN-4AO": {
        "short": "4AO",
        "description": "4× Analog Outputs",
        "detail": "0-10V output",
        "io_type": "analog_output",
        "channels": 4,
        "max_per_ce": 1,
        "icon": "📈",
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
    Modern SPI module configuration dialog.
    
    Features:
    - Visual module cards with inline channel editing
    - Quick-add buttons for each module type
    - Chip enable assignment overview
    - Dark theme with modern styling
    """
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file_path = Path(__file__).parent.parent.parent / "config" / "hardware_config.yaml"
        self.spi_modules: List[Dict[str, Any]] = []
        self.module_cards: List[ModuleCard] = []
        
        self.init_ui()
        self.load_config()
        
        logger.info("SPIConfigDialog initialized")
    
    def init_ui(self):
        self.setWindowTitle("SPI Module Configuration")
        self.setMinimumSize(900, 700)
        self.resize(1000, 750)
        
        # Dark theme
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
                background-color: {COLORS['bg_hover']};
                border-radius: 5px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent_cyan']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 20, 24, 20)
        main_layout.setSpacing(16)
        
        # Header
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        title = QLabel("SPI Module Configuration")
        title.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            font-size: 22px;
            font-weight: bold;
        """)
        header_layout.addWidget(title)
        
        subtitle = QLabel("Configure Widgetlords PI-SPI-DIN modules and assign I/O channels")
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(subtitle)
        
        main_layout.addLayout(header_layout)
        
        # Quick-add toolbar
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Main content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)
        
        # Modules list (main area)
        modules_panel = self.create_modules_panel()
        content_layout.addWidget(modules_panel, stretch=3)
        
        # Sidebar with CE overview
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar, stretch=1)
        
        main_layout.addLayout(content_layout, stretch=1)
        
        # Footer buttons
        footer = self.create_footer()
        main_layout.addLayout(footer)
    
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
        
        empty_icon = QLabel("📦")
        empty_icon.setStyleSheet("font-size: 48px;")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_layout.addWidget(empty_icon)
        
        empty_text = QLabel("No modules configured")
        empty_text.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 14px;")
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
        hint = QLabel("💡 Each module is assigned to a Chip Enable (CE) line. "
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
            
            self.spi_modules = config.get('hardware', {}).get('widgetlords', {}).get('spi_modules', [])
            
            # Deep copy to avoid modifying original
            self.spi_modules = [dict(m) for m in self.spi_modules]
            for m in self.spi_modules:
                m['channels'] = [dict(c) for c in m.get('channels', [])]
            
            self.refresh_ui()
            logger.info(f"Loaded {len(self.spi_modules)} SPI modules")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            QMessageBox.warning(self, "Load Error", f"Failed to load configuration:\n{e}")
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Get latest configs from cards
            self.spi_modules = [card.get_config() for card in self.module_cards]
            
            # Validate
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
            
            # Update config
            if 'hardware' not in config:
                config['hardware'] = {}
            if 'widgetlords' not in config['hardware']:
                config['hardware']['widgetlords'] = {}
            
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
            
            # Save
            with open(self.config_file_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved {len(self.spi_modules)} SPI modules")
            
            self.config_saved.emit()
            
            QMessageBox.information(
                self, "Saved",
                f"Configuration saved successfully!\n\n"
                f"• {len(self.spi_modules)} module(s) configured\n"
                f"• Restart the application to apply changes"
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
