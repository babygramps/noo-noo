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

from .sequence import TestSequence, TestStage, SequenceMode

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
            is_valid, errors = sequence.validate(self.config_limits)
            if not is_valid:
                logger.warning(f"Loaded sequence '{sequence.name}' has validation errors:")
                for error in errors:
                    logger.warning(f"  - {error}")
            
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
        is_valid, errors = sequence.validate(self.config_limits)
        if not is_valid:
            logger.error(f"Cannot save invalid sequence '{sequence.name}':")
            for error in errors:
                logger.error(f"  - {error}")
            return False
        
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
        Create a default simple sequence.
        
        Args:
            name: Name for the sequence
        
        Returns:
            TestSequence: Default sequence with one stage
        """
        stage = TestStage(
            name="Default Stage",
            target_vacuum_bar=0.5,
            hold_time_seconds=30.0,
        )
        
        sequence = TestSequence(
            name=name,
            description="Default test sequence",
            mode=SequenceMode.SIMPLE,
            stages=[stage],
        )
        
        logger.info(f"Created default sequence '{name}'")
        return sequence
    
    def create_template_simple(self) -> TestSequence:
        """
        Create a template simple sequence with multiple stages.
        
        Returns:
            TestSequence: Template simple sequence
        """
        stages = [
            TestStage(
                name="Low Vacuum Test",
                target_vacuum_bar=0.3,
                hold_time_seconds=20.0,
            ),
            TestStage(
                name="Medium Vacuum Test",
                target_vacuum_bar=0.5,
                hold_time_seconds=30.0,
            ),
            TestStage(
                name="High Vacuum Test",
                target_vacuum_bar=0.7,
                hold_time_seconds=40.0,
            ),
        ]
        
        sequence = TestSequence(
            name="Simple Multi-Stage Template",
            description="Template for testing at multiple vacuum levels",
            mode=SequenceMode.SIMPLE,
            stages=stages,
        )
        
        logger.info("Created simple template sequence")
        return sequence
    
    def create_template_advanced(self) -> TestSequence:
        """
        Create a template advanced sequence with full parameter control.
        
        Returns:
            TestSequence: Template advanced sequence
        """
        stages = [
            TestStage(
                name="Initial Ramp",
                target_vacuum_bar=0.3,
                hold_time_seconds=15.0,
                ramp_rate_bar_per_sec=0.05,
                sample_rate_hz=10.0,
                collect_data=True,
            ),
            TestStage(
                name="Stabilization Hold",
                target_vacuum_bar=0.5,
                hold_time_seconds=30.0,
                ramp_rate_bar_per_sec=0.1,
                sample_rate_hz=10.0,
                delay_before_seconds=5.0,
                max_force_kg=600.0,
                collect_data=True,
            ),
            TestStage(
                name="Peak Test",
                target_vacuum_bar=0.8,
                hold_time_seconds=20.0,
                ramp_rate_bar_per_sec=0.05,
                sample_rate_hz=20.0,
                delay_before_seconds=5.0,
                max_force_kg=800.0,
                max_single_cell_kg=250.0,
                collect_data=True,
            ),
        ]
        
        sequence = TestSequence(
            name="Advanced Multi-Stage Template",
            description="Template with full parameter control for detailed testing",
            mode=SequenceMode.ADVANCED,
            stages=stages,
            pause_between_stages=True,
        )
        
        logger.info("Created advanced template sequence")
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
                "mode": data.get("mode", "simple"),
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

