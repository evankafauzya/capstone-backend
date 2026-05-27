"""
Internal proctoring API (FastAPI).

These routes drive the on-host session lifecycle (camera capture, reports,
statistics). They are protected by the same Bearer-token auth as the
Moodle-compatible routes, except for the lightweight health probe.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

import cv2
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse, Response, StreamingResponse

from src.api.auth import require_api_key
from src.api.schemas import (
    StartSessionRequest,
    StartSessionResponse,
    UpdateConfigurationRequest,
)

logger = logging.getLogger(__name__)

# Two routers: one bare (for the public health probe), one gated by Bearer
# auth. The prefix lives on the outer ``proctoring_api`` only; nesting an
# inner router with the same prefix would concatenate them.
proctoring_api = APIRouter(prefix="/api/proctoring", tags=["Proctoring"])
_secure = APIRouter(
    tags=["Proctoring"],
    dependencies=[Depends(require_api_key)],
)

proctoring_system = None


def set_proctoring_system(system):
    """Set the global proctoring system reference."""
    global proctoring_system
    proctoring_system = system


def _err(message: str, code: int, **extra) -> JSONResponse:
    body: Dict[str, Any] = {"error": message}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=code, content=body)


def _require_session() -> JSONResponse | None:
    """Return an error response if no proctoring session is active, else None."""
    if proctoring_system is None or proctoring_system.current_session is None:
        return _err("No active session", 400)
    return None


# ---------------------------------------------------------------------------
# Health / system
# ---------------------------------------------------------------------------
@proctoring_api.get("/health", tags=["Internal"], summary="Internal health check")
def health():
    gpu_available = False
    gpu_device = "cpu"
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        if gpu_available:
            gpu_device = torch.cuda.get_device_name(0)
    except ImportError:
        pass

    return {
        "status": "healthy",
        "service": "proctoring-ai-backend",
        "version": "2.0.0",
        "timestamp": time.time(),
        "gpu_available": gpu_available,
        "gpu_device": gpu_device,
    }


@_secure.get("/system-info", tags=["Internal"], summary="Runtime system information")
def system_info():
    if proctoring_system is None:
        return _err("System not initialized", 500)
    try:
        return proctoring_system.get_system_info()
    except Exception as exc:
        logger.error("Error getting system info: %s", exc)
        return _err(str(exc), 500)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------
@_secure.post("/session/start", tags=["Session"], summary="Start a new proctoring session")
def start_session(body: StartSessionRequest):
    try:
        if not proctoring_system.start_session(body.session_id, body.user_id):
            return _err("Failed to start session", 400)
        return StartSessionResponse(
            message="Session started successfully",
            session_id=body.session_id,
            user_id=body.user_id,
            timestamp=time.time(),
        )
    except Exception as exc:
        logger.error("Error starting session: %s", exc)
        return _err(str(exc), 500)


@_secure.post("/session/stop", tags=["Session"], summary="Stop the current session")
def stop_session():
    err = _require_session()
    if err is not None:
        return err
    try:
        result = proctoring_system.stop_session()
        if not result:
            return _err("Failed to stop session", 400)
        return {
            "message": "Session stopped successfully",
            "summary": result.get("session_summary"),
            "reports": result.get("report_paths"),
        }
    except Exception as exc:
        logger.error("Error stopping session: %s", exc)
        return _err(str(exc), 500)


@_secure.get("/session/status", tags=["Session"], summary="Current session status")
def session_status():
    try:
        status_ = proctoring_system.get_session_status()
        return status_ or {"message": "No active session"}
    except Exception as exc:
        logger.error("Error getting session status: %s", exc)
        return _err(str(exc), 500)


@_secure.get("/session/report", tags=["Session"], summary="Current session report")
def get_session_report():
    err = _require_session()
    if err is not None:
        return err
    try:
        return proctoring_system.current_session.get_session_report()
    except Exception as exc:
        logger.error("Error getting session report: %s", exc)
        return _err(str(exc), 500)


# ---------------------------------------------------------------------------
# Video
# ---------------------------------------------------------------------------
@_secure.get("/video/frame", tags=["Video"], summary="Get the latest webcam frame as JPEG")
def get_current_frame():
    err = _require_session()
    if err is not None:
        return err
    try:
        frame = proctoring_system.get_current_frame()
        if frame is None:
            return _err("No frame available", 404)
        ok, buffer = cv2.imencode(".jpg", frame)
        if not ok:
            return _err("Failed to encode frame", 500)
        return Response(content=buffer.tobytes(), media_type="image/jpeg")
    except Exception as exc:
        logger.error("Error getting frame: %s", exc)
        return _err(str(exc), 500)


@_secure.get(
    "/video/stream",
    tags=["Video"],
    summary="Live Motion JPEG webcam stream",
)
def video_stream():
    err = _require_session()
    if err is not None:
        return err

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

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ---------------------------------------------------------------------------
# Stats / configuration
# ---------------------------------------------------------------------------
@_secure.get(
    "/face-detection/stats", tags=["Stats"], summary="Face-detection statistics",
)
def face_detection_stats():
    err = _require_session()
    if err is not None:
        return err
    try:
        return proctoring_system.face_detector.get_detection_statistics()
    except Exception as exc:
        logger.error("Error getting face detection stats: %s", exc)
        return _err(str(exc), 500)


@_secure.get(
    "/eye-tracking/stats", tags=["Stats"], summary="Eye-tracking statistics",
)
def eye_tracking_stats():
    err = _require_session()
    if err is not None:
        return err
    try:
        return proctoring_system.eye_tracker.get_statistics()
    except Exception as exc:
        logger.error("Error getting eye tracking stats: %s", exc)
        return _err(str(exc), 500)


@_secure.get("/warnings", tags=["Session"], summary="Latest session warnings")
def get_warnings(limit: int = Query(default=50, ge=1, le=1000)):
    err = _require_session()
    if err is not None:
        return err
    try:
        warnings_ = proctoring_system.current_session.warnings[-limit:]
        return {
            "total_warnings": len(proctoring_system.current_session.warnings),
            "warnings": warnings_,
        }
    except Exception as exc:
        logger.error("Error getting warnings: %s", exc)
        return _err(str(exc), 500)


@_secure.get(
    "/configuration", tags=["Internal"], summary="Get runtime configuration (safe)",
)
def get_configuration():
    try:
        from config.settings import public_config
        return public_config()
    except Exception as exc:
        logger.error("Error getting configuration: %s", exc)
        return _err(str(exc), 500)


@_secure.put(
    "/configuration", tags=["Internal"], summary="Update mutable configuration values",
)
def update_configuration(body: UpdateConfigurationRequest):
    try:
        from config.settings import ProctoringConfig
        mutable = {
            "capture_interval": "CAPTURE_INTERVAL",
            "reverification_interval": "REVERIFICATION_INTERVAL",
            "max_faces_allowed": "MAX_FACES_ALLOWED",
        }
        updated = []
        data = body.model_dump(exclude_unset=True)
        for key, attr in mutable.items():
            if key in data and data[key] is not None:
                setattr(ProctoringConfig, attr, data[key])
                updated.append(key)
        return {
            "message": "Configuration updated successfully",
            "updated_fields": updated,
        }
    except Exception as exc:
        logger.error("Error updating configuration: %s", exc)
        return _err(str(exc), 500)


# Merge the secure router into the exported one.
proctoring_api.include_router(_secure)
