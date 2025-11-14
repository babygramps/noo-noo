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
- **Simple mode:** Quick setup with just vacuum target and hold time
- **Advanced mode:** Full control over ramp rates, sampling, and safety limits
- **Save/load sequences:** Reusable test configurations stored as YAML files
- **Visual editor:** Table-based interface with drag-and-drop reordering
- **Real-time validation:** Immediate feedback on parameter validity
- **Stage management:** Add, remove, duplicate, and reorder test stages
- **Progress tracking:** Live updates showing current stage during execution

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

The test sequencing feature allows you to create, save, load, and execute complex multi-stage test sequences. This is useful for:
- Testing seals at multiple vacuum levels
- Endurance testing with extended hold times
- Ramp rate sensitivity studies
- Standardized QA testing procedures

### Creating a Sequence

1. **From the GUI:**
   - Click **Sequence → New Sequence** or use the **New** button in the sequence selector
   - Enter a name for your sequence
   - The sequence editor dialog will open

2. **Sequence Editor Modes:**
   
   **Simple Mode:**
   - Quick stage creation with minimal parameters
   - Specify only vacuum target (bar) and hold time (seconds)
   - Uses default ramp rates and safety limits from configuration
   - Perfect for basic multi-level testing
   
   **Advanced Mode:**
   - Full control over all parameters:
     - Target vacuum pressure
     - Hold time
     - Ramp rate (bar/second)
     - Data sample rate (Hz)
     - Delay before stage
     - Per-stage force limits
     - Data collection options
   - Stage naming and descriptions
   - Pause between stages option

3. **Managing Stages:**
   - **Add Stage:** Click "Add Stage" to append a new stage
   - **Duplicate:** Select a stage and click "Duplicate" to create a copy
   - **Remove:** Select a stage and click "Remove" to delete it
   - **Reorder:** Use "Move Up" and "Move Down" buttons to change stage order
   - **Edit:** Double-click cells in the table to edit values directly

4. **Validation:**
   - The editor validates all parameters in real-time
   - Invalid values are highlighted with error messages
   - Estimated total test duration is displayed
   - Click "Validate" to see a detailed report

5. **Saving:**
   - Click "Save" to save the sequence as a YAML file in the `sequences/` directory
   - Sequences are automatically validated before saving

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

### Example Sequences

Several example sequences are included in the `sequences/` directory:

- **quick_test.yaml:** Single-stage 10-second test at 0.5 bar
- **simple_multi_stage.yaml:** Three stages testing at 0.3, 0.5, and 0.7 bar
- **advanced_detailed_test.yaml:** Comprehensive test with precise ramp rates and sampling control
- **endurance_test.yaml:** Extended 5-minute hold test for long-term seal evaluation

### Sequence File Format

Sequences are stored as YAML files. Example structure:

```yaml
name: My Test Sequence
description: Description of what this test does
mode: simple  # or 'advanced'
loop_count: 1
pause_between_stages: false
stages:
  - name: Stage 1
    target_vacuum_bar: 0.5
    hold_time_seconds: 30.0
    collect_data: true
    auto_vent: true
  - name: Stage 2
    target_vacuum_bar: 0.7
    hold_time_seconds: 45.0
    collect_data: true
    auto_vent: true
```

Advanced mode stages include additional parameters:
- `ramp_rate_bar_per_sec`: Control how quickly vacuum is applied
- `sample_rate_hz`: Data collection frequency
- `delay_before_seconds`: Wait time before starting stage
- `max_force_kg`: Per-stage force limit
- `max_single_cell_kg`: Per-cell force limit

### Tips

- **Start Simple:** Use simple mode for initial sequence development
- **Copy and Modify:** Duplicate existing sequences and modify them for new tests
- **Name Stages:** Give stages descriptive names for easier tracking during execution
- **Validate Often:** Use the validation button to catch errors before running
- **Test Incrementally:** Start with short hold times and increase gradually
- **Document Sequences:** Use the description field to note the purpose and expected results

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

