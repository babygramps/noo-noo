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
    
    def validate(self, config_limits: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str]]:
        """
        Validate stage parameters against safety limits.
        
        Args:
            config_limits: Dictionary with safety limits from config
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
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
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
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
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestStage":
        """Create TestStage from dictionary."""
        return cls(**data)
    
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
    
    def validate(self, config_limits: Optional[Dict[str, Any]] = None) -> tuple[bool, List[str]]:
        """
        Validate entire sequence.
        
        Args:
            config_limits: Dictionary with safety limits from config
        
        Returns:
            Tuple of (is_valid, list_of_error_messages)
        """
        errors = []
        
        # Check if sequence has stages
        if not self.stages:
            errors.append("Sequence has no stages")
            return False, errors
        
        # Check if name is valid
        if not self.name or not self.name.strip():
            errors.append("Sequence name cannot be empty")
        
        # Validate each stage
        for i, stage in enumerate(self.stages):
            stage_valid, stage_errors = stage.validate(config_limits)
            if not stage_valid:
                for error in stage_errors:
                    errors.append(f"Stage {i+1}: {error}")
        
        # Check total duration
        total_duration = self.get_estimated_duration()
        if total_duration > 7200:  # 2 hours
            errors.append(f"Total sequence duration {total_duration/60:.1f} minutes exceeds 2 hours")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
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

