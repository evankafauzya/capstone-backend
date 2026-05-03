"""
Eye Tracking Module
Detects eye movement and tracks gaze direction
"""
import logging
import numpy as np
import cv2
import mediapipe as mp
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class EyeTracker:
    """Handles eye detection and movement tracking"""
    
    def __init__(self, movement_threshold: float = 0.3, aspect_ratio_threshold: float = 0.2):
        """
        Initialize Eye Tracker
        
        Args:
            movement_threshold: Threshold for detecting unusual eye movement
            aspect_ratio_threshold: Threshold for eye aspect ratio (blink detection)
        """
        self.movement_threshold = movement_threshold
        self.aspect_ratio_threshold = aspect_ratio_threshold
        
        # Initialize MediaPipe Face Landmarker (Tasks API)
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision
        
        base_options = python.BaseOptions(model_asset_path='models_data/face_landmarker.task')
        options = vision.FaceLandmarkerOptions(base_options=base_options,
                                               output_face_blendshapes=False,
                                               output_facial_transformation_matrixes=False,
                                               num_faces=1)
        self.face_mesh = vision.FaceLandmarker.create_from_options(options)
        
        self.eye_movement_history = []
        self.gaze_direction_history = []
        self.blink_count = 0
        self.consecutive_eye_closed = 0
    
    def detect_eyes(self, frame: np.ndarray) -> Dict:
        """
        Detect eyes and track movement
        
        Args:
            frame: Input frame from webcam
            
        Returns:
            Dictionary containing:
            - left_eye: Left eye landmarks
            - right_eye: Right eye landmarks
            - gaze_direction: Detected gaze direction
            - eye_aspect_ratio: Current eye aspect ratio
            - blink_detected: Boolean indicating blink
            - warnings: List of warnings
        """
        try:
            h, w = frame.shape[:2]
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
            results = self.face_mesh.detect(mp_image)
            
            result = {
                "left_eye": None,
                "right_eye": None,
                "gaze_direction": "CENTER",
                "eye_aspect_ratio": 0.0,
                "blink_detected": False,
                "warnings": [],
                "eyes_detected": False
            }
            
            if results.face_landmarks:
                face_landmarks = results.face_landmarks[0]
                
                # Eye landmarks indices in MediaPipe Face Mesh
                LEFT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
                RIGHT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
                
                # Get eye landmarks
                left_eye_landmarks = np.array(
                    [[face_landmarks[i].x * w, face_landmarks[i].y * h] 
                     for i in LEFT_EYE_INDICES]
                )
                right_eye_landmarks = np.array(
                    [[face_landmarks[i].x * w, face_landmarks[i].y * h] 
                     for i in RIGHT_EYE_INDICES]
                )
                
                result["left_eye"] = left_eye_landmarks.tolist()
                result["right_eye"] = right_eye_landmarks.tolist()
                result["eyes_detected"] = True
                
                # Calculate eye aspect ratio
                left_eye_ar = self._calculate_eye_aspect_ratio(left_eye_landmarks)
                right_eye_ar = self._calculate_eye_aspect_ratio(right_eye_landmarks)
                avg_eye_ar = (left_eye_ar + right_eye_ar) / 2.0
                result["eye_aspect_ratio"] = avg_eye_ar
                
                # Detect blink
                if avg_eye_ar < self.aspect_ratio_threshold:
                    self.consecutive_eye_closed += 1
                    if self.consecutive_eye_closed > 3:  # Blink detected
                        self.blink_count += 1
                        result["blink_detected"] = True
                        logger.debug(f"Blink detected (total: {self.blink_count})")
                else:
                    self.consecutive_eye_closed = 0
                
                # Detect gaze direction
                gaze_direction = self._detect_gaze_direction(
                    left_eye_landmarks, right_eye_landmarks, w, h
                )
                result["gaze_direction"] = gaze_direction
                
                # Check for unusual eye movement
                if self.eye_movement_history:
                    prev_direction = self.eye_movement_history[-1]
                    if self._is_unusual_movement(prev_direction, gaze_direction):
                        result["warnings"].append("WARNING: Unusual eye movement detected!")
                        logger.warning(f"Unusual eye movement: {prev_direction} -> {gaze_direction}")
                
                self.eye_movement_history.append(gaze_direction)
                self.gaze_direction_history.append(gaze_direction)
                
                # Keep history manageable
                if len(self.eye_movement_history) > 1000:
                    self.eye_movement_history = self.eye_movement_history[-500:]
                if len(self.gaze_direction_history) > 1000:
                    self.gaze_direction_history = self.gaze_direction_history[-500:]
            
            return result
        
        except Exception as e:
            logger.error(f"Error in eye tracking: {e}")
            return {
                "left_eye": None,
                "right_eye": None,
                "gaze_direction": "UNKNOWN",
                "eye_aspect_ratio": 0.0,
                "blink_detected": False,
                "warnings": [f"ERROR: Eye detection failed - {str(e)}"],
                "eyes_detected": False
            }
    
    def _calculate_eye_aspect_ratio(self, eye_landmarks: np.ndarray) -> float:
        """
        Calculate eye aspect ratio using Euclidean distances
        
        Args:
            eye_landmarks: Array of eye landmark coordinates
            
        Returns:
            Eye aspect ratio value
        """
        if len(eye_landmarks) < 6:
            return 0.0
        
        # Calculate distances
        A = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
        B = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
        C = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
        
        # Calculate aspect ratio
        ear = (A + B) / (2.0 * C)
        return ear
    
    def _detect_gaze_direction(self, left_eye: np.ndarray, right_eye: np.ndarray, 
                               w: int, h: int) -> str:
        """
        Detect gaze direction based on eye landmarks
        
        Args:
            left_eye: Left eye landmarks
            right_eye: Right eye landmarks
            w: Frame width
            h: Frame height
            
        Returns:
            Gaze direction string: CENTER, LEFT, RIGHT, UP, DOWN
        """
        # Calculate center positions
        left_center = left_eye.mean(axis=0)
        right_center = right_eye.mean(axis=0)
        
        # Calculate gaze center
        gaze_center_x = (left_center[0] + right_center[0]) / 2.0
        gaze_center_y = (left_center[1] + right_center[1]) / 2.0
        
        # Determine direction
        h_third = h / 3
        w_third = w / 3
        
        direction = "CENTER"
        
        if gaze_center_x < w_third:
            direction = "LEFT"
        elif gaze_center_x > 2 * w_third:
            direction = "RIGHT"
        
        if gaze_center_y < h_third:
            direction = "UP" if direction == "CENTER" else f"{direction}_UP"
        elif gaze_center_y > 2 * h_third:
            direction = "DOWN" if direction == "CENTER" else f"{direction}_DOWN"
        
        return direction
    
    def _is_unusual_movement(self, prev_direction: str, current_direction: str) -> bool:
        """
        Detect unusual eye movement patterns
        
        Args:
            prev_direction: Previous gaze direction
            current_direction: Current gaze direction
            
        Returns:
            Boolean indicating unusual movement
        """
        # Define allowed movements
        allowed_movements = {
            "CENTER": ["LEFT", "RIGHT", "UP", "DOWN", "CENTER"],
            "LEFT": ["CENTER", "LEFT", "LEFT_UP", "LEFT_DOWN"],
            "RIGHT": ["CENTER", "RIGHT", "RIGHT_UP", "RIGHT_DOWN"],
            "UP": ["CENTER", "UP", "LEFT_UP", "RIGHT_UP"],
            "DOWN": ["CENTER", "DOWN", "LEFT_DOWN", "RIGHT_DOWN"],
        }
        
        if prev_direction in allowed_movements:
            if current_direction not in allowed_movements[prev_direction]:
                return True
        
        return False
    
    def draw_eyes(self, frame: np.ndarray, eye_detection: Dict) -> np.ndarray:
        """
        Draw eye landmarks and gaze direction on frame
        
        Args:
            frame: Input frame
            eye_detection: Eye detection result
            
        Returns:
            Frame with drawn eye landmarks
        """
        output_frame = frame.copy()
        
        if eye_detection["eyes_detected"]:
            # Draw left eye
            if eye_detection["left_eye"]:
                left_eye = np.array(eye_detection["left_eye"], dtype=np.int32)
                cv2.polylines(output_frame, [left_eye], True, (0, 255, 0), 2)
            
            # Draw right eye
            if eye_detection["right_eye"]:
                right_eye = np.array(eye_detection["right_eye"], dtype=np.int32)
                cv2.polylines(output_frame, [right_eye], True, (0, 255, 0), 2)
            
            # Draw gaze direction
            gaze = eye_detection["gaze_direction"]
            color = (0, 255, 0) if gaze == "CENTER" else (0, 165, 255)
            cv2.putText(
                output_frame,
                f"Gaze: {gaze}",
                (10, 60),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                color,
                2
            )
            
            # Draw eye aspect ratio
            ear = eye_detection["eye_aspect_ratio"]
            cv2.putText(
                output_frame,
                f"EAR: {ear:.2f}",
                (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )
        
        return output_frame
    
    def get_statistics(self) -> Dict:
        """Get eye tracking statistics"""
        return {
            "total_gaze_samples": len(self.gaze_direction_history),
            "blink_count": self.blink_count,
            "most_common_direction": self._get_most_common(self.gaze_direction_history),
            "consecutive_eye_closed": self.consecutive_eye_closed
        }
    
    def _get_most_common(self, data: List) -> str:
        """Get most common element in list"""
        if not data:
            return "UNKNOWN"
        return max(set(data), key=data.count)
    
    def reset(self):
        """Reset eye tracker"""
        self.eye_movement_history = []
        self.gaze_direction_history = []
        self.blink_count = 0
        self.consecutive_eye_closed = 0
        logger.info("Eye tracker reset")
