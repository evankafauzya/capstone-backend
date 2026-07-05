# syntax=docker/dockerfile:1.7
# ---------------------------------------------------------------------------
# Moodle Proctoring AI Backend — production image (multi-stage, CPU-only)
#
# Stage 1 (builder) compiles all dependencies into an isolated virtualenv.
# Stage 2 (runtime) copies only that venv + the app code, so build tools and
# pip caches never ship in the final image.
#
# Torch/Torchvision/Torchaudio are installed from the PyTorch CPU wheel index.
# None of the compose files request a GPU, and the default PyPI wheels bundle
# CUDA (~2.5 GB). The CPU wheels cut the image by roughly an order of
# magnitude. If you deploy on a CUDA host, swap the index URL below.
# ---------------------------------------------------------------------------

# =============================== builder ===================================
FROM python:3.11-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    DEBIAN_FRONTEND=noninteractive

# build-essential covers the few deps that may build from source on slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# Self-contained virtualenv so the runtime stage can copy it wholesale.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --upgrade pip

# Install the CPU builds of torch first so the requirements.txt resolve below
# finds them already satisfied (PyPI would otherwise pull the CUDA wheels).
RUN pip install --index-url https://download.pytorch.org/whl/cpu \
        torch torchvision torchaudio

COPY requirements.txt ./
RUN pip install -r requirements.txt

# =============================== runtime ===================================
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/opt/venv/bin:$PATH"

# OpenCV / MediaPipe shared libraries + curl for the healthcheck.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender1 \
        libgomp1 \
        libgles2 \
        libegl1 \
        curl \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Bring in the fully-built virtualenv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

COPY . .

# Non-root user. Create every directory config/settings.py writes to
# (models_data, reports, logs, data) so the app can boot even when a volume
# is not mounted over them.
RUN useradd --create-home --shell /bin/bash app \
    && mkdir -p /app/logs /app/reports /app/models_data /app/data \
    && chown -R app:app /app
USER app

EXPOSE 5000

# Models load lazily at startup (torch + ~250 MB of weights), so give the
# readiness probe a generous start period before failures begin to count.
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -fsS http://localhost:5000/health || exit 1

# Single Uvicorn worker behind Gunicorn: FastAPI runs sync handlers on a
# thread pool, and each worker process loads ~1 GB of model weights, so
# multiple workers would multiply memory without adding throughput.
ENV GUNICORN_WORKERS=1 \
    GUNICORN_TIMEOUT=120 \
    YOLO_VERBOSE=False \
    YOLO_OFFLINE=1

CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${GUNICORN_WORKERS} --worker-class uvicorn.workers.UvicornWorker --timeout ${GUNICORN_TIMEOUT} --access-logfile - --error-logfile - asgi:app"]
