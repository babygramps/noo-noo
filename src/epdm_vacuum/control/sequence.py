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


class PumpMode(Enum):
    """Vacuum pump control mode."""
    CONTINUOUS = "continuous"         # Pump ON entire stage
    MAINTAIN_VACUUM = "maintain"     # Cycle pump to maintain vacuum at setpoint
    OFF = "off"                       # Pump stays OFF (for venting stages, etc.)


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
    
    A stage defines parameters for one phase of testing with flexible
    completion conditions (time-based, setpoint-based, or both).
    """
    
    # Core parameters
    name: str = "New Stage"
    
    # Completion conditions (OR logic - first to complete wins)
    target_vacuum_bar: Optional[float] = None  # None = no vacuum setpoint
    max_time_seconds: Optional[float] = None   # None = run indefinitely
    min_time_seconds: float = 0.0              # Minimum hold before checking setpoint
    
    # Pump control
    pump_mode: PumpMode = PumpMode.CONTINUOUS
    vacuum_tolerance_bar: float = 0.05  # For MAINTAIN_VACUUM mode
    
    # I/O control actions
    io_actions: List[IOAction] = field(default_factory=list)
    
    # Data collection
    collect_data: bool = True
    
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
        
        # Check that at least one completion condition is set
        if self.target_vacuum_bar is None and self.max_time_seconds is None:
            warnings.append("No completion condition set - stage will run indefinitely until manual stop")
        
        # Vacuum setpoint validation
        if self.target_vacuum_bar is not None:
            if self.target_vacuum_bar < 0 or self.target_vacuum_bar > 1.0:
                errors.append(f"Target vacuum {self.target_vacuum_bar} bar is out of range [0, 1.0]")
            
            # Check against config limits
            if config_limits:
                max_vacuum = config_limits.get("max_vacuum_bar", 1.0)
                if self.target_vacuum_bar > max_vacuum:
                    errors.append(f"Target vacuum {self.target_vacuum_bar} bar exceeds config limit {max_vacuum} bar")
        
        # Time limit validation
        if self.max_time_seconds is not None:
            if self.max_time_seconds <= 0:
                errors.append(f"Time limit {self.max_time_seconds}s must be positive")
            
            if self.max_time_seconds > 3600:
                errors.append(f"Time limit {self.max_time_seconds}s exceeds 1 hour (safety limit)")
        
        # Minimum time validation
        if self.min_time_seconds < 0:
            errors.append(f"Minimum time {self.min_time_seconds}s cannot be negative")
        
        if self.min_time_seconds > 600:
            warnings.append(f"Minimum time {self.min_time_seconds}s is quite long (>10 minutes)")
        
        # Pump mode validation
        if self.pump_mode == PumpMode.MAINTAIN_VACUUM and self.target_vacuum_bar is None:
            warnings.append("Pump mode 'Maintain Vacuum' requires a vacuum setpoint to be effective")
        
        if self.vacuum_tolerance_bar <= 0:
            errors.append(f"Vacuum tolerance {self.vacuum_tolerance_bar} bar must be positive")
        
        # Validate I/O actions
        for i, io_action in enumerate(self.io_actions):
            action_valid, action_errors = io_action.validate()
            if not action_valid:
                for error in action_errors:
                    errors.append(f"I/O Action {i+1}: {error}")
        
        # Check for recommended I/O actions (warnings, not errors)
        if self.target_vacuum_bar is not None and self.target_vacuum_bar > 0.0:  # Only for vacuum stages
            # Check if vacuum valve is open (needed to connect pump to chamber)
            has_vacuum_valve_open = any(
                action.device_name == "vacuum_valve" and 
                action.value == True and
                action.timing in (IOActionTiming.BEFORE_STAGE, IOActionTiming.START_OF_STAGE)
                for action in self.io_actions
            )
            
            if not has_vacuum_valve_open:
                warnings.append("⚠️ No I/O action opens 'vacuum_valve' - pump won't connect to chamber")
            
            # Check if vent valve is being closed during vacuum
            has_vent_close = any(
                action.device_name == "vent_valve" and 
                action.value == False and
                action.timing in (IOActionTiming.BEFORE_STAGE, IOActionTiming.START_OF_STAGE)
                for action in self.io_actions
            )
            
            if not has_vent_close:
                warnings.append("⚠️ No I/O action closes 'vent_valve' - vacuum will leak to atmosphere")
            
            # Check if vent valve opens at end
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
        
        # Add minimum time
        duration += self.min_time_seconds
        
        # If only time limit is set, use that
        if self.max_time_seconds is not None and self.target_vacuum_bar is None:
            duration += self.max_time_seconds
            return duration
        
        # If only setpoint is set, estimate ramp time
        if self.target_vacuum_bar is not None and self.max_time_seconds is None:
            # Conservative estimate: 10 seconds per 0.1 bar
            ramp_time = self.target_vacuum_bar * 100
            duration += ramp_time
            return duration
        
        # If both are set, use the shorter estimate (since it's OR logic)
        if self.max_time_seconds is not None and self.target_vacuum_bar is not None:
            ramp_time = self.target_vacuum_bar * 100
            duration += min(self.max_time_seconds, ramp_time)
            return duration
        
        # If neither is set, return minimum time only
        return duration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary for serialization."""
        data = {
            "name": self.name,
            "target_vacuum_bar": self.target_vacuum_bar,
            "max_time_seconds": self.max_time_seconds,
            "min_time_seconds": self.min_time_seconds,
            "pump_mode": self.pump_mode.value,
            "vacuum_tolerance_bar": self.vacuum_tolerance_bar,
            "collect_data": self.collect_data,
            "io_actions": [action.to_dict() for action in self.io_actions],
        }
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStage":
        """Create TestStage from dictionary."""
        # Extract and convert I/O actions
        io_actions_data = data.pop("io_actions", [])
        io_actions = [IOAction.from_dict(action_data) for action_data in io_actions_data]
        
        # Convert pump_mode if it's a string
        if "pump_mode" in data and isinstance(data["pump_mode"], str):
            data["pump_mode"] = PumpMode(data["pump_mode"])
        
        # Handle legacy fields (for backward compatibility)
        legacy_mappings = {
            "hold_time_seconds": "max_time_seconds",
            "auto_vent": None,  # Ignore, handled by I/O actions now
            "ramp_rate_bar_per_sec": None,  # Ignore, simplified
            "sample_rate_hz": None,  # Ignore, use global
            "delay_before_seconds": None,  # Ignore, simplified
            "max_force_kg": None,  # Ignore for now
            "max_single_cell_kg": None,  # Ignore for now
        }
        
        for old_key, new_key in legacy_mappings.items():
            if old_key in data:
                if new_key:
                    data[new_key] = data.pop(old_key)
                else:
                    data.pop(old_key)
        
        # Create stage with remaining data
        stage = cls(**data)
        stage.io_actions = io_actions
        
        return stage
    
    def __str__(self) -> str:
        """String representation."""
        conditions = []
        if self.target_vacuum_bar is not None:
            conditions.append(f"{self.target_vacuum_bar} bar")
        if self.max_time_seconds is not None:
            conditions.append(f"{self.max_time_seconds}s max")
        
        condition_str = " OR ".join(conditions) if conditions else "run until stopped"
        return f"{self.name}: {condition_str}"


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
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    author: Optional[str] = None
    
    def __post_init__(self):
        """Initialize metadata if not provided."""
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()
        
        # Ensure pump_mode is PumpMode enum in all stages
        for stage in self.stages:
            if isinstance(stage.pump_mode, str):
                stage.pump_mode = PumpMode(stage.pump_mode)
    
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
            "created_date": self.created_date,
            "modified_date": self.modified_date,
            "author": self.author,
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

