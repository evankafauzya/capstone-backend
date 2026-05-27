"""
Stateless liveness analyzer.

Takes a short sequence of frames (typically 8-15 frames at ~3 FPS, i.e. a
~3 second webcam clip) and decides whether the subject is a live human or
a static photo / video replay.

Signal model:
  * Real humans blink every 2-10 seconds and have small involuntary head
    sway from breathing and balance corrections.
  * A printed photo held in front of a camera never blinks, and stays
    pixel-perfectly still relative to the room.
  * A looped video replay can blink but usually has consistent micro-jitter
    artifacts; that detection is out of scope for this baseline. Blink +
    motion is enough to defeat the "print a JPEG" attack.

Verdict:
    is_alive  = (total_blinks >= 1) OR (max_nose_displacement_px > 4.0)

The MediaPipe FaceLandmarker model file is the same one used by the
FaceAligner; we look up the default location from there.
"""
from __future__ import annotations

import logging
import os
import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Indices into the MediaPipe FaceLandmarker (468-point) topology.
LEFT_EYE_OUTER, LEFT_EYE_INNER = 33, 133
LEFT_EYE_TOP, LEFT_EYE_BOTTOM = 159, 145
RIGHT_EYE_OUTER, RIGHT_EYE_INNER = 263, 362
RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM = 386, 374
NOSE_TIP = 1

# Soukupová & Čech-style eye-aspect-ratio thresholds.
EAR_CLOSED = 0.20   # below this counts as "closed"
EAR_OPEN = 0.25     # above this counts as "open" (hysteresis)

# Liveness verdict thresholds.
MIN_BLINKS_FOR_LIVE = 1
MIN_MOTION_PX_FOR_LIVE = 4.0


def _ear(corners: Tuple[float, float], top: Tuple[float, float],
         bottom: Tuple[float, float], inner: Tuple[float, float]) -> float:
    """Simple eye aspect ratio: vertical / horizontal."""
    horizontal = max(1e-6, float(np.hypot(corners[0] - inner[0],
                                          corners[1] - inner[1])))
    vertical = float(np.hypot(top[0] - bottom[0], top[1] - bottom[1]))
    return vertical / horizontal


class LivenessAnalyzer:
    """Runs MediaPipe FaceLandmarker frame-by-frame and emits a liveness verdict."""

    def __init__(self, landmarker_model_path: Optional[str] = None):
        # Default location matches FaceAligner.DEFAULT_MODEL_PATH so we share
        # the same bundled .task file. Computed at import time, not earlier,
        # so test stubs can override.
        from src.models.face_aligner import DEFAULT_MODEL_PATH
        path = landmarker_model_path or DEFAULT_MODEL_PATH
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"face_landmarker.task not found at {path}; "
                f"liveness analysis cannot start."
            )

        # Lazy MediaPipe import.
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        self._mp = mp
        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=path),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        logger.info("LivenessAnalyzer ready (model=%s)", path)

    # ---- per-frame ---------------------------------------------------------
    def _landmarks_for(self, frame_bgr: np.ndarray):
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w = frame_bgr.shape[:2]
        mp_image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect(mp_image)
        if not result.face_landmarks:
            return None
        lm = result.face_landmarks[0]

        def pt(idx):
            return (lm[idx].x * w, lm[idx].y * h)

        # Mean EAR across both eyes.
        left_ear = _ear(
            pt(LEFT_EYE_OUTER), pt(LEFT_EYE_TOP),
            pt(LEFT_EYE_BOTTOM), pt(LEFT_EYE_INNER),
        )
        right_ear = _ear(
            pt(RIGHT_EYE_OUTER), pt(RIGHT_EYE_TOP),
            pt(RIGHT_EYE_BOTTOM), pt(RIGHT_EYE_INNER),
        )
        return {
            "ear": (left_ear + right_ear) / 2.0,
            "nose": pt(NOSE_TIP),
        }

    # ---- public API --------------------------------------------------------
    def analyze(self, frames: List[np.ndarray]) -> dict:
        """Process ``frames`` in order and emit a liveness verdict."""
        start = time.time()
        ears: List[float] = []
        noses: List[Tuple[float, float]] = []
        no_face_count = 0

        for f in frames:
            data = self._landmarks_for(f) if f is not None else None
            if data is None:
                no_face_count += 1
                continue
            ears.append(data["ear"])
            noses.append(data["nose"])

        # Blink counting with hysteresis -- EAR drops below CLOSED then
        # comes back above OPEN.
        total_blinks = 0
        closed = False
        for e in ears:
            if not closed and e < EAR_CLOSED:
                closed = True
            elif closed and e > EAR_OPEN:
                total_blinks += 1
                closed = False

        # Max pairwise displacement of the nose tip across the clip.
        head_motion_px = 0.0
        if len(noses) >= 2:
            arr = np.asarray(noses, dtype=np.float32)
            head_motion_px = float(
                np.max(np.linalg.norm(arr[:, None, :] - arr[None, :, :], axis=-1))
            )

        reasons: List[str] = []
        if not ears:
            reasons.append("no_face_in_any_frame")
        if total_blinks < MIN_BLINKS_FOR_LIVE:
            reasons.append("no_blink_detected")
        if head_motion_px < MIN_MOTION_PX_FOR_LIVE:
            reasons.append("no_head_motion")

        is_alive = (
            total_blinks >= MIN_BLINKS_FOR_LIVE
            or head_motion_px >= MIN_MOTION_PX_FOR_LIVE
        )

        return {
            "is_alive": is_alive,
            "total_blinks": total_blinks,
            "head_movement_pixels": round(head_motion_px, 2),
            "frames_processed": len(ears),
            "frames_no_face": no_face_count,
            "reasons_against_liveness": reasons if not is_alive else [],
            "processing_time_ms": round((time.time() - start) * 1000.0, 2),
        }
