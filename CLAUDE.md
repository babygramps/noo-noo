# CLAUDE.md - AI Assistant Guidelines

## Project Overview

EPDM Gasket Vacuum Seal Testing System - Python/PyQt5 application for Raspberry Pi 5 that controls vacuum seal testing equipment via Modbus RTU (load cells) and SPI (analog I/O). Includes a web-based monitoring interface via FastAPI + Next.js.

**Purpose**: Automated vacuum seal testing for EPDM gaskets. The system draws vacuum in a sealed chamber, monitors pressure/force over time, and detects leaks through seal degradation.

## Quick Commands

```bash
# Run the GUI application (PyQt5)
python -m epdm_vacuum.app_main

# Run the FastAPI backend (for web interface)
python -m epdm_vacuum.api_main
# Or with uvicorn directly:
uvicorn epdm_vacuum.api_main:app --host 0.0.0.0 --port 8000

# Run the Next.js web frontend
cd web && npm run dev

# Start both backend and frontend (Windows)
./scripts/run_web.ps1

# Start both backend and frontend (Linux/Pi)
./scripts/run_web.sh

# TLB4 register scanner (discover Modbus registers)
python scripts/tlb4_register_scanner.py --port COM4 --interactive

# TLB4 slope calibration helper
python scripts/tlb4_slope_helper.py

# Install Python dependencies
pip install -r requirements.txt

# Install web dependencies
cd web && npm install
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
├── docs/                        # Documentation and reference PDFs
├── scripts/                     # Utility scripts
│   ├── run_web.ps1              # Start web UI (Windows)
│   ├── run_web.sh               # Start web UI (Linux)
│   ├── tlb4_register_scanner.py # Modbus register discovery
│   ├── tlb4_slope_helper.py     # Load cell calibration helper
│   └── test_pressure_reading.py # Pressure sensor debugging
├── src/epdm_vacuum/
│   ├── app_main.py              # PyQt5 GUI entry point
│   ├── api_main.py              # FastAPI server entry point
│   ├── api/                     # Web API layer (FastAPI)
│   │   ├── hardware_manager.py  # Singleton for thread-safe hardware access
│   │   ├── routes.py            # REST API endpoints
│   │   ├── websocket.py         # WebSocket manager for real-time data
│   │   └── models.py            # API data models
│   ├── config/
│   │   ├── settings.py          # Config loader, factory functions
│   │   └── hardware_config.yaml # Hardware parameters (CRITICAL FILE)
│   ├── daq/                     # Hardware abstraction
│   │   ├── hardware_interface.py    # Base class for all interfaces
│   │   ├── modbus_interface.py      # TLB4 Modbus RTU driver (load cells)
│   │   ├── widgetlords_interface.py # PI-SPI-DIN module driver (SPI)
│   │   ├── relay_state_manager.py   # Global relay state (SSOT)
│   │   └── calibration.py           # Sensor calibration utilities
│   ├── gui/
│   │   ├── main_window.py       # Main Qt window with dockable panels
│   │   ├── widgets/
│   │   │   ├── display_widget.py      # Large LCD sensor displays
│   │   │   ├── plot_widget.py         # Real-time pyqtgraph plots
│   │   │   ├── control_panel.py       # Test/pump control buttons
│   │   │   ├── sequence_selector.py   # Test sequence dropdown
│   │   │   ├── test_status_panel.py   # Stage progress + IO status
│   │   │   ├── stage_progress_widget.py
│   │   │   └── io_status_widget.py    # Relay/valve state indicators
│   │   ├── threads/
│   │   │   ├── daq_thread.py          # Background sensor reading (10Hz)
│   │   │   └── control_thread.py      # Test execution thread
│   │   └── dialogs/
│   │       ├── sequence_editor.py     # Test sequence editor
│   │       ├── gasket_weighing_dialog.py  # Pre-test weighing workflow
│   │       ├── io_action_dialog.py    # I/O action editor
│   │       ├── io_config_dialog.py    # IO device configuration
│   │       ├── spi_config_dialog.py   # Widgetlords SPI module setup
│   │       └── test_metadata_dialog.py
│   ├── control/
│   │   ├── sequence.py          # TestSequence, TestStage, IOAction dataclasses
│   │   ├── sequence_manager.py  # Load/save/validate sequences
│   │   ├── test_controller.py   # Test execution engine (IMPORTANT)
│   │   ├── pump_controller.py   # Pump control logic
│   │   └── safety_monitor.py    # Safety limit monitoring
│   └── logging/
│       ├── data_logger.py       # CSV/HDF5/JSON export
│       └── buffer.py            # In-memory data buffer
└── web/                         # Next.js Web Frontend
    ├── package.json             # Node.js dependencies
    ├── src/
    │   ├── app/
    │   │   ├── page.tsx         # Main dashboard page
    │   │   ├── layout.tsx       # App layout
    │   │   └── globals.css      # Tailwind styles
    │   ├── components/
    │   │   ├── ControlPanel.tsx      # Test controls, valve toggles
    │   │   ├── SensorDisplay.tsx     # Pressure/force displays
    │   │   ├── LiveChart.tsx         # Real-time Recharts graph
    │   │   ├── StageProgress.tsx     # Stage list and progress
    │   │   ├── TestMetadataModal.tsx # Pre-test metadata form
    │   │   ├── GasketWeighingModal.tsx # Assembly weighing workflow
    │   │   └── TestDataBrowser.tsx   # Download/manage test data
    │   ├── hooks/
    │   │   └── useWebSocket.ts  # WebSocket hook for real-time data
    │   └── lib/
    │       └── api.ts           # API client functions
    └── tailwind.config.js       # Tailwind CSS configuration
```

## Dual Interface Architecture

The system has two user interfaces:

### 1. PyQt5 Desktop GUI (`app_main.py`)
- For operator use on the Raspberry Pi directly
- Full-featured with sequence editor, calibration dialogs
- Uses PyQtGraph for real-time plotting
- Runs DAQ thread for sensor reading

### 2. Web Interface (FastAPI + Next.js)
- For remote monitoring from any device on the network
- React-based dashboard at `http://<pi-ip>:3000`
- FastAPI backend at `http://<pi-ip>:8000`
- Real-time data via WebSocket (`ws://<pi-ip>:8000/api/ws`)

**Important**: Run EITHER the GUI OR the Web API, not both simultaneously (they share hardware access).

## FastAPI Backend Architecture

### Entry Point (`api_main.py`)

```python
# Uses uvicorn ASGI server
uvicorn epdm_vacuum.api_main:app --host 0.0.0.0 --port 8000

# Lifespan management handles:
# - Hardware initialization
# - Sensor broadcast thread startup
# - WebSocket event callback setup
# - Graceful shutdown
```

### HardwareManager Singleton (`api/hardware_manager.py`)

Thread-safe singleton managing all hardware access:

```python
from epdm_vacuum.api.hardware_manager import get_hardware_manager

hw = get_hardware_manager()
hw.initialize()  # Called once at startup

# Hardware control
hw.set_pump(True)
hw.set_valve("vacuum_valve", True)  # True = CLOSED (NO valves)
hw.tare_load_cells()

# Sensor data
data = hw.get_sensor_data()  # Returns latest cached readings

# Test control
hw.start_test("300mbar3times", metadata={"operator": "John"})
hw.stop_test()
status = hw.get_test_status()
```

### REST API Endpoints (`api/routes.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/status` | System status (connections, test state) |
| GET | `/api/sensors` | Current sensor readings |
| GET | `/api/io/states` | Current relay/valve states |
| POST | `/api/pump/on` | Turn pump ON |
| POST | `/api/pump/off` | Turn pump OFF |
| POST | `/api/valve/{name}/{action}` | Control valve (open/close) |
| POST | `/api/tare` | Tare load cells |
| GET | `/api/sequences` | List available sequences |
| GET | `/api/sequences/{name}` | Get sequence details |
| POST | `/api/sequences` | Create/update sequence |
| POST | `/api/test/start` | Start test with sequence |
| POST | `/api/test/stop` | Stop running test |
| GET | `/api/test/status` | Get test execution status |
| GET | `/api/data` | List test data files |
| GET | `/api/data/{filename}` | Download test data file |
| GET | `/api/data/{filename}/metadata` | Get test metadata |
| DELETE | `/api/data/{filename}` | Delete test data |
| WS | `/api/ws` | WebSocket for real-time data |

### WebSocket Messages (`api/websocket.py`)

The WebSocket streams these message types at 10Hz:

```typescript
// Sensor data (10Hz)
{ type: "sensor_data", data: { vacuum_bar, pressure_psi, load_cell_1_kg, ... } }

// Test events
{ type: "status", message: "Starting stage: Evacuate" }
{ type: "stage_change", data: { stage_index, stage_name, current_cycle, total_cycles } }
{ type: "progress", data: { progress: 0.75, status: "Reaching setpoint..." } }
{ type: "io_change", data: { device: "vacuum_valve", state: true } }
{ type: "test_complete" }
{ type: "error", message: "..." }

// Connection management
{ type: "connected", data: { ...system_status } }
{ type: "heartbeat" }
{ type: "pong" }
```

## Next.js Web Frontend

### Key Components

**Dashboard (`page.tsx`)**: Main layout with grid of panels

**SensorDisplay**: LCD-style displays for vacuum and load cells

**LiveChart**: Real-time Recharts line graph with vacuum and force traces

**ControlPanel**: 
- Sequence selector dropdown
- Start/Stop test buttons  
- Manual pump/valve toggles
- Tare button
- Weigh Assembly button

**StageProgress**: Shows current stage, progress bar, cycle info

**TestMetadataModal**: Pre-test form for operator, test name, notes

**GasketWeighingModal**: Workflow for weighing assembly before test:
- Live weight display with stability detection
- Tare functionality
- Assembly ID and description fields
- Captures weight to include in test metadata

**TestDataBrowser**: Modal for managing test data:
- List all CSV/JSON files in `data/` directory
- Download individual files
- Delete old test data
- View metadata summary

### WebSocket Hook (`useWebSocket.ts`)

```typescript
const { 
  isConnected, 
  currentData,      // Latest sensor readings
  dataHistory,      // Array for charting (last N points)
  ioStates,         // { vacuum_pump: true, vacuum_valve: false, ... }
  stageInfo,        // Current stage details
  progress,         // { progress: 0.5, status: "..." }
  testRunning,
  clearHistory,
} = useSensorData(600); // Keep 600 samples (1 min at 10Hz)
```

### API Client (`api.ts`)

```typescript
import * as api from '@/lib/api';

// All functions return Promise with typed responses
await api.getStatus();
await api.pumpOn();
await api.controlValve('vacuum_valve', 'open');
await api.startTest('300mbar3times', { operator: 'John' });
await api.stopTest();
await api.listTestData();
await api.deleteTestData('test_20241210_143022.csv');
```

### Environment Variables

Create `web/.env.local` for custom API URL:

```bash
# Default: uses same host as frontend
NEXT_PUBLIC_API_URL=http://192.168.1.100:8000
NEXT_PUBLIC_WS_HOST=192.168.1.100:8000
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

**In Web API:**
- `POST /api/valve/vacuum_valve/close` → relay ON → valve physically closed
- `POST /api/valve/vacuum_valve/open` → relay OFF → valve physically open

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
User clicks Start Test (GUI or Web)
        ↓
[GUI] MainWindow.on_start_test()  OR  [API] POST /api/test/start
        ↓
[GUI] ControlThread.run()  OR  [API] HardwareManager._run_test() thread
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
    description: str = ""         # Optional description

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
    created_date: Optional[str] = None
    modified_date: Optional[str] = None
    author: Optional[str] = None
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

# I/O Device Roles for automatic sequence validation
io_devices:
  digital_outputs:
    - name: vacuum_pump
      channel: 0
      device_role: vacuum_pump      # Controlled by pump_mode
      description: Main vacuum pump relay
    
    - name: vacuum_valve
      channel: 1
      device_role: vacuum_valve     # Opens to connect pump to chamber
      description: Vacuum valve - between pump and chamber
    
    - name: vent_valve
      channel: 2
      device_role: vent_valve       # Opens to release vacuum
      description: Vent valve - releases chamber to atmosphere

# API Configuration
api:
  enabled: false     # Set to true to enable web API
  host: 0.0.0.0
  port: 8000
  debug: false
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
- Test metadata (operator, test_name, test_id, notes)
- Gasket assembly weight (if captured)
- Sequence definition with all stages
- Data interpretation guide (column meanings, sign conventions)

### Test Data Management via API
```bash
# List test files
GET /api/data
# Returns: { files: [{ filename, size_formatted, modified_time, test_name, ... }] }

# Download file
GET /api/data/test_20241210_143022.csv

# Get metadata
GET /api/data/test_20241210_143022.csv/metadata

# Delete file (also deletes companion JSON)
DELETE /api/data/test_20241210_143022.csv
```

## Debugging & Troubleshooting

### Log Analysis
```bash
# Run GUI with DEBUG logging
python -m epdm_vacuum.app_main 2>&1 | tee debug.log

# Run API with logging
python -m epdm_vacuum.api_main
# Logs to: epdm_vacuum_api.log

# Key log prefixes to search for:
# [RUN_TEST] - Test execution flow
# [STAGE_EXEC] - Stage execution details
# [SETPOINT] - Vacuum setpoint checking
# [MAINTAIN] - Pump cycling in maintain mode
# [IO_ACTION] - IO action execution
# [PUMP] - Pump control
# [RSM] - RelayStateManager operations
# [MODBUS DIAGNOSTIC] - Load cell readings
# [WebSocket] - WebSocket connections (in browser console)
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

**WebSocket not connecting**
- Check FastAPI backend is running on port 8000
- Verify CORS is enabled (default: allow all origins)
- Check browser console for connection errors
- Verify firewall allows port 8000

**Web frontend shows stale data**
- Check WebSocket connection status (header shows Live/Offline)
- Browser will auto-reconnect after 3 seconds
- Clear browser cache if issues persist

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
        description: Connect pump to chamber
      - device_name: vent_valve
        action_type: digital_output
        value: false               # CLOSE the valve (relay will be ON)
        timing: start_of_stage
        description: Seal chamber
  
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
- **Node.js**: 18+ (for web frontend)
- **Remote Development**: VS Code with Remote-SSH

### Key Python Dependencies
- PyQt5, pyqtgraph (GUI)
- minimalmodbus, pyserial (Modbus RTU)
- widgetlords (Pi only, SPI modules)
- numpy, pandas (data processing)
- PyYAML, python-dotenv (configuration)
- fastapi, uvicorn (Web API)

### Key Web Dependencies
- Next.js 14 (React framework)
- Tailwind CSS (styling)
- Recharts (charts)
- Lucide React (icons)

## Deployment on Raspberry Pi

The system should run independently of SSH connections so tests continue even if your computer sleeps.

### Option 1: Systemd Services (Production)

Services auto-start on boot and restart on crash:

```bash
# Install services
sudo ./scripts/install_services.sh

# Useful commands
sudo systemctl status epdm-api        # Check API status
sudo systemctl status epdm-web        # Check web status
sudo journalctl -u epdm-api -f        # View API logs
sudo journalctl -u epdm-web -f        # View web logs
sudo systemctl restart epdm-api       # Restart API
sudo systemctl restart epdm-web       # Restart web
sudo ./scripts/install_services.sh remove  # Uninstall

# Service files are in systemd/ directory
```

### Option 2: tmux Sessions (Development)

Run in detached sessions that survive SSH disconnect but not reboot:

```bash
# Start both services
./scripts/run_detached.sh

# Reconnect to see output (after SSH reconnection)
tmux attach -t epdm-api
tmux attach -t epdm-web

# Detach from session (keeps running): Ctrl+B then D

# Other commands
./scripts/run_detached.sh stop        # Stop all
./scripts/run_detached.sh status      # Show status
./scripts/run_detached.sh restart     # Restart all
```

### Web Interface Access

After deployment, access the web UI from any device on the same network:

```
http://<pi-ip>:3000      # Web interface
http://<pi-ip>:8000      # API
http://<pi-ip>:8000/docs # API documentation
```

Find Pi's IP: `hostname -I` on the Pi, or check your router.

## Future LLM Context Notes

1. **When modifying IO actions**: Remember valve inversion - sequences use "desired state" (OPEN/CLOSED), code inverts for NO valves
2. **When debugging vacuum**: Check vacuum_bar (positive magnitude) vs pressure_psig (signed gauge)
3. **When adding new relays**: Update hardware_config.yaml, RelayStateManager interlocks if needed, and io_devices section
4. **When modifying test execution**: All flow goes through TestController, callbacks notify both GUI and Web API
5. **Thread safety**: DAQ thread reads continuously; Modbus writes use locks; RelayStateManager is thread-safe singleton; HardwareManager is singleton with sensor read thread
6. **Logging is verbose**: Search logs by prefix for specific subsystems
7. **Web vs GUI**: Run only one at a time - they share hardware access. Web API uses HardwareManager singleton, GUI uses direct interfaces.
8. **WebSocket data flow**: HardwareManager._sensor_loop() → sensor_broadcaster → WebSocket clients
9. **Test events**: TestController callbacks → HardwareManager callbacks → event_broadcaster → WebSocket → React components
10. **Deployment**: Use systemd services (production) or tmux (development) so tests survive SSH disconnect
