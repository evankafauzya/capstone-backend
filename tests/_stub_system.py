"""
Stub ProctoringSystem used in tests / CI when the real model files are not
available (e.g. on GitHub Actions runners).

The stub keeps the exact same public interface as the real
``src.core.orchestrator.ProctoringSystem`` / ``src.core.model_manager.ModelManager``
so the routes can run unchanged.

Embeddings are deterministic per input image (seeded from a hash of the
pixel bytes), so two calls with the same crop return the same vector and
verify_face self-similarity stays exactly 1.0. Two different crops return
different vectors with cosine ~0, mimicking a healthy real model.
"""
from __future__ import annotations

import hashlib
from typing import Optional

import numpy as np


def _deterministic_embedding(crop: np.ndarray) -> np.ndarray:
    """Return a deterministic L2-normalized 512-d vector for ``crop``."""
    digest = hashlib.blake2b(crop.tobytes(), digest_size=8).digest()
    seed = int.from_bytes(digest, "little") & 0xFFFFFFFF
    rng = np.random.RandomState(seed)
    v = rng.randn(512).astype(np.float32)
    n = float(np.linalg.norm(v)) or 1.0
    return v / n


class StubFaceRecognizer:
    embedding_dim = 512
    img_size = 112
    match_threshold = 0.4
    unknown_threshold = 0.5
    aligner = None
    alignment_stats = {"aligned": 0, "fallback": 0}
    meta = {"backbone_arch": "stub", "best_val_acc": 0.0}
    label_to_name = {}
    class_centers = None

    def embed_face(self, crop: np.ndarray) -> np.ndarray:
        return _deterministic_embedding(crop)


class StubModelManager:
    detector_backend = "stub_detector"
    recognizer_backend = "arcface_stub_emb512"
    recognition_available = True
    device = "cpu"

    def __init__(self) -> None:
        self.face_recognizer = StubFaceRecognizer()
        self.face_detector = None
        self.recognition_model_path = "stub://recognition"
        self.detection_model_path = "stub://detection"
        self.yolo_detection_model_path = None
        self.match_threshold = self.face_recognizer.match_threshold

    def detect_faces(self, frame: np.ndarray, confidence_threshold: float = 0.6):
        """Return a single fake face roughly filling the frame.

        Per-test monkeypatches in conftest can still override the route-level
        ``_detect`` helper to return *no* faces if a test wants to exercise
        the no-face branches.
        """
        if frame is None or frame.size == 0:
            return []
        h, w = frame.shape[:2]
        return [{
            "x": 50, "y": 50,
            "w": max(1, w - 100), "h": max(1, h - 100),
            "confidence": 0.95,
            "landmarks": None,
        }]

    def embed_face(self, crop: np.ndarray) -> np.ndarray:
        return self.face_recognizer.embed_face(crop)

    def get_model_info(self) -> dict:
        return {
            "device": "cpu",
            "cuda_available": False,
            "detector": {
                "backend": self.detector_backend,
                "checkpoint": "stub",
                "loaded": True,
            },
            "recognizer": {
                "backend": self.recognizer_backend,
                "checkpoint": "stub",
                "loaded": True,
                "embedding_dim": 512,
                "img_size": 112,
                "num_identities": 0,
                "best_val_acc": 0.0,
                "alignment_enabled": False,
                "alignment_stats": {
                    "aligned": 0, "fallback": 0, "aligned_pct": None,
                },
            },
        }


class StubProctoringSystem:
    """Mimics ``ProctoringSystem`` with just the surface the routes touch."""

    is_running = False

    def __init__(self) -> None:
        self.model_manager = StubModelManager()
        self.current_session: Optional[object] = None
        self.face_detector = self  # any non-None sentinel
        self.eye_tracker = self    # likewise

    # ---- Session lifecycle (not exercised by smoke tests) -----------------
    def start_session(self, session_id: str, user_id: str) -> bool:
        self.current_session = type("Session", (), {
            "session_id": session_id, "user_id": user_id, "warnings": [],
        })()
        return True

    def stop_session(self) -> dict:
        self.current_session = None
        return {"session_summary": {}, "report_paths": []}

    def get_session_status(self) -> Optional[dict]:
        return None if self.current_session is None else {
            "session_id": self.current_session.session_id,
            "user_id": self.current_session.user_id,
        }

    def get_current_frame(self):
        return None

    def get_system_info(self) -> dict:
        return {
            "status": "stub",
            "model_manager": self.model_manager.get_model_info(),
        }
