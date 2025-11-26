# CLAUDE.md - AI Assistant Guidelines

## Project Overview

EPDM Gasket Vacuum Seal Testing System - Python/PyQt5 application for Raspberry Pi 5 that controls vacuum seal testing equipment via Modbus RTU (load cells) and SPI (analog I/O).

## Quick Commands

```bash
# Run the GUI application
python -m epdm_vacuum.app_main

# Run Flask API (optional remote monitoring)
python -m epdm_vacuum.api_main

# TLB4 register scanner (discover Modbus registers)
python scripts/tlb4_register_scanner.py --port COM4 --interactive

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
src/epdm_vacuum/
├── app_main.py              # GUI entry point
├── api_main.py              # Flask API entry point
├── config/
│   ├── settings.py          # Config loader, TLB4Config creation
│   └── hardware_config.yaml # Hardware parameters (ports, registers)
├── daq/                     # Hardware abstraction
│   ├── hardware_interface.py    # Base class for all interfaces
│   ├── modbus_interface.py      # TLB4 Modbus RTU driver (IMPORTANT)
│   └── widgetlords_interface.py # SPI analog I/O
├── gui/
│   ├── main_window.py       # Main Qt window, hardware init
│   ├── widgets/             # Display, plots, controls
│   └── threads/             # DAQ and control background threads
├── control/                 # Test sequencing, safety, pump control
└── logging/                 # CSV/HDF5 data logging
```

## Key Files

- `modbus_interface.py` - TLB4 load cell driver with software tare, thread-safe reads
- `hardware_config.yaml` - Register addresses, port settings, scaling factors
- `settings.py` - `create_modbus_interface_from_settings()` factory function
- `main_window.py` - Hardware initialization in `init_hardware_interfaces()`
- `display_widget.py` - Real-time weight/vacuum display updates

## Code Patterns

### Hardware Interface Pattern
All hardware interfaces inherit from `HardwareInterface` base class:
```python
class HardwareInterface:
    def connect(self) -> bool
    def disconnect(self) -> bool
    def read(self) -> Dict[str, Any]
    def write(self, data: Dict[str, Any]) -> bool
    def is_connected(self) -> bool
```

### Modbus Thread Safety
The ModbusInterface uses `threading.Lock` for serial port access:
```python
with self._lock:
    # Read or write operations here
```

### TLB4 Command Writing
TLB4 only supports Function 16 (Write Multiple Registers), NOT Function 06:
```python
self.instrument.write_registers(register_address, [value])  # Correct
# NOT: self.instrument.write_register(register, value, functioncode=6)
```

## Hardware Configuration

### TLB4 Load Cell Transmitter (Modbus RTU)
- Port: COM4 (Windows) or /dev/ttyUSB0 (Linux)
- Baud: 9600, Parity: None, Stop bits: 1
- Slave address: 1
- Data format: 16-bit integers with 2 decimal places (246 = 2.46 kg)

### Key Registers (discovered via scanner)
- R0: Gross weight (total)
- R2: Net weight (after tare)
- R5: Command register (write 7=tare, 8=zero, 9=gross)
- R8: Channel 1 (connected load cell)

### TLB4 Commands (write to register 5)
- 7: Semi-automatic tare
- 8: Zero scale
- 9: Switch to gross weight display

## Code Style

- Python 3.11+, type hints on all functions
- Use `logging` module, not print statements
- PyQt5 signals/slots for thread communication
- Dataclasses for configuration objects (`TLB4Config`, `TLB4ChannelConfig`)
- YAML for configuration files

## Testing Workflow

1. Use `scripts/tlb4_register_scanner.py` to discover/verify register addresses
2. Update `hardware_config.yaml` with correct registers and scaling
3. Run `python -m epdm_vacuum.app_main` to test GUI
4. Check terminal logs for Modbus communication errors

## Common Issues

### "No communication with instrument"
- Check COM port is correct and not in use by another process
- Verify TLB4 is in Modbus mode (not "nOnE")
- Ensure correct baud rate (9600)

### Permission errors on COM port
- Another Python process may have the port open
- Run: `Get-Process python | Stop-Process -Force` (Windows)

### Tare not updating in GUI
- TLB4 hardware tare only affects total weight, not individual channels
- Software tare offsets are stored in `_channel_tare_offsets`
- Total Force = sum of individual load cells (with software tare)

## Environment

- Windows 10/11 for development, Raspberry Pi 5 for deployment
- Python 3.11+ (tested with 3.14)
- VS Code with Remote-SSH for Pi development

