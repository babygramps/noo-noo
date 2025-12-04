"""
Relay State Manager - Global Relay State Tracking

Provides a singleton manager for tracking relay/valve states across the application.
This ensures all components have a consistent view of hardware state.

Usage:
    from epdm_vacuum.daq.relay_state_manager import relay_state_manager
    
    # Set state (typically called by hardware interface)
    relay_state_manager.set_state("relay_module", "vacuum_valve", True)
    
    # Get state
    state = relay_state_manager.get_state("relay_module", "vacuum_valve")
    
    # Get all states
    all_states = relay_state_manager.get_all_states()
    
    # Listen for changes
    relay_state_manager.add_listener(my_callback)
"""

from typing import Dict, Optional, Callable, List, Any
import logging
from threading import Lock

logger = logging.getLogger(__name__)


class RelayStateManager:
    """
    Singleton manager for tracking relay/valve states globally.
    
    Thread-safe state storage with change notification support.
    """
    
    _instance: Optional["RelayStateManager"] = None
    _lock = Lock()
    
    def __new__(cls) -> "RelayStateManager":
        """Ensure singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the relay state manager."""
        if self._initialized:
            return
        
        self._initialized = True
        self._state_lock = Lock()
        
        # State storage: {module_name: {channel_name: bool}}
        self._states: Dict[str, Dict[str, bool]] = {}
        
        # State change listeners: List of callbacks (module, channel, state) -> None
        self._listeners: List[Callable[[str, str, bool], None]] = []
        
        # PyQt signals support (set by GUI components)
        self._qt_signal = None
        
        logger.info("RelayStateManager initialized")
    
    def set_state(
        self, 
        module_name: str, 
        channel_name: str, 
        state: bool,
        notify: bool = True
    ) -> None:
        """
        Set the state of a relay channel.
        
        Args:
            module_name: Name of the relay module
            channel_name: Name of the channel
            state: True for ON/OPEN, False for OFF/CLOSED
            notify: Whether to notify listeners (default True)
        """
        with self._state_lock:
            if module_name not in self._states:
                self._states[module_name] = {}
            
            old_state = self._states[module_name].get(channel_name)
            self._states[module_name][channel_name] = state
            
            # Only notify if state actually changed
            if notify and old_state != state:
                self._notify_listeners(module_name, channel_name, state)
        
        logger.debug(f"Relay state set: {module_name}:{channel_name} = {'ON' if state else 'OFF'}")
    
    def get_state(self, module_name: str, channel_name: str) -> bool:
        """
        Get the state of a relay channel.
        
        Args:
            module_name: Name of the relay module
            channel_name: Name of the channel
        
        Returns:
            bool: Current state (False if unknown)
        """
        with self._state_lock:
            return self._states.get(module_name, {}).get(channel_name, False)
    
    def get_module_states(self, module_name: str) -> Dict[str, bool]:
        """
        Get all channel states for a module.
        
        Args:
            module_name: Name of the relay module
        
        Returns:
            Dict mapping channel names to states
        """
        with self._state_lock:
            return dict(self._states.get(module_name, {}))
    
    def get_all_states(self) -> Dict[str, Dict[str, bool]]:
        """
        Get all relay states.
        
        Returns:
            Dict: {module_name: {channel_name: state}}
        """
        with self._state_lock:
            return {
                mod: dict(channels) 
                for mod, channels in self._states.items()
            }
    
    def get_channel_by_role(self, role: str) -> Optional[tuple]:
        """
        Find a channel by its device role.
        
        Args:
            role: Device role (e.g., "vacuum_pump", "vent_valve", "vacuum_valve")
        
        Returns:
            Tuple of (module_name, channel_name) or None if not found
        """
        # This requires config access - to be implemented if needed
        # For now, return None
        return None
    
    def set_all_off(self, module_name: Optional[str] = None) -> None:
        """
        Turn off all relays.
        
        Args:
            module_name: Optional module to target (all modules if None)
        """
        with self._state_lock:
            if module_name:
                if module_name in self._states:
                    for channel_name in self._states[module_name]:
                        self._states[module_name][channel_name] = False
                        self._notify_listeners(module_name, channel_name, False)
            else:
                for mod_name, channels in self._states.items():
                    for channel_name in channels:
                        channels[channel_name] = False
                        self._notify_listeners(mod_name, channel_name, False)
        
        logger.info(f"All relays set to OFF" + (f" for module {module_name}" if module_name else ""))
    
    def add_listener(self, callback: Callable[[str, str, bool], None]) -> None:
        """
        Add a state change listener.
        
        Args:
            callback: Function(module_name, channel_name, state) called on state change
        """
        if callback not in self._listeners:
            self._listeners.append(callback)
            logger.debug(f"Added relay state listener: {callback}")
    
    def remove_listener(self, callback: Callable[[str, str, bool], None]) -> None:
        """
        Remove a state change listener.
        
        Args:
            callback: The callback to remove
        """
        if callback in self._listeners:
            self._listeners.remove(callback)
            logger.debug(f"Removed relay state listener: {callback}")
    
    def set_qt_signal(self, signal) -> None:
        """
        Set a PyQt signal to emit on state changes.
        
        Args:
            signal: PyQt signal with signature (str, str, bool)
        """
        self._qt_signal = signal
        logger.debug("Qt signal registered for relay state changes")
    
    def _notify_listeners(self, module_name: str, channel_name: str, state: bool) -> None:
        """Notify all listeners of a state change."""
        # Call registered callbacks
        for listener in self._listeners:
            try:
                listener(module_name, channel_name, state)
            except Exception as e:
                logger.error(f"Error in relay state listener: {e}")
        
        # Emit Qt signal if registered
        if self._qt_signal:
            try:
                self._qt_signal.emit(module_name, channel_name, state)
            except Exception as e:
                logger.error(f"Error emitting Qt signal: {e}")
    
    def sync_from_hardware(self, hardware_states: Dict[str, Dict[str, bool]]) -> None:
        """
        Synchronize state from hardware reading.
        
        Called by hardware interface to update tracked state to match actual hardware.
        
        Args:
            hardware_states: Dict of {module_name: {channel_name: state}}
        """
        with self._state_lock:
            for module_name, channels in hardware_states.items():
                if module_name not in self._states:
                    self._states[module_name] = {}
                
                for channel_name, state in channels.items():
                    old_state = self._states[module_name].get(channel_name)
                    self._states[module_name][channel_name] = state
                    
                    # Notify if state differs from tracked
                    if old_state != state:
                        self._notify_listeners(module_name, channel_name, state)
        
        logger.debug(f"Synced relay states from hardware: {hardware_states}")
    
    def clear(self) -> None:
        """Clear all tracked states (for testing/reset)."""
        with self._state_lock:
            self._states.clear()
        logger.debug("Relay state manager cleared")


# Global singleton instance
relay_state_manager = RelayStateManager()

