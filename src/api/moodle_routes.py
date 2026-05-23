"""
Moodle-Compatible REST API Endpoints

These endpoints match the contract expected by the Moodle quizaccess plugin:
  health_check()              -> GET  /health (defined in app.py)
  detect_faces()              -> POST /detect/faces
  verify_face_match()         -> POST /verify/face
  detect_suspicious_behavior()-> POST /detect/behavior
  get_face_embeddings()       -> POST /embeddings
  batch_process_frames()      -> POST /batch/process
"""
import logging
import base64
import time
import numpy as np
import cv2
from flask import Blueprint, request, jsonify

from src.api.auth import require_api_key

logger = logging.getLogger(__name__)

moodle_api = Blueprint("moodle", __name__)

_proctoring_system = None


def set_moodle_proctoring_system(system):
    """Set the global proctoring system reference"""
    global _proctoring_system
    _proctoring_system = system


def decode_base64_image(image_base64: str) -> np.ndarray:
    """
    Decode a base64-encoded image string into an OpenCV numpy array.
    
    Handles both raw base64 and data URI format (data:image/...;base64,...).
    
    Args:
        image_base64: Base64 encoded image string
        
    Returns:
        OpenCV image (numpy array in BGR format)
        
    Raises:
        ValueError: If image cannot be decoded
    """
    try:
        # Strip data URI prefix if present
        if ',' in image_base64 and image_base64.startswith('data:'):
            image_base64 = image_base64.split(',', 1)[1]
        
        # Decode base64
        image_bytes = base64.b64decode(image_base64)
        
        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)
        
        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            raise ValueError("Failed to decode image from base64 data")
        
        return frame
    except Exception as e:
        raise ValueError(f"Invalid base64 image: {str(e)}")


def compute_face_similarity(face1_roi: np.ndarray, face2_roi: np.ndarray) -> float:
    """
    Compute similarity score between two face regions.
    
    Uses histogram comparison as a lightweight similarity metric.
    For production, replace with deep learning embeddings (FaceNet, ArcFace).
    
    Args:
        face1_roi: First face region (BGR image)
        face2_roi: Second face region (BGR image)
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        # Resize both faces to same dimensions
        target_size = (128, 128)
        face1_resized = cv2.resize(face1_roi, target_size)
        face2_resized = cv2.resize(face2_roi, target_size)
        
        # Convert to HSV for better color comparison
        face1_hsv = cv2.cvtColor(face1_resized, cv2.COLOR_BGR2HSV)
        face2_hsv = cv2.cvtColor(face2_resized, cv2.COLOR_BGR2HSV)
        
        # Calculate histograms
        h_bins, s_bins = 50, 60
        hist_size = [h_bins, s_bins]
        h_ranges = [0, 180]
        s_ranges = [0, 256]
        ranges = h_ranges + s_ranges
        channels = [0, 1]
        
        hist1 = cv2.calcHist([face1_hsv], channels, None, hist_size, ranges)
        cv2.normalize(hist1, hist1, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        hist2 = cv2.calcHist([face2_hsv], channels, None, hist_size, ranges)
        cv2.normalize(hist2, hist2, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        
        # Compare histograms (correlation method returns -1 to 1)
        score = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)
        
        # Also compute structural similarity on grayscale
        face1_gray = cv2.cvtColor(face1_resized, cv2.COLOR_BGR2GRAY)
        face2_gray = cv2.cvtColor(face2_resized, cv2.COLOR_BGR2GRAY)
        
        # Template matching as additional signal
        result = cv2.matchTemplate(face1_gray, face2_gray, cv2.TM_CCOEFF_NORMED)
        template_score = float(result[0][0])
        
        # Weighted combination
        combined_score = 0.6 * max(0, score) + 0.4 * max(0, template_score)
        
        return min(1.0, max(0.0, combined_score))
    except Exception as e:
        logger.error(f"Error computing face similarity: {e}")
        return 0.0


# ============================================================================
# Moodle-Compatible Endpoints
# ============================================================================

@moodle_api.route('/detect/faces', methods=['POST'])
@require_api_key
def detect_faces():
    """Detect faces in an image.
    ---
    tags:
      - Moodle
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image:
                type: string
                description: Base64-encoded image (raw or data URI).
              options:
                type: object
                properties:
                  confidence_threshold:
                    type: number
                    default: 0.6
                  return_landmarks:
                    type: boolean
                    default: true
    responses:
      200:
        description: Faces detected
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing 'image' field in request body"}), 400
        
        start_time = time.time()
        
        # Decode base64 image
        try:
            frame = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Get options
        options = data.get('options', {})
        confidence_threshold = options.get('confidence_threshold', 0.6)
        return_landmarks = options.get('return_landmarks', True)
        
        # Detect faces using the proctoring system
        if _proctoring_system and _proctoring_system.face_detector:
            detection_result = _proctoring_system.face_detector.detect_faces(frame)
            raw_faces = detection_result.get("faces", [])
        else:
            # Fallback: use OpenCV Haar Cascade directly
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            raw_faces = detected.tolist() if len(detected) > 0 else []
        
        # Format faces for Moodle API response
        faces = []
        for face in raw_faces:
            if isinstance(face, (list, tuple)) and len(face) >= 4:
                faces.append({
                    "x": int(face[0]),
                    "y": int(face[1]),
                    "w": int(face[2]),
                    "h": int(face[3]),
                    "confidence": confidence_threshold + 0.1  # Base confidence
                })
            elif isinstance(face, dict):
                faces.append({
                    "x": int(face.get('x', 0)),
                    "y": int(face.get('y', 0)),
                    "w": int(face.get('w', 0)),
                    "h": int(face.get('h', 0)),
                    "confidence": float(face.get('confidence', confidence_threshold))
                })
        
        # Get landmarks if requested
        landmarks = []
        if return_landmarks and _proctoring_system and _proctoring_system.eye_tracker:
            try:
                eye_result = _proctoring_system.eye_tracker.detect_eyes(frame)
                if eye_result.get("eyes_detected"):
                    landmarks = {
                        "left_eye": eye_result.get("left_eye"),
                        "right_eye": eye_result.get("right_eye"),
                    }
            except Exception as e:
                logger.debug(f"Landmark detection skipped: {e}")
        
        processing_time = (time.time() - start_time) * 1000
        
        return jsonify({
            "faces": faces,
            "face_count": len(faces),
            "landmarks": landmarks,
            "processing_time_ms": round(processing_time, 2),
        }), 200
    
    except Exception as e:
        logger.error(f"Error in /detect/faces: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@moodle_api.route('/verify/face', methods=['POST'])
@require_api_key
def verify_face():
    """Verify a current face against a reference face.
    ---
    tags:
      - Moodle
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [current_face, reference_face]
            properties:
              current_face:
                type: string
                description: Base64-encoded current capture.
              reference_face:
                type: string
                description: Base64-encoded reference image (registered face).
              options:
                type: object
                properties:
                  match_threshold:
                    type: number
                    default: 0.6
    responses:
      200:
        description: Verification result
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        if 'current_face' not in data or 'reference_face' not in data:
            return jsonify({"error": "Missing 'current_face' or 'reference_face'"}), 400
        
        start_time = time.time()
        
        # Decode both images
        try:
            current_frame = decode_base64_image(data['current_face'])
            reference_frame = decode_base64_image(data['reference_face'])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Get options
        options = data.get('options', {})
        match_threshold = options.get('match_threshold', 0.6)
        
        # Detect face in current frame
        current_faces = _detect_faces_in_frame(current_frame)
        reference_faces = _detect_faces_in_frame(reference_frame)
        
        if not current_faces:
            return jsonify({
                "is_match": False,
                "match_score": 0.0,
                "confidence": 0.0,
                "details": {"reason": "no_face_in_current_frame"},
            }), 200
        
        if not reference_faces:
            return jsonify({
                "is_match": False,
                "match_score": 0.0,
                "confidence": 0.0,
                "details": {"reason": "no_face_in_reference_frame"},
            }), 200
        
        # Extract face ROIs
        cx, cy, cw, ch = current_faces[0]
        current_face_roi = current_frame[cy:cy+ch, cx:cx+cw]
        
        rx, ry, rw, rh = reference_faces[0]
        reference_face_roi = reference_frame[ry:ry+rh, rx:rx+rw]
        
        # Compute similarity
        match_score = compute_face_similarity(current_face_roi, reference_face_roi)
        is_match = match_score >= match_threshold
        
        processing_time = (time.time() - start_time) * 1000
        
        return jsonify({
            "is_match": is_match,
            "match_score": round(match_score, 4),
            "confidence": round(match_score, 4),
            "details": {
                "method": "histogram_correlation+template_matching",
                "threshold_used": match_threshold,
                "processing_time_ms": round(processing_time, 2),
                "current_face_detected": True,
                "reference_face_detected": True,
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error in /verify/face: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@moodle_api.route('/detect/behavior', methods=['POST'])
@require_api_key
def detect_behavior():
    """Detect suspicious behavior in a frame.
    ---
    tags:
      - Moodle
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image:
                type: string
                description: Base64-encoded image.
              options:
                type: object
                properties:
                  detect_multiple_faces:
                    type: boolean
                    default: true
                  detect_eye_gaze:
                    type: boolean
                    default: true
                  detect_head_pose:
                    type: boolean
                    default: true
    responses:
      200:
        description: Behavior analysis result
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing 'image' field"}), 400
        
        start_time = time.time()
        
        # Decode image
        try:
            frame = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        options = data.get('options', {})
        
        # Initialize result
        result = {
            "multiple_faces_detected": False,
            "face_count": 0,
            "no_face_detected": False,
            "unusual_eye_gaze": False,
            "unusual_head_pose": False,
            "suspicious_indicators": [],
            "risk_level": "low",
        }
        
        # 1. Face detection
        faces = _detect_faces_in_frame(frame)
        result["face_count"] = len(faces)
        
        if len(faces) == 0:
            result["no_face_detected"] = True
            result["suspicious_indicators"].append("no_face_detected")
            result["risk_level"] = "medium"
        
        if options.get('detect_multiple_faces', True) and len(faces) > 1:
            result["multiple_faces_detected"] = True
            result["suspicious_indicators"].append(f"multiple_faces: {len(faces)}")
            result["risk_level"] = "high"
        
        # 2. Eye gaze detection
        if options.get('detect_eye_gaze', True) and len(faces) > 0:
            if _proctoring_system and _proctoring_system.eye_tracker:
                try:
                    eye_result = _proctoring_system.eye_tracker.detect_eyes(frame)
                    if eye_result.get("eyes_detected"):
                        gaze = eye_result.get("gaze_direction", "CENTER")
                        # Off-screen gaze is suspicious
                        if gaze in ["LEFT", "RIGHT", "LEFT_UP", "RIGHT_UP", "LEFT_DOWN", "RIGHT_DOWN"]:
                            result["unusual_eye_gaze"] = True
                            result["suspicious_indicators"].append(f"gaze_direction: {gaze}")
                            if result["risk_level"] == "low":
                                result["risk_level"] = "medium"
                        
                        result["gaze_direction"] = gaze
                        result["eye_aspect_ratio"] = eye_result.get("eye_aspect_ratio", 0.0)
                except Exception as e:
                    logger.debug(f"Eye gaze detection error: {e}")
        
        # 3. Head pose estimation (simplified using face position)
        if options.get('detect_head_pose', True) and len(faces) > 0:
            h, w = frame.shape[:2]
            fx, fy, fw, fh = faces[0]
            face_center_x = fx + fw / 2
            face_center_y = fy + fh / 2
            
            # Check if face is significantly off-center (possible head turn)
            x_ratio = face_center_x / w
            y_ratio = face_center_y / h
            
            if x_ratio < 0.25 or x_ratio > 0.75:
                result["unusual_head_pose"] = True
                result["suspicious_indicators"].append("head_turned_sideways")
                if result["risk_level"] == "low":
                    result["risk_level"] = "medium"
            
            if y_ratio < 0.2 or y_ratio > 0.8:
                result["unusual_head_pose"] = True
                result["suspicious_indicators"].append("head_tilted")
                if result["risk_level"] == "low":
                    result["risk_level"] = "medium"
        
        processing_time = (time.time() - start_time) * 1000
        result["processing_time_ms"] = round(processing_time, 2)
        
        return jsonify(result), 200
    
    except Exception as e:
        logger.error(f"Error in /detect/behavior: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@moodle_api.route('/embeddings', methods=['POST'])
@require_api_key
def get_embeddings():
    """Compute face embeddings.
    ---
    tags:
      - Moodle
    security:
      - BearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            required: [image]
            properties:
              image:
                type: string
                description: Base64-encoded image.
    responses:
      200:
        description: Embeddings vector
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json()
        if not data or 'image' not in data:
            return jsonify({"error": "Missing 'image' field"}), 400
        
        # Decode image
        try:
            frame = decode_base64_image(data['image'])
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        
        # Detect face
        faces = _detect_faces_in_frame(frame)
        
        if not faces:
            return jsonify({
                "embeddings": [],
                "embedding_dim": 0,
                "model_used": "none",
                "error": "No face detected in image"
            }), 200
        
        # Extract face ROI
        x, y, w, h = faces[0]
        face_roi = frame[y:y+h, x:x+w]
        
        # Generate embedding using histogram (lightweight)
        face_resized = cv2.resize(face_roi, (128, 128))
        face_gray = cv2.cvtColor(face_resized, cv2.COLOR_BGR2GRAY)
        
        # Create a simple embedding from histogram + pixel features
        hist = cv2.calcHist([face_gray], [0], None, [64], [0, 256])
        cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        embedding = hist.flatten().tolist()
        
        # Add spatial features
        face_small = cv2.resize(face_gray, (8, 8)).flatten()
        face_small = (face_small / 255.0).tolist()
        embedding.extend(face_small)
        
        return jsonify({
            "embeddings": embedding,
            "embedding_dim": len(embedding),
            "model_used": "opencv_histogram_spatial",
        }), 200
    
    except Exception as e:
        logger.error(f"Error in /embeddings: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


@moodle_api.route('/batch/process', methods=['POST'])
@require_api_key
def batch_process():
    """Process a batch of frames.
    ---
    tags:
      - Moodle
    security:
      - BearerAuth: []
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
                items:
                  type: string
                description: List of base64-encoded images.
              task:
                type: string
                enum: [face_detection, behavior_analysis]
                default: face_detection
    responses:
      200:
        description: Batch results
      400:
        description: Invalid request
      401:
        description: Unauthorized
    """
    try:
        data = request.get_json()
        if not data or 'images' not in data:
            return jsonify({"error": "Missing 'images' field"}), 400
        
        images = data['images']
        task = data.get('task', 'face_detection')
        options = data.get('options', {})
        
        results = []
        failed_count = 0
        
        for i, image_base64 in enumerate(images):
            try:
                frame = decode_base64_image(image_base64)
                
                if task == 'face_detection':
                    faces = _detect_faces_in_frame(frame)
                    results.append({
                        "index": i,
                        "faces": [{"x": f[0], "y": f[1], "w": f[2], "h": f[3]} for f in faces],
                        "face_count": len(faces),
                        "status": "success"
                    })
                elif task == 'behavior_analysis':
                    faces = _detect_faces_in_frame(frame)
                    results.append({
                        "index": i,
                        "face_count": len(faces),
                        "no_face_detected": len(faces) == 0,
                        "multiple_faces_detected": len(faces) > 1,
                        "status": "success"
                    })
                else:
                    results.append({
                        "index": i,
                        "status": "success",
                        "message": f"Task '{task}' processed"
                    })
            except Exception as e:
                failed_count += 1
                results.append({
                    "index": i,
                    "status": "failed",
                    "error": str(e)
                })
        
        return jsonify({
            "results": results,
            "processed_count": len(results) - failed_count,
            "failed_count": failed_count,
        }), 200
    
    except Exception as e:
        logger.error(f"Error in /batch/process: {e}")
        return jsonify({"error": str(e), "status": "error"}), 500


# ============================================================================
# Helper Functions
# ============================================================================

def _detect_faces_in_frame(frame: np.ndarray) -> list:
    """
    Detect faces in a frame using the proctoring system or fallback.
    
    Returns list of [x, y, w, h] tuples.
    """
    try:
        if _proctoring_system and _proctoring_system.face_detector:
            detection = _proctoring_system.face_detector.detect_faces(frame)
            raw_faces = detection.get("faces", [])
        else:
            cascade = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
            raw_faces = detected.tolist() if len(detected) > 0 else []
        
        # Normalize to list of [x, y, w, h]
        faces = []
        for face in raw_faces:
            if isinstance(face, (list, tuple)) and len(face) >= 4:
                faces.append([int(face[0]), int(face[1]), int(face[2]), int(face[3])])
            elif isinstance(face, dict):
                faces.append([
                    int(face.get('x', 0)),
                    int(face.get('y', 0)),
                    int(face.get('w', 0)),
                    int(face.get('h', 0))
                ])
        return faces
    except Exception as e:
        logger.error(f"Face detection error: {e}")
        return []
