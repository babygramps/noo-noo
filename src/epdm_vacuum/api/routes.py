"""
API Routes - Flask REST API Endpoints

Provides HTTP endpoints for remote monitoring and control.
"""

from typing import Dict, Any
import logging
import time

from flask import Flask, jsonify, request
from flask_cors import CORS

from .models import APIResponse, format_sensor_data_for_api

logger = logging.getLogger(__name__)


# Global reference to hardware interfaces (set by app_main)
_hardware_manager = None


def set_hardware_manager(manager):
    """
    Set the hardware manager reference for the API.
    
    Args:
        manager: Hardware manager instance with access to all interfaces
    """
    global _hardware_manager
    _hardware_manager = manager
    logger.info("Hardware manager set for API")


def create_app(debug: bool = False) -> Flask:
    """
    Create and configure Flask application.
    
    Args:
        debug: Enable debug mode
    
    Returns:
        Flask: Configured Flask app
    """
    app = Flask(__name__)
    app.config["DEBUG"] = debug
    
    # Enable CORS for browser access
    CORS(app)
    
    # Register routes
    register_routes(app)
    
    logger.info("Flask app created")
    return app


def register_routes(app: Flask) -> None:
    """
    Register all API routes.
    
    Args:
        app: Flask application
    """
    
    @app.route("/", methods=["GET"])
    def index():
        """Root endpoint - API information."""
        return jsonify(
            APIResponse.success(
                data={
                    "name": "EPDM Vacuum Fixture API",
                    "version": "1.1.0",
                    "endpoints": [
                        "/",
                        "/api/status",
                        "/api/sensors",
                        "/api/sensors/latest",
                        "/api/test/start",
                        "/api/test/stop",
                        "/api/pump/on",
                        "/api/pump/off",
                        "/api/safety",
                    ],
                },
                message="EPDM Vacuum Fixture API",
            )
        )
    
    @app.route("/api/status", methods=["GET"])
    def get_status():
        """Get system status."""
        try:
            # TODO: Get actual status from hardware manager
            status = {
                "system": "operational",
                "hardware_connected": False,
                "test_running": False,
                "pump_on": False,
                "uptime": time.time(),
            }
            
            return jsonify(APIResponse.success(data=status))
            
        except Exception as e:
            logger.error(f"Error getting status: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/sensors", methods=["GET"])
    def get_sensors():
        """Get all sensor readings."""
        try:
            # TODO: Get actual sensor data from hardware manager
            # if _hardware_manager:
            #     raw_data = _hardware_manager.read_all_sensors()
            #     formatted_data = format_sensor_data_for_api(raw_data)
            
            # Mock data for development
            formatted_data = {
                "timestamp": time.time(),
                "vacuum": {"bar": 0.0, "psi": 0.0},
                "pressure": {"psi": 14.7, "voltage": 5.0},
                "force": {
                    "total_kg": 0.0,
                    "load_cells": [0.0, 0.0, 0.0, 0.0],
                },
            }
            
            return jsonify(APIResponse.success(data=formatted_data))
            
        except Exception as e:
            logger.error(f"Error reading sensors: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/sensors/latest", methods=["GET"])
    def get_latest_sensor():
        """Get latest sensor reading."""
        return get_sensors()
    
    @app.route("/api/test/start", methods=["POST"])
    def start_test():
        """Start a test sequence."""
        try:
            # Get test configuration from request body
            config = request.get_json() or {}
            
            logger.info(f"Start test requested with config: {config}")
            
            # TODO: Implement test start via hardware manager
            # if _hardware_manager:
            #     success = _hardware_manager.start_test(config)
            
            logger.warning("TODO: Test start not implemented")
            
            return jsonify(
                APIResponse.success(
                    data={"test_started": True, "config": config},
                    message="Test started (placeholder)",
                )
            )
            
        except Exception as e:
            logger.error(f"Error starting test: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/test/stop", methods=["POST"])
    def stop_test():
        """Stop the current test."""
        try:
            logger.info("Stop test requested")
            
            # TODO: Implement test stop via hardware manager
            # if _hardware_manager:
            #     _hardware_manager.stop_test()
            
            logger.warning("TODO: Test stop not implemented")
            
            return jsonify(
                APIResponse.success(
                    data={"test_stopped": True},
                    message="Test stopped (placeholder)",
                )
            )
            
        except Exception as e:
            logger.error(f"Error stopping test: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/pump/on", methods=["POST"])
    def pump_on():
        """Turn vacuum pump on."""
        try:
            logger.info("Pump ON requested via API")
            
            # TODO: Implement pump control via hardware manager
            # if _hardware_manager:
            #     _hardware_manager.set_pump(True)
            
            logger.warning("TODO: Pump control not implemented")
            
            return jsonify(
                APIResponse.success(
                    data={"pump_on": True},
                    message="Pump turned ON (placeholder)",
                )
            )
            
        except Exception as e:
            logger.error(f"Error turning pump on: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/pump/off", methods=["POST"])
    def pump_off():
        """Turn vacuum pump off."""
        try:
            logger.info("Pump OFF requested via API")
            
            # TODO: Implement pump control via hardware manager
            # if _hardware_manager:
            #     _hardware_manager.set_pump(False)
            
            logger.warning("TODO: Pump control not implemented")
            
            return jsonify(
                APIResponse.success(
                    data={"pump_on": False},
                    message="Pump turned OFF (placeholder)",
                )
            )
            
        except Exception as e:
            logger.error(f"Error turning pump off: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.route("/api/safety", methods=["GET"])
    def get_safety_status():
        """Get safety system status."""
        try:
            # TODO: Get actual safety status from hardware manager
            # if _hardware_manager:
            #     safety_data = _hardware_manager.get_safety_status()
            
            # Mock data for development
            safety_data = {
                "state": "normal",
                "safe_to_operate": True,
                "limits": {
                    "max_vacuum_bar": 1.0,
                    "max_force_kg": 800.0,
                },
                "violations": [],
            }
            
            return jsonify(APIResponse.success(data=safety_data))
            
        except Exception as e:
            logger.error(f"Error getting safety status: {e}", exc_info=True)
            return jsonify(APIResponse.error(str(e))), 500
    
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return jsonify(APIResponse.error("Endpoint not found", code=404)), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return jsonify(APIResponse.error("Internal server error", code=500)), 500
    
    logger.info("API routes registered")

