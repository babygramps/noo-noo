"""
Gasket Assembly Weighing Dialog

Professional dialog for weighing gasket + frame assemblies before testing.
Captures the weight and stores it in test metadata for traceability.

Features:
- Live weight display from load cells
- Stability detection for accurate capture
- Tare functionality
- Assembly identification fields
- Professional, step-by-step UX
"""

from typing import Optional, Dict, Any, Callable
import logging
import time
from collections import deque
from dataclasses import dataclass

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QFrame,
    QProgressBar,
    QMessageBox,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QPalette, QColor

logger = logging.getLogger(__name__)


@dataclass
class WeighingResult:
    """Result from gasket weighing operation."""
    weight_kg: float
    assembly_id: str
    assembly_description: str
    timestamp: float
    is_tared: bool
    individual_cells: Dict[str, float]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "gasket_assembly_weight_kg": round(self.weight_kg, 3),
            "gasket_assembly_id": self.assembly_id or None,
            "gasket_assembly_description": self.assembly_description or None,
            "gasket_weight_timestamp": self.timestamp,
            "gasket_weight_tared": self.is_tared,
            "gasket_weight_individual_cells_kg": {
                f"cell_{i+1}": round(v, 3) 
                for i, (k, v) in enumerate(self.individual_cells.items())
            },
        }


class StabilityIndicator(QFrame):
    """Visual indicator for weight reading stability."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 30)
        self._stable = False
        self._stability_percent = 0.0
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.status_label = QLabel("Waiting...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self._update_style()
        
        layout.addWidget(self.status_label)
    
    def _update_style(self):
        if self._stable:
            self.setStyleSheet("""
                QFrame {
                    background-color: #27ae60;
                    border-radius: 8px;
                    border: 2px solid #1e8449;
                }
            """)
            self.status_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 11pt;
                }
            """)
            self.status_label.setText("✓ STABLE")
        elif self._stability_percent > 50:
            self.setStyleSheet("""
                QFrame {
                    background-color: #f39c12;
                    border-radius: 8px;
                    border: 2px solid #d68910;
                }
            """)
            self.status_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 11pt;
                }
            """)
            self.status_label.setText("Stabilizing...")
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #7f8c8d;
                    border-radius: 8px;
                    border: 2px solid #5d6d7e;
                }
            """)
            self.status_label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-weight: bold;
                    font-size: 11pt;
                }
            """)
            self.status_label.setText("Waiting...")
    
    def set_stable(self, stable: bool, percent: float = 0.0):
        self._stable = stable
        self._stability_percent = percent
        self._update_style()


class GasketWeighingDialog(QDialog):
    """
    Professional dialog for weighing gasket + frame assemblies.
    
    Provides:
    - Live weight display with stability detection
    - Tare functionality for zero-offset
    - Assembly ID and description fields
    - Professional step-by-step workflow
    
    Signals:
        weight_captured: Emitted when weight is successfully captured with WeighingResult
    """
    
    weight_captured = pyqtSignal(object)  # WeighingResult
    
    # Stability parameters
    STABILITY_WINDOW_SIZE = 20  # Samples to check for stability (~2 seconds at 10Hz)
    STABILITY_THRESHOLD_KG = 0.010  # Must be within 10g for stable reading
    MIN_STABLE_DURATION = 1.0  # Seconds of stable readings required
    
    def __init__(
        self, 
        parent=None,
        modbus_interface=None,
        get_current_data_callback: Optional[Callable[[], Dict[str, Any]]] = None,
    ):
        """
        Initialize the gasket weighing dialog.
        
        Args:
            parent: Parent widget
            modbus_interface: ModbusInterface for tare operations
            get_current_data_callback: Callback to get current sensor data
        """
        super().__init__(parent)
        
        self.modbus_interface = modbus_interface
        self.get_current_data = get_current_data_callback
        
        # Weighing state
        self._weight_history: deque = deque(maxlen=self.STABILITY_WINDOW_SIZE)
        self._is_stable = False
        self._stable_since: Optional[float] = None
        self._captured_weight: Optional[float] = None
        self._is_tared = False
        self._current_weight = 0.0
        self._individual_cells: Dict[str, float] = {}
        
        # Update timer
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._update_display)
        
        self._setup_ui()
        logger.info("GasketWeighingDialog initialized")
    
    def _setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Weigh Gasket Assembly")
        self.setModal(True)
        self.setMinimumSize(550, 650)
        self.setMaximumSize(700, 800)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header with instructions
        self._create_header(layout)
        
        # Weight display section
        self._create_weight_display(layout)
        
        # Tare controls
        self._create_tare_controls(layout)
        
        # Assembly identification
        self._create_assembly_fields(layout)
        
        # Action buttons
        self._create_action_buttons(layout)
        
        # Apply global dialog styling
        self.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
            QGroupBox {
                font-size: 11pt;
                font-weight: bold;
                color: #2c3e50;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                background-color: #f8f9fa;
            }
        """)
    
    def _create_header(self, layout: QVBoxLayout):
        """Create the header with instructions."""
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2c3e50;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        title = QLabel("⚖️ Gasket Assembly Weighing")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 18pt;
                font-weight: bold;
            }
        """)
        title.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title)
        
        instructions = QLabel(
            "Place the gasket + frame assembly on the test fixture.\n"
            "Wait for the reading to stabilize, then capture the weight."
        )
        instructions.setStyleSheet("""
            QLabel {
                color: #ecf0f1;
                font-size: 10pt;
            }
        """)
        instructions.setAlignment(Qt.AlignCenter)
        instructions.setWordWrap(True)
        header_layout.addWidget(instructions)
        
        layout.addWidget(header_frame)
    
    def _create_weight_display(self, layout: QVBoxLayout):
        """Create the live weight display section."""
        group = QGroupBox("Current Weight")
        group.setStyleSheet("""
            QGroupBox {
                border: 3px solid #27ae60;
                background-color: #ffffff;
            }
            QGroupBox::title {
                color: #27ae60;
            }
        """)
        group_layout = QVBoxLayout()
        group_layout.setSpacing(10)
        
        # Large weight display
        self.weight_display = QLabel("0.000")
        self.weight_display.setAlignment(Qt.AlignCenter)
        self.weight_display.setStyleSheet("""
            QLabel {
                background-color: #1a1a2e;
                color: #00ff88;
                font-size: 48pt;
                font-weight: bold;
                font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                border: 3px solid #16213e;
                border-radius: 10px;
                padding: 20px;
                min-height: 80px;
            }
        """)
        group_layout.addWidget(self.weight_display)
        
        # Unit label
        unit_label = QLabel("kg")
        unit_label.setAlignment(Qt.AlignCenter)
        unit_label.setStyleSheet("""
            QLabel {
                font-size: 16pt;
                font-weight: bold;
                color: #27ae60;
            }
        """)
        group_layout.addWidget(unit_label)
        
        # Stability indicator and individual cells row
        status_row = QHBoxLayout()
        
        # Stability indicator
        stability_container = QVBoxLayout()
        stability_title = QLabel("Reading Status:")
        stability_title.setStyleSheet("font-size: 9pt; color: #7f8c8d;")
        stability_container.addWidget(stability_title)
        
        self.stability_indicator = StabilityIndicator()
        stability_container.addWidget(self.stability_indicator)
        status_row.addLayout(stability_container)
        
        status_row.addStretch()
        
        # Individual load cells display (compact)
        cells_container = QVBoxLayout()
        cells_title = QLabel("Individual Cells (kg):")
        cells_title.setStyleSheet("font-size: 9pt; color: #7f8c8d;")
        cells_container.addWidget(cells_title)
        
        self.cells_display = QLabel("LC1: --  LC2: --  LC3: --  LC4: --")
        self.cells_display.setStyleSheet("""
            QLabel {
                font-size: 9pt;
                font-family: 'Consolas', monospace;
                color: #2c3e50;
                background-color: #ecf0f1;
                padding: 5px 10px;
                border-radius: 4px;
            }
        """)
        cells_container.addWidget(self.cells_display)
        status_row.addLayout(cells_container)
        
        group_layout.addLayout(status_row)
        
        group.setLayout(group_layout)
        layout.addWidget(group)
    
    def _create_tare_controls(self, layout: QVBoxLayout):
        """Create tare control section."""
        tare_frame = QFrame()
        tare_frame.setStyleSheet("""
            QFrame {
                background-color: #fff3cd;
                border: 2px solid #ffc107;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        tare_layout = QHBoxLayout(tare_frame)
        
        tare_icon = QLabel("💡")
        tare_icon.setStyleSheet("font-size: 20pt;")
        tare_layout.addWidget(tare_icon)
        
        tare_text = QLabel(
            "Tip: If you need to zero the scale (e.g., to exclude fixture weight),\n"
            "use the Tare button before placing the gasket assembly."
        )
        tare_text.setStyleSheet("font-size: 9pt; color: #856404;")
        tare_text.setWordWrap(True)
        tare_layout.addWidget(tare_text, stretch=1)
        
        self.tare_btn = QPushButton("Tare Scale")
        self.tare_btn.setFixedSize(100, 35)
        self.tare_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffc107;
                color: #212529;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #ffca2c;
            }
            QPushButton:pressed {
                background-color: #e0a800;
            }
        """)
        self.tare_btn.clicked.connect(self._on_tare)
        tare_layout.addWidget(self.tare_btn)
        
        layout.addWidget(tare_frame)
    
    def _create_assembly_fields(self, layout: QVBoxLayout):
        """Create assembly identification fields."""
        group = QGroupBox("Assembly Identification (Optional)")
        form = QFormLayout()
        form.setSpacing(10)
        
        # Assembly ID
        self.assembly_id_edit = QLineEdit()
        self.assembly_id_edit.setPlaceholderText("e.g., GASKET-001, FRAME-A-2025")
        self.assembly_id_edit.setStyleSheet("""
            QLineEdit {
                font-size: 11pt;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
            }
            QLineEdit:focus {
                border-color: #3498db;
            }
        """)
        form.addRow("Assembly ID:", self.assembly_id_edit)
        
        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText(
            "Optional notes: gasket material, frame type, batch number, etc."
        )
        self.description_edit.setMaximumHeight(80)
        self.description_edit.setStyleSheet("""
            QTextEdit {
                font-size: 10pt;
                padding: 8px;
                border: 2px solid #bdc3c7;
                border-radius: 6px;
                background-color: white;
            }
            QTextEdit:focus {
                border-color: #3498db;
            }
        """)
        form.addRow("Description:", self.description_edit)
        
        group.setLayout(form)
        layout.addWidget(group)
    
    def _create_action_buttons(self, layout: QVBoxLayout):
        """Create action buttons."""
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        # Skip button
        self.skip_btn = QPushButton("Skip Weighing")
        self.skip_btn.setFixedHeight(45)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                font-size: 11pt;
                font-weight: bold;
                border: none;
                border-radius: 8px;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        self.skip_btn.clicked.connect(self._on_skip)
        button_layout.addWidget(self.skip_btn)
        
        button_layout.addStretch()
        
        # Capture Weight button
        self.capture_btn = QPushButton("📥 Capture Weight")
        self.capture_btn.setFixedHeight(50)
        self.capture_btn.setMinimumWidth(200)
        self.capture_btn.setEnabled(False)  # Disabled until stable
        self.capture_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                font-size: 14pt;
                font-weight: bold;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
                color: #7f8c8d;
            }
        """)
        self.capture_btn.clicked.connect(self._on_capture)
        button_layout.addWidget(self.capture_btn)
        
        layout.addLayout(button_layout)
        
        # Hint text
        hint = QLabel("Reading must be stable for at least 1 second to capture")
        hint.setStyleSheet("color: #7f8c8d; font-size: 9pt; font-style: italic;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
    
    def showEvent(self, event):
        """Start updates when dialog is shown."""
        super().showEvent(event)
        self._weight_history.clear()
        self._is_stable = False
        self._stable_since = None
        self._update_timer.start(100)  # Update at 10Hz
        logger.info("GasketWeighingDialog shown, starting weight updates")
    
    def hideEvent(self, event):
        """Stop updates when dialog is hidden."""
        super().hideEvent(event)
        self._update_timer.stop()
        logger.info("GasketWeighingDialog hidden, stopped weight updates")
    
    def _update_display(self):
        """Update the weight display with current readings."""
        if not self.get_current_data:
            return
        
        try:
            data = self.get_current_data()
            if not data:
                return
            
            # Calculate total weight from individual cells
            total_weight = 0.0
            cells = {}
            for i in range(1, 5):
                key = f"load_cell_{i}_kg"
                if key in data:
                    cells[key] = data[key]
                    total_weight += data[key]
            
            # Fallback to total_force_kg if individual cells not available
            if not cells and "total_force_kg" in data:
                total_weight = data["total_force_kg"]
            
            self._current_weight = total_weight
            self._individual_cells = cells
            
            # Update display
            self.weight_display.setText(f"{total_weight:.3f}")
            
            # Update individual cells display
            if cells:
                cell_text = "  ".join([
                    f"LC{i}: {cells.get(f'load_cell_{i}_kg', 0):.2f}"
                    for i in range(1, 5)
                ])
                self.cells_display.setText(cell_text)
            
            # Check stability
            self._check_stability(total_weight)
            
        except Exception as e:
            logger.warning(f"Error updating weight display: {e}")
    
    def _check_stability(self, current_weight: float):
        """Check if readings are stable enough for capture."""
        current_time = time.time()
        self._weight_history.append((current_time, current_weight))
        
        if len(self._weight_history) < self.STABILITY_WINDOW_SIZE // 2:
            # Not enough samples yet
            self.stability_indicator.set_stable(False, 
                len(self._weight_history) / self.STABILITY_WINDOW_SIZE * 100)
            self._is_stable = False
            self._stable_since = None
            self.capture_btn.setEnabled(False)
            return
        
        # Calculate variation in the window
        weights = [w for _, w in self._weight_history]
        weight_range = max(weights) - min(weights)
        
        # Stability percentage (inverse of variation)
        stability_pct = max(0, min(100, (1 - weight_range / self.STABILITY_THRESHOLD_KG) * 100))
        
        is_currently_stable = weight_range <= self.STABILITY_THRESHOLD_KG
        
        if is_currently_stable:
            if self._stable_since is None:
                self._stable_since = current_time
            
            stable_duration = current_time - self._stable_since
            
            if stable_duration >= self.MIN_STABLE_DURATION:
                self._is_stable = True
                self.stability_indicator.set_stable(True)
                self.capture_btn.setEnabled(True)
                
                # Update display style to show stable state
                self.weight_display.setStyleSheet("""
                    QLabel {
                        background-color: #1a2e1a;
                        color: #00ff88;
                        font-size: 48pt;
                        font-weight: bold;
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                        border: 3px solid #27ae60;
                        border-radius: 10px;
                        padding: 20px;
                        min-height: 80px;
                    }
                """)
            else:
                # Still waiting for stable duration
                self.stability_indicator.set_stable(False, 50 + (stable_duration / self.MIN_STABLE_DURATION) * 50)
        else:
            self._stable_since = None
            self._is_stable = False
            self.stability_indicator.set_stable(False, stability_pct)
            self.capture_btn.setEnabled(False)
            
            # Reset display style
            self.weight_display.setStyleSheet("""
                QLabel {
                    background-color: #1a1a2e;
                    color: #00ff88;
                    font-size: 48pt;
                    font-weight: bold;
                    font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                    border: 3px solid #16213e;
                    border-radius: 10px;
                    padding: 20px;
                    min-height: 80px;
                }
            """)
    
    def _on_tare(self):
        """Handle tare button click."""
        logger.info("Tare requested from gasket weighing dialog")
        
        if self.modbus_interface:
            try:
                success = self.modbus_interface.tare_load_cells()
                if success:
                    self._is_tared = True
                    self._weight_history.clear()
                    self._stable_since = None
                    
                    QMessageBox.information(
                        self,
                        "Tare Complete",
                        "Scale has been tared. The current weight is now zero.\n\n"
                        "Place your gasket assembly on the fixture to weigh it."
                    )
                    logger.info("Tare successful")
                else:
                    QMessageBox.warning(
                        self,
                        "Tare Failed",
                        "Failed to tare the scale. Please try again."
                    )
            except Exception as e:
                logger.error(f"Tare error: {e}")
                QMessageBox.warning(
                    self,
                    "Tare Error",
                    f"Error during tare operation: {e}"
                )
        else:
            QMessageBox.warning(
                self,
                "Hardware Not Connected",
                "Load cell interface not available. Cannot tare."
            )
    
    def _on_capture(self):
        """Handle capture button click."""
        if not self._is_stable:
            QMessageBox.warning(
                self,
                "Reading Not Stable",
                "Please wait for the reading to stabilize before capturing."
            )
            return
        
        # Capture the weight
        self._captured_weight = self._current_weight
        
        result = WeighingResult(
            weight_kg=self._captured_weight,
            assembly_id=self.assembly_id_edit.text().strip(),
            assembly_description=self.description_edit.toPlainText().strip(),
            timestamp=time.time(),
            is_tared=self._is_tared,
            individual_cells=self._individual_cells.copy(),
        )
        
        logger.info(f"Weight captured: {result.weight_kg:.3f} kg")
        
        self.weight_captured.emit(result)
        self.accept()
    
    def _on_skip(self):
        """Handle skip button click."""
        reply = QMessageBox.question(
            self,
            "Skip Weighing?",
            "Are you sure you want to skip weighing the gasket assembly?\n\n"
            "The test will proceed without recording the assembly weight.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("Gasket weighing skipped by user")
            self.reject()
    
    def get_result(self) -> Optional[WeighingResult]:
        """Get the captured weighing result."""
        if self._captured_weight is not None:
            return WeighingResult(
                weight_kg=self._captured_weight,
                assembly_id=self.assembly_id_edit.text().strip(),
                assembly_description=self.description_edit.toPlainText().strip(),
                timestamp=time.time(),
                is_tared=self._is_tared,
                individual_cells=self._individual_cells.copy(),
            )
        return None

