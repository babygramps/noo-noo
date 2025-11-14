# Vacuum Seal Test Fixture - Software Stack

**Project:** EPDM Gasket Vacuum Seal Testing System  
**Platform:** Raspberry Pi 5 (ARM64)  
**Date:** November 2024  
**Version:** 1.1

---

## 📋 Project Overview

This software controls a vacuum seal testing system for EPDM gaskets. It interfaces with:

- **WidgetLords PLC DAQ** (SPI) - Analog inputs and relay outputs
- **TLB4 Load Cell Transmitter** (Modbus RTU) - Four 200kg load cells
- **SPT25-20-V30D Pressure Sensor** - 0-30 PSI vacuum measurement

The system provides:
- Real-time data acquisition and visualization
- Automated test sequence control
- Safety monitoring and interlocks
- Data logging (CSV and HDF5)
- Optional remote monitoring via Flask API

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RASPBERRY PI 5 (8GB RAM)                │
│                     Debian 12 (Bookworm)                   │
│                        Python 3.11+                        │
└─────────────────────────────────────────────────────────────┘
            │
            ├─────────────────────┬─────────────────────┐
            │                     │                     │
        [GPIO 40-pin]         [USB Port]            [HDMI]
            │                     │                     │
            ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────┐
│ WidgetLords  │    │  USB-RS485       │    │ Monitor  │
│ PLC DAQ      │    │  Modbus Adapter  │    │ Display  │
│ (SPI Bus)    │    │  (FT232RL)       │    │          │
└──────────────┘    └──────────────────┘    └──────────┘
```

---

## 🚀 Quick Start

### Prerequisites

Ensure you're working on the Raspberry Pi 5 with:
- Raspberry Pi OS (64-bit) based on Debian 12 Bookworm
- Python 3.11 or higher
- SSH enabled (for remote development)

### System Dependencies

Install required system packages:

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-pyqt5 \
    python3-pyqt5.qtcharts \
    libatlas-base-dev \
    build-essential \
    git
```

### Initial Setup

1. **Clone the repository:**

```bash
cd /home/pi/projects
git clone <repository-url> epdm-vacuum-fixture
cd epdm-vacuum-fixture
```

2. **Run the automated setup script:**

```bash
chmod +x scripts/setup_venv.sh
./scripts/setup_venv.sh
```

This will:
- Create a Python virtual environment in `./venv`
- Upgrade pip
- Install all dependencies from `requirements.txt`

3. **Verify installation:**

```bash
source venv/bin/activate
python -c "import PyQt5; import minimalmodbus; print('Dependencies OK')"
```

---

## 🧑‍💻 Development Workflow

### Remote Development (Recommended)

This project is designed for **remote development** using VS Code Remote-SSH:

1. **On your laptop:**
   - Install VS Code
   - Install the "Remote - SSH" extension
   - Configure SSH access to your Pi

2. **Connect to Pi:**
   - Open VS Code
   - Press `F1` → "Remote-SSH: Connect to Host"
   - Enter `pi@<PI_IP_ADDRESS>`

3. **Open the project:**
   - File → Open Folder → `/home/pi/projects/epdm-vacuum-fixture`

4. **Use the integrated terminal:**
   - All commands run **on the Pi**, not your laptop
   - Hardware access (GPIO, serial) only works on the Pi

### Running the Application

#### GUI Mode (Primary Interface)

```bash
cd /home/pi/projects/epdm-vacuum-fixture
source venv/bin/activate
python -m epdm_vacuum.app_main
```

Or use the convenience script:

```bash
./scripts/dev_run_gui.sh
```

The GUI will display on the Pi's HDMI monitor.

#### API Mode (Optional Remote Monitoring)

```bash
cd /home/pi/projects/epdm-vacuum-fixture
source venv/bin/activate
export FLASK_APP=epdm_vacuum.api_main
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=8000
```

Or use the convenience script:

```bash
./scripts/dev_run_api.sh
```

Access the API from your laptop at: `http://<PI_IP>:8000/`

---

## 📁 Project Structure

```
epdm-vacuum-fixture/
├── README.md                      # This file
├── requirements.txt               # Python dependencies
├── .gitignore                     # Git ignore patterns
├── pyproject.toml                 # Package metadata
├── venv/                          # Virtual environment (created by setup)
├── scripts/
│   ├── setup_venv.sh              # Initial setup automation
│   ├── dev_run_gui.sh             # Launch GUI application
│   └── dev_run_api.sh             # Launch Flask API
└── src/
    └── epdm_vacuum/
        ├── __init__.py
        ├── app_main.py            # PyQt5 GUI entry point
        ├── api_main.py            # Flask API entry point
        ├── gui/                   # PyQt5 GUI components
        │   ├── main_window.py     # Main application window
        │   ├── widgets/           # Custom UI widgets
        │   └── threads/           # Background threads (DAQ, control)
        ├── daq/                   # Hardware abstraction layer
        │   ├── hardware_interface.py       # Base interface
        │   ├── widgetlords_interface.py    # SPI communication
        │   ├── modbus_interface.py         # Modbus RTU
        │   └── calibration.py              # Sensor calibration
        ├── control/               # Test control logic
        │   ├── test_controller.py          # Test sequences
        │   ├── safety_monitor.py           # Safety interlocks
        │   └── pump_controller.py          # Vacuum pump control
        ├── logging/               # Data logging
        │   ├── data_logger.py              # CSV/HDF5 export
        │   └── buffer.py                   # Real-time buffering
        ├── api/                   # Flask REST API
        │   ├── routes.py                   # API endpoints
        │   └── models.py                   # Data models
        └── config/                # Configuration
            ├── settings.py                 # Config loader
            └── hardware_config.yaml        # Hardware parameters
```

---

## 🔌 Hardware Configuration

### WidgetLords Modules

- **PI-SPI-DIN-8AI** (8× Analog Inputs)
  - Channel 0: Pressure sensor (0-10 V)
  - Channels 1-7: Available for expansion

- **PI-SPI-DIN-4KO** (4× SPDT Relays)
  - Relay 0: Vacuum pump SSR control
  - Relays 1-3: Available for expansion

### Modbus Device

- **TLB4 Load Cell Transmitter**
  - Port: `/dev/ttyUSB0`
  - Baud: 9600
  - Slave Address: 1
  - 4× Load cells (200 kg each)

### Sensor Specifications

- **Pressure Sensor:** SPT25-20-V30D
  - Range: 0-30 PSI
  - Output: 0-10 V analog

---

## 🛠️ Configuration

Hardware parameters are configured in `src/epdm_vacuum/config/hardware_config.yaml`:

```yaml
pressure_sensor:
  channel: 0
  voltage_min: 0.0
  voltage_max: 10.0
  pressure_min_psi: 0.0
  pressure_max_psi: 30.0

modbus:
  port: /dev/ttyUSB0
  baudrate: 9600
  slave_address: 1
  timeout: 1.0

safety:
  max_vacuum_bar: 1.0
  max_force_kg: 800
  emergency_stop_enabled: true
```

Edit this file to match your hardware setup.

---

## 📊 Features

### Data Acquisition
- Multi-threaded sensor reading (10 Hz default)
- Real-time display of:
  - Vacuum pressure (bar, PSI)
  - Total force (kg)
  - Individual load cell readings
- Automatic error detection and recovery

### Visualization
- Real-time plotting (pyqtgraph)
- Force vs. Time
- Vacuum vs. Time
- Force vs. Vacuum (optional)

### Test Sequencing
- **Create and edit multi-stage test sequences**
- **Flexible completion:** Stages end when setpoint reached OR time limit (whichever comes first)
- **Intelligent pump control:** Continuous, maintain vacuum (cycling), or OFF modes
- **Save/load sequences:** Reusable test configurations stored as YAML files
- **Unified editor:** Clean interface showing all parameters at once
- **I/O control panel:** Visual display of all valve/relay states per stage
- **Real-time validation:** Immediate feedback with warnings and errors
- **Stage management:** Add, remove, duplicate, and reorder test stages
- **Progress tracking:** Live updates showing current stage and completion reason

### Test Control
- Automated multi-stage test sequences
- Manual pump control
- Load cell tare function
- Emergency stop
- Stage-by-stage execution with pause options

### Data Logging
- CSV export for analysis
- HDF5 format for large datasets
- Timestamped test records
- Per-stage data collection

### Safety Features
- Configurable pressure limits
- Configurable force limits
- Per-stage safety overrides
- Automatic pump shutdown on error
- Emergency stop button

---

## 🔧 Development Notes

### Current Implementation Status

This is a **scaffold implementation** with complete structure but placeholder logic. Each module contains:
- Full class definitions with docstrings
- Method signatures with type hints
- TODO comments indicating implementation points
- Basic error handling structure

### Next Steps for Development

1. **Implement Hardware Interfaces** (`daq/` modules)
   - Test WidgetLords SPI communication
   - Test Modbus RTU communication
   - Implement calibration routines

2. **Build GUI Components** (`gui/` modules)
   - Complete real-time display widgets
   - Implement plot updates
   - Add user controls

3. **Add Control Logic** (`control/` modules)
   - Define test sequences
   - Implement safety checks
   - Add pump control logic

4. **Implement Data Logging** (`logging/` modules)
   - CSV writer
   - HDF5 writer
   - Buffer management

5. **Test Integration**
   - End-to-end testing with hardware
   - Safety system validation
   - Performance optimization

---

## 🧪 Test Sequencing

### Overview

The test sequencing feature allows you to create, save, load, and execute multi-stage test sequences with intelligent completion logic. This is useful for:
- Testing seals at multiple vacuum levels with setpoint control
- Endurance testing with time-based or setpoint-based completion
- Automated sequences that adapt to actual vacuum performance
- Standardized QA testing procedures with reproducible results
- Complex valve sequencing and I/O control

### Creating a Sequence

1. **From the GUI:**
   - Click **Sequence → New Sequence** or use the **New** button in the sequence selector
   - Enter a name for your sequence
   - The sequence editor dialog will open

2. **Creating and Configuring Stages:**
   
   The editor shows a unified interface with all controls visible:
   
   **Stages Table:**
   - Lists all stages with name, setpoint, time limit, pump mode
   - Click "Add Stage" to create a new stage
   - Duplicate, remove, or reorder stages using the buttons
   - Select a stage to configure it in the panel below
   
   **Stage Configuration Panel:**
   - **Stage Name:** Descriptive name for the stage
   - **Completion Conditions:** (stage ends when FIRST condition is met)
     - ☑ Vacuum Setpoint: Target vacuum in bar
     - ☑ Time Limit: Maximum duration in seconds
     - ☐ Minimum Time: Optional minimum hold before checking setpoint
   - **Pump Control Mode:**
     - Continuous ON: Pump runs entire stage
     - Maintain Vacuum: Pump cycles to maintain setpoint (recommended)
     - OFF: Pump stays off (for venting/manual stages)
   - **I/O Device States:**
     - All available devices shown with dropdown controls
     - Set state at start and end of stage (CLOSED/OPEN/Not Set)
     - Auto-configured defaults for common vacuum test setup

3. **Completion Conditions:**
   
   Each stage can end when:
   - **Setpoint Reached:** Vacuum reaches target (e.g., 0.5 bar)
   - **Time Limit:** Maximum duration exceeded (e.g., 60 seconds)
   - **Both:** Whichever happens first (recommended for safety)
   - **Neither:** Stage runs indefinitely until manual stop
   
   Example: "0.5 bar OR 60s max" = Stage ends as soon as vacuum hits 0.5 bar, or after 60 seconds if setpoint not reached

4. **Validation:**
   - The editor validates all parameters in real-time
   - Errors (red) prevent saving
   - Warnings (orange) allow saving with confirmation
   - Estimated total test duration is displayed
   - Click "Validate" to see a detailed report

5. **Saving:**
   - Click "Save" to save the sequence as a YAML file in the `sequences/` directory
   - Sequences are automatically validated before saving
   - Warnings will prompt for confirmation before saving

### Loading and Running Sequences

1. **Load a Sequence:**
   - Use the dropdown in the sequence selector to choose from saved sequences
   - Or click **Sequence → Load Sequence** to browse for a file
   - Sequence info (stages, duration, mode) is displayed once loaded

2. **Edit an Existing Sequence:**
   - Select a sequence from the dropdown
   - Click **Edit** or use **Sequence → Edit Sequence**
   - Make your changes in the editor
   - Save to update the file

3. **Run a Test:**
   - Select your sequence from the dropdown
   - Click **Start Test** in the control panel or press **F5**
   - The test will execute each stage in order
   - Current stage progress is shown in the status bar
   - Data is collected for each stage independently

### Pump Control Modes

Each stage can use one of three pump control modes:

**Continuous ON:**
- Pump runs continuously during the entire stage
- Use for: Initial vacuum ramp, fast evacuation
- Simple and predictable behavior

**Maintain Vacuum (Recommended):**
- Pump cycles ON/OFF to maintain setpoint within tolerance
- Use for: Holding at specific vacuum levels, leak testing
- Reduces pump wear and power consumption
- Only works with a vacuum setpoint configured

**OFF:**
- Pump stays off during the stage
- Use for: Venting stages, manual operations, atmospheric tests
- Often combined with vent valve I/O actions

### I/O Control and Valve Sequencing

The sequencing system includes powerful I/O control for managing valves, relays, and other actuators.

#### Configurable I/O Devices

Available I/O devices are defined in `hardware_config.yaml`:
- **vacuum_pump** - Main vacuum pump relay (controlled automatically by pump mode)
- **vent_valve** - Vent valve for pressure release
- **inlet_valve** - Inlet valve for chamber access
- **safety_valve** - Emergency safety relief valve
- **proportional_valve** - Analog control valve (0-10V)

#### Setting I/O States

In the sequence editor:
1. Select a stage from the stages table
2. In the Stage Configuration panel, scroll to "I/O Device States"
3. **All available I/O devices are displayed automatically**
4. For each device, set the state using dropdown menus:
   - **State at Start**: Device state when the stage begins (Not Set, CLOSED, OPEN)
   - **State at End**: Device state when the stage completes (Not Set, CLOSED, OPEN)
5. Changes are saved automatically to the stage

#### Auto-Generated I/O States

When you create a new stage, the system automatically configures essential I/O states:
- **inlet_valve** → CLOSED at start and end (seals chamber)
- **vent_valve** → CLOSED at start, OPEN at end (enables vacuum, then releases)
- **safety_valve** → CLOSED at start and end

**All available I/O devices are shown in the control panel** for each stage. You can see and modify any device state using the dropdown menus:
- **Not Set** - Device state not controlled in this stage
- **CLOSED** - Device is closed/off (valve closed, relay off)
- **OPEN** - Device is open/on (valve open, relay on)

The I/O control panel makes it easy to see the complete I/O configuration at a glance.

#### Validation System

The system validates your sequences and provides:

**Errors (Red - Prevents Saving):**
- Invalid parameter ranges (vacuum > 1.0 bar, negative times, etc.)
- Missing sequence name
- I/O action configuration errors

**Warnings (Orange - Allows Saving with Confirmation):**
- No completion condition set (stage runs indefinitely)
- Missing recommended I/O actions (inlet/vent valves)
- Pump mode mismatch (e.g., "Maintain" without setpoint)
- Very long durations

Validation runs automatically as you edit, with color-coded feedback in the status bar.

### Example Sequences

Several example sequences are included in the `sequences/` directory:

- **quick_test.yaml:** Single-stage test with setpoint and time limit (0.5 bar OR 30s)
- **simple_multi_stage.yaml:** Three stages testing at different vacuum levels with maintain mode
- **endurance_test.yaml:** Extended 5-minute time-based test with maintain vacuum mode
- **setpoint_only_test.yaml:** Demonstrates setpoint-based completion without time limits
- **venting_stage_example.yaml:** Shows pump OFF mode for controlled venting stages

### Sequence File Format

Sequences are stored as YAML files. Example structure:

```yaml
name: My Test Sequence
description: Description of what this test does
stages:
  - name: Stage 1
    target_vacuum_bar: 0.5      # Setpoint (null = no setpoint)
    max_time_seconds: 30.0      # Time limit (null = no limit)
    min_time_seconds: 0.0       # Minimum hold time
    pump_mode: maintain         # continuous, maintain, or off
    vacuum_tolerance_bar: 0.05  # For maintain mode
    collect_data: true
    io_actions:
      # I/O actions define valve/relay states
      - device_name: inlet_valve
        action_type: digital_output
        value: false              # false = CLOSED, true = OPEN
        timing: start_of_stage
        delay_seconds: 0.0
        description: Close inlet valve
      
      - device_name: vent_valve
        action_type: digital_output
        value: false
        timing: start_of_stage
        delay_seconds: 0.0
        description: Close vent valve
      
      - device_name: vent_valve
        action_type: digital_output
        value: true
        timing: end_of_stage
        delay_seconds: 0.0
        description: Open vent valve
```

**Key Parameters:**
- `target_vacuum_bar`: Vacuum setpoint (null for no setpoint)
- `max_time_seconds`: Time limit (null for no limit)
- `min_time_seconds`: Minimum hold before checking setpoint
- `pump_mode`: `continuous`, `maintain`, or `off`
- `vacuum_tolerance_bar`: Tolerance for maintain mode (default 0.05)
- `io_actions`: List of I/O control actions (auto-generated for new stages)

### Tips

- **Use Both Conditions:** Set both setpoint AND time limit for safety (stage ends at first condition)
- **Maintain Mode:** Use "Maintain Vacuum" pump mode for stable, long-duration holds
- **Minimum Time:** Set minimum time if you need setpoint to stabilize before moving on
- **Copy and Modify:** Duplicate existing stages to create variations quickly
- **Name Stages:** Give stages descriptive names for easier tracking during execution
- **Validate Often:** Use the validation button to catch errors and review warnings
- **Test Incrementally:** Start with short time limits and increase gradually
- **I/O Defaults:** New stages come with sensible I/O defaults - modify as needed
- **Setpoint-Only:** For setpoint-only stages, set time limit to null (uncheck the box)
- **Time-Only:** For time-only stages, set setpoint to null (uncheck the box)
- **Emergency Stop:** All operations respect the emergency stop button

---

## 📝 License

[Specify your license here]

---

## 🤝 Contributing

[Add contribution guidelines if applicable]

---

## 📧 Contact

[Add contact information]

---

**Note:** This software is designed for industrial testing equipment. Always follow proper safety procedures when operating vacuum systems and load testing equipment.

