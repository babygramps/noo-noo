#!/usr/bin/env python3
"""
TLB4 Individual Channel Discovery Script

This script helps discover where the TLB4 stores individual load cell channel values.
Run this while applying load to each load cell individually to identify which registers
correspond to which channels.

Based on TLB4 Modbus documentation:
- Standard registers (40001-40074) include combined weights
- Individual channel values may be in R1-R14 (40051-40064) or extended registers

Usage:
    python scripts/discover_tlb4_channels.py --port COM4
    
    1. Start with no load on any cell
    2. Apply load to LC1 only - note which registers change
    3. Remove LC1 load, apply to LC2 - note which registers change
    4. Use the discovered registers in hardware_config.yaml
"""

import argparse
import sys
import time
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from epdm_vacuum.daq.modbus_interface import ModbusInterface, TLB4Config, DataFormat


def detect_port() -> str:
    """Detect the most likely serial port."""
    import platform
    
    if platform.system() == "Windows":
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        if ports:
            print("Available COM ports:")
            for p in ports:
                print(f"  {p.device}: {p.description}")
            return ports[0].device
        return "COM4"
    else:
        candidates = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]
        for path in candidates:
            if os.path.exists(path):
                return path
        return "/dev/ttyUSB0"


def scan_all_registers(interface: ModbusInterface) -> dict:
    """
    Scan all potentially relevant registers and capture their values.
    Returns dict of register_address -> value
    """
    results = {}
    
    # Standard weight registers (40001-40074 → addresses 0-73)
    # Focus on areas likely to contain channel data
    scan_ranges = [
        (0, 20, "Standard weight/status registers"),
        (49, 70, "R1-R14 general purpose registers (40051-40064)"),
    ]
    
    for start, end, description in scan_ranges:
        print(f"\nScanning {description} (addresses {start}-{end})...")
        for addr in range(start, end + 1):
            try:
                value = interface.read_register(addr, signed=True)
                if value is not None:
                    results[addr] = value
                    if value != 0:
                        # Map to 40001-based register number
                        reg_40k = addr + 40001
                        print(f"  Address {addr:3d} (R{reg_40k}): {value:>8} (0x{value & 0xFFFF:04X})")
            except Exception:
                pass
    
    return results


def monitor_for_changes(interface: ModbusInterface, baseline: dict, duration: float = 30.0):
    """
    Monitor registers and report any changes from baseline.
    This helps identify which registers change when load is applied.
    """
    print("\n" + "=" * 70)
    print("MONITORING FOR CHANGES - Apply load to individual load cells")
    print("=" * 70)
    print(f"Duration: {duration} seconds")
    print("Registers being monitored:", sorted(baseline.keys()))
    print("\nInstructions:")
    print("  1. Start with NO load on any cell")
    print("  2. Apply ~1kg load to FIRST load cell only")
    print("  3. Wait 5 seconds, note which registers changed")
    print("  4. Remove load from first cell, apply to SECOND cell")
    print("  5. Note which different registers changed")
    print("\nChanges will be highlighted below:")
    print("-" * 70)
    
    start_time = time.time()
    last_values = baseline.copy()
    changes_detected = {}  # Track which registers have changed and by how much
    
    try:
        while (time.time() - start_time) < duration:
            elapsed = time.time() - start_time
            
            # Read all monitored registers
            for addr in baseline.keys():
                try:
                    value = interface.read_register(addr, signed=True)
                    if value is not None and value != last_values.get(addr, 0):
                        change = value - last_values.get(addr, 0)
                        reg_40k = addr + 40001
                        
                        # Track this change
                        if addr not in changes_detected:
                            changes_detected[addr] = []
                        changes_detected[addr].append({
                            'time': elapsed,
                            'old': last_values.get(addr, 0),
                            'new': value,
                            'change': change
                        })
                        
                        # Print immediately
                        print(f"  t={elapsed:5.1f}s | Addr {addr:3d} (R{reg_40k}): "
                              f"{last_values.get(addr, 0):>8} → {value:>8} "
                              f"(Δ={change:+d})")
                        
                        last_values[addr] = value
                        
                except Exception:
                    pass
            
            time.sleep(0.25)  # 250ms polling interval
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user.")
    
    print("\n" + "=" * 70)
    print("SUMMARY OF CHANGES DETECTED")
    print("=" * 70)
    
    if changes_detected:
        # Sort by total change magnitude (most significant first)
        sorted_addrs = sorted(
            changes_detected.keys(),
            key=lambda a: sum(abs(c['change']) for c in changes_detected[a]),
            reverse=True
        )
        
        for addr in sorted_addrs:
            reg_40k = addr + 40001
            changes = changes_detected[addr]
            total_change = sum(abs(c['change']) for c in changes)
            
            print(f"\nAddress {addr} (Register {reg_40k}):")
            print(f"  Total changes: {len(changes)}, Total magnitude: {total_change}")
            print(f"  Changes:")
            for c in changes[:5]:  # Show first 5 changes
                print(f"    t={c['time']:5.1f}s: {c['old']} → {c['new']} (Δ={c['change']:+d})")
            
            # Interpret likely meaning
            if addr in [7, 8]:
                print(f"  → This is likely GROSS WEIGHT (combined all cells)")
            elif addr in [9, 10]:
                print(f"  → This is likely NET WEIGHT")
            elif 50 <= addr <= 63:
                ch_num = addr - 49
                print(f"  → This could be CHANNEL {ch_num} individual value (R{ch_num})")
            
    else:
        print("No changes detected. Make sure to apply load to the load cells!")
    
    return changes_detected


def recommend_config(changes_detected: dict):
    """Generate configuration recommendations based on detected changes."""
    print("\n" + "=" * 70)
    print("CONFIGURATION RECOMMENDATIONS")
    print("=" * 70)
    
    # Filter to registers that had significant changes
    significant = {
        addr: changes for addr, changes in changes_detected.items()
        if sum(abs(c['change']) for c in changes) > 10  # At least 10 units total change
    }
    
    if not significant:
        print("No significant changes detected. Please try again with more load variation.")
        return
    
    # Identify likely channel registers (excluding known combined weight registers)
    combined_weight_addrs = {7, 8, 9, 10, 11, 12, 13}  # Gross, Net, Peak weights
    
    channel_candidates = [
        addr for addr in significant.keys()
        if addr not in combined_weight_addrs
    ]
    
    print("\nLikely individual channel registers (excluding combined weights):")
    for i, addr in enumerate(sorted(channel_candidates)[:4], start=1):
        reg_40k = addr + 40001
        changes = significant[addr]
        avg_value = sum(c['new'] for c in changes) / len(changes)
        print(f"  Channel {i}: Address {addr} (Register {reg_40k}), avg value ≈ {avg_value:.0f}")
    
    print("\nSuggested hardware_config.yaml update:")
    print("-" * 40)
    print("modbus:")
    print("  tlb4:")
    print("    registers:")
    print("      gross_weight: 7     # 40008-40009 (32-bit)")
    print("      net_weight: 9       # 40010-40011 (32-bit)")
    print("      tare_weight: 11     # 40012-40013 (if available)")
    print("      status: 6           # Status register")
    
    for i, addr in enumerate(sorted(channel_candidates)[:4], start=1):
        print(f"      channel_{i}: {addr}        # Individual load cell {i}")
    
    print("\n    channel_scaling:")
    for i, addr in enumerate(sorted(channel_candidates)[:4], start=1):
        print(f"      channel_{i}:")
        print(f"        enabled: true")
        print(f"        full_scale_divisions: 100.0")
        print(f"        capacity_kg: 1.0")
        print(f"        zero_offset: 0.0")
    print("-" * 40)


def interactive_discovery(interface: ModbusInterface):
    """Interactive mode to help discover channel registers."""
    print("\n" + "=" * 70)
    print("INTERACTIVE CHANNEL DISCOVERY")
    print("=" * 70)
    
    # Step 1: Scan all registers to get baseline
    print("\nStep 1: Capturing baseline (no load)...")
    input("Press ENTER when load cells are UNLOADED...")
    
    baseline = scan_all_registers(interface)
    non_zero_baseline = {k: v for k, v in baseline.items() if v != 0}
    
    print(f"\nFound {len(non_zero_baseline)} non-zero registers at baseline.")
    
    # Step 2: Monitor for changes
    print("\nStep 2: Monitoring for changes...")
    print("Apply load to each load cell individually during the next 60 seconds.")
    input("Press ENTER to start monitoring...")
    
    changes = monitor_for_changes(interface, baseline, duration=60.0)
    
    # Step 3: Generate recommendations
    if changes:
        recommend_config(changes)
    
    # Step 4: Verify specific registers
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)
    print("\nWould you like to verify specific registers?")
    
    while True:
        addr_input = input("Enter register address to monitor (or 'done' to finish): ").strip()
        if addr_input.lower() in ['done', 'quit', 'exit', '']:
            break
        
        try:
            addr = int(addr_input)
            print(f"\nMonitoring address {addr} for 10 seconds...")
            print("Apply varying load to see changes:")
            
            start = time.time()
            while (time.time() - start) < 10:
                try:
                    value = interface.read_register(addr, signed=True)
                    reg_40k = addr + 40001
                    # Convert to kg assuming 2 decimal places
                    kg_value = value / 100.0 if value else 0
                    print(f"  Addr {addr} (R{reg_40k}): raw={value:>8}, as kg={kg_value:>8.2f}")
                except Exception as e:
                    print(f"  Error reading: {e}")
                time.sleep(0.5)
                
        except ValueError:
            print("Invalid address. Enter a number or 'done'.")


def main():
    parser = argparse.ArgumentParser(
        description="Discover TLB4 individual channel register addresses",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument("--port", "-p", default=None, help="Serial port")
    parser.add_argument("--address", "-a", type=int, default=1, help="Modbus slave address")
    parser.add_argument("--baudrate", "-b", type=int, default=9600, help="Baud rate")
    parser.add_argument("--quick-scan", action="store_true", help="Quick scan without monitoring")
    
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
║  This script helps you find where the TLB4 stores individual         ║
║  load cell values, so you can configure them separately.             ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    interface = ModbusInterface(
        port=port,
        slave_address=args.address,
        baudrate=args.baudrate,
        parity="None",
        stopbits=1,
        debug=False
    )
    
    print("Connecting to TLB4...")
    if not interface.connect():
        print("\n[ERROR] Failed to connect to TLB4!")
        print("Check port, wiring, and TLB4 Modbus settings.")
        return 1
    
    print("[OK] Connected!\n")
    
    try:
        if args.quick_scan:
            # Just scan and print
            results = scan_all_registers(interface)
            print(f"\nTotal registers with values: {len(results)}")
        else:
            # Full interactive discovery
            interactive_discovery(interface)
    
    finally:
        interface.disconnect()
        print("\nDisconnected from TLB4.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

