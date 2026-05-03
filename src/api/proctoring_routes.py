"""
Flask API Endpoints for Proctoring System
"""
import logging
import cv2
import base64
from io import BytesIO
from flask import Blueprint, request, jsonify, Response
from functools import wraps
import time

logger = logging.getLogger(__name__)

# Create blueprint
proctoring_api = Blueprint('proctoring', __name__, url_prefix='/api/proctoring')

# Global reference to proctoring system (will be set by main app)
proctoring_system = None


def set_proctoring_system(system):
    """Set the global proctoring system reference"""
    global proctoring_system
    proctoring_system = system


def require_session(f):
    """Decorator to check if an active session exists"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if proctoring_system is None or proctoring_system.current_session is None:
            return jsonify({"error": "No active session"}), 400
        return f(*args, **kwargs)
    return decorated_function


@proctoring_api.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time()
    }), 200


@proctoring_api.route('/system-info', methods=['GET'])
def system_info():
    """Get system information"""
    try:
        if proctoring_system is None:
            return jsonify({"error": "System not initialized"}), 500
        
        system_info = proctoring_system.get_system_info()
        return jsonify(system_info), 200
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/session/start', methods=['POST'])
def start_session():
    """Start a new proctoring session"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        session_id = data.get('session_id')
        user_id = data.get('user_id')
        
        if not session_id or not user_id:
            return jsonify({"error": "Missing session_id or user_id"}), 400
        
        success = proctoring_system.start_session(session_id, user_id)
        
        if success:
            return jsonify({
                "message": "Session started successfully",
                "session_id": session_id,
                "user_id": user_id,
                "timestamp": time.time()
            }), 200
        else:
            return jsonify({"error": "Failed to start session"}), 400
    
    except Exception as e:
        logger.error(f"Error starting session: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/session/stop', methods=['POST'])
@require_session
def stop_session():
    """Stop the current proctoring session"""
    try:
        result = proctoring_system.stop_session()
        
        if result:
            return jsonify({
                "message": "Session stopped successfully",
                "summary": result.get("session_summary"),
                "reports": result.get("report_paths")
            }), 200
        else:
            return jsonify({"error": "Failed to stop session"}), 400
    
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/session/status', methods=['GET'])
def session_status():
    """Get current session status"""
    try:
        status = proctoring_system.get_session_status()
        
        if status:
            return jsonify(status), 200
        else:
            return jsonify({"message": "No active session"}), 200
    
    except Exception as e:
        logger.error(f"Error getting session status: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/session/report', methods=['GET'])
@require_session
def get_session_report():
    """Get current session report"""
    try:
        report = proctoring_system.current_session.get_session_report()
        return jsonify(report), 200
    
    except Exception as e:
        logger.error(f"Error getting session report: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/video/frame', methods=['GET'])
@require_session
def get_current_frame():
    """Get current frame from webcam as JPEG"""
    try:
        frame = proctoring_system.get_current_frame()
        
        if frame is None:
            return jsonify({"error": "No frame available"}), 404
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        
        # Return as image
        return Response(frame_bytes, mimetype='image/jpeg')
    
    except Exception as e:
        logger.error(f"Error getting frame: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/video/stream', methods=['GET'])
@require_session
def video_stream():
    """Stream video frames as Motion JPEG"""
    try:
        def generate():
            while proctoring_system.is_running and proctoring_system.current_session:
                frame = proctoring_system.get_current_frame()
                
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    frame_bytes = buffer.tobytes()
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n'
                           b'Content-length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                           + frame_bytes + b'\r\n')
                
                time.sleep(0.033)  # ~30 FPS
        
        return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    except Exception as e:
        logger.error(f"Error in video stream: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/face-detection/stats', methods=['GET'])
@require_session
def face_detection_stats():
    """Get face detection statistics"""
    try:
        stats = proctoring_system.face_detector.get_detection_statistics()
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error getting face detection stats: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/eye-tracking/stats', methods=['GET'])
@require_session
def eye_tracking_stats():
    """Get eye tracking statistics"""
    try:
        stats = proctoring_system.eye_tracker.get_statistics()
        return jsonify(stats), 200
    
    except Exception as e:
        logger.error(f"Error getting eye tracking stats: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/warnings', methods=['GET'])
@require_session
def get_warnings():
    """Get warnings from current session"""
    try:
        limit = request.args.get('limit', 50, type=int)
        warnings = proctoring_system.current_session.warnings[-limit:]
        
        return jsonify({
            "total_warnings": len(proctoring_system.current_session.warnings),
            "warnings": warnings
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting warnings: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/configuration', methods=['GET'])
def get_configuration():
    """Get proctoring configuration"""
    try:
        from config.settings import ProctoringConfig
        
        config = {
            "capture_interval": ProctoringConfig.CAPTURE_INTERVAL,
            "reverification_interval": ProctoringConfig.REVERIFICATION_INTERVAL,
            "session_timeout": ProctoringConfig.SESSION_TIMEOUT,
            "eye_movement_threshold": ProctoringConfig.EYE_MOVEMENT_THRESHOLD,
            "eye_aspect_ratio_threshold": ProctoringConfig.EYE_ASPECT_RATIO_THRESHOLD,
            "face_detection_confidence": ProctoringConfig.FACE_DETECTION_CONFIDENCE,
            "max_faces_allowed": ProctoringConfig.MAX_FACES_ALLOWED,
        }
        
        return jsonify(config), 200
    
    except Exception as e:
        logger.error(f"Error getting configuration: {e}")
        return jsonify({"error": str(e)}), 500


@proctoring_api.route('/configuration', methods=['PUT'])
def update_configuration():
    """Update proctoring configuration"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No configuration data provided"}), 400
        
        from config.settings import ProctoringConfig
        
        # Update configuration (in production, persist to database)
        if 'capture_interval' in data:
            ProctoringConfig.CAPTURE_INTERVAL = data['capture_interval']
        
        if 'reverification_interval' in data:
            ProctoringConfig.REVERIFICATION_INTERVAL = data['reverification_interval']
        
        if 'max_faces_allowed' in data:
            ProctoringConfig.MAX_FACES_ALLOWED = data['max_faces_allowed']
        
        return jsonify({
            "message": "Configuration updated successfully",
            "updated_fields": list(data.keys())
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating configuration: {e}")
        return jsonify({"error": str(e)}), 500
