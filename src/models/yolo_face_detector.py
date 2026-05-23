"""
YOLO-based face detector (Ultralytics).

Loads a single-class YOLO checkpoint (e.g. YOLOv8n-face / YOLOv11n-face) and
exposes the same ``detect(image_bgr) -> {"faces": [...]}`` contract as
:class:`src.models.face_detector.RetinaFaceDetector` so the rest of the
codebase does not need to change.

Each face dict has:
    {"x", "y", "w", "h", "confidence", "landmarks": None}

YOLO face detectors typically do not emit facial landmarks; downstream code
that uses landmarks (e.g. /detect/behavior gaze logic) must already handle
``landmarks is None`` — which it does.
"""
from __future__ import annotations

import logging
import os
from typing import List, Optional

import numpy as np
import torch

logger = logging.getLogger(__name__)

# Quiet ultralytics's bootstrap chatter and turn off its outbound telemetry.
os.environ.setdefault("YOLO_VERBOSE", "False")
os.environ.setdefault("YOLO_OFFLINE", "1")


class YoloFaceDetector:
    """Wraps an Ultralytics YOLO single-class face detector."""

    def __init__(
        self,
        checkpoint_path: str,
        device: Optional[torch.device] = None,
        confidence_threshold: float = 0.5,
        iou_threshold: float = 0.45,
        imgsz: int = 640,
        max_detections: int = 50,
    ):
        # Import here so the dependency is only required when this backend is used.
        from ultralytics import YOLO

        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.confidence_threshold = float(confidence_threshold)
        self.iou_threshold = float(iou_threshold)
        self.imgsz = int(imgsz)
        self.max_detections = int(max_detections)

        self.model = YOLO(checkpoint_path)
        # Move underlying torch model onto the right device for inference.
        try:
            self.model.to(self.device)
        except Exception:
            # Older ultralytics versions accept the device on each predict call.
            logger.debug("YOLO.to(device) failed; will pass device per call.")

        self.names = dict(self.model.names) if hasattr(self.model, "names") else {0: "face"}
        n_params = sum(p.numel() for p in self.model.model.parameters())
        logger.info(
            "YOLO face detector loaded (params=%d, classes=%s, device=%s)",
            n_params, list(self.names.values()), self.device,
        )

        # Backwards-compatible cfg dict so ModelManager can label the backend.
        self.cfg = {"name": "yolo", "classes": self.names}

    @torch.no_grad()
    def detect(self, image_bgr: np.ndarray) -> dict:
        if image_bgr is None or image_bgr.size == 0:
            return {"faces": []}

        # Ultralytics accepts BGR numpy arrays directly.
        results = self.model.predict(
            source=image_bgr,
            conf=self.confidence_threshold,
            iou=self.iou_threshold,
            imgsz=self.imgsz,
            max_det=self.max_detections,
            device=self.device,
            verbose=False,
        )

        faces: List[dict] = []
        H, W = image_bgr.shape[:2]
        if not results:
            return {"faces": []}

        res = results[0]
        if res.boxes is None or len(res.boxes) == 0:
            return {"faces": []}

        boxes_xyxy = res.boxes.xyxy.cpu().numpy()
        confidences = res.boxes.conf.cpu().numpy()

        for (x1, y1, x2, y2), conf in zip(boxes_xyxy, confidences):
            x1, y1 = max(0, int(round(float(x1)))), max(0, int(round(float(y1))))
            x2, y2 = min(W, int(round(float(x2)))), min(H, int(round(float(y2))))
            w_box, h_box = x2 - x1, y2 - y1
            if w_box <= 0 or h_box <= 0:
                continue
            faces.append({
                "x": x1, "y": y1, "w": w_box, "h": h_box,
                "confidence": float(conf),
                "landmarks": None,
            })

        return {"faces": faces}
