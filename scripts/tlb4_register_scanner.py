#!/usr/bin/env python3
"""
TLB4 Register Scanner - Discover Modbus Register Addresses

This script scans the Laumas TLB4 load cell transmitter to discover
the correct register addresses for weight data.

BEFORE RUNNING:
1. Ensure TLB4 is configured for Modbus RTU:
   - Protocol: Modbus
   - Baud Rate: 9600
   - Address: 1
   - Parity: None
   - Stop Bits: 1
   
2. Connect TLB4 via RS485 (terminals 29=A/+, 30=B/-)

3. Update the PORT variable below to match your USB-RS485 adapter

Usage:
    python scripts/tlb4_register_scanner.py [OPTIONS]

Options:
    --port PORT       Serial port (default: COM3 on Windows, /dev/ttyUSB0 on Linux)
    --address ADDR    Modbus slave address (default: 1)
    --scan-all        Perform comprehensive scan of all register ranges
    --monitor REGS    Monitor specific registers (comma-separated)
    --duration SEC    Duration for monitoring (default: 30)
"""

import argparse
import sys
import time
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from epdm_vacuum.daq.modbus_interface import ModbusInterface, TLB4Config


def detect_port() -> str:
    """Detect the most likely serial port for the USB-RS485 adapter."""
    import platform
    
    if platform.system() == "Windows":
        # Try common Windows COM ports
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        if ports:
            print("Available COM ports:")
            for p in ports:
                print(f"  {p.device}: {p.description}")
            
            # Return first available port
            return ports[0].device
        return "COM3"
    else:
        # Linux/Mac - try common USB serial paths
        candidates = [
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "/dev/ttyACM0",
            "/dev/ttyACM1",
            "/dev/serial0",
        ]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "/dev/ttyUSB0"


def scan_basic(interface: ModbusInterface) -> dict:
    """Perform basic register scan."""
    print("\n" + "=" * 70)
    print("BASIC REGISTER SCAN (0-50)")
    print("=" * 70)
    
    results = {}
    
    # Scan first 50 registers for 16-bit values
    print("\n16-bit Register Values:")
    print("-" * 40)
    
    for reg in range(51):
        try:
            value = interface.read_register(reg, signed=True)
            if value is not None and value != 0:
                print(f"  Register {reg:3d}: {value:>10} (0x{value & 0xFFFF:04X})")
                results[reg] = value
        except Exception as e:
            pass
    
    return results


def scan_32bit(interface: ModbusInterface) -> dict:
    """Scan for 32-bit values."""
    print("\n" + "=" * 70)
    print("32-BIT VALUE SCAN (0-50)")
    print("=" * 70)
    
    results = interface.scan_for_32bit_values(start=0, end=50)
    return results


def scan_comprehensive(interface: ModbusInterface) -> dict:
    """Perform comprehensive scan of all common register ranges."""
    print("\n" + "=" * 70)
    print("COMPREHENSIVE REGISTER SCAN")
    print("=" * 70)
    
    results = interface.scan_and_identify_channels()
    return results


def monitor_registers(
    interface: ModbusInterface,
    registers: list,
    duration: float,
    as_32bit: bool = False
) -> None:
    """Monitor specific registers for changes."""
    print("\n" + "=" * 70)
    print(f"MONITORING REGISTERS: {registers}")
    print(f"Duration: {duration} seconds")
    print(f"Mode: {'32-bit pairs' if as_32bit else '16-bit singles'}")
    print("=" * 70)
    print("\nApply varying loads to each load cell to identify channel registers.")
    print("Press Ctrl+C to stop early.\n")
    
    # Print header
    header = f"{'Time':>8} |"
    for reg in registers:
        if as_32bit:
            header += f" R{reg}-{reg+1}:{'':>8} |"
        else:
            header += f" R{reg}:{'':>4} |"
    print(header)
    print("-" * len(header))
    
    start_time = time.time()
    interval_sec = 0.5  # 500ms
    
    try:
        while (time.time() - start_time) < duration:
            elapsed = time.time() - start_time
            line = f"{elapsed:7.1f}s |"
            
            for reg in registers:
                try:
                    if as_32bit:
                        # Read as 32-bit (2 registers)
                        value = interface._read_32bit_value(reg)
                        line += f" {value:>14} |"
                    else:
                        # Read as 16-bit single register
                        value = interface.read_register(reg, signed=True)
                        if value is not None:
                            line += f" {value:>8} |"
                        else:
                            line += f" {'ERROR':>8} |"
                except Exception as e:
                    line += f" {'ERR':>8} |"
            
            print(line)
            time.sleep(interval_sec)
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    
    print("-" * 70)
    print("Monitoring complete.")


def interactive_mode(interface: ModbusInterface) -> None:
    """Interactive mode for manual register exploration."""
    print("\n" + "=" * 70)
    print("INTERACTIVE MODE")
    print("=" * 70)
    print("Commands:")
    print("  r <addr>        - Read single register (16-bit)")
    print("  r32 <addr>      - Read 32-bit value (2 registers)")
    print("  scan <s> <e>    - Scan range (16-bit)")
    print("  scan32 <s> <e>  - Scan range (32-bit)")
    print("  mon <r1,r2,...> - Monitor registers (Ctrl+C to stop)")
    print("  help            - Show commands")
    print("  quit            - Exit")
    print("-" * 70)
    
    while True:
        try:
            cmd = input("\n> ").strip().lower()
            
            if not cmd:
                continue
            
            parts = cmd.split()
            action = parts[0]
            
            if action == "quit" or action == "exit" or action == "q":
                break
            
            elif action == "help" or action == "?":
                print("Commands: r, r32, scan, scan32, mon, help, quit")
            
            elif action == "r" and len(parts) >= 2:
                addr = int(parts[1])
                val = interface.read_register(addr)
                print(f"Register {addr}: {val}")
            
            elif action == "r32" and len(parts) >= 2:
                addr = int(parts[1])
                val = interface._read_32bit_value(addr)
                print(f"Register {addr}-{addr+1} (32-bit): {val}")
            
            elif action == "scan" and len(parts) >= 3:
                start, end = int(parts[1]), int(parts[2])
                interface.scan_registers(start, end)
            
            elif action == "scan32" and len(parts) >= 3:
                start, end = int(parts[1]), int(parts[2])
                interface.scan_for_32bit_values(start, end)
            
            elif action == "mon" and len(parts) >= 2:
                regs = [int(r) for r in parts[1].split(",")]
                print("Monitoring... Press Ctrl+C to stop")
                try:
                    interface.monitor_registers(regs, 3600, 500, True)
                except KeyboardInterrupt:
                    print("\nStopped.")
            
            else:
                print(f"Unknown command: {cmd}")
                print("Type 'help' for available commands")
        
        except ValueError as ve:
            print(f"Invalid number: {ve}")
        except Exception as e:
            print(f"Error: {e}")


def print_setup_instructions():
    """Print TLB4 configuration instructions."""
    print("""
+======================================================================+
|                TLB4 MODBUS CONFIGURATION INSTRUCTIONS                |
+======================================================================+
|                                                                      |
|  Before using this scanner, configure the TLB4 device:               |
|                                                                      |
|  1. Enter Menu: Hold ENTER (Button 4) for 2 seconds                  |
|  2. Navigate to SERiAL using Arrow Up (Button 3), press ENTER        |
|  3. Select -S485 (RS485), press ENTER                                |
|  4. Set Protocol:                                                    |
|     - If display shows "nOnE", press Arrow Up until "ModbuS"         |
|     - Press ENTER                                                    |
|  5. Configure Parameters:                                            |
|     - bAud: 9600                                                     |
|     - Addr: 1                                                        |
|     - dELAY: 0                                                       |
|     - PArity: nOnE                                                   |
|     - StOP: 1                                                        |
|  6. Press ESC repeatedly to exit menu                                |
|                                                                      |
|  Wiring: Terminal 29 (A/+) and Terminal 30 (B/-)                     |
|                                                                      |
+======================================================================+
""")


def main():
    parser = argparse.ArgumentParser(
        description="TLB4 Load Cell Transmitter Register Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tlb4_register_scanner.py --port COM3
  python tlb4_register_scanner.py --scan-all
  python tlb4_register_scanner.py --monitor 0,2,8,10,12,14 --duration 60
  python tlb4_register_scanner.py --interactive
        """
    )
    
    parser.add_argument(
        "--port", "-p",
        default=None,
        help="Serial port (auto-detected if not specified)"
    )
    parser.add_argument(
        "--address", "-a",
        type=int,
        default=1,
        help="Modbus slave address (default: 1)"
    )
    parser.add_argument(
        "--baudrate", "-b",
        type=int,
        default=9600,
        help="Baud rate (default: 9600)"
    )
    parser.add_argument(
        "--scan-all",
        action="store_true",
        help="Perform comprehensive scan of all register ranges"
    )
    parser.add_argument(
        "--monitor", "-m",
        type=str,
        default=None,
        help="Monitor specific registers (comma-separated, e.g., 0,2,8,10)"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=30,
        help="Duration for monitoring in seconds (default: 30)"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Enter interactive mode for manual exploration"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output"
    )
    parser.add_argument(
        "--instructions",
        action="store_true",
        help="Show TLB4 setup instructions"
    )
    
    args = parser.parse_args()
    
    # Show instructions if requested
    if args.instructions:
        print_setup_instructions()
        return
    
    # Detect port if not specified
    port = args.port or detect_port()
    
    print(f"""
+======================================================================+
|              TLB4 MODBUS REGISTER SCANNER                            |
+======================================================================+
|  Port:     {port:<20}                                      |
|  Address:  {args.address:<20}                                      |
|  Baudrate: {args.baudrate:<20}                                      |
+======================================================================+
""")
    
    # Create interface
    interface = ModbusInterface(
        port=port,
        slave_address=args.address,
        baudrate=args.baudrate,
        parity="None",
        stopbits=1,
        debug=args.debug
    )
    
    # Connect
    print("Connecting to TLB4...")
    if not interface.connect():
        print("\n[ERROR] Failed to connect to TLB4!")
        print("\nTroubleshooting:")
        print("  1. Check USB-RS485 adapter connection")
        print("  2. Verify TLB4 is powered and configured for Modbus")
        print("  3. Check wiring: Terminal 29=A/+, Terminal 30=B/-")
        print("  4. Confirm correct COM port")
        print("\nRun with --instructions for TLB4 setup guide")
        return 1
    
    print("[OK] Connected successfully!\n")
    
    try:
        if args.interactive:
            interactive_mode(interface)
        
        elif args.monitor:
            regs = [int(r.strip()) for r in args.monitor.split(",")]
            monitor_registers(interface, regs, args.duration)
        
        elif args.scan_all:
            scan_comprehensive(interface)
        
        else:
            # Default: basic scan
            scan_basic(interface)
            scan_32bit(interface)
            
            print("\n" + "=" * 70)
            print("NEXT STEPS")
            print("=" * 70)
            print("""
1. Look for registers with values that seem like weights
   (TLB4 typically uses scaled integers, e.g., 12345 = 123.45 kg)

2. To identify individual channels, run with --monitor:
   python tlb4_register_scanner.py --monitor 0,2,4,6,8,10,12,14 --duration 60
   Then apply load to each cell individually.

3. Once you identify the registers, update hardware_config.yaml:
   modbus:
     tlb4_registers:
       gross_weight: <discovered_address>
       channel_1: <discovered_address>
       channel_2: <discovered_address>
       channel_3: <discovered_address>
       channel_4: <discovered_address>

4. For interactive exploration, run with --interactive
""")
    
    finally:
        interface.disconnect()
        print("\nDisconnected from TLB4.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

