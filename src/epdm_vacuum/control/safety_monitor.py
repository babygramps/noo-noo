"""
Safety Monitor - Safety System Management

Monitors system parameters and enforces safety limits:
- Vacuum pressure limits
- Force limits
- Emergency stop handling
- Interlock management
"""

from typing import Dict, Any, Optional, Callable
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyState(Enum):
    """Safety system states."""
    NORMAL = "normal"
    WARNING = "warning"
    ALARM = "alarm"
    EMERGENCY_STOP = "emergency_stop"


class SafetyMonitor:
    """
    Monitors system safety and enforces limits.
    
    Continuously checks sensor readings against configured limits
    and triggers appropriate responses for safety violations.
    """
    
    def __init__(self):
        """Initialize the safety monitor."""
        self.state = SafetyState.NORMAL
        
        # Default safety limits
        self.limits = {
            "max_vacuum_bar": 1.0,  # Maximum vacuum pressure
            "max_force_kg": 800.0,  # Maximum total force
            "max_single_cell_kg": 250.0,  # Maximum single load cell
            "min_vacuum_bar": 0.0,  # Minimum vacuum (atmospheric)
            "emergency_stop_active": False,
        }
        
        self.violation_counts = {
            "vacuum": 0,
            "force": 0,
            "load_cell": 0,
        }
        
        # Callbacks
        self.alarm_callback: Optional[Callable[[str], None]] = None
        self.warning_callback: Optional[Callable[[str], None]] = None
        
        logger.info("SafetyMonitor initialized")
    
    def set_limits(self, limits: Dict[str, Any]) -> None:
        """
        Set safety limits.
        
        Args:
            limits: Dictionary with limit values:
                - max_vacuum_bar
                - max_force_kg
                - max_single_cell_kg
        """
        self.limits.update(limits)
        logger.info(f"Safety limits updated: {self.limits}")
    
    def check_safety(self, sensor_data: Dict[str, Any]) -> SafetyState:
        """
        Check sensor data against safety limits.
        
        Args:
            sensor_data: Dictionary with current sensor readings
        
        Returns:
            SafetyState: Current safety state
        """
        if self.limits["emergency_stop_active"]:
            return SafetyState.EMERGENCY_STOP
        
        violations = []
        
        # Check vacuum limits
        vacuum = sensor_data.get("vacuum_bar", 0.0)
        if vacuum > self.limits["max_vacuum_bar"]:
            violations.append(f"Vacuum exceeds limit: {vacuum:.3f} > {self.limits['max_vacuum_bar']:.3f} bar")
            self.violation_counts["vacuum"] += 1
        
        # Check total force
        force = sensor_data.get("gross_weight_kg", sensor_data.get("total_force_kg", 0.0))
        if force > self.limits["max_force_kg"]:
            violations.append(f"Force exceeds limit: {force:.1f} > {self.limits['max_force_kg']:.1f} kg")
            self.violation_counts["force"] += 1
        
        # Check individual load cells
        for i in range(1, 5):
            key = f"load_cell_{i}_kg"
            cell_force = sensor_data.get(key, 0.0)
            if cell_force > self.limits["max_single_cell_kg"]:
                violations.append(
                    f"Load cell {i} exceeds limit: {cell_force:.1f} > {self.limits['max_single_cell_kg']:.1f} kg"
                )
                self.violation_counts["load_cell"] += 1
        
        # Update safety state based on violations
        if violations:
            for violation in violations:
                logger.warning(f"Safety violation: {violation}")
            
            # Trigger alarm if multiple violations or persistent violation
            if len(violations) > 1 or any(count > 3 for count in self.violation_counts.values()):
                self.state = SafetyState.ALARM
                self._trigger_alarm("; ".join(violations))
            else:
                self.state = SafetyState.WARNING
                self._trigger_warning("; ".join(violations))
        else:
            # Reset violation counts if back to normal
            if self.state != SafetyState.NORMAL:
                logger.info("Safety state returned to normal")
            self.state = SafetyState.NORMAL
            self.violation_counts = {k: 0 for k in self.violation_counts}
        
        return self.state
    
    def activate_emergency_stop(self) -> None:
        """Activate emergency stop."""
        logger.critical("EMERGENCY STOP ACTIVATED")
        self.state = SafetyState.EMERGENCY_STOP
        self.limits["emergency_stop_active"] = True
        self._trigger_alarm("Emergency stop activated")
    
    def reset_emergency_stop(self) -> bool:
        """
        Reset emergency stop.
        
        Returns:
            bool: True if reset successful
        """
        logger.info("Resetting emergency stop")
        
        # TODO: Implement checks before allowing reset
        # - Verify safe conditions
        # - Require manual confirmation
        
        self.limits["emergency_stop_active"] = False
        self.state = SafetyState.NORMAL
        self.violation_counts = {k: 0 for k in self.violation_counts}
        
        logger.info("Emergency stop reset")
        return True
    
    def is_safe_to_operate(self) -> bool:
        """
        Check if system is safe to operate.
        
        Returns:
            bool: True if safe to operate
        """
        return self.state in [SafetyState.NORMAL, SafetyState.WARNING]
    
    def get_safety_summary(self) -> Dict[str, Any]:
        """
        Get current safety status summary.
        
        Returns:
            Dict with safety state and limit information
        """
        return {
            "state": self.state.value,
            "limits": self.limits.copy(),
            "violation_counts": self.violation_counts.copy(),
            "safe_to_operate": self.is_safe_to_operate(),
        }
    
    def _trigger_alarm(self, message: str) -> None:
        """
        Trigger safety alarm.
        
        Args:
            message: Alarm message
        """
        logger.error(f"SAFETY ALARM: {message}")
        if self.alarm_callback:
            self.alarm_callback(message)
    
    def _trigger_warning(self, message: str) -> None:
        """
        Trigger safety warning.
        
        Args:
            message: Warning message
        """
        logger.warning(f"SAFETY WARNING: {message}")
        if self.warning_callback:
            self.warning_callback(message)
    
    def set_alarm_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for alarm events.
        
        Args:
            callback: Function to call with alarm messages
        """
        self.alarm_callback = callback
    
    def set_warning_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for warning events.
        
        Args:
            callback: Function to call with warning messages
        """
        self.warning_callback = callback

