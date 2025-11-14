"""
Calibration Manager

Handles sensor calibration data and conversions:
- Pressure sensor calibration
- Load cell calibration
- Unit conversions
"""

from typing import Dict, Any, Optional, Tuple
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class CalibrationManager:
    """
    Manages calibration data for all sensors.
    
    Provides:
    - Loading/saving calibration data
    - Sensor value conversions
    - Calibration validation
    """
    
    def __init__(self, calibration_file: Optional[str] = None):
        """
        Initialize the calibration manager.
        
        Args:
            calibration_file: Path to calibration data file (JSON)
        """
        self.calibration_file = calibration_file
        self.calibration_data: Dict[str, Any] = {}
        
        # Default calibration parameters
        self.defaults = {
            "pressure_sensor": {
                "voltage_min": 0.0,
                "voltage_max": 10.0,
                "pressure_min_psi": 0.0,
                "pressure_max_psi": 30.0,
                "offset": 0.0,
                "scale": 1.0,
            },
            "load_cells": {
                "cell_1": {"offset": 0.0, "scale": 1.0},
                "cell_2": {"offset": 0.0, "scale": 1.0},
                "cell_3": {"offset": 0.0, "scale": 1.0},
                "cell_4": {"offset": 0.0, "scale": 1.0},
            },
        }
        
        if calibration_file:
            self.load_calibration(calibration_file)
        else:
            self.calibration_data = self.defaults.copy()
    
    def load_calibration(self, filepath: str) -> bool:
        """
        Load calibration data from JSON file.
        
        Args:
            filepath: Path to calibration file
        
        Returns:
            bool: True if loaded successfully
        """
        try:
            path = Path(filepath)
            if not path.exists():
                logger.warning(f"Calibration file not found: {filepath}, using defaults")
                self.calibration_data = self.defaults.copy()
                return False
            
            with open(path, "r") as f:
                self.calibration_data = json.load(f)
            
            logger.info(f"Loaded calibration data from {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load calibration data: {e}")
            self.calibration_data = self.defaults.copy()
            return False
    
    def save_calibration(self, filepath: Optional[str] = None) -> bool:
        """
        Save calibration data to JSON file.
        
        Args:
            filepath: Path to save file (uses self.calibration_file if None)
        
        Returns:
            bool: True if saved successfully
        """
        try:
            save_path = filepath or self.calibration_file
            if not save_path:
                raise ValueError("No filepath specified for saving calibration")
            
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w") as f:
                json.dump(self.calibration_data, f, indent=2)
            
            logger.info(f"Saved calibration data to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save calibration data: {e}")
            return False
    
    def convert_pressure_voltage(self, voltage: float) -> Tuple[float, float]:
        """
        Convert pressure sensor voltage to PSI and bar.
        
        Args:
            voltage: Raw voltage reading (0-10V)
        
        Returns:
            Tuple[float, float]: (pressure_psi, vacuum_bar)
        """
        cal = self.calibration_data.get("pressure_sensor", self.defaults["pressure_sensor"])
        
        # Apply offset and scale
        voltage_corrected = (voltage + cal["offset"]) * cal["scale"]
        
        # Linear conversion from voltage to PSI
        v_min = cal["voltage_min"]
        v_max = cal["voltage_max"]
        p_min = cal["pressure_min_psi"]
        p_max = cal["pressure_max_psi"]
        
        pressure_psi = p_min + (voltage_corrected - v_min) * (p_max - p_min) / (v_max - v_min)
        
        # Convert to vacuum (relative to atmospheric pressure)
        atmospheric_psi = 14.7
        vacuum_psi = atmospheric_psi - pressure_psi
        
        # Convert to bar (1 PSI = 0.0689476 bar)
        vacuum_bar = vacuum_psi * 0.0689476
        
        return pressure_psi, vacuum_bar
    
    def convert_load_cell(self, cell_number: int, raw_value: float) -> float:
        """
        Convert raw load cell reading to calibrated kg value.
        
        Args:
            cell_number: Load cell number (1-4)
            raw_value: Raw reading from load cell
        
        Returns:
            float: Calibrated force in kg
        """
        if not 1 <= cell_number <= 4:
            logger.error(f"Invalid load cell number: {cell_number}")
            return 0.0
        
        cell_key = f"cell_{cell_number}"
        load_cells = self.calibration_data.get("load_cells", self.defaults["load_cells"])
        cal = load_cells.get(cell_key, {"offset": 0.0, "scale": 1.0})
        
        # Apply calibration
        calibrated_value = (raw_value + cal["offset"]) * cal["scale"]
        
        return calibrated_value
    
    def set_pressure_calibration(
        self,
        voltage_min: float,
        voltage_max: float,
        pressure_min_psi: float,
        pressure_max_psi: float,
        offset: float = 0.0,
        scale: float = 1.0,
    ) -> None:
        """
        Set pressure sensor calibration parameters.
        
        Args:
            voltage_min: Minimum voltage (V)
            voltage_max: Maximum voltage (V)
            pressure_min_psi: Pressure at min voltage (PSI)
            pressure_max_psi: Pressure at max voltage (PSI)
            offset: Voltage offset correction
            scale: Voltage scale factor
        """
        self.calibration_data["pressure_sensor"] = {
            "voltage_min": voltage_min,
            "voltage_max": voltage_max,
            "pressure_min_psi": pressure_min_psi,
            "pressure_max_psi": pressure_max_psi,
            "offset": offset,
            "scale": scale,
        }
        logger.info("Updated pressure sensor calibration")
    
    def set_load_cell_calibration(
        self,
        cell_number: int,
        offset: float = 0.0,
        scale: float = 1.0,
    ) -> None:
        """
        Set load cell calibration parameters.
        
        Args:
            cell_number: Load cell number (1-4)
            offset: Zero offset correction
            scale: Scale factor
        """
        if not 1 <= cell_number <= 4:
            logger.error(f"Invalid load cell number: {cell_number}")
            return
        
        cell_key = f"cell_{cell_number}"
        if "load_cells" not in self.calibration_data:
            self.calibration_data["load_cells"] = {}
        
        self.calibration_data["load_cells"][cell_key] = {
            "offset": offset,
            "scale": scale,
        }
        logger.info(f"Updated load cell {cell_number} calibration")
    
    def get_calibration_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current calibration parameters.
        
        Returns:
            Dict[str, Any]: Calibration summary
        """
        return {
            "pressure_sensor": self.calibration_data.get(
                "pressure_sensor", self.defaults["pressure_sensor"]
            ),
            "load_cells": self.calibration_data.get(
                "load_cells", self.defaults["load_cells"]
            ),
        }

