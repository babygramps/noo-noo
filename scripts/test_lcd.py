#!/usr/bin/env python3
"""
Test script for Arduino LCD display.

Tests communication with Arduino Nano connected to I2C 1602 LCD.

Usage:
    python scripts/test_lcd.py [--port COM5]
    python scripts/test_lcd.py --list  # List available ports
"""

import sys
import time
import argparse

# Add src to path
sys.path.insert(0, "src")

from epdm_vacuum.daq.lcd_interface import LCDInterface, list_serial_ports


def list_ports():
    """List available serial ports."""
    print("\n=== Available Serial Ports ===\n")
    ports = list_serial_ports()
    
    if not ports:
        print("No serial ports found.")
        return
    
    for port in ports:
        print(f"  Device: {port['device']}")
        print(f"    Description: {port['description']}")
        print(f"    VID: {port['vid']}, PID: {port['pid']}")
        if port['serial_number']:
            print(f"    Serial: {port['serial_number']}")
        print()


def test_lcd(port=None):
    """Run LCD test sequence."""
    print("\n=== LCD Display Test ===\n")
    
    # Create interface
    print(f"Connecting to LCD{'...' if port is None else f' on {port}...'}")
    lcd = LCDInterface(port=port, auto_connect=True)
    
    if not lcd.is_connected():
        print("ERROR: Failed to connect to LCD display!")
        print("\nTroubleshooting:")
        print("  1. Check Arduino is connected via USB")
        print("  2. Verify Arduino sketch is uploaded")
        print("  3. Try --list to see available ports")
        print("  4. Specify port with --port COMx or --port /dev/ttyUSBx")
        return False
    
    print(f"Connected to LCD on {lcd.port}")
    print()
    
    try:
        # Test 1: Basic display
        print("Test 1: Basic display...")
        lcd.display("Hello EPDM!", "LCD Test v1.0")
        time.sleep(2)
        
        # Test 2: Clear display
        print("Test 2: Clear display...")
        lcd.clear()
        time.sleep(1)
        
        # Test 3: Single line updates
        print("Test 3: Single line updates...")
        lcd.display_line(0, "Line 1 Only")
        time.sleep(1)
        lcd.display_line(1, "Now Line 2")
        time.sleep(2)
        
        # Test 4: Show vacuum reading format
        print("Test 4: Vacuum display format...")
        lcd.show_vacuum(0.300, "Evacuating...")
        time.sleep(2)
        
        # Test 5: Stage progress display
        print("Test 5: Stage progress display...")
        for progress in [0.0, 0.25, 0.50, 0.75, 1.0]:
            lcd.show_test_stage("Evacuate", progress, cycle=1, total_cycles=3)
            time.sleep(0.5)
        time.sleep(1)
        
        # Test 6: Stage progress without cycles
        print("Test 6: Progress bar format...")
        for i in range(11):
            lcd.show_test_stage("Hold Vacuum", i / 10.0)
            time.sleep(0.3)
        time.sleep(1)
        
        # Test 7: Error display
        print("Test 7: Error display...")
        lcd.show_error("Connection Lost")
        time.sleep(2)
        
        # Test 8: Backlight control
        print("Test 8: Backlight control...")
        lcd.display("Backlight OFF", "in 1 second...")
        time.sleep(1)
        lcd.set_backlight(False)
        time.sleep(2)
        lcd.set_backlight(True)
        lcd.display("Backlight ON", "Test complete!")
        time.sleep(1)
        
        # Show idle
        print("Test 9: Idle display...")
        lcd.show_idle()
        time.sleep(2)
        
        print("\n=== All tests passed! ===\n")
        return True
        
    except Exception as e:
        print(f"\nERROR during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        lcd.disconnect()
        print("Disconnected from LCD.")


def interactive_mode(port=None):
    """Interactive mode for sending custom messages."""
    print("\n=== Interactive LCD Mode ===")
    print("Commands:")
    print("  line1|line2  - Display text (pipe separates lines)")
    print("  CLEAR        - Clear display")
    print("  BACKLIGHT:ON - Turn on backlight")
    print("  BACKLIGHT:OFF- Turn off backlight")
    print("  quit         - Exit")
    print()
    
    lcd = LCDInterface(port=port, auto_connect=True)
    
    if not lcd.is_connected():
        print("ERROR: Failed to connect to LCD!")
        return
    
    print(f"Connected to {lcd.port}")
    print()
    
    try:
        while True:
            try:
                text = input("Enter message: ").strip()
            except EOFError:
                break
            
            if not text:
                continue
            
            if text.lower() == "quit":
                break
            
            if text == "CLEAR":
                lcd.clear()
                print("Cleared")
            elif text == "BACKLIGHT:ON":
                lcd.set_backlight(True)
                print("Backlight ON")
            elif text == "BACKLIGHT:OFF":
                lcd.set_backlight(False)
                print("Backlight OFF")
            elif "|" in text:
                parts = text.split("|", 1)
                lcd.display(parts[0], parts[1] if len(parts) > 1 else "")
                print("Displayed")
            else:
                lcd.display(text)
                print("Displayed")
    
    finally:
        lcd.disconnect()
        print("\nDisconnected.")


def main():
    parser = argparse.ArgumentParser(description="Test Arduino LCD display")
    parser.add_argument("--port", "-p", help="Serial port (e.g., COM5, /dev/ttyUSB0)")
    parser.add_argument("--list", "-l", action="store_true", help="List available ports")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    if args.list:
        list_ports()
        return 0
    
    if args.interactive:
        interactive_mode(args.port)
        return 0
    
    success = test_lcd(args.port)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
