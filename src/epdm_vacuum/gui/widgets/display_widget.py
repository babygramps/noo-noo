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
    QComboBox,
    QPushButton,
    QDialog,
    QDoubleSpinBox,
    QDialogButtonBox,
    QFormLayout,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPalette, QColor, QFont

logger = logging.getLogger(__name__)


# Pressure unit conversion factors (from PSI)
PRESSURE_UNITS = {
    "PSIG": {"factor": 1.0, "decimals": 2, "label": "PSIG"},
    "bar": {"factor": 0.0689476, "decimals": 4, "label": "bar"},
    "mbar": {"factor": 68.9476, "decimals": 1, "label": "mbar"},
    "kPa": {"factor": 6.89476, "decimals": 2, "label": "kPa"},
    "Torr": {"factor": 51.7149, "decimals": 1, "label": "Torr"},
    "inHg": {"factor": 2.03602, "decimals": 2, "label": "inHg"},
    "atm": {"factor": 0.068046, "decimals": 4, "label": "atm"},
}

# Default sense resistor value (can be calibrated by user)
DEFAULT_SENSE_RESISTOR_OHMS = 454.0


class DisplayWidget(QWidget):
    """
    Widget for displaying real-time sensor values.
    
    Displays:
    - Pressure (gauge) with selectable units
    - Total force (kg) - LARGE prominent display
    - Individual load cell readings
    """
    
    def __init__(self):
        """Initialize the display widget."""
        super().__init__()
        
        # Settings for persistence
        self.settings = QSettings("EPDM", "VacuumTestFixture")
        
        # Current pressure in PSIG (base unit)
        self._current_pressure_psig = 0.0
        
        # Current raw voltage (for calibration)
        self._current_voltage = 0.0
        
        # Load calibrated sense resistor value
        self._sense_resistor_ohms = float(self.settings.value(
            "sense_resistor_ohms", DEFAULT_SENSE_RESISTOR_OHMS
        ))
        
        self.init_ui()
        
        # Restore saved unit preference
        saved_unit = self.settings.value("pressure_unit", "PSIG")
        if saved_unit in PRESSURE_UNITS:
            index = list(PRESSURE_UNITS.keys()).index(saved_unit)
            self.unit_selector.setCurrentIndex(index)
        
        logger.info(f"DisplayWidget initialized (sense resistor: {self._sense_resistor_ohms}Ω)")
    
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
        Create pressure display group with unit selector.
        
        Shows gauge pressure with user-selectable units:
        - Positive = above atmospheric
        - Negative = vacuum (below atmospheric)
        
        Returns:
            QGroupBox: Pressure display group
        """
        group = QGroupBox("Pressure (Gauge)")
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
        
        # Unit selector row
        unit_layout = QHBoxLayout()
        unit_label = QLabel("Unit:")
        unit_label.setStyleSheet("font-size: 10pt; color: #555;")
        self.unit_selector = QComboBox()
        self.unit_selector.addItems(list(PRESSURE_UNITS.keys()))
        self.unit_selector.setStyleSheet("""
            QComboBox {
                font-size: 10pt;
                padding: 4px 8px;
                border: 1px solid #bdc3c7;
                border-radius: 4px;
                background-color: white;
            }
            QComboBox:hover {
                border-color: #3498db;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
        """)
        self.unit_selector.currentTextChanged.connect(self._on_unit_changed)
        unit_layout.addWidget(unit_label)
        unit_layout.addWidget(self.unit_selector)
        unit_layout.addStretch()
        layout.addLayout(unit_layout)
        
        # Main pressure display with dynamic unit label
        pressure_layout = QHBoxLayout()
        self.pressure_unit_label = QLabel("PSIG:")
        self.pressure_unit_label.setStyleSheet("font-size: 11pt; font-weight: bold; color: #555;")
        self.pressure_unit_label.setFixedWidth(50)
        self.pressure_lcd = self.create_styled_lcd(digits=8, height=55)
        pressure_layout.addWidget(self.pressure_unit_label)
        pressure_layout.addWidget(self.pressure_lcd)
        layout.addLayout(pressure_layout)
        
        # Raw current display (4-20mA transmitter) with calibration button
        raw_layout = QHBoxLayout()
        raw_label = QLabel("mA:")
        raw_label.setStyleSheet("font-size: 9pt; color: #888;")
        raw_label.setFixedWidth(50)
        self.raw_current_label = QLabel("-- mA")
        self.raw_current_label.setStyleSheet("font-size: 9pt; color: #888; font-family: monospace;")
        self.raw_current_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        
        # Calibration button
        self.calibrate_btn = QPushButton("Cal")
        self.calibrate_btn.setFixedSize(35, 22)
        self.calibrate_btn.setToolTip("Calibrate mA reading using multimeter")
        self.calibrate_btn.setStyleSheet("""
            QPushButton {
                font-size: 8pt;
                padding: 2px;
                background-color: #ecf0f1;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #3498db;
                color: white;
            }
        """)
        self.calibrate_btn.clicked.connect(self._show_calibration_dialog)
        
        raw_layout.addWidget(raw_label)
        raw_layout.addWidget(self.raw_current_label)
        raw_layout.addWidget(self.calibrate_btn)
        layout.addLayout(raw_layout)
        
        group.setLayout(layout)
        return group
    
    def _show_calibration_dialog(self) -> None:
        """Show the mA calibration dialog."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Calibrate mA Reading")
        dialog.setMinimumWidth(350)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        instructions = QLabel(
            "Enter the current reading from your multimeter (in series with the transmitter).\n"
            "The app will calibrate the sense resistor value to match."
        )
        instructions.setWordWrap(True)
        instructions.setStyleSheet("color: #555; margin-bottom: 10px;")
        layout.addWidget(instructions)
        
        # Current readings display
        readings_group = QGroupBox("Current Readings")
        readings_layout = QFormLayout()
        
        voltage_label = QLabel(f"{self._current_voltage:.4f} V")
        voltage_label.setStyleSheet("font-weight: bold; font-family: monospace;")
        readings_layout.addRow("ADC Voltage:", voltage_label)
        
        current_mA = (self._current_voltage / self._sense_resistor_ohms) * 1000.0 if self._sense_resistor_ohms > 0 else 0
        app_ma_label = QLabel(f"{current_mA:.2f} mA")
        app_ma_label.setStyleSheet("font-weight: bold; font-family: monospace;")
        readings_layout.addRow("App shows:", app_ma_label)
        
        resistor_label = QLabel(f"{self._sense_resistor_ohms:.1f} Ω")
        resistor_label.setStyleSheet("font-family: monospace;")
        readings_layout.addRow("Current resistor:", resistor_label)
        
        readings_group.setLayout(readings_layout)
        layout.addWidget(readings_group)
        
        # Multimeter input
        input_group = QGroupBox("Multimeter Reading")
        input_layout = QFormLayout()
        
        self._cal_spinbox = QDoubleSpinBox()
        self._cal_spinbox.setRange(0.0, 25.0)
        self._cal_spinbox.setDecimals(2)
        self._cal_spinbox.setSuffix(" mA")
        self._cal_spinbox.setValue(current_mA)  # Start with current value
        self._cal_spinbox.setStyleSheet("font-size: 12pt; padding: 5px;")
        input_layout.addRow("Multimeter mA:", self._cal_spinbox)
        
        # Show calculated resistor
        self._calc_resistor_label = QLabel("--")
        self._calc_resistor_label.setStyleSheet("font-family: monospace; color: #27ae60;")
        input_layout.addRow("Calculated resistor:", self._calc_resistor_label)
        
        self._cal_spinbox.valueChanged.connect(self._update_calculated_resistor)
        self._update_calculated_resistor()  # Initial calculation
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Reset
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        button_box.button(QDialogButtonBox.Reset).clicked.connect(self._reset_calibration)
        button_box.button(QDialogButtonBox.Reset).setText("Reset to Default")
        layout.addWidget(button_box)
        
        # Store dialog reference for reset
        self._cal_dialog = dialog
        
        if dialog.exec_() == QDialog.Accepted:
            self._apply_calibration()
    
    def _update_calculated_resistor(self) -> None:
        """Update the calculated resistor value based on multimeter input."""
        multimeter_mA = self._cal_spinbox.value()
        if multimeter_mA > 0.1 and self._current_voltage > 0.1:
            # R = V / I
            calculated_R = (self._current_voltage / multimeter_mA) * 1000.0
            self._calc_resistor_label.setText(f"{calculated_R:.1f} Ω")
            self._calc_resistor_label.setStyleSheet("font-family: monospace; color: #27ae60;")
        else:
            self._calc_resistor_label.setText("Need valid readings")
            self._calc_resistor_label.setStyleSheet("font-family: monospace; color: #e74c3c;")
    
    def _apply_calibration(self) -> None:
        """Apply the calibration from the dialog."""
        multimeter_mA = self._cal_spinbox.value()
        if multimeter_mA > 0.1 and self._current_voltage > 0.1:
            # Calculate new resistor value: R = V / I
            new_resistor = (self._current_voltage / multimeter_mA) * 1000.0
            
            # Sanity check
            if 100 < new_resistor < 1000:
                self._sense_resistor_ohms = new_resistor
                self.settings.setValue("sense_resistor_ohms", new_resistor)
                logger.info(f"Calibration applied: sense resistor = {new_resistor:.1f}Ω")
                
                QMessageBox.information(
                    self,
                    "Calibration Applied",
                    f"Sense resistor calibrated to {new_resistor:.1f}Ω\n\n"
                    f"The mA reading should now match your multimeter."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Calibration Error",
                    f"Calculated resistor value ({new_resistor:.1f}Ω) is outside reasonable range.\n"
                    "Expected 100-1000Ω. Please check your readings."
                )
    
    def _reset_calibration(self) -> None:
        """Reset calibration to default value."""
        self._sense_resistor_ohms = DEFAULT_SENSE_RESISTOR_OHMS
        self.settings.setValue("sense_resistor_ohms", DEFAULT_SENSE_RESISTOR_OHMS)
        self._cal_spinbox.setValue((self._current_voltage / DEFAULT_SENSE_RESISTOR_OHMS) * 1000.0)
        self._update_calculated_resistor()
        logger.info(f"Calibration reset to default: {DEFAULT_SENSE_RESISTOR_OHMS}Ω")
    
    def get_sense_resistor(self) -> float:
        """Get the current calibrated sense resistor value."""
        return self._sense_resistor_ohms
    
    def _on_unit_changed(self, unit_name: str) -> None:
        """
        Handle unit selector change.
        
        Args:
            unit_name: Selected unit name
        """
        # Save preference
        self.settings.setValue("pressure_unit", unit_name)
        
        # Update label
        unit_info = PRESSURE_UNITS.get(unit_name, PRESSURE_UNITS["PSIG"])
        self.pressure_unit_label.setText(f"{unit_info['label']}:")
        
        # Update display with current pressure
        self._update_pressure_display()
        
        logger.info(f"Pressure unit changed to: {unit_name}")
    
    def _update_pressure_display(self) -> None:
        """Update the pressure display with the current unit."""
        unit_name = self.unit_selector.currentText()
        unit_info = PRESSURE_UNITS.get(unit_name, PRESSURE_UNITS["PSIG"])
        
        # Convert from PSIG to selected unit
        converted_value = self._current_pressure_psig * unit_info["factor"]
        decimals = unit_info["decimals"]
        
        # Display the converted value
        self.pressure_lcd.display(round(converted_value, decimals))
    
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
        # Track update count for diagnostic logging
        if not hasattr(self, '_update_count'):
            self._update_count = 0
        self._update_count += 1
        
        # Log first few updates for debugging
        if self._update_count <= 5:
            logger.info(f"[DisplayWidget #{self._update_count}] Data keys: {list(data.keys())}")
            logger.info(f"  vacuum_bar={data.get('vacuum_bar')}, vacuum_psi={data.get('vacuum_psi')}")
            logger.info(f"  pressure_voltage={data.get('pressure_voltage')}, pressure_psi={data.get('pressure_psi')}")
        
        # Update pressure display - show gauge pressure in user-selected units
        # Positive = above atmospheric, Negative = vacuum
        if "pressure_psig" in data:
            self._current_pressure_psig = data['pressure_psig']
            self._update_pressure_display()
            
            if self._update_count <= 5:
                unit_name = self.unit_selector.currentText()
                unit_info = PRESSURE_UNITS.get(unit_name, PRESSURE_UNITS["PSIG"])
                converted = self._current_pressure_psig * unit_info["factor"]
                logger.info(f"  -> pressure: {self._current_pressure_psig:.2f} PSIG = {converted:.2f} {unit_name}")
        elif "pressure_psi" in data:
            # Legacy fallback
            self._current_pressure_psig = data['pressure_psi']
            self._update_pressure_display()
            if self._update_count <= 5:
                logger.info(f"  -> pressure (legacy): {self._current_pressure_psig:.2f} PSIG")
        else:
            if self._update_count <= 5:
                logger.warning(f"  -> pressure_psig NOT in data!")
        
        # Update raw current display (4-20mA transmitter)
        # Uses calibrated sense resistor value (user-adjustable via Cal button)
        if "pressure_voltage" in data:
            raw_v = data["pressure_voltage"]
            self._current_voltage = raw_v  # Store for calibration dialog
            
            # Convert voltage to mA using Ohm's law with calibrated resistor
            raw_mA = (raw_v / self._sense_resistor_ohms) * 1000.0
            
            self.raw_current_label.setText(f"{raw_mA:.2f} mA")
            
            # Color code: green if in valid range (4-20mA), yellow if near limits, red if out of range
            if raw_mA < 3.8 or raw_mA > 20.5:
                self.raw_current_label.setStyleSheet("font-size: 9pt; color: #e74c3c; font-family: monospace;")
            elif raw_mA < 4.2 or raw_mA > 19.8:
                self.raw_current_label.setStyleSheet("font-size: 9pt; color: #f39c12; font-family: monospace;")
            else:
                self.raw_current_label.setStyleSheet("font-size: 9pt; color: #27ae60; font-family: monospace;")
        
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
