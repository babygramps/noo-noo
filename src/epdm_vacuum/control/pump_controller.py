"""
Pump Controller - Vacuum Pump Management

Controls the vacuum pump with:
- On/off control
- Safety interlocks
- Status monitoring
"""

from typing import Optional
import logging
import time

logger = logging.getLogger(__name__)


class PumpController:
    """
    Controls the vacuum pump operation.
    
    Provides safe pump control with interlocks and status monitoring.
    """
    
    def __init__(self, widgetlords_interface=None, safety_monitor=None):
        """
        Initialize the pump controller.
        
        Args:
            widgetlords_interface: WidgetLords interface for relay control
            safety_monitor: Safety monitor for interlock checks
        """
        self.widgetlords = widgetlords_interface
        self.safety = safety_monitor
        
        self.pump_on = False
        self.pump_start_time: Optional[float] = None
        self.total_run_time = 0.0
        
        # Operating limits
        self.max_continuous_run_seconds = 3600  # 1 hour max continuous
        self.cooldown_seconds = 300  # 5 minutes cooldown after max run
        
        logger.info("PumpController initialized")
    
    def turn_on(self, force: bool = False) -> bool:
        """
        Turn on the vacuum pump.
        
        Args:
            force: If True, bypass some safety checks (use with caution)
        
        Returns:
            bool: True if pump started successfully
        """
        try:
            # Safety checks
            if not force:
                if not self._safety_checks():
                    logger.error("Safety checks failed, cannot start pump")
                    return False
            
            logger.info("Turning on vacuum pump")
            
            # Control relay via WidgetLords
            if self.widgetlords:
                success = self.widgetlords.set_relay(0, True)
                if not success:
                    logger.error("Failed to activate pump relay")
                    return False
            else:
                logger.warning("No hardware interface, pump control is simulated")
            
            self.pump_on = True
            self.pump_start_time = time.time()
            
            logger.info("Vacuum pump ON")
            return True
            
        except Exception as e:
            logger.error(f"Error turning on pump: {e}", exc_info=True)
            return False
    
    def turn_off(self) -> bool:
        """
        Turn off the vacuum pump.
        
        Returns:
            bool: True if pump stopped successfully
        """
        try:
            logger.info("Turning off vacuum pump")
            
            # Control relay via WidgetLords
            if self.widgetlords:
                success = self.widgetlords.set_relay(0, False)
                if not success:
                    logger.error("Failed to deactivate pump relay")
                    return False
            else:
                logger.warning("No hardware interface, pump control is simulated")
            
            # Update run time
            if self.pump_on and self.pump_start_time:
                run_duration = time.time() - self.pump_start_time
                self.total_run_time += run_duration
                logger.info(f"Pump ran for {run_duration:.1f} seconds")
            
            self.pump_on = False
            self.pump_start_time = None
            
            logger.info("Vacuum pump OFF")
            return True
            
        except Exception as e:
            logger.error(f"Error turning off pump: {e}", exc_info=True)
            return False
    
    def toggle(self) -> bool:
        """
        Toggle pump state.
        
        Returns:
            bool: True if toggle successful
        """
        if self.pump_on:
            return self.turn_off()
        else:
            return self.turn_on()
    
    def emergency_stop(self) -> bool:
        """
        Emergency stop of pump.
        
        Returns:
            bool: True if stopped successfully
        """
        logger.critical("EMERGENCY STOP - Shutting down pump")
        return self.turn_off()
    
    def is_running(self) -> bool:
        """
        Check if pump is currently running.
        
        Returns:
            bool: True if pump is on
        """
        return self.pump_on
    
    def get_run_time(self) -> float:
        """
        Get current continuous run time in seconds.
        
        Returns:
            float: Seconds pump has been running continuously
        """
        if self.pump_on and self.pump_start_time:
            return time.time() - self.pump_start_time
        return 0.0
    
    def get_total_run_time(self) -> float:
        """
        Get total accumulated run time.
        
        Returns:
            float: Total seconds pump has run
        """
        if self.pump_on and self.pump_start_time:
            return self.total_run_time + (time.time() - self.pump_start_time)
        return self.total_run_time
    
    def get_status(self) -> dict:
        """
        Get pump status information.
        
        Returns:
            dict: Status information
        """
        return {
            "running": self.pump_on,
            "current_run_time": self.get_run_time(),
            "total_run_time": self.get_total_run_time(),
            "max_continuous_run": self.max_continuous_run_seconds,
        }
    
    def _safety_checks(self) -> bool:
        """
        Perform safety checks before starting pump.
        
        Returns:
            bool: True if safe to start
        """
        # Check safety monitor
        if self.safety:
            if not self.safety.is_safe_to_operate():
                logger.error("Safety system indicates unsafe to operate")
                return False
        
        # Check maximum run time
        current_run = self.get_run_time()
        if current_run > self.max_continuous_run_seconds:
            logger.error(f"Pump has exceeded max continuous run time: {current_run:.0f}s")
            return False
        
        # TODO: Add more safety checks
        # - Chamber seal verification
        # - Oil level check
        # - Temperature check
        
        return True
    
    def reset_run_time(self) -> None:
        """Reset the total run time counter."""
        self.total_run_time = 0.0
        logger.info("Pump run time counter reset")

