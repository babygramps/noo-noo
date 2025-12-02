"""
Plot Widget - Real-time Data Visualization

Provides live plotting of sensor data using pyqtgraph:
- Force vs. Time
- Vacuum vs. Time
- Optional: Force vs. Vacuum
"""

from typing import Dict, Any, List
import logging
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from PyQt5.QtCore import Qt

logger = logging.getLogger(__name__)


class PlotWidget(QWidget):
    """
    Widget for real-time data plotting.
    
    Displays multiple plots in tabs:
    - Force vs. Time
    - Vacuum vs. Time
    - Force vs. Vacuum
    """
    
    def __init__(self, buffer_size: int = 1000):
        """
        Initialize the plot widget.
        
        Args:
            buffer_size: Maximum number of data points to keep in memory
        """
        super().__init__()
        
        self.buffer_size = buffer_size
        
        # Data buffers
        self.time_buffer = deque(maxlen=buffer_size)
        self.force_buffer = deque(maxlen=buffer_size)
        self.vacuum_buffer = deque(maxlen=buffer_size)
        
        self.start_time = None
        
        self.init_ui()
        logger.info("PlotWidget initialized")
    
    def init_ui(self) -> None:
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        
        # Create tab widget for multiple plots
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Create individual plot tabs
        self.create_force_time_plot()
        self.create_vacuum_time_plot()
        self.create_force_vacuum_plot()
        
        # Configure pyqtgraph
        pg.setConfigOptions(antialias=True)
    
    def create_force_time_plot(self) -> None:
        """Create Force vs. Time plot."""
        plot_widget = pg.PlotWidget()
        plot_widget.setTitle("Force vs. Time")
        plot_widget.setLabel("left", "Force (kg)")
        plot_widget.setLabel("bottom", "Time (s)")
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setBackground("w")
        
        # Create plot curve
        pen = pg.mkPen(color=(0, 0, 255), width=2)
        self.force_curve = plot_widget.plot([], [], pen=pen, name="Force")
        
        # Add legend
        plot_widget.addLegend()
        
        self.tab_widget.addTab(plot_widget, "Force vs. Time")
        self.force_plot = plot_widget
    
    def create_vacuum_time_plot(self) -> None:
        """Create Vacuum vs. Time plot."""
        plot_widget = pg.PlotWidget()
        plot_widget.setTitle("Vacuum vs. Time")
        plot_widget.setLabel("left", "Vacuum (bar)")
        plot_widget.setLabel("bottom", "Time (s)")
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setBackground("w")
        
        # Create plot curve
        pen = pg.mkPen(color=(255, 0, 0), width=2)
        self.vacuum_curve = plot_widget.plot([], [], pen=pen, name="Vacuum")
        
        # Add legend
        plot_widget.addLegend()
        
        self.tab_widget.addTab(plot_widget, "Vacuum vs. Time")
        self.vacuum_plot = plot_widget
    
    def create_force_vacuum_plot(self) -> None:
        """Create Force vs. Vacuum plot."""
        plot_widget = pg.PlotWidget()
        plot_widget.setTitle("Force vs. Vacuum")
        plot_widget.setLabel("left", "Force (kg)")
        plot_widget.setLabel("bottom", "Vacuum (bar)")
        plot_widget.showGrid(x=True, y=True)
        plot_widget.setBackground("w")
        
        # Create scatter plot
        self.force_vacuum_scatter = pg.ScatterPlotItem(
            size=5, pen=pg.mkPen(None), brush=pg.mkBrush(0, 128, 0, 120)
        )
        plot_widget.addItem(self.force_vacuum_scatter)
        
        self.tab_widget.addTab(plot_widget, "Force vs. Vacuum")
        self.force_vacuum_plot = plot_widget
    
    def add_data_point(self, data: Dict[str, Any]) -> None:
        """
        Add new data point and update plots.
        
        Args:
            data: Dictionary containing sensor readings with 'timestamp' key
        """
        if "timestamp" not in data:
            logger.warning("Data point missing timestamp, skipping")
            return
        
        # Initialize start time on first data point
        if self.start_time is None:
            self.start_time = data["timestamp"]
        
        # Calculate relative time
        relative_time = data["timestamp"] - self.start_time
        
        # Extract force value - use sum of software-tared individual load cells
        # (same calculation as DisplayWidget) for consistency
        force = 0.0
        has_load_cells = False
        for i in range(4):
            key = f"load_cell_{i+1}_kg"
            if key in data:
                force += data[key]
                has_load_cells = True
        
        # Fall back to gross/total if no individual load cells available
        if not has_load_cells:
            force = data.get("total_force_kg", data.get("gross_weight_kg", 0.0))
        
        vacuum = data.get("vacuum_bar", 0.0)
        
        # Add to buffers
        self.time_buffer.append(relative_time)
        self.force_buffer.append(force)
        self.vacuum_buffer.append(vacuum)
        
        # Update plots
        self.update_plots()
    
    def update_plots(self) -> None:
        """Update all plots with current buffer data."""
        if len(self.time_buffer) == 0:
            return
        
        # Convert buffers to numpy arrays for plotting
        time_array = np.array(self.time_buffer)
        force_array = np.array(self.force_buffer)
        vacuum_array = np.array(self.vacuum_buffer)
        
        # Update Force vs. Time
        self.force_curve.setData(time_array, force_array)
        
        # Update Vacuum vs. Time
        self.vacuum_curve.setData(time_array, vacuum_array)
        
        # Update Force vs. Vacuum (scatter plot)
        points = [{"pos": (v, f)} for v, f in zip(vacuum_array, force_array)]
        self.force_vacuum_scatter.setData(vacuum_array, force_array)
    
    def clear_data(self) -> None:
        """Clear all data buffers and plots."""
        self.time_buffer.clear()
        self.force_buffer.clear()
        self.vacuum_buffer.clear()
        self.start_time = None
        
        self.force_curve.setData([], [])
        self.vacuum_curve.setData([], [])
        self.force_vacuum_scatter.setData([], [])
        
        logger.info("Plot data cleared")
    
    def export_data(self) -> Dict[str, List[float]]:
        """
        Export current plot data.
        
        Returns:
            Dict with time, force, and vacuum arrays
        """
        return {
            "time": list(self.time_buffer),
            "force": list(self.force_buffer),
            "vacuum": list(self.vacuum_buffer),
        }

