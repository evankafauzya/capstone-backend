"""
Generate beginner-friendly PDF documentation for the Moodle Proctoring AI
Backend in English and Bahasa Indonesia.

The tone aims at first-year computer-science students: every technical term
is defined the first time it appears, every step has a "why", and every
abstraction has a concrete example.

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
    Spacer,
    Table,
    TableStyle,
)

DOCS_DIR = Path(__file__).resolve().parent

BRAND = colors.HexColor("#1f4e79")
ACCENT = colors.HexColor("#d35400")
LIGHT = colors.HexColor("#f4f6f8")
TIP_BG = colors.HexColor("#e8f4ff")
TIP_BD = colors.HexColor("#1f77b4")
WARN_BG = colors.HexColor("#fff4e5")
WARN_BD = colors.HexColor("#d35400")
WHY_BG = colors.HexColor("#eef9ee")
WHY_BD = colors.HexColor("#2e7d32")
MONO_BG = colors.HexColor("#1e1e1e")
MONO_FG = colors.HexColor("#f8f8f2")


# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------
def make_styles():
    base = getSampleStyleSheet()
    s = {}
    s["title"] = ParagraphStyle(
        "title", parent=base["Title"], fontSize=26, leading=32,
        textColor=BRAND, spaceAfter=4, alignment=TA_LEFT,
    )
    s["subtitle"] = ParagraphStyle(
        "subtitle", parent=base["Normal"], fontSize=12, leading=16,
        textColor=colors.grey, spaceAfter=22,
    )
    s["h1"] = ParagraphStyle(
        "h1", parent=base["Heading1"], fontSize=18, leading=22,
        textColor=BRAND, spaceBefore=18, spaceAfter=10,
    )
    s["h2"] = ParagraphStyle(
        "h2", parent=base["Heading2"], fontSize=13.5, leading=18,
        textColor=BRAND, spaceBefore=12, spaceAfter=6,
    )
    s["h3"] = ParagraphStyle(
        "h3", parent=base["Heading3"], fontSize=11.5, leading=15,
        textColor=ACCENT, spaceBefore=8, spaceAfter=3,
    )
    s["body"] = ParagraphStyle(
        "body", parent=base["BodyText"], fontSize=10.5, leading=15,
        spaceAfter=6, alignment=TA_LEFT,
    )
    s["bullet"] = ParagraphStyle(
        "bullet", parent=s["body"], leftIndent=14, bulletIndent=2, spaceAfter=3,
    )
    s["mono"] = ParagraphStyle(
        "mono", parent=base["Code"], fontName="Courier", fontSize=8.5,
        leading=11, leftIndent=8, rightIndent=8, textColor=MONO_FG,
        backColor=MONO_BG, borderPadding=8, spaceBefore=4, spaceAfter=10,
    )
    s["intro"] = ParagraphStyle(
        "intro", parent=s["body"], fontSize=11, textColor=colors.HexColor("#555555"),
        spaceAfter=10,
    )
    return s


STYLES = make_styles()


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------
def p(text, style="body"):
    return Paragraph(text, STYLES[style])


def code(text):
    return Preformatted(text, STYLES["mono"])


def bullets(items):
    return [Paragraph(f"• {item}", STYLES["bullet"]) for item in items]


def numbered(items):
    return [Paragraph(f"<b>{i + 1}.</b> {item}", STYLES["bullet"])
            for i, item in enumerate(items)]


def callout(label, body, bg, border):
    """Boxed callout — a single-cell table with a colored background."""
    content = [
        Paragraph(f"<b>{label}</b>", STYLES["body"]),
        Paragraph(body, STYLES["body"]),
    ]
    t = Table([[content]], colWidths=(16 * cm,))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), bg),
        ("LINEBEFORE", (0, 0), (-1, -1), 3, border),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def tip(text):       return callout("Tip",         text, TIP_BG, TIP_BD)
def why(text):       return callout("Why this matters", text, WHY_BG, WHY_BD)
def warn(text):      return callout("Watch out",   text, WARN_BG, WARN_BD)
def analogy(text):   return callout("Analogy",     text, TIP_BG, TIP_BD)
def definition(text):return callout("In plain English", text, LIGHT, BRAND)


def kv_table(rows, col_widths=(4.7 * cm, 11.3 * cm)):
    data = [[Paragraph(f"<b>{k}</b>", STYLES["body"]),
             Paragraph(v, STYLES["body"])] for k, v in rows]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
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
    data = [head] + [[
        Paragraph(m, STYLES["body"]),
        Paragraph(f"<font face='Courier'>{path}</font>", STYLES["body"]),
        Paragraph(desc, STYLES["body"]),
    ] for m, path, desc in rows]
    t = Table(data, colWidths=(2 * cm, 6.5 * cm, 7.5 * cm), repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND),
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
                      f"Moodle Proctoring AI Backend — Page {doc.page}")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, "v2.0.0")
    canvas.restoreState()


# ---------------------------------------------------------------------------
# Shared ASCII diagrams
# ---------------------------------------------------------------------------
ARCHITECTURE = """ +-----------------------------------------------------------+
 |  CLIENT  (Moodle plugin, a browser, curl, Postman, ...)   |
 |  Sends an HTTP request with: Authorization: Bearer <key>  |
 +-----------------------------------------------------------+
                              |
                              v
 +-----------------------------------------------------------+
 |  FLASK APP  (app.py)         <-- "the front door"         |
 |  - Reads .env via config/settings.py                      |
 |  - Enables CORS, error handlers, /docs (Swagger)          |
 +-----------------------------------------------------------+
                              |
                              v
 +-----------------------------------------------------------+
 |  src/api/auth.py             <-- "the security guard"     |
 |  Checks the Bearer token before letting the request in    |
 +-----------------------------------------------------------+
                              |
            +-----------------+-----------------+
            v                                   v
 +----------------------+        +-----------------------------+
 | src/api/moodle_routes.py      | src/api/proctoring_routes.py|
 |   /detect/faces               |   /api/proctoring/...       |
 |   /verify/face                |   session, video, stats     |
 |   /detect/behavior            |                             |
 |   /embeddings                 |                             |
 |   /batch/process              |                             |
 +-------------------------------+-----------------------------+
                              |
                              v
 +-----------------------------------------------------------+
 |  src/core/orchestrator.py    <-- "the project manager"    |
 |  Owns the model_manager, detectors, processors, reports   |
 +-----------------------------------------------------------+
       |              |               |                |
       v              v               v                v
 +-----------+ +--------------+ +-------------+ +---------------+
 | detectors | | processors   | | utils       | | core          |
 | face      | | session_mgr  | | report_gen  | | model_manager |
 | eye       | | webcam_capt  | |             | |               |
 +-----------+ +--------------+ +-------------+ +---------------+
"""

REQUEST_FLOW = """ TIME --->
 [client]   [Flask app]   [auth.py]   [route]      [detector]
    |           |            |          |             |
    |--POST---->|            |          |             |
    |           |--check---->|          |             |
    |           |            |--ok----->|             |
    |           |            |          |--detect---->|
    |           |            |          |<--faces-----|
    |           |<----------------JSON--|             |
    |<----200---|            |          |             |
"""


# ---------------------------------------------------------------------------
# Shared API tables
# ---------------------------------------------------------------------------
PUBLIC_ENDPOINTS = [
    ("GET",  "/health",          "Is the server alive? (no auth needed)"),
    ("GET",  "/docs",            "Open the Swagger UI in your browser"),
    ("GET",  "/openapi.json",    "Machine-readable API description"),
    ("POST", "/detect/faces",    "Detect faces in an image"),
    ("POST", "/verify/face",     "Compare a current face to a reference"),
    ("POST", "/detect/behavior", "Look for suspicious behavior in a frame"),
    ("POST", "/embeddings",      "Turn a face into a list of numbers"),
    ("POST", "/batch/process",   "Send several images in one request"),
]

INTERNAL_ENDPOINTS = [
    ("POST", "/api/proctoring/session/start",        "Start a new exam session"),
    ("POST", "/api/proctoring/session/stop",         "Stop a session and write reports"),
    ("GET",  "/api/proctoring/session/status",       "What is the current session doing?"),
    ("GET",  "/api/proctoring/session/report",       "Get the live session report"),
    ("GET",  "/api/proctoring/video/frame",          "Get the latest frame as JPEG"),
    ("GET",  "/api/proctoring/video/stream",         "Watch the live MJPEG stream"),
    ("GET",  "/api/proctoring/face-detection/stats", "Detector counters and timings"),
    ("GET",  "/api/proctoring/eye-tracking/stats",   "Eye-tracker counters"),
    ("GET",  "/api/proctoring/warnings",             "Latest warnings raised"),
    ("GET",  "/api/proctoring/configuration",        "Safe runtime configuration"),
    ("PUT",  "/api/proctoring/configuration",        "Update a few tunable values"),
]


# ===========================================================================
#                                ENGLISH
# ===========================================================================
def build_english():
    s = []

    s.append(p("Moodle Proctoring AI Backend", "title"))
    s.append(p("A beginner's guide — written for first-year students.",
               "subtitle"))

    s.append(p(
        "This guide assumes you have <b>never</b> built a web backend before. "
        "Every technical word is defined the first time it appears, every "
        "step has a reason, and every abstraction has an example. If "
        "something feels obvious to you, skim past it. If something is "
        "confusing, the glossary at the very end summarizes every term."
    , "intro"))

    s.append(p("What is in this guide", "h2"))
    s.extend(bullets([
        "Chapter 1 — What is this software, and what problem does it solve?",
        "Chapter 2 — A crash course on the words we will keep using.",
        "Chapter 3 — The architecture: how the code is organized.",
        "Chapter 4 — What happens when one request hits the server.",
        "Chapter 5 — Installing the project on your computer.",
        "Chapter 6 — The <font face='Courier'>.env</font> file explained line by line.",
        "Chapter 7 — Running the app the simple way.",
        "Chapter 8 — Deploying with Docker (the recommended way).",
        "Chapter 9 — The API: what each endpoint does, with examples.",
        "Chapter 10 — Using the Swagger UI to test the API in your browser.",
        "Chapter 11 — Security checklist before going live.",
        "Chapter 12 — What to do when something breaks.",
        "Glossary — every technical word from this guide.",
    ]))

    # ---- Chapter 1 ----
    s.append(PageBreak())
    s.append(p("Chapter 1 — What is this software?", "h1"))
    s.append(p(
        "This project is a <b>backend</b> for online exam proctoring. "
        "\"Proctoring\" is the act of supervising an exam to prevent cheating. "
        "When a student takes a quiz on <i>Moodle</i> (a popular online "
        "learning platform), this backend uses the student's webcam to check "
        "that they are alone, looking at the screen, and that they are the "
        "person who logged in."
    ))
    s.append(definition(
        "A <b>backend</b> is a program that runs on a server and does work "
        "behind the scenes — it never shows pretty buttons or windows. "
        "Other programs talk to it over the internet by sending small "
        "messages, and it sends small messages back. The visible part the "
        "student sees (the Moodle page) is called the <b>frontend</b>."
    ))
    s.append(p("What the backend does, in one paragraph", "h2"))
    s.append(p(
        "Moodle sends an image (a snapshot of the student's webcam) to this "
        "backend. The backend looks at the image with AI models, decides "
        "whether anything looks suspicious (no face, multiple people, looking "
        "away, not the same person who registered) and sends a structured "
        "answer back. Moodle uses that answer to record warnings during the "
        "exam."
    ))
    s.append(p("What is included", "h2"))
    s.extend(bullets([
        "An <b>HTTP API</b> — endpoints that other programs can call.",
        "An <b>interactive playground</b> (Swagger UI) so you can try the "
        "API in your browser.",
        "Strong <b>authentication</b> — only callers who present a secret "
        "token are allowed in.",
        "A <b>Dockerfile</b> — a recipe to package everything into a "
        "container you can deploy anywhere.",
        "A complete <b>configuration</b> system based on a single "
        "<font face='Courier'>.env</font> file.",
    ]))

    # ---- Chapter 2 — crash course ----
    s.append(PageBreak())
    s.append(p("Chapter 2 — Words we will use", "h1"))
    s.append(p("Before going further, here is a short crash course on the "
               "vocabulary. Read it once now and refer back as needed."))

    s.append(p("Servers and clients", "h2"))
    s.append(p(
        "A <b>server</b> is a computer running a program that waits for "
        "requests. A <b>client</b> is anything that sends a request — your "
        "browser, a mobile app, Moodle, or a tool like <i>curl</i>. The "
        "server listens, processes the request, and sends a response."
    ))
    s.append(analogy(
        "Think of a restaurant. The kitchen is the server. The waiter "
        "carrying your order back and forth is HTTP. You, sitting at the "
        "table, are the client. You don't go into the kitchen — you just "
        "send your order in (the request) and get a plate back (the "
        "response)."
    ))

    s.append(p("HTTP, methods, status codes", "h2"))
    s.append(p(
        "Every interaction over the web uses <b>HTTP</b>, the protocol that "
        "says how requests and responses are formatted. The two parts you "
        "will see the most are:"
    ))
    s.extend(bullets([
        "<b>Method</b>: <font face='Courier'>GET</font> means \"give me "
        "something\", <font face='Courier'>POST</font> means \"here is "
        "data, do something with it\", <font face='Courier'>PUT</font> "
        "means \"update\", <font face='Courier'>DELETE</font> means "
        "\"remove\".",
        "<b>Status code</b>: a number telling you what happened. "
        "<font face='Courier'>200</font> = OK, <font face='Courier'>400</font> = "
        "your request was malformed, <font face='Courier'>401</font> = "
        "you are not authenticated, <font face='Courier'>404</font> = "
        "not found, <font face='Courier'>500</font> = the server crashed.",
    ]))

    s.append(p("JSON", "h2"))
    s.append(p(
        "<b>JSON</b> is the most common way to send structured data over "
        "HTTP. It looks like this:"
    ))
    s.append(code(
        '{\n  "face_count": 1,\n  "faces": [{"x": 100, "y": 50, "w": 200, "h": 200}],\n'
        '  "processing_time_ms": 42.5\n}'
    ))
    s.append(p("Keys are strings; values can be strings, numbers, lists, "
               "booleans, <font face='Courier'>null</font>, or other JSON "
               "objects."))

    s.append(p("API and endpoint", "h2"))
    s.append(p(
        "An <b>API</b> (Application Programming Interface) is the menu of "
        "things a server knows how to do. Each item on that menu is called "
        "an <b>endpoint</b> — a specific URL plus a method (for example "
        "<font face='Courier'>POST /detect/faces</font>)."
    ))

    s.append(p("Authentication and tokens", "h2"))
    s.append(p(
        "<b>Authentication</b> answers the question \"who is calling?\". "
        "The simplest scheme is a <b>token</b> — a long random string that "
        "the server hands out, and that the client must send on every "
        "request. We use the <b>Bearer</b> style:"
    ))
    s.append(code("Authorization: Bearer ABC123XYZ..."))
    s.append(analogy(
        "An API token is like a hotel key card. The hotel issues it to you. "
        "Whenever you want to enter your room, you have to show the card. "
        "Anyone holding the card can enter — so do not share it, do not "
        "post it online, do not commit it to git."
    ))

    s.append(p("Environment variables and .env", "h2"))
    s.append(p(
        "An <b>environment variable</b> is a setting that lives outside "
        "your code, in the operating system's memory. The same code can "
        "behave differently on different machines just by changing these "
        "values. A <font face='Courier'>.env</font> file is a plain text "
        "file that lists them, one per line:"
    ))
    s.append(code("API_KEY=ABC123XYZ\nDEBUG=false"))

    s.append(p("Docker, image, container", "h2"))
    s.append(p(
        "<b>Docker</b> packages a program plus everything it needs (Python "
        "version, libraries, system tools) into a single bundle. The "
        "recipe is the <b>Dockerfile</b>. Building the recipe produces an "
        "<b>image</b>. Running the image gives you a <b>container</b> — a "
        "small isolated computer-inside-your-computer. The same image runs "
        "the same way on your laptop, on a cloud VM, or in your school's "
        "server room."
    ))
    s.append(why(
        "Without Docker, you would have to repeat the install steps on "
        "every machine and hope no version conflicts pop up. With Docker, "
        "one command — <font face='Courier'>docker compose up -d --build</font> "
        "— rebuilds the whole environment from scratch."
    ))

    # ---- Chapter 3 — architecture ----
    s.append(PageBreak())
    s.append(p("Chapter 3 — How the code is organized", "h1"))
    s.append(p(
        "The project is split into layers, like floors of a building. A "
        "request enters at the top floor (Flask), travels down through "
        "security (auth), arrives at a specific room (a route handler), "
        "and that room calls specialists (detectors, processors) to do the "
        "actual work."
    ))
    s.append(code(ARCHITECTURE))

    s.append(p("Folder map — what every file does", "h3"))
    s.append(kv_table([
        ("app.py", "The \"front door\". Creates the Flask application, "
                   "registers all routes, wires up CORS and Swagger UI."),
        ("wsgi.py", "A one-line entrypoint used by Gunicorn in production. "
                    "You will not edit it often."),
        ("config/settings.py", "Reads the .env file. If you are in "
                               "production and a secret is missing, this file "
                               "refuses to let the app start. Fail loudly."),
        ("src/api/auth.py", "Contains the @require_api_key decorator. "
                            "Every protected endpoint sits behind it."),
        ("src/api/moodle_routes.py", "The endpoints Moodle calls "
                                     "(/detect/faces, /verify/face, ...)."),
        ("src/api/proctoring_routes.py", "The endpoints you call to start, "
                                          "stop, and inspect sessions."),
        ("src/core/orchestrator.py", "The brain. Knows how to talk to "
                                     "every detector and processor."),
        ("src/core/model_manager.py", "Loads .pth/.pkl model files. If a "
                                       "file is missing or broken, falls back "
                                       "to OpenCV automatically."),
        ("src/detectors/", "face_detector.py finds faces. eye_tracker.py "
                           "follows the eyes."),
        ("src/processors/", "session_manager.py keeps track of a single "
                            "exam session. webcam_capture.py reads from a "
                            "physical camera."),
        ("src/utils/report_generator.py", "Writes the final JSON / TXT / "
                                          "PDF reports for a session."),
        ("Dockerfile + docker-compose.yml", "The recipe + the one-command "
                                            "way to run it as a container."),
        (".env.example", "Template you copy to .env and fill in."),
    ]))

    # ---- Chapter 4 — flow ----
    s.append(PageBreak())
    s.append(p("Chapter 4 — One request, step by step", "h1"))
    s.append(p(
        "Let's follow a single request through the system. Imagine Moodle "
        "sends a base64-encoded image to "
        "<font face='Courier'>POST /detect/faces</font>:"))
    s.append(code(REQUEST_FLOW))

    s.append(p("The steps in plain English", "h3"))
    s.extend(numbered([
        "<b>The HTTP request arrives.</b> Flask checks that the body is no "
        "bigger than 50 MB (we set this limit because images can be huge).",
        "<b>Auth check.</b> The decorator "
        "<font face='Courier'>require_api_key</font> reads the "
        "<font face='Courier'>Authorization</font> header. If the token is "
        "missing or wrong, the server immediately answers 401 and stops.",
        "<b>JSON parsing.</b> Flask reads the JSON body, finds the "
        "<font face='Courier'>image</font> field, and hands it to the route.",
        "<b>Base64 decoding.</b> The route turns the string back into raw "
        "image bytes, then into an OpenCV image (a grid of pixel values).",
        "<b>Detection.</b> The orchestrator calls the face detector. If the "
        "deep-learning model failed to load earlier, the system "
        "transparently uses OpenCV's Haar Cascade. Either way, the route "
        "gets a list of face boxes.",
        "<b>Optional landmarks.</b> If the request asked for landmarks, the "
        "eye tracker also runs and returns eye coordinates.",
        "<b>Build the JSON response.</b> The route assembles a dictionary "
        "with face boxes, count, and processing time, and Flask sends it "
        "back with status 200.",
    ]))

    s.append(p("How a full session looks", "h3"))
    s.extend(bullets([
        "<b>1.</b> The client calls <font face='Courier'>POST /api/proctoring/session/start</font> "
        "with a session ID and a user ID.",
        "<b>2.</b> The orchestrator creates a session object. From now on it "
        "remembers every frame, every warning, and every timing.",
        "<b>3.</b> The client (or the local webcam) feeds frames in.",
        "<b>4.</b> Each frame is checked. If something is off, a warning is "
        "added to the session's log.",
        "<b>5.</b> The client calls <font face='Courier'>POST /api/proctoring/session/stop</font>. "
        "The report generator writes "
        "<font face='Courier'>reports/&lt;id&gt;.json</font>, "
        "<font face='Courier'>.txt</font>, and "
        "<font face='Courier'>.pdf</font>.",
    ]))

    # ---- Chapter 5 — install ----
    s.append(PageBreak())
    s.append(p("Chapter 5 — Installing the project", "h1"))
    s.append(p("You have two choices. If you are evaluating the code or "
               "developing locally, follow the \"plain Python\" path. If "
               "you are deploying, skip to Chapter 8 (Docker)."))

    s.append(p("Plain-Python path", "h2"))
    s.append(p("Step 1 — open a terminal and clone the repository:", "h3"))
    s.append(code("git clone https://github.com/evankafauzya/capstone-backend.git\ncd capstone-backend"))

    s.append(p("Step 2 — create a virtual environment.", "h3"))
    s.append(p(
        "A virtual environment is a private folder where Python installs "
        "this project's libraries without touching the rest of your "
        "computer. If you ever delete the project, you delete the "
        "virtualenv with it — nothing else breaks."
    ))
    s.append(code(
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate          # Windows (PowerShell or CMD)\n"
        "# source venv/bin/activate        # macOS / Linux"
    ))
    s.append(tip(
        "If your prompt now starts with <font face='Courier'>(venv)</font>, "
        "you are inside the virtual environment. Anything you "
        "<font face='Courier'>pip install</font> from now on lives in "
        "this folder only."
    ))

    s.append(p("Step 3 — install the dependencies:", "h3"))
    s.append(code("pip install -r requirements.txt"))
    s.append(p(
        "This downloads Flask, OpenCV, PyTorch, etc. The first time it "
        "runs it may take several minutes — PyTorch alone is hundreds of "
        "megabytes."))

    s.append(p("Step 4 — create your .env file.", "h3"))
    s.append(code("cp .env.example .env   # macOS / Linux\ncopy .env.example .env # Windows"))

    s.append(p("Step 5 — generate two strong secrets and paste them into .env:", "h3"))
    s.append(code('python -c "import secrets; print(secrets.token_urlsafe(48))"'))
    s.append(p("Run that twice. Put the first output as "
               "<font face='Courier'>SECRET_KEY</font> and the second as "
               "<font face='Courier'>API_KEY</font>."))

    s.append(warn(
        "Do <b>not</b> share your <font face='Courier'>.env</font> file. "
        "Do <b>not</b> commit it to git. The example file is safe to "
        "commit because it has blank values; the real file has your "
        "secrets in it."
    ))

    # ---- Chapter 6 — .env line by line ----
    s.append(PageBreak())
    s.append(p("Chapter 6 — The .env file, line by line", "h1"))
    s.append(kv_table([
        ("ENVIRONMENT", "<font face='Courier'>development</font> or "
                        "<font face='Courier'>production</font>. In "
                        "production, missing secrets crash the app on boot "
                        "(this is intentional)."),
        ("DEBUG", "<font face='Courier'>true</font> shows full error pages "
                  "with stack traces. Useful while learning, dangerous in "
                  "production. Default is true in development, false in "
                  "production."),
        ("HOST", "Which network interface the server listens on. "
                 "<font face='Courier'>0.0.0.0</font> means \"all "
                 "interfaces\". Leave it as 0.0.0.0 unless you know why."),
        ("PORT", "Which TCP port to listen on. Default 5000. If the port is "
                 "already taken, the app will fail to start."),
        ("LOG_LEVEL", "How chatty the logs are. Set to "
                      "<font face='Courier'>DEBUG</font> while learning, "
                      "<font face='Courier'>INFO</font> in production."),
        ("SECRET_KEY", "Used by Flask to sign session cookies. Required in "
                       "production. Should be a long random string."),
        ("API_KEY", "The bearer token you give to clients. Anyone with this "
                    "value can call the API. Required in production."),
        ("API_KEY_REQUIRED", "If set to <font face='Courier'>false</font>, "
                             "the auth check is skipped. Only ever use this "
                             "on your own machine."),
        ("CORS_ORIGINS", "Which web origins can call the API. "
                         "<font face='Courier'>*</font> means \"anyone\". In "
                         "production, set it to your Moodle URL (e.g. "
                         "<font face='Courier'>https://moodle.yourschool.edu</font>)."),
        ("CAPTURE_INTERVAL", "How often the webcam is read, in seconds."),
        ("REVERIFICATION_INTERVAL", "How often we re-check that the student "
                                    "is the same person, in seconds."),
        ("SESSION_TIMEOUT", "Maximum session length in seconds."),
        ("FACE_DETECTION_CONFIDENCE", "Minimum score (0–1) for the detector "
                                      "to keep a face. Lower = more faces "
                                      "but more false positives."),
        ("FACE_MATCH_THRESHOLD", "Minimum similarity score for two faces to "
                                 "be considered the same person."),
        ("MAX_FACES_ALLOWED", "If more faces than this are seen, a warning "
                              "is raised."),
    ]))

    # ---- Chapter 7 — run ----
    s.append(PageBreak())
    s.append(p("Chapter 7 — Running the app (the simple way)", "h1"))
    s.append(p("With the virtual environment active and .env filled in:"))
    s.append(code("python app.py"))
    s.append(p("You should see lines like:"))
    s.append(code(
        "Proctoring system initialized successfully\n"
        "Moodle Proctoring AI Backend v2.0.0 ready (env=development, debug=True)\n"
        " * Running on http://0.0.0.0:5000"
    ))
    s.append(p("Now open the URLs:"))
    s.extend(bullets([
        "<font face='Courier'>http://localhost:5000/health</font> — should "
        "return a JSON object that says <font face='Courier'>\"status\": "
        "\"healthy\"</font>.",
        "<font face='Courier'>http://localhost:5000/docs</font> — the "
        "Swagger UI. You can click on each endpoint and try it.",
        "<font face='Courier'>http://localhost:5000/openapi.json</font> — "
        "the machine-readable spec, useful if you build a client.",
    ]))

    s.append(p("Stop the app at any time with <b>Ctrl+C</b> in the terminal."))

    # ---- Chapter 8 — Docker ----
    s.append(PageBreak())
    s.append(p("Chapter 8 — Deploying with Docker", "h1"))
    s.append(p(
        "Docker is how you ship this backend to a real server (or to a "
        "classmate's machine) without worrying about Python versions or "
        "missing system libraries."
    ))
    s.append(p("What you get out of the box", "h2"))
    s.extend(bullets([
        "<font face='Courier'>Dockerfile</font> — the recipe. Starts from "
        "<font face='Courier'>python:3.11-slim</font>, installs the "
        "OpenCV system libraries, copies your code, installs Python "
        "packages, then runs Gunicorn.",
        "<font face='Courier'>docker-compose.yml</font> — a higher-level "
        "file that says \"build this image, run it, expose port 5000, "
        "mount these folders\".",
        "<font face='Courier'>.dockerignore</font> — keeps secrets, the "
        "venv, and big files out of the build.",
    ]))

    s.append(p("Three commands you actually need", "h2"))
    s.append(code(
        "# 1. Make sure .env is filled (ENVIRONMENT=production, SECRET_KEY=..., API_KEY=...)\n"
        "# 2. Build the image and start the container in the background:\n"
        "docker compose up -d --build\n\n"
        "# 3. Check it is healthy:\n"
        "curl http://localhost:5000/health"
    ))
    s.append(p("Other handy commands:"))
    s.append(code(
        "docker compose logs -f         # live logs (Ctrl+C to detach)\n"
        "docker compose ps              # container status\n"
        "docker compose down            # stop and remove container\n"
        "docker compose restart         # restart without rebuilding"
    ))

    s.append(p("What the compose file mounts and why", "h2"))
    s.append(kv_table([
        ("./models_data → /app/models_data",
         "Read-only. Drop your .pth / .pkl model files here; the container "
         "sees them without a rebuild."),
        ("./reports → /app/reports",
         "Reports written by a session are saved here, even after the "
         "container is destroyed."),
        ("./logs → /app/logs",
         "Application logs survive container restarts."),
    ]))
    s.append(why(
        "Without these <b>volumes</b>, when you stop the container, "
        "everything inside it disappears. The volume tells Docker \"keep "
        "this folder on the host disk, not in the throwaway container "
        "layer\"."
    ))

    s.append(p("Production tuning", "h2"))
    s.append(p(
        "Inside the Dockerfile, Gunicorn runs with workers and threads "
        "controlled by environment variables. Add these to "
        "<font face='Courier'>.env</font> as needed:"))
    s.append(code(
        "GUNICORN_WORKERS=4    # parallel processes (CPU-bound work)\n"
        "GUNICORN_THREADS=8    # threads per worker (I/O-bound work)\n"
        "GUNICORN_TIMEOUT=180  # seconds before a slow request is killed"
    ))
    s.append(tip(
        "A common starting point on a small VM is workers=2 and threads=4. "
        "Increase workers if the CPU is idle. Increase threads if many "
        "requests are waiting on the network."
    ))

    # ---- Chapter 9 — API ----
    s.append(PageBreak())
    s.append(p("Chapter 9 — The API endpoints", "h1"))
    s.append(p(
        "Every endpoint that does real work expects a Bearer token. Send "
        "it like this:"))
    s.append(code("Authorization: Bearer <your API_KEY>"))
    s.append(p("The server also accepts the alternative header:"))
    s.append(code("X-API-Key: <your API_KEY>"))

    s.append(p("Public endpoints (the ones Moodle calls)", "h2"))
    s.append(endpoint_table(PUBLIC_ENDPOINTS))

    s.append(p("Internal endpoints (session lifecycle)", "h2"))
    s.append(p("All paths below are under "
               "<font face='Courier'>/api/proctoring</font>."))
    s.append(endpoint_table(INTERNAL_ENDPOINTS))

    s.append(p("A full example: detect faces in an image", "h2"))
    s.append(p("Request:"))
    s.append(code(
        'curl -X POST http://localhost:5000/detect/faces \\\n'
        '  -H "Authorization: Bearer $API_KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"image": "data:image/jpeg;base64,/9j/4AAQ..."}\''
    ))
    s.append(p("Response (status 200):"))
    s.append(code(
        '{\n'
        '  "faces": [\n'
        '    {"x": 120, "y": 80, "w": 180, "h": 180, "confidence": 0.91}\n'
        '  ],\n'
        '  "face_count": 1,\n'
        '  "landmarks": {"left_eye": [165, 130], "right_eye": [235, 130]},\n'
        '  "processing_time_ms": 47.3\n'
        '}'
    ))

    s.append(p("Common error responses", "h3"))
    s.append(kv_table([
        ("400 Bad Request",   "Your request body is missing a required field or has invalid base64."),
        ("401 Unauthorized",  "Missing or wrong API token."),
        ("404 Not Found",     "Wrong URL — check the spelling."),
        ("405 Method Not Allowed", "You used GET on a POST endpoint or vice versa."),
        ("500 Internal Server Error", "The server crashed. Check the logs."),
    ]))

    # ---- Chapter 10 — Swagger ----
    s.append(PageBreak())
    s.append(p("Chapter 10 — Using the Swagger UI", "h1"))
    s.append(p(
        "Swagger UI is a website built into the backend that lists every "
        "endpoint and lets you call it from your browser without writing "
        "any code. It is the fastest way to learn the API."
    ))
    s.append(p("Walk-through", "h2"))
    s.extend(numbered([
        "Open <font face='Courier'>http://localhost:5000/docs</font> in your browser.",
        "Click the green <b>Authorize</b> button at the top right.",
        "Paste the value of <font face='Courier'>API_KEY</font> from your "
        ".env into the dialog. Click <b>Authorize</b>, then <b>Close</b>.",
        "Scroll down and expand any endpoint, for example "
        "<font face='Courier'>POST /detect/faces</font>.",
        "Click <b>Try it out</b>. A text area appears with an example "
        "request body. Edit it if you like.",
        "Click <b>Execute</b>. The UI prints the response, the status "
        "code, and the exact <font face='Courier'>curl</font> command you "
        "could run to reproduce it from the terminal.",
    ]))
    s.append(tip(
        "If the <b>Authorize</b> button does not appear, your browser is "
        "showing a cached copy. Press Ctrl+Shift+R to hard-reload."
    ))

    # ---- Chapter 11 — security ----
    s.append(PageBreak())
    s.append(p("Chapter 11 — Security checklist before going live", "h1"))
    s.append(p("Go through this list before you put the server on the public internet."))
    s.extend(bullets([
        "<font face='Courier'>ENVIRONMENT=production</font> is set in .env.",
        "<font face='Courier'>SECRET_KEY</font> and "
        "<font face='Courier'>API_KEY</font> are both long random strings "
        "(at least 32 characters). Never reuse the values from the example.",
        ".env is not committed to git (it is already in .gitignore).",
        "<font face='Courier'>DEBUG=false</font>. Otherwise stack traces "
        "leak through error pages.",
        "<font face='Courier'>CORS_ORIGINS</font> lists only your Moodle "
        "origin(s), never <font face='Courier'>*</font>.",
        "A reverse proxy (Nginx, Caddy, or a cloud load balancer) sits in "
        "front of the container and terminates TLS so traffic is HTTPS.",
        "<font face='Courier'>models_data/</font>, "
        "<font face='Courier'>reports/</font> and "
        "<font face='Courier'>logs/</font> are mounted to durable storage.",
        "If you rotate the API key, update every Moodle plugin and every "
        "client at the same time.",
    ]))
    s.append(why(
        "Bearer tokens are powerful — anyone holding the token can call "
        "the API. That is why we never log them, never expose them via "
        "<font face='Courier'>/configuration</font>, and compare them with "
        "<font face='Courier'>hmac.compare_digest</font> (a timing-safe "
        "comparison that does not leak information even to a "
        "millisecond-accurate attacker)."
    ))

    # ---- Chapter 12 — troubleshooting ----
    s.append(PageBreak())
    s.append(p("Chapter 12 — When things break", "h1"))
    s.append(kv_table([
        ("App refuses to start with \"SECRET_KEY is required\"",
         "You set ENVIRONMENT=production but left SECRET_KEY blank. Set it "
         "or temporarily switch to ENVIRONMENT=development."),
        ("App refuses to start with \"API_KEY is required\"",
         "Same as above for API_KEY."),
        ("Every request returns 401",
         "Either the header is misspelled (must be exactly "
         "<font face='Courier'>Authorization: Bearer ...</font>) or the "
         "token does not match API_KEY in .env. Tokens are case-sensitive."),
        ("Swagger UI is blank or shows old endpoints",
         "Hard-reload (Ctrl+Shift+R). If still blank, visit "
         "<font face='Courier'>/openapi.json</font> directly — it should "
         "return JSON."),
        ("Detection always returns 0 faces",
         "Make sure the image is well-lit and contains a face. Check the "
         "logs for \"Falling back to OpenCV Cascade\" — that means the "
         ".pth model failed to load, but detection still works."),
        ("Webcam endpoints fail inside Docker",
         "Containers cannot see the host webcam by default. Use the "
         "base64-image endpoints from a client that has webcam access, "
         "or run the app outside Docker."),
        ("Port 5000 already in use",
         "Change PORT in .env, or stop whichever program is on 5000 "
         "(macOS AirPlay uses it, for example)."),
        ("\"docker: command not found\"",
         "Install Docker Desktop (Windows / macOS) or docker-ce (Linux)."),
    ]))

    # ---- Glossary ----
    s.append(PageBreak())
    s.append(p("Glossary", "h1"))
    s.append(kv_table([
        ("API",           "A menu of things a server can do for its clients."),
        ("Backend",       "Code that runs on a server, away from the user's eyes."),
        ("Base64",        "A way to turn bytes (like an image) into a long ASCII string so they can travel in a JSON field."),
        ("Bearer token",  "A secret string a client sends to prove who it is."),
        ("Client",        "Anything that calls the server (browser, app, Moodle, curl)."),
        ("Container",     "A running instance of a Docker image. Isolated from the host."),
        ("CORS",          "A web rule that controls which other websites are allowed to call your API."),
        ("Docker",        "A tool that packages a program plus its dependencies into a portable image."),
        ("Endpoint",      "A specific URL + HTTP method the server understands."),
        ("Environment variable", "A setting kept in the OS, not in the code. Read at startup."),
        ("Flask",         "A Python web framework. Handles routing and HTTP details for us."),
        ("Frontend",      "The visible part of an application (web page, app screen)."),
        ("Gunicorn",      "A production-grade web server that runs Flask apps reliably."),
        ("Header",        "Extra metadata sent alongside an HTTP request or response."),
        ("HTTP",          "The protocol that browsers and APIs speak."),
        ("HTTPS",         "HTTP secured with TLS encryption."),
        ("JSON",          "A simple text format for structured data."),
        ("OpenAPI",       "A standard, machine-readable description of an API."),
        ("Proctoring",    "Supervising an exam to detect cheating."),
        ("Request",       "A message a client sends to a server."),
        ("Response",      "The message the server sends back."),
        ("REST",          "A style of designing HTTP APIs around resources and methods."),
        ("Reverse proxy", "A server that sits in front of your app, handles TLS, and forwards requests."),
        ("Route",         "Code that handles a specific endpoint."),
        ("Server",        "A computer (or program) that waits for and answers requests."),
        ("Status code",   "A number the server returns to say what happened (200, 401, 500, ...)."),
        ("Swagger UI",    "An interactive web page that documents and tests an API."),
        ("Volume",        "A folder on the host computer that a Docker container can read/write."),
        ("WSGI",          "The Python standard for connecting web apps to web servers (Gunicorn talks WSGI)."),
    ]))

    return s


# ===========================================================================
#                          BAHASA INDONESIA
# ===========================================================================
def build_indonesian():
    s = []

    s.append(p("Moodle Proctoring AI Backend", "title"))
    s.append(p("Panduan pemula — ditulis untuk mahasiswa tahun pertama.",
               "subtitle"))

    s.append(p(
        "Panduan ini berasumsi Anda <b>belum pernah</b> membangun backend web. "
        "Setiap istilah teknis dijelaskan saat pertama kali muncul, setiap "
        "langkah memiliki alasan, dan setiap konsep abstrak punya contoh "
        "nyata. Bila ada bagian yang sudah Anda pahami, lewati saja. Bila "
        "ada yang membingungkan, lihat glosarium di akhir buku."
    , "intro"))

    s.append(p("Isi panduan ini", "h2"))
    s.extend(bullets([
        "Bab 1 — Apa software ini dan masalah apa yang dipecahkannya?",
        "Bab 2 — Kursus singkat istilah yang akan sering dipakai.",
        "Bab 3 — Arsitektur: bagaimana kode diorganisasi.",
        "Bab 4 — Apa yang terjadi saat satu request masuk ke server.",
        "Bab 5 — Memasang proyek di komputer Anda.",
        "Bab 6 — File <font face='Courier'>.env</font> dijelaskan baris per baris.",
        "Bab 7 — Menjalankan aplikasi dengan cara paling sederhana.",
        "Bab 8 — Deployment dengan Docker (cara yang disarankan).",
        "Bab 9 — API: apa fungsi tiap endpoint, lengkap dengan contoh.",
        "Bab 10 — Menggunakan Swagger UI untuk menguji API di browser.",
        "Bab 11 — Checklist keamanan sebelum go-live.",
        "Bab 12 — Apa yang harus dilakukan saat ada masalah.",
        "Glosarium — semua istilah teknis dari panduan ini.",
    ]))

    # ---- Bab 1 ----
    s.append(PageBreak())
    s.append(p("Bab 1 — Apa software ini?", "h1"))
    s.append(p(
        "Proyek ini adalah <b>backend</b> untuk proctoring ujian online. "
        "\"Proctoring\" artinya kegiatan mengawasi ujian agar tidak ada "
        "kecurangan. Saat mahasiswa mengerjakan kuis di <i>Moodle</i> "
        "(platform pembelajaran online yang populer), backend ini "
        "menggunakan webcam mahasiswa untuk memastikan ia sendirian, "
        "menghadap layar, dan benar-benar orang yang login."
    ))
    s.append(definition(
        "<b>Backend</b> adalah program yang berjalan di server dan "
        "bekerja di balik layar — tidak menampilkan tombol atau jendela. "
        "Program lain berkomunikasi dengannya lewat internet dengan "
        "mengirim pesan kecil, dan ia membalas dengan pesan kecil pula. "
        "Bagian yang dilihat mahasiswa (halaman Moodle) disebut "
        "<b>frontend</b>."
    ))
    s.append(p("Apa yang dikerjakan backend, dalam satu paragraf", "h2"))
    s.append(p(
        "Moodle mengirim gambar (foto webcam mahasiswa) ke backend ini. "
        "Backend memeriksa gambar dengan model AI, memutuskan apakah ada "
        "yang mencurigakan (tidak ada wajah, beberapa orang, melihat ke "
        "samping, bukan orang yang sama saat registrasi), lalu mengirim "
        "jawaban terstruktur balik. Moodle memakai jawaban itu untuk "
        "mencatat peringatan selama ujian."
    ))
    s.append(p("Apa saja yang sudah disiapkan", "h2"))
    s.extend(bullets([
        "Sebuah <b>HTTP API</b> — endpoint yang dapat dipanggil program lain.",
        "<b>Playground interaktif</b> (Swagger UI) supaya Anda dapat mencoba "
        "API langsung di browser.",
        "<b>Autentikasi</b> yang kuat — hanya pemanggil yang membawa token "
        "rahasia yang diperbolehkan masuk.",
        "Sebuah <b>Dockerfile</b> — resep untuk mengemas semuanya menjadi "
        "container yang bisa dideploy di mana pun.",
        "Sistem <b>konfigurasi</b> lengkap berbasis satu file "
        "<font face='Courier'>.env</font>.",
    ]))

    # ---- Bab 2 ----
    s.append(PageBreak())
    s.append(p("Bab 2 — Istilah yang akan kita pakai", "h1"))
    s.append(p("Sebelum melangkah lebih jauh, berikut kursus singkat kosa "
               "kata. Baca sekali sekarang, kembali lagi kapan pun perlu."))

    s.append(p("Server dan client", "h2"))
    s.append(p(
        "<b>Server</b> adalah komputer yang menjalankan program yang "
        "menunggu request. <b>Client</b> adalah apa pun yang mengirim "
        "request — browser Anda, aplikasi mobile, Moodle, atau alat "
        "seperti <i>curl</i>. Server mendengarkan, memproses request, "
        "lalu mengirim respon."
    ))
    s.append(analogy(
        "Bayangkan sebuah restoran. Dapur adalah server. Pelayan yang "
        "membawa pesanan bolak-balik adalah HTTP. Anda yang duduk di "
        "meja adalah client. Anda tidak masuk ke dapur — Anda hanya "
        "menyerahkan pesanan (request) dan menerima piring jadinya "
        "(response)."
    ))

    s.append(p("HTTP, method, status code", "h2"))
    s.append(p(
        "Setiap interaksi di web memakai <b>HTTP</b>, protokol yang "
        "mengatur format request dan response. Dua bagian yang akan "
        "paling sering Anda lihat:"
    ))
    s.extend(bullets([
        "<b>Method</b>: <font face='Courier'>GET</font> artinya \"berikan "
        "sesuatu\", <font face='Courier'>POST</font> artinya \"ini "
        "datanya, kerjakan sesuatu\", <font face='Courier'>PUT</font> = "
        "\"perbarui\", <font face='Courier'>DELETE</font> = \"hapus\".",
        "<b>Status code</b>: angka yang menjelaskan apa yang terjadi. "
        "<font face='Courier'>200</font> = OK, "
        "<font face='Courier'>400</font> = request Anda salah bentuk, "
        "<font face='Courier'>401</font> = belum login / token salah, "
        "<font face='Courier'>404</font> = tidak ditemukan, "
        "<font face='Courier'>500</font> = server error.",
    ]))

    s.append(p("JSON", "h2"))
    s.append(p(
        "<b>JSON</b> adalah cara paling umum mengirim data terstruktur "
        "lewat HTTP. Bentuknya seperti ini:"
    ))
    s.append(code(
        '{\n  "face_count": 1,\n  "faces": [{"x": 100, "y": 50, "w": 200, "h": 200}],\n'
        '  "processing_time_ms": 42.5\n}'
    ))
    s.append(p("Kunci berupa string; nilai bisa string, angka, list, "
               "boolean, <font face='Courier'>null</font>, atau objek JSON lain."))

    s.append(p("API dan endpoint", "h2"))
    s.append(p(
        "<b>API</b> (Application Programming Interface) adalah daftar "
        "menu yang dapat dikerjakan server. Tiap item di menu disebut "
        "<b>endpoint</b> — kombinasi URL spesifik dan method (contoh: "
        "<font face='Courier'>POST /detect/faces</font>)."
    ))

    s.append(p("Autentikasi dan token", "h2"))
    s.append(p(
        "<b>Autentikasi</b> menjawab pertanyaan \"siapa yang memanggil?\". "
        "Skema paling sederhana adalah <b>token</b> — string acak panjang "
        "yang dibagikan server, dan harus dikirim client setiap request. "
        "Kita pakai gaya <b>Bearer</b>:"
    ))
    s.append(code("Authorization: Bearer ABC123XYZ..."))
    s.append(analogy(
        "Token API itu seperti kartu kunci hotel. Hotel memberikannya pada "
        "Anda. Setiap mau masuk kamar, kartu harus ditempel. Siapa pun "
        "yang memegang kartu bisa masuk — jadi jangan dibagikan, jangan "
        "diposting online, dan jangan di-commit ke git."
    ))

    s.append(p("Environment variable dan .env", "h2"))
    s.append(p(
        "<b>Environment variable</b> adalah konfigurasi yang hidup di luar "
        "kode, di memori sistem operasi. Kode yang sama bisa berperilaku "
        "berbeda di mesin yang berbeda hanya dengan mengubah nilai ini. "
        "File <font face='Courier'>.env</font> adalah file teks yang "
        "mendaftarkannya, satu baris per variabel:"
    ))
    s.append(code("API_KEY=ABC123XYZ\nDEBUG=false"))

    s.append(p("Docker, image, container", "h2"))
    s.append(p(
        "<b>Docker</b> mengemas program beserta segala kebutuhannya "
        "(versi Python, library, tool sistem) menjadi satu paket. "
        "Resepnya disebut <b>Dockerfile</b>. Membangun resep menghasilkan "
        "<b>image</b>. Menjalankan image menghasilkan <b>container</b> — "
        "komputer-kecil-di-dalam-komputer yang terisolasi. Image yang "
        "sama akan berjalan sama di laptop Anda, di VM cloud, atau di "
        "ruang server kampus."
    ))
    s.append(why(
        "Tanpa Docker, Anda harus mengulang langkah instalasi di setiap "
        "mesin dan berharap tidak ada konflik versi. Dengan Docker, satu "
        "perintah — <font face='Courier'>docker compose up -d --build</font> "
        "— membangun ulang seluruh lingkungan dari awal."
    ))

    # ---- Bab 3 ----
    s.append(PageBreak())
    s.append(p("Bab 3 — Bagaimana kode diorganisasi", "h1"))
    s.append(p(
        "Proyek dipecah menjadi lapisan, seperti lantai sebuah gedung. "
        "Sebuah request masuk dari lantai atas (Flask), melewati keamanan "
        "(auth), tiba di ruangan tertentu (handler route), dan ruangan itu "
        "memanggil para spesialis (detector, processor) untuk benar-benar "
        "mengerjakan tugasnya."
    ))
    s.append(code(ARCHITECTURE))

    s.append(p("Peta folder — apa fungsi tiap file", "h3"))
    s.append(kv_table([
        ("app.py", "\"Pintu depan\". Membuat aplikasi Flask, mendaftarkan "
                   "semua route, mengaktifkan CORS dan Swagger UI."),
        ("wsgi.py", "Entrypoint satu baris yang dipakai Gunicorn di "
                    "production. Jarang Anda ubah."),
        ("config/settings.py", "Membaca file .env. Bila Anda di production "
                               "dan secret tidak ada, file ini menolak "
                               "menjalankan aplikasi. Gagal dengan keras."),
        ("src/api/auth.py", "Berisi decorator @require_api_key. Setiap "
                            "endpoint terproteksi berdiri di belakangnya."),
        ("src/api/moodle_routes.py", "Endpoint yang dipanggil Moodle "
                                     "(/detect/faces, /verify/face, ...)."),
        ("src/api/proctoring_routes.py", "Endpoint untuk memulai, "
                                          "menghentikan, dan memeriksa sesi."),
        ("src/core/orchestrator.py", "Otaknya. Tahu cara berbicara dengan "
                                     "setiap detector dan processor."),
        ("src/core/model_manager.py", "Memuat file model .pth/.pkl. Bila "
                                       "file tidak ada atau rusak, otomatis "
                                       "fallback ke OpenCV."),
        ("src/detectors/", "face_detector.py mencari wajah. eye_tracker.py "
                           "mengikuti mata."),
        ("src/processors/", "session_manager.py mencatat satu sesi ujian. "
                            "webcam_capture.py membaca dari kamera fisik."),
        ("src/utils/report_generator.py", "Menulis laporan akhir JSON / "
                                          "TXT / PDF tiap sesi."),
        ("Dockerfile + docker-compose.yml", "Resep + cara satu-perintah "
                                            "untuk menjalankannya sebagai "
                                            "container."),
        (".env.example", "Template yang Anda salin ke .env dan isi."),
    ]))

    # ---- Bab 4 ----
    s.append(PageBreak())
    s.append(p("Bab 4 — Satu request, selangkah demi selangkah", "h1"))
    s.append(p(
        "Mari ikuti satu request melalui sistem. Bayangkan Moodle mengirim "
        "gambar berformat base64 ke "
        "<font face='Courier'>POST /detect/faces</font>:"))
    s.append(code(REQUEST_FLOW))

    s.append(p("Langkahnya dalam bahasa sederhana", "h3"))
    s.extend(numbered([
        "<b>HTTP request tiba.</b> Flask memeriksa bahwa body tidak lebih "
        "besar dari 50 MB (batasan ini ada karena gambar bisa sangat besar).",
        "<b>Pemeriksaan auth.</b> Decorator "
        "<font face='Courier'>require_api_key</font> membaca header "
        "<font face='Courier'>Authorization</font>. Bila token hilang atau "
        "salah, server langsung membalas 401 dan berhenti.",
        "<b>Parsing JSON.</b> Flask membaca body JSON, menemukan field "
        "<font face='Courier'>image</font>, dan menyerahkannya ke route.",
        "<b>Decoding base64.</b> Route mengubah string kembali menjadi "
        "bytes gambar, lalu menjadi gambar OpenCV (matriks nilai piksel).",
        "<b>Deteksi.</b> Orchestrator memanggil face detector. Bila model "
        "deep learning gagal dimuat sebelumnya, sistem otomatis memakai "
        "Haar Cascade dari OpenCV. Apa pun jalurnya, route mendapat daftar "
        "kotak wajah.",
        "<b>Landmark (opsional).</b> Bila request meminta landmark, eye "
        "tracker juga dijalankan dan mengembalikan koordinat mata.",
        "<b>Menyusun response JSON.</b> Route merakit kamus berisi kotak "
        "wajah, jumlah, dan waktu proses, lalu Flask mengirim balik dengan "
        "status 200.",
    ]))

    s.append(p("Bagaimana satu sesi penuh terlihat", "h3"))
    s.extend(bullets([
        "<b>1.</b> Client memanggil "
        "<font face='Courier'>POST /api/proctoring/session/start</font> "
        "dengan session ID dan user ID.",
        "<b>2.</b> Orchestrator membuat objek sesi. Mulai sekarang ia "
        "mengingat setiap frame, peringatan, dan waktu.",
        "<b>3.</b> Client (atau webcam lokal) memasukkan frame.",
        "<b>4.</b> Tiap frame diperiksa. Bila ada yang ganjil, peringatan "
        "ditambahkan ke log sesi.",
        "<b>5.</b> Client memanggil "
        "<font face='Courier'>POST /api/proctoring/session/stop</font>. "
        "Report generator menulis "
        "<font face='Courier'>reports/&lt;id&gt;.json</font>, "
        "<font face='Courier'>.txt</font>, dan "
        "<font face='Courier'>.pdf</font>.",
    ]))

    # ---- Bab 5 ----
    s.append(PageBreak())
    s.append(p("Bab 5 — Memasang proyek", "h1"))
    s.append(p("Anda punya dua pilihan. Bila Anda sekadar mengevaluasi kode "
               "atau ngoprek lokal, ikuti jalur \"Python langsung\". Bila "
               "Anda akan deploy, lompat ke Bab 8 (Docker)."))

    s.append(p("Jalur Python langsung", "h2"))
    s.append(p("Langkah 1 — buka terminal dan clone repository:", "h3"))
    s.append(code("git clone https://github.com/evankafauzya/capstone-backend.git\ncd capstone-backend"))

    s.append(p("Langkah 2 — buat virtual environment.", "h3"))
    s.append(p(
        "Virtual environment adalah folder pribadi tempat Python memasang "
        "library proyek ini tanpa mengganggu komputer Anda secara umum. "
        "Bila suatu saat Anda menghapus proyek, virtualenv ikut hilang — "
        "tidak ada yang rusak."
    ))
    s.append(code(
        "python -m venv venv\n"
        ".\\venv\\Scripts\\activate          # Windows (PowerShell / CMD)\n"
        "# source venv/bin/activate        # macOS / Linux"
    ))
    s.append(tip(
        "Bila prompt Anda kini diawali <font face='Courier'>(venv)</font>, "
        "Anda sudah berada di dalam virtual environment. Semua "
        "<font face='Courier'>pip install</font> dari sini hanya tersimpan "
        "di folder ini."
    ))

    s.append(p("Langkah 3 — instal dependency:", "h3"))
    s.append(code("pip install -r requirements.txt"))
    s.append(p(
        "Perintah ini mengunduh Flask, OpenCV, PyTorch, dsb. Pertama "
        "kali bisa memakan beberapa menit — PyTorch saja ukurannya "
        "ratusan megabyte."))

    s.append(p("Langkah 4 — buat file .env:", "h3"))
    s.append(code("cp .env.example .env   # macOS / Linux\ncopy .env.example .env # Windows"))

    s.append(p("Langkah 5 — buat dua secret kuat, tempelkan ke .env:", "h3"))
    s.append(code('python -c "import secrets; print(secrets.token_urlsafe(48))"'))
    s.append(p("Jalankan dua kali. Pakai output pertama sebagai "
               "<font face='Courier'>SECRET_KEY</font> dan output kedua "
               "sebagai <font face='Courier'>API_KEY</font>."))

    s.append(warn(
        "<b>Jangan</b> bagikan file <font face='Courier'>.env</font> Anda. "
        "<b>Jangan</b> commit ke git. File example aman di-commit karena "
        "nilai-nilainya kosong; file asli berisi rahasia Anda."
    ))

    # ---- Bab 6 ----
    s.append(PageBreak())
    s.append(p("Bab 6 — File .env, baris per baris", "h1"))
    s.append(kv_table([
        ("ENVIRONMENT", "<font face='Courier'>development</font> atau "
                        "<font face='Courier'>production</font>. Di "
                        "production, secret yang hilang akan menggagalkan "
                        "boot (ini disengaja)."),
        ("DEBUG", "<font face='Courier'>true</font> menampilkan halaman "
                  "error lengkap dengan stack trace. Berguna saat belajar, "
                  "berbahaya di production. Default true di development, "
                  "false di production."),
        ("HOST", "Interface jaringan tempat server mendengarkan. "
                 "<font face='Courier'>0.0.0.0</font> berarti \"semua "
                 "interface\". Biarkan 0.0.0.0 kecuali Anda tahu alasannya."),
        ("PORT", "Port TCP. Default 5000. Bila port sudah dipakai, "
                 "aplikasi gagal start."),
        ("LOG_LEVEL", "Seberapa cerewet log. Set "
                      "<font face='Courier'>DEBUG</font> saat belajar, "
                      "<font face='Courier'>INFO</font> di production."),
        ("SECRET_KEY", "Dipakai Flask untuk menandatangani cookie sesi. "
                       "Wajib di production. Harus string acak panjang."),
        ("API_KEY", "Bearer token yang Anda berikan ke client. Siapa pun "
                    "yang memilikinya bisa memanggil API. Wajib di "
                    "production."),
        ("API_KEY_REQUIRED", "Bila diset "
                             "<font face='Courier'>false</font>, "
                             "pengecekan auth dilewati. Pakai hanya di "
                             "mesin Anda sendiri."),
        ("CORS_ORIGINS", "Origin web mana yang boleh memanggil API. "
                         "<font face='Courier'>*</font> berarti siapa saja. "
                         "Di production, set ke URL Moodle Anda (mis. "
                         "<font face='Courier'>https://moodle.kampus.ac.id</font>)."),
        ("CAPTURE_INTERVAL", "Seberapa sering webcam dibaca, dalam detik."),
        ("REVERIFICATION_INTERVAL", "Seberapa sering kita memeriksa ulang "
                                    "bahwa mahasiswa adalah orang yang "
                                    "sama, dalam detik."),
        ("SESSION_TIMEOUT", "Durasi maksimum sesi dalam detik."),
        ("FACE_DETECTION_CONFIDENCE", "Skor minimum (0–1) supaya detector "
                                      "mempertahankan sebuah wajah. Lebih "
                                      "kecil = wajah lebih banyak tapi "
                                      "false positive juga lebih banyak."),
        ("FACE_MATCH_THRESHOLD", "Skor kemiripan minimum supaya dua wajah "
                                 "dianggap orang yang sama."),
        ("MAX_FACES_ALLOWED", "Bila terlihat lebih dari sekian wajah, "
                              "peringatan dimunculkan."),
    ]))

    # ---- Bab 7 ----
    s.append(PageBreak())
    s.append(p("Bab 7 — Menjalankan aplikasi (cara sederhana)", "h1"))
    s.append(p("Dengan virtual environment aktif dan .env terisi:"))
    s.append(code("python app.py"))
    s.append(p("Anda akan melihat baris seperti ini:"))
    s.append(code(
        "Proctoring system initialized successfully\n"
        "Moodle Proctoring AI Backend v2.0.0 ready (env=development, debug=True)\n"
        " * Running on http://0.0.0.0:5000"
    ))
    s.append(p("Sekarang buka URL berikut:"))
    s.extend(bullets([
        "<font face='Courier'>http://localhost:5000/health</font> — harus "
        "mengembalikan JSON berisi <font face='Courier'>\"status\": "
        "\"healthy\"</font>.",
        "<font face='Courier'>http://localhost:5000/docs</font> — Swagger "
        "UI. Anda dapat klik tiap endpoint dan mencobanya.",
        "<font face='Courier'>http://localhost:5000/openapi.json</font> — "
        "spesifikasi mesin-bisa-baca, berguna saat membangun client.",
    ]))
    s.append(p("Hentikan aplikasi kapan pun dengan <b>Ctrl+C</b> di terminal."))

    # ---- Bab 8 ----
    s.append(PageBreak())
    s.append(p("Bab 8 — Deployment dengan Docker", "h1"))
    s.append(p(
        "Docker adalah cara mengirim backend ini ke server sungguhan (atau "
        "ke mesin teman) tanpa pusing soal versi Python atau library sistem "
        "yang kurang."
    ))
    s.append(p("Apa yang sudah disiapkan", "h2"))
    s.extend(bullets([
        "<font face='Courier'>Dockerfile</font> — resepnya. Mulai dari "
        "<font face='Courier'>python:3.11-slim</font>, memasang library "
        "sistem OpenCV, menyalin kode, memasang paket Python, lalu "
        "menjalankan Gunicorn.",
        "<font face='Courier'>docker-compose.yml</font> — file tingkat "
        "lebih tinggi yang berkata \"build image ini, jalankan, expose "
        "port 5000, mount folder ini\".",
        "<font face='Courier'>.dockerignore</font> — menjaga rahasia, "
        "venv, dan file besar tidak ikut ke build.",
    ]))

    s.append(p("Tiga perintah yang sebenarnya Anda perlu", "h2"))
    s.append(code(
        "# 1. Pastikan .env terisi (ENVIRONMENT=production, SECRET_KEY=..., API_KEY=...)\n"
        "# 2. Build image dan jalankan container di background:\n"
        "docker compose up -d --build\n\n"
        "# 3. Cek apakah sehat:\n"
        "curl http://localhost:5000/health"
    ))
    s.append(p("Perintah lain yang berguna:"))
    s.append(code(
        "docker compose logs -f         # log live (Ctrl+C untuk keluar)\n"
        "docker compose ps              # status container\n"
        "docker compose down            # hentikan dan hapus container\n"
        "docker compose restart         # restart tanpa build ulang"
    ))

    s.append(p("Apa yang di-mount oleh compose dan kenapa", "h2"))
    s.append(kv_table([
        ("./models_data → /app/models_data",
         "Read-only. Letakkan file model .pth / .pkl di sini; container "
         "langsung melihat tanpa perlu build ulang."),
        ("./reports → /app/reports",
         "Laporan yang ditulis sesi tersimpan di sini, bahkan setelah "
         "container dihapus."),
        ("./logs → /app/logs",
         "Log aplikasi tetap ada walau container di-restart."),
    ]))
    s.append(why(
        "Tanpa <b>volume</b> ini, saat container Anda hentikan, semua isi "
        "di dalamnya hilang. Volume berkata kepada Docker \"simpan folder "
        "ini di disk host, bukan di lapisan sekali pakai container\"."
    ))

    s.append(p("Tuning untuk production", "h2"))
    s.append(p(
        "Di dalam Dockerfile, Gunicorn berjalan dengan worker dan thread "
        "yang dikendalikan environment variable. Tambahkan ini ke "
        "<font face='Courier'>.env</font> bila perlu:"))
    s.append(code(
        "GUNICORN_WORKERS=4    # proses paralel (kerja CPU-bound)\n"
        "GUNICORN_THREADS=8    # thread per worker (kerja I/O-bound)\n"
        "GUNICORN_TIMEOUT=180  # detik sebelum request lambat di-kill"
    ))
    s.append(tip(
        "Titik awal yang umum untuk VM kecil: workers=2 dan threads=4. "
        "Naikkan worker bila CPU sering menganggur. Naikkan thread bila "
        "banyak request menunggu jaringan."
    ))

    # ---- Bab 9 ----
    s.append(PageBreak())
    s.append(p("Bab 9 — Endpoint API", "h1"))
    s.append(p(
        "Setiap endpoint yang melakukan kerja nyata mengharapkan Bearer "
        "token. Kirim seperti ini:"))
    s.append(code("Authorization: Bearer <API_KEY anda>"))
    s.append(p("Server juga menerima header alternatif:"))
    s.append(code("X-API-Key: <API_KEY anda>"))

    s.append(p("Endpoint publik (yang dipanggil Moodle)", "h2"))
    s.append(endpoint_table(PUBLIC_ENDPOINTS))

    s.append(p("Endpoint internal (siklus hidup sesi)", "h2"))
    s.append(p("Semua path di bawah ini berada di bawah "
               "<font face='Courier'>/api/proctoring</font>."))
    s.append(endpoint_table(INTERNAL_ENDPOINTS))

    s.append(p("Contoh lengkap: mendeteksi wajah pada sebuah gambar", "h2"))
    s.append(p("Request:"))
    s.append(code(
        'curl -X POST http://localhost:5000/detect/faces \\\n'
        '  -H "Authorization: Bearer $API_KEY" \\\n'
        '  -H "Content-Type: application/json" \\\n'
        '  -d \'{"image": "data:image/jpeg;base64,/9j/4AAQ..."}\''
    ))
    s.append(p("Response (status 200):"))
    s.append(code(
        '{\n'
        '  "faces": [\n'
        '    {"x": 120, "y": 80, "w": 180, "h": 180, "confidence": 0.91}\n'
        '  ],\n'
        '  "face_count": 1,\n'
        '  "landmarks": {"left_eye": [165, 130], "right_eye": [235, 130]},\n'
        '  "processing_time_ms": 47.3\n'
        '}'
    ))

    s.append(p("Pesan error yang sering muncul", "h3"))
    s.append(kv_table([
        ("400 Bad Request",   "Body request kekurangan field wajib atau base64-nya salah."),
        ("401 Unauthorized",  "Token API hilang atau salah."),
        ("404 Not Found",     "URL salah — periksa ejaannya."),
        ("405 Method Not Allowed", "Anda memakai GET pada endpoint POST atau sebaliknya."),
        ("500 Internal Server Error", "Server crash. Lihat log."),
    ]))

    # ---- Bab 10 ----
    s.append(PageBreak())
    s.append(p("Bab 10 — Memakai Swagger UI", "h1"))
    s.append(p(
        "Swagger UI adalah halaman web bawaan backend yang mencatatkan "
        "setiap endpoint dan membiarkan Anda memanggilnya dari browser "
        "tanpa menulis kode. Ini cara tercepat belajar API."
    ))
    s.append(p("Panduan langkah demi langkah", "h2"))
    s.extend(numbered([
        "Buka <font face='Courier'>http://localhost:5000/docs</font> di browser.",
        "Klik tombol hijau <b>Authorize</b> di pojok kanan atas.",
        "Tempelkan nilai <font face='Courier'>API_KEY</font> dari .env Anda "
        "ke dialog. Klik <b>Authorize</b>, lalu <b>Close</b>.",
        "Gulir ke bawah dan buka endpoint apa pun, misal "
        "<font face='Courier'>POST /detect/faces</font>.",
        "Klik <b>Try it out</b>. Akan muncul textarea berisi contoh body "
        "request. Ubah sesuai keinginan.",
        "Klik <b>Execute</b>. UI menampilkan response, status code, dan "
        "perintah <font face='Courier'>curl</font> yang ekuivalen — Anda "
        "bisa pakai untuk reproduksi di terminal.",
    ]))
    s.append(tip(
        "Bila tombol <b>Authorize</b> tidak muncul, browser Anda "
        "menampilkan cache lama. Tekan Ctrl+Shift+R untuk hard-reload."
    ))

    # ---- Bab 11 ----
    s.append(PageBreak())
    s.append(p("Bab 11 — Checklist keamanan sebelum go-live", "h1"))
    s.append(p("Periksa daftar ini sebelum menaruh server di internet publik."))
    s.extend(bullets([
        "<font face='Courier'>ENVIRONMENT=production</font> sudah di-set di .env.",
        "<font face='Courier'>SECRET_KEY</font> dan "
        "<font face='Courier'>API_KEY</font> keduanya string acak panjang "
        "(minimal 32 karakter). Jangan pernah memakai nilai dari example.",
        ".env tidak di-commit ke git (sudah di .gitignore).",
        "<font face='Courier'>DEBUG=false</font>. Jika tidak, stack trace "
        "bisa bocor lewat halaman error.",
        "<font face='Courier'>CORS_ORIGINS</font> hanya berisi origin "
        "Moodle Anda, tidak <font face='Courier'>*</font>.",
        "Reverse proxy (Nginx, Caddy, atau load balancer cloud) berada di "
        "depan container dan menangani TLS sehingga lalu lintas HTTPS.",
        "<font face='Courier'>models_data/</font>, "
        "<font face='Courier'>reports/</font> dan "
        "<font face='Courier'>logs/</font> di-mount ke storage permanen.",
        "Bila Anda mengganti API key, perbarui semua plugin Moodle dan "
        "client secara bersamaan.",
    ]))
    s.append(why(
        "Bearer token sangat kuat — siapa pun yang memegangnya bisa "
        "memanggil API. Karena itu kami tidak pernah log, tidak pernah "
        "menampilkan lewat <font face='Courier'>/configuration</font>, "
        "dan membandingkannya dengan "
        "<font face='Courier'>hmac.compare_digest</font> (perbandingan "
        "aman-timing yang tidak bocor walaupun attacker mengukur "
        "millisecond)."
    ))

    # ---- Bab 12 ----
    s.append(PageBreak())
    s.append(p("Bab 12 — Saat ada masalah", "h1"))
    s.append(kv_table([
        ("Aplikasi menolak start: \"SECRET_KEY is required\"",
         "Anda menyetel ENVIRONMENT=production tapi SECRET_KEY kosong. "
         "Isi nilainya, atau sementara ubah ENVIRONMENT=development."),
        ("Aplikasi menolak start: \"API_KEY is required\"",
         "Sama seperti di atas, untuk API_KEY."),
        ("Setiap request mendapat 401",
         "Header mungkin salah tulis (harus persis "
         "<font face='Courier'>Authorization: Bearer ...</font>) atau "
         "token tidak cocok dengan API_KEY di .env. Token case-sensitive."),
        ("Swagger UI kosong atau menampilkan endpoint lama",
         "Hard-reload (Ctrl+Shift+R). Bila masih kosong, buka langsung "
         "<font face='Courier'>/openapi.json</font> — harus mengembalikan JSON."),
        ("Deteksi selalu menghasilkan 0 wajah",
         "Pastikan gambar terang dan ada wajah. Lihat log; bila ada baris "
         "\"Falling back to OpenCV Cascade\", berarti model .pth gagal "
         "dimuat tapi deteksi tetap berjalan."),
        ("Endpoint webcam gagal di Docker",
         "Container tidak melihat webcam host secara default. Pakai "
         "endpoint berbasis gambar base64 dari client yang punya akses "
         "webcam, atau jalankan aplikasi di luar Docker."),
        ("Port 5000 sudah dipakai",
         "Ubah PORT di .env, atau hentikan program yang memakai 5000 "
         "(macOS AirPlay sering memakainya)."),
        ("\"docker: command not found\"",
         "Pasang Docker Desktop (Windows / macOS) atau docker-ce (Linux)."),
    ]))

    # ---- Glosarium ----
    s.append(PageBreak())
    s.append(p("Glosarium", "h1"))
    s.append(kv_table([
        ("API",           "Daftar menu hal yang dapat dilakukan server untuk client-nya."),
        ("Backend",       "Kode yang berjalan di server, di balik layar pengguna."),
        ("Base64",        "Cara mengubah bytes (misalnya gambar) menjadi string ASCII panjang supaya bisa lewat field JSON."),
        ("Bearer token",  "String rahasia yang dikirim client untuk membuktikan identitasnya."),
        ("Client",        "Apa pun yang memanggil server (browser, aplikasi, Moodle, curl)."),
        ("Container",     "Instance Docker image yang sedang berjalan. Terisolasi dari host."),
        ("CORS",          "Aturan web yang menentukan situs lain mana yang boleh memanggil API Anda."),
        ("Docker",        "Tool yang mengemas program beserta dependency-nya ke dalam image yang portable."),
        ("Endpoint",      "Kombinasi URL + HTTP method yang dipahami server."),
        ("Environment variable", "Konfigurasi yang disimpan OS, bukan di kode. Dibaca saat startup."),
        ("Flask",         "Framework web Python. Menangani routing dan detail HTTP untuk kita."),
        ("Frontend",      "Bagian aplikasi yang terlihat pengguna (halaman web, layar aplikasi)."),
        ("Gunicorn",      "Web server produksi yang menjalankan aplikasi Flask dengan andal."),
        ("Header",        "Metadata tambahan yang ikut dalam request atau response HTTP."),
        ("HTTP",          "Protokol yang dipakai browser dan API untuk berbicara."),
        ("HTTPS",         "HTTP yang dienkripsi TLS."),
        ("JSON",          "Format teks sederhana untuk data terstruktur."),
        ("OpenAPI",       "Standar deskripsi API yang machine-readable."),
        ("Proctoring",    "Pengawasan ujian untuk mendeteksi kecurangan."),
        ("Request",       "Pesan yang dikirim client ke server."),
        ("Response",      "Pesan balasan yang dikirim server."),
        ("REST",          "Gaya desain API HTTP berbasis resource dan method."),
        ("Reverse proxy", "Server yang berada di depan aplikasi Anda, menangani TLS, dan meneruskan request."),
        ("Route",         "Kode yang menangani endpoint tertentu."),
        ("Server",        "Komputer (atau program) yang menunggu dan menjawab request."),
        ("Status code",   "Angka yang dikirim server untuk memberitahu apa yang terjadi (200, 401, 500, ...)."),
        ("Swagger UI",    "Halaman web interaktif yang mendokumentasikan dan menguji API."),
        ("Volume",        "Folder di komputer host yang dapat dibaca/ditulis container Docker."),
        ("WSGI",          "Standar Python untuk menghubungkan aplikasi web dengan web server (Gunicorn berbicara WSGI)."),
    ]))

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
        topMargin=2 * cm,  bottomMargin=2 * cm,
        title="Moodle Proctoring AI Backend Guide",
    )
    doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
    return out


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    en = render("proctoring-backend-guide_EN.pdf", build_english())
    print(f"Generated: {en}  ({en.stat().st_size // 1024} KB)")
    id_ = render("proctoring-backend-guide_ID.pdf", build_indonesian())
    print(f"Generated: {id_} ({id_.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
