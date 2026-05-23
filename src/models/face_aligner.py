"""
Face alignment via MediaPipe FaceLandmarker + similarity transform.

Aligns face crops to the standard ArcFace 5-point template (InsightFace
convention) before they are fed to the recognizer. This makes the
embedding much more stable across head pose, because the model always
sees eyes at the same horizontal position and the face at the same scale.

Pipeline:
    BGR face crop
      -> MediaPipe FaceLandmarker -> 478 landmarks
      -> 5-point reduction (eyes, nose, mouth corners)
      -> cv2.estimateAffinePartial2D against the canonical template
      -> warpAffine -> 112x112 aligned BGR crop

If the landmarker cannot find a face (rare, at extreme angles), ``align()``
returns ``None`` so the caller can fall back to a plain resize.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Canonical InsightFace ArcFace 5-point template for 112x112 inputs.
ARCFACE_TEMPLATE_112 = np.array(
    [
        [38.2946, 51.6963],   # left eye (image-left side)
        [73.5318, 51.5014],   # right eye (image-right side)
        [56.0252, 71.7366],   # nose tip
        [41.5493, 92.3655],   # left mouth corner
        [70.7299, 92.2041],   # right mouth corner
    ],
    dtype=np.float32,
)

# MediaPipe FaceLandmarker indices. Image-left = template "left".
LEFT_EYE_CORNERS = (33, 133)     # outer, inner — image-left side
RIGHT_EYE_CORNERS = (263, 362)   # outer, inner — image-right side
NOSE_TIP = 1
LEFT_MOUTH = 61
RIGHT_MOUTH = 291

# Default location of the bundled face_landmarker.task model.
DEFAULT_MODEL_PATH = os.path.join("models_data", "face_landmarker.task")


class FaceAligner:
    """Aligns face crops to the ArcFace 5-point template using MediaPipe."""

    def __init__(
        self,
        output_size: int = 112,
        landmarker_model_path: Optional[str] = None,
    ):
        self.output_size = int(output_size)
        scale = self.output_size / 112.0
        self.template = ARCFACE_TEMPLATE_112 * scale

        # Lazy import — keeps MediaPipe out of modules that don't need it.
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision as mp_vision

        self._mp = mp  # for Image / ImageFormat at inference time

        model_path = landmarker_model_path or DEFAULT_MODEL_PATH
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"face_landmarker.task not found at {model_path}; "
                f"face alignment cannot start."
            )

        options = mp_vision.FaceLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=model_path),
            output_face_blendshapes=False,
            output_facial_transformation_matrixes=False,
            num_faces=1,
        )
        self._landmarker = mp_vision.FaceLandmarker.create_from_options(options)
        logger.info(
            "FaceAligner ready (output_size=%d, model=%s)",
            self.output_size, model_path,
        )

    # ---- landmark extraction ---------------------------------------------
    def _five_landmarks(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        h, w = image_bgr.shape[:2]
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        mp_image = self._mp.Image(
            image_format=self._mp.ImageFormat.SRGB, data=rgb,
        )
        result = self._landmarker.detect(mp_image)
        if not result.face_landmarks:
            return None
        lm = result.face_landmarks[0]

        def pt(idx):
            return (lm[idx].x * w, lm[idx].y * h)

        def midpoint(a, b):
            ax, ay = pt(a)
            bx, by = pt(b)
            return ((ax + bx) * 0.5, (ay + by) * 0.5)

        try:
            return np.array(
                [
                    midpoint(*LEFT_EYE_CORNERS),
                    midpoint(*RIGHT_EYE_CORNERS),
                    pt(NOSE_TIP),
                    pt(LEFT_MOUTH),
                    pt(RIGHT_MOUTH),
                ],
                dtype=np.float32,
            )
        except IndexError:
            return None

    # ---- public API ------------------------------------------------------
    def align(self, image_bgr: np.ndarray) -> Optional[np.ndarray]:
        """Align a face crop to the canonical template.

        Returns the warped ``output_size x output_size`` BGR image, or
        ``None`` if landmarks could not be extracted.
        """
        if image_bgr is None or image_bgr.size == 0:
            return None
        landmarks = self._five_landmarks(image_bgr)
        if landmarks is None:
            return None

        M, _inliers = cv2.estimateAffinePartial2D(
            landmarks, self.template,
            method=cv2.LMEDS, ransacReprojThreshold=3.0,
        )
        if M is None:
            return None

        return cv2.warpAffine(
            image_bgr, M,
            (self.output_size, self.output_size),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_REPLICATE,
        )
