"""
Moodle-Compatible REST API Endpoints.

These endpoints sit behind Bearer-token auth and delegate to the real
trained models loaded by :class:`src.core.model_manager.ModelManager`:

* RetinaFace (MobileNet0.25) — face detection + landmarks
* ArcFace (ResNet50, 512-d embeddings) — face verification + identification
"""
from __future__ import annotations

import base64
import logging
import time
from typing import List, Optional

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

from src.api.auth import require_api_key
from src.services.face_enrollment import (
    EnrollmentError,
    FaceEnrollmentStore,
    validate_user_id,
)

logger = logging.getLogger(__name__)

moodle_api = Blueprint("moodle", __name__)
_proctoring_system = None
_enrollment_store: "FaceEnrollmentStore | None" = None


def set_moodle_proctoring_system(system) -> None:
    """Set the global proctoring system reference."""
    global _proctoring_system
    _proctoring_system = system


def set_enrollment_store(store: FaceEnrollmentStore) -> None:
    """Set the global enrollment store reference."""
    global _enrollment_store
    _enrollment_store = store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _model_manager():
    return getattr(_proctoring_system, "model_manager", None)


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
    """Pick the most likely 'student' face.

    RetinaFace can fire on small high-confidence regions (eye corners,
    background artifacts). For verification we want the *biggest* face that
    is also above a sensible confidence — that's almost certainly the person
    in front of the camera.
    """
    if not faces:
        return None
    viable = [
        f for f in faces
        if min(f["w"], f["h"]) >= min_side
        and f.get("confidence", 0.0) >= min_confidence
    ]
    pool = viable or faces  # fall back if nothing meets the bar
    return max(pool, key=lambda f: f["w"] * f["h"])


def _crop_first_face(
    frame: np.ndarray, faces: list, margin: float = 0.15,
) -> Optional[np.ndarray]:
    """Return the BGR crop of the primary face, with a small context margin.

    ``margin`` adds ``margin * face_size`` pixels on every side. ArcFace was
    trained on face crops with a little context around the head, so a tight
    bbox can hurt accuracy.
    """
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


# ===========================================================================
# Endpoints
# ===========================================================================
@moodle_api.route("/detect/faces", methods=["POST"])
@require_api_key
def detect_faces():
    """Detect faces in an image.
    ---
    tags: [Moodle]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image: {type: string, description: "Base64 image (raw or data URI)."}
              options:
                type: object
                properties:
                  confidence_threshold: {type: number, default: 0.6}
                  return_landmarks: {type: boolean, default: true}
    responses:
      200: {description: Faces detected}
      400: {description: Invalid request}
      401: {description: Unauthorized}
    """
    data = request.get_json(silent=True) or {}
    if "image" not in data:
        return jsonify({"error": "Missing 'image' field in request body"}), 400

    try:
        frame = decode_base64_image(data["image"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    options = data.get("options") or {}
    conf = float(options.get("confidence_threshold", 0.6))
    return_landmarks = bool(options.get("return_landmarks", True))

    start = time.time()
    faces = _detect(frame, confidence_threshold=conf)

    response_faces: List[dict] = []
    landmarks_collected: List[dict] = []
    for f in faces:
        item = {
            "x": int(f["x"]), "y": int(f["y"]),
            "w": int(f["w"]), "h": int(f["h"]),
            "confidence": float(f.get("confidence", 0.0)),
        }
        if return_landmarks and f.get("landmarks"):
            item["landmarks"] = f["landmarks"]
            landmarks_collected.append(f["landmarks"])
        response_faces.append(item)

    return jsonify({
        "faces": response_faces,
        "face_count": len(response_faces),
        "landmarks": landmarks_collected,
        "processing_time_ms": round((time.time() - start) * 1000.0, 2),
        "backend": _backend_label(),
    }), 200


@moodle_api.route("/verify/face", methods=["POST"])
@require_api_key
def verify_face():
    """Verify a current face against either a single reference image *or*
    against all references previously enrolled for ``user_id``.

    Exactly one of ``reference_face`` / ``user_id`` must be provided.

    ---
    tags: [Moodle]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [current_face]
            properties:
              current_face: {type: string, description: "Base64 current capture."}
              reference_face:
                type: string
                description: "Base64 reference image (single-reference mode)."
              user_id:
                type: string
                description: "User id to look up previously enrolled references."
              options:
                type: object
                properties:
                  match_threshold: {type: number}
                  return_embeddings: {type: boolean, default: false}
    responses:
      200: {description: Verification result}
      400: {description: Invalid request}
      401: {description: Unauthorized}
      404: {description: user_id has no enrolled references}
      503: {description: Recognition model not loaded}
    """
    data = request.get_json(silent=True) or {}
    if "current_face" not in data:
        return jsonify({"error": "Missing 'current_face' field"}), 400

    has_reference = "reference_face" in data
    has_user_id = "user_id" in data
    if has_reference == has_user_id:
        return jsonify({
            "error": "Provide exactly one of 'reference_face' or 'user_id'."
        }), 400

    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return jsonify({
            "error": "Face recognition model not loaded on this server.",
            "details": _backend_label(),
        }), 503

    try:
        current_frame = decode_base64_image(data["current_face"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    options = data.get("options") or {}
    threshold = float(options.get("match_threshold", mm.face_recognizer.match_threshold))
    return_embeddings = bool(options.get("return_embeddings", False))

    start = time.time()

    # ---- detect and crop current face ----
    cur_faces = _detect(current_frame, confidence_threshold=0.8)
    if not cur_faces:
        return jsonify({
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "no_face_in_current_frame"},
        }), 200
    cur_crop = _crop_first_face(current_frame, cur_faces)
    if cur_crop is None:
        return jsonify({
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "invalid_face_crop"},
        }), 200

    emb_cur = mm.embed_face(cur_crop)

    # ---- branch: stored references vs single reference ----
    if has_user_id:
        try:
            user_id = validate_user_id(data["user_id"])
        except EnrollmentError as exc:
            return jsonify({"error": str(exc)}), 400
        if _enrollment_store is None:
            return jsonify({"error": "Enrollment store unavailable."}), 503

        ref_ids, ref_embs = _enrollment_store.get_embeddings(user_id)
        if ref_embs.shape[0] == 0:
            return jsonify({
                "error": f"No enrolled references for user '{user_id}'.",
                "user_id": user_id,
            }), 404

        scores = ref_embs @ emb_cur  # both L2-normalized -> cosines, shape [N]
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
        return jsonify(payload), 200

    # ---- single-reference (legacy) mode ----
    try:
        reference_frame = decode_base64_image(data["reference_face"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    ref_faces = _detect(reference_frame, confidence_threshold=0.8)
    logger.info(
        "verify_face: detected %d face(s) in current, %d in reference",
        len(cur_faces), len(ref_faces),
    )
    if not ref_faces:
        return jsonify({
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "no_face_in_reference_frame"},
        }), 200

    ref_crop = _crop_first_face(reference_frame, ref_faces)
    if ref_crop is None:
        return jsonify({
            "is_match": False, "match_score": 0.0, "confidence": 0.0,
            "details": {"reason": "invalid_face_crop"},
        }), 200

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
    return jsonify(payload), 200


@moodle_api.route("/detect/behavior", methods=["POST"])
@require_api_key
def detect_behavior():
    """Detect suspicious behavior in a frame.
    ---
    tags: [Moodle]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image: {type: string}
              options:
                type: object
                properties:
                  detect_multiple_faces: {type: boolean, default: true}
                  detect_eye_gaze: {type: boolean, default: true}
                  detect_head_pose: {type: boolean, default: true}
    responses:
      200: {description: Behavior analysis result}
      400: {description: Invalid request}
      401: {description: Unauthorized}
    """
    data = request.get_json(silent=True) or {}
    if "image" not in data:
        return jsonify({"error": "Missing 'image' field"}), 400

    try:
        frame = decode_base64_image(data["image"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    options = data.get("options") or {}
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

    if options.get("detect_multiple_faces", True) and len(faces) > 1:
        result["multiple_faces_detected"] = True
        result["suspicious_indicators"].append(f"multiple_faces: {len(faces)}")
        result["risk_level"] = "high"

    # Head pose (rough): does the face sit far from the frame center?
    if options.get("detect_head_pose", True) and faces:
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

    # Eye gaze (rough): use the RetinaFace landmarks if available.
    if options.get("detect_eye_gaze", True) and faces:
        best = max(faces, key=lambda f: f.get("confidence", 0.0))
        lm = best.get("landmarks") or {}
        le, re_, nose = lm.get("left_eye"), lm.get("right_eye"), lm.get("nose")
        if le and re_ and nose:
            eye_mid_x = (le[0] + re_[0]) / 2
            eye_span = max(1.0, abs(re_[0] - le[0]))
            offset = (nose[0] - eye_mid_x) / eye_span
            if abs(offset) > 0.25:  # nose far from eye midpoint -> looking sideways
                result["unusual_eye_gaze"] = True
                result["suspicious_indicators"].append(
                    f"gaze_offset:{offset:+.2f}"
                )
                if result["risk_level"] == "low":
                    result["risk_level"] = "medium"
            result["gaze_offset"] = round(offset, 3)

    result["processing_time_ms"] = round((time.time() - start) * 1000.0, 2)
    result["backend"] = _backend_label()
    return jsonify(result), 200


@moodle_api.route("/embeddings", methods=["POST"])
@require_api_key
def get_embeddings():
    """Compute a 512-d ArcFace face embedding.
    ---
    tags: [Moodle]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image: {type: string}
    responses:
      200: {description: Embeddings vector}
      400: {description: Invalid request}
      401: {description: Unauthorized}
      503: {description: Recognition model not loaded}
    """
    data = request.get_json(silent=True) or {}
    if "image" not in data:
        return jsonify({"error": "Missing 'image' field"}), 400

    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return jsonify({
            "error": "Face recognition model not loaded on this server.",
            "details": _backend_label(),
        }), 503

    try:
        frame = decode_base64_image(data["image"])
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    start = time.time()
    faces = _detect(frame, confidence_threshold=0.8)
    if not faces:
        return jsonify({
            "embeddings": [], "embedding_dim": 0,
            "model_used": mm.recognizer_backend,
            "error": "No face detected in image",
        }), 200

    crop = _crop_first_face(frame, faces)
    if crop is None:
        return jsonify({"error": "Invalid face crop"}), 400

    embedding = mm.embed_face(crop)
    return jsonify({
        "embeddings": embedding.tolist(),
        "embedding_dim": int(embedding.shape[0]),
        "model_used": mm.recognizer_backend,
        "processing_time_ms": round((time.time() - start) * 1000.0, 2),
    }), 200


# ---------------------------------------------------------------------------
# Enrollment
# ---------------------------------------------------------------------------
def _select_diverse_references(
    candidates: list, target_count: int = 3,
) -> tuple:
    """Pick the best ``target_count`` frames from a list of candidates.

    Each candidate is a dict with keys ``embedding``, ``face_box``, ``index``.
    Strategy:
      1. Highest-quality (confidence x sqrt(area)) wins the first slot.
      2. Subsequent picks maximize the minimum cosine distance to the
         already-picked set (farthest-point sampling). This gives us frames
         that cover varied head angles, not three near-identical ones.

    Returns ``(picked, metrics)`` where ``picked`` is the chosen list
    (preserving input order metadata) and ``metrics`` is a small dict
    summarizing the selection quality.
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
        # Distance from each remaining candidate to the closest already-picked one.
        # Embeddings are L2-normalized -> cosine_similarity = a . b, distance = 1 - a . b.
        picked_embs = np.stack([p["embedding"] for p in picked], axis=0)
        best_idx, best_dist = None, -1.0
        for i, cand in enumerate(remaining):
            sims = picked_embs @ cand["embedding"]
            min_dist = float(1.0 - np.max(sims))
            if min_dist > best_dist:
                best_dist, best_idx = min_dist, i
        picked.append(remaining.pop(best_idx))

    # Summary metrics for the response.
    boxes = [p["face_box"] for p in picked]
    avg_w = sum(b["w"] for b in boxes) / len(boxes)
    avg_h = sum(b["h"] for b in boxes) / len(boxes)
    avg_conf = sum(float(b.get("confidence", 0.0)) for b in boxes) / len(boxes)

    if len(picked) >= 2:
        embs = np.stack([p["embedding"] for p in picked], axis=0)
        sims = embs @ embs.T
        np.fill_diagonal(sims, -1.0)  # ignore self-similarity
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


@moodle_api.route("/enroll/face", methods=["POST"])
@require_api_key
def enroll_face():
    """Add one or more reference photos for a user.
    ---
    tags: [Enrollment]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [user_id, images]
            properties:
              user_id:
                type: string
                description: "Up to 64 chars, letters/digits/underscore/dash."
              images:
                type: array
                items: {type: string}
                minItems: 1
                maxItems: 5
                description: "Base64-encoded face photos."
    responses:
      201: {description: References enrolled}
      400: {description: Invalid request}
      401: {description: Unauthorized}
      409: {description: Per-user reference limit would be exceeded}
      503: {description: Recognition model not loaded}
    """
    data = request.get_json(silent=True) or {}
    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return jsonify({
            "error": "Face recognition model not loaded on this server.",
            "details": _backend_label(),
        }), 503
    if _enrollment_store is None:
        return jsonify({"error": "Enrollment store unavailable."}), 503

    try:
        user_id = validate_user_id(data.get("user_id", ""))
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 400

    images = data.get("images") or []
    if not isinstance(images, list) or not images:
        return jsonify({"error": "'images' must be a non-empty list"}), 400
    if len(images) > 5:
        return jsonify({"error": "At most 5 images per enroll request"}), 400

    embeddings, boxes, skipped = _embed_images_for_enrollment(images)
    if not embeddings:
        return jsonify({
            "error": "No usable face found in any provided image.",
            "skipped": skipped,
        }), 400

    try:
        result = _enrollment_store.enroll(
            user_id=user_id,
            embeddings=embeddings,
            face_boxes=boxes,
            model_backend=mm.recognizer_backend,
        )
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 409

    return jsonify({
        **result,
        "skipped": skipped,
        "model_backend": mm.recognizer_backend,
    }), 201


@moodle_api.route("/enroll/face/<user_id>", methods=["GET"])
@require_api_key
def get_enrollment(user_id: str):
    """Get enrollment metadata for a user (never returns embedding values).
    ---
    tags: [Enrollment]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: user_id, required: true, schema: {type: string}}
    responses:
      200: {description: Enrollment metadata}
      400: {description: Invalid user_id}
      401: {description: Unauthorized}
      404: {description: User not enrolled}
    """
    if _enrollment_store is None:
        return jsonify({"error": "Enrollment store unavailable."}), 503
    try:
        validate_user_id(user_id)
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 400

    info = _enrollment_store.get_user_info(user_id)
    if info is None:
        return jsonify({"error": f"No enrollment found for user '{user_id}'."}), 404
    return jsonify(info), 200


@moodle_api.route("/enroll/face/guided", methods=["POST"])
@require_api_key
def enroll_face_guided():
    """Guided enrollment: submit 5-20 frames from a single supervised
    registration session; the server picks the best (and most varied)
    ``target_count`` frames and enrolls them.

    Intended use: a short webcam clip at the start of a course/semester.
    The caller (frontend / Moodle plugin) captures ~5 seconds of frames and
    sends them all at once. The backend handles selection so the caller does
    not have to.

    ---
    tags: [Enrollment]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [user_id, frames]
            properties:
              user_id:
                type: string
                description: "Up to 64 chars, letters/digits/underscore/dash."
              frames:
                type: array
                items: {type: string}
                minItems: 5
                maxItems: 20
                description: "Base64-encoded frames from the registration clip."
              target_count:
                type: integer
                default: 3
                minimum: 1
                maximum: 5
              replace_existing:
                type: boolean
                default: false
                description:
                  "If true, wipe any existing references for this user before
                   enrolling. Use this for a fresh re-enrollment."
    responses:
      201: {description: References enrolled}
      400: {description: Invalid request or no usable frames}
      401: {description: Unauthorized}
      409: {description: Per-user reference limit would be exceeded}
      503: {description: Recognition model not loaded}
    """
    data = request.get_json(silent=True) or {}
    mm = _model_manager()
    if mm is None or not mm.recognition_available:
        return jsonify({
            "error": "Face recognition model not loaded on this server.",
            "details": _backend_label(),
        }), 503
    if _enrollment_store is None:
        return jsonify({"error": "Enrollment store unavailable."}), 503

    try:
        user_id = validate_user_id(data.get("user_id", ""))
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 400

    frames = data.get("frames") or []
    if not isinstance(frames, list) or not (5 <= len(frames) <= 20):
        return jsonify({
            "error": "'frames' must be a list of 5 to 20 base64 images.",
        }), 400

    target_count = int(data.get("target_count", 3))
    if not 1 <= target_count <= 5:
        return jsonify({"error": "'target_count' must be 1..5"}), 400

    replace_existing = bool(data.get("replace_existing", False))

    # ---- detect + embed every submitted frame ----
    embeddings, boxes, skipped = _embed_images_for_enrollment(
        frames, min_confidence=0.7,
    )
    if not embeddings:
        return jsonify({
            "error": "No usable face found in any submitted frame.",
            "skipped": skipped,
            "received_frames": len(frames),
        }), 400

    candidates = [
        {"embedding": emb, "face_box": box, "index": i}
        for i, (emb, box) in enumerate(zip(embeddings, boxes))
    ]
    picked, metrics = _select_diverse_references(candidates, target_count)

    # ---- optionally wipe the previous enrollment ----
    if replace_existing:
        _enrollment_store.delete_user(user_id)

    try:
        result = _enrollment_store.enroll(
            user_id=user_id,
            embeddings=[p["embedding"] for p in picked],
            face_boxes=[p["face_box"] for p in picked],
            model_backend=mm.recognizer_backend,
        )
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 409

    logger.info(
        "enroll_guided[user_id=%s]: kept %d of %d viable frames (received=%d, "
        "skipped=%d) — selection_div=%s",
        user_id, len(picked), len(candidates), len(frames),
        len(skipped), metrics.get("min_pairwise_diversity"),
    )
    return jsonify({
        **result,
        "received_frames": len(frames),
        "selected_from": len(candidates),
        "selection_strategy": "diverse_top_quality",
        "selection_metrics": metrics,
        "skipped": skipped,
        "replaced_existing": replace_existing,
        "model_backend": mm.recognizer_backend,
    }), 201


@moodle_api.route("/enroll/face/<user_id>", methods=["DELETE"])
@require_api_key
def delete_enrollment(user_id: str):
    """Delete all enrolled references for a user.
    ---
    tags: [Enrollment]
    security: [{BearerAuth: []}]
    parameters:
      - {in: path, name: user_id, required: true, schema: {type: string}}
    responses:
      200: {description: Enrollment deleted (or did not exist)}
      400: {description: Invalid user_id}
      401: {description: Unauthorized}
    """
    if _enrollment_store is None:
        return jsonify({"error": "Enrollment store unavailable."}), 503
    try:
        validate_user_id(user_id)
    except EnrollmentError as exc:
        return jsonify({"error": str(exc)}), 400

    deleted = _enrollment_store.delete_user(user_id)
    return jsonify({"user_id": user_id, "deleted": bool(deleted)}), 200


@moodle_api.route("/batch/process", methods=["POST"])
@require_api_key
def batch_process():
    """Process several frames in one request.
    ---
    tags: [Moodle]
    security: [{BearerAuth: []}]
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [images]
            properties:
              images:
                type: array
                items: {type: string}
                description: List of base64 images.
              task:
                type: string
                enum: [face_detection, behavior_analysis]
                default: face_detection
    responses:
      200: {description: Batch results}
      400: {description: Invalid request}
      401: {description: Unauthorized}
    """
    data = request.get_json(silent=True) or {}
    if "images" not in data:
        return jsonify({"error": "Missing 'images' field"}), 400

    images = data["images"]
    task = data.get("task", "face_detection")
    results = []
    failed = 0

    for idx, image_b64 in enumerate(images):
        try:
            frame = decode_base64_image(image_b64)
            faces = _detect(frame, confidence_threshold=0.6)
            entry = {
                "index": idx,
                "face_count": len(faces),
                "status": "success",
            }
            if task == "behavior_analysis":
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

    return jsonify({
        "results": results,
        "processed_count": len(results) - failed,
        "failed_count": failed,
        "backend": _backend_label(),
    }), 200
