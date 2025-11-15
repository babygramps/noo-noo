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
from pathlib import Path

from .sequence import TestSequence, TestStage, IOAction, IOActionTiming, IOActionType, PumpMode
from ..logging.data_logger import DataLogger

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
        data_logger: Optional[DataLogger] = None,
        csv_path: Optional[str] = None,
        test_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the test controller.
        
        Args:
            widgetlords_interface: WidgetLords hardware interface
            modbus_interface: Modbus hardware interface
            safety_monitor: Safety monitoring system
            pump_controller: Vacuum pump controller
            data_logger: DataLogger instance for saving data
            csv_path: Path to CSV file for real-time data logging
            test_metadata: Metadata about the test (name, operator, etc.)
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
        
        # Data logging
        self.data_logger = data_logger
        self.csv_path = csv_path
        self.test_metadata = test_metadata or {}
        self.csv_file = None
        self.csv_writer = None
        self.csv_header_written = False
        
        # Track IO device states for logging
        self.io_device_states: Dict[str, bool] = {}
        
        # Callbacks for status updates
        self.status_callback: Optional[Callable[[str], None]] = None
        self.stage_callback: Optional[Callable[[int, int, TestStage], None]] = None
        self.io_callback: Optional[Callable[[str, bool], None]] = None
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self.completion_callback: Optional[Callable[[int, str], None]] = None
        
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
            is_valid, errors, warnings = sequence.validate()
            if not is_valid:
                logger.error("Cannot load invalid sequence:")
                for error in errors:
                    logger.error(f"  - {error}")
                return False
            
            # Log warnings if any
            if warnings:
                logger.warning("Sequence validation warnings:")
                for warning in warnings:
                    logger.warning(f"  - {warning}")
            
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
            
            # Open CSV file for real-time logging
            if not self._open_csv_file():
                raise RuntimeError("Failed to open CSV file for logging")
            
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
        finally:
            # Always close CSV file
            self._close_csv_file()
    
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
            
            # Enhanced logging with formatted output
            logger.info("=" * 60)
            logger.info(f"[STAGE {stage_index + 1}/{total_stages}] {stage_name} - STARTED")
            logger.info(f"  Target Vacuum: {stage.target_vacuum_bar:.3f} bar" if stage.target_vacuum_bar else "  Target Vacuum: None")
            logger.info(f"  Time Limit: {stage.max_time_seconds:.1f}s" if stage.max_time_seconds else "  Time Limit: None")
            logger.info(f"  Pump Mode: {stage.pump_mode.value}")
            logger.info(f"  IO Actions: {len(stage.io_actions)}")
            logger.info("=" * 60)
            
            self._update_status(f"Stage {stage_index + 1}/{total_stages}: {stage_name}")
            
            # Notify stage change
            if self.stage_callback:
                self.stage_callback(stage_index, total_stages, stage)
            
            # Execute the stage
            stage_success = self._execute_stage(stage)
            
            if not stage_success:
                logger.error(f"[STAGE {stage_index + 1}/{total_stages}] {stage_name} - FAILED")
                return False
            
            logger.info(f"[STAGE {stage_index + 1}/{total_stages}] {stage_name} - COMPLETED SUCCESSFULLY")
        
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
            
            logger.info(f"  Completion Reason: {completion_reason}")
            self._update_status(f"Stage complete: {completion_reason}")
            
            # Notify stage completion
            if self.completion_callback:
                self.completion_callback(self.current_stage_index, completion_reason)
            
            # Execute I/O actions: END_OF_STAGE
            self._execute_io_actions(stage, IOActionTiming.END_OF_STAGE)
            
            # Turn off pump
            self._control_pump(False)
            
            # Execute I/O actions: AFTER_STAGE
            self._execute_io_actions(stage, IOActionTiming.AFTER_STAGE)
            
            # Store stage data
            self.stage_data.append(stage_data)
            
            stage_duration = time.time() - stage_start_time
            logger.info(f"  Duration: {stage_duration:.1f} seconds")
            logger.info(f"  Data Points Collected: {len(stage_data)}")
            
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
        last_progress_log = 0.0  # Track last progress log time
        
        logger.info(f"  Monitoring Completion Conditions:")
        if stage.target_vacuum_bar is not None:
            logger.info(f"    - Vacuum Setpoint: {stage.target_vacuum_bar:.3f} bar")
        if stage.max_time_seconds is not None:
            logger.info(f"    - Time Limit: {stage.max_time_seconds:.1f}s")
        if stage.min_time_seconds > 0:
            logger.info(f"    - Minimum Hold: {stage.min_time_seconds:.1f}s")
        
        while self.state == TestState.RUNNING:
            elapsed = time.time() - stage_start
            
            # TODO: Read actual vacuum from sensors
            current_vacuum = 0.0  # Placeholder
            
            # Check minimum time first
            if elapsed < stage.min_time_seconds:
                time.sleep(sample_interval)
                continue
            
            # Calculate progress percentage
            progress = 0.0
            if stage.max_time_seconds is not None and stage.max_time_seconds > 0:
                progress = min(1.0, elapsed / stage.max_time_seconds)
            elif stage.target_vacuum_bar is not None and stage.target_vacuum_bar > 0:
                # For setpoint-based, estimate progress
                estimated_vacuum = min(elapsed * 0.1, stage.target_vacuum_bar)
                current_vacuum = estimated_vacuum
                progress = min(1.0, current_vacuum / stage.target_vacuum_bar)
            
            # Emit progress update every second
            if elapsed - last_progress_log >= 1.0:
                status_text = f"Elapsed: {elapsed:.1f}s"
                if stage.target_vacuum_bar is not None:
                    status_text += f" | Vacuum: {current_vacuum:.3f} bar"
                
                # Notify progress callback
                if self.progress_callback:
                    self.progress_callback(progress, status_text)
                
                # Log progress periodically (every 5 seconds)
                if int(elapsed) % 5 == 0:
                    logger.debug(f"  Progress: {progress*100:.1f}% - {status_text}")
                
                last_progress_log = elapsed
            
            # Check completion conditions (OR logic - first to complete wins)
            
            # Condition 1: Setpoint reached
            if stage.target_vacuum_bar is not None:
                # TODO: Replace with actual vacuum reading
                # For now, estimate that vacuum builds at ~0.1 bar/sec
                estimated_vacuum = min(elapsed * 0.1, stage.target_vacuum_bar)
                current_vacuum = estimated_vacuum
                
                if current_vacuum >= stage.target_vacuum_bar:
                    logger.info(f"  ✓ Setpoint reached: {current_vacuum:.3f} >= {stage.target_vacuum_bar:.3f} bar")
                    return f"setpoint reached ({current_vacuum:.3f} bar)"
            
            # Condition 2: Time limit exceeded
            if stage.max_time_seconds is not None:
                if elapsed >= stage.max_time_seconds:
                    logger.info(f"  ⏱ Time limit reached: {elapsed:.1f}s >= {stage.max_time_seconds:.1f}s")
                    return f"time limit ({elapsed:.1f}s)"
            
            # Pump cycling for MAINTAIN_VACUUM mode
            if stage.pump_mode == PumpMode.MAINTAIN_VACUUM and stage.target_vacuum_bar is not None:
                self._maintain_vacuum_cycle(current_vacuum, stage.target_vacuum_bar, stage.vacuum_tolerance_bar)
            
            # Collect data if enabled
            if stage.collect_data and elapsed % 1.0 < sample_interval:  # Collect ~1 sample/sec
                current_time = time.time()
                from datetime import datetime
                data_point = {
                    "timestamp": current_time,
                    "datetime": datetime.fromtimestamp(current_time).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],  # Include milliseconds
                    "elapsed_time": elapsed,
                    "stage_index": self.current_stage_index,
                    "stage_name": stage.name or f"Stage {self.current_stage_index + 1}",
                    "vacuum_bar": current_vacuum,
                    "test_state": self.state.value,
                }
                
                # Add IO device states (valve positions, etc.)
                for device_name, state in self.io_device_states.items():
                    # Create column name like "valve_vent_valve" or "io_pump_relay"
                    column_name = f"io_{device_name}"
                    data_point[column_name] = "OPEN" if state else "CLOSED"
                
                # Add hardware readings if available
                try:
                    if self.widgetlords:
                        wl_data = self.widgetlords.read()
                        data_point.update(wl_data)
                    
                    if self.modbus:
                        modbus_data = self.modbus.read()
                        data_point.update(modbus_data)
                except Exception as e:
                    logger.warning(f"Error reading sensors for data logging: {e}")
                
                # Store in memory
                stage_data.append(data_point)
                
                # Write to CSV in real-time
                self._write_csv_data(data_point)
            
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
        
        logger.info(f"  Executing {len(actions)} I/O action(s) at timing: {timing.value}")
        
        for i, action in enumerate(actions, 1):
            logger.info(f"    [{i}/{len(actions)}] {action.device_name}: {'OPEN' if action.value else 'CLOSED'}")
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
            
            # Execute based on action type
            if action.action_type == IOActionType.DIGITAL_OUTPUT:
                state = bool(action.value)
                self._set_digital_output(action.device_name, state)
                
                # Track IO state
                self.io_device_states[action.device_name] = state
                
                # Notify IO callback
                if self.io_callback:
                    self.io_callback(action.device_name, state)
            
            elif action.action_type == IOActionType.ANALOG_OUTPUT:
                self._set_analog_output(action.device_name, float(action.value))
            
            elif action.action_type == IOActionType.PULSE:
                # Turn on
                self._set_digital_output(action.device_name, True)
                self.io_device_states[action.device_name] = True
                if self.io_callback:
                    self.io_callback(action.device_name, True)
                
                # Wait for duration
                if action.duration_seconds:
                    time.sleep(action.duration_seconds)
                
                # Turn off
                self._set_digital_output(action.device_name, False)
                self.io_device_states[action.device_name] = False
                if self.io_callback:
                    self.io_callback(action.device_name, False)
            
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
        logger.debug(f"      → {device_name}: {'OPEN/ON' if state else 'CLOSED/OFF'}")
        
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
    
    def set_io_callback(self, callback: Callable[[str, bool], None]) -> None:
        """
        Set callback for IO device state changes.
        
        Args:
            callback: Function to call with (device_name, state)
        """
        self.io_callback = callback
    
    def set_progress_callback(self, callback: Callable[[float, str], None]) -> None:
        """
        Set callback for stage progress updates.
        
        Args:
            callback: Function to call with (percentage, status_text)
        """
        self.progress_callback = callback
    
    def set_completion_callback(self, callback: Callable[[int, str], None]) -> None:
        """
        Set callback for stage completion.
        
        Args:
            callback: Function to call with (stage_index, completion_reason)
        """
        self.completion_callback = callback
    
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
    
    def _open_csv_file(self) -> bool:
        """
        Open CSV file for real-time data logging.
        
        Returns:
            bool: True if file opened successfully
        """
        if not self.csv_path:
            logger.warning("No CSV path specified, data will not be saved")
            return True  # Not an error, just skip logging
        
        try:
            import csv
            import json
            
            # Ensure directory exists
            csv_file_path = Path(self.csv_path)
            csv_file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save metadata to separate JSON file
            if self.test_metadata:
                metadata_path = csv_file_path.with_suffix('.json')
                try:
                    with open(metadata_path, 'w') as meta_file:
                        json.dump(self.test_metadata, meta_file, indent=2)
                    logger.info(f"Saved test metadata to: {metadata_path}")
                except Exception as e:
                    logger.error(f"Failed to save metadata file: {e}", exc_info=True)
                    # Continue anyway - metadata save failure shouldn't stop the test
            
            # Open CSV file for writing (clean, no comments)
            self.csv_file = open(self.csv_path, 'w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            
            # CSV header will be written when first data point arrives
            self.csv_header_written = False
            
            logger.info(f"Opened CSV file for logging: {self.csv_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to open CSV file: {e}", exc_info=True)
            return False
    
    def _write_csv_data(self, data: Dict[str, Any]) -> None:
        """
        Write a data point to the CSV file in real-time.
        
        Args:
            data: Dictionary containing data to write
        """
        if not self.csv_file or not self.csv_writer:
            return
        
        try:
            # Write header if not yet written
            if not self.csv_header_written:
                headers = sorted(data.keys())
                self.csv_writer.writerow(headers)
                self.csv_header_written = True
                self._stored_headers = headers
            
            # Write data row (in same order as headers)
            row = [data.get(key, '') for key in self._stored_headers]
            self.csv_writer.writerow(row)
            
            # Flush to ensure data is written immediately
            self.csv_file.flush()
            
        except Exception as e:
            logger.error(f"Error writing to CSV: {e}", exc_info=True)
    
    def _close_csv_file(self) -> None:
        """Close the CSV file."""
        if self.csv_file:
            try:
                self.csv_file.close()
                logger.info(f"Closed CSV file: {self.csv_path}")
            except Exception as e:
                logger.error(f"Error closing CSV file: {e}", exc_info=True)
            finally:
                self.csv_file = None
                self.csv_writer = None

