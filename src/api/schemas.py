"""
Pydantic request/response models for the FastAPI routes.

These types do two things:

1. They are the OpenAPI source of truth — FastAPI generates the Swagger
   documentation directly from them. No docstring annotations needed.

2. They validate incoming request bodies before our handlers run. Missing
   or malformed fields surface as 422 errors with a clear field path; we
   re-shape those errors to ``{"error": ...}`` in app.py so existing
   clients keep working.
"""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Common
# ---------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    """Uniform error shape returned by every route in this app."""
    error: str
    status: Optional[str] = None


class FaceBox(BaseModel):
    x: int
    y: int
    w: int
    h: int
    confidence: float
    landmarks: Optional[Dict[str, List[float]]] = None


# ---------------------------------------------------------------------------
# /detect/faces
# ---------------------------------------------------------------------------
class DetectFacesOptions(BaseModel):
    confidence_threshold: float = 0.6
    return_landmarks: bool = True


class DetectFacesRequest(BaseModel):
    image: str = Field(..., description="Base64 image (raw or data URI).")
    options: DetectFacesOptions = Field(default_factory=DetectFacesOptions)


class DetectFacesResponse(BaseModel):
    faces: List[FaceBox]
    face_count: int
    landmarks: List[Dict[str, List[float]]] = Field(default_factory=list)
    processing_time_ms: float
    backend: Dict[str, str]


# ---------------------------------------------------------------------------
# /verify/face
# ---------------------------------------------------------------------------
class VerifyFaceOptions(BaseModel):
    match_threshold: Optional[float] = None
    return_embeddings: bool = False


class VerifyFaceRequest(BaseModel):
    """Provide the live capture as ``current_face`` (one frame) **or**
    ``current_frames`` (several frames; the best-scoring frame wins). Exactly
    one of ``reference_face`` / ``user_id`` selects what to compare against."""
    current_face: Optional[str] = Field(
        default=None, description="Base64 current capture (single frame).",
    )
    current_frames: Optional[List[str]] = Field(
        default=None, min_length=1, max_length=10,
        description=(
            "Base64 current captures; the highest-scoring frame is used. Send a "
            "few frames to survive transient glasses glare / screen reflection "
            "that would sink a single frame."
        ),
    )
    reference_face: Optional[str] = Field(
        default=None, description="Base64 reference image (single-reference mode)."
    )
    user_id: Optional[str] = Field(
        default=None, description="User id to look up previously enrolled references.",
    )
    options: VerifyFaceOptions = Field(default_factory=VerifyFaceOptions)


class VerifyFaceResponse(BaseModel):
    model_config = ConfigDict(extra="allow")  # for optional ``embeddings`` field
    is_match: bool
    match_score: float
    confidence: float
    details: Dict[str, Any]


# ---------------------------------------------------------------------------
# /detect/behavior
# ---------------------------------------------------------------------------
class DetectBehaviorOptions(BaseModel):
    detect_multiple_faces: bool = True
    detect_eye_gaze: bool = True
    detect_head_pose: bool = True


class DetectBehaviorRequest(BaseModel):
    image: str
    options: DetectBehaviorOptions = Field(default_factory=DetectBehaviorOptions)


class DetectBehaviorResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    multiple_faces_detected: bool
    face_count: int
    no_face_detected: bool
    unusual_eye_gaze: bool
    unusual_head_pose: bool
    suspicious_indicators: List[str]
    risk_level: str
    processing_time_ms: float
    backend: Dict[str, str]


# ---------------------------------------------------------------------------
# /embeddings
# ---------------------------------------------------------------------------
class EmbeddingsRequest(BaseModel):
    image: str


class EmbeddingsResponse(BaseModel):
    embeddings: List[float]
    embedding_dim: int
    model_used: str
    processing_time_ms: Optional[float] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# /enroll/face — manual + guided
# ---------------------------------------------------------------------------
class EnrollFaceRequest(BaseModel):
    user_id: str = Field(
        ..., description="Up to 64 chars, letters/digits/underscore/dash.",
    )
    images: List[str] = Field(
        ..., min_length=1, max_length=5,
        description="Base64-encoded face photos.",
    )


class EnrollFaceGuidedRequest(BaseModel):
    user_id: str = Field(
        ..., description="Up to 64 chars, letters/digits/underscore/dash.",
    )
    frames: List[str] = Field(
        ..., min_length=5, max_length=20,
        description="Base64-encoded frames from the registration clip.",
    )
    target_count: int = Field(default=3, ge=1, le=5)
    replace_existing: bool = False


class EnrollSkipped(BaseModel):
    index: int
    reason: str


class EnrollResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    user_id: str
    added: List[str]
    added_count: int
    total_references: int
    skipped: List[EnrollSkipped] = Field(default_factory=list)
    model_backend: str


class EnrollmentReferenceInfo(BaseModel):
    id: str
    added_at: str
    face_w: int
    face_h: int
    face_confidence: float


class EnrollmentInfoResponse(BaseModel):
    user_id: str
    enrolled_at: str
    updated_at: str
    embedding_dim: int
    model_backend: str
    reference_count: int
    references: List[EnrollmentReferenceInfo]


class DeleteEnrollmentResponse(BaseModel):
    user_id: str
    deleted: bool


# ---------------------------------------------------------------------------
# /detect/liveness
# ---------------------------------------------------------------------------
class DetectLivenessRequest(BaseModel):
    frames: List[str] = Field(
        ..., min_length=3, max_length=30,
        description="3-30 base64 frames from a short webcam clip (~2-3 s @ 5 FPS).",
    )


class DetectLivenessResponse(BaseModel):
    is_alive: bool
    total_blinks: int
    head_movement_pixels: float
    frames_processed: int
    frames_no_face: int
    reasons_against_liveness: List[str]
    processing_time_ms: float


# ---------------------------------------------------------------------------
# /batch/process
# ---------------------------------------------------------------------------
class BatchProcessRequest(BaseModel):
    images: List[str]
    task: Literal["face_detection", "behavior_analysis"] = "face_detection"


class BatchProcessResponse(BaseModel):
    results: List[Dict[str, Any]]
    processed_count: int
    failed_count: int
    backend: Dict[str, str]


# ---------------------------------------------------------------------------
# Proctoring routes (session lifecycle)
# ---------------------------------------------------------------------------
class StartSessionRequest(BaseModel):
    session_id: str
    user_id: str


class StartSessionResponse(BaseModel):
    message: str
    session_id: str
    user_id: str
    timestamp: float


class UpdateConfigurationRequest(BaseModel):
    capture_interval: Optional[int] = None
    reverification_interval: Optional[int] = None
    max_faces_allowed: Optional[int] = None


# ---------------------------------------------------------------------------
# Health / root
# ---------------------------------------------------------------------------
class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: str
    service: str
    version: str
    timestamp: float
    gpu_available: bool
    gpu_device: str


class RootResponse(BaseModel):
    app: str
    version: str
    status: str
    docs: str
    openapi: str
    health: str
