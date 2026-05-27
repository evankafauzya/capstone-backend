"""
High-level wrapper around the RetinaFace model.

Usage:
    detector = RetinaFaceDetector("models_data/face_detection_model.pth")
    result = detector.detect(bgr_image)
    # -> {"faces": [{"x":..., "y":..., "w":..., "h":..., "confidence":...,
    #                "landmarks": {"left_eye":..., "right_eye":...,
    #                              "nose":..., "left_mouth":..., "right_mouth":...}}]}
"""
from __future__ import annotations

import logging
from typing import List, Optional

import numpy as np
import torch

from .retinaface import (
    PriorBox,
    decode_boxes,
    decode_landms,
    load_retinaface,
    py_cpu_nms,
)

logger = logging.getLogger(__name__)

# Image-net mean used by the original training script.
_MEAN = np.array([104, 117, 123], dtype=np.float32)


class RetinaFaceDetector:
    """Run the trained RetinaFace MobileNet0.25 on BGR frames from OpenCV."""

    def __init__(
        self,
        checkpoint_path: str,
        device: Optional[torch.device] = None,
        confidence_threshold: float = 0.6,
        nms_threshold: float = 0.4,
        top_k: int = 5000,
        keep_top_k: int = 750,
    ):
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )
        self.confidence_threshold = float(confidence_threshold)
        self.nms_threshold = float(nms_threshold)
        self.top_k = int(top_k)
        self.keep_top_k = int(keep_top_k)

        self.model, self.cfg = load_retinaface(checkpoint_path, self.device)
        self.variance = self.cfg["variance"]
        logger.info(
            "RetinaFace loaded (%s) on %s",
            self.cfg.get("name", "?"),
            self.device,
        )

    @torch.no_grad()
    def detect(self, image_bgr: np.ndarray) -> dict:
        if image_bgr is None or image_bgr.size == 0:
            return {"faces": []}

        img = np.float32(image_bgr) - _MEAN
        height, width = img.shape[:2]
        scale_box = torch.tensor([width, height, width, height], device=self.device)
        scale_lm = torch.tensor([width, height] * 5, device=self.device)

        tensor = torch.from_numpy(img.transpose(2, 0, 1)).unsqueeze(0).to(self.device)

        loc, conf, landms = self.model(tensor)

        priors = PriorBox(self.cfg, image_size=(height, width)).forward().to(self.device)

        boxes = decode_boxes(loc.squeeze(0), priors, self.variance) * scale_box
        scores = conf.squeeze(0).cpu().numpy()[:, 1]
        landms_dec = decode_landms(landms.squeeze(0), priors, self.variance) * scale_lm

        boxes_np = boxes.cpu().numpy()
        landms_np = landms_dec.cpu().numpy()

        inds = scores > self.confidence_threshold
        boxes_np, landms_np, scores = boxes_np[inds], landms_np[inds], scores[inds]

        order = scores.argsort()[::-1][: self.top_k]
        boxes_np = boxes_np[order]
        landms_np = landms_np[order]
        scores = scores[order]

        dets = np.hstack((boxes_np, scores[:, np.newaxis])).astype(np.float32, copy=False)
        keep = py_cpu_nms(dets, self.nms_threshold)
        dets = dets[keep]
        landms_np = landms_np[keep]

        dets = dets[: self.keep_top_k]
        landms_np = landms_np[: self.keep_top_k]

        faces: List[dict] = []
        for det, lm in zip(dets, landms_np):
            x1, y1, x2, y2, conf_score = det
            x1, y1 = max(0, int(round(x1))), max(0, int(round(y1)))
            x2, y2 = min(width, int(round(x2))), min(height, int(round(y2)))
            w_box, h_box = x2 - x1, y2 - y1
            if w_box <= 0 or h_box <= 0:
                continue

            landmarks = {
                "left_eye": [float(lm[0]), float(lm[1])],
                "right_eye": [float(lm[2]), float(lm[3])],
                "nose": [float(lm[4]), float(lm[5])],
                "left_mouth": [float(lm[6]), float(lm[7])],
                "right_mouth": [float(lm[8]), float(lm[9])],
            }
            faces.append({
                "x": x1, "y": y1, "w": w_box, "h": h_box,
                "confidence": float(conf_score),
                "landmarks": landmarks,
            })

        return {"faces": faces}
