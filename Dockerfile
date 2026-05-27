# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Moodle Proctoring AI Backend — production image
# ---------------------------------------------------------------------------
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# OpenCV / MediaPipe runtime libs
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .

# Non-root user
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/logs /app/reports /app/models_data \
    && chown -R app:app /app
USER app

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# Single Uvicorn worker behind Gunicorn: FastAPI runs sync handlers on a
# thread pool, and each worker process loads ~1 GB of model weights, so
# multiple workers would multiply memory without adding throughput.
ENV GUNICORN_WORKERS=1 \
    GUNICORN_TIMEOUT=120 \
    YOLO_VERBOSE=False \
    YOLO_OFFLINE=1

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS} --worker-class uvicorn.workers.UvicornWorker --timeout ${GUNICORN_TIMEOUT} --access-logfile - --error-logfile - asgi:app"]
