"""
Model manager — loads the trained RetinaFace and ArcFace checkpoints.

Falls back to OpenCV Haar Cascade ONLY for face detection if the .pth file
is missing. There is no histogram-based recognition fallback any more —
recognition simply reports that it is unavailable.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import cv2
import numpy as np
import torch

from src.models.face_detector import RetinaFaceDetector
from src.models.face_recognizer import FaceRecognizer
from src.models.yolo_face_detector import YoloFaceDetector

logger = logging.getLogger(__name__)


class ModelManager:
    """Owns the deep-learning models used by the proctoring backend.

    Detection backend priority:
      1. YOLO  — if ``yolo_detection_model_path`` exists. Preferred because the
         user trained it specifically for this dataset.
      2. RetinaFace — if ``detection_model_path`` exists.
      3. OpenCV Haar Cascade — last-resort fallback so the service stays up.
    """

    def __init__(
        self,
        recognition_model_path: str,
        detection_model_path: str,
        yolo_detection_model_path: Optional[str] = None,
        match_threshold: float = 0.4,
    ):
        self.recognition_model_path = recognition_model_path
        self.detection_model_path = detection_model_path
        self.yolo_detection_model_path = yolo_detection_model_path
        self.match_threshold = float(match_threshold)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.face_detector = None  # YoloFaceDetector | RetinaFaceDetector | None
        self.face_recognizer: Optional[FaceRecognizer] = None
        self._cascade: Optional[cv2.CascadeClassifier] = None

        self.detector_backend = "uninitialized"
        self.recognizer_backend = "uninitialized"

        self._load_detector()
        self._load_recognizer()

    # ------------------------------------------------------------------ load
    def _load_detector(self) -> None:
        # 1. Try YOLO first if a checkpoint is configured and exists.
        if self.yolo_detection_model_path and os.path.exists(self.yolo_detection_model_path):
            try:
                self.face_detector = YoloFaceDetector(
                    self.yolo_detection_model_path,
                    device=self.device,
                    confidence_threshold=0.5,
                )
                self.detector_backend = "yolo"
                logger.info("Detection backend: %s (%s)",
                            self.detector_backend, self.yolo_detection_model_path)
                return
            except Exception:
                logger.exception(
                    "Failed to load YOLO from %s — trying RetinaFace next.",
                    self.yolo_detection_model_path,
                )

        # 2. Fall back to RetinaFace.
        if os.path.exists(self.detection_model_path):
            try:
                self.face_detector = RetinaFaceDetector(
                    self.detection_model_path, device=self.device,
                )
                self.detector_backend = (
                    f"retinaface_{self.face_detector.cfg.get('name', '?')}"
                )
                logger.info("Detection backend: %s", self.detector_backend)
                return
            except Exception:
                logger.exception(
                    "Failed to load RetinaFace from %s — falling back to OpenCV.",
                    self.detection_model_path,
                )

        # 3. Last-resort OpenCV Haar Cascade.
        logger.warning(
            "No deep-learning detector available — using OpenCV Haar Cascade fallback."
        )
        self._cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.detector_backend = "opencv_haar_cascade"

    def _load_recognizer(self) -> None:
        if not os.path.exists(self.recognition_model_path):
            logger.warning(
                "Recognition model not found at %s — face verification disabled.",
                self.recognition_model_path,
            )
            self.recognizer_backend = "unavailable"
            return

        try:
            self.face_recognizer = FaceRecognizer(
                self.recognition_model_path,
                device=self.device,
                match_threshold=self.match_threshold,
            )
            arch = self.face_recognizer.meta.get("backbone_arch", "unknown")
            self.recognizer_backend = (
                f"arcface_{arch}_emb{self.face_recognizer.embedding_dim}"
            )
            logger.info("Recognition backend: %s", self.recognizer_backend)
        except Exception:
            logger.exception(
                "Failed to load ArcFace from %s — face verification disabled.",
                self.recognition_model_path,
            )
            self.recognizer_backend = "unavailable"

    # -------------------------------------------------------------- detection
    def detect_faces(
        self,
        frame: np.ndarray,
        confidence_threshold: float = 0.6,
    ) -> list:
        """Return a list of face dicts:
        ``[{"x", "y", "w", "h", "confidence", "landmarks"?}, ...]``"""
        if frame is None or frame.size == 0:
            return []

        if self.face_detector is not None:
            old = self.face_detector.confidence_threshold
            self.face_detector.confidence_threshold = float(confidence_threshold)
            try:
                return self.face_detector.detect(frame)["faces"]
            finally:
                self.face_detector.confidence_threshold = old

        # OpenCV fallback (no landmarks, fixed confidence label)
        if self._cascade is not None:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = self._cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
            )
            return [
                {"x": int(x), "y": int(y), "w": int(w), "h": int(h),
                 "confidence": 0.0, "landmarks": None}
                for (x, y, w, h) in detected
            ]
        return []

    # ----------------------------------------------------------- recognition
    @property
    def recognition_available(self) -> bool:
        return self.face_recognizer is not None

    def embed_face(self, face_bgr: np.ndarray) -> Optional[np.ndarray]:
        if self.face_recognizer is None:
            return None
        return self.face_recognizer.embed_face(face_bgr)

    def verify_faces(
        self,
        face_a: np.ndarray,
        face_b: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Optional[dict]:
        if self.face_recognizer is None:
            return None
        return self.face_recognizer.verify(face_a, face_b, threshold=threshold)

    def identify_face(
        self,
        face_bgr: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Optional[dict]:
        if self.face_recognizer is None:
            return None
        return self.face_recognizer.identify(face_bgr, threshold=threshold)

    # ------------------------------------------------------------ diagnostics
    def get_model_info(self) -> dict:
        if self.detector_backend == "yolo":
            detector_ckpt = self.yolo_detection_model_path
        elif self.detector_backend.startswith("retinaface"):
            detector_ckpt = self.detection_model_path
        else:
            detector_ckpt = None

        info = {
            "device": str(self.device),
            "cuda_available": torch.cuda.is_available(),
            "detector": {
                "backend": self.detector_backend,
                "checkpoint": detector_ckpt,
                "loaded": self.face_detector is not None or self._cascade is not None,
            },
            "recognizer": {
                "backend": self.recognizer_backend,
                "checkpoint": self.recognition_model_path,
                "loaded": self.face_recognizer is not None,
            },
        }
        if self.face_recognizer is not None:
            stats = self.face_recognizer.alignment_stats
            total = stats["aligned"] + stats["fallback"]
            info["recognizer"].update({
                "embedding_dim": self.face_recognizer.embedding_dim,
                "img_size": self.face_recognizer.img_size,
                "num_identities": len(self.face_recognizer.label_to_name),
                "best_val_acc": self.face_recognizer.meta.get("best_val_acc"),
                "alignment_enabled": self.face_recognizer.aligner is not None,
                "alignment_stats": {
                    **stats,
                    "aligned_pct": (
                        round(100.0 * stats["aligned"] / total, 1)
                        if total > 0 else None
                    ),
                },
            })
        return info
