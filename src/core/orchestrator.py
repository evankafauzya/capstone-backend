"""
Proctoring System Orchestrator
Main coordinator for the entire proctoring system
"""
import logging
import time
from typing import Dict, Optional
import threading

from src.core.model_manager import ModelManager
from src.detectors.face_detector import FaceDetector
from src.detectors.eye_tracker import EyeTracker
from src.processors.webcam_capture import WebcamCapture
from src.processors.session_manager import ProctoringSession, WarningLevel
from src.utils.report_generator import ReportGenerator
from config.settings import ProctoringConfig, MODELS_DIR, REPORTS_DIR

logger = logging.getLogger(__name__)


class ProctoringSystem:
    """Main orchestrator for the proctoring system"""
    
    def __init__(self, models_dir: str = MODELS_DIR, reports_dir: str = REPORTS_DIR):
        """
        Initialize proctoring system
        
        Args:
            models_dir: Directory containing model files
            reports_dir: Directory for generated reports
        """
        self.models_dir = models_dir
        self.reports_dir = reports_dir
        
        # Initialize components
        self.model_manager = None
        self.face_detector = None
        self.eye_tracker = None
        self.webcam = None
        self.report_generator = ReportGenerator(reports_dir)
        
        self.current_session: Optional[ProctoringSession] = None
        self.is_running = False
        self.processing_thread = None
        
        # State for visualizations
        self.latest_face_detection = None
        self.latest_eye_tracking = None
        self.verified_user_id = "user"
        
        self._initialize_components()
    
    def _initialize_components(self):
        """Initialize all system components"""
        try:
            # Initialize model manager
            recognition_model = f"{self.models_dir}/face_recognition_model.pkl"
            detection_model = f"{self.models_dir}/face_detection_model.pth"
            
            self.model_manager = ModelManager(recognition_model, detection_model)
            logger.info("Model manager initialized")
            
            # Initialize face detector
            self.face_detector = FaceDetector(
                self.model_manager,
                max_faces=ProctoringConfig.MAX_FACES_ALLOWED,
                confidence_threshold=ProctoringConfig.FACE_DETECTION_CONFIDENCE
            )
            logger.info("Face detector initialized")
            
            # Initialize eye tracker
            self.eye_tracker = EyeTracker(
                movement_threshold=ProctoringConfig.EYE_MOVEMENT_THRESHOLD,
                aspect_ratio_threshold=ProctoringConfig.EYE_ASPECT_RATIO_THRESHOLD
            )
            logger.info("Eye tracker initialized")
            
            # Initialize webcam
            self.webcam = WebcamCapture(camera_id=0, resolution=(1280, 720), fps=30)
            logger.info("Webcam initialized")
            
        except Exception as e:
            logger.error(f"Error initializing components: {e}")
            raise
    
    def start_session(self, session_id: str, user_id: str) -> bool:
        """
        Start a new proctoring session
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            
        Returns:
            Boolean indicating successful start
        """
        try:
            if self.current_session is not None:
                logger.warning("A session is already active")
                return False
            
            # Create new session
            self.current_session = ProctoringSession(
                session_id=session_id,
                user_id=user_id,
                capture_interval=ProctoringConfig.CAPTURE_INTERVAL,
                reverification_interval=ProctoringConfig.REVERIFICATION_INTERVAL,
                session_timeout=ProctoringConfig.SESSION_TIMEOUT
            )
            
            # Start webcam
            self.webcam.start()
            
            # Start session
            self.current_session.start_session()
            
            # Start processing thread
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._processing_loop, daemon=True)
            self.processing_thread.start()
            
            logger.info(f"Session {session_id} started for user {user_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return False
    
    def stop_session(self) -> Optional[Dict]:
        """
        Stop the current session and generate report
        
        Returns:
            Session report or None
        """
        try:
            if self.current_session is None:
                logger.warning("No active session to stop")
                return None
            
            # Stop processing
            self.is_running = False
            if self.processing_thread:
                self.processing_thread.join(timeout=5)
            
            # Stop webcam
            self.webcam.stop()
            
            # End session
            session_summary = self.current_session.end_session()
            
            # Generate reports
            session_report = self.current_session.get_session_report()
            report_paths = self.report_generator.generate_all_reports(session_report)
            
            logger.info(f"Session {self.current_session.session_id} stopped")
            logger.info(f"Reports generated: {report_paths}")
            
            session_id = self.current_session.session_id
            self.current_session = None
            
            return {
                "session_summary": session_summary,
                "session_report": session_report,
                "report_paths": report_paths
            }
        
        except Exception as e:
            logger.error(f"Error stopping session: {e}")
            return None
    
    def _processing_loop(self):
        """Main processing loop for frame analysis"""
        logger.info("Starting processing loop")
        
        while self.is_running and self.current_session:
            try:
                # Check for timeout
                if self.current_session.check_session_timeout():
                    self.current_session.add_warning(
                        level=WarningLevel.ALERT,
                        title="Session Timeout",
                        description="Proctoring session timeout reached",
                        details={}
                    )
                    logger.warning(f"Session {self.current_session.session_id} timed out")
                    break
                
                # Get frame from webcam
                frame = self.webcam.get_frame()
                if frame is None:
                    time.sleep(0.05)
                    continue
                
                # Check if capture is needed
                if self.current_session.check_capture_needed():
                    # Perform face detection
                    face_detection = self.face_detector.detect_faces(frame)
                    self.latest_face_detection = face_detection  # Store for visualization
                    
                    self.current_session.record_face_detection(
                        face_count=face_detection["face_count"],
                        face_list=face_detection["faces"],
                        detection_valid=face_detection["is_valid"],
                        warnings=face_detection["warnings"]
                    )
                    
                    # Handle initial verification if needed
                    if (self.current_session.status.value == "verifying" and 
                        face_detection["is_valid"] and face_detection["face_count"] == 1):
                        # Perform initial verification
                        self._perform_verification(frame, face_detection["faces"][0])
                
                # Check if reverification is needed
                if self.current_session.check_reverification_needed():
                    # Throttle failed attempts to once per second to prevent CPU overload
                    current_time = time.time()
                    if not hasattr(self, 'last_reverif_attempt') or current_time - getattr(self, 'last_reverif_attempt', 0) >= 1.0:
                        self.last_reverif_attempt = current_time
                        face_detection = self.face_detector.detect_faces(frame)
                        if face_detection["is_valid"] and face_detection["face_count"] == 1:
                            self._perform_reverification(frame, face_detection["faces"][0])
                
                # Perform eye tracking
                eye_tracking = self.eye_tracker.detect_eyes(frame)
                self.latest_eye_tracking = eye_tracking  # Store for visualization
                
                if eye_tracking["eyes_detected"]:
                    self.current_session.record_eye_tracking(
                        gaze_direction=eye_tracking["gaze_direction"],
                        blink_detected=eye_tracking["blink_detected"],
                        eye_aspect_ratio=eye_tracking["eye_aspect_ratio"],
                        warnings=eye_tracking["warnings"]
                    )
                
                time.sleep(0.05)
            
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                time.sleep(0.1)
        
        logger.info("Processing loop ended")
    
    def _perform_verification(self, frame, face_box):
        """Perform initial user verification"""
        try:
            x, y, w, h = face_box
            face_roi = frame[y:y+h, x:x+w]
            
            # In a real system, extract face encoding and perform verification
            # For now, simulate with dummy data
            verification_result = self.current_session.verify_user(
                face_encoding=None,
                face_id="user_face_001",
                confidence=0.92
            )
            if verification_result.verified:
                self.verified_user_id = self.current_session.user_id
            
            logger.info(f"Verification result: {verification_result.verified}")
        
        except Exception as e:
            logger.error(f"Error in verification: {e}")
    
    def _perform_reverification(self, frame, face_box):
        """Perform user reverification"""
        try:
            x, y, w, h = face_box
            face_roi = frame[y:y+h, x:x+w]
            
            # In a real system, extract face encoding and perform verification
            # For now, simulate with dummy data
            reverification_result = self.current_session.reverify_user(
                face_encoding=None,
                face_id="user_face_001",
                confidence=0.89
            )
            
            logger.info(f"Reverification result: {reverification_result.verified}")
        
        except Exception as e:
            logger.error(f"Error in reverification: {e}")
    
    def get_current_frame(self):
        """Get current frame from webcam and draw annotations"""
        if not self.webcam:
            return None
            
        frame = self.webcam.get_frame()
        if frame is None:
            return None
            
        # Add annotations to the frame
        try:
            import cv2
            
            # Draw face detection bounding boxes
            if getattr(self, 'latest_face_detection', None) and self.latest_face_detection.get("is_valid"):
                for face in self.latest_face_detection.get("faces", []):
                    if isinstance(face, dict):
                        x, y, w, h = face.get('x', 0), face.get('y', 0), face.get('w', 0), face.get('h', 0)
                    elif isinstance(face, (list, tuple)) and len(face) >= 4:
                        x, y, w, h = face[0], face[1], face[2], face[3]
                    else:
                        continue
                        
                    # Draw bounding box
                    cv2.rectangle(frame, (int(x), int(y)), (int(x+w), int(y+h)), (0, 255, 0), 2)
                    
                    # Draw user name
                    user_name = getattr(self, 'verified_user_id', 'Unknown')
                    cv2.putText(frame, f"{user_name}", (int(x), int(y) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        except Exception as e:
            logger.error(f"Error annotating frame: {e}")
            
        return frame
    
    def get_session_status(self) -> Optional[Dict]:
        """Get current session status"""
        if self.current_session is None:
            return None
        
        return {
            "session_id": self.current_session.session_id,
            "user_id": self.current_session.user_id,
            "status": self.current_session.status.value,
            "initial_verified": self.current_session.initial_verified,
            "total_warnings": len(self.current_session.warnings),
            "critical_warnings": sum(1 for w in self.current_session.warnings if w["level"] == "critical"),
            "face_detections": len(self.current_session.face_detections),
            "eye_tracking_records": len(self.current_session.eye_tracking_data),
        }
    
    def get_system_info(self) -> Dict:
        """Get system information"""
        return {
            "model_manager": self.model_manager.get_model_info() if self.model_manager else None,
            "webcam": self.webcam.get_camera_info() if self.webcam else None,
            "has_active_session": self.current_session is not None,
            "is_running": self.is_running,
        }
