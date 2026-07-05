"""
Generate the **deep beginner course** PDFs.

This is the long-form teaching document -- written as if explaining the
project to first-year university students. Unlike ``build_docs.py`` (which
produces a short quick-reference card), this script generates a full course
covering all nine of the requested topics with "why we chose X over Y"
explanations throughout.

Run:
    python docs/build_course.py

Output:
    docs/proctoring-beginner-course_EN.pdf
    docs/proctoring-beginner-course_ID.pdf
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
    Spacer,
    Table,
    TableStyle,
)

DOCS_DIR = Path(__file__).resolve().parent
BRAND_COLOR = colors.HexColor("#1f4e79")
ACCENT_COLOR = colors.HexColor("#d35400")
LIGHT_BG = colors.HexColor("#f4f6f8")
WHY_BG = colors.HexColor("#fff7e6")
MONO_BG = colors.HexColor("#1e1e1e")
MONO_FG = colors.HexColor("#f8f8f2")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def make_styles():
    base = getSampleStyleSheet()
    s = {}
    s["cover_title"] = ParagraphStyle(
        "cover_title", parent=base["Title"], fontSize=30, leading=36,
        textColor=BRAND_COLOR, spaceAfter=4, alignment=TA_LEFT,
    )
    s["cover_sub"] = ParagraphStyle(
        "cover_sub", parent=base["Normal"], fontSize=14, leading=18,
        textColor=colors.grey, spaceAfter=18,
    )
    s["chapter"] = ParagraphStyle(
        "chapter", parent=base["Heading1"], fontSize=22, leading=28,
        textColor=BRAND_COLOR, spaceBefore=8, spaceAfter=12, keepWithNext=True,
    )
    s["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=15, leading=20,
        textColor=BRAND_COLOR, spaceBefore=14, spaceAfter=6, keepWithNext=True,
    )
    s["h3"] = ParagraphStyle(
        "h3", parent=base["Heading3"], fontSize=12, leading=16,
        textColor=ACCENT_COLOR, spaceBefore=10, spaceAfter=4, keepWithNext=True,
    )
    s["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontSize=10.5, leading=15.5,
        spaceAfter=7, alignment=TA_LEFT,
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=s["body"], leftIndent=14, bulletIndent=2,
        spaceAfter=3,
    )
    s["mono"] = ParagraphStyle(
        "mono", parent=base["Code"], fontName="Courier", fontSize=8.5,
        leading=11, leftIndent=8, rightIndent=8, textColor=MONO_FG,
        backColor=MONO_BG, borderPadding=8, spaceBefore=4, spaceAfter=10,
    )
    s["why"] = ParagraphStyle(
        "why", parent=s["body"], leftIndent=10, rightIndent=10,
        backColor=WHY_BG, borderPadding=8, spaceBefore=4, spaceAfter=10,
    )
    s["note"] = ParagraphStyle(
        "note", parent=s["body"], leftIndent=10, rightIndent=10,
        backColor=LIGHT_BG, borderPadding=8, spaceBefore=4, spaceAfter=10,
    )
    return s


STYLES = make_styles()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def code(text):
    return Preformatted(text, STYLES["mono"])


def bullets(items):
    return [Paragraph(f"&#8226; {it}", STYLES["bullet"]) for it in items]


def why(label, text):
    return Paragraph(f"<b>{label}</b> &nbsp; {text}", STYLES["why"])


def note(text):
    return Paragraph(text, STYLES["note"])


def kv_table(rows, col_widths=(4.8 * cm, 11.2 * cm)):
    data = [[Paragraph(f"<b>{k}</b>", STYLES["body"]),
             Paragraph(v, STYLES["body"])] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT_BG),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def endpoint_table(rows):
    head = [Paragraph(f"<b>{h}</b>", STYLES["body"])
            for h in ("Method", "Path", "Description")]
    data = [head] + [[Paragraph(m, STYLES["body"]),
                      Paragraph(f"<font face='Courier'>{path}</font>",
                                STYLES["body"]),
                      Paragraph(desc, STYLES["body"])]
                     for m, path, desc in rows]
    t = Table(data, colWidths=(2 * cm, 6.5 * cm, 7.5 * cm), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_COLOR),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d0d7de")),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def page_footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm,
                      f"Moodle Proctoring AI Backend - Beginner Course - "
                      f"Page {doc.page}")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Shared architecture diagram
# ---------------------------------------------------------------------------
DIAGRAM = """+-------------------------------------------------------------+
|                  CLIENT  (Moodle / browser)                 |
|              Authorization: Bearer <API_KEY>                |
+-------------------------------------------------------------+
                            |  HTTPS
                            v
+-------------------------------------------------------------+
|    CADDY  (reverse proxy + TLS, optional but recommended)   |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|                FASTAPI app (app.py)                         |
|  middlewares:                                               |
|    - body size limit (50 MB)                                |
|    - X-Request-ID                                           |
|    - X-Process-Time                                         |
|    - rate limiting (slowapi, 600/min)                       |
|    - CORS                                                   |
+-------------------------------------------------------------+
                            |
                            v
+-------------------------------------------------------------+
|              src/api/auth.py  (Bearer token)                |
+-------------------------------------------------------------+
                            |
        +-------------------+--------------------+
        v                                        v
+--------------------------+         +---------------------------+
|  moodle_routes.py        |         |  proctoring_routes.py     |
|   /detect/faces          |         |   /api/proctoring/*       |
|   /verify/face           |         |   (in-process sessions)   |
|   /detect/behavior       |         |                           |
|   /detect/liveness       |         |                           |
|   /embeddings            |         |                           |
|   /enroll/face*          |         |                           |
|   /verifications/{id}    |         |                           |
+--------------------------+         +---------------------------+
                            |
                            v
+-------------------------------------------------------------+
|              src/core/orchestrator.py                       |
+-------------------------------------------------------------+
            |                                |
            v                                v
+-----------------------+         +------------------------+
| ModelManager          |         | FaceEnrollmentStore    |
| (src/core)            |         | + VerificationAudit    |
|                       |         | (src/services)         |
|  YOLO    -> bbox      |         |                        |
|  Aligner -> 112x112   |         |   SQLite database      |
|  ArcFace -> 512-d emb |         |   data/enrollments.db  |
+-----------------------+         +------------------------+
"""


# ===========================================================================
#                                ENGLISH
# ===========================================================================
def build_english():
    s = []

    # ---- Cover ----
    s.append(p("Moodle Proctoring AI Backend", "cover_title"))
    s.append(p("Beginner's Course &middot; A walk-through for first-year "
               "students who are new to backend development",
               "cover_sub"))
    s.append(note(
        "This is the deep, teaching version of the documentation. Every "
        "technical choice is explained in plain language and compared to "
        "the alternatives we considered. If you have never built a web "
        "service before, start here and read top-to-bottom. Code examples "
        "are copy-paste-able."
    ))

    # =====================================================================
    # 1. PROJECT OVERVIEW
    # =====================================================================
    s.append(PageBreak())
    s.append(p("1. Project Overview", "chapter"))

    s.append(p("1.1 The real-world problem", "h2"))
    s.append(p(
        "Imagine a university that lets students take their final exam from "
        "home. Without anyone watching, a student could ask a friend to "
        "answer for them, look up answers in another tab, or hold a phone "
        "behind the screen. <i>Online proctoring</i> is the practice of "
        "watching the student's webcam during the exam to discourage and "
        "detect this kind of cheating."
    ))
    s.append(p(
        "Manual proctoring (a human watching each student through Zoom) "
        "does not scale: one proctor per 30 students means hundreds of "
        "extra staff for a typical exam week. AI proctoring uses computer "
        "vision to do the routine watching automatically, so a human only "
        "has to review the suspicious moments. <b>This project is the "
        "backend half of an AI proctor</b>: the Moodle plugin sends webcam "
        "frames to us; we return JSON verdicts."
    ))

    s.append(p("1.2 What this backend does, in one sentence", "h2"))
    s.append(p(
        "<i>Given an image of a student in front of a webcam, the backend "
        "returns a JSON answer to four questions: is there a face, is it "
        "the registered student, is it a live human (not a printed photo), "
        "and is anything suspicious going on.</i>"
    ))

    s.append(p("1.3 Main features", "h2"))
    s.extend(bullets([
        "<b>Face detection</b> -- find every face in a picture and return "
        "its bounding box.",
        "<b>Face verification</b> -- decide whether the live face matches "
        "the registered student. Two modes: against a single reference "
        "photo, or against several reference photos enrolled in advance.",
        "<b>Liveness detection</b> -- given a short clip (a few frames "
        "captured over ~2 seconds), decide whether the subject is a live "
        "human (blink + tiny head movements) or a static photo held up to "
        "the camera.",
        "<b>Behavior analysis</b> -- on a single frame, look for "
        "suspicious signals: multiple faces, head turned far to the side, "
        "eyes not on the screen.",
        "<b>Enrollment</b> -- store a student's reference face(s) under a "
        "user_id so future verify calls can look them up.",
        "<b>Audit log</b> -- every verification gets recorded with the "
        "score, threshold, and decision, so disputes have an evidence trail.",
        "<b>Session lifecycle</b> -- start a session at the beginning of "
        "an exam, accumulate warnings, generate a report at the end.",
    ]))

    s.append(p("1.4 The overall workflow", "h2"))
    s.append(p(
        "A typical exam has three phases. Each phase uses a different "
        "endpoint in our backend:"
    ))
    s.append(kv_table([
        ("1. Enrollment (once per semester)",
            "An admin or the student themselves submits 3-5 reference "
            "photos. The backend computes a face embedding for each photo "
            "and stores them in a database keyed by user_id. The original "
            "image bytes are <b>not</b> kept -- only the 512-number "
            "embedding."),
        ("2. Liveness check (start of exam)",
            "The frontend records ~2 seconds of webcam frames and submits "
            "them. The backend looks for a blink and small head movements. "
            "If neither is present, it suspects a static-photo attack."),
        ("3. Verify (periodically during exam)",
            "Every minute or two the frontend snaps one frame and asks "
            "'is this still student_001?'. The backend compares the live "
            "face against each enrolled reference and returns the maximum "
            "similarity score, plus its decision."),
    ]))

    # =====================================================================
    # 2. TECHNOLOGY STACK
    # =====================================================================
    s.append(PageBreak())
    s.append(p("2. Technology Stack", "chapter"))
    s.append(p(
        "Every project picks technologies. Sometimes the choice is obvious; "
        "sometimes it is a trade-off. This chapter explains each technology "
        "we use and -- importantly -- which alternatives we considered and "
        "why we did not pick them."
    ))

    s.append(p("2.1 Programming language: Python 3.11", "h2"))
    s.append(p(
        "Python is the language of machine learning. Almost every modern "
        "computer-vision library (PyTorch, OpenCV, MediaPipe, Ultralytics) "
        "is either written in Python or has a Python binding as its main "
        "interface."
    ))
    s.append(why("Why Python over Node.js / Go / Java?",
        "Speed of development matters more than raw runtime speed for our "
        "request volume (a few requests per second per student, not "
        "thousands per second). And Python is the only language where you "
        "can call PyTorch + MediaPipe + OpenCV without writing your own "
        "wrappers. Node.js has TensorFlow.js but the ecosystem is much "
        "thinner. Go and Java have similar problems -- excellent for "
        "high-throughput web servers, weak for AI."))
    s.append(why("Why 3.11 specifically?",
        "3.11 is fast (about 25% faster than 3.10 on most code), still "
        "supports every library we depend on, and is the version PyTorch "
        "officially tests. 3.12+ would also work but some scientific "
        "libraries lag behind on the very latest Python."))

    s.append(p("2.2 Web framework: FastAPI", "h2"))
    s.append(p(
        "FastAPI is a Python library that turns Python functions into HTTP "
        "endpoints. You write a function with type hints; FastAPI "
        "automatically validates incoming requests, returns JSON responses, "
        "and generates an interactive Swagger UI."
    ))
    s.append(code(
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "class HelloRequest(BaseModel):\n"
        "    name: str\n"
        "\n"
        "@app.post('/hello')\n"
        "def hello(body: HelloRequest):\n"
        "    return {'message': f'Hello {body.name}'}"
    ))
    s.append(why("Why FastAPI over Flask?",
        "Flask is simpler but requires manual request validation -- you "
        "write <font face='Courier'>data.get('name')</font> and pray it's "
        "there. FastAPI uses pydantic to validate the request before your "
        "function runs, catching bugs early. FastAPI also auto-generates "
        "OpenAPI 3 docs (the Swagger UI at <font face='Courier'>/docs"
        "</font>); with Flask we used flasgger which produced broken specs "
        "(mixing Swagger 2.0 and OpenAPI 3 fields). And FastAPI supports "
        "async natively for I/O-bound workloads -- not critical here, but "
        "future-proof."))
    s.append(why("Why FastAPI over Django?",
        "Django is a 'batteries-included' full-stack framework -- ORM, "
        "admin panel, templates, sessions, the works. We don't need any "
        "of that. We need a small JSON API. Django would force us to "
        "carry hundreds of features we'll never use, plus it's heavier "
        "and slower to boot."))

    s.append(p("2.3 ASGI server: Uvicorn behind Gunicorn", "h2"))
    s.append(p(
        "FastAPI is the framework, but you still need a <b>server</b> that "
        "listens on a port and routes requests into the framework. We use "
        "Uvicorn (the standard runner for ASGI Python apps) supervised by "
        "Gunicorn (a battle-tested Linux process manager)."
    ))
    s.append(why("Why two pieces?",
        "Uvicorn alone is fine in development. In production you want "
        "Gunicorn around it so the process auto-restarts on crash, "
        "graceful-reloads on signal, and rotates log files. Gunicorn + "
        "Uvicorn worker class is the official FastAPI production recipe."))
    s.append(why("Why only one worker?",
        "Each worker loads ~250 MB of PyTorch + YOLO + MediaPipe into "
        "memory. Two workers = double the RAM. Since FastAPI runs sync "
        "handlers in a thread pool, one worker with many threads handles "
        "concurrent requests just as well at our scale."))

    s.append(p("2.4 Deep learning framework: PyTorch", "h2"))
    s.append(p(
        "PyTorch is the Python library that runs our neural networks. "
        "When we call <font face='Courier'>model(image)</font>, PyTorch "
        "moves the image tensor through the network's layers (convolutions, "
        "batch normalizations, activations) and returns the output tensor."
    ))
    s.append(why("Why PyTorch over TensorFlow?",
        "Two reasons. First, the models you trained (RetinaFace and ArcFace) "
        "were saved as PyTorch <font face='Courier'>.pth</font> files; "
        "switching to TensorFlow would mean retraining everything. Second, "
        "PyTorch dominates academic research, so when a new face-recognition "
        "paper drops, the reference code is almost always PyTorch."))

    s.append(p("2.5 Face detection: Ultralytics YOLO (primary)", "h2"))
    s.append(p(
        "YOLO ('You Only Look Once') is a family of fast object-detection "
        "models. The Ultralytics package wraps the YOLOv8 architecture in "
        "a friendly Python API. We use a single-class variant trained "
        "specifically to detect faces."
    ))
    s.append(why("Why YOLO over RetinaFace?",
        "Both are good face detectors. The difference shows up on tricky "
        "input: RetinaFace MobileNet0.25 will fire on small high-confidence "
        "regions like eye corners or shadows on a textured background, "
        "producing dozens of '18x7 pixel face' false positives. YOLO has "
        "fewer false positives at the cost of slightly less accurate "
        "bounding-box edges. For a proctoring backend, fewer false "
        "positives is the right trade -- we'd rather miss an edge case "
        "than hallucinate faces that don't exist."))
    s.append(why("Why keep RetinaFace at all?",
        "It's our fallback. If <font face='Courier'>face_detection_yolo."
        "pt</font> goes missing or fails to load, the system silently "
        "switches to RetinaFace so you have <i>some</i> detector. "
        "RetinaFace also returns five facial landmarks for free, which "
        "we use in <font face='Courier'>/detect/behavior</font> for gaze "
        "estimation."))

    s.append(p("2.6 Face alignment: MediaPipe FaceLandmarker", "h2"))
    s.append(p(
        "Before we hand a face to the recognition model, we want every "
        "face to look the same way (eyes horizontal, face centered in a "
        "112x112 image). MediaPipe is Google's open-source library that "
        "finds 478 landmark points on a face. We use 5 of them -- both "
        "eye centers, the nose tip, and two mouth corners -- to compute a "
        "similarity transform that warps the face into the canonical "
        "position."
    ))
    s.append(why("Why alignment matters",
        "ArcFace was trained on aligned faces. If you skip alignment and "
        "feed it a tilted face, the embedding moves significantly even "
        "though the identity is the same. In our testing, adding "
        "alignment took the match score for a single live verify call "
        "from ~0.44 to ~0.75 for the same person."))
    s.append(why("Why MediaPipe over dlib or InsightFace?",
        "MediaPipe runs on CPU at real-time speeds, has no GPU "
        "requirement, is maintained by Google (so it won't disappear), "
        "and ships as a single 3.7 MB <font face='Courier'>.task</font> "
        "file. dlib's landmark detector is slower; InsightFace's is "
        "faster but pulls in more dependencies."))

    s.append(p("2.7 Face recognition: ArcFace (ResNet50 or EfficientNet-B0)", "h2"))
    s.append(p(
        "Face recognition is a two-step process. First, the model turns a "
        "112x112 face crop into a 512-number vector called an <i>"
        "embedding</i>. Two embeddings of the same person point in nearly "
        "the same direction; two embeddings of different people point in "
        "different directions. To decide if two faces match, you compute "
        "the angle between their embeddings (the <i>cosine similarity</i>) "
        "and compare to a threshold."
    ))
    s.append(p(
        "ArcFace is the training technique that produces the best "
        "embeddings for this task. You give it a face, it gives you 512 "
        "numbers, and you're done. Our system supports two ArcFace "
        "backbones: ResNet50 (200 MB, the original) and EfficientNet-B0 "
        "(40 MB, smaller and faster but similar accuracy). The system "
        "autodetects which one based on the checkpoint shape."
    ))
    s.append(why("Why ArcFace over FaceNet / VGGFace?",
        "ArcFace's training objective adds an angular margin between "
        "classes, which produces tighter same-person clusters and bigger "
        "different-person gaps. Empirically it's been state-of-art for "
        "face verification since 2019. FaceNet (2015) is older and "
        "produces slightly more entangled clusters. VGGFace is even "
        "older."))

    s.append(p("2.8 Database: SQLite", "h2"))
    s.append(p(
        "SQLite is a small SQL database that lives in a single file. "
        "There is no separate server process -- you open the file, run "
        "queries, close the file. Our system uses one SQLite file at "
        "<font face='Courier'>data/enrollments.db</font> with two tables: "
        "<i>users</i> (one row per enrolled student), <i>face_references"
        "</i> (one row per stored reference embedding), and <i>"
        "verifications</i> (one row per audit-log entry)."
    ))
    s.append(why("Why SQLite over PostgreSQL or MongoDB?",
        "Three reasons. First, our scale: one school's worth of students "
        "is well within SQLite's comfort zone (hundreds of thousands of "
        "rows). Second, deployment: PostgreSQL needs a separate container "
        "or service to run. SQLite needs nothing -- just a file. Third, "
        "backups: copying one file <i>is</i> the backup. When you "
        "outgrow it (multiple writers, multi-region), migrating to "
        "Postgres is a one-day job because the SQL stays the same."))

    s.append(p("2.9 Pydantic for request validation", "h2"))
    s.append(p(
        "Pydantic is a Python library for declaring what a piece of data "
        "should look like, then automatically checking that it does. We "
        "use it to define every API request body and response model."
    ))
    s.append(code(
        "class EnrollFaceRequest(BaseModel):\n"
        "    user_id: str\n"
        "    images: List[str] = Field(..., min_length=1, max_length=5)"
    ))
    s.append(p(
        "If a client sends <font face='Courier'>images</font> with six "
        "items, pydantic rejects the request with a 422 error before our "
        "code runs. The same model becomes the OpenAPI schema in Swagger "
        "UI for free."
    ))
    s.append(why("Why pydantic over hand-rolled validation?",
        "Hand-rolled validation (<font face='Courier'>if 'images' not in "
        "data: ...</font>) is verbose, error-prone, and inconsistent. "
        "Pydantic gives you declarative validation, clear error messages, "
        "and free schema generation -- all in five lines."))

    s.append(p("2.10 slowapi for rate limiting", "h2"))
    s.append(p(
        "Without rate limiting, a buggy client (or an attacker) can hit "
        "the GPU-bound <font face='Courier'>/verify/face</font> endpoint "
        "thousands of times per second and exhaust the server. slowapi "
        "lets you set a cap per IP or per API token. Our default: 600 "
        "requests per minute, which is plenty for normal use but caps "
        "abuse."
    ))

    s.append(p("2.11 Caddy for TLS", "h2"))
    s.append(p(
        "If you deploy this backend on a real internet-facing server, "
        "your Bearer token will travel in plaintext over HTTP. Anyone on "
        "the network can steal it. The fix is HTTPS, which encrypts the "
        "connection. Caddy is a small web server that automatically "
        "fetches a free TLS certificate from Let's Encrypt for any "
        "domain you point at it."
    ))
    s.append(why("Why Caddy over Nginx?",
        "Nginx is the industry standard but its configuration files are "
        "hand-written, and you need a separate program (certbot) to "
        "manage TLS certificates. Caddy's Caddyfile is much simpler "
        "(\"<font face='Courier'>proctoring.example.com { reverse_proxy "
        "app:5000 }</font>\" is the whole config) and it auto-renews "
        "certificates without any extra setup."))

    s.append(p("2.12 Docker for deployment", "h2"))
    s.append(p(
        "Docker packages your code <i>plus</i> the operating system "
        "libraries it needs into a single image. When you run that image, "
        "the program sees the same environment everywhere -- your laptop, "
        "the school server, a cloud VM. No more 'it works on my machine.' "
        "Docker Compose lets you describe a multi-service setup (app + "
        "Caddy + volumes) in one YAML file."
    ))

    s.append(p("2.13 pytest + GitHub Actions for testing & CI", "h2"))
    s.append(p(
        "<b>pytest</b> is the standard Python testing library: you write "
        "functions starting with <font face='Courier'>test_</font>, and "
        "<font face='Courier'>pytest</font> finds and runs them. We have "
        "22 tests covering authentication, validation, enrollment, audit, "
        "and rate limiting."
    ))
    s.append(p(
        "<b>GitHub Actions</b> runs those tests automatically on every "
        "push and pull request. If you break something, you find out in "
        "two minutes -- not when a teacher reviews your code."
    ))

    s.append(p("2.14 Other libraries (one-liners)", "h2"))
    s.append(kv_table([
        ("OpenCV (cv2)", "Read/write images, color conversions, resizing. The Swiss Army knife of computer vision."),
        ("NumPy", "Fast numerical arrays. Every image we touch is a NumPy array under the hood."),
        ("ReportLab", "Generates PDFs. Used by the report generator and the doc-generator scripts."),
        ("requests", "Make outbound HTTP calls. Currently unused but kept for the future Moodle webhook integration."),
        ("python-dotenv", "Loads <font face='Courier'>.env</font> files into environment variables at boot."),
    ]))

    s.append(p("2.15 Development environment", "h2"))
    s.append(p(
        "You need: Python 3.11+, git, and (optionally) Docker. Most "
        "developers use Visual Studio Code with the Python extension. "
        "The recommended workflow:"
    ))
    s.append(code(
        "git clone https://github.com/evankafauzya/capstone-backend.git\n"
        "cd capstone-backend\n"
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate      # macOS / Linux\n"
        "pip install -r requirements.txt\n"
        "cp .env.example .env            # then edit it\n"
        "python app.py"
    ))

    # =====================================================================
    # 3. SYSTEM ARCHITECTURE
    # =====================================================================
    s.append(PageBreak())
    s.append(p("3. System Architecture", "chapter"))

    s.append(p("3.1 The big picture", "h2"))
    s.append(p(
        "The backend is built in <b>layers</b>. A request enters at the "
        "top, travels down through each layer, and a response travels "
        "back up. Each layer has a single, narrow job."
    ))
    s.append(code(DIAGRAM))

    s.append(p("3.2 What each layer does", "h2"))
    s.append(kv_table([
        ("Caddy (optional)",
            "Terminates HTTPS, forwards the request to FastAPI over plain HTTP "
            "inside the Docker network. Also serves as an HSTS / security-header "
            "gateway."),
        ("Middlewares",
            "Cross-cutting concerns that apply to every request: enforce a "
            "max body size (50 MB), generate / propagate an X-Request-ID, "
            "measure processing time, enforce rate limits, and handle CORS "
            "for browser callers."),
        ("Auth dependency",
            "Reads the Bearer token from the Authorization header, compares "
            "it (with hmac.compare_digest, to avoid timing attacks) against "
            "the API_KEY environment variable, and rejects the request with "
            "401 if it doesn't match."),
        ("Route handlers",
            "Tiny functions that decode the request body via pydantic, call "
            "into the core / services layer, format the response. They contain "
            "no AI logic of their own."),
        ("Orchestrator + ModelManager",
            "Owns the heavy objects: the YOLO model, the ArcFace model, the "
            "MediaPipe aligner. Loaded once at boot, reused for every request "
            "so we don't pay the load cost per call."),
        ("Services (enrollment + audit)",
            "Persistence layer. They talk to SQLite. Routes do NOT talk to "
            "SQLite directly -- they go through services so we could swap the "
            "database later without touching routes."),
    ]))

    s.append(p("3.3 Following one verify request end-to-end", "h2"))
    s.append(p(
        "Concrete example: client calls <font face='Courier'>POST /verify/face"
        "</font> with a base64-encoded webcam frame and a user_id."
    ))
    s.extend(bullets([
        "<b>Step 1: TLS.</b> Caddy decrypts the HTTPS request, sees a POST to "
        "<font face='Courier'>/verify/face</font>, forwards it to "
        "<font face='Courier'>app:5000</font>.",
        "<b>Step 2: middlewares.</b> The body-size middleware confirms the "
        "request is under 50 MB. The request-ID middleware generates a "
        "unique 16-char ID and attaches it to <font face='Courier'>"
        "request.state</font>. The rate-limit middleware checks that this "
        "Bearer token has not exceeded 600/min.",
        "<b>Step 3: auth.</b> The <font face='Courier'>require_api_key</font> "
        "dependency reads <font face='Courier'>Authorization: Bearer ...</font>, "
        "compares to <font face='Courier'>API_KEY</font>. Wrong token: 401 "
        "before any AI runs.",
        "<b>Step 4: pydantic.</b> The request body is parsed into a "
        "<font face='Courier'>VerifyFaceRequest</font> model. Missing "
        "<font face='Courier'>current_face</font>: 422 with a clean error.",
        "<b>Step 5: decode.</b> The base64 string is turned into a NumPy "
        "image array (BGR, the OpenCV convention).",
        "<b>Step 6: detect.</b> The image goes through YOLO. We get back "
        "zero or more bounding boxes with confidence scores.",
        "<b>Step 7: align.</b> The biggest, most confident face crop is "
        "passed to MediaPipe FaceLandmarker, which returns 478 landmarks. "
        "We extract the 5 key points and compute a similarity transform "
        "to a canonical 112x112.",
        "<b>Step 8: embed.</b> The aligned crop is normalized and run "
        "through ArcFace, producing a 512-d L2-normalized vector.",
        "<b>Step 9: lookup.</b> The enrollment service fetches all stored "
        "embeddings for the user_id from SQLite.",
        "<b>Step 10: compare.</b> Cosine similarity is computed against "
        "each stored embedding; the maximum is the match score.",
        "<b>Step 11: audit.</b> The audit service writes a row to SQLite "
        "with (timestamp, user_id, score, threshold, decision, request_id).",
        "<b>Step 12: response.</b> A JSON body is built with the verdict "
        "plus diagnostics. The middleware adds <font face='Courier'>"
        "X-Process-Time</font> and <font face='Courier'>X-Request-ID</font> "
        "headers. Caddy re-encrypts; the client sees the response.",
    ]))

    s.append(p("3.4 Why this architecture?", "h2"))
    s.append(why("Why layered architecture?",
        "Each layer can be tested independently. The auth layer can be "
        "tested without any AI models loaded. The recognizer can be tested "
        "with no HTTP server at all. Without layering, our test suite "
        "would have to spin up the entire stack for every assertion."))
    s.append(why("Why services between routes and database?",
        "If we ever switch SQLite to PostgreSQL, we only change the "
        "service files. The routes don't know SQL exists. This is the "
        "<i>repository pattern</i> in software-engineering jargon."))
    s.append(why("Why load models once, not per-request?",
        "Loading the EfficientNet ArcFace checkpoint from disk is a 2-3 "
        "second operation. Doing it per request would slow each verify "
        "to a crawl AND waste memory by holding several copies."))

    # =====================================================================
    # 4. FOLDER STRUCTURE
    # =====================================================================
    s.append(PageBreak())
    s.append(p("4. Folder Structure", "chapter"))

    s.append(p("4.1 The tree", "h2"))
    s.append(code(
        "capstone-backend/\n"
        "|-- app.py                       # FastAPI factory + middlewares\n"
        "|-- asgi.py                      # ASGI entry for Gunicorn\n"
        "|-- Dockerfile                   # Builds the container image\n"
        "|-- docker-compose.yml           # Single-node deployment\n"
        "|-- docker-compose.tls.yml       # Overlay adding Caddy + TLS\n"
        "|-- Caddyfile.example            # Copy & edit for production\n"
        "|-- requirements.txt             # Pinned Python dependencies\n"
        "|-- pytest.ini                   # Test runner config\n"
        "|-- .env.example                 # Environment template\n"
        "|-- README.md                    # Technical reference\n"
        "|-- .github/\n"
        "|   `-- workflows/ci.yml         # GitHub Actions: lint + test + docker build\n"
        "|-- config/\n"
        "|   `-- settings.py              # Reads .env, fails closed in production\n"
        "|-- src/\n"
        "|   |-- api/\n"
        "|   |   |-- auth.py              # Bearer-token FastAPI dependency\n"
        "|   |   |-- moodle_routes.py     # /detect /verify /enroll /liveness ...\n"
        "|   |   |-- proctoring_routes.py # /api/proctoring/session/*\n"
        "|   |   `-- schemas.py           # Pydantic request/response models\n"
        "|   |-- core/\n"
        "|   |   |-- model_manager.py     # Loads YOLO + ArcFace + aligner\n"
        "|   |   `-- orchestrator.py      # Glues models, sessions, reports\n"
        "|   |-- models/\n"
        "|   |   |-- _torch_load.py       # Safe torch.load with weights_only=True\n"
        "|   |   |-- yolo_face_detector.py\n"
        "|   |   |-- retinaface.py        # Architecture + priors + NMS\n"
        "|   |   |-- face_detector.py     # RetinaFace inference wrapper\n"
        "|   |   |-- arcface.py           # FaceEmbeddingNet (autodetect backbone)\n"
        "|   |   |-- face_aligner.py      # MediaPipe landmarker + transform\n"
        "|   |   `-- face_recognizer.py   # Align + embed + cosine\n"
        "|   |-- detectors/\n"
        "|   |   |-- eye_tracker.py       # Session-time blink / gaze tracker\n"
        "|   |   |-- face_detector.py     # Session-time wrapper around YOLO\n"
        "|   |   `-- liveness.py          # Stateless blink + motion analyzer\n"
        "|   |-- processors/\n"
        "|   |   |-- session_manager.py\n"
        "|   |   `-- webcam_capture.py\n"
        "|   |-- services/\n"
        "|   |   |-- face_enrollment.py   # SQLite enrollment store\n"
        "|   |   `-- audit.py             # SQLite verification audit log\n"
        "|   `-- utils/\n"
        "|       `-- report_generator.py  # JSON / TXT / PDF reports\n"
        "|-- tests/\n"
        "|   |-- conftest.py              # Fixtures + auto MOCK_MODELS\n"
        "|   |-- _stub_system.py          # Fake ProctoringSystem for CI\n"
        "|   `-- test_smoke.py            # 22 smoke tests\n"
        "|-- docs/\n"
        "|   |-- build_docs.py            # Quick-reference PDF generator\n"
        "|   `-- build_course.py          # THIS course (deep beginner walkthrough)\n"
        "|-- models_data/    (gitignored) # Drop YOLO + ArcFace + landmark files here\n"
        "|-- data/           (gitignored) # SQLite database lives here\n"
        "|-- reports/        (gitignored) # Generated session reports\n"
        "`-- logs/           (gitignored) # Rotating application logs"
    ))

    s.append(p("4.2 How files connect to each other", "h2"))
    s.append(p(
        "Think of imports as arrows from the file that imports to the file "
        "that defines. The arrows point inward to a small core of "
        "domain-logic files, and outward from the route layer. The high-level "
        "dependency graph:"
    ))
    s.extend(bullets([
        "<font face='Courier'>app.py</font> imports the route blueprints from "
        "<font face='Courier'>src.api</font>, the orchestrator from "
        "<font face='Courier'>src.core</font>, and the storage services from "
        "<font face='Courier'>src.services</font>.",
        "<font face='Courier'>src.api.moodle_routes</font> imports schemas, "
        "the auth dependency, and (via globals set at boot) the orchestrator "
        "and stores.",
        "<font face='Courier'>src.core.orchestrator</font> imports detectors "
        "(<font face='Courier'>src.detectors</font>) and the model manager "
        "(<font face='Courier'>src.core.model_manager</font>).",
        "<font face='Courier'>src.core.model_manager</font> imports the three "
        "model wrappers from <font face='Courier'>src.models</font>.",
        "<font face='Courier'>src.services</font> is at the bottom of the "
        "stack -- it imports only the standard library (<font face='Courier'>"
        "sqlite3</font>, <font face='Courier'>uuid</font>, <font face='Courier'>"
        "datetime</font>). Nothing else imports services upward -- services "
        "are leaves of the dependency tree.",
    ]))

    # =====================================================================
    # 5. BACKEND EXPLANATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("5. Backend Explanation", "chapter"))

    s.append(p("5.1 Server setup (app.py)", "h2"))
    s.append(p(
        "<font face='Courier'>app.py</font> is the <b>application factory</b>. "
        "Its job is to wire up the FastAPI app and return it ready to serve."
    ))
    s.append(p("Concretely, <font face='Courier'>create_app()</font> does:", "h3"))
    s.extend(bullets([
        "Read configuration from environment variables via "
        "<font face='Courier'>config/settings.py</font>.",
        "Configure logging (rotating file handler + console).",
        "Build a FastAPI instance with the correct title, version, and "
        "<font face='Courier'>lifespan</font> context manager.",
        "Add the rate-limit middleware, CORS middleware, body-size "
        "middleware, X-Request-ID middleware, and X-Process-Time middleware.",
        "Register the two route blueprints (<font face='Courier'>moodle_api"
        "</font> and <font face='Courier'>proctoring_api</font>).",
        "Register custom exception handlers that reshape Pydantic / Starlette "
        "errors into our uniform <font face='Courier'>{'error': '...'}</font> shape.",
        "Override <font face='Courier'>app.openapi</font> to insert the "
        "Bearer scheme so Swagger UI shows the Authorize button.",
        "Add the public <font face='Courier'>/healthz</font> and "
        "<font face='Courier'>/health</font> endpoints.",
    ]))

    s.append(p("5.2 The lifespan context", "h2"))
    s.append(p(
        "Starting up takes time: PyTorch has to load a 40-200 MB model, "
        "MediaPipe has to load its landmark task, the SQLite database has "
        "to be opened or created. We do all of that <b>once</b>, inside "
        "the <font face='Courier'>lifespan</font> async context manager. "
        "FastAPI calls it on startup, then again on shutdown. Routes can "
        "then assume everything is initialized."
    ))

    s.append(p("5.3 Routes (moodle_routes.py)", "h2"))
    s.append(p(
        "<font face='Courier'>moodle_routes.py</font> defines an "
        "<font face='Courier'>APIRouter</font> that has the Bearer-auth "
        "dependency attached at the router level. Every route inherits it "
        "automatically -- you don't have to repeat <font face='Courier'>"
        "@require_api_key</font> on each endpoint."
    ))
    s.append(p(
        "Each route function is tiny by design: validate, decode, "
        "delegate, format. AI logic lives in <font face='Courier'>"
        "src.core</font> and <font face='Courier'>src.models</font>, "
        "<i>never</i> in the route function itself. This keeps routes "
        "easy to test."
    ))

    s.append(p("5.4 Database handling", "h2"))
    s.append(p(
        "The database lives in <font face='Courier'>data/enrollments.db"
        "</font> -- one SQLite file, three tables."
    ))
    s.append(kv_table([
        ("users",
            "One row per enrolled student. Columns: user_id (PK), "
            "enrolled_at, updated_at, embedding_dim, model_backend."),
        ("face_references",
            "One row per stored face. Columns: id (PK), user_id (FK), "
            "added_at, embedding (raw float32 BLOB, 2 KB), face_w, face_h, "
            "face_confidence."),
        ("verifications",
            "Audit log. Columns: id (PK), ts_utc, user_id, method, "
            "match_score, threshold, matched, references_compared, "
            "best_reference_id, reason, recognizer_backend, detector_backend, "
            "client_ip, request_id."),
    ]))
    s.append(p(
        "Embeddings are stored as <b>raw float32 BLOBs</b> rather than "
        "JSON arrays: 2 KB per 512-d vector vs ~6 KB if we used JSON. "
        "Across thousands of references this matters; for a single user "
        "it doesn't, but consistent design choices compound."
    ))

    s.append(p("5.5 Authentication", "h2"))
    s.append(p(
        "Every protected endpoint expects the header:"
    ))
    s.append(code("Authorization: Bearer <API_KEY>"))
    s.append(p(
        "where <font face='Courier'>API_KEY</font> is whatever you set in "
        "<font face='Courier'>.env</font>. The dependency function "
        "<font face='Courier'>require_api_key</font> extracts the token "
        "and calls <font face='Courier'>hmac.compare_digest(token, API_KEY)"
        "</font>. We use <font face='Courier'>compare_digest</font> "
        "instead of <font face='Courier'>token == API_KEY</font> to prevent "
        "<i>timing attacks</i>: a normal string comparison short-circuits "
        "on the first wrong byte, leaking the byte position via response "
        "latency. <font face='Courier'>compare_digest</font> compares all "
        "bytes regardless."
    ))

    s.append(p("5.6 Why this style of backend?", "h2"))
    s.append(why("Why a single shared API_KEY (not per-user OAuth)?",
        "Our caller is a Moodle plugin -- a server, not a browser. The "
        "single-key model is appropriate for server-to-server traffic. "
        "OAuth would add a token-issuance flow we don't need."))
    s.append(why("Why dependency injection for auth (instead of decorators)?",
        "FastAPI's <font face='Courier'>Depends()</font> is testable: you "
        "can override it in tests with a stub. The auth dependency also "
        "doubles as documentation -- Swagger UI sees it and renders the "
        "Authorize button automatically."))
    s.append(why("Why fail closed in production?",
        "If <font face='Courier'>SECRET_KEY</font> or <font face='Courier'>"
        "API_KEY</font> is missing in production mode, the app raises at "
        "boot rather than starting with a weak default. A noisy "
        "<font face='Courier'>RuntimeError</font> is easier to diagnose "
        "than a silently-insecure production service."))

    # =====================================================================
    # 6. FUNCTION EXPLANATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("6. Function Explanation", "chapter"))
    s.append(p(
        "Out of ~3,500 lines of Python, here are the dozen functions you "
        "should understand if you want to know how this system actually "
        "works."
    ))

    # Function 1
    s.append(p("6.1 create_app() - app.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Build a FastAPI instance with everything wired up."))
    s.append(p("<b>Input:</b> None.", "h3"))
    s.append(p("<b>Output:</b> A FastAPI <font face='Courier'>app</font> object.", "h3"))
    s.append(p(
        "<b>Logic:</b> Builds the FastAPI object with our title and the "
        "lifespan handler. Adds five middlewares in a deliberate order: "
        "rate limiter (outermost so it counts even invalid requests), CORS, "
        "body size limit, request-ID, process-time. Includes the two "
        "routers. Registers exception handlers for pydantic errors and "
        "Starlette HTTPExceptions. Customizes the OpenAPI schema to "
        "include the Bearer security scheme. Returns the app."
    ))

    # Function 2
    s.append(p("6.2 require_api_key(request) - src/api/auth.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> A FastAPI dependency that gates every protected route."))
    s.append(p("<b>Input:</b> The FastAPI <font face='Courier'>Request</font> object.", "h3"))
    s.append(p("<b>Output:</b> Nothing on success; raises <font face='Courier'>HTTPException(401)</font> on failure.", "h3"))
    s.append(p(
        "<b>Logic:</b> If <font face='Courier'>API_KEY_REQUIRED</font> is "
        "false (dev mode), return immediately. Otherwise pull the Bearer "
        "token from <font face='Courier'>Authorization</font> (or the "
        "<font face='Courier'>X-API-Key</font> fallback header). Compare "
        "against <font face='Courier'>API_KEY</font> via "
        "<font face='Courier'>hmac.compare_digest</font>. If mismatch, "
        "raise 401 with a structured error body."
    ))

    # Function 3
    s.append(p("6.3 verify_face(body, request) - moodle_routes.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Compare a live face against a single reference "
        "image <i>or</i> against all references previously enrolled for a "
        "user_id."))
    s.append(p("<b>Input:</b> Pydantic <font face='Courier'>VerifyFaceRequest</font> "
               "(current_face base64, plus exactly one of reference_face / user_id, "
               "plus optional threshold / return_embeddings). Plus the FastAPI Request "
               "(for IP, request-ID, audit logging).", "h3"))
    s.append(p("<b>Output:</b> JSON: <font face='Courier'>{is_match: bool, match_score: "
               "float, confidence: float, details: {...}}</font>", "h3"))
    s.append(p(
        "<b>Logic:</b> Validate that exactly one of reference_face / "
        "user_id is set. Decode the current face. Run YOLO; pick the "
        "biggest face above 0.7 confidence; crop with 15% padding. Compute "
        "the embedding via the recognizer (which internally runs alignment "
        "+ ArcFace). Then branch:"
    ))
    s.extend(bullets([
        "<b>user_id mode:</b> pull all stored embeddings for that user, "
        "compute cosine similarity against each, return the maximum plus "
        "diagnostic per-reference scores in <font face='Courier'>"
        "details.all_scores</font>.",
        "<b>reference_face mode:</b> decode the reference image, detect "
        "+ crop + embed the same way, return the single cosine similarity.",
    ]))
    s.append(p(
        "Either way, write one row to the audit log with the score, "
        "threshold, and decision, then return the JSON."
    ))

    # Function 4
    s.append(p("6.4 FaceRecognizer.embed_face(crop) - src/models/face_recognizer.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Turn a face crop into a 512-d L2-normalized embedding."))
    s.append(p("<b>Input:</b> A BGR NumPy array (HxWx3, uint8).", "h3"))
    s.append(p("<b>Output:</b> A NumPy array shape <font face='Courier'>(512,)</font>, "
               "L2-normalized.", "h3"))
    s.append(p(
        "<b>Logic:</b> Preprocess the crop (alignment via MediaPipe, "
        "fallback to resize if alignment fails). Normalize pixels to "
        "[-1, 1]. Run through the FaceEmbeddingNet (which itself does "
        "<font face='Courier'>F.normalize</font> at the end). Return the "
        "resulting vector. Increments <font face='Courier'>"
        "alignment_stats[aligned]</font> or <font face='Courier'>"
        "alignment_stats[fallback]</font> for observability."
    ))

    # Function 5
    s.append(p("6.5 FaceAligner.align(image) - src/models/face_aligner.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Warp a face crop into the canonical InsightFace "
        "112x112 template."))
    s.append(p("<b>Input:</b> A BGR NumPy array containing a face.", "h3"))
    s.append(p("<b>Output:</b> A 112x112 BGR NumPy array, or "
               "<font face='Courier'>None</font> if landmarks couldn't be found.", "h3"))
    s.append(p(
        "<b>Logic:</b> Run MediaPipe FaceLandmarker on the input. If no "
        "face is found, return None (the recognizer will fall back to "
        "plain resize). Otherwise extract 5 landmarks: midpoints of left/"
        "right eye corners, nose tip, and left/right mouth corners. Call "
        "<font face='Courier'>cv2.estimateAffinePartial2D</font> against "
        "the canonical template to get a rotation + scale + translation "
        "matrix. Apply it via <font face='Courier'>cv2.warpAffine</font>."
    ))

    # Function 6
    s.append(p("6.6 _select_diverse_references(candidates, target_count) - "
               "moodle_routes.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Out of N viable candidate frames, pick the K best "
        "AND most varied ones for guided enrollment."))
    s.append(p("<b>Input:</b> A list of <font face='Courier'>{embedding, face_box, "
               "index}</font> dicts; the target number to pick.", "h3"))
    s.append(p("<b>Output:</b> A tuple <font face='Courier'>(picked, metrics)</font>.", "h3"))
    s.append(p(
        "<b>Logic:</b> Sort candidates by quality (confidence x sqrt(area)). "
        "Pick the highest-quality one as the anchor. Then iteratively "
        "<i>farthest-point sampling</i>: at each step, pick the candidate "
        "whose embedding is most different from everything already picked. "
        "Repeat until target_count or no candidates left. Compute "
        "diagnostic metrics (avg face size, avg confidence, minimum "
        "pairwise diversity)."
    ))
    s.append(p("This is what gives guided enrollment its 'three different "
               "head angles instead of three near-identical frontals' "
               "behavior."))

    # Function 7
    s.append(p("6.7 LivenessAnalyzer.analyze(frames) - src/detectors/liveness.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Decide whether a short clip shows a live human "
        "or a static photo."))
    s.append(p("<b>Input:</b> A list of BGR NumPy arrays (3-30 frames).", "h3"))
    s.append(p("<b>Output:</b> JSON with <font face='Courier'>is_alive, "
               "total_blinks, head_movement_pixels, ...</font>", "h3"))
    s.append(p(
        "<b>Logic:</b> For each frame, run MediaPipe to get landmarks. "
        "Compute the eye aspect ratio (EAR) -- vertical-over-horizontal "
        "of the eye. Track the nose tip position. Count blinks via "
        "hysteresis: EAR drops below 0.20 (closed) then rebounds above "
        "0.25 (open) = one blink. Compute the maximum pairwise nose "
        "displacement across all frames. Verdict: alive if at least one "
        "blink, OR head moved more than 4 pixels."
    ))

    # Function 8
    s.append(p("6.8 FaceEnrollmentStore.enroll(...) - src/services/face_enrollment.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Persist new reference embeddings for a user_id."))
    s.append(p("<b>Input:</b> user_id, list of embeddings, list of face_box "
               "metadata dicts, model_backend label.", "h3"))
    s.append(p("<b>Output:</b> A result dict including the new reference IDs "
               "and total reference count.", "h3"))
    s.append(p(
        "<b>Logic:</b> Validate the user_id (alphanumeric / _ / -, 1-64 "
        "chars). Validate each embedding has the right shape. Check that "
        "adding them won't blow the per-user cap (10). Open a SQLite "
        "transaction. UPSERT the users row. INSERT one face_references "
        "row per embedding, converting the numpy array to raw float32 "
        "bytes. Commit. Return."
    ))

    # Function 9
    s.append(p("6.9 VerificationAuditStore.record(...) - src/services/audit.py", "h2"))
    s.append(p(
        "<b>Purpose:</b> Append one row to the verifications audit table."))
    s.append(p("<b>Input:</b> All the per-call data (user_id, method, score, "
               "threshold, matched, references_compared, ...).", "h3"))
    s.append(p("<b>Output:</b> The new audit row ID.", "h3"))
    s.append(p(
        "<b>Logic:</b> Generate a random 12-char ID. Open a SQLite "
        "connection. INSERT one row. Close the connection. Note: this is "
        "<i>best-effort</i> -- if the DB is briefly unhappy, "
        "<font face='Courier'>_record_audit</font> in the route logs the "
        "exception and returns None instead of failing the user's verify "
        "call."
    ))

    # Function 10
    s.append(p("6.10 _rate_limit_key(request) - app.py", "h2"))
    s.append(p("<b>Purpose:</b> Decide which 'bucket' a request belongs to "
               "for rate limiting."))
    s.append(p("<b>Input:</b> The FastAPI Request object.", "h3"))
    s.append(p("<b>Output:</b> A string like <font face='Courier'>'key:abc123'</font> "
               "or <font face='Courier'>'ip:192.0.2.5'</font>.", "h3"))
    s.append(p(
        "<b>Logic:</b> If the request has a Bearer token (or X-API-Key "
        "header), bucket by token value. Otherwise bucket by the client "
        "IP. This stops one authenticated client from exhausting the "
        "bucket of every anonymous caller from the same NAT, and stops "
        "one API key from being sprayed across many IPs."
    ))

    # Function 11
    s.append(p("6.11 ModelManager._load_detector() - src/core/model_manager.py", "h2"))
    s.append(p("<b>Purpose:</b> Pick the best available face detector at boot."))
    s.append(p("<b>Input:</b> None (reads paths from <font face='Courier'>self</font>).", "h3"))
    s.append(p("<b>Output:</b> None; sets <font face='Courier'>self.face_detector</font> "
               "and <font face='Courier'>self.detector_backend</font>.", "h3"))
    s.append(p(
        "<b>Logic:</b> Try YOLO first if the .pt file is present. If "
        "that fails or the file is missing, try RetinaFace. If <i>that</i> "
        "fails, fall back to OpenCV Haar Cascades so the service stays "
        "up. Log a clear backend label so <font face='Courier'>/health"
        "</font> can tell operators which detector is live."
    ))

    # Function 12
    s.append(p("6.12 safe_torch_load(path, map_location) - "
               "src/models/_torch_load.py", "h2"))
    s.append(p("<b>Purpose:</b> Safer version of <font face='Courier'>torch.load"
               "</font> that opts into PyTorch's locked-down pickle mode."))
    s.append(p("<b>Input:</b> A checkpoint file path; a device.", "h3"))
    s.append(p("<b>Output:</b> The deserialized checkpoint object.", "h3"))
    s.append(p(
        "<b>Logic:</b> Try <font face='Courier'>weights_only=True</font> "
        "first -- this rejects arbitrary Python objects, so a malicious "
        "checkpoint file cannot execute code during load. If the "
        "checkpoint contains non-tensor metadata that <font face='Courier'>"
        "weights_only=True</font> refuses, log a single warning and "
        "fall back to <font face='Courier'>weights_only=False</font>. "
        "Both of our shipped checkpoints succeed under "
        "<font face='Courier'>weights_only=True</font>, so the security "
        "win is real."
    ))

    # =====================================================================
    # 7. API DOCUMENTATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("7. API Documentation", "chapter"))
    s.append(p(
        "Every protected endpoint expects:"
    ))
    s.append(code("Authorization: Bearer <API_KEY>"))
    s.append(p("Failed requests return a uniform shape: "
               "<font face='Courier'>{'error': 'human-readable message'}"
               "</font>. Successful requests have endpoint-specific shapes."))

    s.append(p("7.1 Health probes", "h2"))
    s.append(endpoint_table([
        ("GET", "/", "Service banner."),
        ("GET", "/healthz", "Liveness probe. 200 while the process is alive."),
        ("GET", "/health", "Readiness probe. 200 with models loaded, 503 otherwise."),
    ]))

    s.append(p("7.2 Face APIs", "h2"))
    s.append(endpoint_table([
        ("POST", "/detect/faces",
            "Detect faces in a base64 image. Returns bounding boxes."),
        ("POST", "/verify/face",
            "Compare a face against a reference image OR an enrolled user_id."),
        ("POST", "/detect/behavior",
            "Per-frame behavior analysis (multi-face / gaze / head pose)."),
        ("POST", "/detect/liveness",
            "Verdict on a short clip: live human or static photo."),
        ("POST", "/embeddings",
            "Compute a 512-d ArcFace embedding for the largest face."),
        ("POST", "/batch/process",
            "Run detection or behavior analysis on many frames in one call."),
    ]))

    s.append(p("7.3 Enrollment", "h2"))
    s.append(endpoint_table([
        ("POST", "/enroll/face",
            "Append 1-5 reference photos for a user. Max 10 total per user."),
        ("POST", "/enroll/face/guided",
            "Submit 5-20 frames; the server picks the best+varied target_count."),
        ("GET", "/enroll/face/&lt;user_id&gt;",
            "Enrollment metadata. Never returns embedding values."),
        ("DELETE", "/enroll/face/&lt;user_id&gt;",
            "Delete all references for a user."),
    ]))

    s.append(p("7.4 Audit", "h2"))
    s.append(endpoint_table([
        ("GET", "/verifications/&lt;user_id&gt;",
            "Most-recent verify attempts for a user. Score / threshold / "
            "decision / metadata only."),
    ]))

    s.append(p("7.5 Session (internal)", "h2"))
    s.append(endpoint_table([
        ("POST", "/api/proctoring/session/start", "Start a session."),
        ("POST", "/api/proctoring/session/stop", "Stop + generate reports."),
        ("GET", "/api/proctoring/session/status", "Current session status."),
        ("GET", "/api/proctoring/session/report", "Current session report (JSON)."),
        ("GET", "/api/proctoring/video/frame", "Latest webcam frame (JPEG)."),
        ("GET", "/api/proctoring/video/stream", "Live MJPEG stream."),
        ("GET", "/api/proctoring/warnings", "Recent session warnings."),
        ("GET", "/api/proctoring/system-info", "Model + alignment + device info."),
    ]))

    s.append(p("7.6 Example: enrollment + verify", "h2"))
    s.append(code(
        "# Enroll three reference photos\n"
        "B1=$(base64 -w0 photo1.jpg)\n"
        "B2=$(base64 -w0 photo2.jpg)\n"
        "B3=$(base64 -w0 photo3.jpg)\n"
        "\n"
        "curl -X POST http://localhost:5000/enroll/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"user_id\\\": \\\"student_001\\\", \"\\\n"
        "      \"\\\"images\\\": [\\\"$B1\\\", \\\"$B2\\\", \\\"$B3\\\"]}\"\n"
        "\n"
        "# Response (201):\n"
        "# {\n"
        "#   \"user_id\": \"student_001\",\n"
        "#   \"added\": [\"a1b2c3...\", \"d4e5f6...\", \"g7h8i9...\"],\n"
        "#   \"added_count\": 3,\n"
        "#   \"total_references\": 3,\n"
        "#   \"skipped\": [],\n"
        "#   \"model_backend\": \"arcface_efficientnet_b0_emb512\"\n"
        "# }\n"
        "\n"
        "# During exam: verify\n"
        "LIVE=$(base64 -w0 live_capture.jpg)\n"
        "curl -X POST http://localhost:5000/verify/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"current_face\\\": \\\"$LIVE\\\", \\\n"
        "       \\\"user_id\\\": \\\"student_001\\\"}\"\n"
        "\n"
        "# Response (200):\n"
        "# {\n"
        "#   \"is_match\": true,\n"
        "#   \"match_score\": 0.6730,\n"
        "#   \"confidence\": 0.6730,\n"
        "#   \"details\": {\n"
        "#     \"method\": \"arcface_max_similarity_over_references\",\n"
        "#     \"threshold_used\": 0.4,\n"
        "#     \"user_id\": \"student_001\",\n"
        "#     \"references_compared\": 3,\n"
        "#     \"best_reference_id\": \"a1b2c3...\",\n"
        "#     \"all_scores\": [0.6730, 0.5121, 0.3575],\n"
        "#     \"embedding_dim\": 512\n"
        "#   }\n"
        "# }"
    ))

    # =====================================================================
    # 8. EXECUTION FLOW
    # =====================================================================
    s.append(PageBreak())
    s.append(p("8. Execution Flow", "chapter"))

    s.append(p("8.1 What happens at startup", "h2"))
    s.append(p("From <font face='Courier'>python app.py</font> to first "
               "request served, in order:"))
    s.extend(bullets([
        "<b>1.</b> Python imports <font face='Courier'>app.py</font>, which "
        "in turn imports <font face='Courier'>config/settings.py</font>. "
        "Settings reads <font face='Courier'>.env</font> via python-dotenv. "
        "If <font face='Courier'>ENVIRONMENT=production</font> and a "
        "required secret is missing, the import raises and the process "
        "exits.",
        "<b>2.</b> Logging is configured: console + rotating file handler "
        "at <font face='Courier'>logs/proctoring.log</font>.",
        "<b>3.</b> The FastAPI app object is created via "
        "<font face='Courier'>create_app()</font>. Middlewares + routers + "
        "exception handlers are registered. No models are loaded yet.",
        "<b>4.</b> Uvicorn binds the port and starts the event loop. The "
        "<font face='Courier'>lifespan</font> async context manager runs.",
        "<b>5.</b> <font face='Courier'>_init_proctoring_system()</font> "
        "either builds a real <font face='Courier'>ProctoringSystem</font> "
        "(loading YOLO, ArcFace, MediaPipe) or, if <font face='Courier'>"
        "MOCK_MODELS=1</font>, a stub. The result is attached to "
        "<font face='Courier'>app.state.system</font>.",
        "<b>6.</b> The enrollment and audit SQLite stores are opened "
        "(creating tables on first run).",
        "<b>7.</b> The MediaPipe FaceLandmarker model is lazy-loaded "
        "later on first use of <font face='Courier'>/detect/liveness</font>.",
        "<b>8.</b> Uvicorn logs 'Application startup complete' and starts "
        "accepting connections.",
    ]))

    s.append(p("8.2 What happens when a user calls /verify/face", "h2"))
    s.extend(bullets([
        "The TCP connection comes in (via Caddy if you're using TLS).",
        "Middlewares: body-size, request-ID generation, process-time "
        "timer start, rate-limit bucket check, CORS preflight if applicable.",
        "Routing: FastAPI matches the path to <font face='Courier'>"
        "verify_face</font>.",
        "Dependency: <font face='Courier'>require_api_key</font> runs. "
        "If the token is wrong, 401 is raised and control returns up the "
        "middleware stack, which still sets X-Request-ID and X-Process-Time.",
        "Body parsing: pydantic <font face='Courier'>VerifyFaceRequest"
        "</font> validates the JSON.",
        "Route body: decode base64 -> YOLO -> align -> embed -> SQLite "
        "lookup -> cosine -> verdict -> audit row written.",
        "Response: JSON body returned. Middlewares add X-Process-Time, "
        "X-Request-ID, X-RateLimit-* headers.",
        "Connection closes (or stays open for HTTP/2 multiplexing).",
    ]))

    s.append(p("8.3 What happens when a user enrolls via /enroll/face/guided", "h2"))
    s.extend(bullets([
        "Auth + body validation (5-20 base64 frames).",
        "Each frame is decoded, run through YOLO; frames without a "
        "detected face are appended to <font face='Courier'>skipped"
        "</font>.",
        "Each viable frame gets a face crop and an embedding.",
        "Quality-then-diversity selection picks the best target_count "
        "(default 3) frames.",
        "If <font face='Courier'>replace_existing=true</font>, the user's "
        "previous references are deleted first.",
        "The enrollment service writes one row to <font face='Courier'>"
        "users</font> (UPSERT) and target_count rows to "
        "<font face='Courier'>face_references</font>.",
        "The response includes selection metrics so the client knows "
        "how varied the picked frames were.",
    ]))

    # =====================================================================
    # 9. ENVIRONMENT & SETUP
    # =====================================================================
    s.append(PageBreak())
    s.append(p("9. Environment & Setup", "chapter"))

    s.append(p("9.1 Environment variables", "h2"))
    s.append(kv_table([
        ("ENVIRONMENT",
            "<font face='Courier'>development</font> or "
            "<font face='Courier'>production</font>. Production triggers "
            "fail-closed checks on secrets."),
        ("DEBUG",
            "<font face='Courier'>true</font>/<font face='Courier'>false"
            "</font>. Auto-on in development. Controls auto-reload."),
        ("HOST / PORT",
            "Bind address and port. Defaults: 0.0.0.0:5000."),
        ("SECRET_KEY",
            "Session signing key. Required in production. Generate with "
            "<font face='Courier'>python -c \"import secrets; "
            "print(secrets.token_urlsafe(48))\"</font>."),
        ("API_KEY",
            "Bearer token. Required in production. Same generation method."),
        ("API_KEY_REQUIRED",
            "Default true when API_KEY is set. Set false to disable auth (dev only)."),
        ("CORS_ORIGINS",
            "Comma-separated origins. Default * (warns at boot in production)."),
        ("LOG_LEVEL",
            "DEBUG / INFO / WARNING / ERROR. Default depends on DEBUG."),
        ("MODELS_DIR",
            "Where model files live. Default <font face='Courier'>./models_data</font>."),
        ("DATA_DIR",
            "Where SQLite DB lives. Default <font face='Courier'>./data</font>."),
        ("ENROLLMENT_DB_PATH",
            "Override the SQLite path explicitly."),
        ("FACE_MATCH_THRESHOLD",
            "Cosine threshold for verification. Default 0.4 (tuned for "
            "webcam-vs-registered-photo)."),
        ("FACE_DETECTION_CONFIDENCE",
            "Detector confidence cutoff. Default 0.5."),
        ("MAX_FACES_ALLOWED",
            "More than this fires a behavior warning. Default 1."),
        ("MOCK_MODELS",
            "Set to 1 to skip real model loading (CI uses this)."),
    ]))

    s.append(p("9.2 Local development setup", "h2"))
    s.append(code(
        "# 1. Clone\n"
        "git clone https://github.com/evankafauzya/capstone-backend.git\n"
        "cd capstone-backend\n"
        "\n"
        "# 2. Drop your model files into models_data/:\n"
        "#    face_detection_yolo.pt\n"
        "#    face_recognition_efficient.pth  (or face_recognition_model.pth)\n"
        "#    face_landmarker.task\n"
        "#    face_detection_model.pth        (optional RetinaFace fallback)\n"
        "\n"
        "# 3. Python virtual environment\n"
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate      # macOS / Linux\n"
        "pip install -r requirements.txt\n"
        "\n"
        "# 4. Environment\n"
        "cp .env.example .env\n"
        "# Edit .env -- set SECRET_KEY and API_KEY (use the secrets one-liner)\n"
        "\n"
        "# 5. Run\n"
        "python app.py\n"
        "\n"
        "# 6. Browser -> http://localhost:5000/docs"
    ))

    s.append(p("9.3 Docker (recommended for production)", "h2"))
    s.append(code(
        "# Same models_data/ + .env setup as local\n"
        "docker compose up -d --build\n"
        "\n"
        "# Health check\n"
        "curl http://localhost:5000/health\n"
        "\n"
        "# Logs\n"
        "docker compose logs -f\n"
        "\n"
        "# Stop\n"
        "docker compose down"
    ))

    s.append(p("9.4 Docker + TLS via Caddy", "h2"))
    s.append(code(
        "# Copy and edit the Caddyfile for your domain\n"
        "cp Caddyfile.example Caddyfile\n"
        "\n"
        "# Start with the TLS overlay\n"
        "docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build\n"
        "\n"
        "# Caddy auto-fetches Let's Encrypt cert for your domain.\n"
        "# Browser -> https://proctoring.example.com/docs"
    ))

    s.append(p("9.5 Running the tests", "h2"))
    s.append(code(
        "# All 22 tests (real models if .pt/.pth files are present, otherwise stubs)\n"
        "pytest tests/ -v\n"
        "\n"
        "# Force mock mode (fast, no model files needed)\n"
        "MOCK_MODELS=1 pytest tests/ -v\n"
        "\n"
        "# Lint with ruff (zero unused imports, no dead code)\n"
        "python -m ruff check . --exclude venv --exclude __pycache__"
    ))

    s.append(p("9.6 Common pitfalls", "h2"))
    s.append(kv_table([
        ("RuntimeError: SECRET_KEY is required",
            "Set SECRET_KEY and API_KEY in .env or container env. The "
            "fail-closed check is intentional in production."),
        ("/health returns 503",
            "One of the models failed to load. Check the boot logs and "
            "confirm the files are in models_data/."),
        ("Verify scores look low",
            "Check /api/proctoring/system-info and confirm "
            "alignment_enabled is true. If false, the face_landmarker.task "
            "file is missing -- drop it into models_data/."),
        ("Match never reaches threshold",
            "Re-enroll with webcam photos at the same camera + lighting "
            "as the live frames (not a studio portrait). OR lower "
            "FACE_MATCH_THRESHOLD to 0.35."),
        ("404 on verify by user_id",
            "That user_id has no enrolled references. Enroll first via "
            "/enroll/face or /enroll/face/guided."),
        ("Webcam endpoints fail in Docker",
            "Containers do not see the host webcam by default. Use the "
            "base64 image endpoints, or run outside Docker for live capture."),
    ]))

    s.append(p("9.7 You're done. Now what?", "h2"))
    s.append(p(
        "Open <font face='Courier'>http://localhost:5000/docs</font>. "
        "Click the green Authorize button, paste your API_KEY, and start "
        "calling endpoints. Every endpoint is documented with its request "
        "schema and example response."
    ))
    s.append(p(
        "Then read the source code, starting with <font face='Courier'>"
        "app.py</font>. Open files referenced by imports. Within an hour "
        "you should have a clear mental model of how the whole system fits "
        "together. Good luck."
    ))

    return s


# ===========================================================================
#                          BAHASA INDONESIA
# ===========================================================================
def build_indonesian():
    s = []

    # ---- Cover ----
    s.append(p("Moodle Proctoring AI Backend", "cover_title"))
    s.append(p("Kursus Pemula &middot; Panduan mendalam untuk mahasiswa "
               "tingkat satu yang baru mengenal pengembangan backend",
               "cover_sub"))
    s.append(note(
        "Ini adalah versi dokumentasi yang dalam dan bersifat mengajar. "
        "Setiap pilihan teknis dijelaskan dengan bahasa sederhana dan "
        "dibandingkan dengan alternatif yang kami pertimbangkan. Jika "
        "Anda belum pernah membangun web service, mulailah di sini dan "
        "baca dari awal sampai akhir. Contoh kode bisa langsung di-copy."
    ))

    # =====================================================================
    # 1. PROJECT OVERVIEW
    # =====================================================================
    s.append(PageBreak())
    s.append(p("1. Gambaran Proyek", "chapter"))

    s.append(p("1.1 Masalah di dunia nyata", "h2"))
    s.append(p(
        "Bayangkan sebuah universitas yang memperbolehkan mahasiswa "
        "mengerjakan ujian akhir dari rumah. Tanpa pengawasan, mahasiswa "
        "bisa minta tolong teman untuk menjawab, membuka jawaban di tab "
        "lain, atau menyembunyikan HP di belakang layar. <i>Online "
        "proctoring</i> adalah praktik mengawasi webcam mahasiswa selama "
        "ujian untuk mencegah dan mendeteksi kecurangan seperti ini."
    ))
    s.append(p(
        "Pengawasan manual (satu pengawas mengamati setiap mahasiswa "
        "lewat Zoom) tidak scalable: satu pengawas untuk 30 mahasiswa "
        "berarti ratusan staf tambahan untuk satu minggu ujian. AI "
        "proctoring memakai computer vision untuk melakukan pengawasan "
        "rutin secara otomatis, sehingga manusia hanya perlu mereview "
        "momen-momen yang mencurigakan. <b>Proyek ini adalah setengah "
        "backend dari AI proctor</b>: plugin Moodle mengirim frame webcam "
        "ke kita, kita mengembalikan jawaban JSON."
    ))

    s.append(p("1.2 Apa yang dilakukan backend ini, dalam satu kalimat", "h2"))
    s.append(p(
        "<i>Diberikan sebuah gambar mahasiswa di depan webcam, backend "
        "mengembalikan jawaban JSON untuk empat pertanyaan: apakah ada "
        "wajah, apakah itu mahasiswa yang terdaftar, apakah itu manusia "
        "hidup (bukan foto cetak), dan apakah ada hal mencurigakan yang "
        "terjadi.</i>"
    ))

    s.append(p("1.3 Fitur utama", "h2"))
    s.extend(bullets([
        "<b>Deteksi wajah</b> -- menemukan setiap wajah dalam gambar dan "
        "mengembalikan bounding box-nya.",
        "<b>Verifikasi wajah</b> -- memutuskan apakah wajah live cocok "
        "dengan mahasiswa terdaftar. Dua mode: terhadap satu foto "
        "referensi, atau terhadap beberapa foto referensi yang sudah "
        "didaftarkan sebelumnya.",
        "<b>Deteksi liveness</b> -- diberikan klip pendek (beberapa frame "
        "selama ~2 detik), memutuskan apakah subjek adalah manusia hidup "
        "(berkedip + gerakan kepala kecil) atau foto statis yang "
        "diarahkan ke kamera.",
        "<b>Analisis perilaku</b> -- pada satu frame, mencari sinyal "
        "mencurigakan: wajah berganda, kepala menengok jauh ke samping, "
        "mata tidak ke layar.",
        "<b>Enrollment (pendaftaran)</b> -- menyimpan wajah referensi "
        "mahasiswa di bawah user_id agar panggilan verify di masa depan "
        "bisa mencarinya.",
        "<b>Audit log</b> -- setiap verifikasi dicatat dengan skor, "
        "threshold, dan keputusan, sehingga sengketa punya jejak bukti.",
        "<b>Siklus sesi</b> -- mulai sesi di awal ujian, kumpulkan "
        "peringatan, hasilkan laporan di akhir.",
    ]))

    s.append(p("1.4 Alur kerja keseluruhan", "h2"))
    s.append(p(
        "Sebuah ujian biasa punya tiga fase. Setiap fase menggunakan "
        "endpoint yang berbeda di backend kita:"
    ))
    s.append(kv_table([
        ("1. Enrollment (sekali per semester)",
            "Admin atau mahasiswa sendiri mengunggah 3-5 foto referensi. "
            "Backend menghitung face embedding untuk setiap foto dan "
            "menyimpannya di database dengan key user_id. Byte gambar "
            "asli <b>tidak</b> disimpan -- hanya embedding 512 angka saja."),
        ("2. Cek liveness (mulai ujian)",
            "Frontend merekam ~2 detik frame webcam dan mengirimkannya. "
            "Backend mencari kedipan dan gerakan kepala kecil. Jika "
            "keduanya tidak ada, backend mencurigai serangan foto statis."),
        ("3. Verify (berkala selama ujian)",
            "Setiap satu-dua menit, frontend mengambil satu frame dan "
            "bertanya 'apakah ini masih student_001?'. Backend "
            "membandingkan wajah live dengan setiap referensi terdaftar "
            "dan mengembalikan skor kemiripan maksimum, plus keputusannya."),
    ]))

    # =====================================================================
    # 2. TECHNOLOGY STACK
    # =====================================================================
    s.append(PageBreak())
    s.append(p("2. Technology Stack", "chapter"))
    s.append(p(
        "Setiap proyek memilih teknologi. Kadang pilihan jelas; kadang "
        "merupakan trade-off. Bab ini menjelaskan setiap teknologi yang "
        "kita pakai dan -- yang penting -- alternatif mana yang kita "
        "pertimbangkan dan mengapa tidak kita pilih."
    ))

    s.append(p("2.1 Bahasa pemrograman: Python 3.11", "h2"))
    s.append(p(
        "Python adalah bahasa untuk machine learning. Hampir setiap "
        "library computer vision modern (PyTorch, OpenCV, MediaPipe, "
        "Ultralytics) ditulis dalam Python atau punya Python binding "
        "sebagai interface utamanya."
    ))
    s.append(why("Mengapa Python dibanding Node.js / Go / Java?",
        "Kecepatan pengembangan lebih penting daripada kecepatan runtime "
        "untuk volume request kita (beberapa request per detik per "
        "mahasiswa, bukan ribuan per detik). Dan Python adalah satu-"
        "satunya bahasa di mana Anda bisa memanggil PyTorch + MediaPipe "
        "+ OpenCV tanpa menulis wrapper sendiri. Node.js punya "
        "TensorFlow.js tapi ekosistemnya jauh lebih tipis. Go dan Java "
        "punya masalah serupa -- bagus untuk web server throughput "
        "tinggi, lemah untuk AI."))
    s.append(why("Mengapa 3.11 khususnya?",
        "3.11 lebih cepat (sekitar 25% lebih cepat dari 3.10 untuk "
        "kebanyakan kode), masih mendukung setiap library yang kita "
        "butuhkan, dan merupakan versi yang diuji resmi oleh PyTorch. "
        "3.12+ juga jalan tapi beberapa library scientific masih tertinggal."))

    s.append(p("2.2 Web framework: FastAPI", "h2"))
    s.append(p(
        "FastAPI adalah library Python yang mengubah fungsi Python "
        "menjadi HTTP endpoint. Anda menulis fungsi dengan type hints; "
        "FastAPI otomatis memvalidasi request masuk, mengembalikan "
        "response JSON, dan menghasilkan Swagger UI yang interaktif."
    ))
    s.append(code(
        "from fastapi import FastAPI\n"
        "from pydantic import BaseModel\n"
        "\n"
        "app = FastAPI()\n"
        "\n"
        "class HelloRequest(BaseModel):\n"
        "    name: str\n"
        "\n"
        "@app.post('/hello')\n"
        "def hello(body: HelloRequest):\n"
        "    return {'message': f'Halo {body.name}'}"
    ))
    s.append(why("Mengapa FastAPI dibanding Flask?",
        "Flask lebih sederhana tapi butuh validasi request manual -- "
        "Anda menulis <font face='Courier'>data.get('name')</font> dan "
        "berdoa nilainya ada. FastAPI memakai pydantic untuk validasi "
        "request sebelum fungsi Anda jalan, menangkap bug lebih awal. "
        "FastAPI juga otomatis generate OpenAPI 3 docs (Swagger UI di "
        "<font face='Courier'>/docs</font>); dengan Flask kita pakai "
        "flasgger yang menghasilkan spec rusak (mencampur Swagger 2.0 "
        "dan field OpenAPI 3). Dan FastAPI mendukung async secara native "
        "untuk workload I/O-bound -- tidak kritis di sini, tapi "
        "future-proof."))
    s.append(why("Mengapa FastAPI dibanding Django?",
        "Django adalah framework full-stack 'batteries-included' -- ORM, "
        "admin panel, template, sesi, semuanya. Kita tidak butuh itu "
        "semua. Kita butuh JSON API kecil. Django akan memaksa kita "
        "membawa ratusan fitur yang tidak pernah dipakai, ditambah lebih "
        "berat dan boot lebih lambat."))

    s.append(p("2.3 ASGI server: Uvicorn di belakang Gunicorn", "h2"))
    s.append(p(
        "FastAPI adalah framework-nya, tapi Anda tetap butuh <b>server</b> "
        "yang listen di port dan mengarahkan request ke framework. Kita "
        "memakai Uvicorn (runner standar untuk ASGI Python apps) yang "
        "diawasi Gunicorn (process manager Linux yang sudah teruji)."
    ))
    s.append(why("Mengapa dua bagian?",
        "Uvicorn sendiri sudah cukup di development. Di production, Anda "
        "ingin Gunicorn membungkusnya supaya proses otomatis restart "
        "saat crash, graceful-reload saat menerima sinyal, dan rotasi "
        "file log. Gunicorn + Uvicorn worker class adalah resep "
        "production resmi FastAPI."))
    s.append(why("Mengapa hanya satu worker?",
        "Setiap worker memuat ~250 MB PyTorch + YOLO + MediaPipe ke "
        "memori. Dua worker = RAM dua kali lipat. Karena FastAPI "
        "menjalankan handler sync di thread pool, satu worker dengan "
        "banyak thread menangani request konkuren sama baiknya pada "
        "skala kita."))

    s.append(p("2.4 Framework deep learning: PyTorch", "h2"))
    s.append(p(
        "PyTorch adalah library Python yang menjalankan neural network "
        "kita. Saat kita memanggil <font face='Courier'>model(image)"
        "</font>, PyTorch menggerakkan tensor gambar melewati layer-"
        "layer network (convolution, batch normalization, activation) "
        "dan mengembalikan tensor output."
    ))
    s.append(why("Mengapa PyTorch dibanding TensorFlow?",
        "Dua alasan. Pertama, model yang Anda train (RetinaFace dan "
        "ArcFace) disimpan sebagai file PyTorch <font face='Courier'>"
        ".pth</font>; beralih ke TensorFlow berarti retrain semuanya. "
        "Kedua, PyTorch mendominasi riset akademik, jadi saat paper "
        "face recognition baru rilis, kode referensinya hampir selalu "
        "PyTorch."))

    s.append(p("2.5 Deteksi wajah: Ultralytics YOLO (utama)", "h2"))
    s.append(p(
        "YOLO ('You Only Look Once') adalah keluarga model deteksi objek "
        "yang cepat. Package Ultralytics membungkus arsitektur YOLOv8 "
        "dalam API Python yang ramah. Kita memakai varian satu-kelas "
        "yang dilatih khusus untuk mendeteksi wajah."
    ))
    s.append(why("Mengapa YOLO dibanding RetinaFace?",
        "Keduanya detektor wajah yang bagus. Perbedaannya muncul pada "
        "input rumit: RetinaFace MobileNet0.25 sering memunculkan "
        "deteksi pada area kecil ber-confidence tinggi seperti sudut "
        "mata atau bayangan pada background bertekstur, menghasilkan "
        "puluhan false positive 'wajah 18x7 piksel'. YOLO punya lebih "
        "sedikit false positive dengan trade-off edge bounding box "
        "sedikit kurang akurat. Untuk backend proctoring, false "
        "positive yang lebih sedikit adalah pilihan yang benar -- "
        "lebih baik melewatkan edge case daripada berhalusinasi wajah "
        "yang tidak ada."))
    s.append(why("Mengapa tetap menyimpan RetinaFace?",
        "Sebagai fallback. Jika <font face='Courier'>face_detection_"
        "yolo.pt</font> hilang atau gagal dimuat, sistem otomatis "
        "berpindah ke RetinaFace sehingga Anda punya <i>detector</i> "
        "apa pun. RetinaFace juga mengembalikan lima landmark wajah "
        "secara cuma-cuma, yang kita pakai di <font face='Courier'>"
        "/detect/behavior</font> untuk estimasi gaze."))

    s.append(p("2.6 Face alignment: MediaPipe FaceLandmarker", "h2"))
    s.append(p(
        "Sebelum kita memberi wajah ke model recognition, kita ingin "
        "setiap wajah terlihat sama (mata horizontal, wajah di tengah "
        "gambar 112x112). MediaPipe adalah library open-source Google "
        "yang menemukan 478 titik landmark di wajah. Kita memakai 5 di "
        "antaranya -- kedua pusat mata, ujung hidung, dan dua sudut "
        "mulut -- untuk menghitung similarity transform yang merotasi "
        "dan menskalakan wajah ke posisi kanonis."
    ))
    s.append(why("Mengapa alignment penting",
        "ArcFace dilatih pada wajah yang sudah aligned. Jika Anda "
        "melewati alignment dan memberinya wajah miring, embedding "
        "bergerak signifikan meski identitasnya sama. Dalam pengujian "
        "kita, menambahkan alignment menaikkan skor match satu panggilan "
        "verify live dari ~0,44 ke ~0,75 untuk orang yang sama."))
    s.append(why("Mengapa MediaPipe dibanding dlib atau InsightFace?",
        "MediaPipe jalan di CPU dengan kecepatan real-time, tidak butuh "
        "GPU, di-maintain oleh Google (jadi tidak akan menghilang), dan "
        "hanya berukuran 3,7 MB file <font face='Courier'>.task</font> "
        "saja. Landmark detector dlib lebih lambat; InsightFace lebih "
        "cepat tapi membawa lebih banyak dependency."))

    s.append(p("2.7 Face recognition: ArcFace (ResNet50 atau EfficientNet-B0)", "h2"))
    s.append(p(
        "Face recognition adalah proses dua langkah. Pertama, model "
        "mengubah crop wajah 112x112 menjadi vektor 512 angka yang "
        "disebut <i>embedding</i>. Dua embedding dari orang yang sama "
        "menunjuk ke arah yang nyaris sama; dua embedding orang berbeda "
        "menunjuk ke arah berbeda. Untuk memutuskan apakah dua wajah "
        "cocok, Anda menghitung sudut antara embedding mereka (<i>"
        "cosine similarity</i>) dan membandingkan dengan threshold."
    ))
    s.append(p(
        "ArcFace adalah teknik training yang menghasilkan embedding "
        "terbaik untuk tugas ini. Anda beri wajah, dia beri 512 angka, "
        "selesai. Sistem kita mendukung dua backbone ArcFace: ResNet50 "
        "(200 MB, original) dan EfficientNet-B0 (40 MB, lebih kecil dan "
        "cepat tapi akurasi mirip). Sistem otomatis mendeteksi backbone "
        "mana berdasarkan shape checkpoint."
    ))
    s.append(why("Mengapa ArcFace dibanding FaceNet / VGGFace?",
        "Objective training ArcFace menambah angular margin antar kelas, "
        "yang menghasilkan cluster orang yang sama lebih rapat dan gap "
        "antar orang berbeda lebih lebar. Secara empiris ini sudah jadi "
        "state-of-the-art untuk face verification sejak 2019. FaceNet "
        "(2015) lebih lama dan menghasilkan cluster yang sedikit lebih "
        "kusut. VGGFace bahkan lebih lama."))

    s.append(p("2.8 Database: SQLite", "h2"))
    s.append(p(
        "SQLite adalah database SQL kecil yang tinggal di satu file. "
        "Tidak ada proses server terpisah -- Anda buka file, jalankan "
        "query, tutup file. Sistem kita memakai satu file SQLite di "
        "<font face='Courier'>data/enrollments.db</font> dengan tiga "
        "tabel: <i>users</i> (satu baris per mahasiswa terdaftar), <i>"
        "face_references</i> (satu baris per embedding referensi), dan "
        "<i>verifications</i> (satu baris per entri audit log)."
    ))
    s.append(why("Mengapa SQLite dibanding PostgreSQL atau MongoDB?",
        "Tiga alasan. Pertama, skala kita: jumlah mahasiswa satu kampus "
        "masih dalam zona nyaman SQLite (ratusan ribu baris). Kedua, "
        "deployment: PostgreSQL butuh container atau service terpisah "
        "untuk jalan. SQLite tidak butuh apa-apa -- cukup satu file. "
        "Ketiga, backup: menyalin satu file <i>adalah</i> backupnya. "
        "Saat Anda mulai out-grow (multiple writer, multi-region), "
        "migrasi ke Postgres adalah pekerjaan satu hari karena SQL-nya "
        "tetap sama."))

    s.append(p("2.9 Pydantic untuk validasi request", "h2"))
    s.append(p(
        "Pydantic adalah library Python untuk mendeklarasikan bagaimana "
        "sepotong data seharusnya terlihat, lalu otomatis memeriksa "
        "memang seperti itu. Kita memakainya untuk mendefinisikan setiap "
        "request body dan response model API."
    ))
    s.append(code(
        "class EnrollFaceRequest(BaseModel):\n"
        "    user_id: str\n"
        "    images: List[str] = Field(..., min_length=1, max_length=5)"
    ))
    s.append(p(
        "Jika klien mengirim <font face='Courier'>images</font> dengan "
        "enam item, pydantic menolak request dengan 422 sebelum kode "
        "kita jalan. Model yang sama menjadi schema OpenAPI di Swagger "
        "UI secara gratis."
    ))
    s.append(why("Mengapa pydantic dibanding validasi manual?",
        "Validasi manual (<font face='Courier'>if 'images' not in data: "
        "...</font>) bertele-tele, rentan bug, dan tidak konsisten. "
        "Pydantic memberi Anda validasi deklaratif, pesan error yang "
        "jelas, dan generasi schema gratis -- semua dalam lima baris."))

    s.append(p("2.10 slowapi untuk rate limiting", "h2"))
    s.append(p(
        "Tanpa rate limiting, klien yang bermasalah (atau attacker) bisa "
        "menghantam endpoint <font face='Courier'>/verify/face</font> "
        "yang GPU-bound ribuan kali per detik dan menghabiskan server. "
        "slowapi memungkinkan Anda menetapkan batas per IP atau per API "
        "token. Default kita: 600 request per menit, cukup untuk "
        "penggunaan normal tapi membatasi penyalahgunaan."
    ))

    s.append(p("2.11 Caddy untuk TLS", "h2"))
    s.append(p(
        "Jika Anda men-deploy backend ini di server yang facing internet, "
        "Bearer token Anda akan bepergian dalam plaintext lewat HTTP. "
        "Siapa pun di jaringan bisa mencurinya. Solusinya adalah HTTPS, "
        "yang mengenkripsi koneksi. Caddy adalah web server kecil yang "
        "otomatis mengambil sertifikat TLS gratis dari Let's Encrypt "
        "untuk domain apa pun yang Anda arahkan ke sana."
    ))
    s.append(why("Mengapa Caddy dibanding Nginx?",
        "Nginx adalah standar industri tapi file konfigurasinya ditulis "
        "manual, dan Anda butuh program terpisah (certbot) untuk "
        "mengelola sertifikat TLS. Caddyfile Caddy jauh lebih sederhana "
        "(\"<font face='Courier'>proctoring.example.com { reverse_proxy "
        "app:5000 }</font>\" sudah keseluruhan konfigurasinya) dan dia "
        "otomatis renew sertifikat tanpa setup tambahan."))

    s.append(p("2.12 Docker untuk deployment", "h2"))
    s.append(p(
        "Docker mengemas kode Anda <i>plus</i> library sistem operasi "
        "yang dibutuhkannya ke dalam satu image. Saat Anda menjalankan "
        "image itu, program melihat environment yang sama di mana pun -- "
        "laptop Anda, server kampus, VM cloud. Tidak ada lagi 'jalan di "
        "mesin saya'. Docker Compose memungkinkan Anda mendeskripsikan "
        "setup multi-service (app + Caddy + volume) dalam satu file YAML."
    ))

    s.append(p("2.13 pytest + GitHub Actions untuk testing & CI", "h2"))
    s.append(p(
        "<b>pytest</b> adalah library testing Python standar: Anda menulis "
        "fungsi yang dimulai dengan <font face='Courier'>test_</font>, "
        "dan <font face='Courier'>pytest</font> menemukan dan "
        "menjalankannya. Kita punya 22 test yang menangani autentikasi, "
        "validasi, enrollment, audit, dan rate limiting."
    ))
    s.append(p(
        "<b>GitHub Actions</b> menjalankan test itu otomatis di setiap "
        "push dan pull request. Jika Anda merusak sesuatu, Anda tahu "
        "dalam dua menit -- bukan saat dosen mereview kode Anda."
    ))

    s.append(p("2.14 Library lainnya (penjelasan satu baris)", "h2"))
    s.append(kv_table([
        ("OpenCV (cv2)",
            "Baca/tulis gambar, konversi warna, resize. Swiss Army knife "
            "computer vision."),
        ("NumPy",
            "Array numerik cepat. Setiap gambar yang kita sentuh adalah "
            "NumPy array di balik layar."),
        ("ReportLab",
            "Generate PDF. Dipakai report generator dan script doc-generator."),
        ("requests",
            "Membuat HTTP outbound. Belum dipakai tapi disimpan untuk "
            "integrasi webhook Moodle di masa depan."),
        ("python-dotenv",
            "Memuat file <font face='Courier'>.env</font> ke environment "
            "variable saat boot."),
    ]))

    s.append(p("2.15 Development environment", "h2"))
    s.append(p(
        "Anda butuh: Python 3.11+, git, dan (opsional) Docker. Kebanyakan "
        "developer memakai Visual Studio Code dengan extension Python. "
        "Workflow yang direkomendasikan:"
    ))
    s.append(code(
        "git clone https://github.com/evankafauzya/capstone-backend.git\n"
        "cd capstone-backend\n"
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate      # macOS / Linux\n"
        "pip install -r requirements.txt\n"
        "cp .env.example .env            # lalu edit isinya\n"
        "python app.py"
    ))

    # =====================================================================
    # 3. SYSTEM ARCHITECTURE
    # =====================================================================
    s.append(PageBreak())
    s.append(p("3. Arsitektur Sistem", "chapter"))

    s.append(p("3.1 Gambaran besar", "h2"))
    s.append(p(
        "Backend ini dibangun berlapis (<b>layered</b>). Request masuk "
        "di atas, melewati setiap lapisan ke bawah, dan response kembali "
        "ke atas. Setiap lapisan punya satu pekerjaan sempit."
    ))
    s.append(code(DIAGRAM))

    s.append(p("3.2 Apa yang dilakukan setiap lapisan", "h2"))
    s.append(kv_table([
        ("Caddy (opsional)",
            "Menerminate HTTPS, meneruskan request ke FastAPI lewat HTTP "
            "biasa di dalam network Docker. Juga jadi gateway HSTS / "
            "security header."),
        ("Middlewares",
            "Cross-cutting concern yang berlaku untuk setiap request: "
            "enforce body size maksimum (50 MB), generate / propagate "
            "X-Request-ID, ukur waktu proses, enforce rate limit, dan "
            "tangani CORS untuk pemanggil browser."),
        ("Auth dependency",
            "Membaca Bearer token dari header Authorization, "
            "membandingkannya (dengan hmac.compare_digest, untuk mencegah "
            "timing attack) terhadap environment variable API_KEY, dan "
            "menolak request dengan 401 jika tidak cocok."),
        ("Route handler",
            "Fungsi-fungsi kecil yang men-decode request body via "
            "pydantic, memanggil layer core / services, dan memformat "
            "response. Tidak berisi logika AI sendiri."),
        ("Orchestrator + ModelManager",
            "Memiliki object berat: model YOLO, model ArcFace, aligner "
            "MediaPipe. Dimuat sekali saat boot, dipakai ulang untuk "
            "setiap request supaya kita tidak bayar biaya load per call."),
        ("Services (enrollment + audit)",
            "Layer persistensi. Mereka berbicara ke SQLite. Route TIDAK "
            "berbicara ke SQLite secara langsung -- mereka lewat services "
            "sehingga kita bisa swap database nanti tanpa menyentuh route."),
    ]))

    s.append(p("3.3 Mengikuti satu request verify dari awal sampai akhir", "h2"))
    s.append(p(
        "Contoh konkret: klien memanggil <font face='Courier'>POST "
        "/verify/face</font> dengan frame webcam ter-base64-encode dan "
        "user_id."
    ))
    s.extend(bullets([
        "<b>Langkah 1: TLS.</b> Caddy men-decrypt request HTTPS, melihat "
        "POST ke <font face='Courier'>/verify/face</font>, meneruskan ke "
        "<font face='Courier'>app:5000</font>.",
        "<b>Langkah 2: middlewares.</b> Middleware body-size memastikan "
        "request di bawah 50 MB. Middleware request-ID generate ID unik "
        "16 karakter dan melampirkannya ke <font face='Courier'>"
        "request.state</font>. Middleware rate-limit memeriksa Bearer "
        "token ini belum melewati 600/menit.",
        "<b>Langkah 3: auth.</b> Dependency <font face='Courier'>"
        "require_api_key</font> membaca <font face='Courier'>"
        "Authorization: Bearer ...</font>, membandingkan dengan "
        "<font face='Courier'>API_KEY</font>. Token salah: 401 sebelum "
        "AI mana pun jalan.",
        "<b>Langkah 4: pydantic.</b> Request body di-parse menjadi model "
        "<font face='Courier'>VerifyFaceRequest</font>. Tidak ada "
        "<font face='Courier'>current_face</font>: 422 dengan error rapi.",
        "<b>Langkah 5: decode.</b> String base64 diubah ke array gambar "
        "NumPy (BGR, konvensi OpenCV).",
        "<b>Langkah 6: detect.</b> Gambar melewati YOLO. Kita dapat "
        "nol-atau-lebih bounding box dengan skor confidence.",
        "<b>Langkah 7: align.</b> Crop wajah terbesar dengan confidence "
        "tertinggi dilewatkan ke MediaPipe FaceLandmarker, yang "
        "mengembalikan 478 landmark. Kita ambil 5 titik kunci dan "
        "hitung similarity transform ke 112x112 kanonis.",
        "<b>Langkah 8: embed.</b> Crop yang sudah aligned dinormalisasi "
        "dan dijalankan melalui ArcFace, menghasilkan vector L2-"
        "normalized 512-d.",
        "<b>Langkah 9: lookup.</b> Service enrollment mengambil semua "
        "embedding tersimpan untuk user_id dari SQLite.",
        "<b>Langkah 10: compare.</b> Cosine similarity dihitung terhadap "
        "setiap embedding tersimpan; maksimum adalah skor match.",
        "<b>Langkah 11: audit.</b> Service audit menulis satu baris ke "
        "SQLite dengan (timestamp, user_id, score, threshold, decision, "
        "request_id).",
        "<b>Langkah 12: response.</b> JSON body dibangun dengan verdict "
        "plus diagnostik. Middleware menambah header X-Process-Time dan "
        "X-Request-ID. Caddy meng-encrypt kembali; klien melihat response.",
    ]))

    s.append(p("3.4 Mengapa arsitektur ini?", "h2"))
    s.append(why("Mengapa arsitektur berlapis?",
        "Setiap lapisan bisa di-test independen. Lapisan auth bisa "
        "di-test tanpa model AI dimuat. Recognizer bisa di-test tanpa "
        "HTTP server sama sekali. Tanpa pelapisan, test suite kita harus "
        "menjalankan seluruh stack untuk setiap assertion."))
    s.append(why("Mengapa services di antara route dan database?",
        "Jika suatu hari kita ganti SQLite ke PostgreSQL, kita hanya "
        "mengubah file service. Route tidak tahu SQL ada. Ini disebut "
        "<i>repository pattern</i> dalam jargon software engineering."))
    s.append(why("Mengapa load model sekali, bukan per-request?",
        "Memuat checkpoint EfficientNet ArcFace dari disk butuh 2-3 "
        "detik. Melakukannya per request akan memperlambat setiap "
        "verify secara drastis DAN membuang memori dengan menyimpan "
        "beberapa salinan."))

    # =====================================================================
    # 4. FOLDER STRUCTURE
    # =====================================================================
    s.append(PageBreak())
    s.append(p("4. Struktur Folder", "chapter"))

    s.append(p("4.1 Pohon folder", "h2"))
    s.append(code(
        "capstone-backend/\n"
        "|-- app.py                       # FastAPI factory + middlewares\n"
        "|-- asgi.py                      # Entry ASGI untuk Gunicorn\n"
        "|-- Dockerfile                   # Membangun image container\n"
        "|-- docker-compose.yml           # Deployment node tunggal\n"
        "|-- docker-compose.tls.yml       # Overlay yang menambahkan Caddy + TLS\n"
        "|-- Caddyfile.example            # Copy & edit untuk production\n"
        "|-- requirements.txt             # Dependency Python yang dipin\n"
        "|-- pytest.ini                   # Config test runner\n"
        "|-- .env.example                 # Template environment\n"
        "|-- README.md                    # Referensi teknis\n"
        "|-- .github/\n"
        "|   `-- workflows/ci.yml         # GitHub Actions: lint + test + docker build\n"
        "|-- config/\n"
        "|   `-- settings.py              # Baca .env, fail-closed di production\n"
        "|-- src/\n"
        "|   |-- api/\n"
        "|   |   |-- auth.py              # FastAPI dependency Bearer-token\n"
        "|   |   |-- moodle_routes.py     # /detect /verify /enroll /liveness ...\n"
        "|   |   |-- proctoring_routes.py # /api/proctoring/session/*\n"
        "|   |   `-- schemas.py           # Pydantic request/response models\n"
        "|   |-- core/\n"
        "|   |   |-- model_manager.py     # Memuat YOLO + ArcFace + aligner\n"
        "|   |   `-- orchestrator.py      # Mengelem model, sesi, laporan\n"
        "|   |-- models/\n"
        "|   |   |-- _torch_load.py       # Aman torch.load dengan weights_only=True\n"
        "|   |   |-- yolo_face_detector.py\n"
        "|   |   |-- retinaface.py        # Arsitektur + priors + NMS\n"
        "|   |   |-- face_detector.py     # Wrapper inference RetinaFace\n"
        "|   |   |-- arcface.py           # FaceEmbeddingNet (autodetect backbone)\n"
        "|   |   |-- face_aligner.py      # MediaPipe landmarker + transform\n"
        "|   |   `-- face_recognizer.py   # Align + embed + cosine\n"
        "|   |-- detectors/\n"
        "|   |   |-- eye_tracker.py       # Tracker blink / gaze sesi\n"
        "|   |   |-- face_detector.py     # Wrapper YOLO untuk sesi\n"
        "|   |   `-- liveness.py          # Analyzer blink + motion stateless\n"
        "|   |-- processors/\n"
        "|   |   |-- session_manager.py\n"
        "|   |   `-- webcam_capture.py\n"
        "|   |-- services/\n"
        "|   |   |-- face_enrollment.py   # SQLite enrollment store\n"
        "|   |   `-- audit.py             # SQLite verification audit log\n"
        "|   `-- utils/\n"
        "|       `-- report_generator.py  # Laporan JSON / TXT / PDF\n"
        "|-- tests/\n"
        "|   |-- conftest.py              # Fixtures + auto MOCK_MODELS\n"
        "|   |-- _stub_system.py          # ProctoringSystem palsu untuk CI\n"
        "|   `-- test_smoke.py            # 22 smoke test\n"
        "|-- docs/\n"
        "|   |-- build_docs.py            # Generator PDF referensi cepat\n"
        "|   `-- build_course.py          # Kursus INI (panduan dalam)\n"
        "|-- models_data/    (gitignored) # Taruh file YOLO + ArcFace + landmark di sini\n"
        "|-- data/           (gitignored) # Database SQLite tinggal di sini\n"
        "|-- reports/        (gitignored) # Laporan sesi yang dihasilkan\n"
        "`-- logs/           (gitignored) # Log aplikasi rotating"
    ))

    s.append(p("4.2 Bagaimana file terhubung satu sama lain", "h2"))
    s.append(p(
        "Anggap import sebagai panah dari file yang meng-import ke file "
        "yang mendefinisikan. Panah menunjuk ke dalam, ke inti kecil file "
        "domain-logic, dan keluar dari lapisan route. Dependency graph "
        "level tinggi:"
    ))
    s.extend(bullets([
        "<font face='Courier'>app.py</font> meng-import blueprint route "
        "dari <font face='Courier'>src.api</font>, orchestrator dari "
        "<font face='Courier'>src.core</font>, dan service penyimpanan "
        "dari <font face='Courier'>src.services</font>.",
        "<font face='Courier'>src.api.moodle_routes</font> meng-import "
        "schema, dependency auth, dan (lewat global yang di-set saat boot) "
        "orchestrator dan store.",
        "<font face='Courier'>src.core.orchestrator</font> meng-import "
        "detector (<font face='Courier'>src.detectors</font>) dan model "
        "manager (<font face='Courier'>src.core.model_manager</font>).",
        "<font face='Courier'>src.core.model_manager</font> meng-import "
        "tiga wrapper model dari <font face='Courier'>src.models</font>.",
        "<font face='Courier'>src.services</font> ada di bawah stack -- "
        "hanya meng-import standard library (<font face='Courier'>"
        "sqlite3</font>, <font face='Courier'>uuid</font>, "
        "<font face='Courier'>datetime</font>). Tidak ada yang meng-import "
        "services dari atas -- services adalah daun di dependency tree.",
    ]))

    # =====================================================================
    # 5. BACKEND EXPLANATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("5. Penjelasan Backend", "chapter"))

    s.append(p("5.1 Server setup (app.py)", "h2"))
    s.append(p(
        "<font face='Courier'>app.py</font> adalah <b>application "
        "factory</b>. Tugasnya menyatukan kabel-kabel FastAPI app dan "
        "mengembalikannya siap untuk melayani."
    ))
    s.append(p("Secara konkret, <font face='Courier'>create_app()</font> "
               "melakukan:", "h3"))
    s.extend(bullets([
        "Membaca konfigurasi dari environment variable via "
        "<font face='Courier'>config/settings.py</font>.",
        "Mengkonfigurasi logging (rotating file handler + konsol).",
        "Membangun instance FastAPI dengan judul, versi, dan "
        "<font face='Courier'>lifespan</font> context manager yang benar.",
        "Menambahkan middleware rate-limit, CORS, body-size, "
        "X-Request-ID, dan X-Process-Time.",
        "Mendaftarkan dua route blueprint (<font face='Courier'>"
        "moodle_api</font> dan <font face='Courier'>proctoring_api</font>).",
        "Mendaftarkan exception handler kustom yang membentuk ulang error "
        "Pydantic / Starlette menjadi shape <font face='Courier'>"
        "{'error': '...'}</font> seragam.",
        "Override <font face='Courier'>app.openapi</font> untuk "
        "memasukkan Bearer scheme sehingga Swagger UI menampilkan tombol "
        "Authorize.",
        "Menambahkan endpoint publik <font face='Courier'>/healthz</font> "
        "dan <font face='Courier'>/health</font>.",
    ]))

    s.append(p("5.2 Konteks lifespan", "h2"))
    s.append(p(
        "Startup butuh waktu: PyTorch harus memuat model 40-200 MB, "
        "MediaPipe harus memuat task landmark-nya, database SQLite harus "
        "dibuka atau dibuat. Kita melakukan semua itu <b>sekali</b>, di "
        "dalam async context manager <font face='Courier'>lifespan"
        "</font>. FastAPI memanggilnya saat startup, lalu lagi saat "
        "shutdown. Route bisa kemudian mengasumsikan semuanya sudah "
        "ter-inisialisasi."
    ))

    s.append(p("5.3 Routes (moodle_routes.py)", "h2"))
    s.append(p(
        "<font face='Courier'>moodle_routes.py</font> mendefinisikan "
        "<font face='Courier'>APIRouter</font> yang memiliki dependency "
        "auth Bearer terlampir di level router. Setiap route mewarisinya "
        "otomatis -- Anda tidak perlu mengulang <font face='Courier'>"
        "@require_api_key</font> di setiap endpoint."
    ))
    s.append(p(
        "Setiap fungsi route dirancang kecil: validasi, decode, delegasi, "
        "format. Logika AI tinggal di <font face='Courier'>src.core"
        "</font> dan <font face='Courier'>src.models</font>, <i>tidak "
        "pernah</i> di dalam fungsi route. Ini menjaga route mudah "
        "di-test."
    ))

    s.append(p("5.4 Penanganan database", "h2"))
    s.append(p(
        "Database tinggal di <font face='Courier'>data/enrollments.db"
        "</font> -- satu file SQLite, tiga tabel."
    ))
    s.append(kv_table([
        ("users",
            "Satu baris per mahasiswa terdaftar. Kolom: user_id (PK), "
            "enrolled_at, updated_at, embedding_dim, model_backend."),
        ("face_references",
            "Satu baris per wajah tersimpan. Kolom: id (PK), user_id (FK), "
            "added_at, embedding (BLOB float32 mentah, 2 KB), face_w, "
            "face_h, face_confidence."),
        ("verifications",
            "Audit log. Kolom: id (PK), ts_utc, user_id, method, "
            "match_score, threshold, matched, references_compared, "
            "best_reference_id, reason, recognizer_backend, "
            "detector_backend, client_ip, request_id."),
    ]))
    s.append(p(
        "Embedding disimpan sebagai <b>BLOB float32 mentah</b>, bukan "
        "array JSON: 2 KB per vector 512-d vs ~6 KB jika pakai JSON. "
        "Untuk ribuan referensi ini berarti; untuk satu user tidak, "
        "tapi pilihan desain yang konsisten membentuk kebiasaan."
    ))

    s.append(p("5.5 Autentikasi", "h2"))
    s.append(p(
        "Setiap protected endpoint mengharapkan header:"
    ))
    s.append(code("Authorization: Bearer <API_KEY>"))
    s.append(p(
        "di mana <font face='Courier'>API_KEY</font> adalah apa pun "
        "yang Anda set di <font face='Courier'>.env</font>. Fungsi "
        "dependency <font face='Courier'>require_api_key</font> "
        "mengekstrak token dan memanggil <font face='Courier'>"
        "hmac.compare_digest(token, API_KEY)</font>. Kita memakai "
        "<font face='Courier'>compare_digest</font> dan bukan "
        "<font face='Courier'>token == API_KEY</font> untuk mencegah "
        "<i>timing attack</i>: perbandingan string biasa berhenti di "
        "byte yang salah pertama, membocorkan posisi byte lewat latency "
        "response. <font face='Courier'>compare_digest</font> "
        "membandingkan semua byte tanpa pandang."
    ))

    s.append(p("5.6 Mengapa gaya backend ini?", "h2"))
    s.append(why("Mengapa satu API_KEY dipakai bersama (bukan OAuth per-user)?",
        "Pemanggil kita adalah plugin Moodle -- server, bukan browser. "
        "Model satu-kunci cocok untuk traffic server-ke-server. OAuth "
        "akan menambah alur token-issuance yang tidak kita butuhkan."))
    s.append(why("Mengapa dependency injection untuk auth (bukan decorator)?",
        "<font face='Courier'>Depends()</font> FastAPI bisa di-test: "
        "Anda bisa override di test dengan stub. Dependency auth juga "
        "berfungsi sebagai dokumentasi -- Swagger UI melihatnya dan "
        "merender tombol Authorize otomatis."))
    s.append(why("Mengapa fail-closed di production?",
        "Jika <font face='Courier'>SECRET_KEY</font> atau "
        "<font face='Courier'>API_KEY</font> hilang di mode production, "
        "app raise saat boot daripada start dengan default lemah. "
        "<font face='Courier'>RuntimeError</font> yang berisik lebih "
        "mudah didiagnosis daripada service production yang diam-diam "
        "tidak aman."))

    # =====================================================================
    # 6. FUNCTION EXPLANATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("6. Penjelasan Fungsi", "chapter"))
    s.append(p(
        "Dari ~3.500 baris Python, berikut adalah selusin fungsi yang "
        "harus Anda pahami jika ingin tahu cara sistem ini benar-benar "
        "bekerja."
    ))

    s.append(p("6.1 create_app() - app.py", "h2"))
    s.append(p("<b>Tujuan:</b> Membangun instance FastAPI dengan semua "
               "sudah dikonfigurasi."))
    s.append(p("<b>Input:</b> Tidak ada.", "h3"))
    s.append(p("<b>Output:</b> Object FastAPI <font face='Courier'>app</font>.", "h3"))
    s.append(p(
        "<b>Logika:</b> Membangun object FastAPI dengan title dan "
        "lifespan handler kita. Menambahkan lima middleware dalam "
        "urutan yang disengaja: rate limiter (terluar agar terhitung "
        "bahkan untuk request invalid), CORS, body size limit, "
        "request-ID, process-time. Memasukkan dua router. Mendaftarkan "
        "exception handler untuk error pydantic dan Starlette "
        "HTTPException. Mengkustom schema OpenAPI untuk menyertakan "
        "Bearer security scheme. Mengembalikan app."
    ))

    s.append(p("6.2 require_api_key(request) - src/api/auth.py", "h2"))
    s.append(p("<b>Tujuan:</b> Dependency FastAPI yang menggerbangkan "
               "setiap protected route."))
    s.append(p("<b>Input:</b> Object FastAPI <font face='Courier'>Request"
               "</font>.", "h3"))
    s.append(p("<b>Output:</b> Tidak ada saat sukses; raise "
               "<font face='Courier'>HTTPException(401)</font> saat gagal.", "h3"))
    s.append(p(
        "<b>Logika:</b> Jika <font face='Courier'>API_KEY_REQUIRED"
        "</font> false (mode dev), langsung return. Selain itu ambil "
        "Bearer token dari <font face='Courier'>Authorization</font> "
        "(atau header fallback <font face='Courier'>X-API-Key</font>). "
        "Bandingkan terhadap <font face='Courier'>API_KEY</font> via "
        "<font face='Courier'>hmac.compare_digest</font>. Jika tidak "
        "cocok, raise 401 dengan body error terstruktur."
    ))

    s.append(p("6.3 verify_face(body, request) - moodle_routes.py", "h2"))
    s.append(p("<b>Tujuan:</b> Membandingkan wajah live terhadap satu "
               "gambar referensi <i>atau</i> terhadap semua referensi yang "
               "sudah didaftarkan untuk user_id."))
    s.append(p("<b>Input:</b> Pydantic <font face='Courier'>VerifyFaceRequest"
               "</font> (current_face base64, plus tepat salah satu dari "
               "reference_face / user_id, plus opsional threshold / "
               "return_embeddings). Plus FastAPI Request (untuk IP, "
               "request-ID, audit logging).", "h3"))
    s.append(p("<b>Output:</b> JSON: <font face='Courier'>{is_match: bool, "
               "match_score: float, confidence: float, details: {...}}"
               "</font>", "h3"))
    s.append(p(
        "<b>Logika:</b> Validasi bahwa tepat satu dari reference_face / "
        "user_id yang di-set. Decode wajah saat ini. Jalankan YOLO; "
        "pilih wajah terbesar di atas confidence 0,7; crop dengan "
        "padding 15%. Hitung embedding via recognizer (yang secara "
        "internal menjalankan alignment + ArcFace). Lalu bercabang:"
    ))
    s.extend(bullets([
        "<b>Mode user_id:</b> ambil semua embedding tersimpan untuk "
        "user itu, hitung cosine similarity terhadap setiap, kembalikan "
        "maksimum plus skor per-referensi diagnostik di "
        "<font face='Courier'>details.all_scores</font>.",
        "<b>Mode reference_face:</b> decode gambar referensi, detect + "
        "crop + embed dengan cara yang sama, kembalikan cosine similarity "
        "tunggal.",
    ]))
    s.append(p(
        "Apa pun cabangnya, tulis satu baris ke audit log dengan skor, "
        "threshold, dan keputusan, lalu kembalikan JSON."
    ))

    s.append(p("6.4 FaceRecognizer.embed_face(crop) - src/models/face_recognizer.py", "h2"))
    s.append(p("<b>Tujuan:</b> Mengubah crop wajah menjadi embedding "
               "L2-normalized 512-d."))
    s.append(p("<b>Input:</b> BGR NumPy array (HxWx3, uint8).", "h3"))
    s.append(p("<b>Output:</b> NumPy array shape <font face='Courier'>(512,)"
               "</font>, L2-normalized.", "h3"))
    s.append(p(
        "<b>Logika:</b> Preprocess crop (alignment via MediaPipe, fallback "
        "ke resize jika alignment gagal). Normalisasi piksel ke [-1, 1]. "
        "Jalankan melalui FaceEmbeddingNet (yang melakukan "
        "<font face='Courier'>F.normalize</font> di akhir). Kembalikan "
        "vector hasilnya. Menaikkan <font face='Courier'>alignment_stats"
        "[aligned]</font> atau <font face='Courier'>alignment_stats"
        "[fallback]</font> untuk observability."
    ))

    s.append(p("6.5 FaceAligner.align(image) - src/models/face_aligner.py", "h2"))
    s.append(p("<b>Tujuan:</b> Memutarkan crop wajah ke template kanonis "
               "InsightFace 112x112."))
    s.append(p("<b>Input:</b> BGR NumPy array yang berisi wajah.", "h3"))
    s.append(p("<b>Output:</b> BGR NumPy array 112x112, atau "
               "<font face='Courier'>None</font> jika landmark tidak "
               "ditemukan.", "h3"))
    s.append(p(
        "<b>Logika:</b> Jalankan MediaPipe FaceLandmarker pada input. "
        "Jika tidak ada wajah ditemukan, return None (recognizer akan "
        "fallback ke resize biasa). Selain itu ekstrak 5 landmark: "
        "titik tengah sudut mata kiri/kanan, ujung hidung, dan sudut "
        "mulut kiri/kanan. Panggil <font face='Courier'>"
        "cv2.estimateAffinePartial2D</font> terhadap template kanonis "
        "untuk dapat matrix rotasi + skala + translasi. Terapkan via "
        "<font face='Courier'>cv2.warpAffine</font>."
    ))

    s.append(p("6.6 _select_diverse_references(candidates, target_count) - "
               "moodle_routes.py", "h2"))
    s.append(p("<b>Tujuan:</b> Dari N kandidat frame yang layak, pilih K "
               "frame terbaik DAN paling beragam untuk guided enrollment."))
    s.append(p("<b>Input:</b> List dict <font face='Courier'>{embedding, "
               "face_box, index}</font>; jumlah target yang akan dipilih.", "h3"))
    s.append(p("<b>Output:</b> Tuple <font face='Courier'>(picked, metrics)</font>.", "h3"))
    s.append(p(
        "<b>Logika:</b> Sort kandidat berdasarkan kualitas (confidence x "
        "sqrt(area)). Pilih yang kualitas tertinggi sebagai jangkar. "
        "Lalu iterasi <i>farthest-point sampling</i>: di setiap langkah, "
        "pilih kandidat yang embedding-nya paling berbeda dari semua "
        "yang sudah dipilih. Ulang sampai target_count atau tidak ada "
        "kandidat tersisa. Hitung metrik diagnostik (ukuran wajah "
        "rata-rata, confidence rata-rata, diversitas pairwise minimum)."
    ))
    s.append(p("Inilah yang memberi guided enrollment perilaku 'tiga "
               "sudut kepala berbeda alih-alih tiga frontal nyaris "
               "identik'."))

    s.append(p("6.7 LivenessAnalyzer.analyze(frames) - src/detectors/liveness.py", "h2"))
    s.append(p("<b>Tujuan:</b> Memutuskan apakah klip pendek menunjukkan "
               "manusia hidup atau foto statis."))
    s.append(p("<b>Input:</b> List BGR NumPy array (3-30 frame).", "h3"))
    s.append(p("<b>Output:</b> JSON dengan <font face='Courier'>is_alive, "
               "total_blinks, head_movement_pixels, ...</font>", "h3"))
    s.append(p(
        "<b>Logika:</b> Untuk setiap frame, jalankan MediaPipe untuk "
        "dapat landmark. Hitung eye aspect ratio (EAR) -- vertikal-"
        "dibagi-horizontal dari mata. Lacak posisi ujung hidung. Hitung "
        "kedipan via hysteresis: EAR turun di bawah 0,20 (tertutup) "
        "lalu naik kembali di atas 0,25 (terbuka) = satu kedipan. "
        "Hitung perpindahan hidung pairwise maksimum di semua frame. "
        "Verdict: hidup jika setidaknya satu kedipan, ATAU kepala "
        "bergerak lebih dari 4 piksel."
    ))

    s.append(p("6.8 FaceEnrollmentStore.enroll(...) - src/services/face_enrollment.py", "h2"))
    s.append(p("<b>Tujuan:</b> Menyimpan embedding referensi baru untuk user_id."))
    s.append(p("<b>Input:</b> user_id, list embedding, list dict metadata "
               "face_box, label model_backend.", "h3"))
    s.append(p("<b>Output:</b> Dict hasil termasuk ID referensi baru dan "
               "jumlah total referensi.", "h3"))
    s.append(p(
        "<b>Logika:</b> Validasi user_id (alphanumeric / _ / -, 1-64 "
        "karakter). Validasi setiap embedding punya shape yang benar. "
        "Cek bahwa menambahkan tidak akan melewati cap per-user (10). "
        "Buka transaksi SQLite. UPSERT baris users. INSERT satu baris "
        "face_references per embedding, mengubah numpy array ke byte "
        "float32 mentah. Commit. Return."
    ))

    s.append(p("6.9 VerificationAuditStore.record(...) - src/services/audit.py", "h2"))
    s.append(p("<b>Tujuan:</b> Menambahkan satu baris ke tabel audit verifications."))
    s.append(p("<b>Input:</b> Semua data per-call (user_id, method, score, "
               "threshold, matched, references_compared, ...).", "h3"))
    s.append(p("<b>Output:</b> ID baris audit baru.", "h3"))
    s.append(p(
        "<b>Logika:</b> Generate ID acak 12 karakter. Buka koneksi "
        "SQLite. INSERT satu baris. Tutup koneksi. Catatan: ini "
        "<i>best-effort</i> -- jika DB sebentar tidak senang, "
        "<font face='Courier'>_record_audit</font> di route mencatat "
        "exception dan return None alih-alih menggagalkan verify user."
    ))

    s.append(p("6.10 _rate_limit_key(request) - app.py", "h2"))
    s.append(p("<b>Tujuan:</b> Memutuskan 'bucket' mana yang dimiliki "
               "request untuk rate limiting."))
    s.append(p("<b>Input:</b> Object FastAPI Request.", "h3"))
    s.append(p("<b>Output:</b> String seperti <font face='Courier'>"
               "'key:abc123'</font> atau <font face='Courier'>"
               "'ip:192.0.2.5'</font>.", "h3"))
    s.append(p(
        "<b>Logika:</b> Jika request punya Bearer token (atau header "
        "X-API-Key), bucket berdasarkan nilai token. Selain itu bucket "
        "berdasarkan IP klien. Ini mencegah satu klien terautentikasi "
        "menghabiskan bucket setiap pemanggil anonim dari NAT yang sama, "
        "dan mencegah satu API key disebar ke banyak IP."
    ))

    s.append(p("6.11 ModelManager._load_detector() - src/core/model_manager.py", "h2"))
    s.append(p("<b>Tujuan:</b> Memilih detektor wajah terbaik yang tersedia "
               "saat boot."))
    s.append(p("<b>Input:</b> Tidak ada (baca path dari "
               "<font face='Courier'>self</font>).", "h3"))
    s.append(p("<b>Output:</b> Tidak ada; men-set "
               "<font face='Courier'>self.face_detector</font> dan "
               "<font face='Courier'>self.detector_backend</font>.", "h3"))
    s.append(p(
        "<b>Logika:</b> Coba YOLO dulu jika file .pt ada. Jika gagal "
        "atau file hilang, coba RetinaFace. Jika <i>itu</i> juga gagal, "
        "fallback ke OpenCV Haar Cascade sehingga service tetap up. "
        "Log label backend yang jelas sehingga <font face='Courier'>"
        "/health</font> bisa memberi tahu operator detektor mana yang "
        "live."
    ))

    s.append(p("6.12 safe_torch_load(path, map_location) - "
               "src/models/_torch_load.py", "h2"))
    s.append(p("<b>Tujuan:</b> Versi <font face='Courier'>torch.load</font> "
               "yang lebih aman yang opt-in ke mode pickle terkunci PyTorch."))
    s.append(p("<b>Input:</b> Path file checkpoint; device.", "h3"))
    s.append(p("<b>Output:</b> Object checkpoint yang ter-deserialize.", "h3"))
    s.append(p(
        "<b>Logika:</b> Coba <font face='Courier'>weights_only=True"
        "</font> dulu -- ini menolak object Python sembarang, jadi file "
        "checkpoint jahat tidak bisa menjalankan kode saat load. Jika "
        "checkpoint berisi metadata non-tensor yang ditolak "
        "<font face='Courier'>weights_only=True</font>, log satu "
        "warning dan fallback ke <font face='Courier'>weights_only=False"
        "</font>. Kedua checkpoint yang kita kirim sukses di bawah "
        "<font face='Courier'>weights_only=True</font>, jadi security "
        "win-nya nyata."
    ))

    # =====================================================================
    # 7. API DOCUMENTATION
    # =====================================================================
    s.append(PageBreak())
    s.append(p("7. Dokumentasi API", "chapter"))
    s.append(p(
        "Setiap protected endpoint mengharapkan:"
    ))
    s.append(code("Authorization: Bearer <API_KEY>"))
    s.append(p("Request yang gagal mengembalikan shape seragam: "
               "<font face='Courier'>{'error': 'pesan yang manusia bisa "
               "baca'}</font>. Request yang sukses memiliki shape spesifik "
               "per endpoint."))

    s.append(p("7.1 Probe kesehatan", "h2"))
    s.append(endpoint_table([
        ("GET", "/", "Banner layanan."),
        ("GET", "/healthz", "Probe liveness. 200 selama proses hidup."),
        ("GET", "/health", "Probe readiness. 200 saat model dimuat, 503 selain itu."),
    ]))

    s.append(p("7.2 API wajah", "h2"))
    s.append(endpoint_table([
        ("POST", "/detect/faces",
            "Mendeteksi wajah di gambar base64. Mengembalikan bounding box."),
        ("POST", "/verify/face",
            "Membandingkan wajah dengan gambar referensi ATAU user_id terdaftar."),
        ("POST", "/detect/behavior",
            "Analisis perilaku per-frame (multi-wajah / gaze / pose kepala)."),
        ("POST", "/detect/liveness",
            "Verdict klip pendek: manusia hidup atau foto statis."),
        ("POST", "/embeddings",
            "Hitung embedding ArcFace 512-d untuk wajah terbesar."),
        ("POST", "/batch/process",
            "Jalankan deteksi atau analisis perilaku pada banyak frame sekaligus."),
    ]))

    s.append(p("7.3 Enrollment", "h2"))
    s.append(endpoint_table([
        ("POST", "/enroll/face",
            "Menambah 1-5 foto referensi untuk user. Maksimum 10 total per user."),
        ("POST", "/enroll/face/guided",
            "Kirim 5-20 frame; server memilih target_count terbaik+varied."),
        ("GET", "/enroll/face/&lt;user_id&gt;",
            "Metadata enrollment. Tidak pernah mengembalikan nilai embedding."),
        ("DELETE", "/enroll/face/&lt;user_id&gt;",
            "Menghapus semua referensi untuk user."),
    ]))

    s.append(p("7.4 Audit", "h2"))
    s.append(endpoint_table([
        ("GET", "/verifications/&lt;user_id&gt;",
            "Verify attempt terbaru untuk user. Hanya score / threshold / "
            "decision / metadata."),
    ]))

    s.append(p("7.5 Sesi (internal)", "h2"))
    s.append(endpoint_table([
        ("POST", "/api/proctoring/session/start", "Memulai sesi."),
        ("POST", "/api/proctoring/session/stop", "Berhenti + menghasilkan laporan."),
        ("GET", "/api/proctoring/session/status", "Status sesi saat ini."),
        ("GET", "/api/proctoring/session/report", "Laporan sesi saat ini (JSON)."),
        ("GET", "/api/proctoring/video/frame", "Frame webcam terbaru (JPEG)."),
        ("GET", "/api/proctoring/video/stream", "MJPEG stream live."),
        ("GET", "/api/proctoring/warnings", "Peringatan sesi terkini."),
        ("GET", "/api/proctoring/system-info", "Info model + alignment + device."),
    ]))

    s.append(p("7.6 Contoh: enrollment + verify", "h2"))
    s.append(code(
        "# Enroll tiga foto referensi\n"
        "B1=$(base64 -w0 foto1.jpg)\n"
        "B2=$(base64 -w0 foto2.jpg)\n"
        "B3=$(base64 -w0 foto3.jpg)\n"
        "\n"
        "curl -X POST http://localhost:5000/enroll/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"user_id\\\": \\\"student_001\\\", \"\\\n"
        "      \"\\\"images\\\": [\\\"$B1\\\", \\\"$B2\\\", \\\"$B3\\\"]}\"\n"
        "\n"
        "# Response (201):\n"
        "# {\n"
        "#   \"user_id\": \"student_001\",\n"
        "#   \"added\": [\"a1b2c3...\", \"d4e5f6...\", \"g7h8i9...\"],\n"
        "#   \"added_count\": 3,\n"
        "#   \"total_references\": 3,\n"
        "#   \"skipped\": [],\n"
        "#   \"model_backend\": \"arcface_efficientnet_b0_emb512\"\n"
        "# }\n"
        "\n"
        "# Saat ujian: verify\n"
        "LIVE=$(base64 -w0 capture_live.jpg)\n"
        "curl -X POST http://localhost:5000/verify/face \\\n"
        "  -H \"Authorization: Bearer $API_KEY\" \\\n"
        "  -H \"Content-Type: application/json\" \\\n"
        "  -d \"{\\\"current_face\\\": \\\"$LIVE\\\", \\\n"
        "       \\\"user_id\\\": \\\"student_001\\\"}\"\n"
        "\n"
        "# Response (200):\n"
        "# {\n"
        "#   \"is_match\": true,\n"
        "#   \"match_score\": 0.6730,\n"
        "#   \"confidence\": 0.6730,\n"
        "#   \"details\": {\n"
        "#     \"method\": \"arcface_max_similarity_over_references\",\n"
        "#     \"threshold_used\": 0.4,\n"
        "#     \"user_id\": \"student_001\",\n"
        "#     \"references_compared\": 3,\n"
        "#     \"best_reference_id\": \"a1b2c3...\",\n"
        "#     \"all_scores\": [0.6730, 0.5121, 0.3575],\n"
        "#     \"embedding_dim\": 512\n"
        "#   }\n"
        "# }"
    ))

    # =====================================================================
    # 8. EXECUTION FLOW
    # =====================================================================
    s.append(PageBreak())
    s.append(p("8. Alur Eksekusi", "chapter"))

    s.append(p("8.1 Apa yang terjadi saat startup", "h2"))
    s.append(p("Dari <font face='Courier'>python app.py</font> sampai "
               "request pertama dilayani, secara berurutan:"))
    s.extend(bullets([
        "<b>1.</b> Python meng-import <font face='Courier'>app.py</font>, "
        "yang lalu meng-import <font face='Courier'>config/settings.py"
        "</font>. Settings membaca <font face='Courier'>.env</font> via "
        "python-dotenv. Jika <font face='Courier'>ENVIRONMENT=production"
        "</font> dan secret yang dibutuhkan hilang, import raise dan "
        "proses keluar.",
        "<b>2.</b> Logging dikonfigurasi: konsol + rotating file handler "
        "di <font face='Courier'>logs/proctoring.log</font>.",
        "<b>3.</b> Object FastAPI app dibuat via "
        "<font face='Courier'>create_app()</font>. Middlewares + router + "
        "exception handler didaftarkan. Belum ada model yang dimuat.",
        "<b>4.</b> Uvicorn bind ke port dan mulai event loop. Async "
        "context manager <font face='Courier'>lifespan</font> berjalan.",
        "<b>5.</b> <font face='Courier'>_init_proctoring_system()</font> "
        "membangun <font face='Courier'>ProctoringSystem</font> nyata "
        "(memuat YOLO, ArcFace, MediaPipe) atau, jika "
        "<font face='Courier'>MOCK_MODELS=1</font>, stub. Hasilnya "
        "dilampirkan ke <font face='Courier'>app.state.system</font>.",
        "<b>6.</b> Enrollment dan audit SQLite store dibuka (membuat "
        "tabel saat pertama run).",
        "<b>7.</b> Model MediaPipe FaceLandmarker di-lazy-load nanti "
        "saat pertama kali <font face='Courier'>/detect/liveness</font> "
        "dipakai.",
        "<b>8.</b> Uvicorn log 'Application startup complete' dan mulai "
        "menerima koneksi.",
    ]))

    s.append(p("8.2 Apa yang terjadi saat user memanggil /verify/face", "h2"))
    s.extend(bullets([
        "Koneksi TCP masuk (via Caddy jika Anda pakai TLS).",
        "Middlewares: body-size, generasi request-ID, mulai timer "
        "process-time, cek bucket rate-limit, CORS preflight jika perlu.",
        "Routing: FastAPI mencocokkan path ke <font face='Courier'>"
        "verify_face</font>.",
        "Dependency: <font face='Courier'>require_api_key</font> "
        "berjalan. Jika token salah, 401 di-raise dan kontrol kembali "
        "ke atas middleware stack, yang tetap men-set X-Request-ID dan "
        "X-Process-Time.",
        "Parsing body: pydantic <font face='Courier'>VerifyFaceRequest"
        "</font> memvalidasi JSON.",
        "Body route: decode base64 -> YOLO -> align -> embed -> SQLite "
        "lookup -> cosine -> verdict -> baris audit ditulis.",
        "Response: JSON body dikembalikan. Middlewares menambah X-Process-"
        "Time, X-Request-ID, header X-RateLimit-*.",
        "Koneksi ditutup (atau tetap terbuka untuk HTTP/2 multiplexing).",
    ]))

    s.append(p("8.3 Apa yang terjadi saat user enroll via /enroll/face/guided", "h2"))
    s.extend(bullets([
        "Auth + validasi body (5-20 frame base64).",
        "Setiap frame di-decode, dijalankan melalui YOLO; frame tanpa "
        "wajah terdeteksi ditambahkan ke <font face='Courier'>skipped"
        "</font>.",
        "Setiap frame yang layak dapat crop wajah dan embedding.",
        "Pemilihan kualitas-lalu-diversitas memilih target_count terbaik "
        "(default 3) frame.",
        "Jika <font face='Courier'>replace_existing=true</font>, "
        "referensi user sebelumnya dihapus terlebih dahulu.",
        "Service enrollment menulis satu baris ke <font face='Courier'>"
        "users</font> (UPSERT) dan target_count baris ke "
        "<font face='Courier'>face_references</font>.",
        "Response menyertakan metrik pemilihan sehingga klien tahu "
        "seberapa beragam frame yang dipilih.",
    ]))

    # =====================================================================
    # 9. ENVIRONMENT & SETUP
    # =====================================================================
    s.append(PageBreak())
    s.append(p("9. Environment & Setup", "chapter"))

    s.append(p("9.1 Environment variables", "h2"))
    s.append(kv_table([
        ("ENVIRONMENT",
            "<font face='Courier'>development</font> atau "
            "<font face='Courier'>production</font>. Production memicu "
            "pengecekan fail-closed pada secret."),
        ("DEBUG",
            "<font face='Courier'>true</font>/<font face='Courier'>false"
            "</font>. Otomatis on di development. Mengontrol auto-reload."),
        ("HOST / PORT",
            "Alamat bind dan port. Default: 0.0.0.0:5000."),
        ("SECRET_KEY",
            "Kunci tanda tangan sesi. Wajib di production. Generate dengan "
            "<font face='Courier'>python -c \"import secrets; "
            "print(secrets.token_urlsafe(48))\"</font>."),
        ("API_KEY",
            "Bearer token. Wajib di production. Metode generate yang sama."),
        ("API_KEY_REQUIRED",
            "Default true saat API_KEY di-set. Set false untuk "
            "menonaktifkan auth (dev only)."),
        ("CORS_ORIGINS",
            "Origin dipisah koma. Default * (memberi warning saat boot di "
            "production)."),
        ("LOG_LEVEL",
            "DEBUG / INFO / WARNING / ERROR. Default tergantung DEBUG."),
        ("MODELS_DIR",
            "Tempat file model. Default <font face='Courier'>"
            "./models_data</font>."),
        ("DATA_DIR",
            "Tempat database SQLite. Default <font face='Courier'>"
            "./data</font>."),
        ("ENROLLMENT_DB_PATH",
            "Override path SQLite secara eksplisit."),
        ("FACE_MATCH_THRESHOLD",
            "Threshold cosine untuk verifikasi. Default 0,4 (tuning untuk "
            "webcam-vs-foto-terdaftar)."),
        ("FACE_DETECTION_CONFIDENCE",
            "Batas confidence detektor. Default 0,5."),
        ("MAX_FACES_ALLOWED",
            "Lebih dari ini memicu warning perilaku. Default 1."),
        ("MOCK_MODELS",
            "Set ke 1 untuk skip pemuatan model nyata (CI memakai ini)."),
    ]))

    s.append(p("9.2 Setup development lokal", "h2"))
    s.append(code(
        "# 1. Clone\n"
        "git clone https://github.com/evankafauzya/capstone-backend.git\n"
        "cd capstone-backend\n"
        "\n"
        "# 2. Taruh file model Anda di models_data/:\n"
        "#    face_detection_yolo.pt\n"
        "#    face_recognition_efficient.pth  (atau face_recognition_model.pth)\n"
        "#    face_landmarker.task\n"
        "#    face_detection_model.pth        (RetinaFace fallback opsional)\n"
        "\n"
        "# 3. Virtual environment Python\n"
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate         # Windows\n"
        "# source venv/bin/activate      # macOS / Linux\n"
        "pip install -r requirements.txt\n"
        "\n"
        "# 4. Environment\n"
        "cp .env.example .env\n"
        "# Edit .env -- set SECRET_KEY dan API_KEY (pakai one-liner secrets)\n"
        "\n"
        "# 5. Jalankan\n"
        "python app.py\n"
        "\n"
        "# 6. Browser -> http://localhost:5000/docs"
    ))

    s.append(p("9.3 Docker (direkomendasikan untuk production)", "h2"))
    s.append(code(
        "# Setup models_data/ + .env yang sama seperti lokal\n"
        "docker compose up -d --build\n"
        "\n"
        "# Health check\n"
        "curl http://localhost:5000/health\n"
        "\n"
        "# Log\n"
        "docker compose logs -f\n"
        "\n"
        "# Stop\n"
        "docker compose down"
    ))

    s.append(p("9.4 Docker + TLS via Caddy", "h2"))
    s.append(code(
        "# Copy dan edit Caddyfile untuk domain Anda\n"
        "cp Caddyfile.example Caddyfile\n"
        "\n"
        "# Mulai dengan overlay TLS\n"
        "docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build\n"
        "\n"
        "# Caddy otomatis ambil sertifikat Let's Encrypt untuk domain Anda.\n"
        "# Browser -> https://proctoring.example.com/docs"
    ))

    s.append(p("9.5 Menjalankan test", "h2"))
    s.append(code(
        "# Semua 22 test (model nyata jika file .pt/.pth ada, selain itu stub)\n"
        "pytest tests/ -v\n"
        "\n"
        "# Force mode mock (cepat, tidak butuh file model)\n"
        "MOCK_MODELS=1 pytest tests/ -v\n"
        "\n"
        "# Lint dengan ruff (nol unused import, tidak ada dead code)\n"
        "python -m ruff check . --exclude venv --exclude __pycache__"
    ))

    s.append(p("9.6 Jebakan umum", "h2"))
    s.append(kv_table([
        ("RuntimeError: SECRET_KEY is required",
            "Set SECRET_KEY dan API_KEY di .env atau env container. "
            "Pengecekan fail-closed disengaja di production."),
        ("/health mengembalikan 503",
            "Salah satu model gagal dimuat. Cek log boot dan konfirmasi "
            "file ada di models_data/."),
        ("Skor verify tampak rendah",
            "Cek /api/proctoring/system-info dan konfirmasi "
            "alignment_enabled bernilai true. Jika false, file "
            "face_landmarker.task hilang -- taruh di models_data/."),
        ("Match tidak pernah mencapai threshold",
            "Enroll ulang dengan foto webcam pada kamera + pencahayaan "
            "yang sama dengan frame live (bukan foto studio). ATAU "
            "turunkan FACE_MATCH_THRESHOLD ke 0,35."),
        ("404 saat verify by user_id",
            "user_id itu belum punya referensi terdaftar. Enroll dulu "
            "via /enroll/face atau /enroll/face/guided."),
        ("Endpoint webcam gagal di Docker",
            "Container tidak melihat webcam host secara default. Pakai "
            "endpoint berbasis gambar base64, atau jalankan di luar "
            "Docker untuk capture live."),
    ]))

    s.append(p("9.7 Anda selesai. Sekarang apa?", "h2"))
    s.append(p(
        "Buka <font face='Courier'>http://localhost:5000/docs</font>. "
        "Klik tombol Authorize hijau, paste API_KEY Anda, dan mulai "
        "memanggil endpoint. Setiap endpoint terdokumentasi dengan "
        "schema request dan contoh response."
    ))
    s.append(p(
        "Lalu baca source code, mulai dengan <font face='Courier'>"
        "app.py</font>. Buka file yang dirujuk oleh import. Dalam "
        "satu jam Anda harus punya model mental yang jelas tentang "
        "bagaimana seluruh sistem berkaitan. Selamat berjuang."
    ))

    return s


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render(filename, story):
    out = DOCS_DIR / filename
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
        title="Moodle Proctoring AI Backend - Beginner Course",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return out


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    en = render("proctoring-beginner-course_EN.pdf", build_english())
    print(f"Generated: {en}  ({en.stat().st_size // 1024} KB)")
    id_ = render("proctoring-beginner-course_ID.pdf", build_indonesian())
    print(f"Generated: {id_} ({id_.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
