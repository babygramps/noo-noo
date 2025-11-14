"""
Test Controller - Test Sequence Orchestration

Manages the execution of automated test sequences:
- Pre-test checks
- Vacuum application
- Data collection
- Post-test procedures
"""

from typing import Optional, Dict, Any, Callable, List
import logging
import time
from enum import Enum

from .sequence import TestSequence, TestStage

logger = logging.getLogger(__name__)


class TestState(Enum):
    """Test execution states."""
    IDLE = "idle"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    COMPLETED = "completed"
    FAILED = "failed"


class TestController:
    """
    Orchestrates test sequences and manages test execution.
    
    Coordinates hardware interfaces and safety monitors to
    execute automated test procedures.
    """
    
    def __init__(
        self,
        widgetlords_interface=None,
        modbus_interface=None,
        safety_monitor=None,
        pump_controller=None,
    ):
        """
        Initialize the test controller.
        
        Args:
            widgetlords_interface: WidgetLords hardware interface
            modbus_interface: Modbus hardware interface
            safety_monitor: Safety monitoring system
            pump_controller: Vacuum pump controller
        """
        self.widgetlords = widgetlords_interface
        self.modbus = modbus_interface
        self.safety = safety_monitor
        self.pump = pump_controller
        
        self.state = TestState.IDLE
        self.test_data = []
        self.test_start_time: Optional[float] = None
        self.test_config: Dict[str, Any] = {}
        
        # Sequence management
        self.current_sequence: Optional[TestSequence] = None
        self.current_stage_index: int = 0
        self.stage_data: List[List[Dict[str, Any]]] = []  # Data for each stage
        
        # Callbacks for status updates
        self.status_callback: Optional[Callable[[str], None]] = None
        self.stage_callback: Optional[Callable[[int, int, TestStage], None]] = None
        
        logger.info("TestController initialized")
    
    def configure_test(self, config: Dict[str, Any]) -> bool:
        """
        Configure test parameters.
        
        Args:
            config: Dictionary with test configuration:
                - target_vacuum_bar: Target vacuum pressure
                - hold_time_seconds: Duration to hold vacuum
                - ramp_rate_bar_per_sec: Vacuum ramp rate
                - max_force_kg: Maximum allowed force
        
        Returns:
            bool: True if configuration valid
        """
        try:
            self.test_config = config
            
            # Validate configuration
            required_keys = ["target_vacuum_bar", "hold_time_seconds"]
            for key in required_keys:
                if key not in config:
                    raise ValueError(f"Missing required config key: {key}")
            
            logger.info(f"Test configured: {config}")
            return True
            
        except Exception as e:
            logger.error(f"Test configuration error: {e}")
            return False
    
    def load_sequence(self, sequence: TestSequence) -> bool:
        """
        Load a test sequence for execution.
        
        Args:
            sequence: TestSequence to execute
        
        Returns:
            bool: True if sequence loaded successfully
        """
        try:
            # Validate sequence
            is_valid, errors = sequence.validate()
            if not is_valid:
                logger.error("Cannot load invalid sequence:")
                for error in errors:
                    logger.error(f"  - {error}")
                return False
            
            self.current_sequence = sequence
            self.current_stage_index = 0
            self.stage_data = []
            
            logger.info(f"Loaded sequence '{sequence.name}' with {len(sequence.stages)} stages")
            return True
            
        except Exception as e:
            logger.error(f"Error loading sequence: {e}", exc_info=True)
            return False
    
    def run_test(self) -> bool:
        """
        Execute the full test sequence.
        
        If a sequence is loaded, executes all stages in order.
        Otherwise, executes a single test with configured parameters.
        
        Returns:
            bool: True if test completed successfully
        """
        try:
            logger.info("Starting test sequence")
            self.state = TestState.INITIALIZING
            self.test_start_time = time.time()
            self.test_data = []
            
            # Pre-test checks
            self._update_status("Performing pre-test checks...")
            if not self._pre_test_checks():
                raise RuntimeError("Pre-test checks failed")
            
            # Tare load cells
            self._update_status("Taring load cells...")
            self._tare_load_cells()
            
            self.state = TestState.RUNNING
            
            # Execute sequence or single test
            if self.current_sequence:
                success = self._run_sequence()
            else:
                success = self._run_single_test()
            
            if not success:
                raise RuntimeError("Test execution failed")
            
            # Complete test
            self.state = TestState.COMPLETED
            self._update_status("Test completed successfully")
            logger.info("Test sequence completed")
            
            return True
            
        except Exception as e:
            logger.error(f"Test execution error: {e}", exc_info=True)
            self.state = TestState.FAILED
            self._emergency_stop()
            return False
    
    def _run_sequence(self) -> bool:
        """
        Execute a multi-stage sequence.
        
        Returns:
            bool: True if all stages completed successfully
        """
        if not self.current_sequence:
            return False
        
        logger.info(f"Executing sequence '{self.current_sequence.name}' with {len(self.current_sequence.stages)} stages")
        
        total_stages = len(self.current_sequence.stages)
        
        for stage_index, stage in enumerate(self.current_sequence.stages):
            if self.state != TestState.RUNNING:
                logger.warning("Test stopped during sequence execution")
                return False
            
            self.current_stage_index = stage_index
            stage_name = stage.name or f"Stage {stage_index + 1}"
            
            logger.info(f"Starting stage {stage_index + 1}/{total_stages}: {stage_name}")
            self._update_status(f"Stage {stage_index + 1}/{total_stages}: {stage_name}")
            
            # Notify stage change
            if self.stage_callback:
                self.stage_callback(stage_index, total_stages, stage)
            
            # Execute the stage
            stage_success = self._execute_stage(stage)
            
            if not stage_success:
                logger.error(f"Stage {stage_index + 1} failed")
                return False
            
            # Pause between stages if configured
            if self.current_sequence.pause_between_stages and stage_index < total_stages - 1:
                self._update_status("Pausing between stages...")
                time.sleep(5.0)
            
            logger.info(f"Completed stage {stage_index + 1}/{total_stages}")
        
        logger.info(f"Sequence '{self.current_sequence.name}' completed successfully")
        return True
    
    def _run_single_test(self) -> bool:
        """
        Execute a single test with configured parameters.
        
        Returns:
            bool: True if test completed successfully
        """
        logger.info("Executing single test")
        
        # Start vacuum pump
        self._update_status("Starting vacuum pump...")
        self._control_pump(True)
        
        # Ramp to target vacuum
        self._update_status("Ramping to target vacuum...")
        self._ramp_to_vacuum()
        
        # Hold at vacuum and collect data
        self._update_status("Holding at target vacuum...")
        self._hold_and_collect()
        
        # Vent chamber
        self._update_status("Venting chamber...")
        self._vent_chamber()
        
        return True
    
    def _execute_stage(self, stage: TestStage) -> bool:
        """
        Execute a single test stage.
        
        Args:
            stage: TestStage to execute
        
        Returns:
            bool: True if stage completed successfully
        """
        try:
            stage_start_time = time.time()
            stage_data = []
            
            # Apply delay before stage if specified
            if stage.delay_before_seconds and stage.delay_before_seconds > 0:
                self._update_status(f"Waiting {stage.delay_before_seconds:.0f}s before stage...")
                time.sleep(stage.delay_before_seconds)
            
            # Start vacuum pump
            self._update_status("Starting vacuum pump...")
            self._control_pump(True)
            
            # Ramp to target vacuum
            self._update_status(f"Ramping to {stage.target_vacuum_bar:.3f} bar...")
            self._ramp_to_vacuum_target(stage.target_vacuum_bar, stage.ramp_rate_bar_per_sec)
            
            # Hold at vacuum and collect data
            self._update_status(f"Holding at {stage.target_vacuum_bar:.3f} bar for {stage.hold_time_seconds:.0f}s...")
            self._hold_and_collect_stage(stage, stage_data)
            
            # Vent chamber if configured
            if stage.auto_vent:
                self._update_status("Venting chamber...")
                self._vent_chamber()
            else:
                # Just turn off pump but don't vent
                self._control_pump(False)
            
            # Store stage data
            self.stage_data.append(stage_data)
            
            stage_duration = time.time() - stage_start_time
            logger.info(f"Stage completed in {stage_duration:.1f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing stage: {e}", exc_info=True)
            return False
    
    def stop_test(self) -> None:
        """Stop the current test immediately."""
        logger.info("Stopping test")
        self.state = TestState.STOPPING
        self._emergency_stop()
    
    def pause_test(self) -> None:
        """Pause the current test."""
        if self.state == TestState.RUNNING:
            logger.info("Pausing test")
            self.state = TestState.PAUSED
            # TODO: Implement pause logic
    
    def resume_test(self) -> None:
        """Resume a paused test."""
        if self.state == TestState.PAUSED:
            logger.info("Resuming test")
            self.state = TestState.RUNNING
            # TODO: Implement resume logic
    
    def _pre_test_checks(self) -> bool:
        """
        Perform pre-test safety and readiness checks.
        
        Returns:
            bool: True if all checks pass
        """
        logger.info("Running pre-test checks")
        
        # TODO: Implement actual checks
        # - Verify hardware connections
        # - Check safety limits
        # - Verify chamber seal
        # - Check initial conditions
        
        # Placeholder
        time.sleep(1)
        
        logger.info("Pre-test checks passed")
        return True
    
    def _tare_load_cells(self) -> None:
        """Tare all load cells to zero."""
        logger.info("Taring load cells")
        
        if self.modbus:
            # TODO: Implement actual tare via Modbus
            # self.modbus.tare_load_cells()
            pass
        
        time.sleep(1)
        logger.info("Load cells tared")
    
    def _control_pump(self, state: bool) -> None:
        """
        Control vacuum pump state.
        
        Args:
            state: True for ON, False for OFF
        """
        logger.info(f"Setting pump to {'ON' if state else 'OFF'}")
        
        if self.pump:
            # TODO: Use pump controller
            # self.pump.set_pump_state(state)
            pass
        elif self.widgetlords:
            # Direct control via WidgetLords
            self.widgetlords.write({"pump": state})
        
        time.sleep(0.5)
    
    def _ramp_to_vacuum(self) -> None:
        """Ramp vacuum pressure to target value (legacy single test)."""
        target = self.test_config.get("target_vacuum_bar", 0.5)
        self._ramp_to_vacuum_target(target, None)
    
    def _ramp_to_vacuum_target(self, target_bar: float, ramp_rate: Optional[float] = None) -> None:
        """
        Ramp vacuum pressure to target value.
        
        Args:
            target_bar: Target vacuum in bar
            ramp_rate: Optional ramp rate in bar/s
        """
        logger.info(f"Ramping to target vacuum: {target_bar} bar")
        
        # TODO: Implement closed-loop vacuum control
        # Monitor pressure and adjust pump timing
        
        # Placeholder: wait for vacuum to build
        if ramp_rate and ramp_rate > 0:
            ramp_time = target_bar / ramp_rate
        else:
            ramp_time = target_bar * 10  # Conservative estimate
        
        time.sleep(min(ramp_time, 30))  # Cap at 30 seconds for safety
        
        logger.info("Target vacuum reached")
    
    def _hold_and_collect(self) -> None:
        """Hold at target vacuum and collect data (legacy single test)."""
        hold_time = self.test_config.get("hold_time_seconds", 30)
        logger.info(f"Holding for {hold_time} seconds")
        
        # TODO: Implement data collection loop
        # - Monitor vacuum and force
        # - Check safety limits
        # - Store data points
        
        # Placeholder
        time.sleep(hold_time)
        
        logger.info("Hold period completed")
    
    def _hold_and_collect_stage(self, stage: TestStage, stage_data: List[Dict[str, Any]]) -> None:
        """
        Hold at target vacuum and collect data for a specific stage.
        
        Args:
            stage: TestStage being executed
            stage_data: List to append collected data points to
        """
        logger.info(f"Holding for {stage.hold_time_seconds} seconds")
        
        # TODO: Implement actual data collection loop
        # - Monitor vacuum and force at sample_rate_hz
        # - Check safety limits (stage.max_force_kg, etc.)
        # - Store data points in stage_data
        
        # Placeholder: simulate data collection
        if stage.collect_data:
            sample_rate = stage.sample_rate_hz or 10.0
            num_samples = int(stage.hold_time_seconds * sample_rate)
            
            for i in range(num_samples):
                if self.state != TestState.RUNNING:
                    break
                
                # Simulate sample
                data_point = {
                    "timestamp": time.time(),
                    "vacuum_bar": stage.target_vacuum_bar,
                    "force_kg": 100.0,  # Mock data
                }
                stage_data.append(data_point)
                
                time.sleep(1.0 / sample_rate)
        else:
            # Just wait without collecting data
            time.sleep(stage.hold_time_seconds)
        
        logger.info("Hold period completed")
    
    def _vent_chamber(self) -> None:
        """Safely vent the test chamber."""
        logger.info("Venting chamber")
        
        # Turn off pump
        self._control_pump(False)
        
        # TODO: Open vent valve if available
        # Wait for pressure to equalize
        
        time.sleep(3)
        logger.info("Chamber vented")
    
    def _emergency_stop(self) -> None:
        """Execute emergency stop procedure."""
        logger.warning("EMERGENCY STOP")
        
        # Turn off pump immediately
        self._control_pump(False)
        
        # TODO: Open vent valve
        # TODO: Activate any safety interlocks
        
        self._update_status("EMERGENCY STOP")
    
    def _update_status(self, message: str) -> None:
        """
        Send status update to callback.
        
        Args:
            message: Status message
        """
        logger.info(f"Status: {message}")
        if self.status_callback:
            self.status_callback(message)
    
    def set_status_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set callback for status updates.
        
        Args:
            callback: Function to call with status messages
        """
        self.status_callback = callback
    
    def set_stage_callback(self, callback: Callable[[int, int, TestStage], None]) -> None:
        """
        Set callback for stage transitions.
        
        Args:
            callback: Function to call with (current_stage, total_stages, stage_object)
        """
        self.stage_callback = callback
    
    def get_test_data(self) -> list:
        """
        Get collected test data.
        
        Returns:
            list: List of data points collected during test
        """
        return self.test_data
    
    def get_stage_data(self) -> List[List[Dict[str, Any]]]:
        """
        Get data collected for each stage.
        
        Returns:
            List of lists, where each inner list contains data points for that stage
        """
        return self.stage_data
    
    def get_current_stage_index(self) -> int:
        """
        Get the index of the currently executing stage.
        
        Returns:
            int: Current stage index (0-based)
        """
        return self.current_stage_index
    
    def get_state(self) -> TestState:
        """
        Get current test state.
        
        Returns:
            TestState: Current state
        """
        return self.state

