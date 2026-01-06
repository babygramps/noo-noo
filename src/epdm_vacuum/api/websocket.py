"""
WebSocket Manager - Real-time Data Streaming

Manages WebSocket connections for streaming sensor data and test events.
"""

from typing import Set, Dict, Any, Optional
import logging
import asyncio
import json
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts data to all connected clients.
    """
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def connect(self, websocket: WebSocket) -> None:
        """Accept a new WebSocket connection."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        json_message = json.dumps(message)
        
        # Collect disconnected clients
        disconnected = set()
        
        async with self._lock:
            for connection in self.active_connections:
                try:
                    await connection.send_text(json_message)
                except Exception as e:
                    logger.debug(f"Failed to send to client: {e}")
                    disconnected.add(connection)
        
        # Remove disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections -= disconnected
            logger.info(f"Removed {len(disconnected)} disconnected clients")
    
    async def send_personal(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
    
    @property
    def connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)


class SensorDataBroadcaster:
    """
    Broadcasts sensor data to all WebSocket clients at a specified rate.
    """
    
    def __init__(self, connection_manager: ConnectionManager, interval: float = 0.1):
        """
        Initialize the broadcaster.
        
        Args:
            connection_manager: WebSocket connection manager
            interval: Broadcast interval in seconds (default 0.1 = 10Hz)
        """
        self.manager = connection_manager
        self.interval = interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._hardware_manager = None
    
    def set_hardware_manager(self, hardware_manager) -> None:
        """Set the hardware manager for reading sensor data."""
        self._hardware_manager = hardware_manager
    
    async def start(self) -> None:
        """Start broadcasting sensor data."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._broadcast_loop())
        logger.info(f"Sensor broadcaster started at {1/self.interval:.0f}Hz")
    
    async def stop(self) -> None:
        """Stop broadcasting sensor data."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("Sensor broadcaster stopped")
    
    async def _broadcast_loop(self) -> None:
        """Main broadcast loop."""
        while self._running:
            try:
                # Only broadcast if there are connections
                if self.manager.connection_count > 0:
                    data = self._get_sensor_data()
                    await self.manager.broadcast({
                        "type": "sensor_data",
                        "data": data
                    })
                
                await asyncio.sleep(self.interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(1.0)  # Backoff on error
    
    def _get_sensor_data(self) -> Dict[str, Any]:
        """Get current sensor data from hardware manager."""
        if self._hardware_manager:
            return self._hardware_manager.get_sensor_data()
        
        # Mock data if no hardware manager
        return {
            "timestamp": datetime.now().timestamp(),
            "datetime": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "vacuum_bar": 0.0,
            "pressure_psi": 0.0,
            "gross_weight_kg": 0.0,
            "total_force_kg": 0.0,
            "load_cell_1_kg": 0.0,
            "load_cell_2_kg": 0.0,
            "load_cell_3_kg": 0.0,
            "load_cell_4_kg": 0.0,
            "test_running": False,
        }


class TestEventBroadcaster:
    """
    Broadcasts test execution events to WebSocket clients.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        self.manager = connection_manager
    
    async def broadcast_status(self, status: str) -> None:
        """Broadcast a status message."""
        await self.manager.broadcast({
            "type": "status",
            "message": status,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_stage_change(
        self,
        stage_index: int,
        stage_name: str,
        stages_per_cycle: int,
        current_cycle: int,
        total_cycles: int
    ) -> None:
        """Broadcast a stage change event."""
        await self.manager.broadcast({
            "type": "stage_change",
            "data": {
                "stage_index": stage_index,
                "stage_name": stage_name,
                "stages_per_cycle": stages_per_cycle,
                "current_cycle": current_cycle,
                "total_cycles": total_cycles,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_progress(self, progress: float, status: str) -> None:
        """Broadcast progress update."""
        await self.manager.broadcast({
            "type": "progress",
            "data": {
                "progress": progress,
                "status": status,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_io_change(self, device_name: str, state: bool) -> None:
        """Broadcast IO state change."""
        await self.manager.broadcast({
            "type": "io_change",
            "data": {
                "device": device_name,
                "state": state,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_test_complete(self) -> None:
        """Broadcast test completion."""
        await self.manager.broadcast({
            "type": "test_complete",
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_error(self, error: str) -> None:
        """Broadcast an error message."""
        await self.manager.broadcast({
            "type": "error",
            "message": error,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_upload_complete(self, filename: str, drive_url: str) -> None:
        """Broadcast successful Google Drive upload."""
        await self.manager.broadcast({
            "type": "upload_complete",
            "data": {
                "filename": filename,
                "drive_url": drive_url,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_upload_failed(self, filename: str, error: str, will_retry: bool) -> None:
        """Broadcast failed Google Drive upload."""
        await self.manager.broadcast({
            "type": "upload_failed",
            "data": {
                "filename": filename,
                "error": error,
                "will_retry": will_retry,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast_joke(self, line1: str, line2: str) -> None:
        """Broadcast a joke for display on web interface ticker."""
        await self.manager.broadcast({
            "type": "joke",
            "data": {
                "line1": line1,
                "line2": line2,
            },
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast(self, message: dict) -> None:
        """Broadcast an arbitrary message."""
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        await self.manager.broadcast(message)


# Global instances
connection_manager = ConnectionManager()
sensor_broadcaster = SensorDataBroadcaster(connection_manager)
event_broadcaster = TestEventBroadcaster(connection_manager)


