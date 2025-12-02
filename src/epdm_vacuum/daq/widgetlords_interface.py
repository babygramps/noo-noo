"""
WidgetLords Interface - SPI Communication

Handles communication with WidgetLords PI-SPI-DIN modules via SPI:
- PI-SPI-DIN-4KO: 4-channel relay output (SPDT, 2A AC)
- PI-SPI-DIN-8AI: 8-channel analog input (0-10V / 4-20mA)
- PI-SPI-DIN-8DI: 8-channel digital input
- PI-SPI-DIN-4AO: 4-channel analog output

Supports multiple modules on different chip enables (CE0-CE4) and
stacking of 4KO modules using addresses 0-3.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging

from .hardware_interface import HardwareInterface

logger = logging.getLogger(__name__)


class ChipEnable(Enum):
    """Chip Enable lines for SPI communication."""
    CE0 = 0
    CE1 = 1
    CE2 = 2
    CE3 = 3
    CE4 = 4


class ModuleType(Enum):
    """Widgetlords module types."""
    RELAY_4KO = "PI-SPI-DIN-4KO"
    ANALOG_IN_8AI = "PI-SPI-DIN-8AI"
    DIGITAL_IN_8DI = "PI-SPI-DIN-8DI"
    ANALOG_OUT_4AO = "PI-SPI-DIN-4AO"


@dataclass
class ChannelConfig:
    """Configuration for a single channel."""
    channel: int
    name: str = ""
    enabled: bool = True
    description: str = ""
    # Analog input span configuration
    input_type: str = "4-20mA"  # "4-20mA", "0-10V", "0-5V"
    low_input: float = 4.0      # Low span input value (mA or V)
    low_output: float = 0.0     # Low span output (engineering units)
    high_input: float = 20.0    # High span input value (mA or V)
    high_output: float = 100.0  # High span output (engineering units)
    units: str = ""             # Engineering units label (e.g., "PSI", "bar")
    # Legacy analog fields (for backward compatibility)
    min_value: float = 0.0
    max_value: float = 10.0
    # Digital input specific
    inverted: bool = False


@dataclass
class SPIModuleConfig:
    """Configuration for an SPI module."""
    name: str
    module_type: str
    chip_enable: str
    address: int = 0
    channels: List[ChannelConfig] = field(default_factory=list)


class SPIModule:
    """
    Base class for SPI modules.
    
    Provides common functionality for all Widgetlords modules.
    """
    
    def __init__(self, config: SPIModuleConfig):
        """Initialize the SPI module."""
        self.config = config
        self.name = config.name
        self.module_type = config.module_type
        self.chip_enable = self._parse_chip_enable(config.chip_enable)
        self.address = config.address
        self.channels = config.channels
        self._hardware = None
        self._initialized = False
    
    def _parse_chip_enable(self, ce_str: str) -> ChipEnable:
        """Parse chip enable string to enum."""
        ce_map = {
            "CE0": ChipEnable.CE0,
            "CE1": ChipEnable.CE1,
            "CE2": ChipEnable.CE2,
            "CE3": ChipEnable.CE3,
            "CE4": ChipEnable.CE4,
        }
        return ce_map.get(ce_str, ChipEnable.CE0)
    
    def initialize(self) -> bool:
        """Initialize the hardware module."""
        raise NotImplementedError("Subclasses must implement initialize()")
    
    def shutdown(self) -> None:
        """Shutdown the hardware module."""
        self._initialized = False
        self._hardware = None
    
    @property
    def is_initialized(self) -> bool:
        """Check if module is initialized."""
        return self._initialized


class RelayModule(SPIModule):
    """
    PI-SPI-DIN-4KO Relay Output Module.
    
    4 SPDT relay outputs with 2A AC/DC rating.
    Supports stacking up to 4 modules per chip enable using addresses 0-3.
    """
    
    def __init__(self, config: SPIModuleConfig):
        super().__init__(config)
        self._relay_states = [False] * 4
    
    def initialize(self) -> bool:
        """Initialize the 4KO relay module."""
        try:
            logger.info(f"Initializing relay module '{self.name}' on {self.config.chip_enable} address {self.address}")
            
            # Try to import widgetlords library
            try:
                from widgetlords.pi_spi_din import Mod4KO, ChipEnable as WLChipEnable
                
                # Map our ChipEnable to widgetlords ChipEnable
                wl_ce_map = {
                    ChipEnable.CE0: WLChipEnable.CE0,
                    ChipEnable.CE1: WLChipEnable.CE1,
                    ChipEnable.CE2: WLChipEnable.CE2,
                    ChipEnable.CE3: WLChipEnable.CE3,
                    ChipEnable.CE4: WLChipEnable.CE4,
                }
                
                wl_ce = wl_ce_map.get(self.chip_enable, WLChipEnable.CE0)
                self._hardware = Mod4KO(wl_ce, self.address)
                self._initialized = True
                logger.info(f"Relay module '{self.name}' initialized successfully")
                
            except ImportError:
                logger.warning(f"widgetlords library not available - relay module '{self.name}' in mock mode")
                self._initialized = True  # Mock mode
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize relay module '{self.name}': {e}", exc_info=True)
            return False
    
    def write_all(self, states: int) -> bool:
        """
        Write all relay states as a bitmask.
        
        Args:
            states: Bitmask of relay states (0x0F = all on)
        
        Returns:
            bool: True if successful
        """
        try:
            if self._hardware:
                self._hardware.write(states)
            
            # Update internal state tracking
            for i in range(4):
                self._relay_states[i] = bool(states & (1 << i))
            
            logger.debug(f"Relay module '{self.name}': wrote 0x{states:02X}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write relay states: {e}")
            return False
    
    def write_single(self, relay: int, state: bool) -> bool:
        """
        Write a single relay state.
        
        Args:
            relay: Relay number (0-3)
            state: True for ON, False for OFF
        
        Returns:
            bool: True if successful
        """
        if not 0 <= relay <= 3:
            logger.error(f"Invalid relay number: {relay}")
            return False
        
        try:
            if self._hardware:
                self._hardware.write_single(relay, 1 if state else 0)
            
            self._relay_states[relay] = state
            logger.debug(f"Relay module '{self.name}': K{relay+1} = {'ON' if state else 'OFF'}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write relay {relay}: {e}")
            return False
    
    def write_by_name(self, channel_name: str, state: bool) -> bool:
        """
        Write a relay state by channel name.
        
        Args:
            channel_name: Name of the channel (from config)
            state: True for ON, False for OFF
        
        Returns:
            bool: True if successful
        """
        for ch in self.channels:
            if ch.name == channel_name and ch.enabled:
                return self.write_single(ch.channel, state)
        
        logger.warning(f"Channel '{channel_name}' not found in relay module '{self.name}'")
        return False
    
    def get_state(self, relay: int) -> bool:
        """Get cached relay state."""
        if 0 <= relay <= 3:
            return self._relay_states[relay]
        return False
    
    def get_all_states(self) -> Dict[str, bool]:
        """Get all relay states by channel name."""
        states = {}
        for ch in self.channels:
            if ch.enabled and 0 <= ch.channel <= 3:
                states[ch.name] = self._relay_states[ch.channel]
        return states


class AnalogInputModule(SPIModule):
    """
    PI-SPI-DIN-8AI Analog Input Module.
    
    8 analog input channels, 0-10V or 4-20mA (jumper selectable).
    Supports span scaling to convert raw readings to engineering units.
    """
    
    def __init__(self, config: SPIModuleConfig):
        super().__init__(config)
        self._last_readings = [0.0] * 8
    
    def initialize(self) -> bool:
        """Initialize the 8AI analog input module."""
        try:
            logger.info(f"Initializing analog input module '{self.name}' on {self.config.chip_enable}")
            
            # Log channel configuration for debugging
            for ch in self.channels:
                if ch.enabled:
                    logger.info(f"  Channel {ch.channel} '{ch.name}': {ch.input_type}, "
                              f"span {ch.low_input}-{ch.high_input} -> {ch.low_output}-{ch.high_output} {ch.units}")
            
            try:
                from widgetlords.pi_spi_din import Mod8AI, ChipEnable as WLChipEnable
                
                wl_ce_map = {
                    ChipEnable.CE0: WLChipEnable.CE0,
                    ChipEnable.CE1: WLChipEnable.CE1,
                    ChipEnable.CE2: WLChipEnable.CE2,
                    ChipEnable.CE3: WLChipEnable.CE3,
                    ChipEnable.CE4: WLChipEnable.CE4,
                }
                
                wl_ce = wl_ce_map.get(self.chip_enable, WLChipEnable.CE0)
                logger.info(f"Creating Mod8AI with ChipEnable={wl_ce} (our enum: {self.chip_enable})")
                logger.info(f"  This matches: inputs=Mod8AI(ChipEnable.{self.chip_enable.name})")
                self._hardware = Mod8AI(wl_ce)
                self._initialized = True
                logger.info(f"Analog input module '{self.name}' initialized successfully with REAL hardware")
                
                # Test read to verify hardware is working - read all enabled channels
                logger.info(f"  Performing test reads on enabled channels...")
                logger.info(f"  NOTE: MCP3208 returns raw ADC counts (0-4095), converted to voltage (0-10V)")
                for ch in self.channels:
                    if ch.enabled:
                        try:
                            raw_counts = self._hardware.read_single(ch.channel)
                            voltage = (raw_counts / 4095.0) * 10.0
                            logger.info(f"    Channel {ch.channel} '{ch.name}': raw_counts={raw_counts}, voltage={voltage:.4f}V")
                        except Exception as test_e:
                            logger.warning(f"    Channel {ch.channel} '{ch.name}' test read FAILED: {test_e}")
                
            except ImportError as ie:
                logger.warning(f"widgetlords library not available - analog module '{self.name}' in mock mode: {ie}")
                self._initialized = True
            except Exception as hw_e:
                logger.error(f"Hardware init error for '{self.name}': {hw_e}", exc_info=True)
                self._initialized = True  # Allow mock mode on hardware error
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analog module '{self.name}': {e}", exc_info=True)
            return False
    
    def _apply_span_scaling(self, raw_value: float, ch_config: ChannelConfig) -> float:
        """
        Apply span scaling to convert raw input to engineering units.
        
        The PI-SPI-DIN-8AI module returns voltage (0-10V).
        For 4-20mA mode, voltage is converted to current using Ohm's law
        with the calibrated sense resistor value.
        
        Args:
            raw_value: Raw voltage reading from module (0-10V)
            ch_config: Channel configuration with span settings
        
        Returns:
            Scaled value in engineering units
        """
        # Track scaling calls for verbose logging
        if not hasattr(self, '_scale_count'):
            self._scale_count = 0
        self._scale_count += 1
        verbose = self._scale_count <= 10
        
        # Map raw voltage to input value based on input type
        input_type = ch_config.input_type
        
        if input_type == "4-20mA":
            # PI-SPI-DIN-8AI: Convert voltage to mA using Ohm's law
            # Calibrated sense resistor: 454Ω (measured with multimeter)
            SENSE_RESISTOR_OHMS = 454.0
            input_value = (raw_value / SENSE_RESISTOR_OHMS) * 1000.0  # mA
            if verbose:
                logger.info(f"  [Span #{self._scale_count}] 4-20mA: {raw_value:.4f}V / {SENSE_RESISTOR_OHMS}Ω = {input_value:.2f}mA")
        elif input_type == "0-5V":
            input_value = raw_value
            if verbose:
                logger.info(f"  [Span #{self._scale_count}] 0-5V: {raw_value:.4f}V -> {input_value:.4f}V")
        else:  # "0-10V" or default
            input_value = raw_value
            if verbose:
                logger.info(f"  [Span #{self._scale_count}] 0-10V: {raw_value:.4f}V -> {input_value:.4f}V")
        
        # Apply span scaling: linear interpolation
        low_in = ch_config.low_input
        high_in = ch_config.high_input
        low_out = ch_config.low_output
        high_out = ch_config.high_output
        
        # Avoid division by zero
        if abs(high_in - low_in) < 0.001:
            logger.warning(f"Span scaling: low_in ~= high_in ({low_in}), returning low_out={low_out}")
            return low_out
        
        # Linear interpolation
        scaled = low_out + (input_value - low_in) * (high_out - low_out) / (high_in - low_in)
        if verbose:
            logger.info(f"  [Span #{self._scale_count}] Scaling: {input_value:.2f} in [{low_in}, {high_in}] -> {scaled:.4f} {ch_config.units}")
        return scaled
    
    def read_channel(self, channel: int) -> Optional[float]:
        """
        Read a single analog channel and convert to voltage.
        
        The MCP3208 ADC returns raw counts (0-4095 for 12-bit).
        This method converts to voltage (0-10V range).
        
        Args:
            channel: Channel number (0-7)
        
        Returns:
            float: Voltage reading (0-10V), or None on error
        """
        if not 0 <= channel <= 7:
            logger.error(f"Invalid analog channel: {channel}")
            return None
        
        try:
            if self._hardware:
                # read_single() returns RAW ADC COUNTS (0-4095 for MCP3208 12-bit ADC)
                raw_counts = self._hardware.read_single(channel)
                
                # Convert raw counts to voltage
                # MCP3208 is 12-bit (0-4095), reference voltage is typically 10V for 0-10V input
                # For PI-SPI-DIN-8AI: 0 counts = 0V, 4095 counts = 10V
                voltage = (raw_counts / 4095.0) * 10.0
                
                # Log at INFO level for first few reads to help debug
                if not hasattr(self, '_read_count'):
                    self._read_count = 0
                self._read_count += 1
                if self._read_count <= 20:
                    logger.info(f"Analog ch{channel}: raw_counts={raw_counts}, voltage={voltage:.4f}V (read #{self._read_count})")
                else:
                    logger.debug(f"Analog module '{self.name}' ch{channel}: counts={raw_counts}, V={voltage:.4f}")
            else:
                voltage = 0.0  # Mock mode
                logger.debug(f"Analog module '{self.name}' ch{channel} MOCK read: {voltage:.4f}V")
            
            self._last_readings[channel] = voltage
            return voltage
            
        except Exception as e:
            logger.error(f"Failed to read analog channel {channel}: {e}", exc_info=True)
            return None
    
    def read_by_name(self, channel_name: str, scaled: bool = True) -> Optional[float]:
        """
        Read an analog channel by name.
        
        Args:
            channel_name: Name of the channel (from config)
            scaled: If True, apply span scaling to engineering units
        
        Returns:
            float: Reading (scaled or raw voltage), or None if not found
        """
        for ch in self.channels:
            if ch.name == channel_name and ch.enabled:
                raw_voltage = self.read_channel(ch.channel)
                if raw_voltage is None:
                    return None
                if scaled:
                    return self._apply_span_scaling(raw_voltage, ch)
                return raw_voltage
        
        logger.warning(f"Channel '{channel_name}' not found in analog module '{self.name}'")
        return None
    
    def read_all_enabled(self, scaled: bool = True) -> Dict[str, float]:
        """
        Read all enabled channels by name.
        
        Args:
            scaled: If True, apply span scaling to engineering units
        
        Returns:
            Dict mapping channel names to values
        """
        readings = {}
        for ch in self.channels:
            if ch.enabled and 0 <= ch.channel <= 7:
                raw_voltage = self.read_channel(ch.channel)
                if raw_voltage is not None:
                    if scaled:
                        scaled_value = self._apply_span_scaling(raw_voltage, ch)
                        readings[ch.name] = scaled_value
                        logger.debug(f"Channel '{ch.name}': raw={raw_voltage:.4f}V -> scaled={scaled_value:.4f} {ch.units}")
                    else:
                        readings[ch.name] = raw_voltage
        
        if not readings:
            logger.warning(f"Analog module '{self.name}': No enabled channels found or all reads failed!")
            logger.warning(f"  Channels: {[(ch.channel, ch.name, ch.enabled) for ch in self.channels]}")
        
        return readings
    
    def get_channel_units(self, channel_name: str) -> str:
        """Get the engineering units for a channel."""
        for ch in self.channels:
            if ch.name == channel_name:
                return ch.units
        return ""


class DigitalInputModule(SPIModule):
    """
    PI-SPI-DIN-8DI Digital Input Module.
    
    8 digital input channels, 12-24V compatible.
    """
    
    def __init__(self, config: SPIModuleConfig):
        super().__init__(config)
        self._last_states = [False] * 8
    
    def initialize(self) -> bool:
        """Initialize the 8DI digital input module."""
        try:
            logger.info(f"Initializing digital input module '{self.name}' on {self.config.chip_enable}")
            
            try:
                from widgetlords.pi_spi_din import Mod8DI, ChipEnable as WLChipEnable
                
                wl_ce_map = {
                    ChipEnable.CE0: WLChipEnable.CE0,
                    ChipEnable.CE1: WLChipEnable.CE1,
                    ChipEnable.CE2: WLChipEnable.CE2,
                    ChipEnable.CE3: WLChipEnable.CE3,
                    ChipEnable.CE4: WLChipEnable.CE4,
                }
                
                wl_ce = wl_ce_map.get(self.chip_enable, WLChipEnable.CE0)
                self._hardware = Mod8DI(wl_ce)
                self._initialized = True
                logger.info(f"Digital input module '{self.name}' initialized successfully")
                
            except ImportError:
                logger.warning(f"widgetlords library not available - digital input module '{self.name}' in mock mode")
                self._initialized = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize digital input module '{self.name}': {e}", exc_info=True)
            return False
    
    def read_channel(self, channel: int) -> Optional[bool]:
        """
        Read a single digital input channel.
        
        Args:
            channel: Channel number (0-7)
        
        Returns:
            bool: Input state, or None on error
        """
        if not 0 <= channel <= 7:
            logger.error(f"Invalid digital channel: {channel}")
            return None
        
        try:
            if self._hardware:
                state = bool(self._hardware.read() & (1 << channel))
            else:
                state = False  # Mock mode
            
            # Apply inversion if configured
            ch_config = next((c for c in self.channels if c.channel == channel), None)
            if ch_config and ch_config.inverted:
                state = not state
            
            self._last_states[channel] = state
            return state
            
        except Exception as e:
            logger.error(f"Failed to read digital channel {channel}: {e}")
            return None
    
    def read_all(self) -> int:
        """Read all channels as a bitmask."""
        try:
            if self._hardware:
                return self._hardware.read()
            return 0
        except Exception as e:
            logger.error(f"Failed to read digital inputs: {e}")
            return 0
    
    def read_all_enabled(self) -> Dict[str, bool]:
        """Read all enabled channels by name."""
        readings = {}
        for ch in self.channels:
            if ch.enabled and 0 <= ch.channel <= 7:
                state = self.read_channel(ch.channel)
                if state is not None:
                    readings[ch.name] = state
        return readings


class AnalogOutputModule(SPIModule):
    """
    PI-SPI-DIN-4AO Analog Output Module.
    
    4 analog output channels, 0-10V.
    """
    
    def __init__(self, config: SPIModuleConfig):
        super().__init__(config)
        self._last_outputs = [0.0] * 4
    
    def initialize(self) -> bool:
        """Initialize the 4AO analog output module."""
        try:
            logger.info(f"Initializing analog output module '{self.name}' on {self.config.chip_enable}")
            
            try:
                from widgetlords.pi_spi_din import Mod4AO, ChipEnable as WLChipEnable
                
                wl_ce_map = {
                    ChipEnable.CE0: WLChipEnable.CE0,
                    ChipEnable.CE1: WLChipEnable.CE1,
                    ChipEnable.CE2: WLChipEnable.CE2,
                    ChipEnable.CE3: WLChipEnable.CE3,
                    ChipEnable.CE4: WLChipEnable.CE4,
                }
                
                wl_ce = wl_ce_map.get(self.chip_enable, WLChipEnable.CE0)
                self._hardware = Mod4AO(wl_ce)
                self._initialized = True
                logger.info(f"Analog output module '{self.name}' initialized successfully")
                
            except ImportError:
                logger.warning(f"widgetlords library not available - analog output module '{self.name}' in mock mode")
                self._initialized = True
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize analog output module '{self.name}': {e}", exc_info=True)
            return False
    
    def write_channel(self, channel: int, voltage: float) -> bool:
        """
        Write a voltage to an analog output channel.
        
        Args:
            channel: Channel number (0-3)
            voltage: Output voltage (0-10V)
        
        Returns:
            bool: True if successful
        """
        if not 0 <= channel <= 3:
            logger.error(f"Invalid analog output channel: {channel}")
            return False
        
        voltage = max(0.0, min(10.0, voltage))  # Clamp to 0-10V
        
        try:
            if self._hardware:
                self._hardware.write_single(channel, voltage)
            
            self._last_outputs[channel] = voltage
            logger.debug(f"Analog output '{self.name}' Ch{channel} = {voltage:.2f}V")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write analog output channel {channel}: {e}")
            return False
    
    def write_by_name(self, channel_name: str, voltage: float) -> bool:
        """Write voltage by channel name."""
        for ch in self.channels:
            if ch.name == channel_name and ch.enabled:
                return self.write_channel(ch.channel, voltage)
        
        logger.warning(f"Channel '{channel_name}' not found in analog output module '{self.name}'")
        return False


class WidgetLordsInterface(HardwareInterface):
    """
    Interface for WidgetLords SPI modules.
    
    Manages multiple PI-SPI-DIN modules configured via hardware_config.yaml.
    Provides unified access to:
    - Relay output modules (4KO)
    - Analog input modules (8AI)
    - Digital input modules (8DI)
    - Analog output modules (4AO)
    """
    
    def __init__(self, spi_modules_config: Optional[List[Dict]] = None):
        """
        Initialize the WidgetLords interface.
        
        Args:
            spi_modules_config: List of module configurations from hardware_config.yaml
        """
        super().__init__()
        
        self.spi_modules_config = spi_modules_config or []
        
        # Module storage by type
        self.relay_modules: Dict[str, RelayModule] = {}
        self.analog_input_modules: Dict[str, AnalogInputModule] = {}
        self.digital_input_modules: Dict[str, DigitalInputModule] = {}
        self.analog_output_modules: Dict[str, AnalogOutputModule] = {}
        
        # All modules by name
        self.modules: Dict[str, SPIModule] = {}
        
        # Legacy compatibility
        self._pressure_channel = 0
        self._pump_relay = 0
        
        logger.info(f"WidgetLordsInterface created with {len(self.spi_modules_config)} module configs")
        
    def connect(self) -> bool:
        """
        Initialize SPI communication with all configured modules.
        
        Returns:
            bool: True if at least one module initialized successfully
        """
        try:
            logger.info("=" * 60)
            logger.info("Connecting to WidgetLords SPI modules...")
            logger.info(f"Number of module configs: {len(self.spi_modules_config)}")
            
            # Initialize widgetlords library
            try:
                from widgetlords.pi_spi_din import init
                init()
                logger.info("Widgetlords library initialized successfully")
            except ImportError as ie:
                logger.warning(f"Widgetlords library not available - using mock mode: {ie}")
            except Exception as e:
                logger.warning(f"Failed to init widgetlords library: {e} - using mock mode")
            
            # Create and initialize modules
            success_count = 0
            
            for i, mod_cfg in enumerate(self.spi_modules_config):
                logger.info(f"Processing module config [{i}]: {mod_cfg.get('name')} ({mod_cfg.get('module_type')}) on {mod_cfg.get('chip_enable')}")
                module = self._create_module(mod_cfg)
                if module:
                    logger.info(f"  Module created: {module.name}, type={module.module_type}")
                    if module.initialize():
                        self.modules[module.name] = module
                        self._register_module(module)
                        success_count += 1
                        logger.info(f"  Module '{module.name}' registered successfully")
                    else:
                        logger.error(f"Failed to initialize module '{mod_cfg.get('name')}'")
                else:
                    logger.error(f"Failed to create module from config: {mod_cfg}")
            
            self.initialized = success_count > 0 or len(self.spi_modules_config) == 0
            
            # Log summary
            logger.info(f"WidgetLords interface connected: {success_count}/{len(self.spi_modules_config)} modules initialized")
            logger.info(f"  Relay modules: {list(self.relay_modules.keys())}")
            logger.info(f"  Analog input modules: {list(self.analog_input_modules.keys())}")
            logger.info(f"  Digital input modules: {list(self.digital_input_modules.keys())}")
            logger.info(f"  Analog output modules: {list(self.analog_output_modules.keys())}")
            logger.info("=" * 60)
            return self.initialized
            
        except Exception as e:
            logger.error(f"Exception during WidgetLords connect: {e}", exc_info=True)
            self.handle_error(e)
            return False
    
    def _create_module(self, config: Dict) -> Optional[SPIModule]:
        """Create a module instance from config."""
        try:
            # Parse channels
            channels = []
            for ch_cfg in config.get("channels", []):
                ch_config = ChannelConfig(
                    channel=ch_cfg.get("channel", 0),
                    name=ch_cfg.get("name", ""),
                    enabled=ch_cfg.get("enabled", True),
                    description=ch_cfg.get("description", ""),
                    # Span scaling configuration (critical for analog inputs!)
                    input_type=ch_cfg.get("input_type", "4-20mA"),
                    low_input=ch_cfg.get("low_input", 4.0),
                    low_output=ch_cfg.get("low_output", 0.0),
                    high_input=ch_cfg.get("high_input", 20.0),
                    high_output=ch_cfg.get("high_output", 100.0),
                    units=ch_cfg.get("units", ""),
                    # Legacy fields
                    min_value=ch_cfg.get("min_value", 0.0),
                    max_value=ch_cfg.get("max_value", 10.0),
                    inverted=ch_cfg.get("inverted", False),
                )
                channels.append(ch_config)
                logger.debug(f"Parsed channel config: ch={ch_config.channel}, name={ch_config.name}, "
                           f"input_type={ch_config.input_type}, low={ch_config.low_input}->{ch_config.low_output}, "
                           f"high={ch_config.high_input}->{ch_config.high_output}, units={ch_config.units}")
            
            module_config = SPIModuleConfig(
                name=config.get("name", "unnamed"),
                module_type=config.get("module_type", "PI-SPI-DIN-4KO"),
                chip_enable=config.get("chip_enable", "CE0"),
                address=config.get("address", 0),
                channels=channels,
            )
            
            # Create appropriate module type
            mod_type = module_config.module_type
            
            if mod_type == "PI-SPI-DIN-4KO":
                return RelayModule(module_config)
            elif mod_type == "PI-SPI-DIN-8AI":
                return AnalogInputModule(module_config)
            elif mod_type == "PI-SPI-DIN-8DI":
                return DigitalInputModule(module_config)
            elif mod_type == "PI-SPI-DIN-4AO":
                return AnalogOutputModule(module_config)
            else:
                logger.warning(f"Unknown module type: {mod_type}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create module: {e}", exc_info=True)
            return None
    
    def _register_module(self, module: SPIModule) -> None:
        """Register a module in the appropriate type dictionary."""
        if isinstance(module, RelayModule):
            self.relay_modules[module.name] = module
        elif isinstance(module, AnalogInputModule):
            self.analog_input_modules[module.name] = module
        elif isinstance(module, DigitalInputModule):
            self.digital_input_modules[module.name] = module
        elif isinstance(module, AnalogOutputModule):
            self.analog_output_modules[module.name] = module
    
    def disconnect(self) -> bool:
        """
        Disconnect from WidgetLords modules.
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            logger.info("Disconnecting from WidgetLords SPI modules...")
            
            # Shutdown all modules
            for module in self.modules.values():
                module.shutdown()
            
            self.modules.clear()
            self.relay_modules.clear()
            self.analog_input_modules.clear()
            self.digital_input_modules.clear()
            self.analog_output_modules.clear()
            
            self.initialized = False
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def read(self) -> Dict[str, Any]:
        """
        Read all analog inputs and digital inputs.
        
        Returns:
            Dict containing all sensor readings including:
            - analog_inputs: {module_name: {channel_name: scaled_value}}
            - analog_inputs_raw: {module_name: {channel_name: raw_voltage}}
            - digital_inputs: {module_name: {channel_name: state}}
            - relay_states: {module_name: {channel_name: state}}
            - pressure_voltage: raw voltage from pressure sensor
            - pressure_psi: pressure in PSI
            - vacuum_psi: vacuum in PSI
            - vacuum_bar: vacuum in bar
        """
        try:
            if not self.initialized:
                raise RuntimeError("WidgetLords interface not initialized")
            
            data = {
                "analog_inputs": {},
                "analog_inputs_raw": {},  # Raw voltage values for debugging
                "digital_inputs": {},
                "relay_states": {},
            }
            
            # Read all analog inputs (both scaled and raw for debugging)
            for name, module in self.analog_input_modules.items():
                scaled_readings = module.read_all_enabled(scaled=True)
                raw_readings = module.read_all_enabled(scaled=False)
                data["analog_inputs"][name] = scaled_readings
                data["analog_inputs_raw"][name] = raw_readings
            
            # Read all digital inputs
            for name, module in self.digital_input_modules.items():
                readings = module.read_all_enabled()
                data["digital_inputs"][name] = readings
            
            # Get all relay states
            for name, module in self.relay_modules.items():
                states = module.get_all_states()
                data["relay_states"][name] = states
            
            # Legacy format for backward compatibility (vacuum pressure display)
            if self.analog_input_modules:
                first_ai = next(iter(self.analog_input_modules.values()))
                module_name = first_ai.name
                
                # Get readings from data dict (already read above)
                scaled_readings = data["analog_inputs"].get(module_name, {})
                raw_readings = data["analog_inputs_raw"].get(module_name, {})
                
                # Log first few reads at INFO level for debugging
                if not hasattr(self, '_data_read_count'):
                    self._data_read_count = 0
                self._data_read_count += 1
                if self._data_read_count <= 5:
                    logger.info(f"[Read #{self._data_read_count}] Analog module '{module_name}':")
                    logger.info(f"  Raw voltages: {raw_readings}")
                    logger.info(f"  Scaled values: {scaled_readings}")
                
                if "pressure_sensor" in scaled_readings:
                    # The scaled reading is in GAUGE pressure (PSIG)
                    # Negative = vacuum, Positive = above atmospheric
                    pressure_psig = scaled_readings["pressure_sensor"]
                    raw_voltage = raw_readings.get("pressure_sensor", 0.0)
                    
                    # Convert voltage to mA using Ohm's law
                    # PI-SPI-DIN-8AI uses a sense resistor (calibrated: 454Ω)
                    SENSE_RESISTOR_OHMS = 454.0  # Calibrated from multimeter measurement
                    raw_mA = (raw_voltage / SENSE_RESISTOR_OHMS) * 1000.0
                    
                    # Convert PSI to millibar (1 PSI = 68.9476 mbar)
                    pressure_mbar = pressure_psig * 68.9476
                    
                    # Store in data dict for display widgets
                    data["pressure_voltage"] = raw_voltage
                    data["pressure_mA"] = raw_mA
                    data["pressure_psig"] = pressure_psig
                    data["pressure_mbar"] = pressure_mbar
                    data["pressure_psi"] = pressure_psig  # Legacy key
                    
                    # Legacy vacuum keys (for backward compatibility with plots, etc.)
                    # vacuum = -pressure for gauge pressure
                    vacuum_psi = -pressure_psig
                    vacuum_bar = vacuum_psi * 0.0689476
                    data["vacuum_psi"] = vacuum_psi
                    data["vacuum_bar"] = vacuum_bar
                    
                    if self._data_read_count <= 5:
                        logger.info(f"  Pressure: raw_V={raw_voltage:.4f}V -> {raw_mA:.2f}mA")
                        logger.info(f"  Gauge: {pressure_psig:.2f} PSIG = {pressure_mbar:.1f} mbar")
                        logger.info(f"  (Negative = vacuum, Positive = above atmospheric)")
                    else:
                        logger.debug(f"Pressure: {raw_mA:.2f}mA -> {pressure_psig:.2f} PSIG ({pressure_mbar:.1f} mbar)")
            
            return data
            
        except Exception as e:
            self.handle_error(e)
            return {}
    
    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write to relay and analog outputs.
        
        Args:
            data: Dictionary with output states/values
                  {"pump": True} - legacy pump control
                  {"relay_module": {"vacuum_pump": True}}
                  {"analog_outputs": {"module_name": {"channel_name": 5.0}}}
        
        Returns:
            bool: True if write successful
        """
        try:
            if not self.initialized:
                raise RuntimeError("WidgetLords interface not initialized")
            
            # Legacy pump control
            if "pump" in data:
                pump_state = bool(data["pump"])
                pump_written = False
                
                # First, try to find a relay module with a "vacuum_pump" channel
                for module in self.relay_modules.values():
                    if module.write_by_name("vacuum_pump", pump_state):
                        pump_written = True
                        break
                
                # Fallback: if no "vacuum_pump" channel found, use channel 0 of first module
                if not pump_written and self.relay_modules:
                    first_module = next(iter(self.relay_modules.values()))
                    if first_module.channels:
                        first_module.write_single(0, pump_state)
                        logger.debug("Legacy pump control: using fallback to channel 0")
            
            # Relay module control
            for mod_name, relay_states in data.get("relays", {}).items():
                if mod_name in self.relay_modules:
                    module = self.relay_modules[mod_name]
                    for ch_name, state in relay_states.items():
                        module.write_by_name(ch_name, bool(state))
            
            # Analog output control
            for mod_name, ao_values in data.get("analog_outputs", {}).items():
                if mod_name in self.analog_output_modules:
                    module = self.analog_output_modules[mod_name]
                    for ch_name, voltage in ao_values.items():
                        module.write_by_name(ch_name, float(voltage))
            
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def is_connected(self) -> bool:
        """
        Check if WidgetLords modules are connected.
        
        Returns:
            bool: True if initialized
        """
        return self.initialized
    
    # Convenience methods for common operations
    
    def set_relay(self, relay_or_module: Any, state_or_channel: Any, state: Optional[bool] = None) -> bool:
        """
        Set a specific relay state.
        
        Supports two calling conventions for backward compatibility:
        - Legacy: set_relay(relay: int, state: bool) - uses first relay module
        - New: set_relay(module_name: str, channel_name: str, state: bool)
        
        Args:
            relay_or_module: Relay number (int, legacy) or module name (str)
            state_or_channel: State (bool, legacy) or channel name (str)
            state: Relay state (only for new signature)
        
        Returns:
            bool: True if successful
        """
        # Legacy signature: set_relay(relay: int, state: bool)
        if isinstance(relay_or_module, int) and isinstance(state_or_channel, bool):
            relay_num = relay_or_module
            relay_state = state_or_channel
            
            # Use first available relay module
            if self.relay_modules:
                first_module = next(iter(self.relay_modules.values()))
                return first_module.write_single(relay_num, relay_state)
            
            logger.warning("No relay modules configured")
            return False
        
        # New signature: set_relay(module_name: str, channel_name: str, state: bool)
        module_name = str(relay_or_module)
        channel_name = str(state_or_channel)
        relay_state = bool(state) if state is not None else False
        
        if module_name in self.relay_modules:
            return self.relay_modules[module_name].write_by_name(channel_name, relay_state)
        
        logger.warning(f"Relay module '{module_name}' not found")
        return False
    
    def read_analog(self, module_name: str, channel_name: str) -> Optional[float]:
        """Read a specific analog input by module and channel name."""
        if module_name in self.analog_input_modules:
            return self.analog_input_modules[module_name].read_by_name(channel_name)
        logger.warning(f"Analog input module '{module_name}' not found")
        return None
    
    def read_digital(self, module_name: str, channel_name: str) -> Optional[bool]:
        """Read a specific digital input by module and channel name."""
        if module_name not in self.digital_input_modules:
            logger.warning(f"Digital input module '{module_name}' not found")
            return None
        
        module = self.digital_input_modules[module_name]
        for ch in module.channels:
            if ch.name == channel_name and ch.enabled:
                return module.read_channel(ch.channel)
        
        logger.warning(f"Channel '{channel_name}' not found in digital input module '{module_name}'")
        return None
    
    def set_analog_output(self, module_name: str, channel_name: str, voltage: float) -> bool:
        """Set a specific analog output by module and channel name."""
        if module_name in self.analog_output_modules:
            return self.analog_output_modules[module_name].write_by_name(channel_name, voltage)
        logger.warning(f"Analog output module '{module_name}' not found")
        return False
    
    def get_module(self, name: str) -> Optional[SPIModule]:
        """Get a module by name."""
        return self.modules.get(name)
    
    def list_modules(self) -> Dict[str, str]:
        """List all configured modules with their types."""
        return {name: mod.module_type for name, mod in self.modules.items()}


def create_widgetlords_interface_from_config(config: Dict) -> WidgetLordsInterface:
    """
    Create a WidgetLordsInterface from configuration dictionary.
    
    Args:
        config: Full configuration dict (from hardware_config.yaml)
    
    Returns:
        WidgetLordsInterface: Configured interface ready for connect()
    """
    wl_config = config.get("hardware", {}).get("widgetlords", {})
    spi_modules = wl_config.get("spi_modules", [])
    
    interface = WidgetLordsInterface(spi_modules_config=spi_modules)
    
    # Set legacy options
    interface._pressure_channel = wl_config.get("pressure_channel", 0)
    interface._pump_relay = wl_config.get("pump_relay", 0)
    
    logger.info(f"Created WidgetLordsInterface with {len(spi_modules)} module configurations")
    return interface
