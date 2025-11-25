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
    """Configuration for a single load cell channel."""
    
    # Register address for this channel's divisions/raw value
    register_address: int = 0
    
    # Scaling parameters for Division-to-kg conversion
    # Formula: Load_kg = (Channel_Value / full_scale_divisions) * load_cell_capacity_kg
    full_scale_divisions: float = 10000.0
    load_cell_capacity_kg: float = 250.0
    
    # Data format for this channel
    data_format: DataFormat = DataFormat.INT32
    
    # Offset for calibration
    zero_offset: float = 0.0
    
    # Whether this channel is enabled
    enabled: bool = True


@dataclass
class TLB4Config:
    """Complete configuration for TLB4 transmitter."""
    
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
        
        for i, (reg, ch_cfg) in enumerate(zip(channel_regs, cfg.channels), start=1):
            try:
                if ch_cfg.enabled:
                    raw_value = self._read_value(reg, ch_cfg.data_format)
                    result[f"load_cell_{i}_raw"] = raw_value
                    
                    # Convert divisions to kg
                    kg_value = self._convert_divisions_to_kg(
                        raw_value,
                        ch_cfg.full_scale_divisions,
                        ch_cfg.load_cell_capacity_kg,
                        ch_cfg.zero_offset
                    )
                    # Apply software tare offset (TLB4 only tares total, not channels)
                    kg_value -= self._channel_tare_offsets[i - 1]
                    result[f"load_cell_{i}_kg"] = kg_value
                else:
                    result[f"load_cell_{i}_raw"] = 0
                    result[f"load_cell_{i}_kg"] = 0.0
            except Exception as e:
                logger.debug(f"Failed to read channel {i}: {e}")
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
    
    def _convert_divisions_to_kg(
        self,
        divisions: float,
        full_scale_divisions: float,
        load_cell_capacity_kg: float,
        zero_offset: float = 0.0
    ) -> float:
        """
        Convert raw division value to kg.
        
        Formula: Load_kg = ((divisions - offset) / full_scale) * capacity
        
        Args:
            divisions: Raw division value from TLB4
            full_scale_divisions: Number of divisions at full scale
            load_cell_capacity_kg: Load cell capacity in kg
            zero_offset: Zero offset in divisions
            
        Returns:
            float: Weight in kg
        """
        if full_scale_divisions == 0:
            return 0.0
        
        adjusted = divisions - zero_offset
        return (adjusted / full_scale_divisions) * load_cell_capacity_kg
    
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
        
        Returns:
            bool: True if device is responding
        """
        try:
            if not self.initialized or self.instrument is None:
                return False
            
            # Try reading a register to verify connection
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
    CMD_TARE = 7      # Semi-Automatic Tare (sets current weight as tare, shows Net)
    CMD_ZERO = 8      # Zero (small variations only)
    CMD_GROSS = 9     # Switch back to Gross Weight display
    
    def _write_command(self, command: int) -> bool:
        """
        Write a command to the TLB4 command register.
        
        TLB4 only supports Function 16 (Write Multiple Registers), not Function 6.
        Uses write_registers() to write a single value using FC16.
        Uses a lock to prevent collision with DAQ read operations.
        
        Args:
            command: Command value to write (7=tare, 8=zero, 9=gross)
            
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
    
    def tare_load_cells(self) -> bool:
        """
        Execute Semi-Automatic Tare on TLB4.
        
        Writes command 7 to register 5 (40006) to tare the scale.
        This sets the current weight as the tare value and displays Net Weight.
        
        Also applies software tare to individual channel readings, since
        the TLB4 hardware tare only affects the total weight, not channels.
        
        Note: Tare will fail if:
        - Weight is unstable
        - Gross weight is 0 (displays In2Er0)
        - Tare value is lost on power cycle (use preset tare reg 72 for permanent)
        
        Returns:
            bool: True if tare command sent successfully
        """
        try:
            logger.info("Executing Semi-Automatic Tare on TLB4...")
            
            # Capture current channel values for software tare BEFORE hardware tare
            # Read current values while holding the lock
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
                            raw_value = self._read_value(reg, ch_cfg.data_format)
                            # Convert to kg for the tare offset
                            kg_value = self._convert_divisions_to_kg(
                                raw_value,
                                ch_cfg.full_scale_divisions,
                                ch_cfg.load_cell_capacity_kg,
                                ch_cfg.zero_offset
                            )
                            self._channel_tare_offsets[i] = kg_value
                            logger.debug(f"Channel {i+1} software tare offset: {kg_value:.2f} kg")
                    except Exception as e:
                        logger.warning(f"Failed to capture channel {i+1} tare offset: {e}")
                        self._channel_tare_offsets[i] = 0.0
            
            logger.info(f"Software tare offsets captured: {self._channel_tare_offsets}")
            
            # Small delay to let any pending read complete
            time.sleep(0.1)
            
            # Write command 7 to register 5 (40006) using Function 16
            self._write_command(self.CMD_TARE)
            
            logger.info("Tare command sent successfully to register 5 (value=7)")
            return True
            
        except Exception as e:
            self.handle_error(e)
            logger.error("Tare failed - weight may be unstable or gross weight is 0")
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
    
    def update_channel_scaling(
        self,
        channel: int,
        full_scale_divisions: Optional[float] = None,
        load_cell_capacity_kg: Optional[float] = None,
        zero_offset: Optional[float] = None
    ) -> None:
        """
        Update scaling parameters for a specific channel.
        
        Args:
            channel: Channel number (1-4)
            full_scale_divisions: Divisions at full scale
            load_cell_capacity_kg: Load cell capacity in kg
            zero_offset: Zero offset in divisions
        """
        if channel < 1 or channel > 4:
            logger.error(f"Invalid channel number: {channel}")
            return
        
        ch_cfg = self.tlb4_config.channels[channel - 1]
        
        if full_scale_divisions is not None:
            ch_cfg.full_scale_divisions = full_scale_divisions
        
        if load_cell_capacity_kg is not None:
            ch_cfg.load_cell_capacity_kg = load_cell_capacity_kg
        
        if zero_offset is not None:
            ch_cfg.zero_offset = zero_offset
        
        logger.info(
            f"Channel {channel} scaling updated: "
            f"FS={ch_cfg.full_scale_divisions}, "
            f"Cap={ch_cfg.load_cell_capacity_kg}kg, "
            f"Offset={ch_cfg.zero_offset}"
        )
