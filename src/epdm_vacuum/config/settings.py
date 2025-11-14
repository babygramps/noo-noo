"""
Settings - Configuration Management

Loads and manages configuration from:
- YAML files
- Environment variables
- Default values
"""

from typing import Dict, Any, Optional
import logging
from pathlib import Path
import os

import yaml
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class Settings:
    """
    Application settings manager.
    
    Loads configuration from multiple sources with precedence:
    1. Environment variables (highest priority)
    2. YAML configuration file
    3. Default values (lowest priority)
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize settings.
        
        Args:
            config_file: Path to YAML config file (optional)
        """
        self.config_file = config_file
        self.config: Dict[str, Any] = {}
        
        # Load environment variables from .env file if present
        load_dotenv()
        
        # Load configuration
        self._load_defaults()
        
        if config_file:
            self._load_yaml(config_file)
        
        self._load_environment()
        
        logger.info("Settings initialized")
    
    def _load_defaults(self) -> None:
        """Load default configuration values."""
        self.config = {
            "hardware": {
                "widgetlords": {
                    "enabled": True,
                    "pressure_channel": 0,
                    "pump_relay": 0,
                },
                "modbus": {
                    "enabled": True,
                    "port": "/dev/ttyUSB0",
                    "baudrate": 9600,
                    "slave_address": 1,
                    "timeout": 1.0,
                },
            },
            "pressure_sensor": {
                "voltage_min": 0.0,
                "voltage_max": 10.0,
                "pressure_min_psi": 0.0,
                "pressure_max_psi": 30.0,
            },
            "safety": {
                "max_vacuum_bar": 1.0,
                "max_force_kg": 800.0,
                "max_single_cell_kg": 250.0,
                "emergency_stop_enabled": True,
            },
            "test": {
                "default_target_vacuum_bar": 0.5,
                "default_hold_time_seconds": 30,
                "sample_rate_hz": 10.0,
            },
            "logging": {
                "output_dir": "data",
                "log_level": "INFO",
                "buffer_size": 10000,
            },
            "api": {
                "enabled": False,
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
            },
        }
        
        logger.info("Default configuration loaded")
    
    def _load_yaml(self, filepath: str) -> None:
        """
        Load configuration from YAML file.
        
        Args:
            filepath: Path to YAML file
        """
        try:
            path = Path(filepath)
            if not path.exists():
                logger.warning(f"Config file not found: {filepath}")
                return
            
            with open(path, "r") as f:
                yaml_config = yaml.safe_load(f)
            
            if yaml_config:
                self._merge_config(yaml_config)
                logger.info(f"Configuration loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"Error loading YAML config: {e}", exc_info=True)
    
    def _load_environment(self) -> None:
        """Load configuration from environment variables."""
        # Map environment variables to config keys
        env_mappings = {
            "MODBUS_PORT": ("hardware", "modbus", "port"),
            "MODBUS_BAUDRATE": ("hardware", "modbus", "baudrate"),
            "MODBUS_SLAVE_ADDRESS": ("hardware", "modbus", "slave_address"),
            "MAX_VACUUM_BAR": ("safety", "max_vacuum_bar"),
            "MAX_FORCE_KG": ("safety", "max_force_kg"),
            "SAMPLE_RATE_HZ": ("test", "sample_rate_hz"),
            "LOG_LEVEL": ("logging", "log_level"),
            "API_HOST": ("api", "host"),
            "API_PORT": ("api", "port"),
            "API_DEBUG": ("api", "debug"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested(config_path, value)
                logger.debug(f"Loaded from environment: {env_var}")
    
    def _merge_config(self, new_config: Dict[str, Any]) -> None:
        """
        Merge new configuration into existing config.
        
        Args:
            new_config: Configuration dictionary to merge
        """
        self._deep_merge(self.config, new_config)
    
    def _deep_merge(self, base: Dict, update: Dict) -> None:
        """
        Deep merge two dictionaries.
        
        Args:
            base: Base dictionary (modified in place)
            update: Dictionary with updates
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value
    
    def _set_nested(self, path: tuple, value: Any) -> None:
        """
        Set a nested configuration value.
        
        Args:
            path: Tuple of keys representing path
            value: Value to set
        """
        current = self.config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        # Type conversion
        if isinstance(current.get(path[-1]), (int, float)):
            try:
                if isinstance(current[path[-1]], int):
                    value = int(value)
                else:
                    value = float(value)
            except ValueError:
                pass
        elif isinstance(current.get(path[-1]), bool):
            value = value.lower() in ("true", "1", "yes")
        
        current[path[-1]] = value
    
    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Get a configuration value by path.
        
        Args:
            *keys: Path to configuration value
            default: Default value if not found
        
        Returns:
            Configuration value or default
        """
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current
    
    def set(self, *keys: str, value: Any) -> None:
        """
        Set a configuration value by path.
        
        Args:
            *keys: Path to configuration value
            value: Value to set
        """
        if len(keys) < 1:
            return
        
        current = self.config
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def save(self, filepath: Optional[str] = None) -> bool:
        """
        Save configuration to YAML file.
        
        Args:
            filepath: Path to save file (uses self.config_file if None)
        
        Returns:
            bool: True if saved successfully
        """
        save_path = filepath or self.config_file
        if not save_path:
            logger.error("No filepath specified for saving config")
            return False
        
        try:
            path = Path(save_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            return False
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration.
        
        Returns:
            Dict: Complete configuration
        """
        return self.config.copy()


# Global settings instance
_settings: Optional[Settings] = None


def get_settings(config_file: Optional[str] = None) -> Settings:
    """
    Get global settings instance.
    
    Args:
        config_file: Path to config file (only used on first call)
    
    Returns:
        Settings: Global settings instance
    """
    global _settings
    if _settings is None:
        _settings = Settings(config_file)
    return _settings

