"""
Sequence Manager - Load/Save Test Sequences

Manages test sequence files:
- Load sequences from YAML files
- Save sequences to YAML files
- List available sequences
- Validate sequences
- Create default/template sequences
"""

from pathlib import Path
from typing import List, Optional, Dict, Any
import logging
import yaml

from .sequence import TestSequence, TestStage, PumpMode

logger = logging.getLogger(__name__)


class SequenceManager:
    """
    Manages test sequence files.
    
    Handles loading, saving, and listing sequences stored as YAML files
    in the sequences directory.
    """
    
    def __init__(self, sequences_dir: str = "sequences", config_limits: Optional[Dict[str, Any]] = None):
        """
        Initialize the sequence manager.
        
        Args:
            sequences_dir: Directory for sequence files
            config_limits: Safety limits from configuration
        """
        self.sequences_dir = Path(sequences_dir)
        self.sequences_dir.mkdir(parents=True, exist_ok=True)
        self.config_limits = config_limits or {}
        
        logger.info(f"SequenceManager initialized with directory: {self.sequences_dir}")
    
    def load_sequence(self, filename: str) -> Optional[TestSequence]:
        """
        Load a sequence from a YAML file.
        
        Args:
            filename: Name of the sequence file (with or without .yaml extension)
        
        Returns:
            TestSequence object, or None if loading fails
        """
        # Ensure .yaml extension
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.sequences_dir / filename
        
        try:
            if not filepath.exists():
                logger.error(f"Sequence file not found: {filepath}")
                return None
            
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.error(f"Empty sequence file: {filepath}")
                return None
            
            # Create sequence from dictionary
            sequence = TestSequence.from_dict(data)
            
            # Validate the loaded sequence
            is_valid, errors, warnings = sequence.validate(self.config_limits)
            if not is_valid:
                logger.warning(f"Loaded sequence '{sequence.name}' has validation errors:")
                for error in errors:
                    logger.warning(f"  - {error}")
            if warnings:
                logger.info(f"Loaded sequence '{sequence.name}' has validation warnings:")
                for warning in warnings:
                    logger.info(f"  - {warning}")
            
            logger.info(f"Loaded sequence '{sequence.name}' from {filepath}")
            return sequence
            
        except Exception as e:
            logger.error(f"Error loading sequence from {filepath}: {e}", exc_info=True)
            return None
    
    def save_sequence(self, sequence: TestSequence, filename: Optional[str] = None) -> bool:
        """
        Save a sequence to a YAML file.
        
        Args:
            sequence: TestSequence to save
            filename: Optional filename (uses sequence.name if None)
        
        Returns:
            bool: True if saved successfully
        """
        # Validate before saving
        is_valid, errors, warnings = sequence.validate(self.config_limits)
        if not is_valid:
            logger.error(f"Cannot save invalid sequence '{sequence.name}':")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
        if warnings:
            logger.warning(f"Saving sequence '{sequence.name}' with validation warnings:")
            for warning in warnings:
                logger.warning(f"  - {warning}")
        
        # Generate filename
        if filename is None:
            # Sanitize sequence name for filename
            filename = self._sanitize_filename(sequence.name)
        
        # Ensure .yaml extension
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.sequences_dir / filename
        
        try:
            # Update modified date
            sequence.update_modified_date()
            
            # Convert to dictionary
            data = sequence.to_dict()
            
            # Save to YAML
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2, sort_keys=False)
            
            logger.info(f"Saved sequence '{sequence.name}' to {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving sequence to {filepath}: {e}", exc_info=True)
            return False
    
    def list_sequences(self) -> List[str]:
        """
        List all available sequence files.
        
        Returns:
            List of sequence filenames (without path or extension)
        """
        try:
            # Find all YAML files in sequences directory
            yaml_files = list(self.sequences_dir.glob("*.yaml"))
            yaml_files.extend(self.sequences_dir.glob("*.yml"))
            
            # Extract names without extension
            names = [f.stem for f in yaml_files]
            
            logger.info(f"Found {len(names)} sequence files")
            return sorted(names)
            
        except Exception as e:
            logger.error(f"Error listing sequences: {e}", exc_info=True)
            return []
    
    def delete_sequence(self, filename: str) -> bool:
        """
        Delete a sequence file.
        
        Args:
            filename: Name of sequence file to delete
        
        Returns:
            bool: True if deleted successfully
        """
        # Ensure .yaml extension
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.sequences_dir / filename
        
        try:
            if not filepath.exists():
                logger.error(f"Sequence file not found: {filepath}")
                return False
            
            filepath.unlink()
            logger.info(f"Deleted sequence file: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting sequence {filepath}: {e}", exc_info=True)
            return False
    
    def sequence_exists(self, filename: str) -> bool:
        """
        Check if a sequence file exists.
        
        Args:
            filename: Name of sequence file
        
        Returns:
            bool: True if file exists
        """
        # Ensure .yaml extension
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.sequences_dir / filename
        return filepath.exists()
    
    def create_default_sequence(self, name: str = "Default Sequence") -> TestSequence:
        """
        Create a default sequence with one stage.
        
        Args:
            name: Name for the sequence
        
        Returns:
            TestSequence: Default sequence with one stage
        """
        stage = TestStage(
            name="Default Stage",
            target_vacuum_bar=0.5,
            max_time_seconds=30.0,
            pump_mode=PumpMode.MAINTAIN_VACUUM,
        )
        
        sequence = TestSequence(
            name=name,
            description="Default test sequence",
            stages=[stage],
        )
        
        logger.info(f"Created default sequence '{name}'")
        return sequence
    
    def create_template_multi_level(self) -> TestSequence:
        """
        Create a template multi-level sequence.
        
        Returns:
            TestSequence: Template multi-level sequence
        """
        stages = [
            TestStage(
                name="Low Vacuum Test",
                target_vacuum_bar=0.3,
                max_time_seconds=60.0,  # Max 60s or until 0.3 bar reached
                pump_mode=PumpMode.MAINTAIN_VACUUM,
            ),
            TestStage(
                name="Medium Vacuum Test",
                target_vacuum_bar=0.5,
                max_time_seconds=60.0,
                pump_mode=PumpMode.MAINTAIN_VACUUM,
            ),
            TestStage(
                name="High Vacuum Test",
                target_vacuum_bar=0.7,
                max_time_seconds=90.0,
                pump_mode=PumpMode.MAINTAIN_VACUUM,
            ),
        ]
        
        sequence = TestSequence(
            name="Multi-Level Test Template",
            description="Template for testing at multiple vacuum levels with setpoint control",
            stages=stages,
        )
        
        logger.info("Created multi-level template sequence")
        return sequence
    
    def create_template_setpoint_based(self) -> TestSequence:
        """
        Create a template setpoint-based sequence.
        
        Returns:
            TestSequence: Template setpoint-based sequence
        """
        stages = [
            TestStage(
                name="Ramp to Low Vacuum",
                target_vacuum_bar=0.3,
                max_time_seconds=120.0,  # Max 2 minutes to reach
                min_time_seconds=0.0,
                pump_mode=PumpMode.CONTINUOUS,
            ),
            TestStage(
                name="Hold at Medium Vacuum",
                target_vacuum_bar=0.5,
                max_time_seconds=60.0,  # Hold for max 60s at 0.5 bar
                min_time_seconds=10.0,  # Hold at least 10s before moving on
                pump_mode=PumpMode.MAINTAIN_VACUUM,
            ),
            TestStage(
                name="Peak Vacuum Test",
                target_vacuum_bar=0.8,
                max_time_seconds=45.0,
                min_time_seconds=5.0,
                pump_mode=PumpMode.MAINTAIN_VACUUM,
            ),
        ]
        
        sequence = TestSequence(
            name="Setpoint-Based Test Template",
            description="Template demonstrating setpoint-based stage completion",
            stages=stages,
        )
        
        logger.info("Created setpoint-based template sequence")
        return sequence
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize sequence name for use as filename.
        
        Args:
            name: Sequence name
        
        Returns:
            str: Sanitized filename
        """
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        
        # Limit length
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        return sanitized
    
    def get_sequence_info(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a sequence without loading all stages.
        
        Args:
            filename: Name of sequence file
        
        Returns:
            Dict with sequence metadata, or None if error
        """
        # Ensure .yaml extension
        if not filename.endswith('.yaml') and not filename.endswith('.yml'):
            filename = f"{filename}.yaml"
        
        filepath = self.sequences_dir / filename
        
        try:
            if not filepath.exists():
                return None
            
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
            
            # Extract just the metadata
            info = {
                "name": data.get("name", "Unknown"),
                "description": data.get("description", ""),
                "stage_count": len(data.get("stages", [])),
                "created_date": data.get("created_date", ""),
                "modified_date": data.get("modified_date", ""),
                "author": data.get("author", ""),
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting sequence info from {filepath}: {e}")
            return None
    
    def set_config_limits(self, config_limits: Dict[str, Any]) -> None:
        """
        Update configuration limits for validation.
        
        Args:
            config_limits: Dictionary with safety limits
        """
        self.config_limits = config_limits
        logger.info("Updated sequence manager config limits")

