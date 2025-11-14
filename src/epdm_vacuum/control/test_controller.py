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

from .sequence import TestSequence, TestStage, IOAction, IOActionTiming, IOActionType, PumpMode

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
        Execute a single test stage with flexible completion conditions.
        
        Stage completes when FIRST condition is met:
        - Vacuum setpoint reached (if configured)
        - Time limit exceeded (if configured)
        - Manual stop
        
        Args:
            stage: TestStage to execute
        
        Returns:
            bool: True if stage completed successfully
        """
        try:
            stage_start_time = time.time()
            stage_data = []
            
            # Execute I/O actions: BEFORE_STAGE
            self._execute_io_actions(stage, IOActionTiming.BEFORE_STAGE)
            
            # Execute I/O actions: START_OF_STAGE
            self._execute_io_actions(stage, IOActionTiming.START_OF_STAGE)
            
            # Control pump based on mode
            if stage.pump_mode == PumpMode.CONTINUOUS:
                self._update_status("Starting vacuum pump (continuous mode)...")
                self._control_pump(True)
            elif stage.pump_mode == PumpMode.MAINTAIN_VACUUM:
                self._update_status("Starting vacuum pump (maintain mode)...")
                self._control_pump(True)
            elif stage.pump_mode == PumpMode.OFF:
                self._update_status("Pump OFF mode...")
                self._control_pump(False)
            
            # Execute I/O actions: DURING_STAGE
            self._execute_io_actions(stage, IOActionTiming.DURING_STAGE)
            
            # Run stage with completion monitoring
            completion_reason = self._run_stage_with_monitoring(stage, stage_data)
            
            logger.info(f"Stage completed: {completion_reason}")
            self._update_status(f"Stage complete: {completion_reason}")
            
            # Execute I/O actions: END_OF_STAGE
            self._execute_io_actions(stage, IOActionTiming.END_OF_STAGE)
            
            # Turn off pump
            self._control_pump(False)
            
            # Execute I/O actions: AFTER_STAGE
            self._execute_io_actions(stage, IOActionTiming.AFTER_STAGE)
            
            # Store stage data
            self.stage_data.append(stage_data)
            
            stage_duration = time.time() - stage_start_time
            logger.info(f"Stage completed in {stage_duration:.1f} seconds")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing stage: {e}", exc_info=True)
            return False
    
    def _run_stage_with_monitoring(self, stage: TestStage, stage_data: List[Dict[str, Any]]) -> str:
        """
        Run stage while monitoring for completion conditions.
        
        Args:
            stage: TestStage being executed
            stage_data: List to append collected data to
        
        Returns:
            str: Reason for completion ("setpoint reached", "time limit", etc.)
        """
        stage_start = time.time()
        sample_interval = 0.1  # Check conditions every 100ms
        
        logger.info(f"Monitoring stage completion - Setpoint: {stage.target_vacuum_bar}, Time: {stage.max_time_seconds}")
        
        while self.state == TestState.RUNNING:
            elapsed = time.time() - stage_start
            
            # TODO: Read actual vacuum from sensors
            current_vacuum = 0.0  # Placeholder
            
            # Check minimum time first
            if elapsed < stage.min_time_seconds:
                time.sleep(sample_interval)
                continue
            
            # Check completion conditions (OR logic - first to complete wins)
            
            # Condition 1: Setpoint reached
            if stage.target_vacuum_bar is not None:
                # TODO: Replace with actual vacuum reading
                # For now, estimate that vacuum builds at ~0.1 bar/sec
                estimated_vacuum = min(elapsed * 0.1, stage.target_vacuum_bar)
                current_vacuum = estimated_vacuum
                
                if current_vacuum >= stage.target_vacuum_bar:
                    logger.info(f"Setpoint reached: {current_vacuum:.3f} >= {stage.target_vacuum_bar:.3f} bar")
                    return f"setpoint reached ({current_vacuum:.3f} bar)"
            
            # Condition 2: Time limit exceeded
            if stage.max_time_seconds is not None:
                if elapsed >= stage.max_time_seconds:
                    logger.info(f"Time limit reached: {elapsed:.1f}s >= {stage.max_time_seconds:.1f}s")
                    return f"time limit ({elapsed:.1f}s)"
            
            # Pump cycling for MAINTAIN_VACUUM mode
            if stage.pump_mode == PumpMode.MAINTAIN_VACUUM and stage.target_vacuum_bar is not None:
                self._maintain_vacuum_cycle(current_vacuum, stage.target_vacuum_bar, stage.vacuum_tolerance_bar)
            
            # Collect data if enabled
            if stage.collect_data and elapsed % 1.0 < sample_interval:  # Collect ~1 sample/sec
                data_point = {
                    "timestamp": time.time(),
                    "vacuum_bar": current_vacuum,
                    "elapsed": elapsed,
                }
                stage_data.append(data_point)
            
            time.sleep(sample_interval)
        
        # If we exit the loop, test was stopped manually
        return "manually stopped"
    
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
    
    def _maintain_vacuum_cycle(self, current_vacuum: float, target_vacuum: float, tolerance: float) -> None:
        """
        Cycle pump to maintain vacuum at setpoint.
        
        Args:
            current_vacuum: Current vacuum reading in bar
            target_vacuum: Target vacuum in bar
            tolerance: Acceptable tolerance in bar
        """
        # TODO: Implement actual vacuum reading and control
        # For now, this is a placeholder that would:
        # - Turn pump OFF if vacuum > (target + tolerance)
        # - Turn pump ON if vacuum < (target - tolerance)
        
        # Example logic (when hardware is connected):
        # if current_vacuum > target_vacuum + tolerance:
        #     if self.pump.is_running():
        #         logger.debug("Pump cycling OFF - vacuum above target")
        #         self._control_pump(False)
        # elif current_vacuum < target_vacuum - tolerance:
        #     if not self.pump.is_running():
        #         logger.debug("Pump cycling ON - vacuum below target")
        #         self._control_pump(True)
        
        pass  # Placeholder until hardware interface is implemented
    
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
        
        # Emergency I/O actions
        self._execute_io_emergency_stop()
        
        self._update_status("EMERGENCY STOP")
    
    def _execute_io_actions(self, stage: TestStage, timing: IOActionTiming) -> None:
        """
        Execute I/O actions for a specific timing point.
        
        Args:
            stage: TestStage containing I/O actions
            timing: IOActionTiming to execute
        """
        actions = stage.get_io_actions_for_timing(timing)
        
        if not actions:
            return
        
        logger.info(f"Executing {len(actions)} I/O actions for timing: {timing.value}")
        
        for action in actions:
            self._execute_single_io_action(action)
    
    def _execute_single_io_action(self, action: IOAction) -> None:
        """
        Execute a single I/O action.
        
        Args:
            action: IOAction to execute
        """
        try:
            # Apply delay if specified
            if action.delay_seconds > 0:
                logger.debug(f"Delaying {action.delay_seconds}s before I/O action")
                time.sleep(action.delay_seconds)
            
            logger.info(f"Executing I/O action: {action}")
            
            # Execute based on action type
            if action.action_type == IOActionType.DIGITAL_OUTPUT:
                self._set_digital_output(action.device_name, bool(action.value))
            
            elif action.action_type == IOActionType.ANALOG_OUTPUT:
                self._set_analog_output(action.device_name, float(action.value))
            
            elif action.action_type == IOActionType.PULSE:
                # Turn on
                self._set_digital_output(action.device_name, True)
                # Wait for duration
                if action.duration_seconds:
                    time.sleep(action.duration_seconds)
                # Turn off
                self._set_digital_output(action.device_name, False)
            
            logger.debug(f"I/O action completed: {action.device_name}")
            
        except Exception as e:
            logger.error(f"Error executing I/O action {action}: {e}", exc_info=True)
            # Don't fail the stage on I/O errors, just log them
    
    def _set_digital_output(self, device_name: str, state: bool) -> None:
        """
        Set a digital output (relay/valve) to ON or OFF.
        
        Args:
            device_name: Name of the device
            state: True for ON, False for OFF
        """
        logger.info(f"Setting {device_name} to {'ON' if state else 'OFF'}")
        
        # TODO: Implement actual hardware control via WidgetLords interface
        # This would map device_name to relay channel and set the state
        # Example:
        # if self.widgetlords:
        #     channel = self._get_device_channel(device_name)
        #     self.widgetlords.set_relay(channel, state)
        
        # For now, just log the action
        logger.debug(f"Digital output {device_name}: {state}")
    
    def _set_analog_output(self, device_name: str, value: float) -> None:
        """
        Set an analog output to a specific value.
        
        Args:
            device_name: Name of the device
            value: Analog value to set
        """
        logger.info(f"Setting {device_name} to {value}")
        
        # TODO: Implement actual hardware control via WidgetLords interface
        # This would map device_name to analog channel and set the value
        # Example:
        # if self.widgetlords:
        #     channel = self._get_device_channel(device_name)
        #     self.widgetlords.set_analog_output(channel, value)
        
        # For now, just log the action
        logger.debug(f"Analog output {device_name}: {value}")
    
    def _execute_io_emergency_stop(self) -> None:
        """Execute emergency I/O actions (vent valves, etc.)."""
        logger.warning("Executing emergency I/O stop procedures")
        
        # TODO: Implement emergency I/O actions
        # - Open vent valve
        # - Close inlet valve
        # - Activate safety valve
        # Example:
        # self._set_digital_output("vent_valve", True)
        # self._set_digital_output("inlet_valve", False)
        # self._set_digital_output("safety_valve", True)
        
        logger.debug("Emergency I/O actions completed")
    
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

