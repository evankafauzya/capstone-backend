"""
Shared pytest fixtures.

The tests boot the real FastAPI app inside a TestClient context (so the
``lifespan`` runs and the proctoring system + enrollment store initialize).
The detector is monkey-patched per request when the test does not want to
exercise the real YOLO model -- otherwise the test would need an actual
face photo on disk.
"""
from __future__ import annotations

import base64
import os
import tempfile

import cv2
import numpy as np
import pytest

# --- Test-time configuration --------------------------------------------------
# Must be set BEFORE the app module imports.
os.environ["API_KEY"] = "test-key"
os.environ["API_KEY_REQUIRED"] = "true"
os.environ["ENVIRONMENT"] = "development"

# Auto-enable mock mode when the real model files are absent (CI runners,
# fresh clones). Locally, if the .pth/.pt files are present we use the
# real stack so model-load regressions are still caught.
_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(_HERE)
_REQUIRED_MODELS = [
    os.path.join(_REPO, "models_data", "face_detection_yolo.pt"),
    os.path.join(_REPO, "models_data", "face_recognition_efficient.pth"),
    os.path.join(_REPO, "models_data", "face_recognition_model.pth"),
]
if "MOCK_MODELS" not in os.environ:
    # Mock unless ALL expected detector + at least one recognizer are present.
    has_detector = os.path.exists(_REQUIRED_MODELS[0])
    has_recognizer = (
        os.path.exists(_REQUIRED_MODELS[1])
        or os.path.exists(_REQUIRED_MODELS[2])
    )
    if not (has_detector and has_recognizer):
        os.environ["MOCK_MODELS"] = "1"

# Each test session uses its own DB so previous enrollments do not bleed in.
_TEST_DB = os.path.join(tempfile.gettempdir(), "proctoring_test_enrollments.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)
os.environ["ENROLLMENT_DB_PATH"] = _TEST_DB

# --- Fixtures ----------------------------------------------------------------
@pytest.fixture(scope="session")
def app_instance():
    """Import the app module exactly once per session."""
    import app as app_module
    return app_module.app


@pytest.fixture
def client(app_instance):
    """Fresh TestClient per test, with lifespan triggered."""
    from fastapi.testclient import TestClient
    with TestClient(app_instance) as c:
        yield c


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-key"}


@pytest.fixture
def dummy_jpeg_b64():
    """A black 640x480 JPEG, base64-encoded. Use when the route does not
    care whether a real face is detected (e.g. validation tests)."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    _, jpg = cv2.imencode(".jpg", img)
    return base64.b64encode(jpg.tobytes()).decode()


@pytest.fixture
def fake_detect(monkeypatch):
    """Force the detector to always return a single high-confidence face
    that fills most of the frame. Used by tests that exercise routes
    downstream of detection (enroll, verify) without needing a real photo.
    """
    def _patched(frame, confidence_threshold=0.6):
        h, w = frame.shape[:2]
        return [{
            "x": 50, "y": 50,
            "w": max(1, w - 100), "h": max(1, h - 100),
            "confidence": 0.99,
            "landmarks": None,
        }]

    from src.api import moodle_routes
    monkeypatch.setattr(moodle_routes, "_detect", _patched)
    return _patched
