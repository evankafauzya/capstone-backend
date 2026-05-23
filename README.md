# Moodle Proctoring AI Backend

REST API for face detection, identity verification, behavior analysis, and
session-based proctoring. Designed to integrate with the Moodle
`quizaccess_proctoring` plugin, but usable from any HTTP client.

- Interactive Swagger UI: `http://<host>:5000/docs`
- OpenAPI spec: `http://<host>:5000/openapi.json`
- Health check: `http://<host>:5000/health`

---

## 1. Project layout

```
capstone-backend/
├── app.py                 # Flask application factory
├── wsgi.py                # Production WSGI entrypoint (Gunicorn)
├── Dockerfile             # Container image
├── docker-compose.yml     # One-command deployment
├── requirements.txt       # Python dependencies
├── .env.example           # Environment template (copy to .env)
├── config/
│   └── settings.py        # Env-driven configuration
└── src/
    ├── api/
    │   ├── auth.py            # Shared bearer-token auth
    │   ├── moodle_routes.py   # Public Moodle endpoints
    │   └── proctoring_routes.py # Internal session endpoints
    ├── core/                  # Orchestrator + model manager
    ├── detectors/             # Face & eye trackers
    ├── processors/            # Webcam + session manager
    └── utils/                 # Report generation
```

---

## 2. Configuration

All configuration is read from environment variables. Start from the
template:

```bash
cp .env.example .env
```

### Required for production

| Variable          | Purpose                                              |
| ----------------- | ---------------------------------------------------- |
| `ENVIRONMENT`     | Set to `production`.                                 |
| `SECRET_KEY`      | Flask session signing key.                           |
| `API_KEY`         | Bearer token clients must send.                      |

Generate strong secrets with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

In `production`, the app refuses to start if `SECRET_KEY` or `API_KEY` are
missing — failing closed instead of silently using weak defaults.

### Authentication

Every protected endpoint expects:

```
Authorization: Bearer <API_KEY>
```

The `X-API-Key: <API_KEY>` header is also accepted. The token is compared with
`hmac.compare_digest` and is never echoed back in logs or API responses.

Set `API_KEY_REQUIRED=false` to disable auth (development only).

---

## 3. Running locally (without Docker)

```bash
# 1. Create & activate a virtual environment
python -m venv venv
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
#   then edit .env and set SECRET_KEY / API_KEY

# 4. Start the dev server
python app.py
```

Open <http://localhost:5000/docs> for the Swagger UI.

---

## 4. Running with Docker (recommended for deployment)

### Single command

```bash
docker compose up -d --build
```

Compose reads `.env` from the project root and mounts:

- `./models_data` (read-only) — drop your `.pth` / `.pkl` files here without
  rebuilding the image.
- `./reports` — generated session reports.
- `./logs` — rotating application logs.

Check it's healthy:

```bash
curl http://localhost:5000/health
```

### Manual `docker run`

```bash
docker build -t proctoring-ai-backend .
docker run -d --name proctoring-backend \
  -p 5000:5000 \
  --env-file .env \
  -v $(pwd)/models_data:/app/models_data:ro \
  -v $(pwd)/reports:/app/reports \
  -v $(pwd)/logs:/app/logs \
  proctoring-ai-backend
```

### Production tuning

Gunicorn workers/threads/timeout can be tuned via env:

```bash
GUNICORN_WORKERS=4
GUNICORN_THREADS=8
GUNICORN_TIMEOUT=180
```

---

## 5. Endpoints (summary)

Full schemas live in the Swagger UI at `/docs`.

### Public (Moodle-compatible)

| Method | Path             | Description                       |
| ------ | ---------------- | --------------------------------- |
| GET    | `/health`        | Liveness probe (no auth required) |
| POST   | `/detect/faces`  | Detect faces in an image          |
| POST   | `/verify/face`   | Compare a face to a reference     |
| POST   | `/detect/behavior` | Suspicious-behavior analysis    |
| POST   | `/embeddings`    | Lightweight face embeddings       |
| POST   | `/batch/process` | Process multiple frames at once   |

### Internal (session lifecycle)

All `/api/proctoring/*` routes require the bearer token.

| Method | Path                                | Description              |
| ------ | ----------------------------------- | ------------------------ |
| POST   | `/api/proctoring/session/start`     | Start a session          |
| POST   | `/api/proctoring/session/stop`      | Stop + generate reports  |
| GET    | `/api/proctoring/session/status`    | Current session status   |
| GET    | `/api/proctoring/session/report`    | Current session report   |
| GET    | `/api/proctoring/video/frame`       | JPEG of the latest frame |
| GET    | `/api/proctoring/video/stream`      | MJPEG live stream        |
| GET    | `/api/proctoring/face-detection/stats` | Detector statistics   |
| GET    | `/api/proctoring/eye-tracking/stats` | Eye-tracker statistics  |
| GET    | `/api/proctoring/warnings`          | Recent session warnings  |
| GET    | `/api/proctoring/configuration`     | Public runtime config    |
| PUT    | `/api/proctoring/configuration`     | Update tunable values    |

### Example call

```bash
curl -X POST http://localhost:5000/detect/faces \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"image": "data:image/jpeg;base64,...."}'
```

---

## 6. Security checklist before deployment

- [ ] `ENVIRONMENT=production` in `.env`
- [ ] Long random `SECRET_KEY` and `API_KEY` (never the defaults from the example)
- [ ] `.env` is **not** committed (covered by `.gitignore`)
- [ ] `CORS_ORIGINS` set to your Moodle origin(s), not `*`
- [ ] TLS terminated at a reverse proxy (Nginx, Caddy, cloud LB) in front of the container
- [ ] Logs / reports volumes mounted to durable storage
- [ ] `models_data/` populated with the expected `.pth` / `.pkl` files
  (the system falls back to OpenCV Haar Cascades if they're missing)

---

## 7. Troubleshooting

- **`RuntimeError: SECRET_KEY is required in production`** — set `SECRET_KEY`
  (and `API_KEY`) in your `.env` or container environment.
- **401 Unauthorized on every request** — confirm clients send
  `Authorization: Bearer <token>` and that the value matches `API_KEY`.
- **Swagger UI is empty** — clear the browser cache; `/openapi.json` should
  return JSON.
- **Camera not available in Docker** — webcam capture is for local
  development. The containerized deployment is API-only; clients send frames
  as base64 in the request body.
