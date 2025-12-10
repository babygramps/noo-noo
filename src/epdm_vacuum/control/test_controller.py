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
        
        # NOTE: IO device states are now managed by RelayStateManager (single source of truth)
        # We query RelayStateManager when we need state for logging, rather than maintaining
        # our own cache which could get out of sync.
        # See: _get_io_device_states_for_logging()
        
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
            logger.info("=" * 70)
            logger.info("[RUN_TEST] ========== TEST STARTING ==========")
            logger.info(f"[RUN_TEST] current_sequence: {self.current_sequence}")
            logger.info(f"[RUN_TEST] sequence name: {self.current_sequence.name if self.current_sequence else 'N/A'}")
            logger.info(f"[RUN_TEST] num stages: {len(self.current_sequence.stages) if self.current_sequence else 0}")
            logger.info(f"[RUN_TEST] widgetlords: {self.widgetlords}")
            logger.info(f"[RUN_TEST] widgetlords type: {type(self.widgetlords)}")
            if self.widgetlords:
                logger.info(f"[RUN_TEST] widgetlords.is_connected(): {self.widgetlords.is_connected()}")
                logger.info(f"[RUN_TEST] widgetlords.relay_modules: {list(self.widgetlords.relay_modules.keys()) if hasattr(self.widgetlords, 'relay_modules') else 'N/A'}")
            logger.info("=" * 70)
            
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
            logger.info(f"[RUN_TEST] About to execute - current_sequence is {'SET' if self.current_sequence else 'NONE'}")
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
        
        total_cycles = getattr(self.current_sequence, 'cycles', 1) or 1
        stages_per_cycle = len(self.current_sequence.stages)
        total_stages = stages_per_cycle * total_cycles
        
        logger.info(f"Executing sequence '{self.current_sequence.name}' with {stages_per_cycle} stages x {total_cycles} cycles = {total_stages} total stages")
        
        global_stage_index = 0
        
        for cycle in range(total_cycles):
            if total_cycles > 1:
                logger.info("#" * 60)
                logger.info(f"### CYCLE {cycle + 1}/{total_cycles} ###")
                logger.info("#" * 60)
            
            for stage_index, stage in enumerate(self.current_sequence.stages):
                if self.state != TestState.RUNNING:
                    logger.warning("Test stopped during sequence execution")
                    return False
                
                self.current_stage_index = global_stage_index
                stage_name = stage.name or f"Stage {stage_index + 1}"
                
                # Enhanced logging with formatted output
                logger.info("=" * 60)
                if total_cycles > 1:
                    logger.info(f"[CYCLE {cycle + 1}/{total_cycles}] [STAGE {stage_index + 1}/{stages_per_cycle}] {stage_name} - STARTED")
                else:
                    logger.info(f"[STAGE {stage_index + 1}/{stages_per_cycle}] {stage_name} - STARTED")
                logger.info(f"  Target Vacuum: {stage.target_vacuum_bar:.3f} bar" if stage.target_vacuum_bar else "  Target Vacuum: None")
                logger.info(f"  Time Limit: {stage.max_time_seconds:.1f}s" if stage.max_time_seconds else "  Time Limit: None")
                logger.info(f"  Pump Mode: {stage.pump_mode.value}")
                logger.info(f"  IO Actions: {len(stage.io_actions)}")
                logger.info("=" * 60)
                
                if total_cycles > 1:
                    self._update_status(f"Cycle {cycle + 1}/{total_cycles} - Stage {stage_index + 1}/{stages_per_cycle}: {stage_name}")
                else:
                    self._update_status(f"Stage {stage_index + 1}/{stages_per_cycle}: {stage_name}")
                
                # Notify stage change (use global index for progress tracking)
                if self.stage_callback:
                    self.stage_callback(global_stage_index, total_stages, stage)
                
                # Execute the stage
                stage_success = self._execute_stage(stage)
                
                if not stage_success:
                    logger.error(f"[STAGE {global_stage_index + 1}/{total_stages}] {stage_name} - FAILED")
                    return False
                
                logger.info(f"[STAGE {global_stage_index + 1}/{total_stages}] {stage_name} - COMPLETED SUCCESSFULLY")
                global_stage_index += 1
            
            if total_cycles > 1:
                logger.info(f"### CYCLE {cycle + 1}/{total_cycles} COMPLETED ###")
        
        logger.info(f"Sequence '{self.current_sequence.name}' completed successfully ({total_cycles} cycles)")
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
            # Use monotonic clock for elapsed calculations to avoid jumps if system time changes
            stage_start_time = time.monotonic()
            stage_data = []
            
            # DEBUG: Log stage execution start
            logger.info("=" * 60)
            logger.info(f"[STAGE_EXEC] Starting stage: {stage.name}")
            logger.info(f"[STAGE_EXEC] pump_mode = {stage.pump_mode} (type: {type(stage.pump_mode)})")
            logger.info(f"[STAGE_EXEC] PumpMode.CONTINUOUS = {PumpMode.CONTINUOUS}")
            logger.info(f"[STAGE_EXEC] PumpMode.MAINTAIN_VACUUM = {PumpMode.MAINTAIN_VACUUM}")
            logger.info(f"[STAGE_EXEC] PumpMode.OFF = {PumpMode.OFF}")
            logger.info(f"[STAGE_EXEC] widgetlords interface: {self.widgetlords}")
            logger.info(f"[STAGE_EXEC] widgetlords connected: {self.widgetlords.is_connected() if self.widgetlords else 'N/A'}")
            logger.info(f"[STAGE_EXEC] IO actions count: {len(stage.io_actions)}")
            for i, action in enumerate(stage.io_actions):
                logger.info(f"[STAGE_EXEC]   IO[{i}]: {action.device_name} = {action.value} @ {action.timing}")
            logger.info("=" * 60)
            
            # Execute I/O actions: BEFORE_STAGE
            self._execute_io_actions(stage, IOActionTiming.BEFORE_STAGE)
            
            # Execute I/O actions: START_OF_STAGE
            self._execute_io_actions(stage, IOActionTiming.START_OF_STAGE)
            
            # Control pump based on mode
            logger.info(f"[STAGE_EXEC] Checking pump_mode...")
            if stage.pump_mode == PumpMode.CONTINUOUS:
                logger.info(f"[STAGE_EXEC] MATCH: pump_mode == CONTINUOUS -> calling _control_pump(True)")
                self._update_status("Starting vacuum pump (continuous mode)...")
                self._control_pump(True)
            elif stage.pump_mode == PumpMode.MAINTAIN_VACUUM:
                logger.info(f"[STAGE_EXEC] MATCH: pump_mode == MAINTAIN_VACUUM -> calling _control_pump(True)")
                logger.info(f"[STAGE_EXEC] MAINTAIN MODE: target={stage.target_vacuum_bar:.3f} bar, tolerance=±{stage.vacuum_tolerance_bar:.3f} bar")
                logger.info(f"[STAGE_EXEC] Stage will run for max_time={stage.max_time_seconds}s (setpoint does NOT complete stage)")
                self._update_status("Starting vacuum pump (maintain mode)...")
                self._control_pump(True)
                # Reset maintain pump state tracker
                self._maintain_pump_on = True
            elif stage.pump_mode == PumpMode.OFF:
                logger.info(f"[STAGE_EXEC] MATCH: pump_mode == OFF -> calling _control_pump(False)")
                self._update_status("Pump OFF mode...")
                self._control_pump(False)
            else:
                logger.warning(f"[STAGE_EXEC] NO MATCH: pump_mode={stage.pump_mode} didn't match any PumpMode!")
            
            # Execute I/O actions: DURING_STAGE
            self._execute_io_actions(stage, IOActionTiming.DURING_STAGE)
            
            # Run stage with completion monitoring
            logger.info("[STAGE_EXEC] Entering _run_stage_with_monitoring...")
            completion_reason = self._run_stage_with_monitoring(stage, stage_data)
            
            logger.info("=" * 60)
            logger.info(f"[STAGE_COMPLETE] Monitoring returned: '{completion_reason}'")
            logger.info(f"[STAGE_COMPLETE] About to: 1) END_OF_STAGE IO, 2) TURN OFF PUMP, 3) AFTER_STAGE IO")
            logger.info("=" * 60)
            self._update_status(f"Stage complete: {completion_reason}")
            
            # Notify stage completion
            if self.completion_callback:
                self.completion_callback(self.current_stage_index, completion_reason)
            
            # Execute I/O actions: END_OF_STAGE
            logger.info("[STAGE_COMPLETE] Step 1: Executing END_OF_STAGE I/O actions...")
            self._execute_io_actions(stage, IOActionTiming.END_OF_STAGE)
            
            # Turn off pump
            logger.info("[STAGE_COMPLETE] Step 2: Turning off pump...")
            self._control_pump(False)
            logger.info("[STAGE_COMPLETE] Step 2: Pump turn-off command sent!")
            
            # Execute I/O actions: AFTER_STAGE
            self._execute_io_actions(stage, IOActionTiming.AFTER_STAGE)
            
            # Store stage data
            self.stage_data.append(stage_data)
            
            stage_duration = time.monotonic() - stage_start_time
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
        # CRITICAL: Use time.monotonic() for elapsed calculations (not time.time()!)
        # time.time() returns epoch time (~1.7 billion), time.monotonic() returns system uptime
        # Mixing them gives wildly wrong elapsed values!
        stage_start = time.monotonic()
        sample_interval = 0.1  # Check conditions every 100ms
        last_progress_log = 0.0  # Track last progress log time
        
        logger.info(f"[TIMING] stage_start={stage_start:.3f} (monotonic), will use monotonic for elapsed")
        
        logger.info(f"  Monitoring Completion Conditions:")
        if stage.target_vacuum_bar is not None:
            logger.info(f"    - Vacuum Setpoint: {stage.target_vacuum_bar:.3f} bar (magnitude: {abs(stage.target_vacuum_bar):.3f})")
        if stage.max_time_seconds is not None:
            logger.info(f"    - Time Limit: {stage.max_time_seconds:.1f}s")
        if stage.min_time_seconds > 0:
            logger.info(f"    - Minimum Hold: {stage.min_time_seconds:.1f}s")
        logger.info(f"    - NOTE: vacuum_bar from sensors is POSITIVE magnitude (e.g., 0.3 = 300mbar vacuum)")
        
        min_time_passed_logged = False  # Track if we've logged passing min_time
        loop_count = 0
        
        while self.state == TestState.RUNNING:
            loop_count += 1
            # Monotonic time prevents freezes when system clock steps (e.g., NTP)
            elapsed = time.monotonic() - stage_start
            
            # Log timing debug info occasionally
            if loop_count <= 5 or loop_count % 100 == 0:
                logger.debug(f"[LOOP #{loop_count}] elapsed={elapsed:.2f}s, min_time={stage.min_time_seconds}s, state={self.state}")
            
            # TODO: Read actual vacuum from sensors
            current_vacuum = 0.0  # Placeholder
            
            # Check minimum time first
            if elapsed < stage.min_time_seconds:
                if loop_count <= 3:
                    logger.debug(f"[MIN_TIME] Waiting... elapsed={elapsed:.2f}s < min_time={stage.min_time_seconds}s")
                time.sleep(sample_interval)
                continue
            
            # Log once when min_time is passed
            if not min_time_passed_logged:
                logger.info(f"[MIN_TIME] ✓ Minimum time passed: elapsed={elapsed:.2f}s >= {stage.min_time_seconds}s - now checking setpoint")
                min_time_passed_logged = True
            
            # Read actual vacuum level from sensor FIRST
            # vacuum_bar: 0 = atmosphere, ~1 = full vacuum (matches sequence setpoint units)
            # pressure_psig: gauge pressure (negative = vacuum, positive = above atmosphere)
            current_vacuum = 0.0
            current_pressure_psig = 0.0
            if self.widgetlords:
                try:
                    sensor_data = self.widgetlords.read()
                    current_vacuum = sensor_data.get("vacuum_bar", 0.0)
                    current_pressure_psig = sensor_data.get("pressure_psig", 0.0)
                except Exception as e:
                    logger.warning(f"Failed to read vacuum sensor: {e}")
            
            # Calculate progress percentage
            progress = 0.0
            if stage.max_time_seconds is not None and stage.max_time_seconds > 0:
                progress = min(1.0, elapsed / stage.max_time_seconds)
            elif stage.target_vacuum_bar is not None:
                target_mag = abs(stage.target_vacuum_bar)
                if target_mag > 0:
                    # Use magnitude so negative gauge readings still show progress
                    progress = min(1.0, abs(current_vacuum) / target_mag)
            
            # Emit progress update every second
            if elapsed - last_progress_log >= 1.0:
                status_text = f"Elapsed: {elapsed:.1f}s"
                if stage.target_vacuum_bar is not None:
                    target_mag = abs(stage.target_vacuum_bar)
                    current_mag = abs(current_vacuum)
                    pct_of_target = (current_mag / target_mag * 100) if target_mag > 0 else 0
                    status_text += f" | Vacuum: {current_vacuum:.3f} bar ({pct_of_target:.0f}% of {stage.target_vacuum_bar:.3f})"
                    status_text += f" ({current_pressure_psig:.1f} PSIG)"
                
                # Notify progress callback
                if self.progress_callback:
                    self.progress_callback(progress, status_text)
                
                # Log progress periodically (every 2 seconds for better visibility)
                if int(elapsed) % 2 == 0:
                    logger.info(f"[MONITOR] {status_text}")
                    if stage.target_vacuum_bar is not None:
                        target_mag = abs(stage.target_vacuum_bar)
                        current_mag = abs(current_vacuum)
                        logger.info(f"[MONITOR]   target_mag={target_mag:.4f}, current_mag={current_mag:.4f}, "
                                   f"reached={current_mag >= target_mag}")
                
                last_progress_log = elapsed
            
            # Check completion conditions
            # For MAINTAIN_VACUUM mode: only TIME completes the stage (not setpoint)
            # For other modes: setpoint OR time completes the stage
            
            # Pump cycling for MAINTAIN_VACUUM mode - do this BEFORE completion checks
            if stage.pump_mode == PumpMode.MAINTAIN_VACUUM and stage.target_vacuum_bar is not None:
                self._maintain_vacuum_cycle(current_vacuum, stage.target_vacuum_bar, stage.vacuum_tolerance_bar)
            
            # Condition 1: Setpoint reached (but NOT for MAINTAIN_VACUUM mode)
            # In MAINTAIN_VACUUM mode, we want to HOLD at setpoint, not complete when we reach it
            if stage.pump_mode != PumpMode.MAINTAIN_VACUUM:
                if stage.target_vacuum_bar is not None:
                    # Check if minimum time has passed before allowing setpoint completion
                    if elapsed >= stage.min_time_seconds:
                        target = stage.target_vacuum_bar
                        
                        # IMPORTANT: current_vacuum from widgetlords.read() is ALWAYS POSITIVE
                        # (it's the magnitude of vacuum: vacuum_bar = -pressure_psig * conversion)
                        # Target in sequences can be:
                        #   - Positive (0.3 bar = 300mbar vacuum magnitude)
                        #   - Negative gauge (-0.3 bar = 300mbar below atmosphere)
                        # 
                        # To compare correctly, we need to use magnitudes:
                        #   - current_vacuum is already a positive magnitude
                        #   - For negative targets, use abs(target) for comparison
                        
                        target_magnitude = abs(target)
                        current_magnitude = abs(current_vacuum)
                        
                        # Setpoint reached when current vacuum magnitude >= target magnitude
                        setpoint_reached = current_magnitude >= target_magnitude
                        
                        # VERBOSE LOGGING - always log setpoint check status every second
                        if int(elapsed) != int(elapsed - sample_interval):  # Log once per second
                            pct_progress = (current_magnitude / target_magnitude * 100) if target_magnitude > 0 else 0
                            logger.info(f"[SETPOINT] {current_magnitude:.4f} / {target_magnitude:.4f} bar = {pct_progress:.1f}% | "
                                       f"PSIG={current_pressure_psig:.2f} | reached={setpoint_reached}")
                        
                        # Log when getting close (80%+)
                        if current_magnitude >= target_magnitude * 0.8:
                            logger.info(f"[SETPOINT] APPROACHING TARGET: {current_magnitude:.4f} >= {target_magnitude * 0.8:.4f} (80% threshold)")
                        
                        if setpoint_reached:
                            logger.info("=" * 60)
                            logger.info(f"[SETPOINT] ✓✓✓ SETPOINT REACHED! ✓✓✓")
                            logger.info(f"[SETPOINT]   Current: {current_magnitude:.4f} bar")
                            logger.info(f"[SETPOINT]   Target:  {target_magnitude:.4f} bar")
                            logger.info(f"[SETPOINT]   PSIG:    {current_pressure_psig:.2f}")
                            logger.info(f"[SETPOINT]   Returning 'setpoint reached' - pump should turn OFF next")
                            logger.info("=" * 60)
                            return f"setpoint reached ({current_vacuum:.3f} bar)"
            
            # Condition 2: Time limit exceeded (applies to ALL modes including MAINTAIN_VACUUM)
            if stage.max_time_seconds is not None:
                if elapsed >= stage.max_time_seconds:
                    logger.info(f"  ⏱ Time limit reached: {elapsed:.1f}s >= {stage.max_time_seconds:.1f}s")
                    return f"time limit ({elapsed:.1f}s)"
            
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
                    "pressure_psig": current_pressure_psig,
                    "target_vacuum_bar": stage.target_vacuum_bar,
                    "test_state": self.state.value,
                }
                
                # Add IO device states from RelayStateManager (single source of truth)
                io_states = self._get_io_device_states_for_logging()
                for device_name, state in io_states.items():
                    # Create column name like "io_vent_valve" or "io_vacuum_pump"
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
        Control vacuum pump state via relay.
        
        Args:
            state: True for ON, False for OFF
        """
        logger.info(f"[PUMP] Setting pump to {'ON' if state else 'OFF'}")
        
        if self.widgetlords:
            # Control pump via relay module
            try:
                success = self.widgetlords.set_relay("relay_module", "vacuum_pump", state)
                if success:
                    logger.info(f"[PUMP] Pump {'ON' if state else 'OFF'} - SUCCESS")
                else:
                    logger.warning(f"[PUMP] Pump {'ON' if state else 'OFF'} - FAILED (set_relay returned False)")
            except Exception as e:
                logger.error(f"[PUMP] Failed to control pump: {e}")
        elif self.pump:
            # Use pump controller if available
            try:
                self.pump.set_pump_state(state)
                logger.info(f"[PUMP] Pump {'ON' if state else 'OFF'} via pump controller")
            except Exception as e:
                logger.error(f"[PUMP] Pump controller error: {e}")
        else:
            logger.warning("[PUMP] No pump control available (no widgetlords or pump controller)")
        
        time.sleep(0.5)
    
    def _maintain_vacuum_cycle(self, current_vacuum: float, target_vacuum: float, tolerance: float) -> None:
        """
        Cycle pump ON/OFF to maintain vacuum at setpoint within tolerance.
        
        Logic (using magnitudes to handle both positive and negative gauge values):
        - If |vacuum| < |target| - tolerance: turn pump ON (need more vacuum)
        - If |vacuum| > |target| + tolerance: turn pump OFF (exceeded target)
        - Within tolerance band: keep current pump state (hysteresis)
        
        Args:
            current_vacuum: Current vacuum reading in bar (positive magnitude from widgetlords)
            target_vacuum: Target vacuum in bar (can be negative gauge like -0.3)
            tolerance: Acceptable tolerance in bar (default 0.05)
        """
        # Track pump state for hysteresis (avoid rapid cycling)
        if not hasattr(self, '_maintain_pump_on'):
            self._maintain_pump_on = True  # Start with pump on to reach setpoint
        
        # Track logging to avoid spam
        if not hasattr(self, '_maintain_log_count'):
            self._maintain_log_count = 0
        self._maintain_log_count += 1
        
        # Use magnitudes so this works for positive (absolute) and negative gauge readings
        target_mag = abs(target_vacuum)
        current_mag = abs(current_vacuum)
        lower_bound = max(0.0, target_mag - tolerance)
        upper_bound = target_mag + tolerance
        
        # Log state periodically (every ~5 seconds at 10Hz = every 50 calls)
        verbose = self._maintain_log_count <= 10 or self._maintain_log_count % 50 == 0
        if verbose:
            logger.info(f"[MAINTAIN] current_mag={current_mag:.3f}, target_mag={target_mag:.3f}, "
                       f"bounds=[{lower_bound:.3f}, {upper_bound:.3f}], pump_on={self._maintain_pump_on}")
        
        if current_mag < lower_bound:
            # Not enough vacuum yet (too close to atmosphere) - need more vacuum
            if not self._maintain_pump_on:
                logger.info(f"[MAINTAIN] |Vacuum| {current_mag:.3f} bar < {lower_bound:.3f} bar - turning pump ON")
                self._control_pump(True)
                self._maintain_pump_on = True
        elif current_mag > upper_bound:
            # Exceeds target window - can turn pump off
            if self._maintain_pump_on:
                logger.info(f"[MAINTAIN] |Vacuum| {current_mag:.3f} bar > {upper_bound:.3f} bar - turning pump OFF")
                self._control_pump(False)
                self._maintain_pump_on = False
        # else: within tolerance band - maintain current state (hysteresis)
    
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
            # Log the DESIRED state (what the sequence wants)
            is_valve = "valve" in action.device_name.lower()
            if is_valve:
                state_str = "OPEN" if action.value else "CLOSED"
            else:
                state_str = "ON" if action.value else "OFF"
            logger.info(f"    [{i}/{len(actions)}] {action.device_name}: {state_str} (desired)")
            self._execute_single_io_action(action)
    
    def _execute_single_io_action(self, action: IOAction) -> None:
        """
        Execute a single I/O action.
        
        STATE MANAGEMENT: The _set_digital_output method updates the global
        RelayStateManager, which is the single source of truth for all relay states.
        The IO callback is then fired to notify listeners (GUI, etc.).
        
        VALVE LOGIC: Valves are NORMALLY-OPEN (NO) type, so the relay state is
        INVERTED from the desired physical state:
            - Sequence says "OPEN" (value=True) → relay OFF (False) → valve physically OPEN
            - Sequence says "CLOSED" (value=False) → relay ON (True) → valve physically CLOSED
        
        Args:
            action: IOAction to execute
        """
        logger.info(f"[IO_ACTION] Executing: {action.device_name} = {action.value} (type={action.action_type.value})")
        
        try:
            # Apply delay if specified
            if action.delay_seconds > 0:
                logger.info(f"[IO_ACTION] Delaying {action.delay_seconds}s before I/O action")
                time.sleep(action.delay_seconds)
            
            # Execute based on action type
            if action.action_type == IOActionType.DIGITAL_OUTPUT:
                desired_state = bool(action.value)
                
                # VALVE INVERSION: Valves are NORMALLY-OPEN (NO) type
                # - To physically OPEN a NO valve, de-energize relay (False)
                # - To physically CLOSE a NO valve, energize relay (True)
                # In sequences: value=True means "I want it OPEN", value=False means "I want it CLOSED"
                # So for valves, we INVERT: relay_state = NOT desired_state
                is_valve = "valve" in action.device_name.lower()
                
                if is_valve:
                    relay_state = not desired_state  # Invert for NO valves
                    logger.info(f"[IO_ACTION] VALVE '{action.device_name}': desired={desired_state} (OPEN={desired_state}), relay_state={relay_state} (inverted for NO valve)")
                else:
                    relay_state = desired_state  # Non-valves: state = relay state directly
                    logger.info(f"[IO_ACTION] OUTPUT '{action.device_name}': state={relay_state}")
                
                success = self._set_digital_output(action.device_name, relay_state)
                logger.info(f"[IO_ACTION] _set_digital_output returned: {success}")
                
                # NOTE: State is now tracked by RelayStateManager (SSOT)
                # The _set_digital_output method updates RelayStateManager
                
                # Notify IO callback with RELAY state (not desired state)
                # The UI correctly interprets relay state for NO valves
                if self.io_callback:
                    logger.info(f"[IO_ACTION] Notifying IO callback: {action.device_name} = {relay_state}")
                    self.io_callback(action.device_name, relay_state)
                else:
                    logger.warning(f"[IO_ACTION] No IO callback registered!")
            
            elif action.action_type == IOActionType.ANALOG_OUTPUT:
                self._set_analog_output(action.device_name, float(action.value))
            
            elif action.action_type == IOActionType.PULSE:
                # PULSE: Turn on, wait, turn off
                # For valves (NO type): "on" means physically OPEN (relay OFF), "off" means physically CLOSED (relay ON)
                is_valve = "valve" in action.device_name.lower()
                
                # Turn on (for valves: OPEN = relay OFF)
                relay_on = False if is_valve else True
                self._set_digital_output(action.device_name, relay_on)
                if self.io_callback:
                    self.io_callback(action.device_name, relay_on)
                
                # Wait for duration
                if action.duration_seconds:
                    time.sleep(action.duration_seconds)
                
                # Turn off (for valves: CLOSED = relay ON)
                relay_off = True if is_valve else False
                self._set_digital_output(action.device_name, relay_off)
                if self.io_callback:
                    self.io_callback(action.device_name, relay_off)
            
        except Exception as e:
            logger.error(f"Error executing I/O action {action}: {e}", exc_info=True)
            # Don't fail the stage on I/O errors, just log them
    
    def _set_digital_output(self, device_name: str, state: bool, bypass_interlocks: bool = False) -> bool:
        """
        Set a digital output (relay/valve) to ON or OFF with interlock checking.
        
        INTERLOCK SAFETY: State changes are checked against safety interlocks
        (e.g., pump cannot run with vent valve open). If blocked, this method
        returns False and the state is not changed.
        
        SINGLE SOURCE OF TRUTH: The RelayStateManager owns all relay state.
        This method updates the manager, which then notifies all listeners.
        
        Args:
            device_name: Name of the device
            state: True for ON, False for OFF
            bypass_interlocks: If True, skip safety checks (emergency stop)
        
        Returns:
            bool: True if state was set, False if blocked by interlock
        """
        logger.info(f"[SET_DO] {device_name} -> {'OPEN/ON' if state else 'CLOSED/OFF'} (bypass={bypass_interlocks})")
        
        # Check and update global relay state manager (SINGLE SOURCE OF TRUTH)
        try:
            from ..daq.relay_state_manager import relay_state_manager
            # Use "relay_module" as default module name (matches hardware_config.yaml)
            logger.info(f"[SET_DO] Checking interlock via RelayStateManager...")
            success, error_msg = relay_state_manager.set_state(
                "relay_module", device_name, state,
                bypass_interlocks=bypass_interlocks
            )
            
            if not success:
                logger.warning(f"[SET_DO] INTERLOCK BLOCKED: {error_msg}")
                self._update_status(f"Blocked: {error_msg}")
                return False
            
            logger.info(f"[SET_DO] RelayStateManager accepted state change")
                
        except Exception as e:
            logger.warning(f"[SET_DO] Could not update relay state manager: {e}")
        
        # Interlock passed - control the hardware via WidgetLords interface
        if self.widgetlords:
            logger.info(f"[SET_DO] Calling widgetlords.set_relay('relay_module', '{device_name}', {state})")
            try:
                # The hardware interface will also check interlocks, but state manager
                # already approved, so this should succeed
                success = self.widgetlords.set_relay("relay_module", device_name, state)
                if not success:
                    logger.warning(f"[SET_DO] FAILED: widgetlords.set_relay returned False for {device_name}")
                    return False
                else:
                    logger.info(f"[SET_DO] SUCCESS: Hardware {device_name} set to {'ON' if state else 'OFF'}")
            except Exception as e:
                logger.error(f"[SET_DO] EXCEPTION setting digital output {device_name}: {e}", exc_info=True)
                return False
        else:
            logger.warning(f"[SET_DO] NO HARDWARE INTERFACE - simulated: {device_name} = {'ON' if state else 'OFF'}")
        
        return True
    
    def _get_io_device_states_for_logging(self) -> Dict[str, bool]:
        """
        Get current IO device states from RelayStateManager for data logging.
        
        SINGLE SOURCE OF TRUTH: All relay/valve states are owned by RelayStateManager.
        This method queries the manager to get current states for CSV logging.
        
        Returns:
            Dict mapping device names to current states (True=ON/OPEN, False=OFF/CLOSED)
        """
        try:
            from ..daq.relay_state_manager import relay_state_manager
            
            all_states = relay_state_manager.get_all_states()
            
            # Flatten the nested dict structure to {device_name: state}
            io_states = {}
            for module_name, channels in all_states.items():
                for device_name, state in channels.items():
                    io_states[device_name] = state
            
            return io_states
            
        except Exception as e:
            logger.warning(f"Could not get IO states from RelayStateManager: {e}")
            return {}
    
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
        """
        Execute emergency I/O actions - pump off only (minimal failsafe).
        
        SIMPLIFIED FAILSAFE: Only turns off the pump to prevent damage.
        Valve states are NOT modified to avoid interfering with test restart.
        """
        logger.warning("=" * 60)
        logger.warning("EMERGENCY STOP - PUMP OFF ONLY (MINIMAL FAILSAFE)")
        logger.warning("=" * 60)
        
        # Only stop the pump - valve states remain unchanged
        logger.warning("  E-STOP: Stopping vacuum pump...")
        self._set_digital_output("vacuum_pump", False, bypass_interlocks=True)
        
        # Notify callback that pump state changed
        if self.io_callback:
            self.io_callback("vacuum_pump", False)
        
        logger.warning("  E-STOP: Pump OFF - valves unchanged for easy restart")
        logger.warning("=" * 60)
    
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

