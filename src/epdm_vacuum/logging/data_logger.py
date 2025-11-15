"""
Data Logger - Data Storage and Export

Handles logging of test data to various formats:
- CSV export for easy analysis
- HDF5 format for large datasets
- Metadata management
"""

from typing import Dict, Any, List, Optional
import logging
import csv
from pathlib import Path
from datetime import datetime
import json

import numpy as np

logger = logging.getLogger(__name__)


class DataLogger:
    """
    Manages logging and export of test data.
    
    Supports multiple output formats:
    - CSV for compatibility
    - HDF5 for large datasets
    - JSON for metadata
    """
    
    def __init__(self, output_dir: str = "data"):
        """
        Initialize the data logger.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.current_session: Optional[str] = None
        self.session_metadata: Dict[str, Any] = {}
        
        logger.info(f"DataLogger initialized with output directory: {self.output_dir}")
    
    def start_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start a new logging session.
        
        Args:
            metadata: Optional session metadata
        
        Returns:
            str: Session ID (timestamp-based)
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session = f"test_{timestamp}"
        
        self.session_metadata = {
            "session_id": self.current_session,
            "start_time": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        
        logger.info(f"Started logging session: {self.current_session}")
        return self.current_session
    
    def end_session(self) -> None:
        """End the current logging session."""
        if self.current_session:
            self.session_metadata["end_time"] = datetime.now().isoformat()
            self._save_metadata()
            logger.info(f"Ended logging session: {self.current_session}")
            self.current_session = None
    
    def log_to_csv(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """
        Export data to CSV file.
        
        Args:
            data: List of data dictionaries
            filename: Custom filename (optional)
            metadata: Optional metadata to save in separate JSON file
        
        Returns:
            Path: Path to created CSV file
        """
        if not data:
            logger.warning("No data to export to CSV")
            return None
        
        # Generate filename
        if filename is None:
            session_id = self.current_session or "export"
            filename = f"{session_id}.csv"
        
        filepath = self.output_dir / filename
        
        try:
            # Save metadata to separate JSON file if provided
            if metadata or self.session_metadata:
                metadata_to_save = metadata or self.session_metadata
                metadata_path = Path(filepath).with_suffix('.json')
                try:
                    with open(metadata_path, 'w') as meta_file:
                        json.dump(metadata_to_save, meta_file, indent=2)
                    logger.info(f"Saved metadata to: {metadata_path}")
                except Exception as e:
                    logger.error(f"Failed to save metadata: {e}", exc_info=True)
            
            # Get all unique keys from data
            fieldnames = set()
            for row in data:
                fieldnames.update(row.keys())
            fieldnames = sorted(fieldnames)
            
            # Write CSV (clean, no comments)
            with open(filepath, "w", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            
            logger.info(f"Exported {len(data)} rows to CSV: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}", exc_info=True)
            return None
    
    def log_to_hdf5(
        self,
        data: List[Dict[str, Any]],
        filename: Optional[str] = None,
    ) -> Path:
        """
        Export data to HDF5 file.
        
        Args:
            data: List of data dictionaries
            filename: Custom filename (optional)
        
        Returns:
            Path: Path to created HDF5 file
        """
        if not data:
            logger.warning("No data to export to HDF5")
            return None
        
        try:
            import h5py
        except ImportError:
            logger.error("h5py not available, cannot export to HDF5")
            return None
        
        # Generate filename
        if filename is None:
            session_id = self.current_session or "export"
            filename = f"{session_id}.h5"
        
        filepath = self.output_dir / filename
        
        try:
            # Convert data to structured arrays
            # Get all keys
            keys = set()
            for row in data:
                keys.update(row.keys())
            keys = sorted(keys)
            
            # Create structured arrays for each key
            arrays = {}
            for key in keys:
                values = [row.get(key, np.nan) for row in data]
                arrays[key] = np.array(values)
            
            # Write to HDF5
            with h5py.File(filepath, "w") as hf:
                # Create datasets for each key
                for key, array in arrays.items():
                    hf.create_dataset(key, data=array)
                
                # Add metadata as attributes
                if self.session_metadata:
                    for key, value in self.session_metadata.items():
                        if isinstance(value, (str, int, float)):
                            hf.attrs[key] = value
            
            logger.info(f"Exported {len(data)} rows to HDF5: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error exporting to HDF5: {e}", exc_info=True)
            return None
    
    def _save_metadata(self) -> None:
        """Save session metadata to JSON file."""
        if not self.current_session:
            return
        
        metadata_file = self.output_dir / f"{self.current_session}_metadata.json"
        
        try:
            with open(metadata_file, "w") as f:
                json.dump(self.session_metadata, f, indent=2)
            
            logger.info(f"Saved metadata to {metadata_file}")
            
        except Exception as e:
            logger.error(f"Error saving metadata: {e}", exc_info=True)
    
    def load_metadata(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load metadata for a session.
        
        Args:
            session_id: Session identifier
        
        Returns:
            Dict: Metadata dictionary, or None if not found
        """
        metadata_file = self.output_dir / f"{session_id}_metadata.json"
        
        try:
            if not metadata_file.exists():
                logger.warning(f"Metadata file not found: {metadata_file}")
                return None
            
            with open(metadata_file, "r") as f:
                metadata = json.load(f)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error loading metadata: {e}", exc_info=True)
            return None
    
    def list_sessions(self) -> List[str]:
        """
        List all available session IDs.
        
        Returns:
            List[str]: List of session IDs
        """
        try:
            # Find all metadata files
            metadata_files = list(self.output_dir.glob("*_metadata.json"))
            
            # Extract session IDs
            session_ids = []
            for mf in metadata_files:
                session_id = mf.stem.replace("_metadata", "")
                session_ids.append(session_id)
            
            return sorted(session_ids)
            
        except Exception as e:
            logger.error(f"Error listing sessions: {e}", exc_info=True)
            return []
    
    def get_output_directory(self) -> Path:
        """
        Get the output directory path.
        
        Returns:
            Path: Output directory
        """
        return self.output_dir

