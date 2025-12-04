"""
Control Thread

Background thread for executing test sequences and control logic
without blocking the GUI.
"""

from typing import Optional, Dict
import logging
import time

from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class ControlThread(QThread):
    """
    Background thread for test control operations.
    
    Executes test sequences and control logic while providing
    status updates to the GUI.
    """
    
    # Signals
    status_update = pyqtSignal(str)  # Emitted with status messages
    test_complete = pyqtSignal()  # Emitted when test completes
    error_occurred = pyqtSignal(str)  # Emitted when an error occurs
    stage_changed = pyqtSignal(int, int, str)  # Emitted on stage transition (current, total, name)
    
    # New signals for enhanced UI feedback
    io_state_changed = pyqtSignal(str, bool)  # (device_name, state) - Emitted when IO device state changes
    stage_progress_updated = pyqtSignal(float, str)  # (percentage, status_text) - Emitted for progress updates
    stage_completed = pyqtSignal(int, str)  # (stage_index, completion_reason) - Emitted when stage completes
    
    def __init__(self, test_controller=None, sequence=None):
        """
        Initialize the control thread.
        
        Args:
            test_controller: TestController instance for managing tests
            sequence: Optional TestSequence to execute
        """
        super().__init__()
        
        self.test_controller = test_controller
        self.sequence = sequence
        self.running = False
        self.current_test = None
        
        # NOTE: IO device states are managed by RelayStateManager (single source of truth)
        # This thread receives state changes via callbacks and forwards them via signals
        # to the GUI components. The actual state storage is in RelayStateManager.
        
        logger.info("Control thread initialized")
    
    def run(self) -> None:
        """
        Main thread execution loop.
        
        Executes the current test sequence or single test.
        """
        logger.info("Control thread started")
        self.running = True
        
        try:
            self.status_update.emit("Initializing test...")
            
            if self.test_controller:
                # Load sequence if provided
                if self.sequence:
                    logger.info(f"Loading sequence: {self.sequence.name}")
                    success = self.test_controller.load_sequence(self.sequence)
                    if not success:
                        raise RuntimeError(f"Failed to load sequence '{self.sequence.name}'")
                
                # Set callbacks for progress updates
                self.test_controller.set_status_callback(self._on_status_update)
                self.test_controller.set_stage_callback(self._on_stage_change)
                self.test_controller.set_io_callback(self._on_io_change)
                self.test_controller.set_progress_callback(self._on_progress_update)
                self.test_controller.set_completion_callback(self._on_stage_complete)
                
                # Run the test
                logger.info("Starting test execution")
                success = self.test_controller.run_test()
                
                if success:
                    self.status_update.emit("Test completed successfully")
                    self.test_complete.emit()
                else:
                    raise RuntimeError("Test execution failed")
            else:
                # Fallback to placeholder if no controller
                logger.warning("No test controller available, using placeholder")
                self.execute_placeholder_test()
                self.status_update.emit("Test completed successfully")
                self.test_complete.emit()
            
        except Exception as e:
            error_msg = f"Control thread error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.error_occurred.emit(error_msg)
            self.status_update.emit("Test failed")
        
        finally:
            self.running = False
            logger.info("Control thread finished")
    
    def execute_placeholder_test(self) -> None:
        """
        Placeholder test sequence for development.
        
        Simulates test execution with the loaded sequence, emitting all
        appropriate signals to update the UI.
        """
        logger.info("Executing placeholder test sequence")
        
        # If we have a sequence, simulate it properly
        if self.sequence and len(self.sequence.stages) > 0:
            logger.info(f"Simulating sequence: {self.sequence.name} with {len(self.sequence.stages)} stages")
            self._simulate_sequence_execution()
        else:
            # Fallback to generic placeholder if no sequence
            logger.warning("No sequence loaded, using generic placeholder")
            self._simulate_generic_test()
    
    def _simulate_sequence_execution(self) -> None:
        """Simulate execution of the loaded sequence."""
        total_stages = len(self.sequence.stages)
        
        for stage_index, stage in enumerate(self.sequence.stages):
            if not self.running:
                logger.info("Test sequence interrupted")
                break
            
            stage_name = stage.name or f"Stage {stage_index + 1}"
            
            # Emit stage changed signal
            self.stage_changed.emit(stage_index, total_stages, stage_name)
            self.status_update.emit(f"Stage {stage_index + 1}/{total_stages}: {stage_name}")
            logger.info(f"Simulating stage {stage_index + 1}/{total_stages}: {stage_name}")
            
            # Simulate IO actions at start of stage
            from ...control.sequence import IOActionTiming
            start_actions = stage.get_io_actions_for_timing(IOActionTiming.START_OF_STAGE)
            for io_action in start_actions:
                self.io_state_changed.emit(io_action.device_name, bool(io_action.value))
                logger.debug(f"  IO: {io_action.device_name} -> {'OPEN' if io_action.value else 'CLOSED'}")
            
            # Determine stage duration (use max_time or estimate)
            if stage.max_time_seconds:
                duration = min(stage.max_time_seconds, 30.0)  # Cap at 30s for simulation
            elif stage.target_vacuum_bar:
                duration = stage.target_vacuum_bar * 10  # Estimate based on vacuum
            else:
                duration = 10.0  # Default duration
            
            # Simulate stage execution with progress updates
            start_time = time.time()
            update_interval = 0.5  # Update every 0.5 seconds
            
            while self.running:
                elapsed = time.time() - start_time
                
                if elapsed >= duration:
                    break
                
                # Calculate progress
                progress = min(1.0, elapsed / duration)
                
                # Build status text
                status_text = f"Elapsed: {elapsed:.1f}s"
                if stage.target_vacuum_bar:
                    simulated_vacuum = min(elapsed * 0.1, stage.target_vacuum_bar)
                    status_text += f" | Vacuum: {simulated_vacuum:.3f} bar"
                
                # Emit progress update
                self.stage_progress_updated.emit(progress, status_text)
                
                time.sleep(update_interval)
            
            if not self.running:
                break
            
            # Determine completion reason
            if stage.target_vacuum_bar and stage.max_time_seconds:
                # Simulate that we usually hit setpoint
                completion_reason = f"setpoint reached ({stage.target_vacuum_bar:.3f} bar)"
            elif stage.max_time_seconds:
                completion_reason = f"time limit ({stage.max_time_seconds:.1f}s)"
            elif stage.target_vacuum_bar:
                completion_reason = f"setpoint reached ({stage.target_vacuum_bar:.3f} bar)"
            else:
                completion_reason = "completed"
            
            # Emit stage completed signal
            self.stage_completed.emit(stage_index, completion_reason)
            logger.info(f"  Stage {stage_index} completed: {completion_reason}")
            
            # Simulate IO actions at end of stage
            end_actions = stage.get_io_actions_for_timing(IOActionTiming.END_OF_STAGE)
            for io_action in end_actions:
                self.io_state_changed.emit(io_action.device_name, bool(io_action.value))
                logger.debug(f"  IO: {io_action.device_name} -> {'OPEN' if io_action.value else 'CLOSED'}")
            
            # Brief pause between stages
            if stage_index < total_stages - 1:
                time.sleep(0.5)
    
    def _simulate_generic_test(self) -> None:
        """Fallback generic test simulation when no sequence is loaded."""
        # Generic placeholder stages
        stages = [
            ("Pre-test checks...", 2),
            ("Evacuating chamber...", 5),
            ("Stabilizing vacuum...", 3),
            ("Collecting data...", 10),
            ("Venting chamber...", 3),
            ("Finalizing...", 2),
        ]
        
        for stage_name, duration in stages:
            if not self.running:
                logger.info("Test sequence interrupted")
                break
            
            self.status_update.emit(stage_name)
            logger.info(f"Test stage: {stage_name}")
            
            # Simulate stage duration
            for _ in range(duration):
                if not self.running:
                    break
                time.sleep(1)
    
    def stop(self) -> None:
        """
        Stop the control thread gracefully.
        
        This signals the thread to stop and triggers the test controller's
        stop procedure if available, which handles the emergency I/O shutdown.
        """
        logger.info("Stopping control thread...")
        self.running = False
        
        # Tell the test controller to stop (triggers emergency I/O shutdown)
        if self.test_controller:
            logger.info("Calling test controller stop_test()...")
            self.test_controller.stop_test()
        
        logger.info("Control thread stop initiated")
    
    def set_test_controller(self, controller) -> None:
        """
        Set the test controller.
        
        Args:
            controller: TestController instance
        """
        self.test_controller = controller
        logger.info("Test controller set")
    
    def set_sequence(self, sequence) -> None:
        """
        Set the test sequence to execute.
        
        Args:
            sequence: TestSequence to execute
        """
        self.sequence = sequence
        logger.info(f"Test sequence set: {sequence.name if sequence else 'None'}")
    
    def _on_status_update(self, status: str) -> None:
        """
        Handle status update from test controller.
        
        Args:
            status: Status message
        """
        self.status_update.emit(status)
    
    def _on_stage_change(self, current: int, total: int, stage) -> None:
        """
        Handle stage change from test controller.
        
        Args:
            current: Current stage index
            total: Total number of stages
            stage: TestStage object
        """
        stage_name = stage.name or f"Stage {current + 1}"
        self.stage_changed.emit(current, total, stage_name)
        logger.info(f"Stage changed: {current + 1}/{total} - {stage_name}")
    
    def _on_io_change(self, device_name: str, state: bool) -> None:
        """
        Handle IO device state change from test controller.
        
        NOTE: State is managed by RelayStateManager (single source of truth).
        This callback just forwards the notification to GUI components via signal.
        The IOStatusWidget also subscribes directly to RelayStateManager for
        immediate updates from all sources (manual control, test execution, etc.).
        
        Args:
            device_name: Name of the IO device
            state: True for OPEN/ON, False for CLOSED/OFF
        """
        # Forward to GUI via signal (IOStatusWidget also listens to RelayStateManager directly)
        self.io_state_changed.emit(device_name, state)
        logger.debug(f"IO state changed: {device_name} -> {'OPEN' if state else 'CLOSED'}")
    
    def _on_progress_update(self, percentage: float, status_text: str) -> None:
        """
        Handle stage progress update from test controller.
        
        Args:
            percentage: Progress percentage (0.0 to 1.0)
            status_text: Status message (e.g., elapsed time, vacuum level)
        """
        self.stage_progress_updated.emit(percentage, status_text)
        logger.debug(f"Stage progress: {percentage*100:.1f}% - {status_text}")
    
    def _on_stage_complete(self, stage_index: int, completion_reason: str) -> None:
        """
        Handle stage completion from test controller.
        
        Args:
            stage_index: Index of completed stage
            completion_reason: Reason for completion (e.g., "setpoint reached")
        """
        self.stage_completed.emit(stage_index, completion_reason)
        logger.info(f"Stage {stage_index} completed: {completion_reason}")
    
    def pause_test(self) -> None:
        """
        Pause the current test.
        
        Note: This is a placeholder for future implementation.
        """
        logger.warning("TODO: Pause test not implemented")
        self.status_update.emit("Pause not implemented")
    
    def resume_test(self) -> None:
        """
        Resume a paused test.
        
        Note: This is a placeholder for future implementation.
        """
        logger.warning("TODO: Resume test not implemented")
        self.status_update.emit("Resume not implemented")

