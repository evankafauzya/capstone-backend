"""
Proctoring Session Manager
Orchestrates the complete proctoring process including verification, monitoring, and warnings
"""
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class SessionStatus(Enum):
    """Session status enumeration"""
    INITIALIZED = "initialized"
    VERIFYING = "verifying"
    ACTIVE = "active"
    REVERIFYING = "reverifying"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"


class WarningLevel(Enum):
    """Warning level enumeration"""
    INFO = "info"
    WARNING = "warning"
    ALERT = "alert"
    CRITICAL = "critical"


@dataclass
class SessionEvent:
    """Data class for session events"""
    timestamp: float
    event_type: str
    severity: str
    description: str
    details: Dict
    
    def to_dict(self):
        return asdict(self)


@dataclass
class VerificationResult:
    """Data class for verification results"""
    verified: bool
    face_id: Optional[str]
    confidence: float
    timestamp: float
    details: Dict


class ProctoringSession:
    """Manages proctoring session lifecycle and monitoring"""
    
    def __init__(self, session_id: str, user_id: str, capture_interval: int = 5,
                 reverification_interval: int = 30, session_timeout: int = 3600):
        """
        Initialize proctoring session
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            capture_interval: Frame capture interval in seconds
            reverification_interval: Reverification interval in seconds
            session_timeout: Session timeout in seconds
        """
        self.session_id = session_id
        self.user_id = user_id
        self.capture_interval = capture_interval
        self.reverification_interval = reverification_interval
        self.session_timeout = session_timeout
        
        self.status = SessionStatus.INITIALIZED
        self.start_time = None
        self.last_capture_time = None
        self.last_verification_time = None
        self.last_reverification_time = None
        self.end_time = None
        
        self.events: List[SessionEvent] = []
        self.verification_results: List[VerificationResult] = []
        self.warnings: List[Dict] = []
        self.face_detections: List[Dict] = []
        self.eye_tracking_data: List[Dict] = []
        
        self.initial_verified = False
        self.current_user_face_id = None
        
        logger.info(f"Session {session_id} created for user {user_id}")
    
    def start_session(self) -> bool:
        """
        Start the proctoring session
        
        Returns:
            Boolean indicating successful start
        """
        try:
            self.start_time = time.time()
            self.last_verification_time = self.start_time
            self.last_reverification_time = self.start_time
            self.status = SessionStatus.VERIFYING
            
            event = SessionEvent(
                timestamp=self.start_time,
                event_type="SESSION_STARTED",
                severity=WarningLevel.INFO.value,
                description="Proctoring session started",
                details={"user_id": self.user_id, "session_id": self.session_id}
            )
            self.events.append(event)
            
            logger.info(f"Session {self.session_id} started")
            return True
        except Exception as e:
            logger.error(f"Error starting session: {e}")
            return False
    
    def verify_user(self, face_encoding: Optional[object], face_id: str, 
                   confidence: float) -> VerificationResult:
        """
        Verify user identity during initial verification
        
        Args:
            face_encoding: Encoded face data
            face_id: Detected face identifier
            confidence: Recognition confidence
            
        Returns:
            VerificationResult
        """
        current_time = time.time()
        
        # Determine if verification is successful
        verified = confidence >= 0.6  # Threshold
        
        result = VerificationResult(
            verified=verified,
            face_id=face_id if verified else None,
            confidence=confidence,
            timestamp=current_time,
            details={
                "verification_type": "initial",
                "session_id": self.session_id,
                "user_id": self.user_id
            }
        )
        
        if result.verified:
            self.initial_verified = True
            self.current_user_face_id = face_id
            self.status = SessionStatus.ACTIVE
            
            event = SessionEvent(
                timestamp=current_time,
                event_type="INITIAL_VERIFICATION_SUCCESS",
                severity=WarningLevel.INFO.value,
                description="User successfully verified",
                details={"confidence": confidence, "face_id": face_id}
            )
        else:
            event = SessionEvent(
                timestamp=current_time,
                event_type="INITIAL_VERIFICATION_FAILED",
                severity=WarningLevel.ALERT.value,
                description="Initial verification failed",
                details={"confidence": confidence, "required_confidence": 0.6}
            )
        
        self.events.append(event)
        self.verification_results.append(result)
        self.last_verification_time = current_time
        
        logger.info(f"Initial verification for session {self.session_id}: {result.verified}")
        return result
    
    def reverify_user(self, face_encoding: Optional[object], face_id: str,
                     confidence: float) -> VerificationResult:
        """
        Reverify user identity during session
        
        Args:
            face_encoding: Encoded face data
            face_id: Detected face identifier
            confidence: Recognition confidence
            
        Returns:
            VerificationResult
        """
        current_time = time.time()
        
        # Determine if reverification is successful
        verified = confidence >= 0.5 and face_id == self.current_user_face_id
        
        result = VerificationResult(
            verified=verified,
            face_id=face_id if verified else None,
            confidence=confidence,
            timestamp=current_time,
            details={
                "verification_type": "reverification",
                "session_id": self.session_id,
                "user_id": self.user_id,
                "expected_face_id": self.current_user_face_id
            }
        )
        
        if not result.verified:
            self.add_warning(
                level=WarningLevel.CRITICAL,
                title="Reverification Failed",
                description="User reverification failed. Possible identity change or spoofing attempt.",
                details={
                    "detected_face_id": face_id,
                    "expected_face_id": self.current_user_face_id,
                    "confidence": confidence
                }
            )
            
            logger.warning(f"Reverification failed for session {self.session_id}")
        else:
            logger.debug(f"Reverification successful for session {self.session_id}")
        
        self.verification_results.append(result)
        self.last_reverification_time = current_time
        
        return result
    
    def check_reverification_needed(self) -> bool:
        """Check if reverification is needed"""
        if self.last_reverification_time is None:
            return True
        
        time_since_last = time.time() - self.last_reverification_time
        return time_since_last >= self.reverification_interval
    
    def check_capture_needed(self) -> bool:
        """Check if frame capture is needed"""
        if self.last_capture_time is None:
            return True
        
        time_since_last = time.time() - self.last_capture_time
        return time_since_last >= self.capture_interval
    
    def record_face_detection(self, face_count: int, face_list: List,
                             detection_valid: bool, warnings: List[str]):
        """Record face detection result"""
        self.last_capture_time = time.time()
        
        detection_record = {
            "timestamp": self.last_capture_time,
            "face_count": face_count,
            "detection_valid": detection_valid,
            "warnings": warnings
        }
        
        self.face_detections.append(detection_record)
        
        # Handle warnings
        if not detection_valid:
            for warning in warnings:
                self.add_warning(
                    level=WarningLevel.WARNING,
                    title="Face Detection Issue",
                    description=warning,
                    details=detection_record
                )
    
    def record_eye_tracking(self, gaze_direction: str, blink_detected: bool,
                           eye_aspect_ratio: float, warnings: List[str]):
        """Record eye tracking data"""
        eye_record = {
            "timestamp": time.time(),
            "gaze_direction": gaze_direction,
            "blink_detected": blink_detected,
            "eye_aspect_ratio": eye_aspect_ratio,
            "warnings": warnings
        }
        
        self.eye_tracking_data.append(eye_record)
        
        # Handle eye tracking warnings
        for warning in warnings:
            self.add_warning(
                level=WarningLevel.WARNING,
                title="Eye Tracking Alert",
                description=warning,
                details=eye_record
            )
    
    def add_warning(self, level: WarningLevel, title: str, description: str,
                   details: Dict = None):
        """Add warning to session"""
        warning = {
            "timestamp": time.time(),
            "level": level.value,
            "title": title,
            "description": description,
            "details": details or {}
        }
        
        self.warnings.append(warning)
        logger.warning(f"[{level.value.upper()}] {title}: {description}")
    
    def check_session_timeout(self) -> bool:
        """Check if session has timed out"""
        if self.start_time is None:
            return False
        
        elapsed = time.time() - self.start_time
        return elapsed >= self.session_timeout
    
    def end_session(self) -> Dict:
        """
        End the proctoring session and generate summary
        
        Returns:
            Session summary dictionary
        """
        self.end_time = time.time()
        self.status = SessionStatus.COMPLETED
        
        duration = self.end_time - self.start_time if self.start_time else 0
        
        summary = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": duration,
            "status": self.status.value,
            "initial_verified": self.initial_verified,
            "total_events": len(self.events),
            "total_warnings": len(self.warnings),
            "critical_warnings": sum(1 for w in self.warnings if w["level"] == "critical"),
            "total_face_detections": len(self.face_detections),
            "total_eye_tracking_records": len(self.eye_tracking_data),
            "total_verifications": len(self.verification_results),
            "successful_verifications": sum(1 for v in self.verification_results if v.verified),
            "failed_verifications": sum(1 for v in self.verification_results if not v.verified),
        }
        
        logger.info(f"Session {self.session_id} ended. Summary: {summary}")
        return summary
    
    def get_session_report(self) -> Dict:
        """Generate comprehensive session report"""
        return {
            "session_info": {
                "session_id": self.session_id,
                "user_id": self.user_id,
                "start_time": self.start_time,
                "end_time": self.end_time,
                "duration_seconds": self.end_time - self.start_time if self.end_time and self.start_time else 0,
                "status": self.status.value,
                "initial_verified": self.initial_verified,
            },
            "statistics": {
                "total_events": len(self.events),
                "total_warnings": len(self.warnings),
                "critical_warnings": sum(1 for w in self.warnings if w["level"] == "critical"),
                "alert_warnings": sum(1 for w in self.warnings if w["level"] == "alert"),
                "warning_warnings": sum(1 for w in self.warnings if w["level"] == "warning"),
                "total_face_detections": len(self.face_detections),
                "valid_face_detections": sum(1 for d in self.face_detections if d["detection_valid"]),
                "invalid_face_detections": sum(1 for d in self.face_detections if not d["detection_valid"]),
                "total_eye_tracking_records": len(self.eye_tracking_data),
                "total_verifications": len(self.verification_results),
                "successful_verifications": sum(1 for v in self.verification_results if v.verified),
                "failed_verifications": sum(1 for v in self.verification_results if not v.verified),
            },
            "events": [e.to_dict() for e in self.events[-100:]],  # Last 100 events
            "warnings": self.warnings[-50:],  # Last 50 warnings
            "verification_timeline": [
                {
                    "timestamp": v.timestamp,
                    "verified": v.verified,
                    "confidence": v.confidence,
                    "type": v.details.get("verification_type", "unknown")
                }
                for v in self.verification_results
            ]
        }
