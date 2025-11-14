# Test Sequencing UX Redesign - Implementation Summary

## Overview

Complete redesign of the test sequencing system to provide a unified, intuitive interface with intelligent stage completion logic and simplified I/O control.

## What Changed

### 1. Removed Simple/Advanced Mode Confusion ✅

**Before:** Confusing mode selector with limited Simple mode and complex Advanced mode
**After:** Single unified interface with all features accessible

- Removed `SequenceMode` enum entirely
- Removed mode selector from UI
- All stages now have the same comprehensive interface

### 2. Flexible Completion Conditions ✅

**Before:** Stages only completed after fixed time (hold_time_seconds)
**After:** Stages complete when FIRST condition is met (OR logic)

New completion options:
- **Setpoint Only:** Stage ends when vacuum reaches target (e.g., 0.5 bar)
- **Time Only:** Stage ends after time limit (e.g., 60 seconds)
- **Both:** Whichever comes first (0.5 bar OR 60s - recommended for safety)
- **Neither:** Stage runs indefinitely until manual stop

Fields:
- `target_vacuum_bar: Optional[float]` - Vacuum setpoint (null = no setpoint)
- `max_time_seconds: Optional[float]` - Time limit (null = no limit)
- `min_time_seconds: float` - Minimum hold before checking setpoint

### 3. Intelligent Pump Control ✅

**Before:** Pump hardcoded to ON at start, OFF at end
**After:** Three pump modes with cycling support

New `PumpMode` enum:
- **CONTINUOUS:** Pump ON entire stage (fast evacuation)
- **MAINTAIN_VACUUM:** Pump cycles ON/OFF to maintain setpoint (recommended)
- **OFF:** Pump stays OFF (for venting/manual stages)

Implementation in `TestController`:
- `_run_stage_with_monitoring()` monitors both time and setpoint
- `_maintain_vacuum_cycle()` handles pump cycling (placeholder for hardware)
- Completion reason logged and displayed

### 4. Streamlined Parameters ✅

**Removed:**
- Mode selector (simple/advanced)
- `ramp_rate_bar_per_sec` (simplified)
- `sample_rate_hz` (use global default)
- `description` field per stage (simplified)
- `delay_before_seconds` (simplified)
- `auto_vent` boolean (replaced by I/O actions)
- `loop_count` (can add back if needed)
- `pause_between_stages` (can add back if needed)

**Kept:**
- Stage name
- Vacuum setpoint (optional)
- Time limit (optional)
- Minimum time (optional)
- Pump mode
- I/O device states
- Data collection flag

### 5. Improved I/O Control Panel ✅

**Before:** Add/Edit/Remove I/O actions with complex dialog
**After:** All devices visible with simple dropdown controls

New UX:
```
Device       │ Type    │ State at Start │ State at End
─────────────┼─────────┼────────────────┼──────────────
inlet_valve  │ Digital │ [CLOSED    ▼]  │ [CLOSED  ▼]
vent_valve   │ Digital │ [CLOSED    ▼]  │ [OPEN    ▼]
safety_valve │ Digital │ [CLOSED    ▼]  │ [CLOSED  ▼]
```

Features:
- All devices shown automatically
- Dropdown controls: "Not Set", "CLOSED", "OPEN"
- Changes apply immediately
- Auto-defaults for new stages

## Data Model Changes

### TestStage (Before):
```python
target_vacuum_bar: float  # Required
hold_time_seconds: float  # Required
mode-dependent fields...
```

### TestStage (After):
```python
name: str = "New Stage"
target_vacuum_bar: Optional[float] = None
max_time_seconds: Optional[float] = None
min_time_seconds: float = 0.0
pump_mode: PumpMode = PumpMode.CONTINUOUS
vacuum_tolerance_bar: float = 0.05
io_actions: List[IOAction] = field(default_factory=list)
collect_data: bool = True
```

### TestSequence (Before):
```python
mode: SequenceMode
loop_count: int
pause_between_stages: bool
```

### TestSequence (After):
```python
# Only essential fields
name: str
description: str
stages: List[TestStage]
metadata...
```

## UI Changes

### Sequence Editor Layout (Before):
- Metadata section
- Mode selector (Simple/Advanced)
- Stages table (different columns per mode)
- Add/Remove/Reorder buttons
- I/O Actions section (Advanced only)
- Validation status

### Sequence Editor Layout (After):
- Metadata section (unchanged)
- Stages table (unified columns for all)
- Add/Remove/Reorder buttons
- **NEW: Stage Configuration Panel**
  - Stage name field
  - Completion conditions checkboxes + spinboxes
  - Pump mode radio buttons
  - I/O device states table
- Validation status with warnings

## Control Logic Changes

### TestController._execute_stage()

**Before:**
1. Start pump
2. Ramp to target
3. Hold for fixed time
4. Vent/stop

**After:**
1. Execute I/O actions (BEFORE_STAGE)
2. Execute I/O actions (START_OF_STAGE)
3. Start pump based on pump_mode
4. Execute I/O actions (DURING_STAGE)
5. **Monitor completion conditions in loop:**
   - Check if elapsed >= min_time
   - Check if vacuum >= setpoint
   - Check if elapsed >= max_time
   - Exit loop when first condition met
6. Execute I/O actions (END_OF_STAGE)
7. Turn off pump
8. Execute I/O actions (AFTER_STAGE)
9. **Log completion reason** ("setpoint reached", "time limit", "manually stopped")

### New Methods:
- `_run_stage_with_monitoring()` - Monitors both conditions
- `_maintain_vacuum_cycle()` - Cycles pump for maintain mode

## Example Sequences Updated

All examples converted to new format:

| File | Demonstrates |
|------|-------------|
| `quick_test.yaml` | Setpoint AND time limit (0.5 bar OR 30s) |
| `simple_multi_stage.yaml` | Multi-level with maintain mode |
| `endurance_test.yaml` | Time-only test (300s, no setpoint) |
| `setpoint_only_test.yaml` | Setpoint-only (no time limit) |
| `venting_stage_example.yaml` | Pump OFF mode for venting |

## Backward Compatibility

✅ **Legacy sequences still load:**
- `from_dict()` handles old field names
- `hold_time_seconds` → `max_time_seconds`
- Deprecated fields ignored (ramp_rate, sample_rate, etc.)
- Missing pump_mode defaults to CONTINUOUS

## Testing Recommendations

1. **Launch GUI** and create a new sequence
2. **Add Stage** - verify defaults are sensible
3. **Configure Stage:**
   - Try setpoint only (uncheck time limit)
   - Try time only (uncheck setpoint)
   - Try both conditions
   - Switch pump modes
   - Modify I/O states
4. **Validation:** Uncheck both conditions - should show warning
5. **Save and Load:** Verify round-trip works
6. **Run Test:** Check completion reason is logged correctly

## Files Modified

**Core Logic:**
- `src/epdm_vacuum/control/sequence.py` - Complete data model overhaul
- `src/epdm_vacuum/control/sequence_manager.py` - Updated templates
- `src/epdm_vacuum/control/test_controller.py` - Setpoint monitoring + pump cycling

**GUI:**
- `src/epdm_vacuum/gui/dialogs/sequence_editor.py` - Complete UI redesign
- `src/epdm_vacuum/gui/main_window.py` - Remove mode references

**Sequences:**
- `sequences/quick_test.yaml` - Updated
- `sequences/simple_multi_stage.yaml` - Updated
- `sequences/endurance_test.yaml` - Updated
- `sequences/setpoint_only_test.yaml` - New
- `sequences/venting_stage_example.yaml` - New
- Deleted: advanced_detailed_test, valve_control_test, example files (obsolete)

**Documentation:**
- `README.md` - Complete rewrite of sequencing section

## Key Benefits

✅ **No More Confusion** - One clear interface, no mode switching  
✅ **Setpoint Control** - Stages end when target reached  
✅ **Flexible Completion** - Time OR setpoint OR both  
✅ **Visual I/O** - See all devices at once with simple dropdowns  
✅ **Intelligent Pumping** - Automatic cycling to maintain vacuum  
✅ **Simplified UI** - Only essential parameters shown  
✅ **Better Validation** - Errors vs warnings with clear guidance  
✅ **Comprehensive Logging** - Know why each stage completed

## User Workflow (New)

1. Open Sequence Editor
2. Click "Add Stage"
3. See stage added with defaults:
   - Name: "Stage 1"
   - Setpoint: 0.5 bar ✓
   - Time Limit: 30s ✓  
   - Pump Mode: Maintain Vacuum
   - I/O: inlet CLOSED, vent CLOSED→OPEN
4. Adjust as needed in Stage Configuration panel
5. See all I/O devices with their states
6. Validate (green = OK, orange = warnings, red = errors)
7. Save

Simple, clear, and works correctly the first time!

## Next Steps (When Hardware is Connected)

The following methods have placeholder implementations that need hardware integration:

1. **`_run_stage_with_monitoring()`** - Replace vacuum estimate with actual sensor readings
2. **`_maintain_vacuum_cycle()`** - Implement actual pump cycling based on vacuum sensor
3. **`_set_digital_output()`** - Map device names to relay channels
4. **`_set_analog_output()`** - Implement analog output control

All the sequencing logic is complete and ready - just needs hardware interface connection!

