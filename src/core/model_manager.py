"""
Model Manager for handling face recognition and detection models
Supports both PKL (pickle) and PTH (PyTorch) model formats

Note: PyTorch support is optional. If not installed, system uses OpenCV fallback.
"""
import os
import pickle
import logging
import numpy as np
import cv2
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import PyTorch (optional)
try:
    import torch
    import torchvision.models as models
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logger.warning("PyTorch not available. Using OpenCV fallback for face detection.")


class ModelManager:
    """Manages loading and inference with face recognition and detection models"""
    
    def __init__(self, recognition_model_path: str, detection_model_path: str):
        """
        Initialize model manager
        
        Args:
            recognition_model_path: Path to PKL face recognition model
            detection_model_path: Path to PTH face detection model
        """
        self.recognition_model_path = recognition_model_path
        self.detection_model_path = detection_model_path
        
        if TORCH_AVAILABLE:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = None
        
        self.recognition_model = None
        self.detection_model = None
        
        self._load_models()
    
    def _load_models(self):
        """Load both PKL and PTH models"""
        try:
            self._load_recognition_model()
            self._load_detection_model()
            logger.info("All models loaded successfully")
        except Exception as e:
            logger.error(f"Error loading models: {e}")
            raise
    
    def _load_recognition_model(self):
        """Load face recognition model from PKL file"""
        try:
            if os.path.exists(self.recognition_model_path):
                with open(self.recognition_model_path, 'rb') as f:
                    self.recognition_model = pickle.load(f)
                logger.info(f"Recognition model loaded from {self.recognition_model_path}")
            else:
                logger.warning(f"Recognition model not found at {self.recognition_model_path}")
                logger.info("Using fallback face recognition model")
                # Fallback: use face_recognition library
                self.recognition_model = "face_recognition_library"
        except Exception as e:
            logger.error(f"Error loading recognition model: {e}")
            raise
    
    def _load_detection_model(self):
        """Load face detection model from PTH file"""
        try:
            if os.path.exists(self.detection_model_path):
                # Initialize a ResNet-based model for face detection
                self.detection_model = models.resnet50(pretrained=False)
                # Modify for face detection task
                self.detection_model.fc = torch.nn.Linear(self.detection_model.fc.in_features, 4)  # bounding box
                
                # Load weights from PTH file
                checkpoint = torch.load(self.detection_model_path, map_location=self.device)
                if isinstance(checkpoint, dict):
                    if 'model_state_dict' in checkpoint:
                        self.detection_model.load_state_dict(checkpoint['model_state_dict'], strict=True)
                    elif 'model_state' in checkpoint:
                        self.detection_model.load_state_dict(checkpoint['model_state'], strict=True)
                    elif 'state_dict' in checkpoint:
                        self.detection_model.load_state_dict(checkpoint['state_dict'], strict=True)
                    else:
                        self.detection_model.load_state_dict(checkpoint, strict=True)
                else:
                    self.detection_model.load_state_dict(checkpoint, strict=True)
                
                self.detection_model.to(self.device)
                self.detection_model.eval()
                logger.info(f"Detection model loaded from {self.detection_model_path}")
            else:
                logger.warning(f"Detection model not found at {self.detection_model_path}")
                logger.info("Using fallback face detection model (OpenCV Haar Cascade)")
                self.detection_model = cv2.CascadeClassifier(
                    cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                )
        except Exception as e:
            logger.error(f"Error loading detection model: {e}. Falling back to OpenCV Cascade.")
            self.detection_model = cv2.CascadeClassifier(
                cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            )
    
    def detect_faces(self, frame: np.ndarray, confidence_threshold: float = 0.5):
        """
        Detect faces in frame using detection model
        
        Args:
            frame: Input frame from webcam
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            List of face bounding boxes: [(x, y, w, h), ...]
        """
        try:
            if isinstance(self.detection_model, str):
                # Using fallback detection (this shouldn't happen in production)
                return self._detect_faces_fallback(frame)
            elif isinstance(self.detection_model, cv2.CascadeClassifier):
                return self._detect_faces_cascade(frame)
            else:
                return self._detect_faces_torch(frame, confidence_threshold)
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []
    
    def _detect_faces_cascade(self, frame: np.ndarray):
        """Detect faces using OpenCV Cascade Classifier"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detection_model.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )
        return faces.tolist() if len(faces) > 0 else []
    
    def _detect_faces_torch(self, frame: np.ndarray, confidence_threshold: float):
        """Detect faces using PyTorch model"""
        try:
            # Preprocess frame
            frame_tensor = self._preprocess_frame(frame)
            frame_tensor = frame_tensor.unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                output = self.detection_model(frame_tensor)
            
            # Parse detections (assuming output is [batch, 4] for bounding box)
            detections = []
            if output.shape[1] >= 4:
                bbox = output[0, :4].cpu().numpy()
                # Convert normalized coordinates to pixel coordinates
                h, w = frame.shape[:2]
                x, y, x2, y2 = bbox
                x, y, x2, y2 = int(x*w), int(y*h), int(x2*w), int(y2*h)
                box_w, box_h = x2 - x, y2 - y
                if box_w > 0 and box_h > 0:
                    detections.append([x, y, box_w, box_h])
            
            return detections
        except Exception as e:
            logger.error(f"Error in torch detection: {e}")
            return []
    
    def _detect_faces_fallback(self, frame: np.ndarray):
        """Fallback face detection using OpenCV"""
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(30, 30))
        return faces.tolist() if len(faces) > 0 else []
    
    def _preprocess_frame(self, frame: np.ndarray, target_size: tuple = (224, 224)):
        """Preprocess frame for model input"""
        # Resize frame
        resized = cv2.resize(frame, target_size)
        # Normalize
        normalized = resized.astype(np.float32) / 255.0
        # Convert to tensor and rearrange channels
        tensor = torch.from_numpy(normalized).permute(2, 0, 1)
        return tensor
    
    def recognize_face(self, face_encoding: np.ndarray):
        """
        Recognize face using recognition model
        
        Args:
            face_encoding: Encoded face data
            
        Returns:
            Recognition result (name, confidence)
        """
        try:
            if self.recognition_model is None:
                return {"name": "Unknown", "confidence": 0.0}
            
            if isinstance(self.recognition_model, str):
                return {"name": "Unknown", "confidence": 0.0}
            
            # Use the loaded model for prediction
            result = self.recognition_model.predict(face_encoding)
            return {"name": result[0], "confidence": float(result[1]) if len(result) > 1 else 0.5}
        except Exception as e:
            logger.error(f"Error recognizing face: {e}")
            return {"name": "Unknown", "confidence": 0.0}
    
    def get_model_info(self):
        """Get information about loaded models"""
        return {
            "recognition_model_path": self.recognition_model_path,
            "recognition_model_loaded": self.recognition_model is not None,
            "detection_model_path": self.detection_model_path,
            "detection_model_loaded": self.detection_model is not None,
            "device": str(self.device),
        }
