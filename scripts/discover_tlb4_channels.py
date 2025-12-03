#!/usr/bin/env python3
"""
TLB4 Individual Channel Discovery Script (Standalone)

This script helps discover where the TLB4 stores individual load cell channel values.
Run this while applying load to each load cell individually to identify which registers
correspond to which channels.

Based on TLB4 Modbus documentation:
- Standard registers (40001-40074) include combined weights
- Individual channel values may be in R1-R14 (40051-40064) or extended registers

Usage:
    python scripts/discover_tlb4_channels.py --port /dev/ttyUSB0
    
    1. Start with no load on any cell
    2. Apply load to LC1 only - note which registers change
    3. Remove LC1 load, apply to LC2 - note which registers change
    4. Use the discovered registers in hardware_config.yaml

This is a standalone script that only requires minimalmodbus and pyserial.
"""

import argparse
import sys
import time
import os

# Check for required dependencies
try:
    import minimalmodbus
    import serial
except ImportError as e:
    print(f"Missing dependency: {e}")
    print("Install with: pip install minimalmodbus pyserial")
    sys.exit(1)


class SimpleTLB4:
    """Minimal TLB4 interface for register discovery."""
    
    # Command register and commands
    ADDR_CMD_REG = 5          # Register 40006
    CMD_ENABLE_HIRES = 25     # Enable 4x HiRes Channel Reading
    
    def __init__(self, port: str, address: int = 1, baudrate: int = 9600):
        self.port = port
        self.address = address
        self.baudrate = baudrate
        self.instrument = None
    
    def connect(self) -> bool:
        """Connect to the TLB4."""
        try:
            self.instrument = minimalmodbus.Instrument(
                port=self.port,
                slaveaddress=self.address,
                mode=minimalmodbus.MODE_RTU,
                close_port_after_each_call=False,
                debug=False
            )
            self.instrument.serial.baudrate = self.baudrate
            self.instrument.serial.bytesize = 8
            self.instrument.serial.parity = serial.PARITY_NONE
            self.instrument.serial.stopbits = serial.STOPBITS_ONE
            self.instrument.serial.timeout = 1.0
            
            # Test read
            try:
                self.instrument.read_register(0, functioncode=3)
            except Exception:
                pass  # May fail but connection might still work
            
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def enable_multichannel_mode(self) -> bool:
        """
        Send Command 25 to enable individual channel readings.
        
        This is REQUIRED to see individual load cell data!
        After this command, registers 40051-40058 will contain
        32-bit raw division values for channels 1-4.
        """
        if not self.instrument:
            return False
        try:
            print("Sending Command 25 (Enable HiRes Multi-Channel Mode)...")
            # TLB4 requires Function 16 (write multiple registers)
            self.instrument.write_registers(self.ADDR_CMD_REG, [self.CMD_ENABLE_HIRES])
            time.sleep(0.5)  # Give TLB4 time to switch modes
            print("✓ Multi-channel mode enabled!")
            print("  Channel data now available at registers 40051-40058")
            return True
        except Exception as e:
            print(f"✗ Failed to enable multi-channel mode: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from TLB4."""
        if self.instrument and hasattr(self.instrument, 'serial'):
            if self.instrument.serial.is_open:
                self.instrument.serial.close()
        self.instrument = None
    
    def read_register(self, address: int, signed: bool = True) -> int:
        """Read a single 16-bit register."""
        if not self.instrument:
            return None
        try:
            return self.instrument.read_register(address, functioncode=3, signed=signed)
        except Exception:
            return None
    
    def read_32bit(self, address: int) -> int:
        """Read a 32-bit value from two consecutive registers."""
        if not self.instrument:
            return None
        try:
            regs = self.instrument.read_registers(address, 2, functioncode=3)
            # Big-endian word order (common for TLB4)
            import struct
            raw_bytes = struct.pack('>HH', regs[0], regs[1])
            return struct.unpack('>i', raw_bytes)[0]
        except Exception:
            return None


def detect_port() -> str:
    """Detect the most likely serial port."""
    import platform
    
    if platform.system() == "Windows":
        try:
            import serial.tools.list_ports
            ports = list(serial.tools.list_ports.comports())
            if ports:
                print("Available COM ports:")
                for p in ports:
                    print(f"  {p.device}: {p.description}")
                return ports[0].device
        except Exception:
            pass
        return "COM4"
    else:
        # Priority: modbusd > RPi UART > USB adapters
        candidates = ["/tmp/modbus", "/dev/serial0", "/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "/tmp/modbus"  # Default to WidgetLords modbusd


def scan_all_registers(tlb4: SimpleTLB4) -> dict:
    """
    Scan all potentially relevant registers and capture their values.
    Returns dict of register_address -> value
    """
    results = {}
    
    # Define scan ranges with descriptions
    # TLB4 uses 40001-based numbering, so address = register - 40001
    scan_ranges = [
        (0, 20, "Standard registers (40001-40021: firmware, weights, status)"),
        (49, 70, "R1-R14 general purpose registers (40050-40071)"),
    ]
    
    for start, end, description in scan_ranges:
        print(f"\nScanning {description}...")
        print(f"  Addresses {start}-{end} (Registers {start+40001}-{end+40001})")
        print("-" * 60)
        
        for addr in range(start, end + 1):
            value = tlb4.read_register(addr, signed=True)
            if value is not None:
                results[addr] = value
                if value != 0:
                    reg_40k = addr + 40001
                    # Try to interpret as kg (2 decimal places)
                    kg_val = value / 100.0
                    print(f"  Addr {addr:3d} (Reg {reg_40k}): {value:>8} raw  |  {kg_val:>8.2f} kg")
    
    return results


def monitor_for_changes(tlb4: SimpleTLB4, baseline: dict, duration: float = 60.0):
    """
    Monitor registers and report any changes from baseline.
    This helps identify which registers change when load is applied.
    """
    print("\n" + "=" * 70)
    print("MONITORING FOR CHANGES")
    print("=" * 70)
    print(f"Duration: {duration} seconds")
    print(f"Monitoring {len(baseline)} registers")
    print("\n*** INSTRUCTIONS ***")
    print("  1. Keep load cells UNLOADED for first 10 seconds")
    print("  2. Apply ~1kg to FIRST load cell - watch for changes")
    print("  3. Remove load, apply ~1kg to SECOND load cell")
    print("  4. Note which DIFFERENT registers change for each cell")
    print("\nPress Ctrl+C to stop early.\n")
    print("-" * 70)
    
    start_time = time.time()
    last_values = baseline.copy()
    changes_detected = {}
    
    try:
        while (time.time() - start_time) < duration:
            elapsed = time.time() - start_time
            
            for addr in baseline.keys():
                value = tlb4.read_register(addr, signed=True)
                if value is not None and value != last_values.get(addr, 0):
                    change = value - last_values.get(addr, 0)
                    reg_40k = addr + 40001
                    kg_new = value / 100.0
                    kg_change = change / 100.0
                    
                    if addr not in changes_detected:
                        changes_detected[addr] = []
                    changes_detected[addr].append({
                        'time': elapsed,
                        'old': last_values.get(addr, 0),
                        'new': value,
                        'change': change
                    })
                    
                    # Highlight significant changes
                    marker = "***" if abs(change) > 10 else "   "
                    print(f"{marker} t={elapsed:5.1f}s | Addr {addr:3d} (Reg {reg_40k}): "
                          f"{kg_new:>7.2f} kg (Δ={kg_change:+.2f} kg)")
                    
                    last_values[addr] = value
            
            time.sleep(0.25)
            
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    
    return changes_detected


def read_channels_directly(tlb4: SimpleTLB4, duration: float = 10.0):
    """
    Read the 4 individual channels directly from the known HiRes registers.
    This assumes Command 25 has already been sent.
    """
    print("\n" + "=" * 70)
    print("READING INDIVIDUAL CHANNELS (HiRes Mode)")
    print("=" * 70)
    print("Channel addresses after Command 25:")
    print("  CH1: 40051-40052 (addr 50-51)")
    print("  CH2: 40053-40054 (addr 52-53)")
    print("  CH3: 40055-40056 (addr 54-55)")
    print("  CH4: 40057-40058 (addr 56-57)")
    print("-" * 70)
    print(f"{'Time':>6} | {'CH1 (raw)':>12} | {'CH2 (raw)':>12} | {'CH3 (raw)':>12} | {'CH4 (raw)':>12}")
    print("-" * 70)
    
    # Channel register addresses (32-bit values, so step by 2)
    ch_addrs = [50, 52, 54, 56]
    
    start_time = time.time()
    try:
        while (time.time() - start_time) < duration:
            elapsed = time.time() - start_time
            values = []
            for addr in ch_addrs:
                val = tlb4.read_32bit(addr)
                values.append(val if val is not None else "ERROR")
            
            print(f"{elapsed:5.1f}s | {values[0]:>12} | {values[1]:>12} | {values[2]:>12} | {values[3]:>12}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nStopped.")
    
    print("-" * 70)
    print("NOTE: These are RAW DIVISIONS (ADC counts), not kg!")
    print("To convert to kg, you need to calibrate (see docs).")


def analyze_results(changes_detected: dict):
    """Analyze and display results with recommendations."""
    print("\n" + "=" * 70)
    print("ANALYSIS RESULTS")
    print("=" * 70)
    
    if not changes_detected:
        print("\nNo changes detected!")
        print("Make sure to apply load to the load cells during monitoring.")
        return
    
    # Known combined weight registers to exclude from channel detection
    combined_weight_addrs = {7, 8, 9, 10, 11, 12, 13}
    
    # Sort by total change magnitude
    sorted_addrs = sorted(
        changes_detected.keys(),
        key=lambda a: sum(abs(c['change']) for c in changes_detected[a]),
        reverse=True
    )
    
    print("\nRegisters that changed (sorted by magnitude):\n")
    
    channel_candidates = []
    
    for addr in sorted_addrs:
        reg_40k = addr + 40001
        changes = changes_detected[addr]
        total_change = sum(abs(c['change']) for c in changes)
        num_changes = len(changes)
        
        # Classify the register
        if addr in combined_weight_addrs:
            reg_type = "COMBINED WEIGHT"
        elif 50 <= addr <= 63:
            reg_type = f"R{addr-49} (likely individual channel)"
            channel_candidates.append(addr)
        else:
            reg_type = "Unknown"
            if total_change > 50:
                channel_candidates.append(addr)
        
        print(f"  Addr {addr:3d} (Reg {reg_40k}): {num_changes} changes, "
              f"total Δ={total_change/100:.2f} kg  [{reg_type}]")
    
    # Generate configuration recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDED CONFIGURATION")
    print("=" * 70)
    
    # Filter to registers NOT in combined weight area
    individual_candidates = [a for a in channel_candidates if a not in combined_weight_addrs]
    
    if len(individual_candidates) >= 2:
        print("\nDetected likely individual channel registers:")
        for i, addr in enumerate(sorted(individual_candidates)[:4], start=1):
            reg_40k = addr + 40001
            print(f"  Channel {i}: Address {addr} (Register {reg_40k})")
        
        print("\n\nUpdate your hardware_config.yaml with these values:")
        print("-" * 50)
        print("modbus:")
        print("  tlb4:")
        print("    registers:")
        print("      gross_weight: 7      # Combined weight (32-bit)")
        print("      net_weight: 9        # Net weight (32-bit)")
        print("      status: 6")
        for i, addr in enumerate(sorted(individual_candidates)[:4], start=1):
            print(f"      channel_{i}: {addr}        # Individual LC{i}")
        print("\n    channel_scaling:")
        for i, addr in enumerate(sorted(individual_candidates)[:4], start=1):
            enabled = "true" if i <= 2 else "false"
            print(f"      channel_{i}:")
            print(f"        enabled: {enabled}")
            print(f"        full_scale_divisions: 100.0")
            print(f"        capacity_kg: 1.0")
            print(f"        zero_offset: 0.0")
        print("-" * 50)
    else:
        print("\nCould not identify individual channel registers.")
        print("Try applying load to each cell for longer, or check if your TLB4")
        print("firmware supports individual channel output via Modbus.")
        print("\nThe combined weight registers that changed:")
        for addr in sorted_addrs:
            if addr in combined_weight_addrs:
                reg_40k = addr + 40001
                print(f"  Address {addr} (Register {reg_40k})")


def interactive_mode(tlb4: SimpleTLB4):
    """Interactive discovery mode."""
    print("\n" + "=" * 70)
    print("INTERACTIVE CHANNEL DISCOVERY")
    print("=" * 70)
    
    # Step 0: Enable multi-channel mode (CRITICAL!)
    print("\nStep 0: Enabling multi-channel mode...")
    print("-" * 70)
    tlb4.enable_multichannel_mode()
    
    # Step 1: Baseline scan
    print("\nStep 1: Capturing baseline (no load)...")
    input("Ensure load cells are UNLOADED, then press ENTER...")
    
    baseline = scan_all_registers(tlb4)
    non_zero = {k: v for k, v in baseline.items() if v != 0}
    print(f"\nFound {len(non_zero)} registers with non-zero values.")
    
    # Step 2: Monitor for changes
    print("\nStep 2: Monitoring for changes...")
    input("Press ENTER to start 60-second monitoring...")
    
    changes = monitor_for_changes(tlb4, baseline, duration=60.0)
    
    # Step 3: Analyze and recommend
    analyze_results(changes)
    
    # Step 4: Read channels directly
    print("\n" + "=" * 70)
    print("DIRECT CHANNEL READING")
    print("=" * 70)
    print("Now let's read the 4 channels directly from their known addresses.")
    input("Press ENTER to start 15-second channel reading (apply load to test)...")
    
    read_channels_directly(tlb4, duration=15.0)
    
    # Step 5: Optional verification
    print("\n" + "=" * 70)
    print("VERIFICATION (optional)")
    print("=" * 70)
    
    while True:
        addr_input = input("\nEnter address to monitor (or 'done'): ").strip()
        if addr_input.lower() in ['done', 'quit', 'exit', 'q', '']:
            break
        
        try:
            addr = int(addr_input)
            print(f"Monitoring address {addr} for 10 seconds... Apply varying load:")
            
            start = time.time()
            while (time.time() - start) < 10:
                # Try 32-bit first for channel addresses
                if addr in [50, 52, 54, 56]:
                    value = tlb4.read_32bit(addr)
                    if value is not None:
                        print(f"  Addr {addr} (32-bit): {value:>12}")
                else:
                    value = tlb4.read_register(addr, signed=True)
                    if value is not None:
                        print(f"  Addr {addr} (16-bit): {value:>8}")
                time.sleep(0.5)
                
        except ValueError:
            print("Invalid input. Enter a number or 'done'.")


def main():
    parser = argparse.ArgumentParser(
        description="Discover TLB4 individual channel register addresses",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--port", "-p", default=None, help="Serial port")
    parser.add_argument("--address", "-a", type=int, default=1, help="Modbus slave address")
    parser.add_argument("--baudrate", "-b", type=int, default=9600, help="Baud rate")
    parser.add_argument("--quick-scan", action="store_true", help="Quick scan only")
    
    args = parser.parse_args()
    port = args.port or detect_port()
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║           TLB4 INDIVIDUAL CHANNEL DISCOVERY                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  Port:     {port:<20}                                     ║
║  Address:  {args.address:<20}                                     ║
║  Baudrate: {args.baudrate:<20}                                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  This script finds where the TLB4 stores individual load cell        ║
║  values so you can configure them separately in the GUI.             ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    tlb4 = SimpleTLB4(port, args.address, args.baudrate)
    
    print("Connecting to TLB4...")
    if not tlb4.connect():
        print("\n[ERROR] Failed to connect!")
        print("Check: port, wiring (29=A/+, 30=B/-), TLB4 Modbus settings")
        return 1
    
    print("[OK] Connected!\n")
    
    try:
        if args.quick_scan:
            scan_all_registers(tlb4)
        else:
            interactive_mode(tlb4)
    finally:
        tlb4.disconnect()
        print("\nDisconnected.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
