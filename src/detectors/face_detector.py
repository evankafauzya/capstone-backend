"""
Face Detection Module
Detects faces in frames and provides warnings for missing or multiple faces
"""
import logging
import numpy as np
import cv2
from typing import List, Dict

logger = logging.getLogger(__name__)


class FaceDetector:
    """Handles face detection and multiple face warnings"""
    
    def __init__(self, model_manager, max_faces: int = 1, confidence_threshold: float = 0.5):
        """
        Initialize Face Detector
        
        Args:
            model_manager: Model manager instance
            max_faces: Maximum allowed faces in frame (default: 1)
            confidence_threshold: Confidence threshold for detection
        """
        self.model_manager = model_manager
        self.max_faces = max_faces
        self.confidence_threshold = confidence_threshold
        self.face_detection_history = []
        self.consecutive_no_face_count = 0
    
    def detect_faces(self, frame: np.ndarray) -> Dict:
        """
        Detect faces in frame
        
        Args:
            frame: Input frame from webcam
            
        Returns:
            Dictionary containing:
            - faces: List of face bounding boxes
            - face_count: Number of faces detected
            - warnings: List of warnings
            - is_valid: Boolean indicating valid detection
        """
        try:
            faces = self.model_manager.detect_faces(frame, self.confidence_threshold)
            
            result = {
                "faces": faces,
                "face_count": len(faces),
                "warnings": [],
                "is_valid": True,
                "confidence": self.confidence_threshold
            }
            
            # Check for no faces
            if len(faces) == 0:
                self.consecutive_no_face_count += 1
                result["warnings"].append("WARNING: Face not detected in frame!")
                result["is_valid"] = False
                logger.warning(f"No face detected (count: {self.consecutive_no_face_count})")
            else:
                self.consecutive_no_face_count = 0
            
            # Check for multiple faces
            if len(faces) > self.max_faces:
                result["warnings"].append(
                    f"WARNING: Multiple faces detected ({len(faces)}) in frame! "
                    f"Expected maximum {self.max_faces}."
                )
                result["is_valid"] = False
                logger.warning(f"Multiple faces detected: {len(faces)}")
            
            # Store in history
            self.face_detection_history.append({
                "face_count": len(faces),
                "is_valid": result["is_valid"],
                "warnings": result["warnings"]
            })
            
            # Keep history size manageable
            if len(self.face_detection_history) > 1000:
                self.face_detection_history = self.face_detection_history[-500:]
            
            return result
        
        except Exception as e:
            logger.error(f"Error in face detection: {e}")
            return {
                "faces": [],
                "face_count": 0,
                "warnings": [f"ERROR: Detection failed - {str(e)}"],
                "is_valid": False,
                "confidence": 0.0
            }
    
    def draw_face_boxes(self, frame: np.ndarray, faces: List) -> np.ndarray:
        """
        Draw bounding boxes around detected faces.

        Args:
            frame: Input frame.
            faces: List of face dicts with keys x, y, w, h, confidence,
                landmarks (as produced by ``ModelManager.detect_faces``).
                Tuples ``(x, y, w, h)`` are also accepted for backward
                compatibility.
        """
        output_frame = frame.copy()

        for idx, face in enumerate(faces):
            if isinstance(face, dict):
                x, y, w, h = face["x"], face["y"], face["w"], face["h"]
                conf = face.get("confidence")
            else:
                x, y, w, h = face[0], face[1], face[2], face[3]
                conf = None

            color = (0, 255, 0) if len(faces) <= self.max_faces else (0, 0, 255)
            cv2.rectangle(output_frame, (x, y), (x + w, y + h), color, 2)
            label = f"Face {idx + 1}"
            if conf is not None:
                label += f" {conf:.2f}"
            cv2.putText(
                output_frame, label, (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
            )
        
        # Add warning text if multiple faces or no face
        if len(faces) > self.max_faces:
            cv2.putText(
                output_frame,
                f"WARNING: {len(faces)} faces detected!",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )
        elif len(faces) == 0:
            cv2.putText(
                output_frame,
                "WARNING: No face detected!",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (0, 0, 255),
                2
            )
        
        return output_frame
    
    def get_detection_statistics(self) -> Dict:
        """Get detection statistics from history"""
        if not self.face_detection_history:
            return {
                "total_frames": 0,
                "valid_detections": 0,
                "invalid_detections": 0,
                "accuracy": 0.0,
                "consecutive_no_face": self.consecutive_no_face_count
            }
        
        total = len(self.face_detection_history)
        valid = sum(1 for h in self.face_detection_history if h["is_valid"])
        invalid = total - valid
        
        return {
            "total_frames": total,
            "valid_detections": valid,
            "invalid_detections": invalid,
            "accuracy": (valid / total * 100) if total > 0 else 0.0,
            "consecutive_no_face": self.consecutive_no_face_count
        }
    
    def reset_history(self):
        """Reset detection history"""
        self.face_detection_history = []
        self.consecutive_no_face_count = 0
        logger.info("Face detection history reset")
