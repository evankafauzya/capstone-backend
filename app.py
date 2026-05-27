"""
Moodle Proctoring AI Backend -- FastAPI application entrypoint.

For development run it directly (``python app.py``); for production point an
ASGI server (Uvicorn / Gunicorn with the uvicorn worker class) at
``app:app`` -- see Dockerfile / README for details.
"""
from __future__ import annotations

import logging
import logging.config
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from config.settings import (
    CORS_ORIGINS,
    DEBUG,
    HOST,
    IS_PRODUCTION,
    LOGGING_CONFIG,
    PORT,
)

logging.config.dictConfig(LOGGING_CONFIG)
logger = logging.getLogger(__name__)

# watchfiles (uvicorn's --reload backend) logs "N change detected" at INFO
# for every filesystem write. Our log file is itself written constantly, so
# this floods the console. Keep only warnings.
logging.getLogger("watchfiles").setLevel(logging.WARNING)
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

from src.api.proctoring_routes import proctoring_api, set_proctoring_system
from src.api.moodle_routes import (
    moodle_api, set_audit_store, set_enrollment_store, set_moodle_proctoring_system,
)
from src.core.orchestrator import ProctoringSystem
from src.services.audit import VerificationAuditStore
from src.services.face_enrollment import FaceEnrollmentStore

APP_VERSION = "2.0.0"
APP_NAME = "Moodle Proctoring AI Backend"
MAX_BODY_BYTES = 50 * 1024 * 1024  # 50 MB cap for base64 frames


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
# Bucket requests by API key when present, else by IP. This way one
# authenticated client cannot exhaust the bucket of all anonymous callers
# from the same NAT, and a single API key cannot be sprayed across many IPs
# to bypass the limit.
def _rate_limit_key(request: Request) -> str:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return f"key:{auth[7:].strip()}"
    api_key_header = request.headers.get("X-API-Key", "").strip()
    if api_key_header:
        return f"key:{api_key_header}"
    return f"ip:{get_remote_address(request)}"


# 600 req/min per bucket -> ~10 req/s, plenty for a proctoring poll loop,
# but low enough to absorb the GPU cost of a brute-force attack.
# /health is exempt via per-route override below so load balancers can poll
# it freely.
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["600/minute"],
    headers_enabled=True,  # adds X-RateLimit-* response headers
)


# ---------------------------------------------------------------------------
# Lifespan: build the proctoring system + enrollment store at startup.
# ---------------------------------------------------------------------------
def _init_proctoring_system() -> Optional[ProctoringSystem]:
    # MOCK_MODELS=1 swaps in a stub system (used by tests / CI where the
    # real .pth files are not on disk). The stub has the exact same public
    # interface as the real ProctoringSystem so routes run unchanged.
    if os.getenv("MOCK_MODELS") == "1":
        try:
            from tests._stub_system import StubProctoringSystem
            system = StubProctoringSystem()
            set_proctoring_system(system)
            set_moodle_proctoring_system(system)
            logger.info("MOCK_MODELS=1 -- using StubProctoringSystem")
        except Exception:
            logger.exception("Failed to initialize stub proctoring system")
            return None
    else:
        try:
            system = ProctoringSystem()
            set_proctoring_system(system)
            set_moodle_proctoring_system(system)
            logger.info("Proctoring system initialized successfully")
        except Exception:
            logger.exception("Failed to initialize proctoring system")
            return None

    try:
        from config.settings import ENROLLMENT_DB_PATH
        embedding_dim = 512
        if system.model_manager and system.model_manager.face_recognizer:
            embedding_dim = system.model_manager.face_recognizer.embedding_dim
        store = FaceEnrollmentStore(ENROLLMENT_DB_PATH, embedding_dim=embedding_dim)
        set_enrollment_store(store)
    except Exception:
        logger.exception("Failed to initialize enrollment store")

    # Verification audit store -- shares the same SQLite DB file so backups
    # capture both enrollment and audit data together.
    try:
        from config.settings import ENROLLMENT_DB_PATH
        set_audit_store(VerificationAuditStore(ENROLLMENT_DB_PATH))
    except Exception:
        logger.exception("Failed to initialize verification audit store")

    return system


@asynccontextmanager
async def lifespan(app: FastAPI):
    system = _init_proctoring_system()
    app.state.system = system
    logger.info(
        "%s v%s ready (env=%s, debug=%s)",
        APP_NAME, APP_VERSION,
        "production" if IS_PRODUCTION else "development",
        DEBUG,
    )
    yield
    logger.info("Shutting down %s", APP_NAME)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------
def create_app() -> FastAPI:
    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description=(
            "REST API for face detection, face verification, behavior "
            "analysis, multi-reference enrollment, and session-based "
            "proctoring. Most endpoints require a Bearer token configured "
            "via the API_KEY environment variable."
        ),
        docs_url="/docs",
        redoc_url=None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Rate limiting -- must be wired before CORS so the limiter sees real
    # client IPs even on preflighted requests.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # CORS. Warn loudly if a production deployment is using "*" -- that
    # combination effectively turns off origin-based browser protection.
    if IS_PRODUCTION and "*" in CORS_ORIGINS:
        logger.warning(
            "CORS_ORIGINS contains '*' in production. Browsers will accept "
            "cross-origin calls from ANY domain. Set CORS_ORIGINS to your "
            "Moodle origin(s) before exposing this service publicly."
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS if CORS_ORIGINS != ["*"] else ["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization", "Accept", "X-API-Key"],
    )

    # Body-size guard (50 MB). Starlette has no built-in cap.
    @app.middleware("http")
    async def limit_request_body(request: Request, call_next):
        cl = request.headers.get("content-length")
        if cl is not None:
            try:
                if int(cl) > MAX_BODY_BYTES:
                    return JSONResponse(
                        status_code=413,
                        content={"error": "Request body too large",
                                 "max_bytes": MAX_BODY_BYTES},
                    )
            except ValueError:
                pass
        return await call_next(request)

    # X-Request-ID: accept one from the client (so callers can correlate
    # client-side logs with ours), or generate a new one. Attached to
    # request.state so the audit log can record it, and echoed back as a
    # response header.
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        rid = request.headers.get("X-Request-ID", "").strip() or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # X-Process-Time: free ops visibility. The value is the wall-clock time
    # the request spent inside the app, in seconds, with millisecond precision.
    @app.middleware("http")
    async def process_time_middleware(request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.4f}"
        return response

    # ------------------------------------------------------------------ auth/security
    # Declare the Bearer scheme so Swagger UI renders the Authorize button.
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        schema = get_openapi(
            title=APP_NAME,
            version=APP_VERSION,
            description=app.description,
            routes=app.routes,
        )
        schema.setdefault("components", {})
        schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API-Token",
                "description":
                    "Provide the token from the API_KEY environment variable.",
            }
        }
        schema["security"] = [{"BearerAuth": []}]
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[assignment]

    # ------------------------------------------------------------------ error shape
    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        """Re-shape pydantic validation errors to ``{"error": ...}``.

        FastAPI's default is ``{"detail": [...]}``, which would break existing
        clients that parse ``response.error``.
        """
        # Try to surface a useful summary -- first missing field if any.
        errors = exc.errors()
        if errors:
            first = errors[0]
            loc = ".".join(str(p) for p in first.get("loc", [])[1:])
            msg = first.get("msg", "validation error")
            summary = f"{loc}: {msg}" if loc else msg
        else:
            summary = "Invalid request"
        return JSONResponse(
            status_code=422,
            content={"error": summary, "details": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
        # If detail is already a dict (auth-style), pass it through. Otherwise
        # wrap a plain string in {"error": ...} for shape consistency.
        if isinstance(exc.detail, dict):
            content = exc.detail
        else:
            content = {"error": str(exc.detail)}
        return JSONResponse(status_code=exc.status_code, content=content,
                            headers=getattr(exc, "headers", None) or None)

    # ------------------------------------------------------------------ routers
    app.include_router(proctoring_api)
    app.include_router(moodle_api)

    # ------------------------------------------------------------------ root + health
    @app.get("/", tags=["Internal"], summary="Service banner")
    def index():
        return {
            "app": APP_NAME,
            "version": APP_VERSION,
            "status": "running",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "health": "/health",
        }

    @app.get("/healthz", tags=["Internal"], summary="Liveness probe")
    @limiter.exempt
    def liveness(request: Request):
        """Always 200 while the process is alive. Use this for orchestrator
        liveness checks (Kubernetes liveness, Docker restart policy, etc.).
        ``/health`` is the *readiness* probe that also checks models."""
        return {"status": "alive", "timestamp": time.time()}

    @app.get("/health", tags=["Internal"], summary="Readiness probe (gated on models loaded)")
    @limiter.exempt
    def public_health(request: Request):
        """Readiness probe. Returns **503** if either the face detector or
        face recognizer failed to load — so a load balancer will route
        traffic away from a pod whose models did not come up."""
        system = getattr(app.state, "system", None)
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
        detector_loaded = False
        recognizer_loaded = False
        if system is not None and getattr(system, "model_manager", None) is not None:
            try:
                info = system.model_manager.get_model_info()
                detector_loaded = bool(info["detector"]["loaded"])
                recognizer_loaded = bool(info["recognizer"]["loaded"])
                models = {
                    "detector_backend": info["detector"]["backend"],
                    "detector_loaded": detector_loaded,
                    "recognizer_backend": info["recognizer"]["backend"],
                    "recognizer_loaded": recognizer_loaded,
                }
            except Exception:
                logger.exception("Could not collect model info for /health")

        ready = detector_loaded and recognizer_loaded
        body = {
            "status": "healthy" if ready else "unhealthy",
            "ready": ready,
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
        }
        return JSONResponse(status_code=200 if ready else 503, content=body)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn
    logger.info("Starting %s on %s:%s", APP_NAME, HOST, PORT)
    uvicorn.run(
        "app:app", host=HOST, port=PORT, reload=DEBUG, log_config=None,
    )
