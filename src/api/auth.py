"""
API authentication.

The backend supports a single bearer-token scheme. The token is read once at
process start from the API_KEY environment variable and is *never* echoed back
to clients (logging, /health, /configuration, Swagger UI). Compare tokens with
hmac.compare_digest to avoid timing attacks.

Use it on a route by adding ``Depends(require_api_key)`` to the signature:

    @router.post("/foo", dependencies=[Depends(require_api_key)])
    def foo(...): ...

or attach the dependency at router-level so every route inherits it.
"""
from __future__ import annotations

import hmac
import logging

from fastapi import HTTPException, Request, status

from config.settings import API_KEY, API_KEY_REQUIRED

logger = logging.getLogger(__name__)


def _extract_token(request: Request) -> str:
    """Extract a bearer token from the Authorization header (or X-API-Key)."""
    auth = request.headers.get("Authorization", "").strip()
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.headers.get("X-API-Key", "").strip()


def _is_valid(token: str) -> bool:
    if not token or not API_KEY:
        return False
    return hmac.compare_digest(token, API_KEY)


def require_api_key(request: Request) -> None:
    """FastAPI dependency that gates a route on a valid bearer token.

    Behavior:
      - If API_KEY_REQUIRED is false, the request passes through.
      - Otherwise a valid Bearer token (or X-API-Key header) is required.
    """
    if not API_KEY_REQUIRED:
        return

    token = _extract_token(request)
    if not _is_valid(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "Unauthorized",
                "message": "Missing or invalid API token.",
                "status": "unauthorized",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
