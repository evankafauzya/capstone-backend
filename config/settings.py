"""
Configuration settings for the proctoring system
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

# Flask Configuration
DEBUG = os.getenv('DEBUG', 'True') == 'True'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 5000))

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models_data')
REPORTS_DIR = os.path.join(BASE_DIR, 'reports')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')

# Model paths (PKL and PTH files)
FACE_RECOGNITION_MODEL = os.path.join(MODELS_DIR, 'face_recognition_model.pkl')
FACE_DETECTION_MODEL = os.path.join(MODELS_DIR, 'face_detection_model.pth')

# Proctoring Configuration
class ProctoringConfig:
    # Capture interval in seconds
    CAPTURE_INTERVAL = int(os.getenv('CAPTURE_INTERVAL', 5))  # Capture every 5 seconds
    
    # Reverification interval in seconds
    REVERIFICATION_INTERVAL = int(os.getenv('REVERIFICATION_INTERVAL', 30))  # Reverify every 30 seconds
    
    # Session timeout in seconds
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', 3600))  # 1 hour
    
    # Eye movement detection parameters
    EYE_MOVEMENT_THRESHOLD = float(os.getenv('EYE_MOVEMENT_THRESHOLD', 0.3))
    EYE_ASPECT_RATIO_THRESHOLD = float(os.getenv('EYE_ASPECT_RATIO_THRESHOLD', 0.2))
    
    # Face detection parameters
    FACE_DETECTION_CONFIDENCE = float(os.getenv('FACE_DETECTION_CONFIDENCE', 0.5))
    
    # Multiple face detection threshold
    MAX_FACES_ALLOWED = int(os.getenv('MAX_FACES_ALLOWED', 1))
    
    # Database settings
    DB_HOST = os.getenv('DB_HOST', 'localhost')
    DB_PORT = int(os.getenv('DB_PORT', 5432))
    DB_USER = os.getenv('DB_USER', 'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'password')
    DB_NAME = os.getenv('DB_NAME', 'proctoring_db')

# Warning thresholds
class WarningConfig:
    MULTIPLE_FACES_WARNING = "WARNING: Multiple faces detected in frame!"
    FACE_NOT_DETECTED_WARNING = "WARNING: Face not detected!"
    EYE_MOVEMENT_WARNING = "WARNING: Unusual eye movement detected!"
    REVERIFICATION_REQUIRED = "ALERT: Reverification required!"
    SESSION_TIMEOUT_WARNING = "ALERT: Session timeout approaching!"

# Logging configuration
LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
        'detailed': {
            'format': '%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'standard',
        },
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOGS_DIR, 'proctoring.log'),
            'formatter': 'detailed',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
