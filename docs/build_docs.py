"""
Generate beginner-friendly PDF documentation for the Moodle Proctoring AI
Backend in English and Bahasa Indonesia.

Run:
    python docs/build_docs.py

Output:
    docs/proctoring-backend-guide_EN.pdf
    docs/proctoring-backend-guide_ID.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Table,
    TableStyle,
)

DOCS_DIR = Path(__file__).resolve().parent
BRAND_COLOR = colors.HexColor("#1f4e79")
ACCENT_COLOR = colors.HexColor("#d35400")
LIGHT_BG = colors.HexColor("#f4f6f8")
MONO_BG = colors.HexColor("#1e1e1e")
MONO_FG = colors.HexColor("#f8f8f2")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def make_styles():
    base = getSampleStyleSheet()
    styles = {}

    styles["title"] = ParagraphStyle(
        "title", parent=base["Title"], fontSize=24, leading=30,
        textColor=BRAND_COLOR, spaceAfter=6, alignment=TA_LEFT,
    )
    styles["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"], fontSize=12, leading=16,
        textColor=colors.grey, spaceAfter=24,
    )
    styles["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontSize=18, leading=22,
        textColor=BRAND_COLOR, spaceBefore=18, spaceAfter=10,
    )
    styles["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=14, leading=18,
        textColor=BRAND_COLOR, spaceBefore=12, spaceAfter=6,
    )
    styles["h3"] = ParagraphStyle(
        "h3", parent=base["Heading3"], fontSize=11.5, leading=15,
        textColor=ACCENT_COLOR, spaceBefore=8, spaceAfter=4,
    )
    styles["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontSize=10.5, leading=15,
        spaceAfter=6, alignment=TA_LEFT,
    )
    styles["bullet"] = ParagraphStyle(
        "bullet", parent=styles["body"], leftIndent=14,
        bulletIndent=2, spaceAfter=3,
    )
    styles["mono"] = ParagraphStyle(
        "mono", parent=base["Code"], fontName="Courier", fontSize=8.5,
        leading=11, leftIndent=8, rightIndent=8, textColor=MONO_FG,
        backColor=MONO_BG, borderPadding=8, spaceBefore=4, spaceAfter=10,
    )
    styles["note"] = ParagraphStyle(
        "note", parent=styles["body"], leftIndent=10, rightIndent=10,
        backColor=LIGHT_BG, borderPadding=8, borderColor=BRAND_COLOR,
        borderWidth=0, spaceBefore=4, spaceAfter=10,
    )
    return styles


STYLES = make_styles()


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------
def p(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, STYLES[style])


def code(text: str) -> Preformatted:
    return Preformatted(text, STYLES["mono"])


def bullets(items: list[str]) -> list[Paragraph]:
    return [Paragraph(f"&#8226; {item}", STYLES["bullet"]) for item in items]


def kv_table(rows: list[tuple[str, str]], col_widths=(4.8 * cm, 11.2 * cm)) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", STYLES["body"]),
             Paragraph(v, STYLES["body"])] for k, v in rows]
    table = Table(data, colWidths=col_widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def endpoint_table(rows: list[tuple[str, str, str]]) -> Table:
    head = [Paragraph(f"<b>{h}</b>", STYLES["body"]) for h in ("Method", "Path", "Description")]
    data = [head] + [[Paragraph(m, STYLES["body"]),
                      Paragraph(f"<font face='Courier'>{path}</font>", STYLES["body"]),
                      Paragraph(desc, STYLES["body"])] for m, path, desc in rows]
    table = Table(data, colWidths=(2 * cm, 6.5 * cm, 7.5 * cm), repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm,
                      f"Moodle Proctoring AI Backend - Page {doc.page}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, "v2.1")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# ASCII architecture diagram (shared by both languages)
# ---------------------------------------------------------------------------
ARCHITECTURE_DIAGRAM = """+----------------------------------------------------------+
|                  CLIENT  (Moodle / curl)                 |
|             Authorization: Bearer <API_KEY>              |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|                 FASTAPI APP  (app.py)                    |
|    CORS  |  Swagger UI /docs  |  /openapi.json           |
+----------------------------------------------------------+
                            |
                            v
+----------------------------------------------------------+
|           src/api/auth.py  (Bearer token check)          |
+----------------------------------------------------------+
                            |
        +-------------------+--------------------+
        v                                        v
+---------------------+              +------------------------+
| moodle_routes.py    |              | proctoring_routes.py   |
|  /detect/faces      |              |  /session/start  /stop |
|  /verify/face       |              |  /video/frame  /stream |
|  /embeddings        |              |  /warnings             |
|  /enroll/face       |              |  /configuration        |
|  /enroll/face/      |              |  /system-info          |
|       guided        |              |                        |
|  /detect/behavior   |              |                        |
+---------------------+              +------------------------+
        |                                        |
        +-------------------+--------------------+
                            v
+----------------------------------------------------------+
|              src/core/orchestrator.py                    |
+----------------------------------------------------------+
            |                                |
            v                                v
+-----------------------+        +-------------------------+
|  ModelManager         |        |  FaceEnrollmentStore    |
|  (src/core)           |        |  (src/services)         |
|                       |        |                         |
|  YOLO  -> bbox        |        |  SQLite database        |
|  Aligner -> 112x112   |        |  data/enrollments.db    |
|  ArcFace -> 512-d     |        |  users +                |
|  embedding            |        |  face_references        |
+-----------------------+        +-------------------------+
"""


# ---------------------------------------------------------------------------
# API endpoint tables
# ---------------------------------------------------------------------------
PUBLIC_ENDPOINTS = [
    ("GET",  "/health",          "Liveness probe (no auth)"),
    ("GET",  "/docs",            "Interactive Swagger UI"),
    ("GET",  "/openapi.json",    "Raw OpenAPI 3 spec"),
    ("POST", "/detect/faces",    "Detect faces in a base64 image (YOLO)"),
    ("POST", "/verify/face",     "Compare a current face to a reference image OR an enrolled user_id"),
    ("POST", "/detect/behavior", "Suspicious-behavior analysis on a frame"),
    ("POST", "/embeddings",      "Compute a 512-d ArcFace embedding for the largest face"),
    ("POST", "/batch/process",   "Run a task across multiple frames at once"),
]

ENROLLMENT_ENDPOINTS = [
    ("POST",   "/enroll/face",
        "Append 1-5 reference photos for a user (max 10 total)."),
    ("POST",   "/enroll/face/guided",
        "Submit 5-20 frames from a supervised registration clip; the server "
        "picks the best (and most varied) frames automatically."),
    ("GET",    "/enroll/face/&lt;user_id&gt;",
        "Get enrollment metadata for a user (never returns embedding values)."),
    ("DELETE", "/enroll/face/&lt;user_id&gt;",
        "Delete all enrolled references for a user."),
]

INTERNAL_ENDPOINTS = [
    ("POST", "/api/proctoring/session/start",        "Start a new session"),
    ("POST", "/api/proctoring/session/stop",         "Stop session + generate report"),
    ("GET",  "/api/proctoring/session/status",       "Current session status"),
    ("GET",  "/api/proctoring/session/report",       "Current session report"),
    ("GET",  "/api/proctoring/video/frame",          "Latest frame as JPEG"),
    ("GET",  "/api/proctoring/video/stream",         "Live MJPEG stream"),
    ("GET",  "/api/proctoring/face-detection/stats", "Detector statistics"),
    ("GET",  "/api/proctoring/eye-tracking/stats",   "Eye-tracker statistics"),
    ("GET",  "/api/proctoring/warnings",             "Latest warnings"),
    ("GET",  "/api/proctoring/configuration",        "Runtime config (safe)"),
    ("PUT",  "/api/proctoring/configuration",        "Update mutable values"),
    ("GET",  "/api/proctoring/system-info",          "Model + alignment + device info"),
]


# ===========================================================================
#                                ENGLISH
# ===========================================================================
def build_english() -> list:
    story = []

    story.append(p("Moodle Proctoring AI Backend", "title"))
    story.append(p("Beginner's guide &middot; Architecture, flow, enrollment, deployment, and API",
                   "subtitle"))

    # ---- 1. What is this ----
    story.append(p("1. What is this backend?", "h1"))
    story.append(p(
        "This project is a Python (FastAPI) backend that powers AI-based "
        "proctoring for online exams. It exposes a REST API for face "
        "detection, face verification, behavior analysis, student "
        "enrollment, and exam-session management."
    ))
    story.append(p("In one sentence: <b>Moodle (or any client) sends an image, "
                   "and the backend tells you whether the student is alone, "
                   "facing the screen, and matches the registered identity.</b>"))
    story.append(p("Key features:", "h3"))
    story.extend(bullets([
        "YOLO-based face detector - accurate, no false positives on noise.",
        "MediaPipe face alignment - eyes always horizontal before recognition.",
        "ArcFace 512-d embeddings (ResNet50, 1500 identities, 96.77% val acc).",
        "Multi-reference enrollment - register a student with 3-5 photos and "
        "verify with the best-matching reference.",
        "Bearer-token authentication, Swagger UI, Docker-ready.",
    ]))

    # ---- 2. Glossary ----
    story.append(p("2. Glossary (read this first)", "h1"))
    story.append(p(
        "Face recognition systems use jargon. If you have not worked on one "
        "before, these are the only terms you need to follow this guide."))
    story.append(kv_table([
        ("Face detection",
            "Finding <i>where</i> a face is in an image. Output: a bounding "
            "box (x, y, width, height) plus a confidence score. The backend "
            "uses YOLO for this."),
        ("Face recognition",
            "Figuring out <i>who</i> the face belongs to. We do this in two "
            "steps: turn the face into a vector (embedding), then compare "
            "embeddings."),
        ("Embedding",
            "A list of 512 floating-point numbers (a vector) that summarizes "
            "what a face looks like. Two photos of the same person produce "
            "very similar embeddings; two different people produce very "
            "different ones."),
        ("Face alignment",
            "Rotating and scaling the face crop so the eyes are always at "
            "the same horizontal positions before computing the embedding. "
            "This makes the embedding much more stable."),
        ("Cosine similarity",
            "A number between -1 and 1 that measures how similar two "
            "embeddings are. 1.0 = identical, around 0.5 = same person "
            "different photo, below ~0.3 = different people."),
        ("Verification",
            "Checking whether a live face matches a known identity "
            "(1-to-1 comparison)."),
        ("Enrollment",
            "The privileged, one-time step of recording a student's "
            "reference embeddings so we have something to verify against later."),
    ]))

    # ---- 3. Architecture ----
    story.append(p("3. Architecture (the big picture)", "h1"))
    story.append(p(
        "The backend is organized in layers. A request travels from top to "
        "bottom: it enters the FastAPI app, passes through authentication, "
        "gets routed to a handler, and the handler talks to the orchestrator "
        "which owns the AI models and the enrollment store."
    ))
    story.append(code(ARCHITECTURE_DIAGRAM))

    story.append(p("Folder map:", "h3"))
    story.append(kv_table([
        ("app.py",                  "FastAPI application factory + Swagger setup."),
        ("asgi.py",                 "ASGI entrypoint for Gunicorn + the Uvicorn worker."),
        ("config/settings.py",      "Reads .env, fails fast if secrets are missing."),
        ("src/api/auth.py",         "Bearer-token dependency used by every protected route."),
        ("src/api/moodle_routes.py",
            "Moodle-facing endpoints: /detect/*, /verify/face, /embeddings, "
            "/enroll/face (all 4 variants), /batch/process."),
        ("src/api/proctoring_routes.py",
            "Internal endpoints for the in-process session lifecycle."),
        ("src/core/orchestrator.py",
            "Coordinates detectors + session manager + report generator."),
        ("src/core/model_manager.py",
            "Loads YOLO + RetinaFace + ArcFace + aligner; picks the best detector."),
        ("src/models/yolo_face_detector.py",
            "Ultralytics YOLO wrapper (preferred face detector)."),
        ("src/models/retinaface.py / face_detector.py",
            "RetinaFace fallback architecture and inference wrapper."),
        ("src/models/face_aligner.py",
            "MediaPipe FaceLandmarker + similarity transform to 112x112."),
        ("src/models/arcface.py",
            "FaceEmbeddingNet (ResNet50 + 512-d projection neck)."),
        ("src/models/face_recognizer.py",
            "End-to-end: align + embed + cosine similarity."),
        ("src/services/face_enrollment.py",
            "SQLite-backed enrollment store. One database file at "
            "<font face='Courier'>data/enrollments.db</font>."),
        ("Dockerfile, docker-compose.yml",
            "Containerized deployment with persistent volumes for "
            "models, reports, logs, and the enrollment database."),
    ]))

    # ---- 4. Request flow ----
    story.append(PageBreak())
    story.append(p("4. How a verify request flows end-to-end", "h1"))
    story.append(p(
        "Suppose a client calls <font face='Courier'>POST /verify/face</font> "
        "with a base64 image and a <font face='Courier'>user_id</font> that "
        "was previously enrolled. Step by step:"
    ))
    story.extend(bullets([
        "<b>1. Auth.</b> The <font face='Courier'>require_api_key</font> "
        "dependency compares the <font face='Courier'>Authorization: Bearer "
        "...</font> header to <font face='Courier'>API_KEY</font> using "
        "<font face='Courier'>hmac.compare_digest</font>. Wrong token: 401.",
        "<b>2. Decoding.</b> The base64 string is decoded into an OpenCV "
        "image (numpy array, BGR).",
        "<b>3. Detection.</b> YOLO runs on the image and returns face "
        "bounding boxes. The biggest box above 0.5 confidence wins. "
        "No face: response says <i>no_face_in_current_frame</i>.",
        "<b>4. Alignment.</b> The cropped face is passed to MediaPipe "
        "FaceLandmarker, which finds eyes/nose/mouth landmarks. A "
        "similarity transform rotates and scales the face so the eyes are "
        "at canonical positions in a 112x112 image.",
        "<b>5. Embedding.</b> The aligned 112x112 image goes through "
        "ArcFace, producing a 512-d L2-normalized vector.",
        "<b>6. Lookup.</b> All previously enrolled embeddings for "
        "<font face='Courier'>user_id</font> are loaded from SQLite.",
        "<b>7. Comparison.</b> Cosine similarity is computed against every "
        "stored reference. The <b>maximum</b> score is returned, plus mean "
        "and per-reference scores in <font face='Courier'>details</font>.",
        "<b>8. Response.</b> <font face='Courier'>{is_match, match_score, "
        "details}</font>. <font face='Courier'>is_match</font> is true if "
        "the best score crosses the threshold (default 0.4).",
    ]))

    # ---- 5. Prerequisites ----
    story.append(p("5. Prerequisites", "h1"))
    story.extend(bullets([
        "Python 3.11+ (only needed if you do not use Docker).",
        "Docker + Docker Compose (recommended for deployment).",
        "Pre-trained model files placed in "
        "<font face='Courier'>models_data/</font>:",
    ]))
    story.append(kv_table([
        ("face_detection_yolo.pt",
            "Ultralytics YOLO face detector. <b>Preferred detector.</b>"),
        ("face_detection_model.pth",
            "RetinaFace MobileNet0.25. Used as fallback if YOLO is missing."),
        ("face_recognition_model.pth",
            "ArcFace ResNet50 backbone (also contains the 1500-class head)."),
        ("face_landmarker.task",
            "MediaPipe FaceLandmarker. Required for face alignment; "
            "without it, the recognizer falls back to plain resize and "
            "accuracy drops."),
    ]))

    # ---- 6. First-time setup ----
    story.append(p("6. First-time setup", "h1"))
    story.append(p("Step 1 - clone and enter the project:", "h3"))
    story.append(code("git clone https://github.com/evankafauzya/capstone-backend.git\n"
                      "cd capstone-backend"))
    story.append(p("Step 2 - drop the four model files into "
                   "<font face='Courier'>models_data/</font> (they are not "
                   "in the git repo because they are large).", "h3"))
    story.append(p("Step 3 - copy the environment template:", "h3"))
    story.append(code("cp .env.example .env"))
    story.append(p("Step 4 - generate strong secrets:", "h3"))
    story.append(code("python -c \"import secrets; print(secrets.token_urlsafe(48))\""))
    story.append(p("Run that command twice and paste the outputs as "
                   "<font face='Courier'>SECRET_KEY</font> and "
                   "<font face='Courier'>API_KEY</font> in your .env file."))
    story.append(p(
        "<b>Why?</b> In production the app refuses to start without these "
        "values. <font face='Courier'>.env</font> is already in "
        "<font face='Courier'>.gitignore</font> - never commit it.", "note"))

    # ---- 7. Configuration ----
    story.append(p("7. Configuration reference", "h1"))
    story.append(kv_table([
        ("ENVIRONMENT",
            "development | production. In production, missing secrets crash on boot."),
        ("DEBUG",                  "true / false. Auto-on in development."),
        ("HOST / PORT",            "Bind address and port (default 0.0.0.0:5000)."),
        ("SECRET_KEY",             "Session signing key. Required in production."),
        ("API_KEY",                "Bearer token. Required in production."),
        ("API_KEY_REQUIRED",       "If false, auth is bypassed (dev only)."),
        ("CORS_ORIGINS",           "Comma-separated origins. Use * only locally."),
        ("LOG_LEVEL",              "DEBUG, INFO, WARNING, ERROR."),
        ("MODELS_DIR",             "Where the .pt/.pth/.task files live (default models_data/)."),
        ("DATA_DIR",
            "Where the SQLite enrollment DB lives (default data/). "
            "Mount this as a volume in production so enrollments survive container restarts."),
        ("ENROLLMENT_DB_PATH",     "Override the default DB location."),
        ("FACE_DETECTION_CONFIDENCE", "Per-detector confidence cutoff (default 0.5)."),
        ("FACE_MATCH_THRESHOLD",
            "Cosine threshold for verification. <b>Default 0.4</b>, which is "
            "well-tuned for webcam-vs-registered-photo conditions. Raise to "
            "0.5+ only if both photos come from the same source."),
        ("MAX_FACES_ALLOWED",      "Allowed faces in frame; more triggers a warning."),
    ]))

    # ---- 8. Running locally ----
    story.append(PageBreak())
    story.append(p("8. Running locally (without Docker)", "h1"))
    story.append(code(
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate       # macOS/Linux\n"
        "pip install -r requirements.txt\n"
        "python app.py"
    ))
    story.append(p("Then open:"))
    story.extend(bullets([
        "<font face='Courier'>http://localhost:5000/</font> - service banner.",
        "<font face='Courier'>http://localhost:5000/health</font> - health "
        "check (shows which detector / recognizer backend is active).",
        "<font face='Courier'>http://localhost:5000/docs</font> - Swagger UI.",
    ]))

    # ---- 9. Docker ----
    story.append(p("9. Production deployment with Docker", "h1"))
    story.append(p("This is the recommended path - one command, repeatable, "
                   "isolates the app from the host."))
    story.append(p("Step 1 - make sure .env is filled in and the model files "
                   "are in <font face='Courier'>models_data/</font>.", "h3"))
    story.append(p("Step 2 - build and start:", "h3"))
    story.append(code("docker compose up -d --build"))

    story.append(p("Step 3 - verify health:", "h3"))
    story.append(code("curl http://localhost:5000/health"))

    story.append(p("Useful commands:", "h3"))
    story.append(code(
        "docker compose logs -f             # tail logs\n"
        "docker compose ps                  # status\n"
        "docker compose down                # stop\n"
        "docker compose up -d --build       # rebuild after code change"
    ))

    story.append(p("Volume mounts:", "h3"))
    story.append(kv_table([
        ("./models_data &#8594; /app/models_data",
         "Read-only mount so you can swap models without rebuilding."),
        ("./reports &#8594; /app/reports",
         "Persists generated session reports."),
        ("./logs &#8594; /app/logs",
         "Persists rotating application logs."),
        ("./data &#8594; /app/data",
         "Persists the SQLite enrollment database. <b>Critical</b> - without "
         "this mount, every container restart wipes all enrollments."),
    ]))

    # ---- 10. Enrollment ----
    story.append(p("10. Enrollment - register a student", "h1"))
    story.append(p(
        "Before you can <i>verify</i> a student, you need to <i>enroll</i> "
        "them. Enrollment is the one-time, privileged step that links a "
        "<font face='Courier'>user_id</font> to a few reference photos. "
        "After that, every verify call simply checks the live face against "
        "those references."
    ))
    story.append(p(
        "<b>Important:</b> never auto-enroll from quiz captures. If you "
        "do, the first person to log in as <i>alice</i> becomes <i>alice</i> "
        "forever - even an impostor. Enrollment must be a supervised, "
        "deliberate step.", "note"))

    story.append(p("Two ways to enroll", "h2"))
    story.append(p("<b>Easy path (recommended): guided enrollment.</b>", "h3"))
    story.append(p(
        "The frontend records a short clip of the student (typically 5 "
        "seconds at ~3 frames per second) and sends 5-20 frames at once. "
        "The server detects faces, embeds them, picks the best and most "
        "varied frames automatically, and stores them. The student does "
        "not need to do anything special - just sit in front of the camera."
    ))
    story.append(code(
        "POST /enroll/face/guided\n"
        "Authorization: Bearer <API_KEY>\n"
        "Content-Type: application/json\n"
        "\n"
        "{\n"
        '  "user_id": "student_001",\n'
        '  "frames":  ["...base64...", "...base64...", ...],\n'
        '  "target_count": 3,\n'
        '  "replace_existing": true\n'
        "}"
    ))
    story.append(p(
        "<b>How the server picks the best frames:</b> first it filters out "
        "frames with no face or low detection confidence. Then it picks "
        "the highest-quality (biggest + most confident) frame as the anchor. "
        "Each subsequent pick maximizes the minimum cosine distance to the "
        "already-picked set - this is called <i>farthest-point sampling</i> "
        "and it gives you references that cover different head angles "
        "instead of three near-identical frontal shots."))

    story.append(p("<b>Manual path: explicit enrollment.</b>", "h3"))
    story.append(p(
        "If the frontend already has 3-5 curated photos (for example from "
        "a school's student-ID database), it can submit them directly:"))
    story.append(code(
        "POST /enroll/face\n"
        "{\n"
        '  "user_id": "student_001",\n'
        '  "images": ["...base64...", "...base64...", "...base64..."]\n'
        "}"
    ))
    story.append(p(
        "Each call appends references (does not replace). The hard cap is "
        "10 references per user."))

    story.append(p("Enrollment endpoints (all under "
                   "<font face='Courier'>/enroll/face</font>):", "h2"))
    story.append(endpoint_table(ENROLLMENT_ENDPOINTS))

    # ---- 11. Verification with user_id ----
    story.append(p("11. Verification - checking a student during a quiz", "h1"))
    story.append(p(
        "Once enrolled, the frontend captures a live frame and asks the "
        "server: <i>does this look like student_001?</i>"))
    story.append(code(
        "POST /verify/face\n"
        "Authorization: Bearer <API_KEY>\n"
        "Content-Type: application/json\n"
        "\n"
        "{\n"
        '  "current_face": "...base64 of current webcam frame...",\n'
        '  "user_id": "student_001"\n'
        "}"
    ))
    story.append(p("Response (success case):"))
    story.append(code(
        "{\n"
        '  "is_match": true,\n'
        '  "match_score": 0.6730,\n'
        '  "details": {\n'
        '    "method": "arcface_max_similarity_over_references",\n'
        '    "threshold_used": 0.4,\n'
        '    "user_id": "student_001",\n'
        '    "references_compared": 3,\n'
        '    "best_reference_id": "84b3176944c3",\n'
        '    "best_score": 0.6730,\n'
        '    "mean_score": 0.5142,\n'
        '    "all_scores": [0.6730, 0.5121, 0.3575]\n'
        "  }\n"
        "}"
    ))
    story.append(p(
        "Because we compare against <b>all</b> enrolled references and take "
        "the maximum, the match score is much more stable across head "
        "angles than against a single reference photo. The "
        "<font face='Courier'>all_scores</font> field is a great debug "
        "signal: if every score is low, the photo really is a different "
        "person; if one is high and the others low, the student's head is "
        "at an angle that resembles one of the references."))

    # ---- 12. API reference ----
    story.append(PageBreak())
    story.append(p("12. API reference (full list)", "h1"))
    story.append(p(
        "<b>Authentication.</b> Every protected endpoint expects this header:"))
    story.append(code("Authorization: Bearer <API_KEY>"))
    story.append(p("As a fallback the server also accepts "
                   "<font face='Courier'>X-API-Key: &lt;API_KEY&gt;</font>."))

    story.append(p("Public endpoints (Moodle-facing):", "h2"))
    story.append(endpoint_table(PUBLIC_ENDPOINTS))

    story.append(p("Internal endpoints (in-process session lifecycle, "
                   "prefix <font face='Courier'>/api/proctoring</font>):", "h2"))
    story.append(endpoint_table(INTERNAL_ENDPOINTS))

    story.append(p("Example: enroll then verify with curl", "h3"))
    story.append(code(
        "# 1. Encode three webcam photos to base64\n"
        "B1=$(base64 -w0 photo1.jpg)\n"
        "B2=$(base64 -w0 photo2.jpg)\n"
        "B3=$(base64 -w0 photo3.jpg)\n"
        "\n"
        "# 2. Enroll\n"
        "curl -X POST http://localhost:5000/enroll/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"user_id\\\": \\\"student_001\\\", \"\\\n"
        "      \"\\\"images\\\": [\\\"$B1\\\", \\\"$B2\\\", \\\"$B3\\\"]}\"\n"
        "\n"
        "# 3. Verify\n"
        "LIVE=$(base64 -w0 live_capture.jpg)\n"
        "curl -X POST http://localhost:5000/verify/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"current_face\\\": \\\"$LIVE\\\", \\\n"
        "       \\\"user_id\\\": \\\"student_001\\\"}\""
    ))

    # ---- 13. Swagger ----
    story.append(p("13. Using the Swagger UI", "h1"))
    story.append(p(
        "Swagger UI is the easiest way to explore the API without writing "
        "any code. Open <font face='Courier'>http://localhost:5000/docs</font>:"))
    story.extend(bullets([
        "Click the green <b>Authorize</b> button.",
        "Paste your API token (the value of "
        "<font face='Courier'>API_KEY</font>), click <b>Authorize</b>, "
        "then <b>Close</b>.",
        "Pick any endpoint, click <b>Try it out</b>, fill in the example "
        "body, and click <b>Execute</b>. The server response, status code, "
        "and <font face='Courier'>curl</font> equivalent are printed below.",
    ]))

    # ---- 14. Security checklist ----
    story.append(p("14. Security checklist before deployment", "h1"))
    story.extend(bullets([
        "<font face='Courier'>ENVIRONMENT=production</font> in .env.",
        "Strong random <font face='Courier'>SECRET_KEY</font> and "
        "<font face='Courier'>API_KEY</font>.",
        "<font face='Courier'>.env</font> is not committed to git.",
        "<font face='Courier'>CORS_ORIGINS</font> set to your Moodle "
        "origin(s), not *.",
        "TLS terminated by a reverse proxy (Nginx, Caddy, cloud LB) in "
        "front of the container.",
        "Logs / reports / data volumes mounted to durable storage so they "
        "survive container restarts.",
        "All four model files present in "
        "<font face='Courier'>models_data/</font> (otherwise alignment is "
        "skipped and accuracy drops).",
        "<b>Never auto-enroll from quiz captures.</b> Enrollment must go "
        "through <font face='Courier'>/enroll/face</font> or "
        "<font face='Courier'>/enroll/face/guided</font> as a deliberate, "
        "supervised step.",
    ]))

    # ---- 15. Troubleshooting ----
    story.append(p("15. Troubleshooting", "h1"))
    story.append(kv_table([
        ("RuntimeError: SECRET_KEY is required",
            "Set SECRET_KEY (and API_KEY) in .env or container env. The "
            "check is intentional in production."),
        ("401 Unauthorized on every call",
            "Confirm the header is exactly "
            "<font face='Courier'>Authorization: Bearer &lt;token&gt;</font> "
            "and the token matches API_KEY."),
        ("Swagger UI is empty / 'swagger and openapi cannot be present'",
            "Hard-reload the page; the server now strips Swagger-2.0 fields "
            "from <font face='Courier'>/openapi.json</font>."),
        ("Webcam endpoints fail in Docker",
            "Containers do not see the host webcam by default. Use the "
            "base64 image endpoints, or run the app outside Docker for live capture."),
        ("Match scores are low / inconsistent",
            "Check <font face='Courier'>/api/proctoring/system-info</font> "
            "and confirm <font face='Courier'>alignment_enabled: true</font>. "
            "If not, the face_landmarker.task file is missing - drop it into "
            "models_data/."),
        ("Match never reaches threshold",
            "Lower FACE_MATCH_THRESHOLD to 0.35 in .env, OR re-enroll with "
            "webcam photos that match the live conditions (lighting / camera) "
            "rather than a studio photo."),
        ("404 on /verify/face with user_id",
            "That user_id has no enrolled references. Enroll first via "
            "/enroll/face or /enroll/face/guided."),
        ("409 on enrollment",
            "User already has the maximum of 10 references. Delete first "
            "(DELETE /enroll/face/&lt;user_id&gt;) or use replace_existing=true."),
    ]))

    return story


# ===========================================================================
#                          BAHASA INDONESIA
# ===========================================================================
def build_indonesian() -> list:
    story = []

    story.append(p("Moodle Proctoring AI Backend", "title"))
    story.append(p("Panduan pemula &middot; Arsitektur, alur, enrollment, deployment, dan API",
                   "subtitle"))

    # ---- 1. Apa ini ----
    story.append(p("1. Apa itu backend ini?", "h1"))
    story.append(p(
        "Proyek ini adalah backend Python (FastAPI) yang menjalankan pengawasan "
        "ujian online berbasis AI. Backend menyediakan REST API untuk deteksi "
        "wajah, verifikasi identitas, analisis perilaku, pendaftaran "
        "(enrollment) siswa, dan pengelolaan sesi ujian."
    ))
    story.append(p("Singkatnya: <b>Moodle (atau klien apa pun) mengirim "
                   "sebuah gambar, lalu backend menjawab apakah peserta "
                   "sendirian, menghadap layar, dan cocok dengan identitas "
                   "yang terdaftar.</b>"))
    story.append(p("Fitur utama:", "h3"))
    story.extend(bullets([
        "Deteksi wajah berbasis YOLO - akurat, tidak salah-deteksi pada noise.",
        "Penyelarasan wajah (face alignment) via MediaPipe - mata selalu "
        "horizontal sebelum proses pengenalan.",
        "Embedding 512-d via ArcFace (ResNet50, 1500 identitas, val acc 96.77%).",
        "Multi-reference enrollment - daftarkan siswa dengan 3-5 foto, "
        "verifikasi memakai foto referensi yang paling cocok.",
        "Bearer-token authentication, Swagger UI, siap Docker.",
    ]))

    # ---- 2. Glosarium ----
    story.append(p("2. Glosarium (baca ini dulu)", "h1"))
    story.append(p(
        "Sistem pengenalan wajah penuh istilah teknis. Berikut istilah "
        "minimum yang Anda butuhkan untuk mengikuti panduan ini."))
    story.append(kv_table([
        ("Face detection",
            "Menemukan <i>di mana</i> letak wajah dalam sebuah gambar. "
            "Output: kotak pembatas (x, y, lebar, tinggi) dan skor "
            "kepercayaan. Backend ini memakai YOLO."),
        ("Face recognition",
            "Mencari tahu <i>siapa</i> pemilik wajah tersebut. Dilakukan "
            "dalam dua langkah: ubah wajah menjadi vektor (embedding), "
            "lalu bandingkan vektor."),
        ("Embedding",
            "Daftar berisi 512 angka pecahan (vektor) yang merangkum "
            "bentuk sebuah wajah. Dua foto orang yang sama menghasilkan "
            "embedding yang sangat mirip; dua orang berbeda menghasilkan "
            "yang sangat berbeda."),
        ("Face alignment",
            "Memutar dan mengubah ukuran potongan wajah agar mata selalu "
            "berada di posisi horizontal yang sama sebelum embedding "
            "dihitung. Ini membuat embedding jauh lebih stabil."),
        ("Cosine similarity",
            "Bilangan antara -1 dan 1 yang menunjukkan seberapa mirip "
            "dua embedding. 1.0 = identik, sekitar 0.5 = orang yang sama "
            "foto berbeda, di bawah ~0.3 = orang berbeda."),
        ("Verification",
            "Mengecek apakah wajah live cocok dengan identitas tertentu "
            "(perbandingan 1 ke 1)."),
        ("Enrollment",
            "Langkah berprivilege satu kali untuk merekam embedding "
            "referensi seorang siswa sehingga kita punya sesuatu untuk "
            "diverifikasi nanti."),
    ]))

    # ---- 3. Arsitektur ----
    story.append(p("3. Arsitektur (gambaran besar)", "h1"))
    story.append(p(
        "Backend disusun berlapis. Permintaan berjalan dari atas ke bawah: "
        "masuk ke aplikasi FastAPI, lewat lapisan autentikasi, di-route ke "
        "handler, lalu handler memanggil orchestrator yang memegang model "
        "AI dan tempat penyimpanan enrollment."
    ))
    story.append(code(ARCHITECTURE_DIAGRAM))

    story.append(p("Peta folder:", "h3"))
    story.append(kv_table([
        ("app.py",                  "Application factory FastAPI + setup Swagger."),
        ("asgi.py",                 "Entrypoint ASGI untuk Gunicorn + worker Uvicorn."),
        ("config/settings.py",      "Membaca .env; menolak start bila secret tidak ada."),
        ("src/api/auth.py",         "Dependency bearer-token untuk seluruh route terproteksi."),
        ("src/api/moodle_routes.py",
            "Endpoint yang dipanggil oleh Moodle: /detect/*, /verify/face, "
            "/embeddings, /enroll/face (4 varian), /batch/process."),
        ("src/api/proctoring_routes.py",
            "Endpoint internal untuk siklus sesi di-proses."),
        ("src/core/orchestrator.py",
            "Mengoordinasikan detector, manajer sesi, dan generator laporan."),
        ("src/core/model_manager.py",
            "Memuat YOLO + RetinaFace + ArcFace + aligner; memilih "
            "detector terbaik yang tersedia."),
        ("src/models/yolo_face_detector.py",
            "Wrapper YOLO (Ultralytics) - detector wajah utama."),
        ("src/models/retinaface.py / face_detector.py",
            "Arsitektur RetinaFace dan wrapper inference cadangan."),
        ("src/models/face_aligner.py",
            "MediaPipe FaceLandmarker + transformasi similarity ke 112x112."),
        ("src/models/arcface.py",
            "FaceEmbeddingNet (ResNet50 + proyeksi 512-d)."),
        ("src/models/face_recognizer.py",
            "Pipeline lengkap: align + embed + cosine similarity."),
        ("src/services/face_enrollment.py",
            "Penyimpan enrollment berbasis SQLite. Satu file database di "
            "<font face='Courier'>data/enrollments.db</font>."),
        ("Dockerfile, docker-compose.yml",
            "Deployment container dengan volume persisten untuk model, "
            "report, log, dan database enrollment."),
    ]))

    # ---- 4. Alur request ----
    story.append(PageBreak())
    story.append(p("4. Alur request verifikasi dari awal hingga akhir", "h1"))
    story.append(p(
        "Misalkan klien memanggil <font face='Courier'>POST /verify/face</font> "
        "dengan gambar base64 dan <font face='Courier'>user_id</font> yang "
        "sudah didaftarkan sebelumnya. Langkah demi langkah:"
    ))
    story.extend(bullets([
        "<b>1. Autentikasi.</b> Dependency "
        "<font face='Courier'>require_api_key</font> membandingkan header "
        "<font face='Courier'>Authorization: Bearer ...</font> dengan "
        "<font face='Courier'>API_KEY</font> menggunakan "
        "<font face='Courier'>hmac.compare_digest</font>. Token salah: 401.",
        "<b>2. Decode.</b> String base64 di-decode menjadi gambar OpenCV "
        "(numpy array, format BGR).",
        "<b>3. Deteksi.</b> YOLO dijalankan pada gambar dan mengembalikan "
        "bounding box wajah. Kotak terbesar dengan confidence > 0.5 yang "
        "dipilih. Tidak ada wajah: response berisi "
        "<i>no_face_in_current_frame</i>.",
        "<b>4. Alignment.</b> Potongan wajah dilewatkan ke MediaPipe "
        "FaceLandmarker yang mendeteksi landmark mata/hidung/mulut. "
        "Transformasi similarity memutar dan menskalakan wajah agar mata "
        "berada di posisi kanonis pada gambar 112x112.",
        "<b>5. Embedding.</b> Gambar 112x112 yang sudah selaras dilewatkan "
        "melalui ArcFace, menghasilkan vektor 512-d yang ter-L2-normalize.",
        "<b>6. Lookup.</b> Semua embedding yang sudah ter-enroll untuk "
        "<font face='Courier'>user_id</font> diambil dari SQLite.",
        "<b>7. Perbandingan.</b> Cosine similarity dihitung terhadap setiap "
        "referensi tersimpan. Skor <b>maksimum</b> yang dikembalikan, plus "
        "skor rata-rata dan per-referensi di <font face='Courier'>details</font>.",
        "<b>8. Response.</b> <font face='Courier'>{is_match, match_score, "
        "details}</font>. <font face='Courier'>is_match</font> bernilai "
        "true bila skor terbaik melewati threshold (default 0.4).",
    ]))

    # ---- 5. Prasyarat ----
    story.append(p("5. Prasyarat", "h1"))
    story.extend(bullets([
        "Python 3.11+ (hanya jika Anda tidak memakai Docker).",
        "Docker + Docker Compose (disarankan untuk deployment).",
        "File model terlatih ditaruh di folder "
        "<font face='Courier'>models_data/</font>:",
    ]))
    story.append(kv_table([
        ("face_detection_yolo.pt",
            "Detector wajah YOLO (Ultralytics). <b>Detector utama.</b>"),
        ("face_detection_model.pth",
            "RetinaFace MobileNet0.25. Cadangan bila YOLO tidak ada."),
        ("face_recognition_model.pth",
            "Backbone ArcFace ResNet50 (juga berisi head 1500 kelas)."),
        ("face_landmarker.task",
            "MediaPipe FaceLandmarker. Diperlukan untuk face alignment; "
            "tanpa file ini, recognizer akan fallback ke resize biasa dan "
            "akurasi turun."),
    ]))

    # ---- 6. Setup awal ----
    story.append(p("6. Pengaturan pertama kali", "h1"))
    story.append(p("Langkah 1 - clone dan masuk ke folder proyek:", "h3"))
    story.append(code("git clone https://github.com/evankafauzya/capstone-backend.git\n"
                      "cd capstone-backend"))
    story.append(p("Langkah 2 - tempatkan keempat file model di "
                   "<font face='Courier'>models_data/</font> "
                   "(file ini tidak ada di repo git karena ukurannya besar).",
                   "h3"))
    story.append(p("Langkah 3 - salin template environment:", "h3"))
    story.append(code("cp .env.example .env"))
    story.append(p("Langkah 4 - buat secret yang kuat:", "h3"))
    story.append(code("python -c \"import secrets; print(secrets.token_urlsafe(48))\""))
    story.append(p("Jalankan perintah itu dua kali, lalu paste hasilnya "
                   "sebagai <font face='Courier'>SECRET_KEY</font> dan "
                   "<font face='Courier'>API_KEY</font> di file .env."))
    story.append(p(
        "<b>Kenapa?</b> Di mode production, aplikasi menolak start tanpa "
        "nilai ini. File <font face='Courier'>.env</font> sudah otomatis "
        "di-ignore git - jangan pernah commit.", "note"))

    # ---- 7. Konfigurasi ----
    story.append(p("7. Referensi konfigurasi", "h1"))
    story.append(kv_table([
        ("ENVIRONMENT",
            "development | production. Di production, secret yang hilang "
            "menggagalkan boot."),
        ("DEBUG",                  "true / false. Otomatis aktif saat development."),
        ("HOST / PORT",            "Alamat bind dan port (default 0.0.0.0:5000)."),
        ("SECRET_KEY",             "Kunci tanda tangan sesi. Wajib di production."),
        ("API_KEY",                "Bearer token. Wajib di production."),
        ("API_KEY_REQUIRED",       "Jika false, autentikasi dilewati (khusus dev)."),
        ("CORS_ORIGINS",           "Daftar origin dipisah koma. Pakai * hanya untuk lokal."),
        ("LOG_LEVEL",              "DEBUG, INFO, WARNING, ERROR."),
        ("MODELS_DIR",
            "Tempat file .pt/.pth/.task disimpan (default models_data/)."),
        ("DATA_DIR",
            "Tempat database SQLite enrollment disimpan (default data/). "
            "Mount sebagai volume di production agar enrollment tidak "
            "hilang saat container restart."),
        ("ENROLLMENT_DB_PATH",     "Override lokasi DB default."),
        ("FACE_DETECTION_CONFIDENCE",
            "Batas confidence per-detector (default 0.5)."),
        ("FACE_MATCH_THRESHOLD",
            "Threshold cosine untuk verifikasi. <b>Default 0.4</b>, sudah "
            "dituning untuk perbandingan webcam-vs-foto-registrasi. "
            "Naikkan ke 0.5+ hanya bila kedua foto berasal dari sumber "
            "yang sama."),
        ("MAX_FACES_ALLOWED",
            "Jumlah wajah maksimum; lebih dari itu memicu peringatan."),
    ]))

    # ---- 8. Lokal ----
    story.append(PageBreak())
    story.append(p("8. Menjalankan secara lokal (tanpa Docker)", "h1"))
    story.append(code(
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate       # macOS/Linux\n"
        "pip install -r requirements.txt\n"
        "python app.py"
    ))
    story.append(p("Lalu buka:"))
    story.extend(bullets([
        "<font face='Courier'>http://localhost:5000/</font> - banner layanan.",
        "<font face='Courier'>http://localhost:5000/health</font> - "
        "health check (menampilkan detector / recognizer yang aktif).",
        "<font face='Courier'>http://localhost:5000/docs</font> - Swagger UI.",
    ]))

    # ---- 9. Docker ----
    story.append(p("9. Deployment production dengan Docker", "h1"))
    story.append(p("Ini cara yang disarankan - satu perintah, dapat diulang, "
                   "mengisolasi aplikasi dari host."))
    story.append(p("Langkah 1 - pastikan .env sudah terisi dan file model "
                   "ada di <font face='Courier'>models_data/</font>.", "h3"))
    story.append(p("Langkah 2 - build dan jalankan:", "h3"))
    story.append(code("docker compose up -d --build"))

    story.append(p("Langkah 3 - verifikasi sehat:", "h3"))
    story.append(code("curl http://localhost:5000/health"))

    story.append(p("Perintah berguna:", "h3"))
    story.append(code(
        "docker compose logs -f             # tail log\n"
        "docker compose ps                  # status\n"
        "docker compose down                # berhenti\n"
        "docker compose up -d --build       # build ulang setelah perubahan kode"
    ))

    story.append(p("Mount volume:", "h3"))
    story.append(kv_table([
        ("./models_data &#8594; /app/models_data",
         "Mount read-only agar bisa ganti model tanpa build ulang."),
        ("./reports &#8594; /app/reports",
         "Menyimpan laporan sesi yang dihasilkan."),
        ("./logs &#8594; /app/logs",
         "Menyimpan log aplikasi (rotating)."),
        ("./data &#8594; /app/data",
         "Menyimpan database SQLite enrollment. <b>Penting</b> - tanpa "
         "mount ini, setiap container restart akan menghapus semua enrollment."),
    ]))

    # ---- 10. Enrollment ----
    story.append(p("10. Enrollment - mendaftarkan seorang siswa", "h1"))
    story.append(p(
        "Sebelum bisa <i>memverifikasi</i> seorang siswa, Anda harus "
        "<i>mendaftarkannya</i> terlebih dahulu. Enrollment adalah langkah "
        "satu kali yang berprivilege, yang menghubungkan sebuah "
        "<font face='Courier'>user_id</font> dengan beberapa foto referensi. "
        "Setelah itu, setiap verifikasi tinggal mengecek wajah live "
        "terhadap referensi-referensi tersebut."
    ))
    story.append(p(
        "<b>Penting:</b> jangan pernah auto-enroll dari frame yang ditangkap "
        "saat ujian. Bila Anda lakukan itu, orang pertama yang login "
        "sebagai <i>alice</i> akan jadi <i>alice</i> selamanya - bahkan "
        "kalau dia seorang impostor. Enrollment harus berupa langkah "
        "sengaja yang diawasi.", "note"))

    story.append(p("Dua cara untuk enrollment", "h2"))
    story.append(p("<b>Cara mudah (disarankan): guided enrollment.</b>", "h3"))
    story.append(p(
        "Frontend merekam klip pendek siswa (biasanya 5 detik pada ~3 frame "
        "per detik) dan mengirim 5-20 frame sekaligus. Server mendeteksi "
        "wajah, meng-embed, memilih frame terbaik dan paling beragam "
        "secara otomatis, lalu menyimpannya. Siswa tidak perlu melakukan "
        "apa-apa yang istimewa - cukup duduk di depan kamera."
    ))
    story.append(code(
        "POST /enroll/face/guided\n"
        "Authorization: Bearer <API_KEY>\n"
        "Content-Type: application/json\n"
        "\n"
        "{\n"
        '  "user_id": "student_001",\n'
        '  "frames":  ["...base64...", "...base64...", ...],\n'
        '  "target_count": 3,\n'
        '  "replace_existing": true\n'
        "}"
    ))
    story.append(p(
        "<b>Bagaimana server memilih frame terbaik:</b> pertama, frame "
        "tanpa wajah atau dengan confidence rendah disaring keluar. Lalu "
        "frame paling berkualitas (wajah terbesar + confidence tertinggi) "
        "dipilih sebagai jangkar. Setiap pilihan berikutnya memaksimalkan "
        "jarak cosine minimum terhadap kumpulan yang sudah dipilih - "
        "teknik ini disebut <i>farthest-point sampling</i> dan menghasilkan "
        "referensi yang mencakup berbagai sudut kepala, bukan tiga foto "
        "frontal yang nyaris identik."))

    story.append(p("<b>Cara manual: enrollment eksplisit.</b>", "h3"))
    story.append(p(
        "Bila frontend sudah punya 3-5 foto terpilih (misalnya dari "
        "database kartu mahasiswa), foto tersebut bisa dikirim langsung:"))
    story.append(code(
        "POST /enroll/face\n"
        "{\n"
        '  "user_id": "student_001",\n'
        '  "images": ["...base64...", "...base64...", "...base64..."]\n'
        "}"
    ))
    story.append(p(
        "Setiap panggilan menambah referensi (bukan mengganti). Batas "
        "keras 10 referensi per user."))

    story.append(p("Endpoint enrollment (semua di bawah "
                   "<font face='Courier'>/enroll/face</font>):", "h2"))
    story.append(endpoint_table(ENROLLMENT_ENDPOINTS))

    # ---- 11. Verifikasi ----
    story.append(p("11. Verifikasi - mengecek siswa selama ujian", "h1"))
    story.append(p(
        "Setelah enrollment, frontend menangkap satu frame live dan "
        "bertanya ke server: <i>apakah ini mirip student_001?</i>"))
    story.append(code(
        "POST /verify/face\n"
        "Authorization: Bearer <API_KEY>\n"
        "Content-Type: application/json\n"
        "\n"
        "{\n"
        '  "current_face": "...base64 frame webcam saat ini...",\n'
        '  "user_id": "student_001"\n'
        "}"
    ))
    story.append(p("Response (kasus sukses):"))
    story.append(code(
        "{\n"
        '  "is_match": true,\n'
        '  "match_score": 0.6730,\n'
        '  "details": {\n'
        '    "method": "arcface_max_similarity_over_references",\n'
        '    "threshold_used": 0.4,\n'
        '    "user_id": "student_001",\n'
        '    "references_compared": 3,\n'
        '    "best_reference_id": "84b3176944c3",\n'
        '    "best_score": 0.6730,\n'
        '    "mean_score": 0.5142,\n'
        '    "all_scores": [0.6730, 0.5121, 0.3575]\n'
        "  }\n"
        "}"
    ))
    story.append(p(
        "Karena kita membandingkan dengan <b>semua</b> referensi yang "
        "terdaftar dan mengambil yang maksimum, skor match jauh lebih "
        "stabil terhadap variasi sudut kepala dibandingkan satu foto "
        "referensi saja. Field <font face='Courier'>all_scores</font> "
        "sangat berguna untuk debug: bila semua skor rendah, fotonya "
        "memang orang berbeda; bila satu tinggi dan sisanya rendah, "
        "berarti sudut kepala siswa mirip salah satu referensi."))

    # ---- 12. API ----
    story.append(PageBreak())
    story.append(p("12. Referensi API (daftar lengkap)", "h1"))
    story.append(p(
        "<b>Autentikasi.</b> Semua endpoint terproteksi memerlukan header berikut:"))
    story.append(code("Authorization: Bearer <API_KEY>"))
    story.append(p("Sebagai cadangan, server juga menerima "
                   "<font face='Courier'>X-API-Key: &lt;API_KEY&gt;</font>."))

    story.append(p("Endpoint publik (untuk Moodle):", "h2"))
    story.append(endpoint_table(PUBLIC_ENDPOINTS))

    story.append(p("Endpoint internal (siklus sesi di-proses, prefix "
                   "<font face='Courier'>/api/proctoring</font>):", "h2"))
    story.append(endpoint_table(INTERNAL_ENDPOINTS))

    story.append(p("Contoh: enrollment kemudian verifikasi dengan curl", "h3"))
    story.append(code(
        "# 1. Encode tiga foto webcam ke base64\n"
        "B1=$(base64 -w0 foto1.jpg)\n"
        "B2=$(base64 -w0 foto2.jpg)\n"
        "B3=$(base64 -w0 foto3.jpg)\n"
        "\n"
        "# 2. Enrollment\n"
        "curl -X POST http://localhost:5000/enroll/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"user_id\\\": \\\"student_001\\\", \"\\\n"
        "      \"\\\"images\\\": [\\\"$B1\\\", \\\"$B2\\\", \\\"$B3\\\"]}\"\n"
        "\n"
        "# 3. Verifikasi\n"
        "LIVE=$(base64 -w0 capture_live.jpg)\n"
        "curl -X POST http://localhost:5000/verify/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"current_face\\\": \\\"$LIVE\\\", \\\n"
        "       \\\"user_id\\\": \\\"student_001\\\"}\""
    ))

    # ---- 13. Swagger ----
    story.append(p("13. Menggunakan Swagger UI", "h1"))
    story.append(p(
        "Swagger UI adalah cara termudah mencoba API tanpa menulis kode. "
        "Buka <font face='Courier'>http://localhost:5000/docs</font>:"))
    story.extend(bullets([
        "Klik tombol hijau <b>Authorize</b>.",
        "Tempelkan token API Anda (nilai dari "
        "<font face='Courier'>API_KEY</font>), klik <b>Authorize</b>, "
        "lalu <b>Close</b>.",
        "Pilih salah satu endpoint, klik <b>Try it out</b>, isi contoh "
        "body, lalu klik <b>Execute</b>. Response server, kode status, "
        "dan ekuivalen <font face='Courier'>curl</font> akan ditampilkan "
        "di bawah.",
    ]))

    # ---- 14. Checklist keamanan ----
    story.append(p("14. Checklist keamanan sebelum deployment", "h1"))
    story.extend(bullets([
        "<font face='Courier'>ENVIRONMENT=production</font> di .env.",
        "<font face='Courier'>SECRET_KEY</font> dan "
        "<font face='Courier'>API_KEY</font> acak kuat.",
        "<font face='Courier'>.env</font> tidak di-commit ke git.",
        "<font face='Courier'>CORS_ORIGINS</font> diatur ke origin Moodle "
        "Anda, bukan *.",
        "TLS diterminasi oleh reverse proxy (Nginx, Caddy, cloud LB) di "
        "depan container.",
        "Volume log / reports / data diarahkan ke storage permanen "
        "agar tidak hilang saat container restart.",
        "Keempat file model ada di "
        "<font face='Courier'>models_data/</font> (jika tidak, alignment "
        "dilewati dan akurasi turun).",
        "<b>Jangan pernah auto-enroll dari frame ujian.</b> Enrollment "
        "harus lewat <font face='Courier'>/enroll/face</font> atau "
        "<font face='Courier'>/enroll/face/guided</font> sebagai langkah "
        "sengaja yang diawasi.",
    ]))

    # ---- 15. Troubleshooting ----
    story.append(p("15. Pemecahan masalah umum", "h1"))
    story.append(kv_table([
        ("RuntimeError: SECRET_KEY is required",
            "Isi SECRET_KEY (dan API_KEY) di .env atau env container. "
            "Pengecekan ini disengaja di production."),
        ("401 Unauthorized terus-menerus",
            "Pastikan header tepat: "
            "<font face='Courier'>Authorization: Bearer &lt;token&gt;</font>, "
            "dan token sesuai dengan API_KEY."),
        ("Swagger UI kosong / 'swagger and openapi cannot be present'",
            "Hard-reload halaman; server sekarang menghapus field Swagger-2.0 "
            "dari <font face='Courier'>/openapi.json</font>."),
        ("Endpoint webcam gagal di Docker",
            "Container tidak melihat webcam host secara default. Pakai "
            "endpoint berbasis gambar base64, atau jalankan aplikasi di "
            "luar Docker."),
        ("Skor match rendah / tidak konsisten",
            "Cek <font face='Courier'>/api/proctoring/system-info</font> "
            "dan pastikan <font face='Courier'>alignment_enabled: true</font>. "
            "Bila tidak, file face_landmarker.task hilang - taruh di "
            "models_data/."),
        ("Match tidak pernah mencapai threshold",
            "Turunkan FACE_MATCH_THRESHOLD ke 0.35 di .env, ATAU enroll "
            "ulang dengan foto webcam yang kondisinya cocok (pencahayaan / "
            "kamera) dengan kondisi live, bukan foto studio."),
        ("404 pada /verify/face dengan user_id",
            "user_id tersebut belum punya referensi. Enroll dulu lewat "
            "/enroll/face atau /enroll/face/guided."),
        ("409 pada enrollment",
            "User sudah mencapai batas maksimum 10 referensi. Hapus dulu "
            "(DELETE /enroll/face/&lt;user_id&gt;) atau pakai "
            "replace_existing=true."),
    ]))

    return story


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(filename: str, story: list) -> Path:
    out = DOCS_DIR / filename
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm,  bottomMargin=2 * cm,
        title="Moodle Proctoring AI Backend Guide",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return out


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    en = render("proctoring-backend-guide_EN.pdf", build_english())
    print(f"Generated: {en}  ({en.stat().st_size // 1024} KB)")
    id_ = render("proctoring-backend-guide_ID.pdf", build_indonesian())
    print(f"Generated: {id_} ({id_.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
