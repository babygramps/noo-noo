"""
LCD Display Interface - Serial communication with Arduino LCD controller.

Communicates with Arduino Nano connected to I2C LCD 1602 display.
Used to show real-time status updates during vacuum testing.

The 1602 LCD has 2 lines x 16 characters.
"""

import logging
import threading
import time
from typing import Optional, Tuple
import serial
import serial.tools.list_ports

logger = logging.getLogger(__name__)


class LCDInterface:
    """
    Interface for Arduino-based LCD display.
    
    Sends status messages to Arduino Nano via USB serial.
    The Arduino displays messages on I2C LCD 1602.
    
    Protocol:
        - Messages are newline-terminated
        - Format: "LINE1|LINE2" (pipe separates lines)
        - Special commands: CLEAR, PING, BACKLIGHT:ON/OFF, LINE1:text, LINE2:text
    """
    
    # Standard timeouts
    CONNECT_TIMEOUT = 5.0
    WRITE_TIMEOUT = 1.0
    READ_TIMEOUT = 1.0
    
    # LCD dimensions
    LCD_COLS = 16
    LCD_ROWS = 2
    
    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        auto_connect: bool = True,
    ):
        """
        Initialize LCD interface.
        
        Args:
            port: Serial port (e.g., '/dev/ttyUSB1' or 'COM5').
                  If None, will try to auto-detect Arduino.
            baudrate: Serial baud rate (default 115200)
            auto_connect: If True, connect immediately
        """
        self.port = port
        self.baudrate = baudrate
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._lock = threading.Lock()
        
        # Current display state (for caching)
        self._current_line1 = ""
        self._current_line2 = ""
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> bool:
        """
        Connect to the Arduino LCD controller.
        
        Returns:
            bool: True if connected successfully
        """
        with self._lock:
            if self._connected:
                return True
            
            # Auto-detect port if not specified
            port = self.port or self._find_arduino_port()
            if not port:
                logger.warning("[LCD] No Arduino port found or specified")
                return False
            
            try:
                logger.info(f"[LCD] Connecting to Arduino on {port} at {self.baudrate} baud")
                
                self._serial = serial.Serial(
                    port=port,
                    baudrate=self.baudrate,
                    timeout=self.READ_TIMEOUT,
                    write_timeout=self.WRITE_TIMEOUT,
                )
                
                # Wait for Arduino to reset (happens on serial connection)
                time.sleep(2.0)
                
                # Clear any startup messages
                self._serial.reset_input_buffer()
                
                # Test connection with ping
                if self._ping():
                    self._connected = True
                    self.port = port  # Store detected port
                    logger.info(f"[LCD] Connected to Arduino LCD on {port}")
                    return True
                else:
                    logger.warning(f"[LCD] Arduino on {port} did not respond to PING")
                    self._serial.close()
                    self._serial = None
                    return False
                    
            except serial.SerialException as e:
                logger.error(f"[LCD] Failed to connect to {port}: {e}")
                if self._serial:
                    try:
                        self._serial.close()
                    except Exception:
                        pass
                self._serial = None
                return False
    
    def disconnect(self) -> None:
        """Disconnect from the Arduino."""
        with self._lock:
            if self._serial:
                try:
                    # Clear display before disconnecting
                    self._send_raw("CLEAR")
                    self._serial.close()
                except Exception as e:
                    logger.error(f"[LCD] Error during disconnect: {e}")
                finally:
                    self._serial = None
            self._connected = False
            logger.info("[LCD] Disconnected")
    
    def is_connected(self) -> bool:
        """Check if connected to Arduino."""
        return self._connected and self._serial is not None and self._serial.is_open
    
    def _find_arduino_port(self) -> Optional[str]:
        """
        Auto-detect Arduino port.
        
        Returns:
            str: Port name if found, None otherwise
        """
        # Common Arduino USB identifiers
        arduino_vids = [
            0x2341,  # Arduino
            0x1A86,  # CH340 (common clone chip)
            0x0403,  # FTDI
            0x10C4,  # Silicon Labs CP210x
        ]
        
        arduino_descriptions = [
            "arduino",
            "ch340",
            "usb serial",
            "uart",
        ]
        
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Check VID
            if port.vid in arduino_vids:
                logger.info(f"[LCD] Found potential Arduino: {port.device} (VID={hex(port.vid)})")
                return port.device
            
            # Check description
            desc_lower = (port.description or "").lower()
            for keyword in arduino_descriptions:
                if keyword in desc_lower:
                    logger.info(f"[LCD] Found potential Arduino: {port.device} ({port.description})")
                    return port.device
        
        # Log available ports for debugging
        if ports:
            logger.debug("[LCD] Available serial ports:")
            for port in ports:
                logger.debug(f"  - {port.device}: {port.description} (VID={port.vid}, PID={port.pid})")
        else:
            logger.debug("[LCD] No serial ports found")
        
        return None
    
    def _ping(self) -> bool:
        """
        Ping the Arduino to verify connection.
        
        Returns:
            bool: True if Arduino responded with PONG
        """
        try:
            if not self._serial:
                return False
            
            self._serial.write(b"PING\n")
            self._serial.flush()
            
            # Read response (with timeout)
            start_time = time.time()
            while time.time() - start_time < 2.0:
                if self._serial.in_waiting > 0:
                    response = self._serial.readline().decode('utf-8', errors='ignore').strip()
                    if response == "PONG":
                        return True
                    elif response == "READY":
                        # Arduino just reset, try ping again
                        self._serial.write(b"PING\n")
                        self._serial.flush()
                time.sleep(0.1)
            
            return False
        except Exception as e:
            logger.error(f"[LCD] Ping failed: {e}")
            return False
    
    def _send_raw(self, message: str) -> bool:
        """
        Send raw message to Arduino (internal use).
        
        Args:
            message: Message to send (without newline)
        
        Returns:
            bool: True if sent successfully
        """
        if not self._serial or not self._serial.is_open:
            return False
        
        try:
            self._serial.write(f"{message}\n".encode('utf-8'))
            self._serial.flush()
            return True
        except Exception as e:
            logger.error(f"[LCD] Send failed: {e}")
            return False
    
    def _send(self, message: str) -> bool:
        """
        Thread-safe message send with connection check.
        
        Args:
            message: Message to send
        
        Returns:
            bool: True if sent successfully
        """
        with self._lock:
            if not self.is_connected():
                logger.debug("[LCD] Not connected, message dropped")
                return False
            
            return self._send_raw(message)
    
    def display(self, line1: str, line2: str = "") -> bool:
        """
        Display text on the LCD.
        
        Args:
            line1: Text for first line (max 16 chars)
            line2: Text for second line (max 16 chars)
        
        Returns:
            bool: True if sent successfully
        """
        # Truncate to LCD width
        line1 = line1[:self.LCD_COLS]
        line2 = line2[:self.LCD_COLS]
        
        # Skip if unchanged (reduce serial traffic)
        if line1 == self._current_line1 and line2 == self._current_line2:
            return True
        
        message = f"{line1}|{line2}"
        success = self._send(message)
        
        if success:
            self._current_line1 = line1
            self._current_line2 = line2
            logger.debug(f"[LCD] Display: '{line1}' | '{line2}'")
        
        return success
    
    def display_line(self, line_num: int, text: str) -> bool:
        """
        Update a single line on the display.
        
        Args:
            line_num: Line number (0 or 1)
            text: Text to display (max 16 chars)
        
        Returns:
            bool: True if sent successfully
        """
        text = text[:self.LCD_COLS]
        
        if line_num == 0:
            if text == self._current_line1:
                return True
            command = f"LINE1:{text}"
            self._current_line1 = text
        elif line_num == 1:
            if text == self._current_line2:
                return True
            command = f"LINE2:{text}"
            self._current_line2 = text
        else:
            logger.error(f"[LCD] Invalid line number: {line_num}")
            return False
        
        success = self._send(command)
        if success:
            logger.debug(f"[LCD] Line {line_num + 1}: '{text}'")
        return success
    
    def clear(self) -> bool:
        """
        Clear the display.
        
        Returns:
            bool: True if sent successfully
        """
        success = self._send("CLEAR")
        if success:
            self._current_line1 = ""
            self._current_line2 = ""
            logger.debug("[LCD] Display cleared")
        return success
    
    def set_backlight(self, on: bool) -> bool:
        """
        Control the LCD backlight.
        
        Args:
            on: True to turn on, False to turn off
        
        Returns:
            bool: True if sent successfully
        """
        command = "BACKLIGHT:ON" if on else "BACKLIGHT:OFF"
        success = self._send(command)
        if success:
            logger.debug(f"[LCD] Backlight {'ON' if on else 'OFF'}")
        return success
    
    def scroll(self, line1: str, line2: str = "") -> bool:
        """
        Display text with auto-scrolling for long text.
        
        The Arduino will scroll text that exceeds 16 characters,
        pausing at start and end before looping.
        
        Args:
            line1: Text for first line (can exceed 16 chars)
            line2: Text for second line (can exceed 16 chars)
        
        Returns:
            bool: True if sent successfully
        """
        # Limit to Arduino buffer size
        line1 = line1[:180]
        line2 = line2[:180]
        
        message = f"SCROLL:{line1}|{line2}"
        success = self._send(message)
        
        if success:
            # Clear cache since scrolling is dynamic
            self._current_line1 = ""
            self._current_line2 = ""
            logger.debug(f"[LCD] Scroll: '{line1[:30]}...' | '{line2[:30]}...'")
        
        return success
    
    def stop_scroll(self) -> bool:
        """
        Stop scrolling and return to static display mode.
        
        Returns:
            bool: True if sent successfully
        """
        success = self._send("NOSCROLL")
        if success:
            logger.debug("[LCD] Scroll stopped")
        return success
    
    # === Convenience methods for common status displays ===
    
    def show_status(self, status: str, detail: str = "") -> bool:
        """
        Show a status message.
        
        Args:
            status: Main status text (line 1)
            detail: Additional detail (line 2)
        
        Returns:
            bool: True if sent successfully
        """
        return self.display(status, detail)
    
    def show_vacuum(self, vacuum_bar: float, status: str = "") -> bool:
        """
        Display vacuum reading.
        
        Args:
            vacuum_bar: Vacuum in bar
            status: Optional status text for line 2
        
        Returns:
            bool: True if sent successfully
        """
        line1 = f"Vacuum: {vacuum_bar:.3f} bar"
        return self.display(line1, status)
    
    def show_test_stage(self, stage_name: str, progress: float, cycle: int = 0, total_cycles: int = 0) -> bool:
        """
        Display test stage with progress.
        
        Args:
            stage_name: Name of current stage
            progress: Progress percentage (0.0 to 1.0)
            cycle: Current cycle number (0 if not cycling)
            total_cycles: Total cycles (0 if not cycling)
        
        Returns:
            bool: True if sent successfully
        """
        # Format stage name (truncate if needed)
        if len(stage_name) > 16:
            stage_name = stage_name[:15] + "."
        
        # Format progress line
        if total_cycles > 1:
            line2 = f"{int(progress * 100):3d}% C{cycle}/{total_cycles}"
        else:
            # Create a simple progress bar
            bar_width = 10
            filled = int(progress * bar_width)
            bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"
            line2 = f"{bar} {int(progress * 100):3d}%"
        
        return self.display(stage_name, line2)
    
    def show_error(self, error_msg: str) -> bool:
        """
        Display error message.
        
        Args:
            error_msg: Error message (will be truncated to fit)
        
        Returns:
            bool: True if sent successfully
        """
        # Split long messages across two lines
        if len(error_msg) <= 16:
            return self.display("ERROR:", error_msg)
        else:
            return self.display(error_msg[:16], error_msg[16:32])
    
    def show_idle(self) -> bool:
        """Display idle/ready status."""
        return self.display("EPDM Vacuum Test", "Ready")


def create_lcd_interface_from_config(config: dict) -> Optional[LCDInterface]:
    """
    Create LCD interface from configuration dictionary.
    
    Args:
        config: Configuration dict with 'lcd' section
    
    Returns:
        LCDInterface if configured and connected, None otherwise
    """
    lcd_config = config.get("lcd", {})
    
    if not lcd_config.get("enabled", False):
        logger.info("[LCD] LCD display disabled in config")
        return None
    
    port = lcd_config.get("port")  # Can be None for auto-detect
    baudrate = lcd_config.get("baudrate", 115200)
    
    interface = LCDInterface(
        port=port,
        baudrate=baudrate,
        auto_connect=True,
    )
    
    if interface.is_connected():
        return interface
    else:
        logger.warning("[LCD] Failed to connect to LCD display")
        return None


# Convenience function for listing available ports
def list_serial_ports() -> list:
    """
    List available serial ports (useful for debugging).
    
    Returns:
        List of dicts with port info
    """
    ports = []
    for port in serial.tools.list_ports.comports():
        ports.append({
            "device": port.device,
            "description": port.description,
            "vid": hex(port.vid) if port.vid else None,
            "pid": hex(port.pid) if port.pid else None,
            "serial_number": port.serial_number,
        })
    return ports
