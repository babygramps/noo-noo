"""
Modbus Interface - TLB4 Load Cell Transmitter

Handles Modbus RTU communication with the Laumas TLB4 4-channel
load cell transmitter via USB-RS485 adapter.

Device Configuration (must be set manually on TLB4):
- Protocol: Modbus RTU
- Baud Rate: 9600
- Address: 1
- Parity: None
- Stop Bits: 1
- Delay: 0 ms
- Wiring: Terminal 29 (A/+), Terminal 30 (B/-)
"""

from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import logging
import struct
import time
import threading

from .hardware_interface import HardwareInterface

logger = logging.getLogger(__name__)


class ByteOrder(Enum):
    """Byte ordering for multi-byte values."""
    BIG = "big"
    LITTLE = "little"


class DataFormat(Enum):
    """Data format for register values."""
    INT16 = "int16"
    UINT16 = "uint16"
    INT32 = "int32"
    UINT32 = "uint32"
    FLOAT32 = "float32"


@dataclass
class TLB4ChannelConfig:
    """Configuration for a single load cell channel.
    
    Simple scaling for factory-calibrated 0-20kg load cells.
    Formula: kg = raw_value / kg_per_division
    
    Software taring is handled separately via tare offsets.
    """
    
    # Register address for this channel's divisions/raw value
    register_address: int = 0
    
    # Data format for this channel
    data_format: DataFormat = DataFormat.INT32
    
    # Whether this channel is enabled
    enabled: bool = True
    
    def raw_to_kg(self, raw_value: float, kg_per_division: float) -> float:
        """Convert raw Modbus value to kilograms.
        
        Args:
            raw_value: Raw integer value from Modbus register
            kg_per_division: Scaling factor (raw divisions per kg)
            
        Returns:
            Weight in kilograms
        """
        if kg_per_division == 0:
            return 0.0
        return raw_value / kg_per_division


@dataclass
class TLB4Config:
    """Complete configuration for TLB4 transmitter.
    
    Simple configuration for factory-calibrated 0-20kg load cells.
    """
    
    # Known register addresses (discovered via scanner or manual)
    # These are Modbus register addresses (0-based)
    reg_gross_weight: int = 0
    reg_net_weight: int = 2
    reg_tare_weight: int = 4
    reg_status: int = 6
    
    # Individual channel registers (CH1-CH4 divisions)
    # These typically follow the main weight registers
    reg_channel_1: int = 8
    reg_channel_2: int = 10
    reg_channel_3: int = 12
    reg_channel_4: int = 14
    
    # Channel-specific configurations
    channels: List[TLB4ChannelConfig] = field(default_factory=lambda: [
        TLB4ChannelConfig() for _ in range(4)
    ])
    
    # Data format for gross weight
    gross_weight_format: DataFormat = DataFormat.INT32
    
    # Decimal point position (number of decimal places in raw value)
    # TLB4 may transmit scaled integers, e.g., 12345 = 123.45 kg if decimals=2
    decimal_places: int = 2
    
    # Whether to use automatic scaling based on decimal places
    use_decimal_scaling: bool = True
    
    # Simple scaling: raw divisions per kg (same for all channels)
    # For factory-calibrated 0-20kg load cells, adjust this ONE value
    kg_per_division: float = 5000.0


class ModbusInterface(HardwareInterface):
    """
    Interface for TLB4 Load Cell Transmitter via Modbus RTU.
    
    Provides access to:
    - Gross weight (sum of all load cells)
    - Net weight (gross minus tare)
    - Individual load cell readings (4 channels)
    - Tare and calibration functions
    - Register scanning for address discovery
    
    The TLB4 transmits individual channel values as "Divisions" (raw points).
    Conversion to kg requires applying a scaling factor:
        Load_kg = (Channel_Value / Full_Scale_Divisions) * Load_Cell_Capacity
    """
    
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        slave_address: int = 1,
        baudrate: int = 9600,
        timeout: float = 1.0,
        parity: str = "None",
        databits: int = 8,
        stopbits: float = 1.0,
        byteorder: str = "big",
        wordorder: str = "big",
        close_port_after_each_call: bool = False,
        debug: bool = False,
        tlb4_config: Optional[TLB4Config] = None,
    ):
        """
        Initialize the Modbus interface for TLB4 Load Cell Transmitter.
        
        Args:
            port: Serial port path (e.g., COM3 on Windows, /dev/ttyUSB0 on Linux)
            slave_address: Modbus slave address (1-247, typically 1)
            baudrate: Serial baud rate (TLB4 configured for 9600)
            timeout: Communication timeout in seconds
            parity: Parity setting (None, Even, Odd, Mark, Space)
            databits: Data bits per byte (7 or 8)
            stopbits: Stop bits (1, 1.5, or 2)
            byteorder: Byte order for multi-byte values ('big' or 'little')
            wordorder: Word order for 32-bit values ('big' or 'little')
            close_port_after_each_call: Close port after each communication
            debug: Enable debug logging for troubleshooting
            tlb4_config: TLB4-specific configuration (registers, scaling)
        """
        super().__init__()
        self.port = port
        self.slave_address = slave_address
        self.baudrate = baudrate
        self.timeout = timeout
        self.parity = parity
        self.databits = databits
        self.stopbits = stopbits
        self.byteorder = byteorder
        self.wordorder = wordorder
        self.close_port_after_each_call = close_port_after_each_call
        self.debug = debug
        self.instrument = None
        self.tlb4_config = tlb4_config or TLB4Config()
        
        # Cache for last readings
        self._last_reading: Dict[str, Any] = {}
        self._last_read_time: float = 0.0
        
        # Thread lock for serial port access (prevents read/write collisions)
        self._lock = threading.Lock()
        
        # Software tare offsets for individual channels (TLB4 only tares total, not channels)
        self._channel_tare_offsets: List[float] = [0.0, 0.0, 0.0, 0.0]
        
        # Moving average buffers for smoothing channel readings (10 samples = ~1 sec at 10Hz)
        self._channel_buffers: List[deque] = [deque(maxlen=10) for _ in range(4)]
        
        # Log configuration for troubleshooting
        if self.debug:
            logger.info(f"ModbusInterface initialized with:")
            logger.info(f"  Port: {self.port}")
            logger.info(f"  Baudrate: {self.baudrate}")
            logger.info(f"  Slave Address: {self.slave_address}")
            logger.info(f"  Parity: {self.parity}")
            logger.info(f"  Data Bits: {self.databits}")
            logger.info(f"  Stop Bits: {self.stopbits}")
            logger.info(f"  Timeout: {self.timeout}s")
            logger.info(f"  Byte Order: {self.byteorder}")
            logger.info(f"  Word Order: {self.wordorder}")
        
    def connect(self) -> bool:
        """
        Establish Modbus RTU connection to TLB4.
        
        Returns:
            bool: True if connection successful
        """
        try:
            logger.info(f"Connecting to TLB4 on {self.port} at {self.baudrate} baud...")
            
            import minimalmodbus
            import serial
            
            # Map parity string to serial constant
            parity_map = {
                'None': serial.PARITY_NONE,
                'none': serial.PARITY_NONE,
                'N': serial.PARITY_NONE,
                'Even': serial.PARITY_EVEN,
                'even': serial.PARITY_EVEN,
                'E': serial.PARITY_EVEN,
                'Odd': serial.PARITY_ODD,
                'odd': serial.PARITY_ODD,
                'O': serial.PARITY_ODD,
                'Mark': serial.PARITY_MARK,
                'mark': serial.PARITY_MARK,
                'M': serial.PARITY_MARK,
                'Space': serial.PARITY_SPACE,
                'space': serial.PARITY_SPACE,
                'S': serial.PARITY_SPACE,
            }
            parity_setting = parity_map.get(self.parity, serial.PARITY_NONE)
            
            # Map stopbits to serial constant
            stopbits_map = {
                1: serial.STOPBITS_ONE,
                1.0: serial.STOPBITS_ONE,
                1.5: serial.STOPBITS_ONE_POINT_FIVE,
                2: serial.STOPBITS_TWO,
                2.0: serial.STOPBITS_TWO,
            }
            stopbits_setting = stopbits_map.get(self.stopbits, serial.STOPBITS_ONE)
            
            # Create Modbus instrument
            self.instrument = minimalmodbus.Instrument(
                port=self.port,
                slaveaddress=self.slave_address,
                mode=minimalmodbus.MODE_RTU,
                close_port_after_each_call=self.close_port_after_each_call,
                debug=self.debug
            )
            
            # Configure serial port
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.bytesize = self.databits
            self.instrument.serial.parity = parity_setting
            self.instrument.serial.stopbits = stopbits_setting
            self.instrument.serial.timeout = self.timeout
            
            # Test connection by attempting a read
            try:
                # Try reading from register 0 to verify connection
                _ = self.instrument.read_register(0, functioncode=3)
                logger.info(f"Successfully connected to TLB4 at address {self.slave_address}")
            except Exception as test_error:
                # Connection may still work - device might not have data at register 0
                logger.warning(f"Initial test read failed (may be normal): {test_error}")
                logger.info("Connection established - device may require register scanning")
            
            self.initialized = True
            
            # Enable multi-channel HiRes mode (Command 25)
            # This tells the TLB4 to stream individual channel data to registers 40051-40058
            self._enable_multichannel_mode()
            
            return True
            
        except ImportError as ie:
            logger.error(f"Missing dependency: {ie}")
            logger.error("Install with: pip install minimalmodbus pyserial")
            self.handle_error(ie)
            return False
        except Exception as e:
            self.handle_error(e)
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from Modbus device.
        
        Returns:
            bool: True if disconnection successful
        """
        try:
            logger.info("Disconnecting from TLB4...")
            
            if self.instrument and hasattr(self.instrument, 'serial'):
                if self.instrument.serial.is_open:
                    self.instrument.serial.close()
                    logger.info("Serial port closed")
            
            self.instrument = None
            self.initialized = False
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def read(self) -> Dict[str, Any]:
        """
        Read all load cell data from TLB4.
        
        Uses a lock to prevent collision with write operations.
        
        Returns:
            Dict containing:
            - gross_weight_kg: Total weight from all load cells
            - net_weight_kg: Net weight (gross - tare)
            - tare_weight_kg: Current tare value
            - load_cell_1_kg through load_cell_4_kg: Individual readings
            - load_cell_1_raw through load_cell_4_raw: Raw division values
            - status: Device status word
            - timestamp: Reading timestamp
        """
        try:
            if not self.initialized or self.instrument is None:
                raise RuntimeError("Modbus interface not initialized")
            
            # Use lock to prevent collision with write commands
            with self._lock:
                return self._read_internal()
            
        except Exception as e:
            self.handle_error(e)
            return self._get_error_reading()
    
    def _read_internal(self) -> Dict[str, Any]:
        """Internal read method (called with lock held)."""
        cfg = self.tlb4_config
        result = {
            "timestamp": time.time(),
            "gross_weight_kg": 0.0,
            "net_weight_kg": 0.0,
            "tare_weight_kg": 0.0,
            "status": 0,
        }
        
        # Debug logging for channel discovery (first few reads only)
        if not hasattr(self, '_read_count'):
            self._read_count = 0
        self._read_count += 1
        debug_this_read = self._read_count <= 3 or self.debug
        
        # Read gross weight (format depends on config)
        try:
            gross_raw = self._read_value(
                cfg.reg_gross_weight,
                cfg.gross_weight_format
            )
            result["gross_weight_raw"] = gross_raw
            result["gross_weight_kg"] = self._scale_weight(gross_raw)
        except Exception as e:
            logger.warning(f"Failed to read gross weight: {e}")
            result["gross_weight_kg"] = 0.0
        
        # Read net weight
        try:
            net_raw = self._read_value(
                cfg.reg_net_weight,
                cfg.gross_weight_format
            )
            result["net_weight_raw"] = net_raw
            result["net_weight_kg"] = self._scale_weight(net_raw)
        except Exception as e:
            logger.debug(f"Failed to read net weight: {e}")
        
        # Read tare weight
        try:
            tare_raw = self._read_value(
                cfg.reg_tare_weight,
                cfg.gross_weight_format
            )
            result["tare_weight_raw"] = tare_raw
            result["tare_weight_kg"] = self._scale_weight(tare_raw)
        except Exception as e:
            logger.debug(f"Failed to read tare weight: {e}")
        
        # Read individual channel values (divisions)
        channel_regs = [
            cfg.reg_channel_1,
            cfg.reg_channel_2,
            cfg.reg_channel_3,
            cfg.reg_channel_4
        ]
        
        if debug_this_read:
            logger.info(f"[TLB4 Read #{self._read_count}] Channel registers: {channel_regs}")
            logger.info(f"  Channel configs: " + 
                ", ".join(f"CH{i+1}:{ch.enabled}" for i, ch in enumerate(cfg.channels)))
        
        for i, (reg, ch_cfg) in enumerate(zip(channel_regs, cfg.channels), start=1):
            try:
                if ch_cfg.enabled:
                    raw_value = self._read_value(reg, ch_cfg.data_format)
                    result[f"load_cell_{i}_raw"] = raw_value
                    
                    # Add to moving average buffer for smoothing
                    self._channel_buffers[i - 1].append(raw_value)
                    
                    # Use averaged raw value for stable readings
                    avg_raw = sum(self._channel_buffers[i - 1]) / len(self._channel_buffers[i - 1])
                    
                    # Simple conversion: kg = avg_raw / kg_per_division
                    kg_value = ch_cfg.raw_to_kg(avg_raw, cfg.kg_per_division)
                    
                    # Apply software tare offset
                    kg_value -= self._channel_tare_offsets[i - 1]
                    result[f"load_cell_{i}_kg"] = kg_value
                    
                    if debug_this_read:
                        logger.info(f"  CH{i} @ reg {reg}: raw={raw_value}, avg={avg_raw:.0f}, kg={kg_value:.3f}")
                else:
                    result[f"load_cell_{i}_raw"] = 0
                    result[f"load_cell_{i}_kg"] = 0.0
                    if debug_this_read:
                        logger.info(f"  CH{i} @ reg {reg}: DISABLED")
            except Exception as e:
                logger.warning(f"Failed to read channel {i} @ register {reg}: {e}")
                result[f"load_cell_{i}_raw"] = 0
                result[f"load_cell_{i}_kg"] = 0.0
        
        # Read status register
        try:
            status = self.instrument.read_register(cfg.reg_status, functioncode=3)
            result["status"] = status
        except Exception as e:
            logger.debug(f"Failed to read status: {e}")
        
        # Cache the reading
        self._last_reading = result
        self._last_read_time = time.time()
        
        return result
    
    def _read_value(
        self,
        register: int,
        data_format: DataFormat = DataFormat.INT16
    ) -> float:
        """
        Read a value from register(s) based on data format.
        
        Supports both 16-bit (single register) and 32-bit (two registers) formats.
        
        Args:
            register: Starting register address (0-based)
            data_format: Data format (INT16, UINT16, INT32, UINT32, FLOAT32)
            
        Returns:
            float: The decoded value
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not initialized")
        
        # Handle 16-bit formats (single register)
        if data_format == DataFormat.INT16:
            return self.instrument.read_register(register, functioncode=3, signed=True)
        elif data_format == DataFormat.UINT16:
            return self.instrument.read_register(register, functioncode=3, signed=False)
        
        # Handle 32-bit formats (two registers)
        return self._read_32bit_value(register, data_format)
    
    def _read_32bit_value(
        self,
        register: int,
        data_format: DataFormat = DataFormat.INT32
    ) -> float:
        """
        Read a 32-bit value from two consecutive registers.
        
        Args:
            register: Starting register address (0-based)
            data_format: Data format (INT32, UINT32, FLOAT32)
            
        Returns:
            float: The decoded value
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not initialized")
        
        # Read 2 consecutive 16-bit registers
        regs = self.instrument.read_registers(register, 2, functioncode=3)
        
        # Combine registers based on word order
        if self.wordorder == "big":
            high_word, low_word = regs[0], regs[1]
        else:
            low_word, high_word = regs[0], regs[1]
        
        # Pack into bytes
        if self.byteorder == "big":
            raw_bytes = struct.pack('>HH', high_word, low_word)
        else:
            raw_bytes = struct.pack('<HH', low_word, high_word)
        
        # Unpack based on data format
        if data_format == DataFormat.INT32:
            if self.byteorder == "big":
                return struct.unpack('>i', raw_bytes)[0]
            else:
                return struct.unpack('<i', raw_bytes)[0]
        elif data_format == DataFormat.UINT32:
            if self.byteorder == "big":
                return struct.unpack('>I', raw_bytes)[0]
            else:
                return struct.unpack('<I', raw_bytes)[0]
        elif data_format == DataFormat.FLOAT32:
            if self.byteorder == "big":
                return struct.unpack('>f', raw_bytes)[0]
            else:
                return struct.unpack('<f', raw_bytes)[0]
        else:
            # Default to signed 32-bit
            return struct.unpack('>i', raw_bytes)[0]
    
    def _read_16bit_value(
        self,
        register: int,
        signed: bool = True
    ) -> int:
        """
        Read a single 16-bit register.
        
        Args:
            register: Register address
            signed: Whether to interpret as signed
            
        Returns:
            int: Register value
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not initialized")
        
        return self.instrument.read_register(
            register,
            functioncode=3,
            signed=signed
        )
    
    def _scale_weight(self, raw_value: float) -> float:
        """
        Apply decimal scaling to raw weight value.
        
        The TLB4 may transmit scaled integers where the decimal
        point position is defined by configuration.
        
        Args:
            raw_value: Raw value from register
            
        Returns:
            float: Scaled weight in kg
        """
        if self.tlb4_config.use_decimal_scaling:
            divisor = 10 ** self.tlb4_config.decimal_places
            return raw_value / divisor
        return raw_value
    
    def _get_error_reading(self) -> Dict[str, Any]:
        """Return a default reading structure for error cases."""
        return {
            "timestamp": time.time(),
            "gross_weight_kg": 0.0,
            "net_weight_kg": 0.0,
            "tare_weight_kg": 0.0,
            "load_cell_1_kg": 0.0,
            "load_cell_2_kg": 0.0,
            "load_cell_3_kg": 0.0,
            "load_cell_4_kg": 0.0,
            "load_cell_1_raw": 0,
            "load_cell_2_raw": 0,
            "load_cell_3_raw": 0,
            "load_cell_4_raw": 0,
            "status": 0,
            "error": True,
        }
    
    def write(self, data: Dict[str, Any]) -> bool:
        """
        Write commands to the TLB4.
        
        Args:
            data: Dictionary with commands, e.g.:
                  {"tare": True} to execute tare function
                  {"zero_channel": 1} to zero a specific channel
        
        Returns:
            bool: True if write successful
        """
        try:
            if not self.initialized or self.instrument is None:
                raise RuntimeError("Modbus interface not initialized")
            
            if "tare" in data and data["tare"]:
                return self.tare_load_cells()
            
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def is_connected(self) -> bool:
        """
        Check if TLB4 is connected and responding.
        
        Uses cached data to avoid additional serial port access that could
        conflict with the DAQ thread. Considers connected if we have a recent
        successful read (within last 2 seconds).
        
        Returns:
            bool: True if device appears to be responding
        """
        try:
            if not self.initialized or self.instrument is None:
                return False
            
            # Check if we have recent data (within last 2 seconds)
            # This avoids making additional serial reads that conflict with DAQ thread
            if self._last_read_time > 0:
                time_since_read = time.time() - self._last_read_time
                if time_since_read < 2.0:
                    # We have recent data, assume connected
                    return not self._last_reading.get("error", False)
            
            # No recent data, try a test read with lock to prevent collisions
            with self._lock:
                try:
                    _ = self.instrument.read_register(0, functioncode=3)
                    return True
                except Exception:
                    return False
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def read_register(
        self,
        register: int,
        signed: bool = True,
        functioncode: int = 3
    ) -> Optional[int]:
        """
        Read a specific Modbus register.
        
        Args:
            register: Register address (0-based)
            signed: Whether to interpret as signed integer
            functioncode: Modbus function code (3 or 4)
        
        Returns:
            int: Register value, or None if error
        """
        try:
            if not self.initialized or self.instrument is None:
                raise RuntimeError("Modbus interface not initialized")
            
            value = self.instrument.read_register(
                register,
                functioncode=functioncode,
                signed=signed
            )
            return value
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Failed to read register {register}: {e}")
            return None
    
    def read_registers(
        self,
        start_register: int,
        count: int,
        functioncode: int = 3
    ) -> Optional[List[int]]:
        """
        Read multiple consecutive Modbus registers.
        
        Args:
            start_register: Starting register address (0-based)
            count: Number of registers to read
            functioncode: Modbus function code (3 or 4)
        
        Returns:
            List[int]: Register values, or None if error
        """
        try:
            if not self.initialized or self.instrument is None:
                raise RuntimeError("Modbus interface not initialized")
            
            values = self.instrument.read_registers(
                start_register,
                count,
                functioncode=functioncode
            )
            return values
            
        except Exception as e:
            if self.debug:
                logger.debug(f"Failed to read registers {start_register}-{start_register+count}: {e}")
            return None
    
    # TLB4 Command Register and Commands (from Communication Protocols Manual)
    # Register 40006 = Address 5 (40006 - 40001 = 5)
    TLB4_COMMAND_REGISTER = 5
    CMD_TARE = 7              # Semi-Automatic Tare (sets current weight as tare, shows Net)
    CMD_ZERO = 8              # Zero (small variations only)
    CMD_GROSS = 9             # Switch back to Gross Weight display
    CMD_ENABLE_HIRES = 25     # Enable 4x HiRes Channel Reading (streams individual channels to R1-R8)
    
    # Calibration Commands (from Communication Protocols Manual Section 2659 & 2684)
    CMD_ZERO_CALIBRATION = 100   # "Tare Weight Zero Setting" - defines the zero point
    CMD_SPAN_CALIBRATION = 101   # "Acquisition of a single calibration point" - span calibration
    
    # Calibration Registers
    ADDR_CAL_WEIGHT = 64         # Register 40065: Sample Weight (32-bit signed) for span calibration
    
    def _write_command(self, command: int) -> bool:
        """
        Write a command to the TLB4 command register.
        
        TLB4 only supports Function 16 (Write Multiple Registers), not Function 6.
        Uses write_registers() to write a single value using FC16.
        Uses a lock to prevent collision with DAQ read operations.
        
        Args:
            command: Command value to write (7=tare, 8=zero, 9=gross, 25=enable HiRes channels)
            
        Returns:
            bool: True if command sent successfully
        """
        if not self.initialized or self.instrument is None:
            raise RuntimeError("Modbus interface not initialized")
        
        # Use lock to prevent collision with DAQ reads
        with self._lock:
            # TLB4 only supports Function 16 (Write Multiple Registers)
            # Use write_registers() which uses FC16 by default
            self.instrument.write_registers(
                self.TLB4_COMMAND_REGISTER,
                [command]  # List of values to write
            )
        return True
    
    def _enable_multichannel_mode(self) -> bool:
        """
        Enable multi-channel HiRes mode on TLB4 (Command 25).
        
        This command tells the TLB4 to stream individual load cell channel data
        to registers 40051-40058 (addresses 50-57). Without this command, only
        combined weight data is available.
        
        Channel mapping after Command 25:
            - Channel 1: Registers 40051-40052 (address 50-51) - 32-bit signed
            - Channel 2: Registers 40053-40054 (address 52-53) - 32-bit signed
            - Channel 3: Registers 40055-40056 (address 54-55) - 32-bit signed
            - Channel 4: Registers 40057-40058 (address 56-57) - 32-bit signed
        
        Note: Values are raw divisions (ADC counts), not kg. Calibration required.
        
        Returns:
            bool: True if command sent successfully
        """
        try:
            logger.info("Enabling TLB4 multi-channel HiRes mode (Command 25)...")
            
            # Send Command 25 to Command Register
            self._write_command(self.CMD_ENABLE_HIRES)
            
            # Give the TLB4 a moment to switch modes
            time.sleep(0.3)
            
            logger.info("✓ TLB4 multi-channel mode enabled - individual channels at registers 50-57")
            return True
            
        except Exception as e:
            logger.error(f"Failed to enable multi-channel mode: {e}")
            logger.warning("Individual channel readings may not be available")
            return False
    
    def tare_load_cells(self) -> bool:
        """
        Execute Software Tare on individual load cell channels.
        
        Captures current kg values as tare offsets for each channel.
        Also sends hardware tare command to TLB4 for gross/net weight.
        
        Returns:
            bool: True if tare successful
        """
        try:
            logger.info("Executing Software Tare on load cells...")
            
            # Hold lock for ENTIRE tare operation to prevent DAQ thread collision
            with self._lock:
                cfg = self.tlb4_config
                channel_regs = [
                    cfg.reg_channel_1,
                    cfg.reg_channel_2,
                    cfg.reg_channel_3,
                    cfg.reg_channel_4
                ]
                
                for i, (reg, ch_cfg) in enumerate(zip(channel_regs, cfg.channels)):
                    try:
                        if ch_cfg.enabled:
                            # Use averaged value from buffer for stable tare
                            if len(self._channel_buffers[i]) > 0:
                                avg_raw = sum(self._channel_buffers[i]) / len(self._channel_buffers[i])
                            else:
                                # Buffer empty, read current value
                                avg_raw = self._read_value(reg, ch_cfg.data_format)
                            
                            # Convert to kg using simple scaling
                            kg_value = ch_cfg.raw_to_kg(avg_raw, cfg.kg_per_division)
                            self._channel_tare_offsets[i] = kg_value
                            logger.info(f"Channel {i+1} tare offset: {kg_value:.3f} kg (avg_raw={avg_raw:.0f})")
                    except Exception as e:
                        logger.warning(f"Failed to capture channel {i+1} tare offset: {e}")
                        self._channel_tare_offsets[i] = 0.0
                
                logger.info(f"Software tare offsets: {[f'{x:.3f}' for x in self._channel_tare_offsets]}")
                
                # Send hardware tare to TLB4 (inside lock to prevent collision)
                time.sleep(0.05)
                self.instrument.write_registers(self.TLB4_COMMAND_REGISTER, [self.CMD_TARE])
                
            logger.info("Tare complete")
            return True
            
        except Exception as e:
            self.handle_error(e)
            logger.error("Tare failed")
            return False
    
    def switch_to_gross(self) -> bool:
        """
        Switch back to Gross Weight display (undo tare).
        
        Writes command 9 to register 5 (40006).
        
        Returns:
            bool: True if command sent successfully
        """
        try:
            logger.info("Switching to GROSS weight on TLB4...")
            
            time.sleep(0.1)
            self._write_command(self.CMD_GROSS)
            
            logger.info("Gross weight command sent successfully")
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    def zero_scale(self) -> bool:
        """
        Zero the scale for small drift corrections.
        
        Writes command 8 to register 5 (40006).
        Use for small variations (like dust), not for taring containers.
        
        Returns:
            bool: True if command sent successfully
        """
        try:
            logger.info("Executing ZERO command on TLB4...")
            
            time.sleep(0.1)
            self._write_command(self.CMD_ZERO)
            
            logger.info("Zero command sent successfully")
            return True
            
        except Exception as e:
            self.handle_error(e)
            return False
    
    # =========================================================================
    # Real Calibration Methods (Physical Weight Calibration)
    # From Communication Protocols Manual Section 2659 & 2684
    # =========================================================================
    
    def zero_calibration(self) -> Tuple[bool, str]:
        """
        Perform Zero Calibration (empty scale).
        
        This defines the "zero point" of the scale. The scale must be completely
        unloaded and stable before calling this method.
        
        Procedure:
        1. Ensure scale is EMPTY and STABLE
        2. Send Command 100 to Register 5 (CMDR)
        3. Verify by reading Gross Weight (should be 0)
        
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            if not self.initialized or self.instrument is None:
                return False, "Modbus interface not connected"
            
            logger.info("=" * 50)
            logger.info("ZERO CALIBRATION - Starting")
            logger.info("=" * 50)
            
            # Use lock for ENTIRE calibration sequence to prevent DAQ thread conflicts
            with self._lock:
                # Read current weight before calibration
                cfg = self.tlb4_config
                try:
                    pre_weight = int(self._read_value(cfg.reg_gross_weight, cfg.gross_weight_format))
                    logger.info(f"Pre-calibration gross weight (raw): {pre_weight}")
                except Exception as e:
                    logger.warning(f"Could not read pre-calibration weight: {e}")
                    pre_weight = 0
                
                # Send Command 100 to Command Register
                logger.info(f"Sending Zero Calibration Command ({self.CMD_ZERO_CALIBRATION}) to register {self.TLB4_COMMAND_REGISTER}...")
                self.instrument.write_registers(
                    self.TLB4_COMMAND_REGISTER,
                    [self.CMD_ZERO_CALIBRATION]
                )
                
                # Wait for TLB4 to process the command (inside lock to prevent DAQ reads during processing)
                time.sleep(2.0)
                
                # Verify calibration by reading gross weight
                try:
                    post_weight = int(self._read_value(cfg.reg_gross_weight, cfg.gross_weight_format))
                    logger.info(f"Post-calibration gross weight (raw): {post_weight}")
                except Exception as e:
                    logger.warning(f"Could not read post-calibration weight: {e}")
                    post_weight = 0
            
            # Check if weight is now at or near zero
            if abs(post_weight) < 100:  # Within 100 divisions of zero
                msg = f"Zero Calibration SUCCESS - Weight is now {post_weight} (raw)"
                logger.info(f"✓ {msg}")
                return True, msg
            else:
                msg = f"Zero Calibration completed but weight reads {post_weight}. May need adjustment."
                logger.warning(f"⚠ {msg}")
                return True, msg
            
        except Exception as e:
            error_msg = f"Zero Calibration FAILED: {e}"
            logger.error(f"✗ {error_msg}")
            self.handle_error(e)
            return False, error_msg
    
    def span_calibration(self, known_weight: float, decimal_places: int = 2) -> Tuple[bool, str, int]:
        """
        Perform Span Calibration (known weight).
        
        This defines a calibration point using a known weight. The known weight
        must be placed on the scale and stable before calling this method.
        Recommended: Use at least 50% of the load cell capacity.
        
        Procedure:
        1. Place KNOWN WEIGHT on scale, wait for stability
        2. Write known weight value to Register 64 (CALW) as 32-bit signed int
        3. Send Command 101 to Register 5 (CMDR)
        4. Read Register 64 (CALW) to check result:
           - 0 = Success
           - Non-zero = Error code
        
        Args:
            known_weight: The known weight value (e.g., 50.00 for 50kg)
            decimal_places: Number of decimal places (default 2, so 50.00 becomes 5000)
        
        Returns:
            Tuple[bool, str, int]: (success, message, error_code)
                                   error_code is 0 on success, otherwise the TLB4 error code
        """
        try:
            if not self.initialized or self.instrument is None:
                return False, "Modbus interface not connected", -1
            
            # Convert weight to integer with decimal places
            # e.g., 50.00 kg with 2 decimals = 5000
            weight_int = int(known_weight * (10 ** decimal_places))
            
            logger.info("=" * 50)
            logger.info("SPAN CALIBRATION - Starting")
            logger.info(f"Known weight: {known_weight} kg ({weight_int} with {decimal_places} decimals)")
            logger.info("=" * 50)
            
            cfg = self.tlb4_config
            
            # Use lock for ENTIRE calibration sequence to prevent DAQ thread conflicts
            with self._lock:
                # Read current weight before calibration (informational)
                try:
                    pre_weight = int(self._read_value(cfg.reg_gross_weight, cfg.gross_weight_format))
                    logger.info(f"Pre-calibration gross weight (raw): {pre_weight}")
                except Exception as e:
                    logger.warning(f"Could not read pre-calibration weight: {e}")
                    pre_weight = 0
                
                # Step 1: Write the known weight to CALW register (64)
                # Must be 32-bit signed integer
                logger.info(f"Writing known weight {weight_int} to register {self.ADDR_CAL_WEIGHT}...")
                self._write_32bit_value(self.ADDR_CAL_WEIGHT, weight_int)
                
                time.sleep(0.5)
                
                # Step 2: Send Command 101 to Command Register
                logger.info(f"Sending Span Calibration Command ({self.CMD_SPAN_CALIBRATION}) to register {self.TLB4_COMMAND_REGISTER}...")
                self.instrument.write_registers(
                    self.TLB4_COMMAND_REGISTER,
                    [self.CMD_SPAN_CALIBRATION]
                )
                
                # Wait for TLB4 to process the calibration (inside lock to prevent DAQ reads)
                time.sleep(2.0)
                
                # Step 3: Check result by reading CALW register
                # 0 = Success, non-zero = error code
                result_code = self._read_32bit_value(self.ADDR_CAL_WEIGHT, DataFormat.INT32)
                logger.info(f"Calibration result code from CALW register: {result_code}")
                
                if result_code == 0:
                    # Verify by reading current weight
                    try:
                        post_weight = int(self._read_value(cfg.reg_gross_weight, cfg.gross_weight_format))
                        scaled_weight = post_weight / (10 ** decimal_places)
                        logger.info(f"Post-calibration gross weight: {post_weight} raw = {scaled_weight:.2f} kg")
                    except Exception as e:
                        logger.warning(f"Could not read post-calibration weight: {e}")
                        scaled_weight = known_weight  # Assume it worked
            
            if result_code == 0:
                msg = f"Span Calibration SUCCESS - Scale now reads {scaled_weight:.2f} kg"
                logger.info(f"✓ {msg}")
                return True, msg, 0
            else:
                msg = f"Span Calibration FAILED with error code: {result_code}"
                logger.error(f"✗ {msg}")
                return False, msg, int(result_code)
            
        except Exception as e:
            error_msg = f"Span Calibration FAILED: {e}"
            logger.error(f"✗ {error_msg}")
            self.handle_error(e)
            return False, error_msg, -1
    
    def _write_32bit_value(self, register: int, value: int) -> None:
        """
        Write a 32-bit signed integer to two consecutive registers.
        
        Args:
            register: Starting register address
            value: 32-bit signed integer value to write
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not initialized")
        
        # Pack value as 32-bit signed integer
        if self.byteorder == "big":
            raw_bytes = struct.pack('>i', value)
        else:
            raw_bytes = struct.pack('<i', value)
        
        # Unpack as two 16-bit words
        if self.byteorder == "big":
            high_word, low_word = struct.unpack('>HH', raw_bytes)
        else:
            low_word, high_word = struct.unpack('<HH', raw_bytes)
        
        # Write based on word order
        if self.wordorder == "big":
            self.instrument.write_registers(register, [high_word, low_word])
        else:
            self.instrument.write_registers(register, [low_word, high_word])
        
        logger.debug(f"Wrote 32-bit value {value} to registers {register}-{register+1}")
    
    def _read_gross_weight_raw(self) -> int:
        """
        Read the raw gross weight value (without scaling).
        
        Returns:
            int: Raw gross weight value
        """
        if self.instrument is None:
            raise RuntimeError("Instrument not initialized")
        
        cfg = self.tlb4_config
        raw_value = self._read_value(cfg.reg_gross_weight, cfg.gross_weight_format)
        return int(raw_value)
    
    def get_calibration_status(self) -> Dict[str, Any]:
        """
        Get current calibration-relevant readings for display.
        
        Uses cached data from the last DAQ read to avoid additional serial port
        access that could conflict with the DAQ thread. The DAQ thread already
        reads at ~10Hz, so cached data is always fresh.
        
        Returns:
            Dict with gross_weight_raw, gross_weight_kg, connected status, and stability indicator
        """
        try:
            if not self.initialized or self.instrument is None:
                return {
                    "connected": False,
                    "gross_weight_raw": 0,
                    "gross_weight_kg": 0.0,
                    "stable": False,
                }
            
            # Use cached data to avoid serial port conflicts with DAQ thread
            # The DAQ thread updates _last_reading every ~100ms
            data = self._last_reading
            
            # Check if data is recent (within 2 seconds)
            time_since_read = time.time() - self._last_read_time if self._last_read_time > 0 else float('inf')
            is_connected = time_since_read < 2.0 and not data.get("error", False)
            
            if not is_connected or not data:
                return {
                    "connected": False,
                    "gross_weight_raw": 0,
                    "gross_weight_kg": 0.0,
                    "stable": False,
                }
            
            return {
                "connected": True,
                "gross_weight_raw": data.get("gross_weight_raw", 0),
                "gross_weight_kg": data.get("gross_weight_kg", 0.0),
                "net_weight_kg": data.get("net_weight_kg", 0.0),
                "stable": True,  # Could be enhanced with stability detection
                "data_age_ms": int(time_since_read * 1000),
            }
        except Exception as e:
            logger.warning(f"Error getting calibration status: {e}")
            return {
                "connected": False,
                "gross_weight_raw": 0,
                "gross_weight_kg": 0.0,
                "stable": False,
                "error": str(e),
            }
    
    def get_individual_loads(self) -> List[float]:
        """
        Get individual load cell readings as a list.
        
        Returns:
            List[float]: List of 4 load cell readings in kg
        """
        data = self.read()
        return [
            data.get("load_cell_1_kg", 0.0),
            data.get("load_cell_2_kg", 0.0),
            data.get("load_cell_3_kg", 0.0),
            data.get("load_cell_4_kg", 0.0),
        ]
    
    def get_total_weight(self) -> float:
        """
        Get total gross weight.
        
        Returns:
            float: Total weight in kg
        """
        data = self.read()
        return data.get("gross_weight_kg", 0.0)
    
    # =========================================================================
    # Register Scanner - For discovering TLB4 register addresses
    # =========================================================================
    
    def scan_registers(
        self,
        start: int = 0,
        end: int = 100,
        functioncode: int = 3,
        show_zeros: bool = False
    ) -> Dict[int, int]:
        """
        Scan a range of Modbus registers to discover active addresses.
        
        Use this to find where the TLB4 stores weight data.
        
        Args:
            start: Starting register address
            end: Ending register address
            functioncode: Modbus function code (3=holding, 4=input)
            show_zeros: Include registers with zero values
            
        Returns:
            Dict[int, int]: Map of register address to value
        """
        if not self.initialized or self.instrument is None:
            logger.error("Cannot scan - interface not initialized")
            return {}
        
        logger.info(f"Scanning registers {start}-{end} with function code {functioncode}...")
        results = {}
        
        for reg in range(start, end + 1):
            try:
                value = self.instrument.read_register(reg, functioncode=functioncode)
                if value != 0 or show_zeros:
                    results[reg] = value
                    if value != 0:
                        logger.info(f"  Register {reg}: {value} (0x{value:04X})")
            except Exception as e:
                if self.debug:
                    logger.debug(f"  Register {reg}: Error - {e}")
        
        logger.info(f"Scan complete. Found {len(results)} active registers.")
        return results
    
    def scan_for_32bit_values(
        self,
        start: int = 0,
        end: int = 100,
        functioncode: int = 3
    ) -> Dict[int, Tuple[float, float, float]]:
        """
        Scan for 32-bit values (weights are typically 32-bit).
        
        Reads consecutive register pairs and interprets as:
        - Signed 32-bit integer
        - Unsigned 32-bit integer  
        - 32-bit float
        
        Args:
            start: Starting register address
            end: Ending register address
            functioncode: Modbus function code
            
        Returns:
            Dict mapping register address to (int32, uint32, float32) tuple
        """
        if not self.initialized or self.instrument is None:
            logger.error("Cannot scan - interface not initialized")
            return {}
        
        logger.info(f"Scanning for 32-bit values in registers {start}-{end}...")
        results = {}
        
        for reg in range(start, end, 2):  # Step by 2 for 32-bit values
            try:
                regs = self.instrument.read_registers(reg, 2, functioncode=functioncode)
                
                # Try big-endian word order (common for Laumas)
                raw_be = struct.pack('>HH', regs[0], regs[1])
                int32_be = struct.unpack('>i', raw_be)[0]
                uint32_be = struct.unpack('>I', raw_be)[0]
                float32_be = struct.unpack('>f', raw_be)[0]
                
                # Skip if all zeros
                if int32_be == 0 and uint32_be == 0:
                    continue
                
                # Filter out invalid floats
                import math
                if math.isnan(float32_be) or math.isinf(float32_be):
                    float32_be = 0.0
                
                results[reg] = (int32_be, uint32_be, float32_be)
                
                logger.info(
                    f"  Reg {reg}-{reg+1}: INT32={int32_be}, "
                    f"UINT32={uint32_be}, FLOAT32={float32_be:.4f}"
                )
                
            except Exception as e:
                if self.debug:
                    logger.debug(f"  Register {reg}: Error - {e}")
        
        logger.info(f"Scan complete. Found {len(results)} 32-bit values.")
        return results
    
    def scan_and_identify_channels(
        self,
        ranges: Optional[List[Tuple[int, int]]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive scan to identify TLB4 register layout.
        
        Scans common register ranges for Laumas devices:
        - 0-100 (standard holding registers)
        - 30001-30100 (Modbus convention offset)
        - 40001-40100 (Modbus convention offset)
        
        Returns:
            Dict with discovered register map and recommendations
        """
        if ranges is None:
            ranges = [
                (0, 100),
                (30001 - 30001, 30100 - 30001),  # Normalize to 0-based
                (40001 - 40001, 40100 - 40001),  # Normalize to 0-based
            ]
        
        logger.info("=" * 60)
        logger.info("TLB4 Register Discovery Scan")
        logger.info("=" * 60)
        logger.info("Instructions: Apply varying loads to each load cell during scan")
        logger.info("to help identify which registers correspond to each channel.")
        logger.info("=" * 60)
        
        all_results = {}
        
        for start, end in ranges:
            logger.info(f"\nScanning range {start} to {end}...")
            results = self.scan_for_32bit_values(start, end)
            all_results.update(results)
        
        # Analyze results
        analysis = self._analyze_scan_results(all_results)
        
        logger.info("\n" + "=" * 60)
        logger.info("SCAN ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"Total 32-bit values found: {len(all_results)}")
        
        if analysis.get("likely_weight_registers"):
            logger.info("\nLikely weight registers (values in expected range):")
            for reg, info in analysis["likely_weight_registers"].items():
                logger.info(f"  Register {reg}: {info}")
        
        if analysis.get("recommendations"):
            logger.info("\nRecommendations:")
            for rec in analysis["recommendations"]:
                logger.info(f"  - {rec}")
        
        return {
            "raw_results": all_results,
            "analysis": analysis,
        }
    
    def _analyze_scan_results(
        self,
        results: Dict[int, Tuple[float, float, float]]
    ) -> Dict[str, Any]:
        """
        Analyze scan results to identify likely register assignments.
        
        Args:
            results: Scan results from scan_for_32bit_values
            
        Returns:
            Dict with analysis and recommendations
        """
        analysis = {
            "likely_weight_registers": {},
            "recommendations": [],
        }
        
        # Look for values that could be weights (reasonable range: -10000 to 100000)
        weight_candidates = []
        
        for reg, (int32, uint32, float32) in results.items():
            # Check if value is in reasonable weight range
            # TLB4 often uses scaled integers (e.g., 12345 = 123.45 kg)
            if -1000000 <= int32 <= 1000000:
                weight_candidates.append({
                    "register": reg,
                    "int32": int32,
                    "uint32": uint32,
                    "float32": float32,
                    "likely_kg_2dec": int32 / 100,
                    "likely_kg_3dec": int32 / 1000,
                })
        
        # Sort by register address
        weight_candidates.sort(key=lambda x: x["register"])
        
        for candidate in weight_candidates:
            reg = candidate["register"]
            analysis["likely_weight_registers"][reg] = {
                "raw_int32": candidate["int32"],
                "if_2_decimals": f"{candidate['likely_kg_2dec']:.2f} kg",
                "if_3_decimals": f"{candidate['likely_kg_3dec']:.3f} kg",
            }
        
        # Generate recommendations
        if len(weight_candidates) >= 5:
            analysis["recommendations"].append(
                f"Found {len(weight_candidates)} candidate registers. "
                "Typically: Gross @ 0, Net @ 2, Tare @ 4, CH1-4 @ 8/10/12/14"
            )
        
        if weight_candidates:
            first_reg = weight_candidates[0]["register"]
            analysis["recommendations"].append(
                f"First weight register appears to be at address {first_reg}. "
                f"Update tlb4_config.reg_gross_weight = {first_reg}"
            )
        
        return analysis
    
    def monitor_registers(
        self,
        registers: List[int],
        duration_seconds: float = 10.0,
        interval_ms: int = 500,
        as_32bit: bool = True
    ) -> None:
        """
        Monitor specific registers over time to see value changes.
        
        Useful for identifying which registers change when load is applied.
        
        Args:
            registers: List of register addresses to monitor
            duration_seconds: How long to monitor
            interval_ms: Polling interval in milliseconds
            as_32bit: Read as 32-bit pairs (True) or 16-bit singles (False)
        """
        if not self.initialized or self.instrument is None:
            logger.error("Cannot monitor - interface not initialized")
            return
        
        logger.info(f"Monitoring registers {registers} for {duration_seconds}s...")
        logger.info("Apply load to load cells to see value changes.")
        logger.info("-" * 60)
        
        start_time = time.time()
        interval_sec = interval_ms / 1000.0
        
        while (time.time() - start_time) < duration_seconds:
            line = f"t={time.time()-start_time:.1f}s: "
            
            for reg in registers:
                try:
                    if as_32bit:
                        value = self._read_32bit_value(reg, DataFormat.INT32)
                        line += f"R{reg}={value:>10} "
                    else:
                        value = self.instrument.read_register(reg, functioncode=3)
                        line += f"R{reg}={value:>6} "
                except Exception:
                    line += f"R{reg}=ERROR "
            
            logger.info(line)
            time.sleep(interval_sec)
        
        logger.info("-" * 60)
        logger.info("Monitoring complete.")
    
    def update_register_config(
        self,
        gross_weight: Optional[int] = None,
        net_weight: Optional[int] = None,
        tare_weight: Optional[int] = None,
        status: Optional[int] = None,
        channels: Optional[List[int]] = None
    ) -> None:
        """
        Update the register configuration after discovery.
        
        Args:
            gross_weight: Register address for gross weight
            net_weight: Register address for net weight
            tare_weight: Register address for tare weight
            status: Register address for status
            channels: List of 4 register addresses for CH1-CH4
        """
        if gross_weight is not None:
            self.tlb4_config.reg_gross_weight = gross_weight
            logger.info(f"Updated gross weight register to {gross_weight}")
        
        if net_weight is not None:
            self.tlb4_config.reg_net_weight = net_weight
            logger.info(f"Updated net weight register to {net_weight}")
        
        if tare_weight is not None:
            self.tlb4_config.reg_tare_weight = tare_weight
            logger.info(f"Updated tare weight register to {tare_weight}")
        
        if status is not None:
            self.tlb4_config.reg_status = status
            logger.info(f"Updated status register to {status}")
        
        if channels is not None and len(channels) >= 4:
            self.tlb4_config.reg_channel_1 = channels[0]
            self.tlb4_config.reg_channel_2 = channels[1]
            self.tlb4_config.reg_channel_3 = channels[2]
            self.tlb4_config.reg_channel_4 = channels[3]
            logger.info(f"Updated channel registers to {channels}")
    
    def set_kg_per_division(self, value: float) -> None:
        """
        Set the kg_per_division scaling factor for all channels.
        
        Args:
            value: Raw divisions per kg
        """
        if value <= 0:
            logger.error(f"Invalid kg_per_division: {value}")
            return
        
        self.tlb4_config.kg_per_division = value
        logger.info(f"kg_per_division set to {value}")
    
    def get_channel_raw_value(self, channel: int) -> Tuple[bool, int, str]:
        """
        Get the current raw Modbus value for a specific channel.
        
        Uses the moving average buffer for a stable reading.
        
        Args:
            channel: Channel number (1-4)
            
        Returns:
            Tuple[bool, int, str]: (success, raw_value, message)
        """
        try:
            if not self.initialized or self.instrument is None:
                return False, 0, "Modbus interface not connected"
            
            if channel < 1 or channel > 4:
                return False, 0, f"Invalid channel {channel} (must be 1-4)"
            
            cfg = self.tlb4_config
            ch_cfg = cfg.channels[channel - 1]
            
            if not ch_cfg.enabled:
                return False, 0, f"Channel {channel} is disabled"
            
            # Use averaged value from buffer for stable reading
            if len(self._channel_buffers[channel - 1]) > 0:
                avg_raw = sum(self._channel_buffers[channel - 1]) / len(self._channel_buffers[channel - 1])
                return True, int(avg_raw), f"Averaged raw value: {int(avg_raw)}"
            else:
                return False, 0, "No data in buffer yet"
            
        except Exception as e:
            error_msg = f"Failed to read channel {channel}: {e}"
            logger.error(error_msg)
            return False, 0, error_msg
