# Moodle Proctoring AI Backend

REST API for face detection, multi-reference identity verification, liveness
detection, behavior analysis, and session-based proctoring. Built with
**FastAPI**, designed to integrate with the Moodle `quizaccess_proctoring`
plugin but usable from any HTTP client.

- **Swagger UI:** `http://<host>:5000/docs`
- **OpenAPI 3.x spec:** `http://<host>:5000/openapi.json`
- **Health probes:** `/health` (readiness, gated on models) and `/healthz` (liveness)
- **Beginner-friendly guides:** `docs/proctoring-backend-guide_EN.pdf` + `docs/proctoring-backend-guide_ID.pdf`

---

## 1. What's inside

| Component | Library | Notes |
| --- | --- | --- |
| Face detection (primary) | **Ultralytics YOLO** | Loaded from `models_data/face_detection_yolo.pt`. |
| Face detection (fallback) | **RetinaFace MobileNet0.25** | Loaded from `face_detection_model.pth` if YOLO missing. |
| Face alignment | **MediaPipe FaceLandmarker** | 5-point similarity transform to the canonical InsightFace 112×112 template. |
| Face recognition | **ArcFace** (ResNet50 or EfficientNet-B0) | Backbone autodetected from the checkpoint shape. |
| Enrollment storage | **SQLite** | 512-d embedding BLOBs in `data/enrollments.db`. |
| Audit trail | **SQLite** | Every `/verify/face` call gets logged with request ID, score, threshold, decision. |
| Liveness | **MediaPipe FaceLandmarker** | Stateless blink + micro-motion analyzer over a short clip. |
| Web framework | **FastAPI** + Uvicorn | One Gunicorn worker with the `UvicornWorker` class. |
| Auth | Bearer token (`Authorization: Bearer …` or `X-API-Key`) | `hmac.compare_digest`, never logged. |
| Rate limiting | **slowapi** | 600/min per token-or-IP. |
| TLS | **Caddy** (optional overlay) | Auto-HTTPS via Let's Encrypt with one Caddyfile edit. |

---

## 2. Project layout

```
capstone-backend/
├── app.py                       # FastAPI application factory + middlewares
├── asgi.py                      # ASGI entrypoint (Gunicorn + uvicorn worker)
├── Dockerfile
├── docker-compose.yml           # Local / single-node deployment
├── docker-compose.tls.yml       # Overlay that puts Caddy in front (TLS)
├── Caddyfile.example            # Copy to Caddyfile; pick prod-domain or local-internal-TLS
├── requirements.txt
├── pytest.ini
├── .env.example
├── .github/workflows/ci.yml     # Lint + tests + Docker build on every push
├── config/
│   └── settings.py              # Env-driven configuration; fails closed in production
├── src/
│   ├── api/
│   │   ├── auth.py              # Bearer-token FastAPI dependency
│   │   ├── moodle_routes.py     # Detect / verify / enroll / liveness / audit
│   │   ├── proctoring_routes.py # In-process session lifecycle
│   │   └── schemas.py           # Pydantic request/response models
│   ├── core/
│   │   ├── model_manager.py     # Picks YOLO/RetinaFace, loads ArcFace + aligner
│   │   └── orchestrator.py      # Coordinates models + session + report generator
│   ├── models/
│   │   ├── _torch_load.py       # weights_only=True with safe fallback
│   │   ├── yolo_face_detector.py
│   │   ├── retinaface.py        # Architecture (vendored from biubug6)
│   │   ├── face_detector.py     # RetinaFace inference wrapper
│   │   ├── arcface.py           # Backbone-autodetecting FaceEmbeddingNet
│   │   ├── face_aligner.py      # MediaPipe FaceLandmarker -> similarity transform
│   │   └── face_recognizer.py   # Align + embed + cosine similarity
│   ├── detectors/
│   │   ├── eye_tracker.py       # MediaPipe-based blink / gaze tracker (session)
│   │   ├── face_detector.py     # Session-time face detector wrapper
│   │   └── liveness.py          # Stateless blink + micro-motion liveness
│   ├── processors/
│   │   ├── session_manager.py
│   │   └── webcam_capture.py
│   ├── services/
│   │   ├── face_enrollment.py   # SQLite enrollment store (embeddings BLOB)
│   │   └── audit.py             # SQLite verification audit log
│   └── utils/
│       └── report_generator.py
├── tests/
│   ├── conftest.py              # Auto-enables MOCK_MODELS when .pth/.pt absent
│   ├── _stub_system.py          # Stub ProctoringSystem for CI / fast tests
│   └── test_smoke.py            # 22 tests across auth, validation, enroll, audit, liveness
├── models_data/                 # GITIGNORED -- drop your .pth / .pt / .task here
├── data/                        # GITIGNORED -- SQLite database lives here
├── reports/                     # GITIGNORED -- generated session reports
└── logs/                        # GITIGNORED -- rotating application logs
```

---

## 3. Required model files

These are **not** in the git repo (they're large + your trained weights). Drop
them into `models_data/` before booting:

| File | What it is | Where to find it |
| --- | --- | --- |
| `face_detection_yolo.pt` | Ultralytics YOLO face detector (≈6 MB) | Your YOLO training output |
| `face_detection_model.pth` | RetinaFace MobileNet0.25 (≈3.5 MB) — used as fallback | [biubug6/Pytorch_Retinaface](https://github.com/biubug6/Pytorch_Retinaface) pretrained, or your fine-tune |
| `face_recognition_*.pth` | ArcFace ResNet50 or EfficientNet-B0 (≈40–200 MB) | Your ArcFace training output. Default expected name is set in `config/settings.py`. |
| `face_landmarker.task` | MediaPipe FaceLandmarker (≈3.7 MB) | [MediaPipe model gallery](https://developers.google.com/mediapipe/solutions/vision/face_landmarker) |

Without these, the system **falls back to OpenCV Haar Cascades** and accuracy
collapses. `/health` will return 503 in that state, so a load balancer will
route traffic away.

---

## 4. Configuration

All settings come from environment variables; start from the template:

```bash
cp .env.example .env
```

### Required in production

| Variable | Purpose |
| --- | --- |
| `ENVIRONMENT` | Set to `production`. Triggers fail-closed checks. |
| `SECRET_KEY` | Session signing key. App refuses to boot without it in production. |
| `API_KEY` | Bearer token clients must send. App refuses to boot without it in production. |

Generate strong secrets:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Useful tunables

| Variable | Default | Notes |
| --- | --- | --- |
| `CORS_ORIGINS` | `*` | Comma-separated list. App logs a **warning** in production if `*`. |
| `LOG_LEVEL` | `DEBUG`/`INFO` | Per-environment default. |
| `MODELS_DIR` | `./models_data` | Where the `.pth` / `.pt` / `.task` files live. |
| `DATA_DIR` | `./data` | Where SQLite stores enrollments + audit log. |
| `ENROLLMENT_DB_PATH` | `${DATA_DIR}/enrollments.db` | Override the DB location. |
| `FACE_MATCH_THRESHOLD` | `0.4` | Cosine threshold. 0.4 is tuned for webcam-vs-registered-photo. Raise to 0.5+ only when both photos come from the same source. |
| `FACE_DETECTION_CONFIDENCE` | `0.5` | YOLO confidence cutoff. |
| `MAX_FACES_ALLOWED` | `1` | More than this fires a behavior warning. |
| `MOCK_MODELS` | (unset) | Set to `1` to skip real model loading (used by CI). |

### Auth

Every protected endpoint expects:

```
Authorization: Bearer <API_KEY>
```

`X-API-Key: <API_KEY>` is accepted as a fallback. Set `API_KEY_REQUIRED=false`
to disable auth (development only).

---

## 5. Run it

### Local (no Docker)

```bash
python -m venv venv
.\venv\Scripts\activate         # Windows
# source venv/bin/activate      # macOS / Linux
pip install -r requirements.txt
cp .env.example .env             # then edit SECRET_KEY + API_KEY
python app.py
```

Open <http://localhost:5000/docs>.

### Docker (recommended)

```bash
docker compose up -d --build
curl http://localhost:5000/health
```

Volumes mounted by compose:

| Host → container | Purpose |
| --- | --- |
| `./models_data → /app/models_data:ro` | Swap model files without rebuilding. |
| `./data → /app/data` | Persists the SQLite enrollment + audit DB. **Critical.** |
| `./reports → /app/reports` | Persists generated session reports. |
| `./logs → /app/logs` | Persists rotating application logs. |

### Docker + TLS (production)

```bash
cp Caddyfile.example Caddyfile
# Edit Caddyfile -- pick the production block and your domain
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
```

The TLS overlay removes the app's direct port mapping (port 5000 is only
reachable from inside the compose network) and brings up Caddy on `:80`/`:443`.
Caddy auto-fetches a Let's Encrypt cert when given a real domain; for local
dev it can issue a self-signed cert via `tls internal`. See
`Caddyfile.example` for both options.

---

## 6. API surface

Full schemas in the Swagger UI at `/docs`. Every protected route returns the
same error shape (`{"error": "…"}`).

### Public probes

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/` | Service banner. |
| `GET` | `/healthz` | **Liveness** -- 200 while the process is up. Rate-limit exempt. |
| `GET` | `/health` | **Readiness** -- 200 with models loaded, **503** if detector or recognizer didn't load. Rate-limit exempt. |

### Face APIs (Moodle-facing)

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/detect/faces` | Detect faces in a base64 image (YOLO). |
| `POST` | `/verify/face` | Compare a face against a reference image *or* against all references previously enrolled for a `user_id`. |
| `POST` | `/detect/behavior` | Per-frame behavior analysis (multi-face / head pose / gaze). |
| `POST` | `/detect/liveness` | Verdict on a short clip: live human or static photo. |
| `POST` | `/embeddings` | Compute a 512-d ArcFace embedding for the largest face. |
| `POST` | `/batch/process` | Run detection or behavior analysis across many frames in one call. |

### Enrollment

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/enroll/face` | Append 1–5 reference photos for a user (max 10 total). |
| `POST` | `/enroll/face/guided` | Submit 5–20 frames from a supervised registration clip; the server picks the best + most varied frames automatically. |
| `GET`  | `/enroll/face/{user_id}` | Enrollment metadata. **Never** returns embedding values. |
| `DELETE` | `/enroll/face/{user_id}` | Wipe all references for a user. |

### Audit

| Method | Path | Description |
| --- | --- | --- |
| `GET` | `/verifications/{user_id}` | Most-recent verification attempts for one user. Never returns embeddings or image bytes — only score / threshold / decision / metadata. |

### Internal (session lifecycle)

All `/api/proctoring/*` routes require the bearer token.

| Method | Path | Description |
| --- | --- | --- |
| `POST` | `/api/proctoring/session/start` | Start an on-host proctoring session. |
| `POST` | `/api/proctoring/session/stop` | Stop session + generate reports. |
| `GET`  | `/api/proctoring/session/status` | Current session status. |
| `GET`  | `/api/proctoring/session/report` | Current session report (JSON). |
| `GET`  | `/api/proctoring/video/frame` | Latest webcam frame as JPEG. |
| `GET`  | `/api/proctoring/video/stream` | Live MJPEG stream. |
| `GET`  | `/api/proctoring/face-detection/stats` | Detector statistics. |
| `GET`  | `/api/proctoring/eye-tracking/stats` | Eye-tracker statistics. |
| `GET`  | `/api/proctoring/warnings` | Recent session warnings (?limit=N). |
| `GET`/`PUT` | `/api/proctoring/configuration` | Read / update runtime tunables. |
| `GET`  | `/api/proctoring/system-info` | Model + alignment + device info. |

### Response headers on every call

| Header | Purpose |
| --- | --- |
| `X-Request-ID` | Auto-generated if the client didn't send one, echoed back, written into every audit row. Use it to correlate logs + DB rows. |
| `X-Process-Time` | Wall-clock seconds the request spent inside the app. Cheap latency visibility. |
| `X-RateLimit-Limit` / `X-RateLimit-Remaining` | slowapi headers. |

### Example: enroll, then verify

```bash
# Three reference photos (any of the user's webcam frames)
B1=$(base64 -w0 photo1.jpg)
B2=$(base64 -w0 photo2.jpg)
B3=$(base64 -w0 photo3.jpg)

curl -X POST http://localhost:5000/enroll/face \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": \"student_001\", \"images\": [\"$B1\", \"$B2\", \"$B3\"]}"

# Later, during the exam
LIVE=$(base64 -w0 live_capture.jpg)
curl -X POST http://localhost:5000/verify/face \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d "{\"current_face\": \"$LIVE\", \"user_id\": \"student_001\"}"
```

---

## 7. Tests + CI

```bash
pytest tests/ -v         # 22 tests, ~6s in mock mode, ~12s with real models
```

The tests run in two modes:

- **Real models** — if `models_data/` contains the `.pt`/`.pth` files, the
  full stack boots. Catches model-loading regressions.
- **Mock mode** — if those files are absent (CI runners, fresh clones), or
  `MOCK_MODELS=1` is set explicitly, a stub `ProctoringSystem` is swapped in.
  Tests still validate routes, auth, validation, enrollment lifecycle,
  rate limiting, and audit log.

GitHub Actions (`.github/workflows/ci.yml`) runs ruff + pytest in mock mode
on every push to `main` and every PR, plus a Docker build check.

---

## 8. Security checklist before deployment

- [ ] `ENVIRONMENT=production` in `.env`
- [ ] Long random `SECRET_KEY` and `API_KEY`
- [ ] `.env` is **not** committed (covered by `.gitignore`)
- [ ] `CORS_ORIGINS` set to your Moodle origin(s), not `*`
  (the app logs a `WARNING` at boot otherwise)
- [ ] TLS terminated by Caddy via `docker-compose.tls.yml`, **OR** by your
  own reverse proxy
- [ ] `data/` volume mounted to durable storage (otherwise every container
  restart wipes the enrollment DB)
- [ ] All four model files present in `models_data/`
- [ ] Audit log retention reviewed for your jurisdiction (GDPR / Indonesia
  UU PDP). The system never stores image bytes or embeddings in the audit
  table — only scores and metadata.
- [ ] **Never** auto-enroll from quiz captures. Enrollment must go through
  `/enroll/face` or `/enroll/face/guided` as a deliberate, supervised step.

---

## 9. Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| `RuntimeError: SECRET_KEY is required in production` | Set `SECRET_KEY` + `API_KEY` in `.env` or container env. |
| `/health` returns **503** | A model failed to load. Check the boot logs and confirm the files in `models_data/`. |
| Every request returns **401** | Header must be exactly `Authorization: Bearer <token>` and the value must match `API_KEY`. |
| Verify scores always low (< 0.4) | Likely an unaligned input — confirm `alignment_enabled: true` via `/api/proctoring/system-info`. If false, `face_landmarker.task` is missing. |
| Match never reaches threshold for the same person | Re-enroll with webcam photos at the same camera/lighting (not a studio portrait), **or** lower `FACE_MATCH_THRESHOLD` to 0.35. |
| `404` on `/verify/face` with `user_id` | That user has no enrolled references. Enroll first via `/enroll/face` or `/enroll/face/guided`. |
| `409` on enrollment | User already at the 10-reference cap. Delete first, or pass `replace_existing=true` to the guided endpoint. |
| Webcam endpoints fail in Docker | Containers don't see the host webcam by default. Use the base64 endpoints, or run outside Docker for live capture. |
| Swagger UI is empty | Hard-reload; `/openapi.json` should return JSON. The spec is pure OpenAPI 3.x. |

---

