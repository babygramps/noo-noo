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
python scripts/tlb4_register_scanner.py --interactive  # Auto-detects port

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
│   ├── main_window.py       # Main Qt window with dockable panels
│   ├── widgets/
│   │   ├── display_widget.py      # Large LCD sensor displays
│   │   ├── plot_widget.py         # Real-time pyqtgraph plots
│   │   ├── control_panel.py       # Test/pump control buttons
│   │   ├── sequence_selector.py   # Test sequence dropdown
│   │   ├── test_status_panel.py   # Stage progress + IO status
│   │   ├── stage_progress_widget.py
│   │   └── io_status_widget.py
│   ├── threads/             # DAQ and control background threads
│   └── dialogs/             # Configuration dialogs
│       ├── sequence_editor.py    # Test sequence editor
│       ├── io_config_dialog.py   # IO device configuration
│       ├── spi_config_dialog.py  # Widgetlords SPI module setup
│       └── test_metadata_dialog.py
├── control/                 # Test sequencing, safety, pump control
│   ├── sequence.py          # TestSequence, TestStage dataclasses
│   ├── sequence_manager.py  # Load/save/validate sequences
│   └── test_controller.py   # Test execution engine
└── logging/                 # CSV/HDF5 data logging
    ├── data_logger.py
    └── buffer.py
```

## Key Files

- `modbus_interface.py` - TLB4 load cell driver with software tare, thread-safe reads
- `widgetlords_interface.py` - PI-SPI-DIN module driver with multi-module support
- `hardware_config.yaml` - Register addresses, port settings, SPI module config
- `settings.py` - `create_modbus_interface_from_settings()` factory function
- `main_window.py` - Dockable panel system, hardware init, layout persistence
- `display_widget.py` - Large LCD displays with color-coded load cells
- `spi_config_dialog.py` - GUI for configuring Widgetlords SPI modules

## GUI Architecture

### Dockable Panel System
The main window uses `QDockWidget` for flexible layout:
- **Central Widget**: PlotWidget (gets maximum real estate)
- **Dockable Panels**: DisplayWidget, TestStatusPanel, SequenceSelectorWidget, ControlPanel

Panels can be dragged, floated, tabified, or closed. Layout is saved/restored via `QSettings`.

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Toggle Sensor Display |
| `Ctrl+2` | Toggle Test Status |
| `Ctrl+3` | Toggle Test Sequence |
| `Ctrl+4` | Toggle Controls |
| `Ctrl+Shift+A` | Show All Panels |
| `Ctrl+Shift+F` | Focus on Plot (hide all panels) |
| `Ctrl+Shift+R` | Reset Layout |
| `Ctrl+H` | Hardware Configuration |
| `F5` | Start Test |
| `F6` | Stop Test |
| `F1` | Keyboard Shortcuts Help |

### Creating Dock Widgets
```python
def create_dock_widget(self, name, title, widget, area, shortcut):
    dock = QDockWidget(title, self)
    dock.setObjectName(name)  # Required for state saving
    dock.setWidget(widget)
    self.addDockWidget(area, dock)
    # Toggle action is auto-created
    toggle_action = dock.toggleViewAction()
    toggle_action.setShortcut(shortcut)
```

### Layout Persistence
```python
# Save on close
self.settings.setValue("geometry", self.saveGeometry())
self.settings.setValue("windowState", self.saveState())

# Restore on startup
self.restoreGeometry(self.settings.value("geometry"))
self.restoreState(self.settings.value("windowState"))
```

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

### PyQt5 Signal/Slot Pattern
```python
# In thread class
class ControlThread(QThread):
    stage_changed = pyqtSignal(int, int, str)  # current, total, name
    io_state_changed = pyqtSignal(str, bool)   # device_name, state
    
# In main window
self.control_thread.stage_changed.connect(self.on_stage_changed)
```

### WidgetLords SPI Module Pattern
```python
from epdm_vacuum.daq.widgetlords_interface import (
    WidgetLordsInterface,
    create_widgetlords_interface_from_config
)

# Create from config
interface = create_widgetlords_interface_from_config(config)
interface.connect()

# Control relays by module and channel name
interface.set_relay("relay_module", "vacuum_pump", True)

# Read analog inputs
voltage = interface.read_analog("analog_inputs", "pressure_sensor")

# Read all enabled channels
data = interface.read()  # Returns dict with all readings
```

## Hardware Configuration

### WidgetLords PI-SPI-DIN Modules (SPI)
The system supports multiple PI-SPI-DIN modules via SPI bus:

**Available Module Types:**
- `PI-SPI-DIN-4KO`: 4× Relay Outputs (2A AC/DC SPDT) - stackable up to 4 per CE
- `PI-SPI-DIN-8AI`: 8× Analog Inputs (0-10V or 4-20mA)
- `PI-SPI-DIN-8DI`: 8× Digital Inputs (12-24V)
- `PI-SPI-DIN-4AO`: 4× Analog Outputs (0-10V)

**Chip Enables (CE0-CE4):**
| CE   | GPIO  | Description      |
|------|-------|------------------|
| CE0  | GPIO8 | SPI0 CE0 default |
| CE1  | GPIO7 | SPI0 CE1 default |
| CE2  | GPIO24| Extended CE      |
| CE3  | GPIO23| Extended CE      |
| CE4  | GPIO18| Extended CE      |

**Stacking 4KO Modules:**
The PI-SPI-DIN-4KO uses MCP23S08 with 4 addresses (0-3) per chip enable, allowing up to 16 relays per CE. Set address using J3-A0/A1 jumpers.

**Configuration:** Settings → Hardware Configuration (`Ctrl+H`)

### TLB4 Load Cell Transmitter (Modbus RTU)

The TLB4 connects via RS485. Two connection methods are supported:

**Option 1: WidgetLords PI-SPI-DIN-RTC-RS485 Module (Recommended)**
- Port: `/tmp/modbus` (virtual port created by modbusd daemon)
- The modbusd daemon handles GPIO25 direction control automatically
- Wiring: Terminal A (+) to TLB4 pin 29, Terminal B (-) to TLB4 pin 30

**Option 2: USB-RS485 Adapter (Waveshare, etc.)**
- Port: `/dev/ttyUSB0` (Linux) or `COM4` (Windows)
- No GPIO control needed (adapter handles direction)

**RS485 Direction Control Modes:**
1. `modbusd` service (recommended for WidgetLords): Install the WidgetLords `modbusd` daemon which automatically handles GPIO25 direction switching
2. Manual GPIO: Set `rs485.gpio_mode: manual` in config to let the driver control GPIO25

**Setup modbusd service:**
```bash
# Download from: https://github.com/widgetlords/modbusd/releases
sudo cp modbusd_arm64 /usr/local/bin/
sudo chmod +x /usr/local/bin/modbusd_arm64

# Create systemd service
sudo tee /etc/systemd/system/modbusd.service << 'EOF'
[Unit]
Description=modbusd RS485 direction control
[Service]
Type=simple
ExecStart=/usr/local/bin/modbusd_arm64 -d 25 -s /dev/serial0
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable modbusd
sudo systemctl start modbusd
```

**Common Settings:**
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
- Stylesheets for Qt widget styling (avoid inline where possible)

## Testing Workflow

1. Use `scripts/tlb4_register_scanner.py` to discover/verify register addresses
2. Update `hardware_config.yaml` with correct registers and scaling
3. Run `python -m epdm_vacuum.app_main` to test GUI
4. Check terminal logs for Modbus communication errors
5. Use View menu shortcuts to adjust layout for your workflow

## Common Issues

### "No communication with instrument"
- Check COM port is correct and not in use by another process
- Verify TLB4 is in Modbus mode (not "nOnE")
- Ensure correct baud rate (9600)

### RS485 communication issues (WidgetLords module)
- Verify wiring: A(+) to TLB4 terminal 29, B(-) to TLB4 terminal 30
- Check if `modbusd` service is running: `sudo systemctl status modbusd`
- If using manual GPIO mode, ensure RPi.GPIO is installed: `pip install RPi.GPIO`
- Check GPIO25 is not used by another process
- Enable UART: add `enable_uart=1` to `/boot/config.txt` and reboot
- Disable serial console: `sudo raspi-config` → Interface Options → Serial → No to login shell, Yes to serial hardware

### Permission errors on COM port
- Another Python process may have the port open
- Run: `Get-Process python | Stop-Process -Force` (Windows)

### Tare not updating in GUI
- TLB4 hardware tare only affects total weight, not individual channels
- Software tare offsets are stored in `_channel_tare_offsets`
- Total Force = sum of individual load cells (with software tare)

### Layout issues after code changes
- Delete saved settings: remove `HKEY_CURRENT_USER\Software\EPDM\VacuumTestFixture` (Windows Registry)
- Or use View → Reset Layout in the app

## Environment

- Windows 10/11 for development, Raspberry Pi 5 for deployment
- Python 3.11+ (tested with 3.14)
- VS Code with Remote-SSH for Pi development
- Key dependencies: PyQt5, pyqtgraph, minimalmodbus, numpy, PyYAML
