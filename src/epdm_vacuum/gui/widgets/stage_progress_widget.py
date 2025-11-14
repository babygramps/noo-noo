"""
Stage Progress Widget - Visual Timeline Display

Shows test stage progression as a linear timeline with:
- All stages as milestones
- Current stage highlighted and animated
- Past stages shown as completed
- Future stages shown as pending
- Real-time progress within current stage
"""

from typing import Optional, List
import logging

from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QFrame,
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QFont

from ...control.sequence import TestSequence, TestStage

logger = logging.getLogger(__name__)


class StageProgressWidget(QWidget):
    """
    Widget displaying test stage progression as a visual timeline.
    
    Shows all stages with visual indicators for:
    - Completed stages (green)
    - Current stage (blue, animated)
    - Pending stages (gray)
    """
    
    def __init__(self, parent=None):
        """Initialize the stage progress widget."""
        super().__init__(parent)
        
        self.sequence: Optional[TestSequence] = None
        self.current_stage_index: int = -1
        self.completed_stages: set = set()
        self.stage_progress: float = 0.0  # 0.0 to 1.0
        self.completion_reason: str = ""
        self.elapsed_time: float = 0.0
        
        # Animation state
        self.animation_phase: float = 0.0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.setInterval(50)  # 20 FPS
        
        self.init_ui()
        logger.info("StageProgressWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title
        title_label = QLabel("Test Stage Progress")
        title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #333;")
        layout.addWidget(title_label)
        
        # Timeline canvas
        self.timeline_canvas = TimelineCanvas(self)
        self.timeline_canvas.setMinimumHeight(80)
        layout.addWidget(self.timeline_canvas)
        
        # Current stage info panel
        info_frame = QFrame()
        info_frame.setFrameShape(QFrame.StyledPanel)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(8, 8, 8, 8)
        info_layout.setSpacing(4)
        
        # Current stage name
        self.stage_name_label = QLabel("No test running")
        self.stage_name_label.setStyleSheet("font-size: 12pt; font-weight: bold; color: #2196F3;")
        info_layout.addWidget(self.stage_name_label)
        
        # Stage details (setpoint, time limit)
        self.stage_details_label = QLabel("")
        self.stage_details_label.setStyleSheet("font-size: 10pt; color: #666;")
        info_layout.addWidget(self.stage_details_label)
        
        # Progress bar for current stage
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                height: 24px;
                background-color: #fff;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 3px;
            }
        """)
        info_layout.addWidget(self.progress_bar)
        
        # Status text (elapsed time, completion reason)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("font-size: 10pt; color: #666;")
        info_layout.addWidget(self.status_label)
        
        layout.addWidget(info_frame)
        layout.addStretch()
    
    def set_sequence(self, sequence: TestSequence) -> None:
        """
        Set the test sequence to display.
        
        Args:
            sequence: TestSequence to visualize
        """
        self.sequence = sequence
        self.current_stage_index = -1
        self.completed_stages.clear()
        self.stage_progress = 0.0
        self.completion_reason = ""
        self.elapsed_time = 0.0
        
        self.timeline_canvas.set_sequence(sequence)
        self._update_display()
        
        logger.info(f"Set sequence: {sequence.name} with {len(sequence.stages)} stages")
    
    def set_current_stage(self, stage_index: int, stage_name: str) -> None:
        """
        Set the currently executing stage.
        
        Args:
            stage_index: Index of current stage (0-based)
            stage_name: Name of the current stage
        """
        self.current_stage_index = stage_index
        self.stage_progress = 0.0
        self.completion_reason = ""
        self.elapsed_time = 0.0
        
        self.timeline_canvas.set_current_stage(stage_index)
        self._update_display()
        
        # Start animation
        if not self.animation_timer.isActive():
            self.animation_timer.start()
        
        logger.info(f"Current stage set to: {stage_index} - {stage_name}")
    
    def update_progress(self, percentage: float, status_text: str) -> None:
        """
        Update progress within the current stage.
        
        Args:
            percentage: Progress percentage (0.0 to 1.0)
            status_text: Status message (e.g., elapsed time)
        """
        self.stage_progress = max(0.0, min(1.0, percentage))
        
        # Update progress bar
        self.progress_bar.setValue(int(self.stage_progress * 100))
        
        # Update status text
        self.status_label.setText(status_text)
        
        # Update timeline canvas progress
        self.timeline_canvas.set_progress(self.stage_progress)
    
    def mark_stage_complete(self, stage_index: int, completion_reason: str) -> None:
        """
        Mark a stage as completed.
        
        Args:
            stage_index: Index of completed stage
            completion_reason: Reason for completion (e.g., "setpoint reached")
        """
        self.completed_stages.add(stage_index)
        self.completion_reason = completion_reason
        
        self.timeline_canvas.mark_stage_complete(stage_index, completion_reason)
        self._update_display()
        
        logger.info(f"Stage {stage_index} marked complete: {completion_reason}")
    
    def reset(self) -> None:
        """Reset the widget to initial state."""
        self.sequence = None
        self.current_stage_index = -1
        self.completed_stages.clear()
        self.stage_progress = 0.0
        self.completion_reason = ""
        self.elapsed_time = 0.0
        
        self.timeline_canvas.reset()
        self.animation_timer.stop()
        self._update_display()
        
        logger.info("Stage progress widget reset")
    
    def _update_display(self) -> None:
        """Update all display elements based on current state."""
        if self.sequence is None or self.current_stage_index < 0:
            # No test running
            self.stage_name_label.setText("No test running")
            self.stage_details_label.setText("")
            self.progress_bar.setValue(0)
            self.status_label.setText("")
            return
        
        # Get current stage
        if 0 <= self.current_stage_index < len(self.sequence.stages):
            stage = self.sequence.stages[self.current_stage_index]
            
            # Update stage name
            self.stage_name_label.setText(
                f"Stage {self.current_stage_index + 1}/{len(self.sequence.stages)}: {stage.name}"
            )
            
            # Update stage details
            details = []
            if stage.target_vacuum_bar is not None:
                details.append(f"Target: {stage.target_vacuum_bar:.2f} bar")
            if stage.max_time_seconds is not None:
                details.append(f"Time Limit: {stage.max_time_seconds:.0f}s")
            if stage.min_time_seconds > 0:
                details.append(f"Min Hold: {stage.min_time_seconds:.0f}s")
            
            details.append(f"Pump: {stage.pump_mode.value}")
            self.stage_details_label.setText(" | ".join(details))
        
        # Force timeline redraw
        self.timeline_canvas.update()
    
    def _update_animation(self) -> None:
        """Update animation phase for current stage indicator."""
        self.animation_phase += 0.1
        if self.animation_phase > 1.0:
            self.animation_phase = 0.0
        
        self.timeline_canvas.set_animation_phase(self.animation_phase)


class TimelineCanvas(QWidget):
    """
    Custom widget for drawing the stage timeline.
    
    Renders a horizontal timeline with stage markers showing:
    - Stage positions
    - Completion status (past/current/future)
    - Current progress
    """
    
    def __init__(self, parent=None):
        """Initialize the timeline canvas."""
        super().__init__(parent)
        
        self.sequence: Optional[TestSequence] = None
        self.current_stage_index: int = -1
        self.completed_stages: set = set()
        self.stage_progress: float = 0.0
        self.animation_phase: float = 0.0
        self.completion_reasons: dict = {}  # stage_index -> reason
        
        # Colors
        self.color_completed = QColor("#4CAF50")  # Green
        self.color_current = QColor("#2196F3")    # Blue
        self.color_pending = QColor("#9E9E9E")    # Gray
        self.color_line = QColor("#E0E0E0")       # Light gray
        
        self.setMinimumHeight(80)
    
    def set_sequence(self, sequence: TestSequence) -> None:
        """Set the sequence to display."""
        self.sequence = sequence
        self.current_stage_index = -1
        self.completed_stages.clear()
        self.stage_progress = 0.0
        self.completion_reasons.clear()
        self.update()
    
    def set_current_stage(self, stage_index: int) -> None:
        """Set the current stage index."""
        self.current_stage_index = stage_index
        self.stage_progress = 0.0
        self.update()
    
    def set_progress(self, progress: float) -> None:
        """Set progress within current stage."""
        self.stage_progress = progress
        self.update()
    
    def mark_stage_complete(self, stage_index: int, reason: str) -> None:
        """Mark a stage as completed."""
        self.completed_stages.add(stage_index)
        self.completion_reasons[stage_index] = reason
        self.update()
    
    def set_animation_phase(self, phase: float) -> None:
        """Set animation phase for current stage."""
        self.animation_phase = phase
        self.update()
    
    def reset(self) -> None:
        """Reset the timeline."""
        self.sequence = None
        self.current_stage_index = -1
        self.completed_stages.clear()
        self.stage_progress = 0.0
        self.completion_reasons.clear()
        self.update()
    
    def paintEvent(self, event) -> None:
        """Paint the timeline."""
        if self.sequence is None or len(self.sequence.stages) == 0:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Calculate layout
        width = self.width()
        height = self.height()
        margin = 40
        timeline_y = height // 2
        
        num_stages = len(self.sequence.stages)
        if num_stages == 1:
            stage_positions = [width // 2]
        else:
            stage_spacing = (width - 2 * margin) / (num_stages - 1)
            stage_positions = [margin + i * stage_spacing for i in range(num_stages)]
        
        # Draw timeline line
        pen = QPen(self.color_line, 2)
        painter.setPen(pen)
        if num_stages > 1:
            painter.drawLine(int(stage_positions[0]), timeline_y, 
                           int(stage_positions[-1]), timeline_y)
        
        # Draw stage markers
        for i, stage in enumerate(self.sequence.stages):
            x = stage_positions[i]
            
            # Determine stage state
            if i in self.completed_stages:
                color = self.color_completed
                marker_size = 12
                symbol = "✓"
            elif i == self.current_stage_index:
                # Animated current stage
                color = self.color_current
                pulse = 1.0 + 0.3 * abs(self.animation_phase - 0.5) * 2
                marker_size = int(14 * pulse)
                symbol = "⚙"
            else:
                color = self.color_pending
                marker_size = 10
                symbol = ""
            
            # Draw connecting line segment for completed stages
            if i > 0 and i - 1 in self.completed_stages:
                pen = QPen(self.color_completed, 4)
                painter.setPen(pen)
                painter.drawLine(int(stage_positions[i - 1]), timeline_y,
                               int(x), timeline_y)
            
            # Draw marker circle
            painter.setPen(QPen(color, 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(int(x - marker_size / 2), 
                              int(timeline_y - marker_size / 2),
                              marker_size, marker_size)
            
            # Draw symbol
            if symbol:
                painter.setPen(QPen(Qt.white))
                font = QFont("Arial", 10 if symbol == "✓" else 8, QFont.Bold)
                painter.setFont(font)
                painter.drawText(int(x - 6), int(timeline_y + 6), symbol)
            
            # Draw stage name below
            painter.setPen(QPen(Qt.black))
            font = QFont("Arial", 9)
            painter.setFont(font)
            text = f"{i + 1}. {stage.name}"
            text_width = painter.fontMetrics().horizontalAdvance(text)
            painter.drawText(int(x - text_width / 2), timeline_y + 25, text)
            
            # Draw completion reason if available
            if i in self.completion_reasons:
                reason = self.completion_reasons[i]
                painter.setPen(QPen(self.color_completed))
                font = QFont("Arial", 8)
                painter.setFont(font)
                reason_width = painter.fontMetrics().horizontalAdvance(reason)
                painter.drawText(int(x - reason_width / 2), timeline_y + 38, reason)
        
        # Draw progress indicator for current stage
        if 0 <= self.current_stage_index < num_stages and self.stage_progress > 0:
            x = stage_positions[self.current_stage_index]
            progress_width = 60
            progress_x = x - progress_width / 2
            progress_y = timeline_y - 30
            
            # Draw progress background
            painter.setPen(QPen(Qt.lightGray))
            painter.setBrush(QBrush(Qt.white))
            painter.drawRect(int(progress_x), int(progress_y), int(progress_width), 6)
            
            # Draw progress fill
            fill_width = progress_width * self.stage_progress
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.color_current))
            painter.drawRect(int(progress_x), int(progress_y), int(fill_width), 6)
            
            # Draw percentage
            painter.setPen(QPen(Qt.black))
            font = QFont("Arial", 8)
            painter.setFont(font)
            percent_text = f"{int(self.stage_progress * 100)}%"
            text_width = painter.fontMetrics().horizontalAdvance(percent_text)
            painter.drawText(int(x - text_width / 2), int(progress_y - 2), percent_text)

