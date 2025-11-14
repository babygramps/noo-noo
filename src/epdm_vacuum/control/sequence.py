"""
Test Sequence Models

Data models for test sequences and stages:
- TestStage: Individual stage parameters
- TestSequence: Complete sequence with metadata
- Validation methods for parameter ranges
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SequenceMode(Enum):
    """Sequence configuration mode."""
    SIMPLE = "simple"
    ADVANCED = "advanced"


class IOActionTiming(Enum):
    """When an I/O action should occur relative to stage."""
    BEFORE_STAGE = "before_stage"
    START_OF_STAGE = "start_of_stage"
    DURING_STAGE = "during_stage"
    END_OF_STAGE = "end_of_stage"
    AFTER_STAGE = "after_stage"


class IOActionType(Enum):
    """Type of I/O action."""
    DIGITAL_OUTPUT = "digital_output"  # Set relay/valve on/off
    ANALOG_OUTPUT = "analog_output"    # Set analog output value
    PULSE = "pulse"                     # Pulse output for duration


@dataclass
class IOAction:
    """
    Represents a single I/O control action.
    
    Used to control valves, relays, and other actuators during test execution.
    """
    
    # Device identification
    device_name: str  # Name of the I/O device (e.g., "vent_valve", "inlet_valve")
    action_type: IOActionType = IOActionType.DIGITAL_OUTPUT
    
    # Action parameters
    value: Any = False  # For digital: True/False, for analog: float value
    timing: IOActionTiming = IOActionTiming.START_OF_STAGE
    delay_seconds: float = 0.0  # Delay after timing point
    duration_seconds: Optional[float] = None  # For pulse actions or timed operations
    
    # Description
    description: str = ""
    
    def validate(self) -> tuple[bool, List[str]]:
        """
        Validate I/O action parameters.
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        if not self.device_name or not self.device_name.strip():
            errors.append("Device name cannot be empty")
        
        if self.delay_seconds < 0:
            errors.append(f"Delay {self.delay_seconds}s cannot be negative")
        
        if self.duration_seconds is not None and self.duration_seconds <= 0:
            errors.append(f"Duration {self.duration_seconds}s must be positive")
        
        if self.action_type == IOActionType.PULSE and self.duration_seconds is None:
            errors.append("Pulse action requires duration_seconds")
        
        if self.action_type == IOActionType.DIGITAL_OUTPUT:
            if not isinstance(self.value, bool):
                errors.append(f"Digital output value must be boolean, got {type(self.value)}")
        
        if self.action_type == IOActionType.ANALOG_OUTPUT:
            try:
                float(self.value)
            except (TypeError, ValueError):
                errors.append(f"Analog output value must be numeric, got {self.value}")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "device_name": self.device_name,
            "action_type": self.action_type.value,
            "value": self.value,
            "timing": self.timing.value,
            "delay_seconds": self.delay_seconds,
            "duration_seconds": self.duration_seconds,
            "description": self.description,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IOAction":
        """Create IOAction from dictionary."""
        # Convert string enums back to enum types
        if isinstance(data.get("action_type"), str):
            data["action_type"] = IOActionType(data["action_type"])
        if isinstance(data.get("timing"), str):
            data["timing"] = IOActionTiming(data["timing"])
        
        return cls(**data)
    
    def __str__(self) -> str:
        """String representation."""
        value_str = "ON" if self.value else "OFF" if isinstance(self.value, bool) else str(self.value)
        timing_str = self.timing.value.replace("_", " ").title()
        return f"{self.device_name}: {value_str} ({timing_str})"


@dataclass
class TestStage:
    """
    Represents a single stage in a test sequence.
    
    A stage defines parameters for one phase of testing, such as
    ramping to a target vacuum and holding for a specified duration.
    """
    
    # Core parameters (required for all modes)
    target_vacuum_bar: float
    hold_time_seconds: float
    
    # Advanced parameters (optional, use defaults if None)
    name: Optional[str] = None
    description: Optional[str] = None
    ramp_rate_bar_per_sec: Optional[float] = None
    sample_rate_hz: Optional[float] = None
    delay_before_seconds: Optional[float] = 0.0
    
    # Safety limits (per-stage overrides)
    max_force_kg: Optional[float] = None
    max_single_cell_kg: Optional[float] = None
    
    # Control options
    collect_data: bool = True
    auto_vent: bool = True
    
    # I/O control actions
    io_actions: List[IOAction] = field(default_factory=list)
    
    def add_io_action(self, action: IOAction) -> None:
        """
        Add an I/O action to this stage.
        
        Args:
            action: IOAction to add
        """
        self.io_actions.append(action)
        logger.debug(f"Added I/O action to stage: {action}")
    
    def remove_io_action(self, index: int) -> Optional[IOAction]:
        """
        Remove an I/O action from this stage.
        
        Args:
            index: Index of action to remove
        
        Returns:
            The removed IOAction, or None if index invalid
        """
        if 0 <= index < len(self.io_actions):
            return self.io_actions.pop(index)
        return None
    
    def get_io_actions_for_timing(self, timing: IOActionTiming) -> List[IOAction]:
        """
        Get all I/O actions for a specific timing point.
        
        Args:
            timing: IOActionTiming to filter by
        
        Returns:
            List of IOAction objects for that timing
        """
        return [action for action in self.io_actions if action.timing == timing]
    
    def validate(self, config_limits: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str], List[str]]:
        """
        Validate stage parameters against safety limits.
        
        Args:
            config_limits: Dictionary with safety limits from config
        
        Returns:
            Tuple of (is_valid, list_of_error_messages, list_of_warnings)
        """
        errors = []
        warnings = []
        
        # Basic parameter validation
        if self.target_vacuum_bar < 0 or self.target_vacuum_bar > 1.0:
            errors.append(f"Target vacuum {self.target_vacuum_bar} bar is out of range [0, 1.0]")
        
        if self.hold_time_seconds < 0:
            errors.append(f"Hold time {self.hold_time_seconds}s cannot be negative")
        
        if self.hold_time_seconds > 3600:
            errors.append(f"Hold time {self.hold_time_seconds}s exceeds 1 hour (safety limit)")
        
        if self.delay_before_seconds and self.delay_before_seconds < 0:
            errors.append(f"Delay {self.delay_before_seconds}s cannot be negative")
        
        # Advanced parameter validation
        if self.ramp_rate_bar_per_sec is not None:
            if self.ramp_rate_bar_per_sec <= 0:
                errors.append(f"Ramp rate {self.ramp_rate_bar_per_sec} must be positive")
            if self.ramp_rate_bar_per_sec > 0.5:
                errors.append(f"Ramp rate {self.ramp_rate_bar_per_sec} bar/s exceeds safety limit (0.5)")
        
        if self.sample_rate_hz is not None:
            if self.sample_rate_hz <= 0 or self.sample_rate_hz > 100:
                errors.append(f"Sample rate {self.sample_rate_hz} Hz is out of range (0, 100]")
        
        # Safety limits validation
        if config_limits:
            max_vacuum = config_limits.get("max_vacuum_bar", 1.0)
            if self.target_vacuum_bar > max_vacuum:
                errors.append(f"Target vacuum {self.target_vacuum_bar} bar exceeds config limit {max_vacuum} bar")
            
            if self.max_force_kg:
                max_force_limit = config_limits.get("max_force_kg", 800.0)
                if self.max_force_kg > max_force_limit:
                    errors.append(f"Max force {self.max_force_kg} kg exceeds config limit {max_force_limit} kg")
            
            if self.max_single_cell_kg:
                max_cell_limit = config_limits.get("max_single_cell_kg", 250.0)
                if self.max_single_cell_kg > max_cell_limit:
                    errors.append(f"Max single cell {self.max_single_cell_kg} kg exceeds config limit {max_cell_limit} kg")
        
        # Validate I/O actions
        for i, io_action in enumerate(self.io_actions):
            action_valid, action_errors = io_action.validate()
            if not action_valid:
                for error in action_errors:
                    errors.append(f"I/O Action {i+1}: {error}")
        
        # Check for recommended I/O actions (warnings, not errors)
        if self.target_vacuum_bar > 0.0:  # Only for vacuum stages
            # Check if inlet valve is being closed
            has_inlet_close = any(
                action.device_name == "inlet_valve" and 
                action.value == False and
                action.timing in (IOActionTiming.BEFORE_STAGE, IOActionTiming.START_OF_STAGE)
                for action in self.io_actions
            )
            
            if not has_inlet_close:
                warnings.append("⚠️ No I/O action closes 'inlet_valve' - chamber may not seal properly")
            
            # Check if vent valve is being closed during vacuum
            has_vent_close = any(
                action.device_name == "vent_valve" and 
                action.value == False and
                action.timing in (IOActionTiming.BEFORE_STAGE, IOActionTiming.START_OF_STAGE)
                for action in self.io_actions
            )
            
            if not has_vent_close:
                warnings.append("⚠️ No I/O action closes 'vent_valve' - vacuum may not be maintained")
            
            # Check if vent valve opens at end (if auto_vent is True)
            if self.auto_vent:
                has_vent_open = any(
                    action.device_name == "vent_valve" and 
                    action.value == True and
                    action.timing in (IOActionTiming.END_OF_STAGE, IOActionTiming.AFTER_STAGE)
                    for action in self.io_actions
                )
                
                if not has_vent_open:
                    warnings.append("ℹ️ Consider adding I/O action to open 'vent_valve' at end of stage")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def get_estimated_duration(self) -> float:
        """
        Estimate total duration for this stage.
        
        Returns:
            float: Estimated duration in seconds
        """
        duration = 0.0
        
        # Add delay before stage
        if self.delay_before_seconds:
            duration += self.delay_before_seconds
        
        # Add ramp time (if ramp rate specified)
        if self.ramp_rate_bar_per_sec and self.ramp_rate_bar_per_sec > 0:
            ramp_time = self.target_vacuum_bar / self.ramp_rate_bar_per_sec
            duration += ramp_time
        else:
            # Conservative estimate: assume 10 seconds per 0.1 bar
            duration += self.target_vacuum_bar * 100
        
        # Add hold time
        duration += self.hold_time_seconds
        
        # Add vent time (if auto-vent enabled)
        if self.auto_vent:
            duration += 5.0  # Conservative estimate
        
        return duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary for serialization."""
        data = asdict(self)
        # Convert I/O actions to dictionaries
        if self.io_actions:
            data["io_actions"] = [action.to_dict() for action in self.io_actions]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStage":
        """Create TestStage from dictionary."""
        # Extract and convert I/O actions
        io_actions_data = data.pop("io_actions", [])
        io_actions = [IOAction.from_dict(action_data) for action_data in io_actions_data]
        
        # Create stage with remaining data
        stage = cls(**data)
        stage.io_actions = io_actions
        
        return stage
    
    def __str__(self) -> str:
        """String representation."""
        name = self.name or f"Stage @ {self.target_vacuum_bar} bar"
        return f"{name}: {self.target_vacuum_bar} bar for {self.hold_time_seconds}s"


@dataclass
class TestSequence:
    """
    Represents a complete test sequence with metadata and stages.
    
    A sequence contains one or more stages that are executed sequentially
    during a test run.
    """
    
    name: str
    stages: List[TestStage] = field(default_factory=list)
    
    # Metadata
    description: str = ""
    mode: SequenceMode = SequenceMode.SIMPLE
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    author: Optional[str] = None
    
    # Sequence-level settings
    loop_count: int = 1
    pause_between_stages: bool = False
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()
        
        # Ensure mode is SequenceMode enum
        if isinstance(self.mode, str):
            self.mode = SequenceMode(self.mode)
    
    def add_stage(self, stage: TestStage, index: Optional[int] = None) -> None:
        """
        Add a stage to the sequence.
        
        Args:
            stage: TestStage to add
            index: Optional position to insert (appends if None)
        """
        if index is None:
            self.stages.append(stage)
        else:
            self.stages.insert(index, stage)
        
        self.update_modified_date()
        logger.info(f"Added stage to sequence '{self.name}': {stage}")
    
    def remove_stage(self, index: int) -> Optional[TestStage]:
        """
        Remove a stage from the sequence.
        
        Args:
            index: Index of stage to remove
        
        Returns:
            The removed TestStage, or None if index invalid
        """
        if 0 <= index < len(self.stages):
            stage = self.stages.pop(index)
            self.update_modified_date()
            logger.info(f"Removed stage from sequence '{self.name}': {stage}")
            return stage
        return None
    
    def move_stage(self, from_index: int, to_index: int) -> bool:
        """
        Move a stage to a different position.
        
        Args:
            from_index: Current index
            to_index: Target index
        
        Returns:
            bool: True if successful
        """
        if 0 <= from_index < len(self.stages) and 0 <= to_index < len(self.stages):
            stage = self.stages.pop(from_index)
            self.stages.insert(to_index, stage)
            self.update_modified_date()
            logger.info(f"Moved stage in sequence '{self.name}' from {from_index} to {to_index}")
            return True
        return False
    
    def duplicate_stage(self, index: int) -> bool:
        """
        Duplicate a stage at the given index.
        
        Args:
            index: Index of stage to duplicate
        
        Returns:
            bool: True if successful
        """
        if 0 <= index < len(self.stages):
            stage = self.stages[index]
            # Create a copy
            new_stage = TestStage(**asdict(stage))
            if new_stage.name:
                new_stage.name = f"{new_stage.name} (copy)"
            self.stages.insert(index + 1, new_stage)
            self.update_modified_date()
            logger.info(f"Duplicated stage in sequence '{self.name}'")
            return True
        return False
    
    def validate(self, config_limits: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str], List[str]]:
        """
        Validate entire sequence.
        
        Args:
            config_limits: Dictionary with safety limits from config
        
        Returns:
            Tuple of (is_valid, list_of_error_messages, list_of_warnings)
        """
        errors = []
        warnings = []
        
        # Check if sequence has stages
        if not self.stages:
            errors.append("Sequence has no stages")
            return False, errors, []
        
        # Check if name is valid
        if not self.name or not self.name.strip():
            errors.append("Sequence name cannot be empty")
        
        # Validate each stage
        for i, stage in enumerate(self.stages):
            stage_valid, stage_errors, stage_warnings = stage.validate(config_limits)
            if not stage_valid:
                for error in stage_errors:
                    errors.append(f"Stage {i+1}: {error}")
            # Collect warnings from stages
            for warning in stage_warnings:
                warnings.append(f"Stage {i+1}: {warning}")
        
        # Check total duration
        total_duration = self.get_estimated_duration()
        if total_duration > 7200:  # 2 hours
            errors.append(f"Total sequence duration {total_duration/60:.1f} minutes exceeds 2 hours")
        
        is_valid = len(errors) == 0
        return is_valid, errors, warnings
    
    def get_estimated_duration(self) -> float:
        """
        Get estimated total duration for entire sequence.
        
        Returns:
            float: Estimated duration in seconds
        """
        total = sum(stage.get_estimated_duration() for stage in self.stages)
        
        # Add pause time if enabled
        if self.pause_between_stages and len(self.stages) > 1:
            total += (len(self.stages) - 1) * 5.0  # 5 seconds per pause
        
        # Multiply by loop count
        total *= self.loop_count
        
        return total
    
    def get_stage_count(self) -> int:
        """Get number of stages in sequence."""
        return len(self.stages)
    
    def update_modified_date(self) -> None:
        """Update the modified date to current time."""
        self.modified_date = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert sequence to dictionary for serialization.
        
        Returns:
            Dict: Serializable dictionary
        """
        return {
            "name": self.name,
            "description": self.description,
            "mode": self.mode.value,
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "author": self.author,
            "loop_count": self.loop_count,
            "pause_between_stages": self.pause_between_stages,
            "stages": [stage.to_dict() for stage in self.stages],
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestSequence":
        """
        Create TestSequence from dictionary.
        
        Args:
            data: Dictionary with sequence data
        
        Returns:
            TestSequence: Reconstructed sequence
        """
        # Extract stages and create TestStage objects
        stages_data = data.pop("stages", [])
        stages = [TestStage.from_dict(stage_data) for stage_data in stages_data]
        
        # Create sequence with remaining data
        sequence = cls(stages=stages, **data)
        return sequence
    
    def __str__(self) -> str:
        """String representation."""
        return f"TestSequence '{self.name}': {len(self.stages)} stages, ~{self.get_estimated_duration():.0f}s"

