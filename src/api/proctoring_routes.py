"""
Internal proctoring API.

These routes drive the on-host session lifecycle (camera capture, reports,
statistics). They are protected by the same Bearer-token auth as the
Moodle-compatible routes.
"""
import logging
import time
from functools import wraps

import cv2
from flask import Blueprint, Response, jsonify, request

from src.api.auth import require_api_key

logger = logging.getLogger(__name__)

proctoring_api = Blueprint("proctoring", __name__, url_prefix="/api/proctoring")

proctoring_system = None


def set_proctoring_system(system):
    """Set the global proctoring system reference."""
    global proctoring_system
    proctoring_system = system


def require_session(fn):
    """Reject the request if no proctoring session is active."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if proctoring_system is None or proctoring_system.current_session is None:
            return jsonify({"error": "No active session"}), 400
        return fn(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Health / system
# ---------------------------------------------------------------------------
@proctoring_api.route("/health", methods=["GET"])
def health():
    """Internal health check.
    ---
    tags:
      - Internal
    responses:
      200:
        description: Service is healthy
    """
    gpu_available = False
    gpu_device = "cpu"
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_device = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    return jsonify({
        "status": "healthy",
        "service": "proctoring-ai-backend",
        "version": "2.0.0",
        "timestamp": time.time(),
        "gpu_available": gpu_available,
        "gpu_device": gpu_device,
    }), 200


@proctoring_api.route("/system-info", methods=["GET"])
@require_api_key
def system_info():
    """Return runtime system information.
    ---
    tags:
      - Internal
    security:
      - BearerAuth: []
    responses:
      200:
        description: System info payload
      401:
        description: Unauthorized
    """
    if proctoring_system is None:
        return jsonify({"error": "System not initialized"}), 500
    try:
        return jsonify(proctoring_system.get_system_info()), 200
    except Exception as exc:
        logger.error("Error getting system info: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@proctoring_api.route("/session/start", methods=["POST"])
@require_api_key
def start_session():
    """Start a new proctoring session.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [session_id, user_id]
            properties:
              session_id:
                type: string
              user_id:
                type: string
    responses:
      200:
        description: Session started
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id")
    user_id = data.get("user_id")

    if not session_id or not user_id:
        return jsonify({"error": "Missing session_id or user_id"}), 400

    try:
        if not proctoring_system.start_session(session_id, user_id):
            return jsonify({"error": "Failed to start session"}), 400
        return jsonify({
            "message": "Session started successfully",
            "session_id": session_id,
            "user_id": user_id,
            "timestamp": time.time(),
        }), 200
    except Exception as exc:
        logger.error("Error starting session: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/session/stop", methods=["POST"])
@require_api_key
@require_session
def stop_session():
    """Stop the current proctoring session.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session stopped
      400:
        description: No active session
      401:
        description: Unauthorized
    """
    try:
        result = proctoring_system.stop_session()
        if not result:
            return jsonify({"error": "Failed to stop session"}), 400
        return jsonify({
            "message": "Session stopped successfully",
            "summary": result.get("session_summary"),
            "reports": result.get("report_paths"),
        }), 200
    except Exception as exc:
        logger.error("Error stopping session: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/session/status", methods=["GET"])
@require_api_key
def session_status():
    """Get the status of the current session.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session status (may be empty if none active)
      401:
        description: Unauthorized
    """
    try:
        status = proctoring_system.get_session_status()
        return jsonify(status or {"message": "No active session"}), 200
    except Exception as exc:
        logger.error("Error getting session status: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/session/report", methods=["GET"])
@require_api_key
@require_session
def get_session_report():
    """Get the current session's report.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    responses:
      200:
        description: Session report
      400:
        description: No active session
      401:
        description: Unauthorized
    """
    try:
        return jsonify(proctoring_system.current_session.get_session_report()), 200
    except Exception as exc:
        logger.error("Error getting session report: %s", exc)
        return jsonify({"error": str(exc)}), 500


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------
@proctoring_api.route("/video/frame", methods=["GET"])
@require_api_key
@require_session
def get_current_frame():
    """Get the current webcam frame as JPEG.
    ---
    tags:
      - Video
    security:
      - BearerAuth: []
    produces:
      - image/jpeg
    responses:
      200:
        description: JPEG frame
      404:
        description: No frame available
    """
    try:
        frame = proctoring_system.get_current_frame()
        if frame is None:
            return jsonify({"error": "No frame available"}), 404
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return jsonify({"error": "Failed to encode frame"}), 500
        return Response(buffer.tobytes(), mimetype="image/jpeg")
    except Exception as exc:
        logger.error("Error getting frame: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/video/stream", methods=["GET"])
@require_api_key
@require_session
def video_stream():
    """Stream the live webcam feed as Motion JPEG.
    ---
    tags:
      - Video
    security:
      - BearerAuth: []
    responses:
      200:
        description: multipart/x-mixed-replace MJPEG stream
    """
    def generate():
        while proctoring_system.is_running and proctoring_system.current_session:
            frame = proctoring_system.get_current_frame()
            if frame is not None:
                ok, buffer = cv2.imencode(".jpg", frame)
                if ok:
                    chunk = buffer.tobytes()
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(chunk)).encode() + b"\r\n\r\n"
                        + chunk + b"\r\n"
                    )
            time.sleep(0.033)  # ~30 FPS

    return Response(generate(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ---------------------------------------------------------------------------
# Stats / configuration
# ---------------------------------------------------------------------------
@proctoring_api.route("/face-detection/stats", methods=["GET"])
@require_api_key
@require_session
def face_detection_stats():
    """Get face-detection statistics.
    ---
    tags:
      - Stats
    security:
      - BearerAuth: []
    responses:
      200:
        description: Statistics payload
    """
    try:
        return jsonify(proctoring_system.face_detector.get_detection_statistics()), 200
    except Exception as exc:
        logger.error("Error getting face detection stats: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/eye-tracking/stats", methods=["GET"])
@require_api_key
@require_session
def eye_tracking_stats():
    """Get eye-tracking statistics.
    ---
    tags:
      - Stats
    security:
      - BearerAuth: []
    responses:
      200:
        description: Statistics payload
    """
    try:
        return jsonify(proctoring_system.eye_tracker.get_statistics()), 200
    except Exception as exc:
        logger.error("Error getting eye tracking stats: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/warnings", methods=["GET"])
@require_api_key
@require_session
def get_warnings():
    """Get the latest session warnings.
    ---
    tags:
      - Session
    security:
      - BearerAuth: []
    parameters:
      - in: query
        name: limit
        schema: { type: integer, default: 50 }
    responses:
      200:
        description: Warnings list
    """
    try:
        limit = request.args.get("limit", 50, type=int)
        warnings = proctoring_system.current_session.warnings[-limit:]
        return jsonify({
            "total_warnings": len(proctoring_system.current_session.warnings),
            "warnings": warnings,
        }), 200
    except Exception as exc:
        logger.error("Error getting warnings: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/configuration", methods=["GET"])
@require_api_key
def get_configuration():
    """Get the non-sensitive runtime configuration.
    ---
    tags:
      - Internal
    security:
      - BearerAuth: []
    responses:
      200:
        description: Configuration snapshot
    """
    try:
        from config.settings import public_config
        return jsonify(public_config()), 200
    except Exception as exc:
        logger.error("Error getting configuration: %s", exc)
        return jsonify({"error": str(exc)}), 500


@proctoring_api.route("/configuration", methods=["PUT"])
@require_api_key
def update_configuration():
    """Update mutable proctoring configuration values at runtime.
    ---
    tags:
      - Internal
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              capture_interval:
                type: integer
              reverification_interval:
                type: integer
              max_faces_allowed:
                type: integer
    responses:
      200:
        description: Configuration updated
      400:
        description: Invalid request
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No configuration data provided"}), 400

    try:
        from config.settings import ProctoringConfig

        mutable = {
            "capture_interval": "CAPTURE_INTERVAL",
            "reverification_interval": "REVERIFICATION_INTERVAL",
            "max_faces_allowed": "MAX_FACES_ALLOWED",
        }
        updated = []
        for key, attr in mutable.items():
            if key in data:
                setattr(ProctoringConfig, attr, data[key])
                updated.append(key)

        return jsonify({
            "message": "Configuration updated successfully",
            "updated_fields": updated,
        }), 200
    except Exception as exc:
        logger.error("Error updating configuration: %s", exc)
        return jsonify({"error": str(exc)}), 500
