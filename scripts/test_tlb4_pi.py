#!/usr/bin/env python3
"""
TLB4 Load Cell Transmitter - Raspberry Pi Connection Test

Quick diagnostic script to verify TLB4 Modbus communication is working
on Raspberry Pi before running the full GUI application.

Usage:
    python scripts/test_tlb4_pi.py                    # Default /dev/ttyUSB0
    python scripts/test_tlb4_pi.py --port /dev/ttyUSB1  # Custom port
    python scripts/test_tlb4_pi.py --scan             # Scan for registers
    python scripts/test_tlb4_pi.py --monitor          # Live monitoring

Prerequisites:
    1. TLB4 connected via USB-RS485 adapter
    2. User in 'dialout' group: sudo usermod -a -G dialout $USER
    3. TLB4 configured for Modbus RTU mode (9600, N, 8, 1)
"""

import argparse
import sys
import os
import time

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def check_serial_port(port: str) -> bool:
    """Check if serial port exists and is accessible."""
    import stat
    
    print(f"\n{'='*60}")
    print("SERIAL PORT CHECK")
    print(f"{'='*60}")
    
    if not os.path.exists(port):
        print(f"❌ Serial port NOT FOUND: {port}")
        print("\nAvailable serial ports:")
        for dev in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']:
            if os.path.exists(dev):
                print(f"  ✓ {dev}")
        return False
    
    print(f"✓ Serial port exists: {port}")
    
    # Check permissions
    try:
        mode = os.stat(port).st_mode
        if os.access(port, os.R_OK) and os.access(port, os.W_OK):
            print(f"✓ Read/write access OK")
            return True
        else:
            print(f"❌ Permission denied!")
            print("\nTo fix, add your user to the dialout group:")
            print(f"  sudo usermod -a -G dialout $USER")
            print("  (Then log out and back in)")
            return False
    except Exception as e:
        print(f"❌ Error checking port: {e}")
        return False


def test_basic_connection(port: str, address: int = 1) -> bool:
    """Test basic Modbus connection to TLB4."""
    from epdm_vacuum.daq.modbus_interface import ModbusInterface
    
    print(f"\n{'='*60}")
    print("TLB4 CONNECTION TEST")
    print(f"{'='*60}")
    print(f"Port: {port}")
    print(f"Slave Address: {address}")
    print(f"Baudrate: 9600")
    print()
    
    interface = ModbusInterface(
        port=port,
        slave_address=address,
        baudrate=9600,
        parity="None",
        stopbits=1,
        debug=False
    )
    
    print("Connecting to TLB4...")
    if not interface.connect():
        print("❌ Connection FAILED!")
        print("\nTroubleshooting:")
        print("  1. Check TLB4 is in Modbus mode (not 'nOnE')")
        print("  2. Verify RS485 wiring: Terminal 29 (A/+), 30 (B/-)")
        print("  3. Check baud rate is 9600 on TLB4")
        print("  4. Verify slave address matches TLB4 'Addr' setting")
        return False
    
    print("✓ Connected to TLB4!")
    
    # Try reading weight data
    print("\nReading weight data...")
    try:
        data = interface.read()
        
        if data.get('error'):
            print("❌ Read FAILED!")
            return False
        
        print(f"\n{'─'*40}")
        print("TLB4 WEIGHT DATA")
        print(f"{'─'*40}")
        print(f"Gross Weight:  {data.get('gross_weight_kg', 0):>10.2f} kg")
        print(f"Net Weight:    {data.get('net_weight_kg', 0):>10.2f} kg")
        print(f"Tare Weight:   {data.get('tare_weight_kg', 0):>10.2f} kg")
        print()
        print("Individual Channels:")
        for i in range(1, 5):
            raw = data.get(f'load_cell_{i}_raw', 0)
            kg = data.get(f'load_cell_{i}_kg', 0)
            status = "ACTIVE" if kg != 0 or raw != 0 else "(not connected)"
            print(f"  CH{i}: {kg:>8.2f} kg  (raw: {raw:>6})  {status}")
        
        print(f"\n✓ TLB4 communication successful!")
        return True
        
    except Exception as e:
        print(f"❌ Error reading data: {e}")
        return False
    
    finally:
        interface.disconnect()
        print("\nDisconnected from TLB4.")


def scan_registers(port: str, address: int = 1):
    """Scan TLB4 registers to discover active addresses."""
    from epdm_vacuum.daq.modbus_interface import ModbusInterface
    
    print(f"\n{'='*60}")
    print("TLB4 REGISTER SCAN")
    print(f"{'='*60}")
    
    interface = ModbusInterface(
        port=port,
        slave_address=address,
        baudrate=9600,
        debug=False
    )
    
    if not interface.connect():
        print("❌ Connection failed!")
        return
    
    try:
        print("\nScanning registers 0-50...")
        print("Apply varying load to identify channel registers.\n")
        
        results = interface.scan_registers(start=0, end=50, show_zeros=False)
        
        if results:
            print(f"\n{'─'*40}")
            print("ACTIVE REGISTERS")
            print(f"{'─'*40}")
            for reg, value in sorted(results.items()):
                # Try to interpret the value
                scaled = value / 100  # Assuming 2 decimal places
                print(f"  R{reg:>2}: {value:>6}  ({scaled:>8.2f} if 2 decimals)")
        else:
            print("No active registers found!")
            
    finally:
        interface.disconnect()


def monitor_live(port: str, address: int = 1, duration: float = 30.0):
    """Live monitoring of TLB4 readings."""
    from epdm_vacuum.daq.modbus_interface import ModbusInterface
    
    print(f"\n{'='*60}")
    print("TLB4 LIVE MONITORING")
    print(f"Duration: {duration} seconds (Ctrl+C to stop)")
    print(f"{'='*60}")
    
    interface = ModbusInterface(
        port=port,
        slave_address=address,
        baudrate=9600,
    )
    
    if not interface.connect():
        print("❌ Connection failed!")
        return
    
    print(f"\n{'Time':>6} | {'Gross':>10} | {'CH1':>8} | {'CH2':>8} | {'CH3':>8} | {'CH4':>8}")
    print("-" * 70)
    
    start_time = time.time()
    sample_count = 0
    
    try:
        while (time.time() - start_time) < duration:
            data = interface.read()
            
            elapsed = time.time() - start_time
            gross = data.get('gross_weight_kg', 0)
            ch1 = data.get('load_cell_1_kg', 0)
            ch2 = data.get('load_cell_2_kg', 0)
            ch3 = data.get('load_cell_3_kg', 0)
            ch4 = data.get('load_cell_4_kg', 0)
            
            print(f"{elapsed:6.1f} | {gross:10.2f} | {ch1:8.2f} | {ch2:8.2f} | {ch3:8.2f} | {ch4:8.2f}")
            
            sample_count += 1
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        print("\n\nStopped by user.")
    
    finally:
        interface.disconnect()
        print(f"\n{sample_count} samples recorded.")


def test_tare(port: str, address: int = 1):
    """Test tare command on TLB4."""
    from epdm_vacuum.daq.modbus_interface import ModbusInterface
    
    print(f"\n{'='*60}")
    print("TLB4 TARE TEST")
    print(f"{'='*60}")
    
    interface = ModbusInterface(
        port=port,
        slave_address=address,
        baudrate=9600,
    )
    
    if not interface.connect():
        print("❌ Connection failed!")
        return
    
    try:
        # Read before tare
        print("\nBefore tare:")
        data = interface.read()
        print(f"  Gross: {data.get('gross_weight_kg', 0):.2f} kg")
        print(f"  Net:   {data.get('net_weight_kg', 0):.2f} kg")
        
        # Execute tare
        print("\nExecuting tare command...")
        if interface.tare_load_cells():
            print("✓ Tare command sent!")
        else:
            print("❌ Tare command failed!")
            return
        
        # Wait for TLB4 to process
        time.sleep(0.5)
        
        # Read after tare
        print("\nAfter tare:")
        data = interface.read()
        print(f"  Gross: {data.get('gross_weight_kg', 0):.2f} kg")
        print(f"  Net:   {data.get('net_weight_kg', 0):.2f} kg")
        print(f"  Tare:  {data.get('tare_weight_kg', 0):.2f} kg")
        
    finally:
        interface.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="TLB4 Load Cell Transmitter - Raspberry Pi Connection Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python test_tlb4_pi.py                    # Basic connection test
    python test_tlb4_pi.py --port /dev/ttyUSB1  # Custom port
    python test_tlb4_pi.py --scan             # Scan for registers
    python test_tlb4_pi.py --monitor          # Live monitoring
    python test_tlb4_pi.py --tare             # Test tare function
        """
    )
    parser.add_argument(
        "--port", "-p",
        default="/dev/ttyUSB0",
        help="Serial port (default: /dev/ttyUSB0)"
    )
    parser.add_argument(
        "--address", "-a",
        type=int,
        default=1,
        help="Modbus slave address (default: 1)"
    )
    parser.add_argument(
        "--scan", "-s",
        action="store_true",
        help="Scan registers to discover addresses"
    )
    parser.add_argument(
        "--monitor", "-m",
        action="store_true",
        help="Live monitoring mode"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=30.0,
        help="Monitoring duration in seconds (default: 30)"
    )
    parser.add_argument(
        "--tare", "-t",
        action="store_true",
        help="Test tare function"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("TLB4 RASPBERRY PI DIAGNOSTIC TOOL")
    print("=" * 60)
    
    # First check if serial port is accessible
    if not check_serial_port(args.port):
        sys.exit(1)
    
    # Run requested test
    if args.scan:
        scan_registers(args.port, args.address)
    elif args.monitor:
        monitor_live(args.port, args.address, args.duration)
    elif args.tare:
        test_tare(args.port, args.address)
    else:
        # Default: basic connection test
        success = test_basic_connection(args.port, args.address)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()



