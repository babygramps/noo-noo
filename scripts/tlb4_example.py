#!/usr/bin/env python3
"""
TLB4 Load Cell Transmitter - Usage Example

This script demonstrates how to use the ModbusInterface
to read weight data from the Laumas TLB4.

Before running:
1. Configure TLB4 for Modbus RTU (see tlb4_register_scanner.py --instructions)
2. Connect TLB4 via RS485 (terminals 29=A/+, 30=B/-)
3. Run register scanner to verify/discover register addresses
4. Update hardware_config.yaml with correct registers

Usage:
    python scripts/tlb4_example.py --port COM3
"""

import argparse
import sys
import time
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from epdm_vacuum.daq.modbus_interface import ModbusInterface, TLB4Config, TLB4ChannelConfig


def example_basic_usage():
    """Basic example: Connect and read weights."""
    print("\n" + "=" * 60)
    print("BASIC USAGE EXAMPLE")
    print("=" * 60)
    
    # Create interface with default settings
    interface = ModbusInterface(
        port="COM3",  # Change to your port
        slave_address=1,
        baudrate=9600,
        parity="None",
        stopbits=1,
        debug=True  # Enable debug output
    )
    
    # Connect
    print("\nConnecting to TLB4...")
    if not interface.connect():
        print("Failed to connect!")
        return
    
    print("Connected!\n")
    
    try:
        # Read all data
        print("Reading weight data...")
        data = interface.read()
        
        print(f"\nResults:")
        print(f"  Gross Weight: {data.get('gross_weight_kg', 0):.2f} kg")
        print(f"  Net Weight:   {data.get('net_weight_kg', 0):.2f} kg")
        print(f"  Tare Weight:  {data.get('tare_weight_kg', 0):.2f} kg")
        print(f"\nIndividual Channels:")
        for i in range(1, 5):
            raw = data.get(f'load_cell_{i}_raw', 0)
            kg = data.get(f'load_cell_{i}_kg', 0)
            print(f"  CH{i}: {kg:8.2f} kg  (raw: {raw})")
        
    finally:
        interface.disconnect()
        print("\nDisconnected.")


def example_continuous_logging(port: str, duration: float = 30.0):
    """Example: Continuous data logging."""
    print("\n" + "=" * 60)
    print("CONTINUOUS LOGGING EXAMPLE")
    print(f"Duration: {duration} seconds")
    print("=" * 60)
    
    interface = ModbusInterface(port=port, slave_address=1, baudrate=9600)
    
    if not interface.connect():
        print("Failed to connect!")
        return
    
    print("\nLogging started. Press Ctrl+C to stop.\n")
    print(f"{'Time':>8} | {'Gross':>10} | {'CH1':>8} | {'CH2':>8} | {'CH3':>8} | {'CH4':>8}")
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
            
            print(f"{elapsed:8.1f} | {gross:10.2f} | {ch1:8.2f} | {ch2:8.2f} | {ch3:8.2f} | {ch4:8.2f}")
            
            sample_count += 1
            time.sleep(0.5)  # 2 Hz sample rate
    
    except KeyboardInterrupt:
        print("\nStopped by user.")
    
    finally:
        interface.disconnect()
        print(f"\nLogging complete. {sample_count} samples recorded.")


def example_custom_scaling(port: str):
    """Example: Configure custom scaling for load cells."""
    print("\n" + "=" * 60)
    print("CUSTOM SCALING EXAMPLE")
    print("=" * 60)
    
    # Create custom channel configurations
    # Adjust these values based on your load cells
    channels = [
        TLB4ChannelConfig(
            full_scale_divisions=20000,  # Your load cell's full scale divisions
            load_cell_capacity_kg=500,    # 500 kg capacity cell
            zero_offset=100,              # Zero offset in divisions
            enabled=True
        ),
        TLB4ChannelConfig(
            full_scale_divisions=20000,
            load_cell_capacity_kg=500,
            zero_offset=150,
            enabled=True
        ),
        TLB4ChannelConfig(
            full_scale_divisions=20000,
            load_cell_capacity_kg=500,
            zero_offset=120,
            enabled=True
        ),
        TLB4ChannelConfig(
            full_scale_divisions=20000,
            load_cell_capacity_kg=500,
            zero_offset=80,
            enabled=True
        ),
    ]
    
    # Create TLB4 configuration with custom registers and scaling
    config = TLB4Config(
        reg_gross_weight=0,     # Verify with scanner
        reg_channel_1=8,        # Verify with scanner
        reg_channel_2=10,       # Verify with scanner
        reg_channel_3=12,       # Verify with scanner
        reg_channel_4=14,       # Verify with scanner
        channels=channels,
        decimal_places=2,       # 2 decimal places (12345 = 123.45)
    )
    
    interface = ModbusInterface(
        port=port,
        slave_address=1,
        baudrate=9600,
        tlb4_config=config
    )
    
    if not interface.connect():
        print("Failed to connect!")
        return
    
    try:
        data = interface.read()
        print(f"\nWith custom scaling:")
        for i in range(1, 5):
            kg = data.get(f'load_cell_{i}_kg', 0)
            raw = data.get(f'load_cell_{i}_raw', 0)
            print(f"  CH{i}: {kg:8.2f} kg  (raw divisions: {raw})")
    
    finally:
        interface.disconnect()


def example_from_config(config_path: str):
    """Example: Load configuration from YAML file."""
    print("\n" + "=" * 60)
    print("LOADING FROM CONFIG FILE")
    print(f"Config: {config_path}")
    print("=" * 60)
    
    from epdm_vacuum.config import create_modbus_interface_from_settings, Settings
    
    # Load settings from config file
    settings = Settings(config_path)
    
    # Create interface from settings
    interface = create_modbus_interface_from_settings(settings)
    
    if not interface.connect():
        print("Failed to connect!")
        return
    
    try:
        data = interface.read()
        print(f"\nGross Weight: {data.get('gross_weight_kg', 0):.2f} kg")
        print(f"Individual loads: {interface.get_individual_loads()}")
    
    finally:
        interface.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="TLB4 Load Cell Transmitter Usage Examples"
    )
    parser.add_argument(
        "--port", "-p",
        default="COM3",
        help="Serial port (default: COM3)"
    )
    parser.add_argument(
        "--example", "-e",
        choices=["basic", "continuous", "scaling", "config"],
        default="basic",
        help="Example to run"
    )
    parser.add_argument(
        "--duration", "-d",
        type=float,
        default=30.0,
        help="Duration for continuous logging (seconds)"
    )
    parser.add_argument(
        "--config", "-c",
        default="src/epdm_vacuum/config/hardware_config.yaml",
        help="Path to config file"
    )
    
    args = parser.parse_args()
    
    if args.example == "basic":
        example_basic_usage()
    elif args.example == "continuous":
        example_continuous_logging(args.port, args.duration)
    elif args.example == "scaling":
        example_custom_scaling(args.port)
    elif args.example == "config":
        example_from_config(args.config)


if __name__ == "__main__":
    main()

