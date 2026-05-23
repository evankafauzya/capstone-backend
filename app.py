"""
Moodle Proctoring AI Backend — application entrypoint.

This module is the Flask application factory. For development run it directly
(`python app.py`); for production use a WSGI server (Gunicorn) targeting
`wsgi:app` — see Dockerfile / README for details.
"""
from __future__ import annotations

import logging
import logging.config
import time
from typing import Optional

import json

from flask import Flask, jsonify, request
from flask_cors import CORS
from flasgger import Swagger

from config.settings import (
    CORS_ORIGINS,
    DEBUG,
    HOST,
    IS_PRODUCTION,
    LOGGING_CONFIG,
    PORT,
    SECRET_KEY,
)

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

from src.api.proctoring_routes import proctoring_api, set_proctoring_system
from src.api.moodle_routes import (
    moodle_api, set_enrollment_store, set_moodle_proctoring_system,
)
from src.core.orchestrator import ProctoringSystem
from src.services.face_enrollment import FaceEnrollmentStore

APP_VERSION = "2.0.0"
APP_NAME = "Moodle Proctoring AI Backend"


# ---------------------------------------------------------------------------
# Swagger configuration
# ---------------------------------------------------------------------------
SWAGGER_TEMPLATE = {
    "openapi": "3.0.3",
    "info": {
        "title": APP_NAME,
        "description": (
            "REST API for face detection, face verification, behavior analysis, "
            "and session-based proctoring. Most endpoints require a Bearer token "
            "configured via the API_KEY environment variable."
        ),
        "version": APP_VERSION,
        "contact": {"name": "Proctoring AI Backend"},
    },
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API-Token",
                "description": "Provide the token from the API_KEY environment variable.",
            }
        }
    },
    "security": [{"BearerAuth": []}],
}

SWAGGER_CONFIG = {
    "headers": [],
    "specs": [
        {
            "endpoint": "openapi",
            "route": "/openapi.json",
            "rule_filter": lambda rule: True,
            "model_filter": lambda tag: True,
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs",
}


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------
def _init_proctoring_system() -> Optional[ProctoringSystem]:
    try:
        system = ProctoringSystem()
        set_proctoring_system(system)
        set_moodle_proctoring_system(system)
        logger.info("Proctoring system initialized successfully")
    except Exception:
        logger.exception("Failed to initialize proctoring system")
        return None

    # Enrollment store — keyed on the recognizer's embedding dim when available.
    try:
        from config.settings import ENROLLMENT_DB_PATH
        embedding_dim = 512
        if system.model_manager and system.model_manager.face_recognizer:
            embedding_dim = system.model_manager.face_recognizer.embedding_dim
        store = FaceEnrollmentStore(ENROLLMENT_DB_PATH, embedding_dim=embedding_dim)
        set_enrollment_store(store)
    except Exception:
        logger.exception("Failed to initialize enrollment store")

    return system


def _register_openapi_cleaner(app: Flask) -> None:
    """Flasgger emits both ``swagger: "2.0"`` and ``openapi: "3.0.x"`` in the
    same document, which Swagger UI refuses to render. Strip the Swagger-2.0
    leftovers so the spec is pure OpenAPI 3.0."""

    @app.after_request
    def _strip_swagger_v2_fields(response):
        if request.path != "/openapi.json":
            return response
        if not (response.content_type or "").startswith("application/json"):
            return response
        try:
            data = response.get_json(silent=True)
            if not isinstance(data, dict):
                return response
            if "openapi" in data and "swagger" in data:
                data.pop("swagger", None)
                data.pop("definitions", None)
                response.set_data(json.dumps(data))
                response.content_length = len(response.get_data())
        except Exception:
            logger.exception("Failed to clean OpenAPI spec")
        return response


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(404)
    def not_found(_):
        return jsonify({"error": "Not found", "status": "error"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_):
        return jsonify({"error": "Method not allowed", "status": "error"}), 405

    @app.errorhandler(500)
    def server_error(error):
        logger.error("Internal server error: %s", error)
        return jsonify({"error": "Internal server error", "status": "error"}), 500


def _register_root_routes(app: Flask, system: Optional[ProctoringSystem]) -> None:
    @app.route("/", methods=["GET"])
    def index():
        """Service banner.
        ---
        tags: [Internal]
        responses:
          200:
            description: Service banner
        """
        return jsonify({
            "app": APP_NAME,
            "version": APP_VERSION,
            "status": "running",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }), 200

    @app.route("/health", methods=["GET"])
    def health():
        """Public health check used by Moodle and load balancers.
        ---
        tags: [Internal]
        responses:
          200:
            description: Service health
        """
        gpu_available = False
        gpu_device = "cpu"
        try:
            import torch
            gpu_available = torch.cuda.is_available()
            if gpu_available:
                gpu_device = torch.cuda.get_device_name(0)
        except ImportError:
            pass

        models = {}
        if system is not None and getattr(system, "model_manager", None) is not None:
            try:
                info = system.model_manager.get_model_info()
                models = {
                    "detector_backend": info["detector"]["backend"],
                    "detector_loaded": info["detector"]["loaded"],
                    "recognizer_backend": info["recognizer"]["backend"],
                    "recognizer_loaded": info["recognizer"]["loaded"],
                }
            except Exception:
                logger.exception("Could not collect model info for /health")

        return jsonify({
            "status": "healthy",
            "service": "proctoring-ai-backend",
            "version": APP_VERSION,
            "timestamp": time.time(),
            "gpu_available": gpu_available,
            "gpu_device": gpu_device,
            "components": {
                "face_detector": system is not None and system.face_detector is not None,
                "eye_tracker": system is not None and system.eye_tracker is not None,
                "model_manager": system is not None and system.model_manager is not None,
            },
            "models": models,
        }), 200


def create_app() -> Flask:
    """Application factory."""
    app = Flask(__name__)
    app.config.update(
        DEBUG=DEBUG,
        SECRET_KEY=SECRET_KEY,
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,  # 50 MB cap for base64 frames
        JSON_SORT_KEYS=False,
    )

    CORS(app, resources={
        r"/*": {
            "origins": CORS_ORIGINS,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "Accept", "X-API-Key"],
        }
    })

    Swagger(app, template=SWAGGER_TEMPLATE, config=SWAGGER_CONFIG)

    system = _init_proctoring_system()

    app.register_blueprint(proctoring_api)
    app.register_blueprint(moodle_api)

    _register_root_routes(app, system)
    _register_error_handlers(app)
    _register_openapi_cleaner(app)

    logger.info(
        "%s v%s ready (env=%s, debug=%s)",
        APP_NAME,
        APP_VERSION,
        "production" if IS_PRODUCTION else "development",
        DEBUG,
    )
    return app


app = create_app()


if __name__ == "__main__":
    logger.info("Starting %s on %s:%s", APP_NAME, HOST, PORT)
    app.run(host=HOST, port=PORT, debug=DEBUG)
