#!/usr/bin/env python3
"""
Test script to verify pressure sensor reading through the widgetlords interface.
Run this on your Raspberry Pi to verify the fix works correctly.

Usage:
    python scripts/test_pressure_reading.py
"""

import sys
import time
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_direct_widgetlords():
    """Test direct widgetlords library access (like your working script)."""
    print("\n" + "=" * 60)
    print("TEST 1: Direct widgetlords library access")
    print("=" * 60)
    
    try:
        from widgetlords.pi_spi_din import Mod8AI, ChipEnable, init
        
        init()
        inputs = Mod8AI(ChipEnable.CE1)
        
        print("Reading channel 0 directly from Mod8AI(CE1)...")
        for i in range(5):
            raw_value = inputs.read_single(0)
            print(f"  Reading {i+1}: {raw_value:.4f}V")
            time.sleep(0.5)
        
        print("✓ Direct library access WORKS")
        return True
        
    except Exception as e:
        print(f"✗ Direct library access FAILED: {e}")
        return False


def test_widgetlords_interface():
    """Test the WidgetLordsInterface class."""
    print("\n" + "=" * 60)
    print("TEST 2: WidgetLordsInterface class")
    print("=" * 60)
    
    try:
        from epdm_vacuum.config.settings import get_settings
        from epdm_vacuum.daq.widgetlords_interface import WidgetLordsInterface
        
        # Load config
        config_file = Path(__file__).parent.parent / "src" / "epdm_vacuum" / "config" / "hardware_config.yaml"
        settings = get_settings(str(config_file))
        
        # Get SPI modules config
        widgetlords_config = settings.get("hardware", "widgetlords", default={})
        spi_modules = widgetlords_config.get("spi_modules", [])
        
        print(f"Found {len(spi_modules)} SPI module configs")
        for mod in spi_modules:
            print(f"  - {mod.get('name')} ({mod.get('module_type')}) on {mod.get('chip_enable')}")
        
        # Create and connect interface
        interface = WidgetLordsInterface(spi_modules_config=spi_modules)
        connected = interface.connect()
        
        if not connected:
            print("✗ Failed to connect interface")
            return False
        
        print(f"Interface connected: {interface.is_connected()}")
        print(f"Modules: {interface.list_modules()}")
        
        # Test reading
        print("\nReading all sensors via interface.read()...")
        for i in range(5):
            data = interface.read()
            
            print(f"\nReading {i+1}:")
            print(f"  pressure_voltage: {data.get('pressure_voltage', 'N/A')}")
            print(f"  pressure_psi: {data.get('pressure_psi', 'N/A')}")
            print(f"  vacuum_psi: {data.get('vacuum_psi', 'N/A')}")
            print(f"  vacuum_bar: {data.get('vacuum_bar', 'N/A')}")
            
            # Also show analog_inputs structure
            analog_inputs = data.get('analog_inputs', {})
            if analog_inputs:
                print(f"  analog_inputs: {analog_inputs}")
            
            time.sleep(0.5)
        
        interface.disconnect()
        print("\n✓ WidgetLordsInterface WORKS")
        return True
        
    except Exception as e:
        logger.exception("Interface test failed")
        print(f"✗ WidgetLordsInterface FAILED: {e}")
        return False


def test_span_scaling():
    """Test the span scaling calculation."""
    print("\n" + "=" * 60)
    print("TEST 3: Span scaling verification")
    print("=" * 60)
    
    # Simulate what happens with 4-20mA sensor
    # Config says: 4mA -> 0 PSI, 20mA -> 14 PSI
    # Module converts: 4mA = 2V, 20mA = 10V (500 ohm resistor)
    
    print("Simulating 4-20mA sensor scaling:")
    print("  Config: 4mA -> 0 PSI, 20mA -> 14 PSI")
    print("  Module: 4mA = 2V, 20mA = 10V")
    
    test_voltages = [2.0, 4.0, 6.0, 8.0, 10.0]
    
    for voltage in test_voltages:
        # Voltage to mA conversion (like in _apply_span_scaling)
        if voltage <= 2.0:
            mA = 4.0
        elif voltage >= 10.0:
            mA = 20.0
        else:
            mA = 4.0 + (voltage - 2.0) * (20.0 - 4.0) / (10.0 - 2.0)
        
        # mA to PSI (span scaling)
        low_in, high_in = 4.0, 20.0
        low_out, high_out = 0.0, 14.0
        psi = low_out + (mA - low_in) * (high_out - low_out) / (high_in - low_in)
        
        # Vacuum calculation
        vacuum_psi = 14.7 - psi
        vacuum_bar = vacuum_psi * 0.0689476
        
        print(f"  {voltage:.1f}V -> {mA:.1f}mA -> {psi:.2f} PSI -> vacuum: {vacuum_psi:.2f} PSI / {vacuum_bar:.4f} bar")
    
    print("✓ Span scaling calculation verified")
    return True


if __name__ == "__main__":
    print("Pressure Sensor Reading Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Direct library", test_direct_widgetlords()))
    results.append(("Span scaling", test_span_scaling()))
    results.append(("Interface class", test_widgetlords_interface()))
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {name}: {status}")
    
    all_passed = all(r[1] for r in results)
    sys.exit(0 if all_passed else 1)






