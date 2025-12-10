"""
API Routes - FastAPI REST API and WebSocket Endpoints

Provides HTTP endpoints for remote monitoring and control,
plus WebSocket for real-time data streaming.
"""

from typing import Dict, Any, Optional, List
import logging
import asyncio
import json
from pathlib import Path
from datetime import datetime
import os

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from .hardware_manager import get_hardware_manager
from .websocket import (
    connection_manager,
    sensor_broadcaster,
    event_broadcaster,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


# === Pydantic Models ===

class APIResponse(BaseModel):
    """Standard API response format."""
    success: bool
    message: str = ""
    data: Optional[Dict[str, Any]] = None


class TestStartRequest(BaseModel):
    """Request body for starting a test."""
    sequence_name: str
    metadata: Optional[Dict[str, Any]] = None


class SequenceCreateRequest(BaseModel):
    """Request body for creating/updating a sequence."""
    name: str
    description: str = ""
    cycles: int = 1
    stages: List[Dict[str, Any]]


# === Root Endpoint ===

@router.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "EPDM Vacuum Fixture API",
        "version": "2.0.0",
        "description": "Web API for vacuum seal testing system",
        "endpoints": {
            "status": "/api/status",
            "sensors": "/api/sensors",
            "websocket": "/api/ws",
            "test": {
                "start": "POST /api/test/start",
                "stop": "POST /api/test/stop",
                "status": "GET /api/test/status",
            },
            "control": {
                "pump_on": "POST /api/pump/on",
                "pump_off": "POST /api/pump/off",
                "valve": "POST /api/valve/{name}/{action}",
                "tare": "POST /api/tare",
            },
            "sequences": {
                "list": "GET /api/sequences",
                "get": "GET /api/sequences/{name}",
                "create": "POST /api/sequences",
            }
        }
    }


# === System Status ===

@router.get("/api/status")
async def get_status():
    """Get system status."""
    try:
        hw = get_hardware_manager()
        status = hw.get_status()
        
        return APIResponse(
            success=True,
            message="System status retrieved",
            data={
                **status,
                "websocket_connections": connection_manager.connection_count,
            }
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Sensor Data ===

@router.get("/api/sensors")
async def get_sensors():
    """Get current sensor readings."""
    try:
        hw = get_hardware_manager()
        data = hw.get_sensor_data()
        
        return APIResponse(
            success=True,
            message="Sensor data retrieved",
            data=data
        )
    except Exception as e:
        logger.error(f"Error reading sensors: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/io/states")
async def get_io_states():
    """Get current IO device states."""
    try:
        hw = get_hardware_manager()
        states = hw.get_io_states()
        
        return APIResponse(
            success=True,
            message="IO states retrieved",
            data=states
        )
    except Exception as e:
        logger.error(f"Error getting IO states: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Hardware Control ===

@router.post("/api/pump/on")
async def pump_on():
    """Turn vacuum pump on."""
    try:
        hw = get_hardware_manager()
        success, message = hw.set_pump(True)
        
        if success:
            # Broadcast IO change
            await event_broadcaster.broadcast_io_change("vacuum_pump", True)
        
        return APIResponse(
            success=success,
            message=message,
            data={"pump_on": success}
        )
    except Exception as e:
        logger.error(f"Error turning pump on: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/pump/off")
async def pump_off():
    """Turn vacuum pump off."""
    try:
        hw = get_hardware_manager()
        success, message = hw.set_pump(False)
        
        if success:
            await event_broadcaster.broadcast_io_change("vacuum_pump", False)
        
        return APIResponse(
            success=success,
            message=message,
            data={"pump_on": False}
        )
    except Exception as e:
        logger.error(f"Error turning pump off: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/valve/{valve_name}/{action}")
async def control_valve(valve_name: str, action: str):
    """
    Control a valve.
    
    Args:
        valve_name: Name of valve (vacuum_valve, vent_valve)
        action: open or close
    
    Note: Valves are NORMALLY-OPEN type:
        - action=close → relay ON → valve physically closed
        - action=open → relay OFF → valve physically open
    """
    if valve_name not in ["vacuum_valve", "vent_valve"]:
        raise HTTPException(status_code=400, detail=f"Unknown valve: {valve_name}")
    
    if action not in ["open", "close"]:
        raise HTTPException(status_code=400, detail=f"Invalid action: {action}. Use 'open' or 'close'")
    
    try:
        hw = get_hardware_manager()
        # For NO valves: close = relay ON (True), open = relay OFF (False)
        relay_state = (action == "close")
        success, message = hw.set_valve(valve_name, relay_state)
        
        if success:
            # Broadcast IO change (using desired state, not relay state)
            await event_broadcaster.broadcast_io_change(valve_name, action == "open")
        
        return APIResponse(
            success=success,
            message=message,
            data={"valve": valve_name, "state": action}
        )
    except Exception as e:
        logger.error(f"Error controlling valve: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/tare")
async def tare():
    """Tare load cells."""
    try:
        hw = get_hardware_manager()
        success, message = hw.tare_load_cells()
        
        return APIResponse(
            success=success,
            message=message
        )
    except Exception as e:
        logger.error(f"Error taring load cells: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Test Control ===

@router.post("/api/test/start")
async def start_test(request: TestStartRequest):
    """Start a test with the specified sequence."""
    try:
        hw = get_hardware_manager()
        success, message = hw.start_test(request.sequence_name, request.metadata)
        
        if success:
            await event_broadcaster.broadcast_status(f"Test started: {request.sequence_name}")
        
        return APIResponse(
            success=success,
            message=message,
            data={"sequence": request.sequence_name}
        )
    except Exception as e:
        logger.error(f"Error starting test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/test/stop")
async def stop_test():
    """Stop the current test."""
    try:
        hw = get_hardware_manager()
        success, message = hw.stop_test()
        
        if success:
            await event_broadcaster.broadcast_status("Test stopped")
        
        return APIResponse(
            success=success,
            message=message
        )
    except Exception as e:
        logger.error(f"Error stopping test: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/test/status")
async def get_test_status():
    """Get current test status."""
    try:
        hw = get_hardware_manager()
        status = hw.get_test_status()
        
        return APIResponse(
            success=True,
            message="Test status retrieved",
            data=status
        )
    except Exception as e:
        logger.error(f"Error getting test status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Sequence Management ===

@router.get("/api/sequences")
async def list_sequences():
    """Get list of available test sequences."""
    try:
        hw = get_hardware_manager()
        sequences = hw.get_sequences()
        
        return APIResponse(
            success=True,
            message=f"Found {len(sequences)} sequences",
            data={"sequences": sequences}
        )
    except Exception as e:
        logger.error(f"Error listing sequences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/sequences/{name}")
async def get_sequence(name: str):
    """Get a specific sequence by name."""
    try:
        hw = get_hardware_manager()
        sequence = hw.get_sequence(name)
        
        if sequence is None:
            raise HTTPException(status_code=404, detail=f"Sequence '{name}' not found")
        
        return APIResponse(
            success=True,
            message=f"Sequence '{name}' retrieved",
            data=sequence
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting sequence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/sequences")
async def create_sequence(request: SequenceCreateRequest):
    """Create or update a sequence."""
    try:
        hw = get_hardware_manager()
        
        if not hw.sequence_manager:
            raise HTTPException(status_code=500, detail="Sequence manager not initialized")
        
        from ..control.sequence import TestSequence, TestStage, IOAction, IOActionTiming, IOActionType, PumpMode
        
        # Build stages from request
        stages = []
        for stage_data in request.stages:
            io_actions = []
            for action_data in stage_data.get("io_actions", []):
                io_actions.append(IOAction(
                    device_name=action_data["device_name"],
                    action_type=IOActionType(action_data.get("action_type", "digital_output")),
                    value=action_data["value"],
                    timing=IOActionTiming(action_data.get("timing", "start_of_stage")),
                    delay_seconds=action_data.get("delay_seconds", 0.0),
                    duration_seconds=action_data.get("duration_seconds"),
                    description=action_data.get("description", ""),
                ))
            
            stages.append(TestStage(
                name=stage_data["name"],
                target_vacuum_bar=stage_data.get("target_vacuum_bar"),
                max_time_seconds=stage_data.get("max_time_seconds"),
                min_time_seconds=stage_data.get("min_time_seconds", 0.0),
                pump_mode=PumpMode(stage_data.get("pump_mode", "continuous")),
                vacuum_tolerance_bar=stage_data.get("vacuum_tolerance_bar", 0.05),
                io_actions=io_actions,
                collect_data=stage_data.get("collect_data", True),
            ))
        
        sequence = TestSequence(
            name=request.name,
            description=request.description,
            cycles=request.cycles,
            stages=stages,
        )
        
        # Save sequence
        success = hw.sequence_manager.save_sequence(sequence)
        
        if success:
            return APIResponse(
                success=True,
                message=f"Sequence '{request.name}' saved",
                data={"name": request.name}
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save sequence")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating sequence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === Test Data Management ===

def get_data_directory() -> Path:
    """Get the data directory path."""
    # Default data directory relative to project root
    data_dir = Path(__file__).parent.parent.parent.parent / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class TestDataFile(BaseModel):
    """Information about a test data file."""
    filename: str
    file_type: str  # 'csv' or 'json'
    size_bytes: int
    size_formatted: str
    modified_time: str
    modified_timestamp: float
    test_name: Optional[str] = None
    test_id: Optional[str] = None
    operator: Optional[str] = None
    sequence_name: Optional[str] = None
    has_metadata: bool = False


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.2f} MB"


def extract_metadata_from_json(json_path: Path) -> Dict[str, Any]:
    """Extract metadata fields from a JSON file."""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        # Extract useful fields - handle various metadata structures
        result = {}
        
        # Check for direct fields
        if 'test_name' in data:
            result['test_name'] = data['test_name']
        if 'test_id' in data:
            result['test_id'] = data['test_id']
        if 'operator' in data:
            result['operator'] = data['operator']
        if 'sequence_name' in data:
            result['sequence_name'] = data['sequence_name']
        
        # Check for nested metadata dict (old format)
        metadata = data.get('metadata', {})
        if isinstance(metadata, dict):
            result['test_name'] = result.get('test_name') or metadata.get('test_name')
            result['test_id'] = result.get('test_id') or metadata.get('test_id')
            result['operator'] = result.get('operator') or metadata.get('operator')
            result['sequence_name'] = result.get('sequence_name') or metadata.get('sequence_name')
        
        return result
    except Exception as e:
        logger.debug(f"Could not extract metadata from {json_path}: {e}")
        return {}


@router.get("/api/data")
async def list_test_data():
    """
    List all test data files in the data directory.
    
    Returns CSV files with their associated metadata from JSON files.
    """
    try:
        data_dir = get_data_directory()
        files: List[TestDataFile] = []
        
        # Find all CSV and standalone JSON files
        csv_files = list(data_dir.glob("*.csv"))
        json_files = list(data_dir.glob("*.json"))
        
        # Create a set of JSON basenames for quick lookup
        json_basenames = {jf.stem for jf in json_files}
        
        for csv_file in csv_files:
            stat = csv_file.stat()
            
            # Look for matching JSON metadata file
            json_file = csv_file.with_suffix('.json')
            metadata = {}
            has_metadata = False
            
            if json_file.exists():
                metadata = extract_metadata_from_json(json_file)
                has_metadata = True
            
            files.append(TestDataFile(
                filename=csv_file.name,
                file_type='csv',
                size_bytes=stat.st_size,
                size_formatted=format_file_size(stat.st_size),
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                modified_timestamp=stat.st_mtime,
                test_name=metadata.get('test_name'),
                test_id=metadata.get('test_id'),
                operator=metadata.get('operator'),
                sequence_name=metadata.get('sequence_name'),
                has_metadata=has_metadata,
            ))
        
        # Also include standalone JSON files (metadata files without CSV)
        for json_file in json_files:
            # Skip if there's a matching CSV file (already included above)
            csv_companion = json_file.with_suffix('.csv')
            if csv_companion.exists():
                continue
            
            stat = json_file.stat()
            metadata = extract_metadata_from_json(json_file)
            
            files.append(TestDataFile(
                filename=json_file.name,
                file_type='json',
                size_bytes=stat.st_size,
                size_formatted=format_file_size(stat.st_size),
                modified_time=datetime.fromtimestamp(stat.st_mtime).isoformat(),
                modified_timestamp=stat.st_mtime,
                test_name=metadata.get('test_name'),
                test_id=metadata.get('test_id'),
                operator=metadata.get('operator'),
                sequence_name=metadata.get('sequence_name'),
                has_metadata=True,
            ))
        
        # Sort by modification time, newest first
        files.sort(key=lambda f: f.modified_timestamp, reverse=True)
        
        return APIResponse(
            success=True,
            message=f"Found {len(files)} test data files",
            data={"files": [f.model_dump() for f in files]}
        )
        
    except Exception as e:
        logger.error(f"Error listing test data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/data/{filename}")
async def download_test_data(filename: str):
    """
    Download a specific test data file.
    
    Args:
        filename: Name of the file to download (CSV or JSON)
    """
    try:
        # Sanitize filename to prevent path traversal
        safe_filename = Path(filename).name
        if safe_filename != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        data_dir = get_data_directory()
        file_path = data_dir / safe_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Determine content type
        if file_path.suffix.lower() == '.csv':
            media_type = 'text/csv'
        elif file_path.suffix.lower() == '.json':
            media_type = 'application/json'
        else:
            media_type = 'application/octet-stream'
        
        return FileResponse(
            path=file_path,
            filename=safe_filename,
            media_type=media_type,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error downloading file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/data/{filename}/metadata")
async def get_test_metadata(filename: str):
    """
    Get metadata for a test data file.
    
    For CSV files, returns content of the associated JSON metadata file.
    For JSON files, returns the file content directly.
    """
    try:
        # Sanitize filename
        safe_filename = Path(filename).name
        if safe_filename != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        data_dir = get_data_directory()
        
        # If requesting metadata for CSV, look for JSON companion
        if safe_filename.endswith('.csv'):
            json_filename = safe_filename.replace('.csv', '.json')
        else:
            json_filename = safe_filename
        
        json_path = data_dir / json_filename
        
        if not json_path.exists():
            raise HTTPException(status_code=404, detail=f"Metadata not found for: {filename}")
        
        with open(json_path, 'r') as f:
            metadata = json.load(f)
        
        return APIResponse(
            success=True,
            message="Metadata retrieved",
            data=metadata
        )
        
    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in metadata file: {e}")
    except Exception as e:
        logger.error(f"Error reading metadata: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api/data/{filename}")
async def delete_test_data(filename: str):
    """
    Delete a test data file and its associated metadata.
    
    Args:
        filename: Name of the file to delete
    """
    try:
        # Sanitize filename
        safe_filename = Path(filename).name
        if safe_filename != filename:
            raise HTTPException(status_code=400, detail="Invalid filename")
        
        data_dir = get_data_directory()
        file_path = data_dir / safe_filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        deleted_files = []
        
        # Delete the main file
        file_path.unlink()
        deleted_files.append(safe_filename)
        
        # If CSV, also delete associated JSON metadata
        if safe_filename.endswith('.csv'):
            json_path = file_path.with_suffix('.json')
            if json_path.exists():
                json_path.unlink()
                deleted_files.append(json_path.name)
        
        logger.info(f"Deleted test data files: {deleted_files}")
        
        return APIResponse(
            success=True,
            message=f"Deleted {len(deleted_files)} file(s)",
            data={"deleted": deleted_files}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# === WebSocket Endpoint ===

@router.websocket("/api/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time data streaming.
    
    Clients receive:
    - sensor_data: Real-time sensor readings (10Hz)
    - status: Test status messages
    - stage_change: Test stage transitions
    - progress: Stage progress updates
    - io_change: IO device state changes
    - test_complete: Test completion notification
    - error: Error messages
    """
    await connection_manager.connect(websocket)
    
    # Send initial status
    hw = get_hardware_manager()
    await connection_manager.send_personal(websocket, {
        "type": "connected",
        "data": hw.get_status()
    })
    
    try:
        while True:
            # Wait for messages from client (ping/pong, commands, etc.)
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                
                # Handle client messages if needed
                import json
                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await connection_manager.send_personal(websocket, {"type": "pong"})
                except json.JSONDecodeError:
                    pass
                    
            except asyncio.TimeoutError:
                # Send heartbeat
                await connection_manager.send_personal(websocket, {"type": "heartbeat"})
                
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection_manager.disconnect(websocket)
