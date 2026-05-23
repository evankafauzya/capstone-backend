"""
API authentication.

The backend supports a single bearer-token scheme. The token is read once at
process start from the API_KEY environment variable and is *never* echoed back
to clients (logging, /health, /configuration, Swagger UI). Compare tokens with
hmac.compare_digest to avoid timing attacks.
"""
import hmac
import logging
from functools import wraps

from flask import request, jsonify

from config.settings import API_KEY, API_KEY_REQUIRED

logger = logging.getLogger(__name__)


def _extract_token() -> str:
    """Extract a bearer token from the Authorization header (or X-API-Key)."""
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-API-Key", "").strip()


def _is_valid(token: str) -> bool:
    if not token or not API_KEY:
        return False
    return hmac.compare_digest(token, API_KEY)


def require_api_key(fn):
    """Protect an endpoint with the configured API key.

    Behavior:
      - If API_KEY_REQUIRED is false, the request passes through.
      - Otherwise a valid Bearer token (or X-API-Key header) is required.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not API_KEY_REQUIRED:
            return fn(*args, **kwargs)

        token = _extract_token()
        if not _is_valid(token):
            return jsonify({
                "error": "Unauthorized",
                "message": "Missing or invalid API token.",
                "status": "unauthorized",
            }), 401
        return fn(*args, **kwargs)

    return wrapper
