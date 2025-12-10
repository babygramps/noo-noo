"""
Data Buffer - Real-time Data Buffering

Manages circular buffers for real-time data:
- Efficient memory management
- Thread-safe operations
- Configurable buffer sizes
"""

from typing import Dict, Any, List, Optional
import logging
from collections import deque
from threading import Lock
import time

import numpy as np

logger = logging.getLogger(__name__)


class DataBuffer:
    """
    Circular buffer for real-time sensor data.
    
    Provides thread-safe buffering of incoming sensor data
    with automatic management of buffer size.
    """
    
    def __init__(self, max_size: int = 10000):
        """
        Initialize the data buffer.
        
        Args:
            max_size: Maximum number of data points to store
        """
        self.max_size = max_size
        self.buffer: deque = deque(maxlen=max_size)
        self.lock = Lock()
        
        self.start_time: Optional[float] = None
        self.data_count = 0
        
        logger.info(f"DataBuffer initialized with max size: {max_size}")
    
    def append(self, data: Dict[str, Any]) -> None:
        """
        Add a data point to the buffer.
        
        Args:
            data: Dictionary containing sensor readings
        """
        with self.lock:
            # Add timestamp if not present
            if "timestamp" not in data:
                data["timestamp"] = time.time()
            
            # Set start time on first data point
            if self.start_time is None:
                self.start_time = data["timestamp"]
            
            self.buffer.append(data.copy())
            self.data_count += 1
    
    def append_batch(self, data_list: List[Dict[str, Any]]) -> None:
        """
        Add multiple data points to the buffer.
        
        Args:
            data_list: List of data dictionaries
        """
        with self.lock:
            for data in data_list:
                if "timestamp" not in data:
                    data["timestamp"] = time.time()
                
                if self.start_time is None:
                    self.start_time = data["timestamp"]
                
                self.buffer.append(data.copy())
                self.data_count += 1
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Get all data points in the buffer.
        
        Returns:
            List[Dict]: Copy of all data points
        """
        with self.lock:
            return list(self.buffer)
    
    def get_latest(self, n: int = 1) -> List[Dict[str, Any]]:
        """
        Get the latest N data points.
        
        Args:
            n: Number of points to retrieve
        
        Returns:
            List[Dict]: Latest N data points
        """
        with self.lock:
            if n >= len(self.buffer):
                return list(self.buffer)
            else:
                return list(self.buffer)[-n:]
    
    def get_last(self) -> Optional[Dict[str, Any]]:
        """
        Get the most recent data point.
        
        Returns:
            Dict: Most recent data point, or None if buffer is empty
        """
        with self.lock:
            if len(self.buffer) > 0:
                return self.buffer[-1].copy()
            return None
    
    def get_range(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get data points within a time range.
        
        Args:
            start_time: Start timestamp (inclusive)
            end_time: End timestamp (inclusive)
        
        Returns:
            List[Dict]: Data points in range
        """
        with self.lock:
            result = []
            for data in self.buffer:
                timestamp = data.get("timestamp", 0)
                
                if start_time is not None and timestamp < start_time:
                    continue
                
                if end_time is not None and timestamp > end_time:
                    continue
                
                result.append(data)
            
            return result
    
    def get_column(self, key: str) -> List[Any]:
        """
        Get all values for a specific key.
        
        Args:
            key: Data key to extract
        
        Returns:
            List: All values for the key
        """
        with self.lock:
            return [data.get(key) for data in self.buffer if key in data]
    
    def get_array(self, key: str) -> np.ndarray:
        """
        Get values for a key as numpy array.
        
        Args:
            key: Data key to extract
        
        Returns:
            np.ndarray: Array of values
        """
        values = self.get_column(key)
        return np.array(values)
    
    def clear(self) -> None:
        """Clear all data from the buffer."""
        with self.lock:
            self.buffer.clear()
            self.start_time = None
            logger.info("Buffer cleared")
    
    def size(self) -> int:
        """
        Get current number of data points in buffer.
        
        Returns:
            int: Number of data points
        """
        with self.lock:
            return len(self.buffer)
    
    def is_full(self) -> bool:
        """
        Check if buffer is at maximum capacity.
        
        Returns:
            bool: True if buffer is full
        """
        with self.lock:
            return len(self.buffer) >= self.max_size
    
    def get_statistics(self, key: str) -> Optional[Dict[str, float]]:
        """
        Get statistics for a specific data key.
        
        Args:
            key: Data key to analyze
        
        Returns:
            Dict: Statistics (min, max, mean, std), or None if no data
        """
        array = self.get_array(key)
        
        if len(array) == 0:
            return None
        
        return {
            "min": float(np.min(array)),
            "max": float(np.max(array)),
            "mean": float(np.mean(array)),
            "std": float(np.std(array)),
            "count": len(array),
        }
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get buffer information.
        
        Returns:
            Dict: Buffer status information
        """
        with self.lock:
            return {
                "max_size": self.max_size,
                "current_size": len(self.buffer),
                "total_count": self.data_count,
                "start_time": self.start_time,
                "is_full": len(self.buffer) >= self.max_size,
            }
    
    def downsample(self, factor: int) -> List[Dict[str, Any]]:
        """
        Get downsampled data (every Nth point).
        
        Args:
            factor: Downsample factor (e.g., 10 = every 10th point)
        
        Returns:
            List[Dict]: Downsampled data
        """
        with self.lock:
            return [self.buffer[i] for i in range(0, len(self.buffer), factor)]
    
    def export_to_dict(self) -> Dict[str, List[Any]]:
        """
        Export buffer data as dictionary of lists.
        
        Returns:
            Dict: Dictionary with keys mapped to value lists
        """
        with self.lock:
            if len(self.buffer) == 0:
                return {}
            
            # Get all unique keys
            keys = set()
            for data in self.buffer:
                keys.update(data.keys())
            
            # Build dictionary
            result = {key: [] for key in keys}
            
            for data in self.buffer:
                for key in keys:
                    result[key].append(data.get(key, None))
            
            return result

