"""
Moodle-Compatible REST API Endpoints (FastAPI).

These endpoints sit behind Bearer-token auth and delegate to the real
trained models loaded by :class:`src.core.model_manager.ModelManager`:

* YOLO (Ultralytics) -- face detection (preferred)
* RetinaFace (MobileNet0.25) -- face detection (fallback)
* ArcFace -- verification + identification. The backbone (ResNet50 or
  EfficientNet-B0) is autodetected from the checkpoint's projection
  layer shape -- see src/models/arcface.py.
"""
from __future__ import annotations

import base64
import logging
import time
from typing import List, Optional

import cv2
import numpy as np
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse

from src.api.auth import require_api_key
from src.api.schemas import (
    BatchProcessRequest,
    DeleteEnrollmentResponse,
    DetectBehaviorRequest,
    DetectFacesRequest,
    DetectLivenessRequest,
    EmbeddingsRequest,
    EnrollFaceGuidedRequest,
    EnrollFaceRequest,
    EnrollmentInfoResponse,
    VerifyFaceRequest,
)
from src.services.audit import VerificationAuditStore
from src.services.face_enrollment import (
    EnrollmentError,
    FaceEnrollmentStore,
    validate_user_id,
)

logger = logging.getLogger(__name__)

moodle_api = APIRouter(
    tags=["Moodle"],
    dependencies=[Depends(require_api_key)],
)

_proctoring_system = None
_enrollment_store: "FaceEnrollmentStore | None" = None
_audit_store: "VerificationAuditStore | None" = None


def set_moodle_proctoring_system(system) -> None:
    """Set the global proctoring system reference."""
    global _proctoring_system
    _proctoring_system = system


def set_enrollment_store(store: FaceEnrollmentStore) -> None:
    """Set the global enrollment store reference."""
    global _enrollment_store
    _enrollment_store = store


def set_audit_store(store: VerificationAuditStore) -> None:
    """Set the global verification audit store reference."""
    global _audit_store
    _audit_store = store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _model_manager():
    return getattr(_proctoring_system, "model_manager", None)


def _err(message: str, code: int = 400, **extra) -> JSONResponse:
    """Return a uniformly-shaped error response."""
    body = {"error": message}
    if extra:
        body.update(extra)
    return JSONResponse(status_code=code, content=body)


def decode_base64_image(image_base64: str) -> np.ndarray:
    """Decode a base64 string (with or without ``data:...;base64,`` prefix)
    into a BGR OpenCV image."""
    try:
        if "," in image_base64 and image_base64.startswith("data:"):
            image_base64 = image_base64.split(",", 1)[1]
        image_bytes = base64.b64decode(image_base64)
        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Failed to decode image from base64 data")
        return frame
    except Exception as exc:
        raise ValueError(f"Invalid base64 image: {exc}")


def _detect(frame: np.ndarray, confidence_threshold: float = 0.6) -> list:
    """Run face detection through the ModelManager."""
    mm = _model_manager()
    if mm is None:
        return []
    return mm.detect_faces(frame, confidence_threshold=confidence_threshold)


def _select_primary_face(
    faces: list, min_side: int = 40, min_confidence: float = 0.7,
) -> Optional[dict]:
    """Pick the most likely 'student' face."""
    if not faces:
        return None
    viable = [
        f for f in faces
        if min(f["w"], f["h"]) >= min_side
        and f.get("confidence", 0.0) >= min_confidence
    ]
    pool = viable or faces
    return max(pool, key=lambda f: f["w"] * f["h"])


def _crop_first_face(
    frame: np.ndarray, faces: list, margin: float = 0.15,
) -> Optional[np.ndarray]:
    """Return the BGR crop of the primary face, with a small context margin."""
    primary = _select_primary_face(faces)
    if primary is None:
        return None
    x, y, w, h = primary["x"], primary["y"], primary["w"], primary["h"]
    pad_w, pad_h = int(round(w * margin)), int(round(h * margin))
    H, W = frame.shape[:2]
    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(W, x + w + pad_w)
    y2 = min(H, y + h + pad_h)
    if x2 <= x1 or y2 <= y1:
        return None
    return frame[y1:y2, x1:x2]


def _backend_label() -> dict:
    mm = _model_manager()
    if mm is None:
        return {"detector": "unavailable", "recognizer": "unavailable"}
    return {"detector": mm.detector_backend, "recognizer": mm.recognizer_backend}


# Lazy singleton for the liveness analyzer. We don't build it at boot because
# the route is rarely the hottest path and MediaPipe init takes ~half a second.
_liveness_singleton = None
_liveness_init_failed = False


def _get_liveness_analyzer():
    """Return a shared LivenessAnalyzer, or None if the model file is missing."""
    global _liveness_singleton, _liveness_init_failed
    if _liveness_singleton is not None:
        return _liveness_singleton
    if _liveness_init_failed:
        return None
    try:
        from src.detectors.liveness import LivenessAnalyzer
        _liveness_singleton = LivenessAnalyzer()
        return _liveness_singleton
    except FileNotFoundError as exc:
        logger.warning("LivenessAnalyzer disabled: %s", exc)
        _liveness_init_failed = True
        return None
    except Exception:
        logger.exception("LivenessAnalyzer failed to initialize")
        _liveness_init_failed = True
        return None


def _record_audit(
    request,
    *,
    user_id,
    method,
    match_score,
    threshold,
    matched,
    references_compared=0,
    best_reference_id=None,
    reason=None,
):
    """Best-effort write to the audit log. Never raises — verification
    requests must succeed even if the audit store is temporarily unhappy."""
    if _audit_store is None:
        return None
    mm = _model_manager()
    try:
        client_ip = request.client.host if request and request.client else None
        return _audit_store.record(
            user_id=user_id,
            method=method,
            match_score=float(match_score),
            threshold=float(threshold),
            matched=bool(matched),
            references_compared=int(references_compared),
            best_reference_id=best_reference_id,
            reason=reason,
            recognizer_backend=(mm.recognizer_backend if mm else None),
            detector_backend=(mm.detector_backend if mm else None),
            client_ip=client_ip,
            request_id=(
                getattr(request.state, "request_id", None) if request else None
            ),
        )
    except Exception:
        logger.exception("Failed to write verification audit row")
        return None


# ===========================================================================
# Endpoints
# ===========================================================================
@moodle_api.post("/detect/faces", summary="Detect faces in an image")
def detect_faces(body: DetectFacesRequest):
    try:
        frame = decode_base64_image(body.image)
    except ValueError as exc:
        return _err(str(exc), 400)

    start = time.time()
    faces = _detect(frame, confidence_threshold=body.options.confidence_threshold)

    response_faces: List[dict] = []
    landmarks_collected: List[dict] = []
    for f in faces:
        item = {
            "x": int(f["x"]), "y": int(f["y"]),
            "w": int(f["w"]), "h": int(f["h"]),
            "confidence": float(f.get("confidence", 0.0)),
        }
        if body.options.return_landmarks and f.get("landmarks"):
            item["landmarks"] = f["landmarks"]
            landmarks_collected.append(f["landmarks"])
        response_faces.append(item)

    return {
        "faces": response_faces,
        "face_count": len(response_faces),
        "landmarks": landmarks_collected,
        "processing_time_ms": round((time.time() - start) * 1000.0, 2),
        "backend": _backend_label(),
    }


@moodle_api.post("/verify/face", summary="Verify a face against a reference or enrolled user")
def verify_face(body: VerifyFaceRequest, request: Request):
    """Compare a live face to either a single reference image *or* against
    every reference previously enrolled for ``user_id``.

    Exactly one of ``reference_face`` / ``user_id`` must be provided.
    """
    has_reference = body.reference_face is not None
    has_user_id = body.user_id is not None
    if has_reference == has_user_id:
        return _err("Provide exactly one of 'reference_face' or 'user_id'.", 400)

    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return _err(
            "Face recognition model not loaded on this server.",
            503, details=_backend_label(),
        )

    try:
        current_frame = decode_base64_image(body.current_face)
    except ValueError as exc:
        return _err(str(exc), 400)

    threshold = float(
        body.options.match_threshold
        if body.options.match_threshold is not None
        else mm.face_recognizer.match_threshold
    )
    return_embeddings = body.options.return_embeddings

    start = time.time()

    # ---- detect and crop the current face ----
    cur_faces = _detect(current_frame, confidence_threshold=0.8)
    if not cur_faces:
        _record_audit(request, user_id=body.user_id, method="no_face",
                      match_score=0.0, threshold=threshold, matched=False,
                      reason="no_face_in_current_frame")
        return {
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "no_face_in_current_frame"},
        }
    cur_crop = _crop_first_face(current_frame, cur_faces)
    if cur_crop is None:
        _record_audit(request, user_id=body.user_id, method="no_face",
                      match_score=0.0, threshold=threshold, matched=False,
                      reason="invalid_face_crop")
        return {
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "invalid_face_crop"},
        }

    emb_cur = mm.embed_face(cur_crop)

    # ---- branch: stored references vs single reference ----
    if has_user_id:
        try:
            user_id = validate_user_id(body.user_id)
        except EnrollmentError as exc:
            return _err(str(exc), 400)
        if _enrollment_store is None:
            return _err("Enrollment store unavailable.", 503)

        ref_ids, ref_embs = _enrollment_store.get_embeddings(user_id)
        if ref_embs.shape[0] == 0:
            _record_audit(request, user_id=user_id, method="user_id",
                          match_score=0.0, threshold=threshold, matched=False,
                          reason="no_enrolled_references")
            return _err(
                f"No enrolled references for user '{user_id}'.",
                404, user_id=user_id,
            )

        scores = ref_embs @ emb_cur
        best_idx = int(np.argmax(scores))
        score = float(scores[best_idx])
        mean_score = float(np.mean(scores))
        is_match = score >= threshold

        logger.info(
            "verify_face[user_id=%s]: best=%.4f mean=%.4f threshold=%.2f "
            "match=%s (current_box=%dx%d, references=%d, best_ref=%s)",
            user_id, score, mean_score, threshold, is_match,
            cur_crop.shape[1], cur_crop.shape[0],
            ref_embs.shape[0], ref_ids[best_idx],
        )

        payload = {
            "is_match": is_match,
            "match_score": round(score, 4),
            "confidence": round(score, 4),
            "details": {
                "method": "arcface_max_similarity_over_references",
                "threshold_used": threshold,
                "processing_time_ms": round((time.time() - start) * 1000.0, 2),
                "user_id": user_id,
                "references_compared": int(ref_embs.shape[0]),
                "best_reference_id": ref_ids[best_idx],
                "best_score": round(score, 4),
                "mean_score": round(mean_score, 4),
                "all_scores": [round(float(s), 4) for s in scores],
                "embedding_dim": mm.face_recognizer.embedding_dim,
                "backend": _backend_label(),
            },
        }
        if return_embeddings:
            payload["embeddings"] = {"current": emb_cur.tolist()}
        _record_audit(request, user_id=user_id, method="user_id",
                      match_score=score, threshold=threshold, matched=is_match,
                      references_compared=int(ref_embs.shape[0]),
                      best_reference_id=ref_ids[best_idx])
        return payload

    # ---- single-reference (legacy) mode ----
    try:
        reference_frame = decode_base64_image(body.reference_face)
    except ValueError as exc:
        return _err(str(exc), 400)

    ref_faces = _detect(reference_frame, confidence_threshold=0.8)
    logger.info(
        "verify_face: detected %d face(s) in current, %d in reference",
        len(cur_faces), len(ref_faces),
    )
    if not ref_faces:
        _record_audit(request, user_id=None, method="reference_face",
                      match_score=0.0, threshold=threshold, matched=False,
                      reason="no_face_in_reference_frame")
        return {
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "no_face_in_reference_frame"},
        }

    ref_crop = _crop_first_face(reference_frame, ref_faces)
    if ref_crop is None:
        _record_audit(request, user_id=None, method="reference_face",
                      match_score=0.0, threshold=threshold, matched=False,
                      reason="invalid_face_crop_reference")
        return {
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "invalid_face_crop"},
        }

    emb_ref = mm.embed_face(ref_crop)
    score = float(np.dot(emb_cur, emb_ref))
    is_match = score >= threshold
    logger.info(
        "verify_face: score=%.4f threshold=%.2f match=%s "
        "(current_box=%dx%d, reference_box=%dx%d)",
        score, threshold, is_match,
        cur_crop.shape[1], cur_crop.shape[0],
        ref_crop.shape[1], ref_crop.shape[0],
    )

    payload = {
        "is_match": is_match,
        "match_score": round(score, 4),
        "confidence": round(score, 4),
        "details": {
            "method": "arcface_cosine_similarity",
            "threshold_used": threshold,
            "processing_time_ms": round((time.time() - start) * 1000.0, 2),
            "current_face_detected": True,
            "reference_face_detected": True,
            "embedding_dim": mm.face_recognizer.embedding_dim,
            "backend": _backend_label(),
        },
    }
    if return_embeddings:
        payload["embeddings"] = {
            "current": emb_cur.tolist(),
            "reference": emb_ref.tolist(),
        }
    _record_audit(request, user_id=None, method="reference_face",
                  match_score=score, threshold=threshold, matched=is_match,
                  references_compared=1)
    return payload


# ---------------------------------------------------------------------------
# Verification audit log (read-only, ops/dispute use)
# ---------------------------------------------------------------------------
@moodle_api.get(
    "/verifications/{user_id}",
    tags=["Audit"],
    summary="Return the verification audit trail for a user (most-recent first)",
)
def get_verifications(user_id: str, limit: int = 100):
    """Return up to ``limit`` recent ``/verify/face`` calls that targeted
    this ``user_id``. Embeddings and image bytes are NEVER stored or
    returned -- only the score, threshold, decision, and metadata."""
    if _audit_store is None:
        return _err("Verification audit store unavailable.", 503)
    try:
        validate_user_id(user_id)
    except EnrollmentError as exc:
        return _err(str(exc), 400)
    if not 1 <= int(limit) <= 1000:
        return _err("'limit' must be between 1 and 1000.", 400)
    rows = _audit_store.for_user(user_id, limit=limit)
    return {"user_id": user_id, "count": len(rows), "verifications": rows}


@moodle_api.post(
    "/detect/liveness",
    summary="Verdict whether a short webcam clip shows a live human or a static photo",
)
def detect_liveness(body: DetectLivenessRequest):
    """Analyze a short sequence of frames for signs of a live human (blinking,
    micro head movement). Use this BEFORE ``/verify/face`` to reject the
    "held up a printed photo" attack.

    Returns 503 if the MediaPipe face_landmarker.task model file is not
    present on the server (the same file used by face alignment).
    """
    # Decode frames first; pydantic guarantees the count is 3..30.
    frames = []
    skipped = []
    for i, b64 in enumerate(body.frames):
        try:
            frames.append(decode_base64_image(b64))
        except ValueError as exc:
            skipped.append({"index": i, "reason": str(exc)})
    if not frames:
        return _err(
            "No usable frames in the request.",
            400, skipped=skipped,
        )

    analyzer = _get_liveness_analyzer()
    if analyzer is None:
        return _err(
            "Liveness model not loaded on this server "
            "(face_landmarker.task missing).",
            503,
        )

    try:
        result = analyzer.analyze(frames)
    except Exception as exc:
        logger.exception("Liveness analyzer crashed")
        return _err(f"Liveness analysis failed: {exc}", 500)

    if skipped:
        result["skipped"] = skipped
    return result


@moodle_api.post("/detect/behavior", summary="Detect suspicious behavior in a frame")
def detect_behavior(body: DetectBehaviorRequest):
    try:
        frame = decode_base64_image(body.image)
    except ValueError as exc:
        return _err(str(exc), 400)

    start = time.time()
    faces = _detect(frame, confidence_threshold=0.6)
    H, W = frame.shape[:2]

    result = {
        "multiple_faces_detected": False,
        "face_count": len(faces),
        "no_face_detected": len(faces) == 0,
        "unusual_eye_gaze": False,
        "unusual_head_pose": False,
        "suspicious_indicators": [],
        "risk_level": "low",
    }

    if len(faces) == 0:
        result["suspicious_indicators"].append("no_face_detected")
        result["risk_level"] = "medium"

    if body.options.detect_multiple_faces and len(faces) > 1:
        result["multiple_faces_detected"] = True
        result["suspicious_indicators"].append(f"multiple_faces: {len(faces)}")
        result["risk_level"] = "high"

    if body.options.detect_head_pose and faces:
        best = max(faces, key=lambda f: f.get("confidence", 0.0))
        cx = best["x"] + best["w"] / 2
        cy = best["y"] + best["h"] / 2
        if cx / W < 0.25 or cx / W > 0.75:
            result["unusual_head_pose"] = True
            result["suspicious_indicators"].append("head_turned_sideways")
            if result["risk_level"] == "low":
                result["risk_level"] = "medium"
        if cy / H < 0.20 or cy / H > 0.80:
            result["unusual_head_pose"] = True
            result["suspicious_indicators"].append("head_tilted")
            if result["risk_level"] == "low":
                result["risk_level"] = "medium"

    if body.options.detect_eye_gaze and faces:
        best = max(faces, key=lambda f: f.get("confidence", 0.0))
        lm = best.get("landmarks") or {}
        le, re_, nose = lm.get("left_eye"), lm.get("right_eye"), lm.get("nose")
        if le and re_ and nose:
            eye_mid_x = (le[0] + re_[0]) / 2
            eye_span = max(1.0, abs(re_[0] - le[0]))
            offset = (nose[0] - eye_mid_x) / eye_span
            if abs(offset) > 0.25:
                result["unusual_eye_gaze"] = True
                result["suspicious_indicators"].append(f"gaze_offset:{offset:+.2f}")
                if result["risk_level"] == "low":
                    result["risk_level"] = "medium"
            result["gaze_offset"] = round(offset, 3)

    result["processing_time_ms"] = round((time.time() - start) * 1000.0, 2)
    result["backend"] = _backend_label()
    return result


@moodle_api.post("/embeddings", summary="Compute a 512-d ArcFace embedding")
def get_embeddings(body: EmbeddingsRequest):
    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return _err(
            "Face recognition model not loaded on this server.",
            503, details=_backend_label(),
        )

    try:
        frame = decode_base64_image(body.image)
    except ValueError as exc:
        return _err(str(exc), 400)

    start = time.time()
    faces = _detect(frame, confidence_threshold=0.8)
    if not faces:
        return {
            "embeddings": [], "embedding_dim": 0,
            "model_used": mm.recognizer_backend,
            "error": "No face detected in image",
        }

    crop = _crop_first_face(frame, faces)
    if crop is None:
        return _err("Invalid face crop", 400)

    embedding = mm.embed_face(crop)
    return {
        "embeddings": embedding.tolist(),
        "embedding_dim": int(embedding.shape[0]),
        "model_used": mm.recognizer_backend,
        "processing_time_ms": round((time.time() - start) * 1000.0, 2),
    }


# ---------------------------------------------------------------------------
# Enrollment helpers
# ---------------------------------------------------------------------------
def _select_diverse_references(candidates: list, target_count: int = 3) -> tuple:
    """Pick the best ``target_count`` frames from a list of candidates.

    Strategy:
      1. Highest-quality (confidence x sqrt(area)) wins the first slot.
      2. Subsequent picks maximize the minimum cosine distance to the
         already-picked set (farthest-point sampling).
    """
    if not candidates:
        return [], {}

    def quality(c):
        b = c["face_box"]
        area = max(1, b["w"] * b["h"])
        return float(b.get("confidence", 0.0)) * (area ** 0.5)

    remaining = list(candidates)
    remaining.sort(key=quality, reverse=True)
    picked = [remaining.pop(0)]

    while len(picked) < target_count and remaining:
        picked_embs = np.stack([p["embedding"] for p in picked], axis=0)
        best_idx, best_dist = None, -1.0
        for i, cand in enumerate(remaining):
            sims = picked_embs @ cand["embedding"]
            min_dist = float(1.0 - np.max(sims))
            if min_dist > best_dist:
                best_dist, best_idx = min_dist, i
        picked.append(remaining.pop(best_idx))

    boxes = [p["face_box"] for p in picked]
    avg_w = sum(b["w"] for b in boxes) / len(boxes)
    avg_h = sum(b["h"] for b in boxes) / len(boxes)
    avg_conf = sum(float(b.get("confidence", 0.0)) for b in boxes) / len(boxes)

    if len(picked) >= 2:
        embs = np.stack([p["embedding"] for p in picked], axis=0)
        sims = embs @ embs.T
        np.fill_diagonal(sims, -1.0)
        min_div = float(1.0 - np.max(sims))
    else:
        min_div = None

    metrics = {
        "avg_face_w": round(avg_w, 1),
        "avg_face_h": round(avg_h, 1),
        "avg_confidence": round(avg_conf, 4),
        "min_pairwise_diversity": (None if min_div is None else round(min_div, 4)),
    }
    return picked, metrics


def _embed_images_for_enrollment(
    images_b64: list, min_confidence: float = 0.5,
) -> tuple:
    """Detect + crop + embed each base64 image. Returns (embeddings, boxes,
    skipped) where skipped is a list of per-image error reasons."""
    mm = _model_manager()
    embeddings, boxes, skipped = [], [], []
    for idx, b64 in enumerate(images_b64):
        try:
            frame = decode_base64_image(b64)
        except ValueError as exc:
            skipped.append({"index": idx, "reason": str(exc)})
            continue
        faces = _detect(frame, confidence_threshold=0.8)
        if not faces:
            skipped.append({"index": idx, "reason": "no_face_detected"})
            continue
        crop = _crop_first_face(frame, faces)
        if crop is None:
            skipped.append({"index": idx, "reason": "invalid_face_crop"})
            continue
        primary = _select_primary_face(faces) or {}
        if primary.get("confidence", 0.0) < min_confidence:
            skipped.append({"index": idx, "reason": "low_confidence"})
            continue
        embeddings.append(mm.embed_face(crop))
        boxes.append({
            "w": int(primary.get("w", crop.shape[1])),
            "h": int(primary.get("h", crop.shape[0])),
            "confidence": float(primary.get("confidence", 0.0)),
        })
    return embeddings, boxes, skipped


# ---------------------------------------------------------------------------
# Enrollment endpoints
# ---------------------------------------------------------------------------
@moodle_api.post(
    "/enroll/face",
    status_code=status.HTTP_201_CREATED,
    tags=["Enrollment"],
    summary="Add 1-5 reference photos for a user",
)
def enroll_face(body: EnrollFaceRequest):
    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return _err(
            "Face recognition model not loaded on this server.",
            503, details=_backend_label(),
        )
    if _enrollment_store is None:
        return _err("Enrollment store unavailable.", 503)

    try:
        user_id = validate_user_id(body.user_id)
    except EnrollmentError as exc:
        return _err(str(exc), 400)

    embeddings, boxes, skipped = _embed_images_for_enrollment(body.images)
    if not embeddings:
        return _err(
            "No usable face found in any provided image.",
            400, skipped=skipped,
        )

    try:
        result = _enrollment_store.enroll(
            user_id=user_id,
            embeddings=embeddings,
            face_boxes=boxes,
            model_backend=mm.recognizer_backend,
        )
    except EnrollmentError as exc:
        return _err(str(exc), 409)

    return JSONResponse(
        status_code=201,
        content={
            **result,
            "skipped": skipped,
            "model_backend": mm.recognizer_backend,
        },
    )


@moodle_api.post(
    "/enroll/face/guided",
    status_code=status.HTTP_201_CREATED,
    tags=["Enrollment"],
    summary="Guided enrollment from a 5-20 frame registration clip",
)
def enroll_face_guided(body: EnrollFaceGuidedRequest):
    """Submit 5-20 frames from a single supervised registration clip; the
    server filters, scores, and picks the best (and most varied)
    ``target_count`` frames automatically."""
    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return _err(
            "Face recognition model not loaded on this server.",
            503, details=_backend_label(),
        )
    if _enrollment_store is None:
        return _err("Enrollment store unavailable.", 503)

    try:
        user_id = validate_user_id(body.user_id)
    except EnrollmentError as exc:
        return _err(str(exc), 400)

    embeddings, boxes, skipped = _embed_images_for_enrollment(
        body.frames, min_confidence=0.7,
    )
    if not embeddings:
        return _err(
            "No usable face found in any submitted frame.",
            400, skipped=skipped, received_frames=len(body.frames),
        )

    candidates = [
        {"embedding": emb, "face_box": box, "index": i}
        for i, (emb, box) in enumerate(zip(embeddings, boxes))
    ]
    picked, metrics = _select_diverse_references(candidates, body.target_count)

    if body.replace_existing:
        _enrollment_store.delete_user(user_id)

    try:
        result = _enrollment_store.enroll(
            user_id=user_id,
            embeddings=[p["embedding"] for p in picked],
            face_boxes=[p["face_box"] for p in picked],
            model_backend=mm.recognizer_backend,
        )
    except EnrollmentError as exc:
        return _err(str(exc), 409)

    logger.info(
        "enroll_guided[user_id=%s]: kept %d of %d viable frames (received=%d, "
        "skipped=%d) -- selection_div=%s",
        user_id, len(picked), len(candidates), len(body.frames),
        len(skipped), metrics.get("min_pairwise_diversity"),
    )
    return JSONResponse(
        status_code=201,
        content={
            **result,
            "received_frames": len(body.frames),
            "selected_from": len(candidates),
            "selection_strategy": "diverse_top_quality",
            "selection_metrics": metrics,
            "skipped": skipped,
            "replaced_existing": body.replace_existing,
            "model_backend": mm.recognizer_backend,
        },
    )


@moodle_api.get(
    "/enroll/face/{user_id}",
    tags=["Enrollment"],
    response_model=EnrollmentInfoResponse,
    summary="Get enrollment metadata for a user",
)
def get_enrollment(user_id: str):
    if _enrollment_store is None:
        return _err("Enrollment store unavailable.", 503)
    try:
        validate_user_id(user_id)
    except EnrollmentError as exc:
        return _err(str(exc), 400)

    info = _enrollment_store.get_user_info(user_id)
    if info is None:
        return _err(f"No enrollment found for user '{user_id}'.", 404)
    return info


@moodle_api.delete(
    "/enroll/face/{user_id}",
    tags=["Enrollment"],
    response_model=DeleteEnrollmentResponse,
    summary="Delete all enrolled references for a user",
)
def delete_enrollment(user_id: str):
    if _enrollment_store is None:
        return _err("Enrollment store unavailable.", 503)
    try:
        validate_user_id(user_id)
    except EnrollmentError as exc:
        return _err(str(exc), 400)

    deleted = _enrollment_store.delete_user(user_id)
    return {"user_id": user_id, "deleted": bool(deleted)}


@moodle_api.post("/batch/process", summary="Process several frames in one request")
def batch_process(body: BatchProcessRequest):
    results = []
    failed = 0
    for idx, image_b64 in enumerate(body.images):
        try:
            frame = decode_base64_image(image_b64)
            faces = _detect(frame, confidence_threshold=0.6)
            entry = {
                "index": idx,
                "face_count": len(faces),
                "status": "success",
            }
            if body.task == "behavior_analysis":
                entry.update({
                    "no_face_detected": len(faces) == 0,
                    "multiple_faces_detected": len(faces) > 1,
                })
            else:
                entry["faces"] = [
                    {"x": f["x"], "y": f["y"], "w": f["w"], "h": f["h"],
                     "confidence": f.get("confidence", 0.0)}
                    for f in faces
                ]
            results.append(entry)
        except Exception as exc:
            failed += 1
            results.append({"index": idx, "status": "failed", "error": str(exc)})

    return {
        "results": results,
        "processed_count": len(results) - failed,
        "failed_count": failed,
        "backend": _backend_label(),
    }
