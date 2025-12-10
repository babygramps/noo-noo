# CLAUDE.md - AI Assistant Guidelines

## Project Overview

EPDM Gasket Vacuum Seal Testing System - Python/PyQt5 application for Raspberry Pi 5 that controls vacuum seal testing equipment via Modbus RTU (load cells) and SPI (analog I/O).

**Purpose**: Automated vacuum seal testing for EPDM gaskets. The system draws vacuum in a sealed chamber, monitors pressure/force over time, and detects leaks through seal degradation.

## Quick Commands

```bash
# Run the GUI application
python -m epdm_vacuum.app_main

# Run Flask API (optional remote monitoring)
python -m epdm_vacuum.api_main

# TLB4 register scanner (discover Modbus registers)
python scripts/tlb4_register_scanner.py --port COM4 --interactive

# TLB4 slope calibration helper
python scripts/tlb4_slope_helper.py

# Install dependencies
pip install -r requirements.txt
```

## Project Structure

```
noo-noo/
├── CLAUDE.md                    # This file - AI context
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Package configuration
├── sequences/                   # Test sequence YAML files
│   ├── 300mbar3times.yaml      # Multi-cycle leak test example
│   ├── quick_test.yaml         # Short test for debugging
│   └── ...
├── data/                        # Test output directory (CSV, JSON metadata)
├── scripts/                     # Utility scripts
│   ├── tlb4_register_scanner.py    # Modbus register discovery
│   ├── tlb4_slope_helper.py        # Load cell calibration helper
│   └── test_pressure_reading.py    # Pressure sensor debugging
└── src/epdm_vacuum/
    ├── app_main.py              # GUI entry point
    ├── api_main.py              # Flask API entry point
    ├── config/
    │   ├── settings.py          # Config loader, factory functions
    │   └── hardware_config.yaml # Hardware parameters (CRITICAL FILE)
    ├── daq/                     # Hardware abstraction
    │   ├── hardware_interface.py    # Base class for all interfaces
    │   ├── modbus_interface.py      # TLB4 Modbus RTU driver (load cells)
    │   ├── widgetlords_interface.py # PI-SPI-DIN module driver (SPI)
    │   ├── relay_state_manager.py   # Global relay state (SSOT)
    │   └── calibration.py           # Sensor calibration utilities
    ├── gui/
    │   ├── main_window.py       # Main Qt window with dockable panels
    │   ├── widgets/
    │   │   ├── display_widget.py      # Large LCD sensor displays
    │   │   ├── plot_widget.py         # Real-time pyqtgraph plots
    │   │   ├── control_panel.py       # Test/pump control buttons
    │   │   ├── sequence_selector.py   # Test sequence dropdown
    │   │   ├── test_status_panel.py   # Stage progress + IO status
    │   │   ├── stage_progress_widget.py
    │   │   └── io_status_widget.py    # Relay/valve state indicators
    │   ├── threads/
    │   │   ├── daq_thread.py          # Background sensor reading (10Hz)
    │   │   └── control_thread.py      # Test execution thread
    │   └── dialogs/
    │       ├── sequence_editor.py    # Test sequence editor
    │       ├── io_config_dialog.py   # IO device configuration
    │       ├── spi_config_dialog.py  # Widgetlords SPI module setup
    │       └── test_metadata_dialog.py
    ├── control/
    │   ├── sequence.py          # TestSequence, TestStage, IOAction dataclasses
    │   ├── sequence_manager.py  # Load/save/validate sequences
    │   ├── test_controller.py   # Test execution engine (IMPORTANT)
    │   ├── pump_controller.py   # Pump control logic
    │   └── safety_monitor.py    # Safety limit monitoring
    └── logging/
        ├── data_logger.py       # CSV/HDF5/JSON export
        └── buffer.py            # In-memory data buffer
```

## Critical Concepts

### Sign Conventions (IMPORTANT!)

**Pressure Sensor Output:**
- `pressure_psig`: Gauge pressure in PSI
  - NEGATIVE = vacuum (below atmospheric)
  - POSITIVE = pressurized (above atmospheric)
  - 0 = atmospheric pressure
- `vacuum_bar`: ALWAYS POSITIVE magnitude
  - 0.3 bar = 300 mbar vacuum (below atmosphere)
  - Used for setpoint comparisons in sequences
- `pressure_mbar`: Same sign convention as PSIG

**In Sequences:**
- `target_vacuum_bar: 0.3` means "reach 300 mbar of vacuum"
- Can also use negative gauge: `target_vacuum_bar: -0.3` (same meaning)

### Valve Types (CRITICAL!)

All valves are **NORMALLY-OPEN (NO)** type:
- Relay OFF (state=False) → Valve PHYSICALLY OPEN
- Relay ON (state=True) → Valve PHYSICALLY CLOSED

**In Sequences (io_actions):**
- `value: true` means "I want this valve OPEN" → relay becomes FALSE
- `value: false` means "I want this valve CLOSED" → relay becomes TRUE

The inversion happens in `test_controller.py:_execute_single_io_action()`:
```python
if is_valve:
    relay_state = not desired_state  # Invert for NO valves
```

### Relay State Management

**RelayStateManager** (`relay_state_manager.py`) is the **Single Source of Truth (SSOT)** for all relay/valve states:

```python
from epdm_vacuum.daq.relay_state_manager import relay_state_manager

# Set state (checks interlocks, notifies listeners)
success, error_msg = relay_state_manager.set_state("relay_module", "vacuum_valve", True)

# Get state
state = relay_state_manager.get_state("relay_module", "vacuum_valve")

# Listen for changes
relay_state_manager.add_listener(my_callback)
```

**Safety Interlocks** (disabled by default for development):
- Pump cannot run with vent valve open
- Both valves open simultaneously triggers warning
- Enable via `relay_state_manager.set_interlocks_enabled(True)`

### Test Execution Architecture

```
User clicks Start Test
        ↓
MainWindow.on_start_test()
        ↓
ControlThread.run() [background]
        ↓
TestController.run_test()
        ↓
TestController._run_sequence()
        ↓
For each stage in sequence:
    _execute_stage()
        ↓
    1. BEFORE_STAGE IO actions
    2. START_OF_STAGE IO actions
    3. Control pump based on pump_mode
    4. DURING_STAGE IO actions
    5. _run_stage_with_monitoring() [main loop]
        - Read sensors
        - Check completion conditions (setpoint OR time)
        - Update progress callbacks
        - Data logging
    6. END_OF_STAGE IO actions
    7. Turn off pump
    8. AFTER_STAGE IO actions
```

### Sequence Data Model

```python
# sequence.py contains:

class PumpMode(Enum):
    CONTINUOUS = "continuous"     # Pump ON entire stage
    MAINTAIN_VACUUM = "maintain"  # Cycle pump to maintain setpoint ±tolerance
    OFF = "off"                   # Pump stays OFF

class IOActionTiming(Enum):
    BEFORE_STAGE = "before_stage"
    START_OF_STAGE = "start_of_stage"
    DURING_STAGE = "during_stage"
    END_OF_STAGE = "end_of_stage"
    AFTER_STAGE = "after_stage"

class IOActionType(Enum):
    DIGITAL_OUTPUT = "digital_output"  # Set relay on/off
    ANALOG_OUTPUT = "analog_output"    # Set analog value
    PULSE = "pulse"                    # Pulse for duration

@dataclass
class IOAction:
    device_name: str              # "vacuum_valve", "vent_valve", "vacuum_pump"
    action_type: IOActionType
    value: Any                    # True/False for digital, float for analog
    timing: IOActionTiming
    delay_seconds: float = 0.0
    duration_seconds: Optional[float] = None  # For pulse

@dataclass
class TestStage:
    name: str
    target_vacuum_bar: Optional[float]  # Setpoint (None = no target)
    max_time_seconds: Optional[float]   # Time limit (None = unlimited)
    min_time_seconds: float = 0.0       # Min hold before checking setpoint
    pump_mode: PumpMode
    vacuum_tolerance_bar: float = 0.05  # For MAINTAIN mode
    io_actions: List[IOAction]
    collect_data: bool = True

@dataclass
class TestSequence:
    name: str
    stages: List[TestStage]
    cycles: int = 1               # Repeat entire sequence N times
    description: str = ""
```

### Stage Completion Conditions

Stages complete when FIRST condition is met:
1. **Setpoint reached**: `current_vacuum >= target_vacuum_bar` (magnitude comparison)
2. **Time limit**: `elapsed >= max_time_seconds`
3. **Manual stop**: User clicks Stop Test

For `PumpMode.MAINTAIN_VACUUM`, setpoint does NOT complete the stage - only time does. The pump cycles on/off to maintain vacuum at setpoint.

## Hardware Configuration

### hardware_config.yaml Structure

```yaml
hardware:
  widgetlords:
    enabled: true
    spi_modules:
      - name: relay_module              # Referenced as "relay_module" in code
        module_type: PI-SPI-DIN-4KO
        chip_enable: CE0
        address: 0
        channels:
          - channel: 0
            name: vacuum_pump           # Device names used in sequences
            enabled: true
          - channel: 1
            name: vacuum_valve
            enabled: true
          - channel: 2
            name: vent_valve
            enabled: true
      
      - name: analog_inputs
        module_type: PI-SPI-DIN-8AI
        chip_enable: CE1
        channels:
          - channel: 0
            name: pressure_sensor
            input_type: 4-20mA          # 4-20mA current loop
            low_input: 4.0              # 4mA = -14.7 PSIG (full vacuum)
            low_output: -14.7
            high_input: 20.0            # 20mA = +30 PSIG
            high_output: 30.0
            units: PSIG
  
  modbus:
    enabled: true
    port: /dev/ttyUSB0              # Linux (COM4 on Windows)
    baudrate: 9600
    slave_address: 1
    tlb4:
      registers:
        gross_weight: 7             # 0-based address (40008 - 40001)
        channel_1: 50               # After Command 25 enabled
        channel_2: 52
        channel_3: 54
        channel_4: 56
      channel_scaling:
        kg_per_division: 72000.0    # Calibrated value
```

### TLB4 Load Cell Transmitter (Modbus RTU)

**Communication:**
- Port: COM4 (Windows) or /dev/ttyUSB0 (Linux)
- Baud: 9600, Parity: None, Stop bits: 1
- Slave address: 1
- Function 16 ONLY for writes (not Function 6!)

**Key Registers (0-based addresses):**
- R0-1: Gross weight (32-bit)
- R2-3: Net weight (after tare)
- R5: Command register
- R50-57: Individual channels (after Command 25)

**Commands (write to R5):**
- 7: Semi-automatic tare
- 8: Zero scale
- 9: Switch to gross weight
- 25: Enable multi-channel HiRes mode (CRITICAL - sent on connect)

**Scaling:**
```
kg = raw_divisions / kg_per_division
```
Software tare offsets stored in `_channel_tare_offsets` list.

### WidgetLords PI-SPI-DIN Modules (SPI)

**Module Types:**
- `PI-SPI-DIN-4KO`: 4× Relay Outputs (2A SPDT)
- `PI-SPI-DIN-8AI`: 8× Analog Inputs (0-10V/4-20mA via MCP3208 ADC)
- `PI-SPI-DIN-8DI`: 8× Digital Inputs (12-24V)
- `PI-SPI-DIN-4AO`: 4× Analog Outputs (0-10V)

**Chip Enables:**
| CE   | GPIO  | Description      |
|------|-------|------------------|
| CE0  | GPIO8 | Relay module     |
| CE1  | GPIO7 | Analog inputs    |
| CE2-4| Extended CE for stacking |

**4-20mA Pressure Sensor:**
The 8AI module reads voltage. For 4-20mA sensors, voltage is converted:
```python
current_mA = (voltage / sense_resistor_ohms) * 1000.0
```
Sense resistor value (~454Ω) calibrated via GUI.

## Code Patterns

### Hardware Interface Pattern
```python
class HardwareInterface:
    def connect(self) -> bool
    def disconnect(self) -> bool
    def read(self) -> Dict[str, Any]
    def write(self, data: Dict[str, Any]) -> bool
    def is_connected(self) -> bool
```

### Thread Safety (Modbus)
```python
# ModbusInterface uses threading.Lock
with self._lock:
    # Serial port read/write operations
```

### PyQt Signal/Slot Connections
```python
# ControlThread signals
class ControlThread(QThread):
    status_update = pyqtSignal(str)
    test_complete = pyqtSignal()
    error_occurred = pyqtSignal(str)
    stage_changed = pyqtSignal(int, int, int, int, str)  # idx, per_cycle, cycle, total, name
    io_state_changed = pyqtSignal(str, bool)            # device, state
    stage_progress_updated = pyqtSignal(float, str)     # progress, status
    stage_completed = pyqtSignal(int, str)              # idx, reason

# DAQThread signals
class DataAcquisitionThread(QThread):
    new_data = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)
```

### Factory Functions (settings.py)
```python
from epdm_vacuum.config.settings import (
    get_settings,
    create_modbus_interface_from_settings,
    create_tlb4_config_from_settings,
)

# Create interfaces from hardware_config.yaml
settings = get_settings("src/epdm_vacuum/config/hardware_config.yaml")
modbus = create_modbus_interface_from_settings(settings)
modbus.connect()
```

### WidgetLords Interface Usage
```python
from epdm_vacuum.daq.widgetlords_interface import (
    WidgetLordsInterface,
    create_widgetlords_interface_from_config
)

interface = create_widgetlords_interface_from_config(config)
interface.connect()

# Control relays by module and channel name
interface.set_relay("relay_module", "vacuum_pump", True)

# Read analog inputs
data = interface.read()  # Returns dict with vacuum_bar, pressure_psig, etc.
```

## GUI Architecture

### Dockable Panel System
- **Central Widget**: PlotWidget (pyqtgraph, gets maximum space)
- **Dockable Panels**: DisplayWidget, TestStatusPanel, SequenceSelectorWidget, ControlPanel

### Keyboard Shortcuts
| Shortcut | Action |
|----------|--------|
| `Ctrl+1` | Toggle Sensor Display |
| `Ctrl+2` | Toggle Test Status |
| `Ctrl+3` | Toggle Test Sequence |
| `Ctrl+4` | Toggle Controls |
| `Ctrl+Shift+A` | Show All Panels |
| `Ctrl+Shift+F` | Focus on Plot |
| `Ctrl+Shift+R` | Reset Layout |
| `Ctrl+H` | Hardware Configuration |
| `F5` | Start Test |
| `F6` | Stop Test |
| `F1` | Keyboard Shortcuts Help |

### Layout Persistence
```python
# Save on close
self.settings.setValue("geometry", self.saveGeometry())
self.settings.setValue("windowState", self.saveState())

# Restore on startup
self.restoreGeometry(self.settings.value("geometry"))
self.restoreState(self.settings.value("windowState"))
```

## Data Logging

### CSV Output Format
Test data is saved real-time to CSV during execution. Each row contains:
- `timestamp`, `datetime`, `elapsed_time`
- `stage_index`, `stage_name`, `test_state`
- `vacuum_bar`, `pressure_psig`, `pressure_mbar`
- `target_vacuum_bar`
- `io_vacuum_pump`, `io_vacuum_valve`, `io_vent_valve` (OPEN/CLOSED)
- `total_force_kg`, `load_cell_1_kg` through `load_cell_4_kg`

### Metadata JSON
Companion JSON file with same name contains:
- Test system info
- Sequence definition with all stages
- Data interpretation guide (column meanings, sign conventions)
- User-provided test description

## Debugging & Troubleshooting

### Log Analysis
```bash
# Run with DEBUG logging
python -m epdm_vacuum.app_main 2>&1 | tee debug.log

# Key log prefixes to search for:
# [RUN_TEST] - Test execution flow
# [STAGE_EXEC] - Stage execution details
# [SETPOINT] - Vacuum setpoint checking
# [MAINTAIN] - Pump cycling in maintain mode
# [IO_ACTION] - IO action execution
# [PUMP] - Pump control
# [RSM] - RelayStateManager operations
# [MODBUS DIAGNOSTIC] - Load cell readings
```

### Common Issues

**"No communication with instrument"**
- Check COM port is correct and not in use
- Verify TLB4 is in Modbus mode (not "nOnE")
- Ensure correct baud rate (9600)

**Vacuum setpoint never reached**
- Check pressure sensor span scaling in hardware_config.yaml
- Verify vacuum_bar is being calculated correctly (check logs)
- Confirm vacuum valve opens (check IO status)

**Tare not working**
- TLB4 hardware tare only affects total, not individual channels
- Software tare offsets stored in `_channel_tare_offsets`
- Check for communication errors during tare command

**Relays not responding**
- Check interlocks (may be blocking): `relay_state_manager.are_interlocks_enabled()`
- Verify channel names match between config and sequence
- Check SPI module initialization in logs

**Wrong pressure readings**
- Calibrate sense resistor via GUI (Settings → Hardware → Calibrate Sense Resistor)
- Check span scaling: low_input/low_output, high_input/high_output
- Verify input_type matches sensor (4-20mA vs 0-10V)

### Registry/Settings Reset (Windows)
```powershell
# Delete saved window state
Remove-ItemProperty -Path "HKCU:\Software\EPDM\VacuumTestFixture" -Name *
```

## Sequence YAML Format

```yaml
name: Leak Test
description: Basic leak check at 300 mbar
cycles: 3
stages:
  - name: Evacuate
    target_vacuum_bar: 0.3         # Complete when vacuum reaches 0.3 bar
    max_time_seconds: 120.0        # ...or after 120 seconds
    min_time_seconds: 5.0          # Wait at least 5s before checking setpoint
    pump_mode: continuous          # Pump runs continuously
    collect_data: true
    io_actions:
      - device_name: vacuum_valve
        action_type: digital_output
        value: true                # OPEN the valve (relay will be OFF)
        timing: start_of_stage
      - device_name: vent_valve
        action_type: digital_output
        value: false               # CLOSE the valve (relay will be ON)
        timing: start_of_stage
  
  - name: Hold
    target_vacuum_bar: null        # No setpoint - just wait
    max_time_seconds: 180.0        # Complete after 180s
    pump_mode: off                 # Pump off for leak check
    io_actions:
      - device_name: vacuum_valve
        value: false               # Keep closed
        timing: start_of_stage
  
  - name: Vent
    max_time_seconds: 30.0
    pump_mode: off
    io_actions:
      - device_name: vent_valve
        value: true                # OPEN vent
        timing: start_of_stage
```

## Environment

- **Development**: Windows 10/11
- **Deployment**: Raspberry Pi 5
- **Python**: 3.11+ (tested with 3.14)
- **Remote Development**: VS Code with Remote-SSH

### Key Dependencies
- PyQt5, pyqtgraph (GUI)
- minimalmodbus, pyserial (Modbus RTU)
- widgetlords (Pi only, SPI modules)
- numpy, pandas (data processing)
- PyYAML, python-dotenv (configuration)
- flask, flask-cors (optional API)

## Future LLM Context Notes

1. **When modifying IO actions**: Remember valve inversion - sequences use "desired state" (OPEN/CLOSED), code inverts for NO valves
2. **When debugging vacuum**: Check vacuum_bar (positive magnitude) vs pressure_psig (signed gauge)
3. **When adding new relays**: Update hardware_config.yaml, RelayStateManager interlocks if needed
4. **When modifying test execution**: All flow goes through TestController, callbacks notify GUI
5. **Thread safety**: DAQ thread reads continuously; Modbus writes use locks; RelayStateManager is thread-safe singleton
6. **Logging is verbose**: Search logs by prefix for specific subsystems
