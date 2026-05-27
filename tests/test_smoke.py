"""
Smoke tests covering the main HTTP contract:

* health probes (/health is gated on models loaded, /healthz is not)
* OpenAPI spec is clean OpenAPI 3.x with the Bearer security scheme
* Bearer auth: missing / wrong / valid
* Pydantic validation errors are reshaped to ``{"error": ...}``
* Enrollment lifecycle (POST -> GET -> DELETE)
* /verify/face validates "exactly one of reference_face / user_id"
* Rate-limit headers are present and /healthz is exempt
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# 1. Health endpoints
# ---------------------------------------------------------------------------
def test_healthz_always_alive(client):
    """/healthz only checks that the process is up. No auth, no gating."""
    r = client.get("/healthz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "alive"


def test_health_reports_models_when_loaded(client):
    """/health is the readiness probe. With models loaded it returns 200
    and reports the active detector + recognizer backends."""
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["ready"] is True
    assert body["status"] == "healthy"
    assert body["models"]["detector_loaded"] is True
    assert body["models"]["recognizer_loaded"] is True


# ---------------------------------------------------------------------------
# 2. OpenAPI spec
# ---------------------------------------------------------------------------
def test_openapi_is_pure_v3_with_bearer_scheme(client):
    spec = client.get("/openapi.json").json()
    # No flasgger-era leftovers
    assert "swagger" not in spec
    assert "definitions" not in spec
    assert spec["openapi"].startswith("3.")
    # Bearer security advertised so Swagger UI renders an Authorize button
    assert "BearerAuth" in spec["components"]["securitySchemes"]
    # Sanity: at least the core endpoints exist
    for path in ("/detect/faces", "/verify/face", "/enroll/face", "/health"):
        assert path in spec["paths"], f"missing {path} in openapi"


# ---------------------------------------------------------------------------
# 3. Authentication
# ---------------------------------------------------------------------------
def test_auth_required(client, dummy_jpeg_b64):
    r = client.post("/detect/faces", json={"image": dummy_jpeg_b64})
    assert r.status_code == 401
    assert r.json()["error"] == "Unauthorized"


def test_auth_wrong_token(client, dummy_jpeg_b64):
    r = client.post(
        "/detect/faces",
        headers={"Authorization": "Bearer WRONG"},
        json={"image": dummy_jpeg_b64},
    )
    assert r.status_code == 401


def test_auth_via_x_api_key_header(client, dummy_jpeg_b64):
    """X-API-Key fallback header should work too."""
    r = client.post(
        "/detect/faces",
        headers={"X-API-Key": "test-key"},
        json={"image": dummy_jpeg_b64},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# 4. Pydantic validation -> {"error": "..."} reshape
# ---------------------------------------------------------------------------
def test_validation_missing_field(client, auth_headers):
    r = client.post("/detect/faces", headers=auth_headers, json={})
    assert r.status_code == 422
    body = r.json()
    assert "error" in body            # not the default "detail"
    assert "image" in body["error"]   # message points at the missing field


def test_validation_too_many_enroll_images(client, auth_headers, dummy_jpeg_b64):
    """pydantic max_length=5 on EnrollFaceRequest.images."""
    r = client.post(
        "/enroll/face",
        headers=auth_headers,
        json={"user_id": "alice", "images": [dummy_jpeg_b64] * 6},
    )
    assert r.status_code == 422
    assert "error" in r.json()


# ---------------------------------------------------------------------------
# 5. /verify/face validation
# ---------------------------------------------------------------------------
def test_verify_face_requires_exactly_one_reference(client, auth_headers, dummy_jpeg_b64):
    # neither
    r = client.post(
        "/verify/face",
        headers=auth_headers,
        json={"current_face": dummy_jpeg_b64},
    )
    assert r.status_code == 400
    assert "Provide exactly one" in r.json()["error"]

    # both
    r = client.post(
        "/verify/face",
        headers=auth_headers,
        json={
            "current_face": dummy_jpeg_b64,
            "reference_face": dummy_jpeg_b64,
            "user_id": "alice",
        },
    )
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# 6. Enrollment lifecycle (mocked detector so we don't need a real face)
# ---------------------------------------------------------------------------
def test_enrollment_lifecycle(client, auth_headers, dummy_jpeg_b64, fake_detect):
    """Enroll 3 -> GET shows them -> DELETE -> GET 404."""
    user_id = "smoke_test_user"

    # Enroll
    r = client.post(
        "/enroll/face",
        headers=auth_headers,
        json={"user_id": user_id, "images": [dummy_jpeg_b64] * 3},
    )
    assert r.status_code == 201, r.json()
    body = r.json()
    assert body["added_count"] == 3
    assert body["total_references"] == 3

    # Fetch metadata — must not leak embedding values
    r = client.get(f"/enroll/face/{user_id}", headers=auth_headers)
    assert r.status_code == 200
    info = r.json()
    assert info["reference_count"] == 3
    for ref in info["references"]:
        assert "embedding" not in ref, "embedding values must not be returned"

    # Delete
    r = client.delete(f"/enroll/face/{user_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["deleted"] is True

    # Subsequent fetch is 404
    r = client.get(f"/enroll/face/{user_id}", headers=auth_headers)
    assert r.status_code == 404


def test_enrollment_rejects_path_traversal(client, auth_headers, dummy_jpeg_b64):
    r = client.post(
        "/enroll/face",
        headers=auth_headers,
        json={"user_id": "../etc/passwd", "images": [dummy_jpeg_b64]},
    )
    assert r.status_code == 400
    assert "Invalid user_id" in r.json()["error"]


# ---------------------------------------------------------------------------
# 7. Verify against a stored user (mocked detector again)
# ---------------------------------------------------------------------------
def test_verify_by_user_id_returns_diagnostic_scores(
    client, auth_headers, dummy_jpeg_b64, fake_detect,
):
    user_id = "smoke_verify_user"
    client.post(
        "/enroll/face",
        headers=auth_headers,
        json={"user_id": user_id, "images": [dummy_jpeg_b64] * 2},
    )

    r = client.post(
        "/verify/face",
        headers=auth_headers,
        json={"current_face": dummy_jpeg_b64, "user_id": user_id},
    )
    assert r.status_code == 200
    body = r.json()
    details = body["details"]
    assert details["method"] == "arcface_max_similarity_over_references"
    assert details["references_compared"] == 2
    assert isinstance(details["all_scores"], list)
    assert len(details["all_scores"]) == 2


def test_verify_by_user_id_404_when_no_enrollment(
    client, auth_headers, dummy_jpeg_b64, fake_detect,
):
    r = client.post(
        "/verify/face",
        headers=auth_headers,
        json={"current_face": dummy_jpeg_b64, "user_id": "nobody_enrolled"},
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# 8. Rate limiter is wired (headers present, /healthz exempt)
# ---------------------------------------------------------------------------
def test_rate_limit_headers_on_authed_endpoint(client, auth_headers, dummy_jpeg_b64):
    """slowapi adds X-RateLimit-* headers to responses that pass through
    the limiter. /detect/faces should carry them."""
    r = client.post(
        "/detect/faces", headers=auth_headers, json={"image": dummy_jpeg_b64},
    )
    assert r.status_code == 200
    # Headers might be capitalized differently; check case-insensitively.
    header_keys = {k.lower() for k in r.headers.keys()}
    assert "x-ratelimit-limit" in header_keys


def test_healthz_is_exempt_from_rate_limit(client):
    """A flood of /healthz must never come back with 429."""
    for _ in range(50):
        r = client.get("/healthz")
        assert r.status_code == 200, f"unexpected status {r.status_code}"


# ---------------------------------------------------------------------------
# Ops headers: X-Request-ID + X-Process-Time
# ---------------------------------------------------------------------------
def test_request_id_is_generated_when_missing(client):
    """If the client doesn't send X-Request-ID, the server generates one."""
    r = client.get("/healthz")
    rid = r.headers.get("X-Request-ID")
    assert rid, "X-Request-ID header missing on response"
    assert len(rid) >= 8


def test_request_id_echoed_when_supplied(client):
    """If the client supplies one, the server echoes it back unchanged."""
    r = client.get("/healthz", headers={"X-Request-ID": "client-supplied-abc123"})
    assert r.headers.get("X-Request-ID") == "client-supplied-abc123"


def test_process_time_header_present_and_numeric(client):
    """X-Process-Time is a float (seconds) on every response."""
    r = client.get("/healthz")
    pt = r.headers.get("X-Process-Time")
    assert pt is not None, "X-Process-Time header missing"
    assert float(pt) >= 0.0


# ---------------------------------------------------------------------------
# 9. Liveness route -- input validation + graceful degradation in CI
# ---------------------------------------------------------------------------
def test_liveness_rejects_too_few_frames(client, auth_headers, dummy_jpeg_b64):
    """Pydantic min_length=3."""
    r = client.post(
        "/detect/liveness",
        headers=auth_headers,
        json={"frames": [dummy_jpeg_b64] * 2},
    )
    assert r.status_code == 422
    assert "error" in r.json()


def test_liveness_rejects_too_many_frames(client, auth_headers, dummy_jpeg_b64):
    r = client.post(
        "/detect/liveness",
        headers=auth_headers,
        json={"frames": [dummy_jpeg_b64] * 31},
    )
    assert r.status_code == 422


def test_liveness_returns_verdict_or_503(client, auth_headers, dummy_jpeg_b64):
    """If the MediaPipe model file is missing (CI), liveness returns 503
    cleanly. If it's present (local), the analyzer runs and returns a verdict
    with all expected keys. Either way the route shape is locked."""
    r = client.post(
        "/detect/liveness",
        headers=auth_headers,
        json={"frames": [dummy_jpeg_b64] * 5},
    )
    assert r.status_code in (200, 503)
    body = r.json()
    if r.status_code == 200:
        for field in ("is_alive", "total_blinks", "head_movement_pixels",
                      "frames_processed", "reasons_against_liveness"):
            assert field in body, f"missing field: {field}"
        assert isinstance(body["is_alive"], bool)
    else:
        assert "error" in body


# ---------------------------------------------------------------------------
# 10. Verification audit log
# ---------------------------------------------------------------------------
def test_verify_face_writes_audit_row(client, auth_headers, dummy_jpeg_b64, fake_detect):
    """Every /verify/face call should leave a row in the audit log."""
    user_id = "smoke_audit_user"

    # Enroll a user so verify reaches the success path
    client.post(
        "/enroll/face",
        headers=auth_headers,
        json={"user_id": user_id, "images": [dummy_jpeg_b64]},
    )

    # Do two verifies
    for _ in range(2):
        r = client.post(
            "/verify/face",
            headers=auth_headers,
            json={"current_face": dummy_jpeg_b64, "user_id": user_id},
        )
        assert r.status_code == 200

    # Pull the audit trail
    r = client.get(f"/verifications/{user_id}", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] == user_id
    assert body["count"] >= 2
    row = body["verifications"][0]
    # Must record the decision and metadata but never the embedding values
    for field in (
        "ts_utc", "user_id", "method", "match_score", "threshold",
        "matched", "references_compared", "recognizer_backend",
    ):
        assert field in row, f"missing audit field: {field}"
    assert "embedding" not in row
    assert "image" not in row
