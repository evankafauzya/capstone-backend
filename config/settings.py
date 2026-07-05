"""
Application configuration.

All values are loaded from environment variables (with safe defaults for
development). Production deployments must override SECRET_KEY and API_KEY
via environment variables or a mounted .env file (never commit secrets).
"""
import os
import secrets
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _as_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# Runtime environment
# ---------------------------------------------------------------------------
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"

DEBUG = _as_bool(os.getenv("DEBUG"), default=not IS_PRODUCTION)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "5000"))


# ---------------------------------------------------------------------------
# Secrets
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if not SECRET_KEY:
    if IS_PRODUCTION:
        raise RuntimeError(
            "SECRET_KEY is required in production. "
            "Set it as an environment variable or in your .env file."
        )
    SECRET_KEY = secrets.token_urlsafe(48)
    logger.warning(
        "SECRET_KEY not set; generated an ephemeral key for development. "
        "Sessions will be invalidated on restart."
    )

API_KEY = os.getenv("API_KEY", "").strip()
if IS_PRODUCTION and not API_KEY:
    raise RuntimeError(
        "API_KEY is required in production. "
        "Set it as an environment variable or in your .env file."
    )

API_KEY_HEADER = os.getenv("API_KEY_HEADER", "Authorization")
API_KEY_REQUIRED = _as_bool(os.getenv("API_KEY_REQUIRED"), default=bool(API_KEY))


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
def _csv(value: str, default: list) -> list:
    if not value:
        return default
    return [item.strip() for item in value.split(",") if item.strip()]


CORS_ORIGINS = _csv(os.getenv("CORS_ORIGINS"), ["*"])


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
# Per-bucket request cap (bucket = API token, or client IP when unauthenticated).
# slowapi/limits syntax, e.g. "600/minute", "10/second", "100000/minute".
# Default is production-safe; raise it (or set a very high value) when running
# a load/capacity test so requests actually reach the compute path instead of
# being rejected with 429 by the limiter.
RATE_LIMIT = os.getenv("RATE_LIMIT", "600/minute").strip()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.getenv("MODELS_DIR", os.path.join(BASE_DIR, "models_data"))
REPORTS_DIR = os.getenv("REPORTS_DIR", os.path.join(BASE_DIR, "reports"))
LOGS_DIR = os.getenv("LOGS_DIR", os.path.join(BASE_DIR, "logs"))
DATA_DIR = os.getenv("DATA_DIR", os.path.join(BASE_DIR, "data"))

for _dir in (MODELS_DIR, REPORTS_DIR, LOGS_DIR, DATA_DIR):
    os.makedirs(_dir, exist_ok=True)

ENROLLMENT_DB_PATH = os.getenv(
    "ENROLLMENT_DB_PATH", os.path.join(DATA_DIR, "enrollments.db")
)

FACE_RECOGNITION_MODEL = os.path.join(MODELS_DIR, "face_recognition_efficient.pth")
FACE_DETECTION_MODEL = os.path.join(MODELS_DIR, "face_detection_model.pth")
# YOLO face-detection checkpoint (Ultralytics). Used in preference to
# RetinaFace when present.
FACE_DETECTION_YOLO_MODEL = os.path.join(MODELS_DIR, "face_detection_yolo.pt")


# ---------------------------------------------------------------------------
# Proctoring configuration
# ---------------------------------------------------------------------------
class ProctoringConfig:
    CAPTURE_INTERVAL = int(os.getenv("CAPTURE_INTERVAL", "5"))
    REVERIFICATION_INTERVAL = int(os.getenv("REVERIFICATION_INTERVAL", "30"))
    SESSION_TIMEOUT = int(os.getenv("SESSION_TIMEOUT", "3600"))

    EYE_MOVEMENT_THRESHOLD = float(os.getenv("EYE_MOVEMENT_THRESHOLD", "0.3"))
    EYE_ASPECT_RATIO_THRESHOLD = float(os.getenv("EYE_ASPECT_RATIO_THRESHOLD", "0.2"))

    FACE_DETECTION_CONFIDENCE = float(os.getenv("FACE_DETECTION_CONFIDENCE", "0.5"))
    # Cosine-similarity threshold for ArcFace verification. 0.4 is a good
    # balance for webcam-vs-registered photo comparisons; tighten to 0.5+
    # only if registration and capture come from the same source.
    FACE_MATCH_THRESHOLD = float(os.getenv("FACE_MATCH_THRESHOLD", "0.4"))
    MAX_FACES_ALLOWED = int(os.getenv("MAX_FACES_ALLOWED", "1"))


class WarningConfig:
    MULTIPLE_FACES_WARNING = "WARNING: Multiple faces detected in frame!"
    FACE_NOT_DETECTED_WARNING = "WARNING: Face not detected!"
    EYE_MOVEMENT_WARNING = "WARNING: Unusual eye movement detected!"
    REVERIFICATION_REQUIRED = "ALERT: Reverification required!"
    SESSION_TIMEOUT_WARNING = "ALERT: Session timeout approaching!"


# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG" if DEBUG else "INFO").upper()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(funcName)s() - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": LOG_LEVEL,
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(LOGS_DIR, "proctoring.log"),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "formatter": "detailed",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file"],
            "level": LOG_LEVEL,
            "propagate": True,
        },
    },
}


def public_config() -> dict:
    """Return a non-sensitive snapshot of the runtime configuration."""
    return {
        "environment": ENVIRONMENT,
        "debug": DEBUG,
        "host": HOST,
        "port": PORT,
        "api_key_required": API_KEY_REQUIRED,
        "cors_origins": CORS_ORIGINS,
        "log_level": LOG_LEVEL,
        "proctoring": {
            "capture_interval": ProctoringConfig.CAPTURE_INTERVAL,
            "reverification_interval": ProctoringConfig.REVERIFICATION_INTERVAL,
            "session_timeout": ProctoringConfig.SESSION_TIMEOUT,
            "eye_movement_threshold": ProctoringConfig.EYE_MOVEMENT_THRESHOLD,
            "eye_aspect_ratio_threshold": ProctoringConfig.EYE_ASPECT_RATIO_THRESHOLD,
            "face_detection_confidence": ProctoringConfig.FACE_DETECTION_CONFIDENCE,
            "face_match_threshold": ProctoringConfig.FACE_MATCH_THRESHOLD,
            "max_faces_allowed": ProctoringConfig.MAX_FACES_ALLOWED,
        },
    }
