"""
Display Widget - Real-time Sensor Display

Shows current sensor readings in an easy-to-read format:
- Vacuum pressure
- Total force
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
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor

logger = logging.getLogger(__name__)


class DisplayWidget(QWidget):
    """
    Widget for displaying real-time sensor values.
    
    Displays:
    - Vacuum pressure (bar and PSI)
    - Total force (kg)
    - Individual load cell readings
    """
    
    def __init__(self):
        """Initialize the display widget."""
        super().__init__()
        
        self.init_ui()
        logger.info("DisplayWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QHBoxLayout(self)
        
        # Vacuum display group
        vacuum_group = self.create_vacuum_display()
        layout.addWidget(vacuum_group)
        
        # Force display group
        force_group = self.create_force_display()
        layout.addWidget(force_group)
        
        # Load cells display group
        load_cells_group = self.create_load_cells_display()
        layout.addWidget(load_cells_group)
    
    def create_vacuum_display(self) -> QGroupBox:
        """
        Create vacuum pressure display group.
        
        Returns:
            QGroupBox: Vacuum display group
        """
        group = QGroupBox("Vacuum Pressure")
        layout = QVBoxLayout()
        
        # Vacuum in bar
        bar_layout = QHBoxLayout()
        bar_label = QLabel("Vacuum (bar):")
        self.vacuum_bar_lcd = QLCDNumber()
        self.vacuum_bar_lcd.setDigitCount(6)
        self.vacuum_bar_lcd.setSegmentStyle(QLCDNumber.Flat)
        bar_layout.addWidget(bar_label)
        bar_layout.addWidget(self.vacuum_bar_lcd)
        layout.addLayout(bar_layout)
        
        # Vacuum in PSI
        psi_layout = QHBoxLayout()
        psi_label = QLabel("Vacuum (PSI):")
        self.vacuum_psi_lcd = QLCDNumber()
        self.vacuum_psi_lcd.setDigitCount(6)
        self.vacuum_psi_lcd.setSegmentStyle(QLCDNumber.Flat)
        psi_layout.addWidget(psi_label)
        psi_layout.addWidget(self.vacuum_psi_lcd)
        layout.addLayout(psi_layout)
        
        group.setLayout(layout)
        return group
    
    def create_force_display(self) -> QGroupBox:
        """
        Create total force display group.
        
        Returns:
            QGroupBox: Force display group
        """
        group = QGroupBox("Total Force")
        layout = QVBoxLayout()
        
        # Total force in kg
        force_layout = QHBoxLayout()
        force_label = QLabel("Force (kg):")
        self.force_lcd = QLCDNumber()
        self.force_lcd.setDigitCount(7)
        self.force_lcd.setSegmentStyle(QLCDNumber.Flat)
        force_layout.addWidget(force_label)
        force_layout.addWidget(self.force_lcd)
        layout.addLayout(force_layout)
        
        group.setLayout(layout)
        return group
    
    def create_load_cells_display(self) -> QGroupBox:
        """
        Create individual load cells display group.
        
        Returns:
            QGroupBox: Load cells display group
        """
        group = QGroupBox("Individual Load Cells (kg)")
        layout = QGridLayout()
        
        # Create 4 load cell displays in 2x2 grid
        self.load_cell_lcds = []
        
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        for i, (row, col) in enumerate(positions, start=1):
            label = QLabel(f"LC{i}:")
            lcd = QLCDNumber()
            lcd.setDigitCount(6)
            lcd.setSegmentStyle(QLCDNumber.Flat)
            
            layout.addWidget(label, row, col * 2)
            layout.addWidget(lcd, row, col * 2 + 1)
            
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
        
        # Update total force
        if "gross_weight_kg" in data:
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
        Set visual warning state.
        
        Args:
            is_warning: True to show warning colors
        """
        # TODO: Implement color change for warning state
        # Could change LCD colors to yellow/red when limits exceeded
        logger.warning("TODO: Warning state visual feedback not implemented")

