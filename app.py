"""
Main Flask Application
"""
import logging
import logging.config
from flask import Flask, jsonify
from flask_cors import CORS
import os

# Configure logging
from config.settings import LOGGING_CONFIG, DEBUG, SECRET_KEY, HOST, PORT

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# Import API routes
from src.api.proctoring_routes import proctoring_api, set_proctoring_system
from src.core.orchestrator import ProctoringSystem


def create_app():
    """Create and configure Flask application"""
    
    app = Flask(__name__)
    
    # Configuration
    app.config['DEBUG'] = DEBUG
    app.config['SECRET_KEY'] = SECRET_KEY
    
    # Enable CORS
    CORS(app)
    
    # Initialize proctoring system
    try:
        proctoring_system = ProctoringSystem()
        set_proctoring_system(proctoring_system)
        logger.info("Proctoring system initialized successfully")
    except Exception as e:
        logger.exception("Error initializing proctoring system:")
        proctoring_system = None
    
    # Register blueprints
    app.register_blueprint(proctoring_api)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return jsonify({"error": "Internal server error"}), 500
    
    # Index route
    @app.route('/', methods=['GET'])
    def index():
        return jsonify({
            "app": "Proctoring System",
            "version": "1.0.0",
            "status": "running",
            "endpoints": {
                "health": "/api/proctoring/health",
                "system_info": "/api/proctoring/system-info",
                "session_start": "/api/proctoring/session/start",
                "session_stop": "/api/proctoring/session/stop",
                "session_status": "/api/proctoring/session/status",
                "session_report": "/api/proctoring/session/report",
                "video_frame": "/api/proctoring/video/frame",
                "video_stream": "/api/proctoring/video/stream",
                "face_detection_stats": "/api/proctoring/face-detection/stats",
                "eye_tracking_stats": "/api/proctoring/eye-tracking/stats",
                "warnings": "/api/proctoring/warnings",
                "configuration": "/api/proctoring/configuration",
            }
        }), 200
    
    logger.info("Flask app created successfully")
    return app


if __name__ == '__main__':
    app = create_app()
    logger.info(f"Starting server on {HOST}:{PORT}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
