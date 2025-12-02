"""
Display Widget - Real-time Sensor Display

Shows current sensor readings in large, easy-to-read formats:
- Vacuum pressure (bar and PSI)
- Total force (kg) - prominently displayed
- Individual load cell readings
"""

from typing import Dict, Any
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLCDNumber,
    QGroupBox,
    QGridLayout,
    QSizePolicy,
    QFrame,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor, QFont

logger = logging.getLogger(__name__)


class DisplayWidget(QWidget):
    """
    Widget for displaying real-time sensor values.
    
    Displays:
    - Vacuum pressure (bar and PSI)
    - Total force (kg) - LARGE prominent display
    - Individual load cell readings
    """
    
    def __init__(self):
        """Initialize the display widget."""
        super().__init__()
        
        self.init_ui()
        logger.info("DisplayWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface with large, readable displays."""
        layout = QHBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Vacuum display group
        vacuum_group = self.create_vacuum_display()
        layout.addWidget(vacuum_group, stretch=1)
        
        # Force display group - PROMINENT
        force_group = self.create_force_display()
        layout.addWidget(force_group, stretch=2)
        
        # Load cells display group
        load_cells_group = self.create_load_cells_display()
        layout.addWidget(load_cells_group, stretch=2)
        
        # Set minimum height for the widget
        self.setMinimumHeight(140)
    
    def create_styled_lcd(
        self, 
        digits: int = 7, 
        height: int = 60,
        is_large: bool = False
    ) -> QLCDNumber:
        """
        Create a styled LCD display.
        
        Args:
            digits: Number of digits to display
            height: Minimum height of the LCD
            is_large: Whether this is a large/prominent display
        
        Returns:
            Styled QLCDNumber widget
        """
        lcd = QLCDNumber()
        lcd.setDigitCount(digits)
        lcd.setSegmentStyle(QLCDNumber.Flat)
        lcd.setMinimumHeight(height)
        lcd.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        if is_large:
            lcd.setStyleSheet("""
                QLCDNumber {
                    background-color: #1a1a2e;
                    color: #00ff88;
                    border: 3px solid #16213e;
                    border-radius: 8px;
                }
            """)
        else:
            lcd.setStyleSheet("""
                QLCDNumber {
                    background-color: #f0f0f0;
                    color: #2c3e50;
                    border: 2px solid #bdc3c7;
                    border-radius: 6px;
                }
            """)
        
        return lcd
    
    def create_vacuum_display(self) -> QGroupBox:
        """
        Create vacuum pressure display group.
        
        Returns:
            QGroupBox: Vacuum display group
        """
        group = QGroupBox("Vacuum Pressure")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #3498db;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: white;
            }
        """)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        
        # Vacuum in bar
        bar_layout = QHBoxLayout()
        bar_label = QLabel("bar:")
        bar_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #555;")
        bar_label.setFixedWidth(35)
        self.vacuum_bar_lcd = self.create_styled_lcd(digits=7, height=45)
        bar_layout.addWidget(bar_label)
        bar_layout.addWidget(self.vacuum_bar_lcd)
        layout.addLayout(bar_layout)
        
        # Vacuum in PSI
        psi_layout = QHBoxLayout()
        psi_label = QLabel("PSI:")
        psi_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #555;")
        psi_label.setFixedWidth(35)
        self.vacuum_psi_lcd = self.create_styled_lcd(digits=7, height=45)
        psi_layout.addWidget(psi_label)
        psi_layout.addWidget(self.vacuum_psi_lcd)
        layout.addLayout(psi_layout)
        
        group.setLayout(layout)
        return group
    
    def create_force_display(self) -> QGroupBox:
        """
        Create total force display group - LARGE and prominent.
        
        Returns:
            QGroupBox: Force display group
        """
        group = QGroupBox("Total Force")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 14pt;
                font-weight: bold;
                color: #1a1a2e;
                border: 3px solid #27ae60;
                border-radius: 10px;
                margin-top: 14px;
                padding-top: 12px;
                background-color: #f8fff8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 10px;
                background-color: #f8fff8;
            }
        """)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Large prominent force display
        self.force_lcd = self.create_styled_lcd(digits=7, height=80, is_large=True)
        layout.addWidget(self.force_lcd)
        
        # Unit label
        unit_label = QLabel("kg")
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            color: #27ae60;
        """)
        layout.addWidget(unit_label)
        
        group.setLayout(layout)
        return group
    
    def create_load_cells_display(self) -> QGroupBox:
        """
        Create individual load cells display group.
        
        Returns:
            QGroupBox: Load cells display group
        """
        group = QGroupBox("Individual Load Cells (kg)")
        group.setStyleSheet("""
            QGroupBox {
                font-size: 12pt;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #9b59b6;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: white;
            }
        """)
        layout = QGridLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(10, 15, 10, 10)
        
        # Create 4 load cell displays in 2x2 grid
        self.load_cell_lcds = []
        
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        colors = ["#e74c3c", "#3498db", "#f39c12", "#1abc9c"]  # Different colors for each
        
        for i, ((row, col), color) in enumerate(zip(positions, colors), start=1):
            # Container for label + LCD
            cell_layout = QVBoxLayout()
            
            label = QLabel(f"LC{i}")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(f"""
                font-size: 10pt;
                font-weight: bold;
                color: {color};
            """)
            
            lcd = QLCDNumber()
            lcd.setDigitCount(6)
            lcd.setSegmentStyle(QLCDNumber.Flat)
            lcd.setMinimumHeight(40)
            lcd.setStyleSheet(f"""
                QLCDNumber {{
                    background-color: #fafafa;
                    color: {color};
                    border: 2px solid {color};
                    border-radius: 5px;
                }}
            """)
            
            cell_layout.addWidget(label)
            cell_layout.addWidget(lcd)
            
            # Create container widget for the cell
            cell_widget = QWidget()
            cell_widget.setLayout(cell_layout)
            
            layout.addWidget(cell_widget, row, col)
            self.load_cell_lcds.append(lcd)
        
        group.setLayout(layout)
        return group
    
    def update_values(self, data: Dict[str, Any]) -> None:
        """
        Update displayed values with new sensor data.
        
        Args:
            data: Dictionary containing sensor readings
        """
        # Update vacuum displays
        if "vacuum_bar" in data:
            self.vacuum_bar_lcd.display(f"{data['vacuum_bar']:.3f}")
        
        if "vacuum_psi" in data:
            self.vacuum_psi_lcd.display(f"{data['vacuum_psi']:.2f}")
        elif "pressure_psi" in data:
            # Calculate vacuum from pressure if not provided
            vacuum_psi = 14.7 - data["pressure_psi"]
            self.vacuum_psi_lcd.display(f"{vacuum_psi:.2f}")
        
        # Update total force - sum of individual load cells (already software-tared)
        # This is more reliable than the TLB4's internal gross/net registers
        total_force = 0.0
        has_load_cells = False
        for i in range(4):
            key = f"load_cell_{i+1}_kg"
            if key in data:
                total_force += data[key]
                has_load_cells = True
        
        if has_load_cells:
            self.force_lcd.display(f"{total_force:.2f}")
        elif "net_weight_kg" in data:
            self.force_lcd.display(f"{data['net_weight_kg']:.2f}")
        elif "gross_weight_kg" in data:
            self.force_lcd.display(f"{data['gross_weight_kg']:.2f}")
        elif "total_force_kg" in data:
            self.force_lcd.display(f"{data['total_force_kg']:.2f}")
        
        # Update individual load cells
        for i in range(4):
            key = f"load_cell_{i+1}_kg"
            if key in data:
                self.load_cell_lcds[i].display(f"{data[key]:.2f}")
    
    def set_warning_state(self, is_warning: bool) -> None:
        """
        Set visual warning state for the force display.
        
        Args:
            is_warning: True to show warning colors
        """
        if is_warning:
            self.force_lcd.setStyleSheet("""
                QLCDNumber {
                    background-color: #7f0000;
                    color: #ff4444;
                    border: 3px solid #ff0000;
                    border-radius: 8px;
                }
            """)
            logger.warning("Force display in WARNING state")
        else:
            self.force_lcd.setStyleSheet("""
                QLCDNumber {
                    background-color: #1a1a2e;
                    color: #00ff88;
                    border: 3px solid #16213e;
                    border-radius: 8px;
                }
            """)
            logger.info("Force display WARNING cleared")
